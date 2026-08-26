from __future__ import annotations

"""
material_store.py

Purpose
-------
Provide the shared data foundation for the reference-neighbourhood / structural
context pipeline. The module owns material-universe loading, descriptor caching,
feature preparation, material lookup, run-level feature standardisation and the
cheap pair-screening utilities reused by downstream stages.

Scientific role
---------------
This module is infrastructure rather than a scientific decision layer. It
prepares and exposes material records and low-cost descriptors used elsewhere
in the framework. It does not assign Structural Context Profile interpretations,
construct Reference-Neighbourhood Fingerprints, or perform Candidate Context
clustering.

Primary responsibilities
------------------------
1. Load and cache the raw JARVIS 3D / 2D material universes.
2. Build or load the descriptor cache.
3. Merge descriptors into a unified material universe.
4. Prepare consistent numerical feature columns.
5. Sample run-level material pools.
6. Build run-level standardised feature matrices.
7. Expose a lightweight material lookup API.
8. Provide shared cheap pair-screening helpers.
9. Provide interpretation-oriented feature taxonomy helpers used to explain
   structural contrast.

Principal inputs
----------------
- JARVIS datasets obtained through ``jarvis.db.figshare.data``.
- Optional locally supplied / external material records.
- ``MaterialStoreConfig`` and ``DescriptorCacheConfig`` settings.

Principal outputs
-----------------
- A unified pandas DataFrame material universe.
- Descriptor-cache artefacts and associated manifests.
- ``MaterialRecord`` objects returned through the lookup API.
- ``RunFeatureContext`` objects containing standardised run-level features.
- Cheap pair-screening metrics used by downstream utilities.

Key downstream consumers
------------------------
The exact call graph is controlled by the surrounding pipeline, but this module
is intended to be consumed by profile-building, candidate-pool, evidence,
validation and pair-screening stages rather than to act as a command-line
entry point itself.

Reproducibility notes
---------------------
The module uses explicit schema-version constants for persisted artefacts and
stable identifier-based ordering where applicable. Changes to descriptor
definitions, feature taxonomy, schema versions or material-universe construction
should therefore be treated as release-level changes and regression tested.

Compatibility / legacy surface
------------------------------
Some feature-taxonomy and pair-screening helpers are retained as public
compatibility APIs even when they are not called internally by this module.
They should not be treated as dead code solely because an intra-file search
shows no caller. Removal should only follow a repository-wide dependency check.

Non-goals
---------
- Physical-property prediction.
- Final structural-context interpretation.
- Reference-Neighbourhood Fingerprint construction.
- Candidate Context clustering.

The module is deliberately broad because it centralises data-access and cheap
descriptor logic that would otherwise be duplicated across the pipeline.
"""

import json
import math
import logging
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from jarvis.core.atoms import Atoms
from jarvis.db.figshare import data as jarvis_data
from pymatgen.core import Composition, Element
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from sklearn.preprocessing import StandardScaler


# =============================================================================
# Paths / constants
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
RUNS_DIR = BASE_DIR / "runs"

MATERIAL_STORE_SCHEMA_VERSION = "phase3.material_store.v1"
EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION = "phase5.material_store_external.v1"
DESCRIPTOR_CACHE_SCHEMA_VERSION = "phase3.descriptor_cache.v1"
LOGGER_NAME = "lrt.material_store"
logger = logging.getLogger(LOGGER_NAME)


CRYSTAL_SYSTEM_MAP: Dict[str, int] = {
    "triclinic": 1,
    "monoclinic": 2,
    "orthorhombic": 3,
    "tetragonal": 4,
    "trigonal": 5,
    "hexagonal": 6,
    "cubic": 7,
}

NONMETALS = {
    "H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Se", "Br", "I",
    "Te", "As", "Sb", "Bi",
}

FEATURE_CATEGORIES: Dict[str, List[str]] = {
    "scalar": [
        "band_gap",
        "formation_energy",
        "density_feature",
        "exfoliation_energy_feature",
    ],
    "structural": [
        "spacegroup_number",
        "crystal_system_code",
        "n_symmetry_ops",
        "is_centrosymmetric",
        "coord_mean",
        "coord_std",
        "coord_min",
        "coord_max",
        "frac_low_coord_sites",
        "frac_high_coord_sites",
        "volume_per_atom",
    ],
    "dimensional": [
        "a_axis",
        "b_axis",
        "c_axis_cached",
        "c_over_a",
        "c_over_b",
        "max_axis_over_min_axis",
        "frac_z_span",
        "cart_z_span_over_c",
    ],
    "bonding": [
        "bond_mean_en_diff",
        "bond_std_en_diff",
        "bond_max_en_diff",
        "bond_length_mean",
        "bond_length_std",
        "bond_length_range",
        "frac_short_bonds",
        "ionicity_proxy_comp",
    ],
    "composition": [
        "mean_electronegativity",
        "electronegativity_range",
        "atomic_radius_mean",
        "valence_electrons_mean",
        "n_elements",
        "metal_count",
        "nonmetal_count",
    ],
}


# -----------------------------------------------------------------------------
# Publication / dead-code note
# -----------------------------------------------------------------------------
# The helpers in the interpretation taxonomy and cheap pair-screening sections
# form part of the module's public compatibility surface. Several are designed
# to be called from other modules and therefore may have no caller within this
# file. They are intentionally retained for the Phase 1 publication release.
#
# No executable block in this module has been commented out as "dead code".
# Disabling public helpers based only on intra-file usage would risk breaking
# downstream scripts. Any future removal should be preceded by a repository-wide
# import/call audit and a deprecation release.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Interpretation-oriented feature taxonomy
# -----------------------------------------------------------------------------
#
# FEATURE_CATEGORIES above is retained for backwards compatibility.  The aliases
# below give the interpretation layer a stable, explicit vocabulary for explaining
# structural contrast.  Nothing in the existing API is removed or renamed.
#
# The groups are intentionally coarse.  They are not a chemistry ontology, because
# that would be how a simple helper module turns into a filing cabinet with tenure.
# They are designed for pair-level interpretation:
#   - Which family of descriptors changed most?
#   - Is the contrast mainly dimensional, bonding, coordination, composition, or
#     property-proxy driven?
#
FEATURE_GROUPS: Dict[str, List[str]] = {
    "dimensional": [
        "c_over_a",
        "c_over_b",
        "max_axis_over_min_axis",
        "frac_z_span",
        "cart_z_span_over_c",
    ],
    "bonding": [
        "bond_mean_en_diff",
        "bond_std_en_diff",
        "bond_max_en_diff",
        "bond_length_mean",
        "bond_length_std",
        "bond_length_range",
        "frac_short_bonds",
        "ionicity_proxy_comp",
    ],
    "coordination": [
        "coord_mean",
        "coord_std",
        "frac_low_coord_sites",
        "frac_high_coord_sites",
    ],
    "composition": [
        "n_elements",
        "metal_count",
        "nonmetal_count",
        "mean_electronegativity",
        "electronegativity_range",
        "atomic_radius_mean",
        "valence_electrons_mean",
    ],
    "property_proxy": [
        "band_gap",
        "formation_energy",
        "density_feature",
        "exfoliation_energy_feature",
    ],
}

# Human-facing group descriptions used by interpretation code. These are short on
# purpose: detailed narrative belongs in the interpretation engine, not here.
FEATURE_GROUP_DESCRIPTIONS: Dict[str, str] = {
    "dimensional": "axis ratio, anisotropy, and z-span descriptors",
    "bonding": "bond-length and electronegativity-difference proxies",
    "coordination": "local coordination environment descriptors",
    "composition": "composition and element-balance descriptors",
    "property_proxy": "computed property proxies such as band gap, formation energy, density, or exfoliation energy",
}

# Pair-type hints are deliberately lightweight.  They let downstream modules map
# feature groups to interpretation categories without hard-coding strings in five
# different places, which is how codebases become haunted.
FEATURE_GROUP_PAIR_TYPE_HINTS: Dict[str, str] = {
    "dimensional": "dimensional_structural_contrast",
    "bonding": "bonding_environment_contrast",
    "coordination": "coordination_environment_shift",
    "composition": "composition_complexity_shift",
    "property_proxy": "property_proxy_shift",
}

# Minimal feature set recommended for structural-contrast interpretation.  This
# excludes raw lattice/symmetry identifiers that may be useful for evaluators but
# often produce poor human-facing explanations.
INTERPRETATION_FEATURES: List[str] = [
    feature
    for group in ["dimensional", "bonding", "coordination", "composition", "property_proxy"]
    for feature in FEATURE_GROUPS[group]
]

# Reverse lookup: feature -> group.  First match wins if a feature ever appears in
# multiple groups.  Current groups are intentionally non-overlapping.
FEATURE_TO_GROUP: Dict[str, str] = {
    feature: group
    for group, features in FEATURE_GROUPS.items()
    for feature in features
}

ALL_FEATURES: List[str] = [feature for group in FEATURE_CATEGORIES.values() for feature in group]

DEFAULT_SCREENING_FEATURES: List[str] = [
    "band_gap",
    "formation_energy",
    "density_feature",
    "coord_mean",
    "coord_std",
    "frac_low_coord_sites",
    "frac_high_coord_sites",
    "spacegroup_number",
    "volume_per_atom",
    "c_over_a",
    "c_over_b",
    "max_axis_over_min_axis",
    "frac_z_span",
    "ionicity_proxy_comp",
    "electronegativity_range",
    "atomic_radius_mean",
    "valence_electrons_mean",
    "n_elements",
    "metal_count",
    "nonmetal_count",
]

RAW_REQUIRED_COLUMNS_BULK = {
    "jid",
    "formula",
    "atoms",
    "formation_energy_peratom",
    "optb88vdw_bandgap",
    "density",
}

RAW_REQUIRED_COLUMNS_2D = {
    "jid",
    "formula",
    "atoms",
    "formation_energy_peratom",
    "optb88vdw_bandgap",
    "exfoliation_energy",
}

# -----------------------------------------------------------------------------
# Phase 2 physical plausibility support
# -----------------------------------------------------------------------------
#
# These columns are intentionally kept separate from ALL_FEATURES. They annotate
# physical plausibility for reporting and interpretation, but they do not enter
# topology-sensitive ranking, feature standardisation, or cheap contrast screening.
#
PHYSICAL_PLAUSIBILITY_FIELDS: List[str] = [
    "formation_energy",
    "energy_above_hull",
    "known_synthesized",
]

FORMATION_ENERGY_ALIASES: Tuple[str, ...] = (
    "formation_energy",
    "formation_energy_peratom",
    "formation_energy_per_atom",
    "formation_energy_pa",
)

ENERGY_ABOVE_HULL_ALIASES: Tuple[str, ...] = (
    "energy_above_hull",
    "ehull",
    "e_above_hull",
    "e_above_hull_per_atom",
    "energy_above_hull_peratom",
)

KNOWN_SYNTHESIZED_ALIASES: Tuple[str, ...] = (
    "known_synthesized",
    "is_synthesized",
    "synthesized",
    "experimentally_synthesized",
    "icsd",
    "icsd_id",
)

DESCRIPTOR_REQUIRED_COLUMNS = {
    "jid",
    "formula",
    "mean_electronegativity",
    "electronegativity_range",
    "atomic_radius_mean",
    "valence_electrons_mean",
    "spacegroup_number",
    "crystal_system_code",
    "n_symmetry_ops",
    "is_centrosymmetric",
    "coord_mean",
    "coord_std",
    "coord_min",
    "coord_max",
    "frac_low_coord_sites",
    "frac_high_coord_sites",
    "a_axis",
    "b_axis",
    "c_axis_cached",
    "c_over_a",
    "c_over_b",
    "max_axis_over_min_axis",
    "volume_per_atom",
    "frac_z_span",
    "cart_z_span_over_c",
    "bond_mean_en_diff",
    "bond_std_en_diff",
    "bond_max_en_diff",
    "bond_length_mean",
    "bond_length_std",
    "bond_length_range",
    "frac_short_bonds",
    "ionicity_proxy_comp",
    "reduced_formula",
    "chemical_system",
    "n_elements",
    "composition_family",
    "metal_count",
    "nonmetal_count",
}

DESCRIPTOR_NUMERIC_COLUMNS = sorted(
    DESCRIPTOR_REQUIRED_COLUMNS
    - {"jid", "formula", "reduced_formula", "chemical_system", "composition_family"}
)


# =============================================================================
# Config / payload dataclasses
# =============================================================================
@dataclass
class SamplingConfig:
    """Configuration controlling deterministic run-level sampling.
    
    The values define the sizes and random seed used when constructing sampled
    material regimes. ``to_dict`` returns a serialisable representation suitable
    for manifests and persisted run configuration."""
    bulk_metal_sample: int = 40
    bulk_semi_sample: int = 40
    layered_bulk_sample: int = 40
    d2_sample_size: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Return this configuration as a JSON-serialisable dictionary."""
        return asdict(self)


@dataclass
class DescriptorCacheConfig:
    """Configuration for descriptor-cache construction and reuse.
    
    The configuration is intentionally serialisable so cache provenance can be
    recorded alongside generated artefacts."""
    path: str = str(DATASETS_DIR / "material_descriptor_cache.json")
    version: int = 6
    coordination_cutoff: float = 3.0

    def to_dict(self) -> Dict[str, Any]:
        """Return this configuration as a JSON-serialisable dictionary."""
        return asdict(self)


@dataclass
class MaterialStoreConfig:
    """Top-level configuration for building and using ``MaterialStore``.
    
    The configuration groups dataset, cache, sampling and feature settings and
    provides helpers for loading from and writing to JSON-compatible mappings."""
    data_dir: str = str(DATASETS_DIR)
    runs_dir: str = str(RUNS_DIR)
    descriptor_cache: DescriptorCacheConfig = field(default_factory=DescriptorCacheConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)

    # Optional Phase 2 input. If supplied, this CSV should contain a JID column
    # and a known-synthesized status column. The material store only normalises
    # this information; it does not use it for feature scoring or sampling.
    known_synthesized_path: Optional[str] = None
    known_synthesized_jid_column: str = "jid"
    known_synthesized_status_column: str = "known_synthesized"

    # Phase 3 stabilization controls. These default to backwards-compatible
    # behaviour while making deterministic handling and manifest creation explicit.
    schema_version: str = MATERIAL_STORE_SCHEMA_VERSION
    deterministic_sort: bool = True
    write_manifests: bool = True
    numeric_dtype: str = "float64"

    def to_dict(self) -> Dict[str, Any]:
        """Return this configuration as a JSON-serialisable dictionary."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "MaterialStoreConfig":
        """Create ``MaterialStoreConfig`` from a mapping of configuration values."""
        data = dict(payload or {})
        descriptor_payload = data.get("descriptor_cache")
        if isinstance(descriptor_payload, Mapping):
            data["descriptor_cache"] = DescriptorCacheConfig(**dict(descriptor_payload))
        sampling_payload = data.get("sampling")
        if isinstance(sampling_payload, Mapping):
            data["sampling"] = SamplingConfig(**dict(sampling_payload))
        return cls(**data)

    @classmethod
    def from_json(cls, path: str | Path) -> "MaterialStoreConfig":
        """Load ``MaterialStoreConfig`` from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_mapping(json.load(f))

    def write_json(self, path: str | Path) -> None:
        """Write this configuration to JSON for reproducible reuse."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)


@dataclass
class MaterialRecord:
    """Lightweight material record returned by the store lookup API.
    
    The record packages the identifier, row data and prepared feature values needed
    by downstream pipeline stages without exposing datastore implementation details."""
    jid: str
    formula: Optional[str]
    material_type: Optional[str]
    dataset_kind: Optional[str]
    chemical_system: Optional[str]
    reduced_formula: Optional[str]
    composition_family: Optional[str]
    n_elements: Optional[int]
    elements: List[str]
    features: Dict[str, Optional[float]]
    raw: Dict[str, Any]


@dataclass
class RunFeatureContext:
    """Run-level standardisation context for numerical material features.
    
    It records the selected feature names, fitted scaler/statistics and transformed
    matrix required for reproducible pairwise or cohort-level comparisons."""
    run_id: int
    seed: int
    pool_df: pd.DataFrame
    feature_names: List[str]
    X_raw: pd.DataFrame
    X_scaled: np.ndarray
    scaler: StandardScaler
    feature_scale: Dict[str, float]


# =============================================================================
# Small helpers
# =============================================================================
def safe_float(value: Any) -> Optional[float]:
    """Convert a value to ``float`` when possible, otherwise return ``None``.
    
    This helper centralises tolerant numeric coercion for heterogeneous dataframe
    and JSON values used throughout the store."""
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except Exception:
        return None


def clip01(value: Any) -> float:
    """Clamp a numeric value to the inclusive interval ``[0, 1]``."""
    value_f = safe_float(value)
    if value_f is None:
        return 0.0
    return float(np.clip(value_f, 0.0, 1.0))


def require_columns(df: pd.DataFrame, required: Iterable[str], label: str) -> None:
    """Raise a clear error when required dataframe columns are absent."""
    missing = sorted([col for col in required if col not in df.columns])
    if missing:
        raise ValueError(f"Missing required columns in {label}: {missing}")


def coerce_numeric_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Return a dataframe with selected columns coerced to numeric values."""
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def first_available_numeric_series(df: pd.DataFrame, aliases: Sequence[str]) -> pd.Series:
    """
    Return the first non-null numeric value across a list of possible column names.

    The returned Series always has df.index. Missing aliases are ignored. If no
    alias exists, the result is all-NaN.
    """

    result = pd.Series(np.nan, index=df.index, dtype="float64")
    for alias in aliases:
        if alias not in df.columns:
            continue
        values = pd.to_numeric(df[alias], errors="coerce")
        result = result.where(result.notna(), values)
    return result


def coerce_optional_bool(value: Any) -> Optional[bool]:
    """Convert loose status values into True/False/None."""

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            if math.isnan(float(value)):
                return None
        except Exception:
            pass
        return bool(float(value) != 0.0)
    text = str(value).strip().lower()
    if not text or text in {"nan", "none", "null", "unknown", "na", "n/a"}:
        return None
    if text in {"true", "t", "yes", "y", "1", "known", "synthesized", "synthesised", "experimental", "experiment"}:
        return True
    if text in {"false", "f", "no", "n", "0", "not_known", "not synthesized", "not_synthesized"}:
        return False
    # Non-empty identifiers or database references are treated as support.
    return True


def first_available_bool_series(df: pd.DataFrame, aliases: Sequence[str]) -> pd.Series:
    """
    Return the first non-null boolean-like value across a list of possible columns.

    The dtype is object so missing values remain None rather than becoming False.
    """

    result = pd.Series([None] * len(df), index=df.index, dtype="object")
    for alias in aliases:
        if alias not in df.columns:
            continue
        values = df[alias].map(coerce_optional_bool)
        mask = result.isna() & values.notna()
        result.loc[mask] = values.loc[mask]
    return result


def load_known_synthesized_map(
    path: Optional[str],
    jid_column: str = "jid",
    status_column: str = "known_synthesized",
) -> Dict[str, Optional[bool]]:
    """Load an optional external known-synthesized map from CSV."""

    if not path:
        return {}
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Known-synthesized CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if jid_column not in df.columns:
        raise ValueError(f"Known-synthesized CSV must contain JID column '{jid_column}'.")
    if status_column not in df.columns:
        raise ValueError(f"Known-synthesized CSV must contain status column '{status_column}'.")

    mapping: Dict[str, Optional[bool]] = {}
    for _, row in df.iterrows():
        jid = row.get(jid_column)
        if jid is None or pd.isna(jid):
            continue
        mapping[str(jid)] = coerce_optional_bool(row.get(status_column))
    return mapping


def apply_known_synthesized_map(df: pd.DataFrame, known_map: Dict[str, Optional[bool]]) -> pd.DataFrame:
    """Overlay an external known-synthesized map onto an existing dataframe."""

    out = df.copy()
    if "known_synthesized" not in out.columns:
        out["known_synthesized"] = first_available_bool_series(out, KNOWN_SYNTHESIZED_ALIASES)
    if not known_map or "jid" not in out.columns:
        return out

    mapped = out["jid"].astype(str).map(known_map)
    mask = mapped.notna()
    out.loc[mask, "known_synthesized"] = mapped.loc[mask]
    return out


def classify_composition_family(elements: Sequence[str]) -> Optional[str]:
    """Assign a coarse composition-family label from a chemical formula.
    
    The classification is a lightweight heuristic used for organisation and
    screening; it is not intended to be a comprehensive chemistry ontology."""
    try:
        elems = [str(x) for x in elements if x]
        if not elems:
            return None
        if len(elems) == 1:
            return "elemental"

        metals = 0
        nonmetals = 0
        halogens = 0
        oxygens = 0
        chalcogens = 0

        for symbol in elems:
            if symbol == "O":
                oxygens += 1
            if symbol in {"S", "Se", "Te"}:
                chalcogens += 1
            if symbol in {"F", "Cl", "Br", "I"}:
                halogens += 1
            if symbol in NONMETALS:
                nonmetals += 1
            else:
                metals += 1

        if oxygens > 0:
            return "oxide"
        if halogens > 0:
            return "halide"
        if chalcogens > 0:
            return "chalcogenide"
        if metals >= 2 and nonmetals == 0:
            return "intermetallic"
        return "mixed_compound"
    except Exception:
        return None


def get_element_set_from_formula(formula: Optional[str]) -> List[str]:
    """Return the set of element symbols parsed from a chemical formula."""
    if not formula:
        return []
    try:
        comp = Composition(formula)
        return sorted([str(el.symbol) for el in comp.elements])
    except Exception:
        return []


def stable_pair_key(jid_a: str, jid_b: str) -> str:
    """Return an order-independent identifier for a pair of material IDs.
    
    This helper is part of the compatibility surface used by pair-oriented
    utilities; absence of an internal caller does not by itself make it dead code."""
    a, b = sorted([str(jid_a), str(jid_b)])
    return f"{a}__{b}"



def get_feature_groups(include_legacy_categories: bool = False) -> Dict[str, List[str]]:
    """
    Return a copy of the interpretation-oriented feature taxonomy.

    Parameters
    ----------
    include_legacy_categories:
        If True, also include any FEATURE_CATEGORIES groups not already present.
        This preserves access to legacy groups such as "scalar" or "structural"
        without forcing the interpretation layer to use them.
    """
    groups = {group: list(features) for group, features in FEATURE_GROUPS.items()}
    if include_legacy_categories:
        for group, features in FEATURE_CATEGORIES.items():
            groups.setdefault(group, list(features))
    return groups


def get_interpretation_feature_names() -> List[str]:
    """Return the recommended feature list for structural contrast interpretation."""
    return list(INTERPRETATION_FEATURES)


def get_feature_group(feature_name: str, default: Optional[str] = None) -> Optional[str]:
    """Return the interpretation group for a feature name, if known."""
    return FEATURE_TO_GROUP.get(str(feature_name), default)


def get_features_for_group(group_name: str) -> List[str]:
    """Return the features belonging to an interpretation group."""
    return list(FEATURE_GROUPS.get(str(group_name), []))


def get_feature_group_descriptions() -> Dict[str, str]:
    """Return human-facing descriptions of interpretation feature groups."""
    return dict(FEATURE_GROUP_DESCRIPTIONS)


def get_feature_group_pair_type_hints() -> Dict[str, str]:
    """Return suggested pair-type labels for dominant feature groups."""
    return dict(FEATURE_GROUP_PAIR_TYPE_HINTS)


def get_interpretation_feature_taxonomy() -> Dict[str, Any]:
    """
    Return a compact taxonomy payload for downstream interpretation modules.

    This helper is additive and does not affect existing MaterialStore behaviour.
    """
    return {
        "feature_groups": get_feature_groups(),
        "feature_to_group": dict(FEATURE_TO_GROUP),
        "group_descriptions": get_feature_group_descriptions(),
        "pair_type_hints": get_feature_group_pair_type_hints(),
        "interpretation_features": get_interpretation_feature_names(),
    }


def group_signed_deltas(
    signed_deltas: Dict[str, float],
    feature_groups: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Summarise signed deltas by interpretation feature group.

    Parameters
    ----------
    signed_deltas:
        Mapping feature -> signed standardised delta, where positive means B is
        higher than A.
    feature_groups:
        Optional custom taxonomy. Defaults to FEATURE_GROUPS.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Per group summary with mean absolute delta, max absolute delta, signed
        mean delta, feature count, and dominant feature.
    """
    groups = feature_groups or FEATURE_GROUPS
    result: Dict[str, Dict[str, Any]] = {}

    for group, features in groups.items():
        vals: List[Tuple[str, float]] = []
        for feature in features:
            if feature not in signed_deltas:
                continue
            value = safe_float(signed_deltas.get(feature))
            if value is None:
                continue
            vals.append((feature, float(value)))

        if not vals:
            result[group] = {
                "feature_count": 0,
                "mean_abs_delta": 0.0,
                "max_abs_delta": 0.0,
                "signed_mean_delta": 0.0,
                "dominant_feature": None,
                "dominant_feature_delta": None,
            }
            continue

        arr = np.array([v for _, v in vals], dtype=float)
        abs_arr = np.abs(arr)
        dominant_idx = int(np.argmax(abs_arr))
        dominant_feature, dominant_value = vals[dominant_idx]
        result[group] = {
            "feature_count": int(len(vals)),
            "mean_abs_delta": float(np.mean(abs_arr)),
            "max_abs_delta": float(np.max(abs_arr)),
            "signed_mean_delta": float(np.mean(arr)),
            "dominant_feature": dominant_feature,
            "dominant_feature_delta": float(dominant_value),
        }

    return result


def dominant_delta_groups(
    signed_deltas: Dict[str, float],
    top_n: int = 2,
    feature_groups: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Return the strongest interpretation groups for a signed-delta mapping.

    Groups are ordered by mean_abs_delta, descending.  This helper is intended for
    the structural contrast classifier, not for legacy screening.
    """
    grouped = group_signed_deltas(signed_deltas, feature_groups=feature_groups)
    rows = []
    for group, payload in grouped.items():
        rows.append({"group": group, **payload})
    rows.sort(key=lambda row: float(row.get("mean_abs_delta", 0.0)), reverse=True)
    return rows[: max(int(top_n), 1)]


def top_signed_delta_features(
    signed_deltas: Dict[str, float],
    top_n: int = 8,
    min_abs_delta: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Return top signed-delta features with group annotations.

    This gives interpretation modules a ready-made feature-driver list while
    leaving old absolute-delta screening untouched.
    """
    rows: List[Dict[str, Any]] = []
    for feature, value in signed_deltas.items():
        value_f = safe_float(value)
        if value_f is None:
            continue
        if abs(value_f) < float(min_abs_delta):
            continue
        rows.append({
            "feature": feature,
            "feature_group": get_feature_group(feature),
            "signed_delta": float(value_f),
            "abs_delta": float(abs(value_f)),
            "direction": "increase" if value_f > 0 else "decrease" if value_f < 0 else "no_change",
        })
    rows.sort(key=lambda row: row["abs_delta"], reverse=True)
    return rows[: max(int(top_n), 1)]


# =============================================================================
# Descriptor builders reused from discovery
# =============================================================================


def configure_material_store_logging(level: int = logging.INFO, log_file: Optional[str | Path] = None) -> logging.Logger:
    """Configure module logging in a reusable, idempotent way."""

    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_lrt_console", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler._lrt_console = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(handler)
    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(file_handler)
    return logger


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def write_json_artifact(payload: Mapping[str, Any], path: str | Path) -> None:
    """Write a stable JSON artifact with sorted keys."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(payload), f, indent=2, sort_keys=True, default=_json_default)


def sort_by_jid(df: pd.DataFrame) -> pd.DataFrame:
    """Return a deterministic jid-sorted dataframe when a jid column is present."""

    if "jid" not in df.columns:
        return df.reset_index(drop=True)
    return df.assign(_jid_sort_key=df["jid"].astype(str)).sort_values("_jid_sort_key", kind="mergesort").drop(columns=["_jid_sort_key"]).reset_index(drop=True)


def validate_material_store_config(config: MaterialStoreConfig) -> None:
    """Fail fast on configuration values that would make runs ambiguous."""

    if config.descriptor_cache.version is None:
        raise ValueError("descriptor_cache.version must be set.")
    if config.numeric_dtype not in {"float32", "float64"}:
        raise ValueError("numeric_dtype must be 'float32' or 'float64'.")
    for name in ("bulk_metal_sample", "bulk_semi_sample", "layered_bulk_sample", "d2_sample_size"):
        value = getattr(config.sampling, name)
        if int(value) < 0:
            raise ValueError(f"sampling.{name} must be non-negative.")


def material_store_manifest(config: MaterialStoreConfig, universe_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Build a compact manifest describing the material-store foundation for a run."""

    manifest: Dict[str, Any] = {
        "schema_version": MATERIAL_STORE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "all_features": list(ALL_FEATURES),
        "default_screening_features": list(DEFAULT_SCREENING_FEATURES),
        "physical_plausibility_fields": list(PHYSICAL_PLAUSIBILITY_FIELDS),
    }
    if universe_df is not None:
        manifest["universe_row_count"] = int(len(universe_df))
        manifest["universe_unique_jids"] = int(universe_df["jid"].nunique()) if "jid" in universe_df.columns else None
        manifest["dataset_kind_counts"] = {str(k): int(v) for k, v in universe_df.get("dataset_kind", pd.Series(dtype=object)).value_counts(dropna=False).to_dict().items()}
    return manifest


def descriptor_cache_manifest(config: MaterialStoreConfig, descriptor_df: pd.DataFrame) -> Dict[str, Any]:
    """Build a manifest for descriptor cache provenance and invalidation checks."""

    return {
        "schema_version": DESCRIPTOR_CACHE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "descriptor_cache_version": int(config.descriptor_cache.version),
        "coordination_cutoff": float(config.descriptor_cache.coordination_cutoff),
        "record_count": int(len(descriptor_df)),
        "required_columns": sorted(DESCRIPTOR_REQUIRED_COLUMNS),
        "numeric_columns": list(DESCRIPTOR_NUMERIC_COLUMNS),
    }

def load_raw_datasets(config: MaterialStoreConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the configured raw JARVIS material datasets.
    
    Returns the raw source frames used to construct the unified material universe.
    Dataset retrieval is kept in one function so provenance and failure handling
    remain consistent across the pipeline."""
    logger.info("Loading raw JARVIS datasets...")
    bulk_cache = Path(config.data_dir) / "jarvis_dft_3d_raw.json"
    d2_cache = Path(config.data_dir) / "jarvis_dft_2d_raw.json"

    if bulk_cache.exists():
        logger.info("Reading cached bulk dataset: %s", bulk_cache)
        bulk = pd.read_json(bulk_cache)
    else:
        logger.info("Downloading JARVIS dft_3d dataset...")
        bulk = pd.DataFrame(jarvis_data("dft_3d"))
        bulk.to_json(bulk_cache, orient="records")
        logger.info("Cached bulk dataset: %s", bulk_cache)

    if d2_cache.exists():
        logger.info("Reading cached 2D dataset: %s", d2_cache)
        d2 = pd.read_json(d2_cache)
    else:
        logger.info("Downloading JARVIS dft_2d dataset...")
        d2 = pd.DataFrame(jarvis_data("dft_2d"))
        d2.to_json(d2_cache, orient="records")
        logger.info("Cached 2D dataset: %s", d2_cache)

    require_columns(bulk, RAW_REQUIRED_COLUMNS_BULK, "raw bulk dataset")
    require_columns(d2, RAW_REQUIRED_COLUMNS_2D, "raw 2D dataset")

    bulk = bulk.copy()
    d2 = d2.copy()

    bulk["dataset_kind"] = "dft_3d"
    bulk["material_type"] = "bulk"

    d2["dataset_kind"] = "dft_2d"
    d2["material_type"] = "2d"

    if config.deterministic_sort:
        bulk = sort_by_jid(bulk)
        d2 = sort_by_jid(d2)
    logger.info("Raw datasets ready: bulk=%s, 2D=%s", len(bulk), len(d2))
    return bulk, d2


def build_sampling_regimes(bulk_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Construct deterministic run-level material sampling regimes.
    
    Sampling is governed by ``SamplingConfig`` and is intended to provide bounded,
    repeatable subsets for downstream exploratory or validation workflows."""
    bulk = bulk_df.copy()
    bulk["band_gap_numeric"] = pd.to_numeric(bulk["optb88vdw_bandgap"], errors="coerce")
    bulk["c_axis_numeric"] = np.nan

    for idx, row in bulk.iterrows():
        atoms = row.get("atoms")
        try:
            atom_obj = Atoms.from_dict(atoms) if isinstance(atoms, dict) else None
            if atom_obj is not None:
                lattice = atom_obj.lattice_mat
                if lattice is not None and len(lattice) == 3:
                    c_len = float(np.linalg.norm(np.array(lattice[2], dtype=float)))
                    bulk.at[idx, "c_axis_numeric"] = c_len
        except Exception:
            continue

    regimes = {
        "bulk_metals": bulk[bulk["band_gap_numeric"] < 0.1].copy(),
        "bulk_semis": bulk[(bulk["band_gap_numeric"] >= 0.1) & (bulk["band_gap_numeric"] < 3.0)].copy(),
        "layered_bulk": bulk[bulk["c_axis_numeric"] > 12.0].copy(),
    }
    return regimes


def _coordination_stats(atom_obj: Atoms, cutoff: float) -> Dict[str, Optional[float]]:
    """Compute low-cost coordination statistics for a structure."""
    try:
        coords: List[int] = []
        lattice = np.array(atom_obj.lattice_mat, dtype=float)
        frac = np.array(atom_obj.frac_coords, dtype=float)
        cart = np.array(atom_obj.cart_coords, dtype=float)
        n_sites = len(cart)

        image_shifts = np.array(
            [[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)],
            dtype=float,
        )

        for i in range(n_sites):
            center = cart[i]
            count = 0
            for j in range(n_sites):
                tiled = frac[j] + image_shifts
                tiled_cart = tiled @ lattice
                dists = np.linalg.norm(tiled_cart - center, axis=1)
                if i == j:
                    dists = dists[dists > 1e-8]
                if np.any(dists <= cutoff):
                    count += int(np.sum(dists <= cutoff))
            coords.append(count)

        arr = np.array(coords, dtype=float)
        return {
            "coord_mean": float(np.mean(arr)),
            "coord_std": float(np.std(arr)),
            "coord_min": float(np.min(arr)),
            "coord_max": float(np.max(arr)),
            "frac_low_coord_sites": float(np.mean(arr <= 3.0)),
            "frac_high_coord_sites": float(np.mean(arr >= 8.0)),
        }
    except Exception:
        return {
            "coord_mean": None,
            "coord_std": None,
            "coord_min": None,
            "coord_max": None,
            "frac_low_coord_sites": None,
            "frac_high_coord_sites": None,
        }


def _bonding_proxies(atom_obj: Atoms) -> Dict[str, Optional[float]]:
    """Compute inexpensive bonding-proxy descriptors for a structure."""
    try:
        elements = [str(x) for x in atom_obj.elements]
        en_map: Dict[str, Optional[float]] = {}
        for symbol in set(elements):
            try:
                en_map[symbol] = float(Element(symbol).X)
            except Exception:
                en_map[symbol] = None

        cart = np.array(atom_obj.cart_coords, dtype=float)
        n_sites = len(cart)
        pair_dists: List[float] = []
        pair_en_diffs: List[float] = []

        if n_sites <= 1:
            return {
                "bond_mean_en_diff": None,
                "bond_std_en_diff": None,
                "bond_max_en_diff": None,
                "bond_length_mean": None,
                "bond_length_std": None,
                "bond_length_range": None,
                "frac_short_bonds": None,
                "ionicity_proxy_comp": None,
            }

        lattice = np.array(atom_obj.lattice_mat, dtype=float)
        frac = np.array(atom_obj.frac_coords, dtype=float)
        image_shifts = np.array(
            [[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)],
            dtype=float,
        )

        for i in range(n_sites):
            for j in range(i + 1, n_sites):
                tiled = frac[j] + image_shifts
                tiled_cart = tiled @ lattice
                dists = np.linalg.norm(tiled_cart - cart[i], axis=1)
                d = float(np.min(dists))
                if d <= 4.0:
                    pair_dists.append(d)
                    en_i = en_map.get(elements[i])
                    en_j = en_map.get(elements[j])
                    if en_i is not None and en_j is not None:
                        pair_en_diffs.append(abs(en_i - en_j))

        if not pair_dists:
            return {
                "bond_mean_en_diff": None,
                "bond_std_en_diff": None,
                "bond_max_en_diff": None,
                "bond_length_mean": None,
                "bond_length_std": None,
                "bond_length_range": None,
                "frac_short_bonds": None,
                "ionicity_proxy_comp": None,
            }

        d_arr = np.array(pair_dists, dtype=float)
        en_arr = np.array(pair_en_diffs, dtype=float) if pair_en_diffs else np.array([], dtype=float)

        ionicity_proxy = None
        formula_elements = sorted(set(elements))
        if formula_elements:
            ens: List[float] = []
            for symbol in formula_elements:
                try:
                    ens.append(float(Element(symbol).X))
                except Exception:
                    continue
            if ens:
                ionicity_proxy = float(max(ens) - min(ens))

        return {
            "bond_mean_en_diff": float(en_arr.mean()) if en_arr.size else None,
            "bond_std_en_diff": float(en_arr.std()) if en_arr.size else None,
            "bond_max_en_diff": float(en_arr.max()) if en_arr.size else None,
            "bond_length_mean": float(d_arr.mean()),
            "bond_length_std": float(d_arr.std()),
            "bond_length_range": float(d_arr.max() - d_arr.min()),
            "frac_short_bonds": float(np.mean(d_arr < 2.2)),
            "ionicity_proxy_comp": ionicity_proxy,
        }
    except Exception:
        return {
            "bond_mean_en_diff": None,
            "bond_std_en_diff": None,
            "bond_max_en_diff": None,
            "bond_length_mean": None,
            "bond_length_std": None,
            "bond_length_range": None,
            "frac_short_bonds": None,
            "ionicity_proxy_comp": None,
        }


def composition_reachability_features(formula: str) -> Dict[str, Any]:
    """Compute composition-based features used by cheap pair screening."""
    try:
        comp = Composition(formula).reduced_composition
        elements = sorted([str(el.symbol) for el in comp.elements])
        family = classify_composition_family(elements)
        return {
            "reduced_formula": comp.reduced_formula,
            "chemical_system": "-".join(elements),
            "n_elements": int(len(elements)),
            "composition_family": family,
            "metal_count": int(sum(1 for e in elements if e not in NONMETALS)),
            "nonmetal_count": int(sum(1 for e in elements if e in NONMETALS)),
            "element_set": elements,
        }
    except Exception:
        return {
            "reduced_formula": formula,
            "chemical_system": None,
            "n_elements": None,
            "composition_family": None,
            "metal_count": None,
            "nonmetal_count": None,
            "element_set": [],
        }


def _compute_single_descriptor(row: pd.Series, config: MaterialStoreConfig) -> Dict[str, Any]:
    """Compute the descriptor record for one material row."""
    record: Dict[str, Any] = {
        "jid": row.get("jid"),
        "formula": row.get("formula"),
    }

    formula = row.get("formula")
    if isinstance(formula, str):
        record.update(composition_reachability_features(formula))

    atoms_dict = row.get("atoms")
    atom_obj: Optional[Atoms] = None
    try:
        if isinstance(atoms_dict, dict):
            atom_obj = Atoms.from_dict(atoms_dict)
    except Exception:
        atom_obj = None

    if atom_obj is None:
        for key in DESCRIPTOR_NUMERIC_COLUMNS:
            record.setdefault(key, None)
        return record

    try:
        lengths = atom_obj.lattice.abc
        record["a_axis"] = float(lengths[0])
        record["b_axis"] = float(lengths[1])
        record["c_axis_cached"] = float(lengths[2])
        record["c_over_a"] = float(lengths[2] / lengths[0]) if lengths[0] else None
        record["c_over_b"] = float(lengths[2] / lengths[1]) if lengths[1] else None
        record["max_axis_over_min_axis"] = float(max(lengths) / min(lengths)) if min(lengths) > 0 else None
    except Exception:
        record["a_axis"] = None
        record["b_axis"] = None
        record["c_axis_cached"] = None
        record["c_over_a"] = None
        record["c_over_b"] = None
        record["max_axis_over_min_axis"] = None

    try:
        frac = np.array(atom_obj.frac_coords, dtype=float)
        cart = np.array(atom_obj.cart_coords, dtype=float)
        record["frac_z_span"] = float(np.max(frac[:, 2]) - np.min(frac[:, 2]))
        c_axis = safe_float(record.get("c_axis_cached"))
        if c_axis is not None and c_axis > 1e-8:
            record["cart_z_span_over_c"] = float((np.max(cart[:, 2]) - np.min(cart[:, 2])) / c_axis)
        else:
            record["cart_z_span_over_c"] = None
    except Exception:
        record["frac_z_span"] = None
        record["cart_z_span_over_c"] = None

    try:
        record["volume_per_atom"] = float(atom_obj.volume / atom_obj.num_atoms) if atom_obj.num_atoms else None
    except Exception:
        record["volume_per_atom"] = None

    try:
        sga = SpacegroupAnalyzer(atom_obj.pymatgen_converter())
        record["spacegroup_number"] = int(sga.get_space_group_number())
        record["crystal_system_code"] = CRYSTAL_SYSTEM_MAP.get(str(sga.get_crystal_system()).lower())
        symm_ops = sga.get_symmetry_operations()
        record["n_symmetry_ops"] = int(len(symm_ops)) if symm_ops is not None else None
        try:
            record["is_centrosymmetric"] = int(bool(sga.is_laue()))
        except Exception:
            record["is_centrosymmetric"] = None
    except Exception:
        record["spacegroup_number"] = None
        record["crystal_system_code"] = None
        record["n_symmetry_ops"] = None
        record["is_centrosymmetric"] = None

    record.update(_coordination_stats(atom_obj, cutoff=config.descriptor_cache.coordination_cutoff))
    record.update(_bonding_proxies(atom_obj))

    try:
        comp = Composition(str(row.get("formula")))
        en_vals: List[float] = []
        radius_vals: List[float] = []
        valence_vals: List[float] = []
        for el in comp.elements:
            try:
                e = Element(el.symbol)
                if e.X is not None:
                    en_vals.append(float(e.X))
                if getattr(e, "atomic_radius", None) is not None:
                    radius_vals.append(float(e.atomic_radius))
                try:
                    valence_vals.append(float(e.group))
                except Exception:
                    pass
            except Exception:
                continue
        record["mean_electronegativity"] = float(np.mean(en_vals)) if en_vals else None
        record["electronegativity_range"] = float(max(en_vals) - min(en_vals)) if len(en_vals) >= 2 else None
        record["atomic_radius_mean"] = float(np.mean(radius_vals)) if radius_vals else None
        record["valence_electrons_mean"] = float(np.mean(valence_vals)) if valence_vals else None
    except Exception:
        record["mean_electronegativity"] = None
        record["electronegativity_range"] = None
        record["atomic_radius_mean"] = None
        record["valence_electrons_mean"] = None

    for key in DESCRIPTOR_NUMERIC_COLUMNS:
        record.setdefault(key, None)
    return record


def build_or_load_descriptor_cache(
    bulk_df: pd.DataFrame,
    d2_df: pd.DataFrame,
    config: MaterialStoreConfig,
) -> pd.DataFrame:
    """Build the descriptor cache or load a compatible existing cache.
    
    Cache reuse is controlled by the supplied configuration and schema metadata.
    The returned cache is the canonical descriptor source merged into the material
    universe."""
    cache_path = Path(config.descriptor_cache.path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        logger.info("Reading descriptor cache: %s", cache_path)
        with open(cache_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("version") == config.descriptor_cache.version:
            cache_df = pd.DataFrame(payload.get("records", []))
            if not cache_df.empty:
                if config.deterministic_sort:
                    cache_df = sort_by_jid(cache_df)
                logger.info("Descriptor cache ready: %s records", len(cache_df))
                return cache_df
        logger.info("Descriptor cache version mismatch or empty; rebuilding cache...")

    source_df = pd.concat([bulk_df[["jid", "formula", "atoms"]], d2_df[["jid", "formula", "atoms"]]], ignore_index=True)
    source_df = source_df.drop_duplicates(subset=["jid"]).reset_index(drop=True)
    if config.deterministic_sort:
        source_df = sort_by_jid(source_df)

    logger.info("Building descriptor cache for %s materials...", len(source_df))
    records: List[Dict[str, Any]] = []
    for idx, row in source_df.iterrows():
        if idx % 500 == 0:
            logger.info("Descriptor progress: %s/%s", idx, len(source_df))
        records.append(_compute_single_descriptor(row, config))

    cache_df = pd.DataFrame(records)
    if config.deterministic_sort:
        cache_df = sort_by_jid(cache_df)
        records = cache_df.to_dict(orient="records")
    payload = {"version": config.descriptor_cache.version, "schema_version": DESCRIPTOR_CACHE_SCHEMA_VERSION, "manifest": descriptor_cache_manifest(config, cache_df), "records": records}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=_json_default)
    if config.write_manifests:
        write_json_artifact(payload["manifest"], cache_path.with_suffix(cache_path.suffix + ".manifest.json"))
    logger.info("Descriptor cache written: %s", cache_path)
    return cache_df


def merge_descriptor_cache(
    bulk_df: pd.DataFrame,
    d2_df: pd.DataFrame,
    descriptor_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Merge descriptor-cache columns into the raw material universe."""
    require_columns(descriptor_df, {"jid", "formula"}, "descriptor cache")

    bulk_merged = bulk_df.merge(descriptor_df, on=["jid", "formula"], how="left")
    d2_merged = d2_df.merge(descriptor_df, on=["jid", "formula"], how="left")

    return bulk_merged, d2_merged


# =============================================================================
# Feature prep reused from discovery
# =============================================================================
def ensure_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure that all configured feature columns exist and are numerically usable."""
    df = df.copy()

    df["density_feature"] = pd.to_numeric(df["density"], errors="coerce") if "density" in df.columns else np.nan
    df["band_gap"] = (
        pd.to_numeric(df["optb88vdw_bandgap"], errors="coerce") if "optb88vdw_bandgap" in df.columns else np.nan
    )

    # Phase 2 physical plausibility fields. formation_energy remains part of the
    # legacy scalar feature set for backwards compatibility. energy_above_hull
    # and known_synthesized are deliberately not added to ALL_FEATURES, so they
    # can annotate plausibility without changing topology ranking.
    df["formation_energy"] = first_available_numeric_series(df, FORMATION_ENERGY_ALIASES)
    df["energy_above_hull"] = first_available_numeric_series(df, ENERGY_ABOVE_HULL_ALIASES)
    df["known_synthesized"] = first_available_bool_series(df, KNOWN_SYNTHESIZED_ALIASES)

    df["exfoliation_energy_feature"] = (
        pd.to_numeric(df["exfoliation_energy"], errors="coerce") if "exfoliation_energy" in df.columns else np.nan
    )

    for feat in ALL_FEATURES:
        if feat not in df.columns:
            df[feat] = np.nan

    for field_name in PHYSICAL_PLAUSIBILITY_FIELDS:
        if field_name not in df.columns:
            df[field_name] = np.nan if field_name != "known_synthesized" else None

    require_columns(df, ALL_FEATURES, "feature-prepared df")
    require_columns(df, PHYSICAL_PLAUSIBILITY_FIELDS, "physical-plausibility prepared df")
    df = coerce_numeric_columns(df, ALL_FEATURES)
    df["energy_above_hull"] = pd.to_numeric(df["energy_above_hull"], errors="coerce")
    df["known_synthesized"] = df["known_synthesized"].map(coerce_optional_bool)
    return df


def build_feature_matrix(df: pd.DataFrame, feature_names: Sequence[str]) -> Tuple[pd.DataFrame, np.ndarray, StandardScaler, Dict[str, float]]:
    """Build a standardised numerical feature matrix for a material dataframe."""
    require_columns(df, feature_names, "build_feature_matrix input")

    X = df.loc[:, list(feature_names)].copy()
    X = X.replace([np.inf, -np.inf], np.nan)

    all_nan_cols = X.columns[X.isna().all()].tolist()
    if all_nan_cols:
        print(f"All-NaN feature columns found, filling with 0.0: {all_nan_cols}")
        X.loc[:, all_nan_cols] = 0.0

    median_map = X.median(numeric_only=True)
    X = X.fillna(median_map).fillna(0.0)

    if X.isna().any().any():
        raise ValueError("Feature matrix still contains NaN after imputation.")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if not np.isfinite(X_scaled).all():
        raise ValueError("Scaled feature matrix contains NaN or inf.")

    feature_scale: Dict[str, float] = {}
    for col in X.columns:
        std = float(np.std(X[col].values))
        feature_scale[col] = std if std > 1e-12 else 1.0

    return X, X_scaled, scaler, feature_scale


# =============================================================================
# Shared cheap pair-screening helpers
# =============================================================================
def structural_continuity_score_from_records(a: MaterialRecord, b: MaterialRecord) -> float:
    """Calculate a cheap structural-continuity score for two records."""
    sg_a = safe_float(a.features.get("spacegroup_number"))
    sg_b = safe_float(b.features.get("spacegroup_number"))
    cs_a = safe_float(a.features.get("crystal_system_code"))
    cs_b = safe_float(b.features.get("crystal_system_code"))
    coord_a = safe_float(a.features.get("coord_mean"))
    coord_b = safe_float(b.features.get("coord_mean"))

    score = 0.0
    if sg_a is not None and sg_b is not None:
        dsg = abs(sg_a - sg_b)
        if dsg <= 20:
            score += 0.35
        elif dsg <= 80:
            score += 0.15

    if cs_a is not None and cs_b is not None and int(cs_a) == int(cs_b):
        score += 0.20

    if coord_a is not None and coord_b is not None:
        dc = abs(coord_a - coord_b)
        if dc <= 1.5:
            score += 0.30
        elif dc <= 3.0:
            score += 0.15

    return float(np.clip(score, 0.0, 1.0))


def compute_pair_reachability(a: MaterialRecord, b: MaterialRecord) -> Dict[str, Any]:
    """Compute cheap composition and structural reachability metrics for a pair."""
    formula_a = a.formula
    formula_b = b.formula

    try:
        comp_a = Composition(str(formula_a)).reduced_composition
        comp_b = Composition(str(formula_b)).reduced_composition
    except Exception:
        return {
            "hard_reject": True,
            "reachability_score": 0.0,
            "chemical_reachability_score": 0.0,
            "structural_continuity_score": 0.0,
            "element_jaccard": 0.0,
            "same_reduced_formula": False,
            "same_chemical_system": False,
            "same_family": False,
            "reasons": ["composition_parse_failure"],
        }

    elems_a = {el.symbol for el in comp_a.elements}
    elems_b = {el.symbol for el in comp_b.elements}
    overlap = len(elems_a & elems_b)
    union = len(elems_a | elems_b)
    jaccard = overlap / union if union > 0 else 0.0

    family_a = a.composition_family
    family_b = b.composition_family
    same_reduced_formula = comp_a.reduced_formula == comp_b.reduced_formula
    same_chem_sys = "-".join(sorted(elems_a)) == "-".join(sorted(elems_b))
    same_family = family_a == family_b and family_a is not None

    reasons: List[str] = []
    chem_score = 0.0

    if same_reduced_formula:
        chem_score += 1.00
        reasons.append("same_reduced_formula")
    elif same_chem_sys:
        chem_score += 0.75
        reasons.append("same_chemical_system")
    elif jaccard >= 0.5:
        chem_score += 0.45
        reasons.append("substantial_element_overlap")
    elif jaccard > 0.0:
        chem_score += 0.20
        reasons.append("partial_element_overlap")
    else:
        reasons.append("no_element_overlap")

    if same_family:
        chem_score += 0.20
        reasons.append("same_composition_family")
    else:
        reasons.append("different_composition_family")

    if family_a == "elemental" and family_b != "elemental":
        reasons.append("elemental_to_compound_jump")
    if family_b == "elemental" and family_a != "elemental":
        reasons.append("compound_to_elemental_jump")

    if {family_a, family_b} in ({"intermetallic", "halide"}, {"intermetallic", "chalcogenide"}, {"intermetallic", "oxide"}):
        reasons.append("cross_bonding_regime_jump")

    hard_reject = (
        (jaccard == 0.0 and not same_family)
        or ("elemental_to_compound_jump" in reasons)
        or ("compound_to_elemental_jump" in reasons)
        or ("cross_bonding_regime_jump" in reasons and jaccard == 0.0)
    )

    struct_score = structural_continuity_score_from_records(a, b)
    combined = 0.65 * float(np.clip(chem_score, 0.0, 1.0)) + 0.35 * struct_score

    return {
        "hard_reject": bool(hard_reject),
        "reachability_score": float(np.clip(combined, 0.0, 1.0)),
        "chemical_reachability_score": float(np.clip(chem_score, 0.0, 1.0)),
        "structural_continuity_score": float(struct_score),
        "element_jaccard": float(jaccard),
        "same_reduced_formula": bool(same_reduced_formula),
        "same_chemical_system": bool(same_chem_sys),
        "same_family": bool(same_family),
        "reasons": reasons,
    }


def standardized_feature_deltas(
    a: MaterialRecord,
    b: MaterialRecord,
    feature_stats: Dict[str, Dict[str, float]],
    feature_names: Sequence[str],
) -> Dict[str, float]:
    """
    Return absolute standardized feature deltas for pair screening.

    Backward compatibility note
    ---------------------------
    This function intentionally keeps the original absolute-delta behaviour.
    Existing screening code expects positive contrast magnitudes for metrics such
    as mean_std_delta, max_std_delta, and topk_mean_std_delta. Do not change this
    function to signed deltas. Use signed_standardized_feature_deltas() instead.
    """
    deltas: Dict[str, float] = {}
    for feature in feature_names:
        va = safe_float(a.features.get(feature))
        vb = safe_float(b.features.get(feature))
        stats = feature_stats.get(feature)
        if va is None or vb is None or not stats:
            continue
        std = max(float(stats.get("std", 1.0)), 1e-12)
        deltas[feature] = float(abs(va - vb) / std)
    return deltas


def signed_standardized_feature_deltas(
    a: MaterialRecord,
    b: MaterialRecord,
    feature_stats: Dict[str, Dict[str, float]],
    feature_names: Sequence[str],
) -> Dict[str, float]:
    """
    Return signed standardized feature deltas from material A to material B.

    Definition
    ----------
    delta = (feature_B - feature_A) / feature_std

    Positive values mean the candidate/right-hand material has a higher value
    than the query/left-hand material. Negative values mean it has a lower value.

    This helper is intended for transformation-template and proposal-engine
    logic. It is additive and does not alter the legacy absolute-delta screening
    API.
    """
    deltas: Dict[str, float] = {}
    for feature in feature_names:
        va = safe_float(a.features.get(feature))
        vb = safe_float(b.features.get(feature))
        stats = feature_stats.get(feature)
        if va is None or vb is None or not stats:
            continue
        std = max(float(stats.get("std", 1.0)), 1e-12)
        deltas[feature] = float((vb - va) / std)
    return deltas


def compute_pair_screening_metrics(
    a: MaterialRecord,
    b: MaterialRecord,
    feature_stats: Dict[str, Dict[str, float]],
    feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Compute the shared set of low-cost pair-screening metrics."""
    deltas = standardized_feature_deltas(a, b, feature_stats, feature_names)
    values = np.array(list(deltas.values()), dtype=float) if deltas else np.array([], dtype=float)
    sorted_desc = sorted(deltas.items(), key=lambda kv: kv[1], reverse=True)
    top_vals = [float(v) for _, v in sorted_desc[:max(int(top_k), 1)]]

    mean_std_delta = float(np.mean(values)) if values.size else 0.0
    max_std_delta = float(np.max(values)) if values.size else 0.0
    topk_mean_std_delta = float(np.mean(top_vals)) if top_vals else 0.0

    return {
        "feature_count_used": int(values.size),
        "mean_std_delta": mean_std_delta,
        "max_std_delta": max_std_delta,
        "topk_mean_std_delta": topk_mean_std_delta,
        "top_features": [{"feature": k, "std_delta": float(v)} for k, v in sorted_desc[:max(int(top_k), 1)]],
        "per_feature_std_delta": deltas,
    }


def cheap_pair_precheck(
    a: MaterialRecord,
    b: MaterialRecord,
    feature_stats: Dict[str, Dict[str, float]],
    feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
    min_mean_std_delta: float = 0.15,
    min_topk_mean_std_delta: float = 0.25,
    min_max_std_delta: float = 0.30,
    min_feature_count: int = 5,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Apply the inexpensive pair pre-screen used before more costly analysis."""
    reachability = compute_pair_reachability(a, b)
    metrics = compute_pair_screening_metrics(
        a=a,
        b=b,
        feature_stats=feature_stats,
        feature_names=feature_names,
        top_k=top_k,
    )

    reasons: List[str] = []
    anti_triviality_hard_reject = False

    if reachability["hard_reject"]:
        reasons.append("reachability_hard_reject")

    if metrics["feature_count_used"] < int(min_feature_count):
        anti_triviality_hard_reject = True
        reasons.append("too_few_comparable_features")

    if metrics["mean_std_delta"] < float(min_mean_std_delta):
        anti_triviality_hard_reject = True
        reasons.append("low_mean_standardized_delta")

    if metrics["topk_mean_std_delta"] < float(min_topk_mean_std_delta):
        anti_triviality_hard_reject = True
        reasons.append("low_topk_standardized_delta")

    if metrics["max_std_delta"] < float(min_max_std_delta):
        anti_triviality_hard_reject = True
        reasons.append("low_max_standardized_delta")

    passes = (not reachability["hard_reject"]) and (not anti_triviality_hard_reject)

    return {
        "passes": bool(passes),
        "reachability": reachability,
        "anti_triviality_hard_reject": bool(anti_triviality_hard_reject),
        "screening_metrics": metrics,
        "reasons": reasons,
    }


# =============================================================================
# MaterialStore
# =============================================================================
class MaterialStore:
    """
    Shared data access object for later pair sampling / evaluation modules.

    Notes
    -----
    - Reuses the discovery cache-building logic.
    - Also exposes a record API closer to Framework 2a so downstream code can
      resolve a jid without caring where the row originally came from.
    """

    def __init__(self, config: Optional[MaterialStoreConfig] = None) -> None:
        """Initialise the material store from configuration without changing scientific logic."""
        self.config = config or MaterialStoreConfig()
        validate_material_store_config(self.config)
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.runs_dir).mkdir(parents=True, exist_ok=True)

        self.bulk_df: Optional[pd.DataFrame] = None
        self.d2_df: Optional[pd.DataFrame] = None
        self.descriptor_df: Optional[pd.DataFrame] = None
        self.universe_df: Optional[pd.DataFrame] = None
        self.regimes: Optional[Dict[str, pd.DataFrame]] = None
        self.jid_index: Dict[str, Dict[str, Any]] = {}
        # Phase 5: external materials are kept in a separate in-memory index.
        # They can be resolved and compared against the JARVIS anchor universe
        # without silently polluting the anchor dataframe or its feature statistics.
        self.external_jid_index: Dict[str, Dict[str, Any]] = {}
        self.feature_stats: Dict[str, Dict[str, float]] = {}
        self.known_synthesized_map: Dict[str, Optional[bool]] = load_known_synthesized_map(
            self.config.known_synthesized_path,
            jid_column=self.config.known_synthesized_jid_column,
            status_column=self.config.known_synthesized_status_column,
        )

    def build_universe(self, force_rebuild_descriptor_cache: bool = False) -> pd.DataFrame:
        """Build the unified material universe and associated prepared feature columns."""
        logger.info("Building material universe...")
        self.bulk_df, self.d2_df = load_raw_datasets(self.config)
        logger.info("Building sampling regimes...")
        self.regimes = build_sampling_regimes(self.bulk_df)

        if force_rebuild_descriptor_cache:
            cache_path = Path(self.config.descriptor_cache.path)
            if cache_path.exists():
                cache_path.unlink()

        self.descriptor_df = build_or_load_descriptor_cache(self.bulk_df, self.d2_df, self.config)
        logger.info("Merging descriptor cache into raw datasets...")
        bulk_merged, d2_merged = merge_descriptor_cache(self.bulk_df, self.d2_df, self.descriptor_df)

        logger.info("Preparing feature columns...")
        bulk_merged = ensure_feature_columns(bulk_merged)
        d2_merged = ensure_feature_columns(d2_merged)

        universe = pd.concat([bulk_merged, d2_merged], ignore_index=True)
        universe = universe.drop_duplicates(subset=["jid"]).reset_index(drop=True)
        if self.config.deterministic_sort:
            universe = sort_by_jid(universe)
        universe = apply_known_synthesized_map(universe, self.known_synthesized_map)
        universe["element_set"] = universe.get("element_set", pd.Series([[]] * len(universe))).apply(
            lambda x: x if isinstance(x, list) else []
        )

        self.universe_df = universe
        logger.info("Universe assembled: %s unique materials", len(self.universe_df))
        logger.info("Building JID lookup index...")
        self.jid_index = {str(row["jid"]): row.to_dict() for _, row in self.universe_df.iterrows()}
        if self.external_jid_index:
            self.jid_index.update(self.external_jid_index)
            logger.info("Attached %s registered external materials to JID lookup index.", len(self.external_jid_index))
        logger.info("Computing feature statistics...")
        self.feature_stats = self._compute_feature_stats(self.universe_df)
        if self.config.write_manifests:
            write_json_artifact(self.get_manifest(), Path(self.config.runs_dir) / "material_store_manifest.json")
        logger.info("Material store ready. Feature stats available for %s features.", len(self.feature_stats))
        return self.universe_df

    def ensure_universe(self) -> pd.DataFrame:
        """Return the material universe, building it first when necessary."""
        if self.universe_df is None:
            return self.build_universe()
        return self.universe_df

    def resolve(self, jid: str, strict: bool = True) -> Optional[MaterialRecord]:
        """Resolve a material identifier to a ``MaterialRecord``.
        
        Raises a lookup error when the requested identifier is not present in the
        prepared universe."""
        self.ensure_universe()
        row = self.jid_index.get(str(jid))
        if row is None:
            if strict:
                raise KeyError(f"JID {jid} not found in material universe.")
            return None

        elements = self._extract_elements(row)
        features = {feature: safe_float(row.get(feature)) for feature in ALL_FEATURES}
        n_elements = safe_float(row.get("n_elements"))

        return MaterialRecord(
            jid=str(jid),
            formula=row.get("formula"),
            material_type=row.get("material_type"),
            dataset_kind=row.get("dataset_kind"),
            chemical_system=row.get("chemical_system"),
            reduced_formula=row.get("reduced_formula") or row.get("formula"),
            composition_family=row.get("composition_family") or classify_composition_family(elements),
            n_elements=int(n_elements) if n_elements is not None else None,
            elements=elements,
            features=features,
            raw=row,
        )

    def vector(
        self,
        record: MaterialRecord,
        feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
    ) -> np.ndarray:
        """Return the prepared numerical feature vector for a material identifier."""
        values: List[float] = []
        for feature in feature_names:
            value = record.features.get(feature)
            stats = self.feature_stats.get(feature)
            if value is None or stats is None:
                values.append(np.nan)
            else:
                values.append((float(value) - stats["mean"]) / stats["std"])
        return np.array(values, dtype=float)

    def evaluate_pair_screen(
        self,
        jid_a: str,
        jid_b: str,
        feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
        min_mean_std_delta: float = 0.15,
        min_topk_mean_std_delta: float = 0.25,
        min_max_std_delta: float = 0.30,
        min_feature_count: int = 5,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Evaluate the cheap pair-screening metrics for two material identifiers."""
        left = self.resolve(jid_a)
        right = self.resolve(jid_b)
        return cheap_pair_precheck(
            a=left,
            b=right,
            feature_stats=self.feature_stats,
            feature_names=feature_names,
            min_mean_std_delta=min_mean_std_delta,
            min_topk_mean_std_delta=min_topk_mean_std_delta,
            min_max_std_delta=min_max_std_delta,
            min_feature_count=min_feature_count,
            top_k=top_k,
        )

    def signed_standardized_feature_deltas(
        self,
        jid_a: str,
        jid_b: str,
        feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
    ) -> Dict[str, float]:
        """
        Convenience wrapper returning signed standardized deltas from jid_a to jid_b.

        Positive values mean jid_b is higher than jid_a for that feature. This is
        intended for downstream transformation-template/proposal-engine code.
        """
        left = self.resolve(jid_a)
        right = self.resolve(jid_b)
        return signed_standardized_feature_deltas(
            a=left,
            b=right,
            feature_stats=self.feature_stats,
            feature_names=feature_names,
        )

    def signed_delta_vector(
        self,
        jid_a: str,
        jid_b: str,
        feature_names: Sequence[str] = DEFAULT_SCREENING_FEATURES,
        fill_missing: float = 0.0,
    ) -> np.ndarray:
        """
        Return a dense signed standardized delta vector from jid_a to jid_b.

        The vector follows the order of feature_names. Missing/non-comparable
        features are filled with fill_missing.
        """
        deltas = self.signed_standardized_feature_deltas(
            jid_a=jid_a,
            jid_b=jid_b,
            feature_names=feature_names,
        )
        return np.array([float(deltas.get(feature, fill_missing)) for feature in feature_names], dtype=float)

    def get_feature_groups(self, include_legacy_categories: bool = False) -> Dict[str, List[str]]:
        """Return the interpretation-oriented feature taxonomy."""
        return get_feature_groups(include_legacy_categories=include_legacy_categories)

    def get_interpretation_feature_names(self) -> List[str]:
        """Return recommended feature names for structural contrast interpretation."""
        return get_interpretation_feature_names()

    def get_interpretation_feature_taxonomy(self) -> Dict[str, Any]:
        """Return feature taxonomy metadata for downstream interpretation modules."""
        return get_interpretation_feature_taxonomy()

    def signed_delta_group_summary(
        self,
        jid_a: str,
        jid_b: str,
        feature_names: Optional[Sequence[str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Return group-level summaries of signed standardised deltas from A to B.

        This is additive and does not alter signed_standardized_feature_deltas().
        """
        names = list(feature_names or INTERPRETATION_FEATURES)
        deltas = self.signed_standardized_feature_deltas(jid_a=jid_a, jid_b=jid_b, feature_names=names)
        return group_signed_deltas(deltas)

    def top_signed_delta_features(
        self,
        jid_a: str,
        jid_b: str,
        feature_names: Optional[Sequence[str]] = None,
        top_n: int = 8,
        min_abs_delta: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Return top signed feature changes from A to B with group annotations."""
        names = list(feature_names or INTERPRETATION_FEATURES)
        deltas = self.signed_standardized_feature_deltas(jid_a=jid_a, jid_b=jid_b, feature_names=names)
        return top_signed_delta_features(deltas, top_n=top_n, min_abs_delta=min_abs_delta)

    def get_universe_df(self, include_external: bool = False) -> pd.DataFrame:
        """
        Return the JARVIS anchor universe, optionally with registered external records.

        By default this returns the original anchor universe only. Phase 5 external
        materials are normally query objects, not new anchor rows. Keeping them out
        of the default universe prevents external-vs-itself comparisons and keeps
        feature statistics anchored to JARVIS.
        """
        universe = self.ensure_universe().copy()
        if include_external and self.external_jid_index:
            external_df = pd.DataFrame(list(self.external_jid_index.values()))
            if not external_df.empty:
                universe = pd.concat([universe, external_df], ignore_index=True)
                universe = universe.drop_duplicates(subset=["jid"], keep="first").reset_index(drop=True)
        return universe

    # -------------------------------------------------------------------------
    # Phase 5 external-material registration API
    # -------------------------------------------------------------------------
    def register_external_material(
        self,
        external_record: Mapping[str, Any] | Any,
        *,
        external_id: Optional[str] = None,
        include_in_universe: bool = False,
        overwrite: bool = True,
        recompute_feature_stats: bool = False,
    ) -> MaterialRecord:
        """
        Register a Phase 5 external material for lookup and pair evaluation.

        Parameters
        ----------
        external_record:
            A mapping/dataclass containing either a direct descriptor record
            (for example external_descriptor_record.json) or a payload with a
            top-level ``descriptors`` dictionary (for example an
            ExternalDescriptorReport-like object).
        external_id:
            Optional override for the material identifier. If omitted, the method
            uses external_id, jid, or id from the payload.
        include_in_universe:
            If True, append the external row to ``universe_df``. The default is
            False because external materials should normally act as query objects
            screened against the JARVIS anchor universe, not as new anchor rows.
        overwrite:
            If False, raise when the external ID is already registered.
        recompute_feature_stats:
            If True and include_in_universe is True, recompute feature statistics
            after appending the row. The default keeps statistics anchored to the
            original JARVIS universe, which is the intended Phase 5 MVP behaviour.

        Returns
        -------
        MaterialRecord
            The registered external material as resolved by the normal MaterialStore
            record API.
        """

        self.ensure_universe()
        row = self._normalise_external_material_row(external_record, external_id=external_id)
        jid = str(row["jid"])

        if jid in self.external_jid_index and not overwrite:
            raise ValueError(f"External material {jid} is already registered.")
        if jid in self.jid_index and jid not in self.external_jid_index and not overwrite:
            raise ValueError(f"Material ID {jid} already exists in the anchor universe.")

        self.external_jid_index[jid] = row
        self.jid_index[jid] = row

        if include_in_universe:
            external_df = pd.DataFrame([row])
            external_df = ensure_feature_columns(external_df)
            if self.universe_df is None:
                self.universe_df = external_df
            else:
                anchor = self.universe_df[self.universe_df["jid"].astype(str) != jid].copy()
                self.universe_df = pd.concat([anchor, external_df], ignore_index=True).reset_index(drop=True)
            if recompute_feature_stats:
                self.feature_stats = self._compute_feature_stats(self.universe_df)

        logger.info(
            "Registered external material %s (include_in_universe=%s).",
            jid,
            include_in_universe,
        )
        return self.resolve(jid, strict=True)

    def register_external_material_from_json(
        self,
        path: str | Path,
        *,
        external_id: Optional[str] = None,
        include_in_universe: bool = False,
        overwrite: bool = True,
        recompute_feature_stats: bool = False,
    ) -> MaterialRecord:
        """Register one external material from a JSON descriptor/profile/report file."""

        json_path = Path(path)
        with json_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return self.register_external_material(
            payload,
            external_id=external_id,
            include_in_universe=include_in_universe,
            overwrite=overwrite,
            recompute_feature_stats=recompute_feature_stats,
        )

    def register_external_materials_from_json(
        self,
        paths: Sequence[str | Path],
        *,
        include_in_universe: bool = False,
        overwrite: bool = True,
        recompute_feature_stats: bool = False,
    ) -> List[MaterialRecord]:
        """Register multiple external materials from JSON files."""

        records: List[MaterialRecord] = []
        for path in paths:
            records.append(
                self.register_external_material_from_json(
                    path,
                    include_in_universe=include_in_universe,
                    overwrite=overwrite,
                    recompute_feature_stats=False,
                )
            )
        if include_in_universe and recompute_feature_stats and self.universe_df is not None:
            self.feature_stats = self._compute_feature_stats(self.universe_df)
        return records

    def resolve_external_material(self, external_id: str, strict: bool = True) -> Optional[MaterialRecord]:
        """Resolve a registered external material by ID."""

        if str(external_id) not in self.external_jid_index:
            if strict:
                raise KeyError(f"External material {external_id} is not registered.")
            return None
        return self.resolve(str(external_id), strict=strict)

    def is_external_material(self, jid: str) -> bool:
        """Return True when a material ID belongs to the registered external index."""

        return str(jid) in self.external_jid_index

    def get_external_material_ids(self) -> List[str]:
        """Return registered external material IDs in deterministic order."""

        return sorted(self.external_jid_index.keys())

    def get_external_material_records(self) -> Dict[str, Dict[str, Any]]:
        """Return a copy of registered external rows."""

        return {jid: dict(row) for jid, row in self.external_jid_index.items()}

    def remove_external_material(self, external_id: str, *, remove_from_universe: bool = True) -> bool:
        """Remove a registered external material from lookup, and optionally universe_df."""

        jid = str(external_id)
        existed = jid in self.external_jid_index
        self.external_jid_index.pop(jid, None)
        if self.jid_index.get(jid, {}).get("is_external_material"):
            self.jid_index.pop(jid, None)
        if remove_from_universe and self.universe_df is not None and "jid" in self.universe_df.columns:
            self.universe_df = self.universe_df[self.universe_df["jid"].astype(str) != jid].reset_index(drop=True)
        return existed

    def validate_external_record(self, external_record: Mapping[str, Any] | Any) -> Dict[str, Any]:
        """
        Validate whether a Phase 5 external descriptor payload can be registered.

        This is deliberately lightweight. Detailed parse/descriptor validation belongs
        in external_material_validator.py; this method only checks the MaterialStore
        contract needed for resolve(), vector(), and pair screening.
        """

        row = self._normalise_external_material_row(external_record)
        missing_required = [field for field in DESCRIPTOR_REQUIRED_COLUMNS if row.get(field) is None]
        missing_features = [feature for feature in ALL_FEATURES if safe_float(row.get(feature)) is None]
        usable_features = [feature for feature in ALL_FEATURES if safe_float(row.get(feature)) is not None]
        return {
            "schema_version": EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION,
            "external_id": row.get("jid"),
            "can_register": bool(row.get("jid")) and bool(row.get("formula")),
            "missing_required_descriptor_fields": sorted(missing_required),
            "missing_lrt_feature_fields": sorted(missing_features),
            "usable_lrt_feature_count": int(len(usable_features)),
            "total_lrt_feature_count": int(len(ALL_FEATURES)),
        }

    def _normalise_external_material_row(
        self,
        external_record: Mapping[str, Any] | Any,
        *,
        external_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert Phase 5 payload variants into a MaterialStore row dictionary."""

        if is_dataclass(external_record):
            payload: Dict[str, Any] = asdict(external_record)
        elif hasattr(external_record, "to_dict"):
            payload = dict(external_record.to_dict())
        elif isinstance(external_record, Mapping):
            payload = dict(external_record)
        else:
            raise TypeError("external_record must be a mapping, dataclass, or object with to_dict().")

        descriptors = payload.get("descriptors")
        if isinstance(descriptors, Mapping):
            row = dict(descriptors)
            for key in (
                "external_id",
                "source_file",
                "source_format",
                "external_source_file",
                "external_source_format",
                "schema_version",
            ):
                if key in payload and key not in row:
                    row[key] = payload[key]
        else:
            row = dict(payload)

        jid = external_id or row.get("external_id") or row.get("jid") or row.get("id")
        if not jid:
            raise ValueError("External material payload must contain external_id, jid, or id.")
        jid = str(jid)

        row["jid"] = jid
        row["external_id"] = row.get("external_id") or jid
        row["formula"] = row.get("formula") or row.get("reduced_formula")
        if not row.get("formula"):
            raise ValueError(f"External material {jid} must contain formula or reduced_formula.")

        row["material_type"] = row.get("material_type") or "external"
        row["dataset_kind"] = row.get("dataset_kind") or "external_structure"
        row["is_external_material"] = True
        row["external_registration_schema_version"] = EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION

        if "external_source_file" not in row:
            row["external_source_file"] = row.get("source_file")
        if "external_source_format" not in row:
            row["external_source_format"] = row.get("source_format")

        if not isinstance(row.get("element_set"), list):
            if isinstance(row.get("elements"), list):
                row["element_set"] = [str(x) for x in row.get("elements", [])]
            else:
                row["element_set"] = get_element_set_from_formula(str(row.get("formula")))

        reachability = composition_reachability_features(str(row.get("formula")))
        for key, value in reachability.items():
            row.setdefault(key, value)
        if not row.get("composition_family"):
            row["composition_family"] = classify_composition_family(row.get("element_set", []))

        for field_name in DESCRIPTOR_REQUIRED_COLUMNS:
            row.setdefault(field_name, None)
        for feature in ALL_FEATURES:
            row.setdefault(feature, None)
        for field_name in PHYSICAL_PLAUSIBILITY_FIELDS:
            row.setdefault(field_name, None)
        row.setdefault("formation_energy_peratom", row.get("formation_energy"))
        row.setdefault("optb88vdw_bandgap", row.get("band_gap"))
        row.setdefault("density", row.get("density_feature"))
        row.setdefault("exfoliation_energy", row.get("exfoliation_energy_feature"))

        single = ensure_feature_columns(pd.DataFrame([row])).iloc[0].to_dict()
        single["jid"] = jid
        single["external_id"] = row.get("external_id") or jid
        single["is_external_material"] = True
        single["external_registration_schema_version"] = EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION
        single["element_set"] = row.get("element_set") if isinstance(row.get("element_set"), list) else []
        single["dataset_kind"] = row.get("dataset_kind") or "external_structure"
        single["material_type"] = row.get("material_type") or "external"
        single["external_source_file"] = row.get("external_source_file")
        single["external_source_format"] = row.get("external_source_format")
        return single

    def get_physical_properties(self, jid: str) -> Dict[str, Any]:
        """
        Return Phase 2 physical plausibility inputs for one material.

        This convenience API is for physical_plausibility.py and reporting layers.
        It intentionally returns raw annotation fields only; it does not classify,
        score, or rank.
        """

        self.ensure_universe()
        row = self.jid_index.get(str(jid))
        if row is None:
            raise KeyError(f"JID {jid} not found in material universe.")
        return {
            "jid": str(jid),
            "formula": row.get("formula"),
            "formation_energy": safe_float(row.get("formation_energy")),
            "formation_energy_peratom": safe_float(row.get("formation_energy_peratom")),
            "energy_above_hull": safe_float(row.get("energy_above_hull")),
            "known_synthesized": coerce_optional_bool(row.get("known_synthesized")),
            "dataset_kind": row.get("dataset_kind"),
            "material_type": row.get("material_type"),
        }

    def build_phase1_material_profile_row(self, jid: str) -> Dict[str, Any]:
        """Return a flat, cheap Phase 1 profile row for a resolved material.

        This helper deliberately performs no role scoring and no retrieval. It simply
        exposes identity, chemistry, symmetry, physical plausibility inputs, and
        cached cheap descriptor fields in one dictionary so profile/reporting layers
        do not need to know the internals of MaterialRecord.
        """

        record = self.resolve(jid, strict=True)
        row = dict(record.raw or {})
        out: Dict[str, Any] = {
            "jid": record.jid,
            "formula": record.formula,
            "reduced_formula": record.reduced_formula,
            "material_type": record.material_type,
            "dataset_kind": record.dataset_kind,
            "chemical_system": record.chemical_system,
            "composition_family": record.composition_family,
            "n_elements": record.n_elements,
            "elements": list(record.elements or []),
            "is_external_material": bool(row.get("is_external_material", False)),
            "external_id": row.get("external_id"),
            "external_source_file": row.get("external_source_file"),
            "external_source_format": row.get("external_source_format"),
            # Phase 1 cheap structural-context metadata. These are intentionally
            # best-effort: many JARVIS rows will not carry prototype labels, but
            # exposing nulls here keeps the downstream profile schema stable.
            "formula_anonymous": row.get("formula_anonymous") or row.get("anonymous_formula"),
            "prototype": row.get("prototype") or row.get("structure_type") or row.get("strukturbericht"),
            "prototype_family": row.get("prototype_family") or row.get("structure_family"),
            "material_family": row.get("material_family") or row.get("family") or row.get("composition_family"),
            "spacegroup_number": safe_float(row.get("spacegroup_number")),
            "spacegroup_symbol": row.get("spacegroup_symbol") or row.get("spg_symbol"),
            "crystal_system_code": safe_float(row.get("crystal_system_code")),
            "n_symmetry_ops": safe_float(row.get("n_symmetry_ops")),
            "is_centrosymmetric": coerce_optional_bool(row.get("is_centrosymmetric")),
            "formation_energy": safe_float(row.get("formation_energy")),
            "formation_energy_peratom": safe_float(row.get("formation_energy_peratom")),
            "energy_above_hull": safe_float(row.get("energy_above_hull")),
            "known_synthesized": coerce_optional_bool(row.get("known_synthesized")),
        }
        for feature in ALL_FEATURES:
            out[feature] = safe_float(record.features.get(feature))
        return out

    def get_known_synthesized_map(self) -> Dict[str, Optional[bool]]:
        """Return the loaded external known-synthesized map, if any."""

        return dict(self.known_synthesized_map)

    def get_manifest(self) -> Dict[str, Any]:
        """Return run-stable material-store provenance metadata."""

        manifest = material_store_manifest(self.config, self.universe_df)
        manifest["external_material_schema_version"] = EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION
        manifest["registered_external_material_count"] = int(len(self.external_jid_index))
        manifest["registered_external_material_ids"] = self.get_external_material_ids()
        return manifest

    def write_manifest(self, path: str | Path) -> None:
        """Write material-store provenance metadata to JSON."""

        write_json_artifact(self.get_manifest(), path)

    def sample_run_pool(
        self,
        run_id: int,
        seed: int,
        allow_replacement_when_small: bool = False,
    ) -> pd.DataFrame:
        """
        Default run sampler reused from discovery:
        - 40 bulk metals
        - 40 bulk semiconductors
        - 40 layered bulk
        - 100 2D materials

        Duplicates are removed by jid afterwards, because regime buckets overlap
        and nature apparently refuses to cooperate with neat category borders.
        """
        self.ensure_universe()
        assert self.bulk_df is not None
        assert self.d2_df is not None
        assert self.regimes is not None

        rng = np.random.RandomState(seed)

        parts = [
            self._sample_frame(
                self.regimes["bulk_metals"],
                self.config.sampling.bulk_metal_sample,
                rng,
                allow_replacement_when_small,
            ),
            self._sample_frame(
                self.regimes["bulk_semis"],
                self.config.sampling.bulk_semi_sample,
                rng,
                allow_replacement_when_small,
            ),
            self._sample_frame(
                self.regimes["layered_bulk"],
                self.config.sampling.layered_bulk_sample,
                rng,
                allow_replacement_when_small,
            ),
            self._sample_frame(
                self.d2_df,
                self.config.sampling.d2_sample_size,
                rng,
                allow_replacement_when_small,
            ),
        ]

        pool = pd.concat(parts, ignore_index=True)
        pool = pool.drop_duplicates(subset=["jid"]).reset_index(drop=True)
        if self.config.deterministic_sort:
            pool = sort_by_jid(pool)
        pool = ensure_feature_columns(pool)
        pool = apply_known_synthesized_map(pool, self.known_synthesized_map)
        pool["run_id"] = run_id
        pool["run_seed"] = seed
        return pool

    def build_run_feature_context(
        self,
        run_id: int,
        seed: int,
        pool_df: Optional[pd.DataFrame] = None,
        feature_names: Optional[Sequence[str]] = None,
    ) -> RunFeatureContext:
        """Build a standardised feature context for a selected run-level cohort."""
        pool = pool_df.copy() if pool_df is not None else self.sample_run_pool(run_id=run_id, seed=seed)
        features = list(feature_names or ALL_FEATURES)
        pool = ensure_feature_columns(pool)
        X_raw, X_scaled, scaler, feature_scale = build_feature_matrix(pool, features)
        return RunFeatureContext(
            run_id=run_id,
            seed=seed,
            pool_df=pool,
            feature_names=features,
            X_raw=X_raw,
            X_scaled=X_scaled,
            scaler=scaler,
            feature_scale=feature_scale,
        )

    @staticmethod
    def _sample_frame(
        df: pd.DataFrame,
        n: int,
        rng: np.random.RandomState,
        allow_replacement_when_small: bool,
    ) -> pd.DataFrame:
        """Return a deterministic sample from a dataframe using store configuration."""
        if df.empty:
            raise ValueError("Cannot sample from an empty frame.")
        replace = allow_replacement_when_small and len(df) < n
        n_effective = n if replace else min(n, len(df))
        indices = rng.choice(df.index.values, size=n_effective, replace=replace)
        return df.loc[indices].copy().reset_index(drop=True)

    @staticmethod
    def _extract_elements(row: Dict[str, Any]) -> List[str]:
        """Extract normalised element symbols from a material row."""
        if isinstance(row.get("element_set"), list):
            return [str(x) for x in row["element_set"]]
        if isinstance(row.get("elements"), list):
            return [str(x) for x in row["elements"]]
        formula = row.get("formula")
        if isinstance(formula, str):
            try:
                return [el.symbol for el in Composition(formula).elements]
            except Exception:
                return []
        return []

    @staticmethod
    def _compute_feature_stats(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Compute summary statistics used to standardise configured features."""
        stats: Dict[str, Dict[str, float]] = {}
        for feature in ALL_FEATURES:
            if feature not in df.columns:
                continue
            vals = pd.to_numeric(df[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            if vals.empty:
                continue
            mean = float(vals.mean())
            std = float(vals.std(ddof=0))
            if std <= 1e-12:
                std = 1.0
            stats[feature] = {"mean": mean, "std": std}
        return stats


# =============================================================================
# Convenience constructor
# =============================================================================
def build_material_store(
    config: Optional[MaterialStoreConfig] = None,
    force_rebuild_descriptor_cache: bool = False,
    log_file: Optional[str | Path] = None,
) -> MaterialStore:
    """Construct and initialise a ``MaterialStore`` from configuration.
    
    This is the preferred convenience entry point for downstream modules that need
    a ready-to-use unified material universe."""
    configure_material_store_logging(log_file=log_file)
    logger.info("Initialising MaterialStore...")
    store = MaterialStore(config=config)
    store.build_universe(force_rebuild_descriptor_cache=force_rebuild_descriptor_cache)
    return store


__all__ = [
    "MATERIAL_STORE_SCHEMA_VERSION",
    "DESCRIPTOR_CACHE_SCHEMA_VERSION",
    "EXTERNAL_MATERIAL_STORE_SCHEMA_VERSION",
    "SamplingConfig",
    "DescriptorCacheConfig",
    "MaterialStoreConfig",
    "MaterialRecord",
    "RunFeatureContext",
    "configure_material_store_logging",
    "validate_material_store_config",
    "material_store_manifest",
    "descriptor_cache_manifest",
    "write_json_artifact",
    "sort_by_jid",
    "build_material_store",
    "MaterialStore",
    "ALL_FEATURES",
    "DEFAULT_SCREENING_FEATURES",
    "PHYSICAL_PLAUSIBILITY_FIELDS",
    "get_feature_groups",
    "get_interpretation_feature_names",
    "get_interpretation_feature_taxonomy",
]


if __name__ == "__main__":
    store = build_material_store()
    universe = store.get_universe_df()
    print("Material universe built")
    print(f"Universe size: {len(universe)}")
    print(f"Interpretation feature groups: {list(get_feature_groups().keys())}")
