from __future__ import annotations

"""
material_profile_builder.py

Phase 1 Material Profile Builder

Overview
--------
This module constructs the canonical Phase 1 query profile used throughout the
structural-context pipeline. It converts either a JARVIS material or an
externally supplied material description into a normalised, reproducible
profile that downstream components can consume without requiring further
knowledge of the original source.

Responsibilities
----------------
* Resolve material identity.
* Build a consistent descriptor profile.
* Apply inexpensive feature engineering.
* Attach optional family classification.
* Attach optional physical plausibility annotations.
* Write a versioned query_profile.json for downstream processing.

Architectural role
------------------
This module intentionally performs no retrieval, clustering, role assignment,
or expensive simulation. It acts as the interface between raw material data
and the remainder of the Phase 1 pipeline.

Maintenance guidance
--------------------
Future enhancements should preserve backwards compatibility with the generated
profile schema where practical. New fields should be deterministic, documented
and inexpensive to calculate. Behaviour affecting downstream modules should be
introduced cautiously and accompanied by schema version updates where required.
"""


import argparse
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# MaterialStore is imported lazily inside build_query_profile() so --help works even
# in environments where jarvis/pymatgen are not installed.
ALL_FEATURES: List[str] = []
DEFAULT_SCREENING_FEATURES: List[str] = []
FEATURE_CATEGORIES: Dict[str, List[str]] = {}
FEATURE_GROUPS: Dict[str, List[str]] = {}

try:
    from physical_plausibility import PhysicalPlausibilityAnnotator, PhysicalPlausibilityConfig
except Exception:  # pragma: no cover - physical plausibility is useful but not fatal
    PhysicalPlausibilityAnnotator = None  # type: ignore
    PhysicalPlausibilityConfig = None  # type: ignore

try:
    from material_family_classifier import classify_material_family, flatten_family_classification
except Exception:  # pragma: no cover - family classification should not break --help
    classify_material_family = None  # type: ignore
    flatten_family_classification = None  # type: ignore

PROFILE_SCHEMA_VERSION = "phase1.material_profile.v1.2"

IDENTITY_FIELDS: Tuple[str, ...] = (
    "jid",
    "formula",
    "reduced_formula",
    "material_type",
    "dataset_kind",
    "is_external_material",
    "external_id",
    "external_source_file",
    "external_source_format",
)

COMPOSITION_FIELDS: Tuple[str, ...] = (
    "elements",
    "n_elements",
    "chemical_system",
    "composition_family",
    "metal_count",
    "nonmetal_count",
    "mean_electronegativity",
    "electronegativity_range",
    "atomic_radius_mean",
    "valence_electrons_mean",
)

SYMMETRY_FIELDS: Tuple[str, ...] = (
    "spacegroup_number",
    "spacegroup_symbol",
    "crystal_system_code",
    "n_symmetry_ops",
    "is_centrosymmetric",
)

PHYSICAL_FIELDS: Tuple[str, ...] = (
    "formation_energy",
    "formation_energy_peratom",
    "energy_above_hull",
    "known_synthesized",
    "band_gap",
    "density_feature",
    "exfoliation_energy_feature",
    "volume_per_atom",
)

FAMILY_FIELDS: Tuple[str, ...] = (
    "formula_anonymous",
    "formula_family",
    "prototype",
    "prototype_family",
    "structure_variant",
    "material_family",
    "family_classification_confidence",
)

DIMENSIONAL_FIELDS: Tuple[str, ...] = (
    "a_axis",
    "b_axis",
    "c_axis_cached",
    "c_over_a",
    "c_over_b",
    "max_axis_over_min_axis",
    "frac_z_span",
    "cart_z_span_over_c",
)

COORDINATION_FIELDS: Tuple[str, ...] = (
    "coord_mean",
    "coord_std",
    "coord_min",
    "coord_max",
    "frac_low_coord_sites",
    "frac_high_coord_sites",
)

BONDING_FIELDS: Tuple[str, ...] = (
    "bond_mean_en_diff",
    "bond_std_en_diff",
    "bond_max_en_diff",
    "bond_length_mean",
    "bond_length_std",
    "bond_length_range",
    "frac_short_bonds",
    "ionicity_proxy_comp",
)


def _json_safe(value: Any) -> Any:
    """Convert common numpy/pandas/dataclass values into JSON-safe objects."""
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    # numpy scalar compatibility without importing numpy directly.
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _pick(row: Mapping[str, Any], fields: Sequence[str]) -> Dict[str, Any]:
    return {field: _json_safe(row.get(field)) for field in fields if field in row}


def _missing_fields(payload: Mapping[str, Any], fields: Sequence[str]) -> List[str]:
    missing: List[str] = []
    for field in fields:
        value = payload.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)
    return missing


def _is_present(value: Any) -> bool:
    return value is not None and value != "" and value != []


def _feature_completeness(row: Mapping[str, Any], fields: Sequence[str]) -> Dict[str, Any]:
    values = {field: row.get(field) for field in fields}
    available = [k for k, v in values.items() if _is_present(v)]
    return {
        "available_count": len(available),
        "total_count": len(fields),
        "completeness": (len(available) / len(fields)) if fields else 0.0,
        "available_fields": available,
        "missing_fields": [k for k in fields if k not in available],
    }


def _compact(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop empty keys from a user-facing section while keeping zeros/False."""
    return {str(k): _json_safe(v) for k, v in payload.items() if _is_present(v)}


def _first_present(row: Mapping[str, Any], fields: Sequence[str]) -> Any:
    for field in fields:
        value = row.get(field)
        if _is_present(value):
            return _json_safe(value)
    return None


def _annotation_to_dict(annotation: Any) -> Dict[str, Any]:
    if annotation is None:
        return {
            "available": False,
            "label": "not_run",
            "score": None,
            "flags": ["physical_plausibility_module_unavailable"],
            "evidence": [],
            "data_completeness": 0.0,
        }
    if hasattr(annotation, "to_dict"):
        return _json_safe(annotation.to_dict())
    if is_dataclass(annotation):
        return _json_safe(asdict(annotation))
    if isinstance(annotation, Mapping):
        return _json_safe(annotation)
    return {"available": True, "raw": str(annotation)}


def _load_material_store_symbols() -> Dict[str, Any]:
    """Import material_store lazily and publish the feature lists used by this module."""
    global ALL_FEATURES, DEFAULT_SCREENING_FEATURES, FEATURE_CATEGORIES, FEATURE_GROUPS
    try:
        import material_store as ms
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Could not import material_store.py. Put material_profile_builder.py in the same "
            "folder as the patched material_store.py and ensure jarvis/pymatgen are installed."
        ) from exc
    ALL_FEATURES = list(getattr(ms, "ALL_FEATURES", []))
    DEFAULT_SCREENING_FEATURES = list(getattr(ms, "DEFAULT_SCREENING_FEATURES", []))
    FEATURE_CATEGORIES = dict(getattr(ms, "FEATURE_CATEGORIES", {}))
    FEATURE_GROUPS = dict(getattr(ms, "FEATURE_GROUPS", {}))
    return {
        "build_material_store": ms.build_material_store,
        "safe_float": getattr(ms, "safe_float", float),
    }


def build_query_profile(
    *,
    jid: Optional[str] = None,
    external_json: Optional[str | Path] = None,
    external_id: Optional[str] = None,
    include_external_in_universe: bool = False,
    force_rebuild_descriptor_cache: bool = False,
) -> Dict[str, Any]:
    """Build a Phase 1 material profile for a JARVIS or external material."""
    if bool(jid) == bool(external_json):
        raise ValueError("Supply exactly one of --jid or --external_json.")

    ms_symbols = _load_material_store_symbols()
    build_material_store = ms_symbols["build_material_store"]
    store = build_material_store(force_rebuild_descriptor_cache=force_rebuild_descriptor_cache)

    source: Dict[str, Any]
    if external_json:
        record = store.register_external_material_from_json(
            external_json,
            external_id=external_id,
            include_in_universe=include_external_in_universe,
            overwrite=True,
            recompute_feature_stats=False,
        )
        resolved_jid = record.jid
        source = {
            "input_type": "external_json",
            "input_path": str(external_json),
            "external_id": external_id or record.jid,
            "include_external_in_universe": bool(include_external_in_universe),
        }
    else:
        resolved_jid = str(jid)
        record = store.resolve(resolved_jid, strict=True)
        source = {"input_type": "jarvis_jid", "jid": resolved_jid}

    # Prefer the patched material-store helper; fall back to record fields if an older store is used.
    if hasattr(store, "build_phase1_material_profile_row"):
        row = store.build_phase1_material_profile_row(resolved_jid)
    else:  # pragma: no cover
        row = dict(record.raw or {})
        row.update({
            "jid": record.jid,
            "formula": record.formula,
            "reduced_formula": record.reduced_formula,
            "material_type": record.material_type,
            "dataset_kind": record.dataset_kind,
            "chemical_system": record.chemical_system,
            "composition_family": record.composition_family,
            "n_elements": record.n_elements,
            "elements": record.elements,
            **{f: record.features.get(f) for f in ALL_FEATURES},
        })

    # Phase 1.2: cheap rule-based family/prototype classification.
    # This is evidence, not ground truth. It upgrades broad labels like "oxide"
    # into more useful candidates such as "ABO3" / "perovskite_like" where
    # cheap formula + symmetry rules support it.
    if classify_material_family is not None and flatten_family_classification is not None:
        family_classification = classify_material_family(row)
        row.update(_compact(flatten_family_classification(family_classification)))
    else:  # pragma: no cover
        family_classification = {
            "schema_version": "phase1.material_family_classifier.unavailable",
            "material_family": row.get("material_family") or row.get("composition_family"),
            "formula_family": row.get("formula_anonymous"),
            "prototype": row.get("prototype"),
            "prototype_family": row.get("prototype_family"),
            "structure_variant": None,
            "confidence": 0.0,
            "evidence": [],
            "warnings": ["material_family_classifier_import_failed"],
        }

    physical_annotation: Dict[str, Any]
    if PhysicalPlausibilityAnnotator is not None:
        annotator = PhysicalPlausibilityAnnotator.from_material_store(store)
        physical_annotation = _annotation_to_dict(annotator.annotate_material(resolved_jid, material=row))
    else:
        physical_annotation = _annotation_to_dict(None)

    cheap_descriptor_fields = list(dict.fromkeys(
        list(COMPOSITION_FIELDS)
        + list(FAMILY_FIELDS)
        + list(SYMMETRY_FIELDS)
        + list(PHYSICAL_FIELDS)
        + list(DIMENSIONAL_FIELDS)
        + list(COORDINATION_FIELDS)
        + list(BONDING_FIELDS)
    ))

    identity = _compact(_pick(row, IDENTITY_FIELDS))
    composition = _compact(_pick(row, COMPOSITION_FIELDS))
    structural_metadata = _compact({
        **_pick(row, FAMILY_FIELDS),
        **_pick(row, SYMMETRY_FIELDS),
    })
    physical = _compact(_pick(row, PHYSICAL_FIELDS))
    descriptor_groups = {
        "composition": _compact(_pick(row, COMPOSITION_FIELDS)),
        "family": _compact(_pick(row, FAMILY_FIELDS)),
        "symmetry": _compact(_pick(row, SYMMETRY_FIELDS)),
        "physical_proxy": _compact(_pick(row, PHYSICAL_FIELDS)),
        "dimensional": _compact(_pick(row, DIMENSIONAL_FIELDS)),
        "coordination": _compact(_pick(row, COORDINATION_FIELDS)),
        "bonding": _compact(_pick(row, BONDING_FIELDS)),
    }

    role_inputs = {
        "hub": {
            "composition_family": row.get("composition_family"),
            "material_family": row.get("material_family"),
            "formula_family": row.get("formula_family"),
            "prototype_family": row.get("prototype_family"),
            "structure_variant": row.get("structure_variant"),
            "family_classification_confidence": row.get("family_classification_confidence"),
            "chemical_system": row.get("chemical_system"),
            "spacegroup_number": row.get("spacegroup_number"),
            "energy_above_hull": row.get("energy_above_hull"),
            "known_synthesized": row.get("known_synthesized"),
        },
        "bridge": {
            "composition_family": row.get("composition_family"),
            "material_family": row.get("material_family"),
            "formula_family": row.get("formula_family"),
            "prototype_family": row.get("prototype_family"),
            "structure_variant": row.get("structure_variant"),
            "family_classification_confidence": row.get("family_classification_confidence"),
            "chemical_system": row.get("chemical_system"),
            "n_elements": row.get("n_elements"),
            "electronegativity_range": row.get("electronegativity_range"),
            "volume_per_atom": row.get("volume_per_atom"),
        },
        "boundary": {
            "formula_family": row.get("formula_family"),
            "prototype_family": row.get("prototype_family"),
            "structure_variant": row.get("structure_variant"),
            "family_classification_confidence": row.get("family_classification_confidence"),
            "spacegroup_number": row.get("spacegroup_number"),
            "spacegroup_symbol": row.get("spacegroup_symbol"),
            "crystal_system_code": row.get("crystal_system_code"),
            "n_symmetry_ops": row.get("n_symmetry_ops"),
            "c_over_a": row.get("c_over_a"),
            "c_over_b": row.get("c_over_b"),
            "max_axis_over_min_axis": row.get("max_axis_over_min_axis"),
            "coord_std": row.get("coord_std"),
            "energy_above_hull": row.get("energy_above_hull"),
        },
        "outlier": {
            "composition_family": row.get("composition_family"),
            "material_family": row.get("material_family"),
            "formula_family": row.get("formula_family"),
            "prototype_family": row.get("prototype_family"),
            "structure_variant": row.get("structure_variant"),
            "family_classification_confidence": row.get("family_classification_confidence"),
            "chemical_system": row.get("chemical_system"),
            "n_elements": row.get("n_elements"),
            "spacegroup_number": row.get("spacegroup_number"),
            "energy_above_hull": row.get("energy_above_hull"),
        },
    }
    role_inputs = {k: _compact(v) for k, v in role_inputs.items()}

    candidate_pool_inputs = {
        "family_key": _first_present(row, ["prototype_family", "material_family", "composition_family"]),
        "material_family_key": row.get("material_family"),
        "formula_family_key": row.get("formula_family"),
        "structure_variant_key": row.get("structure_variant"),
        "chemical_key": row.get("chemical_system"),
        "composition_key": row.get("composition_family"),
        "prototype_key": _first_present(row, ["prototype", "prototype_family", "formula_family", "formula_anonymous"]),
        "symmetry_key": row.get("spacegroup_number"),
        "stability_key": "stable_or_known" if (row.get("energy_above_hull") == 0 or row.get("known_synthesized") is True) else None,
    }

    profile: Dict[str, Any] = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "metadata": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "profile_stage": "phase1",
            "profile_scope": "cheap_material_context_only",
            "local_structure_ranking_run": False,
            "role_prior_scoring_run": False,
            "dft_run": False,
            "property_prediction_run": False,
        },
        "source": source,
        "identity": identity,
        "composition": composition,
        "structural_metadata": structural_metadata,
        "family_classification": _json_safe(family_classification),
        "physical": {
            "inputs": physical,
            "plausibility": physical_annotation,
        },
        "descriptor_groups": descriptor_groups,
        "role_inputs": role_inputs,
        "candidate_pool_inputs": _compact(candidate_pool_inputs),
        "graph_context": {
            "degree_centrality": None,
            "betweenness_centrality": None,
            "community_id": None,
            "community_label": None,
            "distance_to_family_centroid": None,
            "isolation_score": None,
            "status": "not_computed_phase1",
        },
        "role_priors": {
            "hub": None,
            "bridge": None,
            "boundary": None,
            "outlier": None,
            "status": "not_computed_phase1",
        },
        "validation": {
            "validation_case": False,
            "expected_primary_role": None,
            "expected_secondary_roles": [],
            "expected_role_confidence": None,
            "literature_basis": None,
            "negative_control": False,
        },
        "diagnostics": {
            "feature_completeness": {
                "cheap_descriptors": _feature_completeness(row, cheap_descriptor_fields),
                "all_lsf_features": _feature_completeness(row, ALL_FEATURES),
                "default_screening_features": _feature_completeness(row, DEFAULT_SCREENING_FEATURES),
            },
            "missing_core_fields": _missing_fields(row, ["jid", "formula", "elements", "chemical_system", "composition_family"]),
            "missing_recommended_fields": _missing_fields(row, ["spacegroup_number", "energy_above_hull", "formation_energy", "known_synthesized"]),
            "notes": [
                "Phase 1 profile only: no retrieval, role-prior scoring, local-structure ranking, DFT, or property prediction has been run.",
                "External materials are registered as query objects by default and are not added to the JARVIS anchor universe unless requested.",
                "Null graph_context and role_priors fields are schema placeholders for later phases.",
                "Family classification is cheap rule-based evidence, not crystallographic ground truth.",
            ],
        },
        "compatibility": {
            "legacy_cheap_descriptors": _pick(row, cheap_descriptor_fields),
            "legacy_physical_inputs": physical,
        },
    }
    return _json_safe(profile)


def write_profile(profile: Mapping[str, Any], output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "query_profile.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(_json_safe(profile), f, indent=2, sort_keys=True)
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a Phase 1 cheap material profile JSON.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jid", help="JARVIS material ID, e.g. JVASP-20955")
    source.add_argument("--external_json", help="External descriptor/profile/report JSON to register and profile")
    parser.add_argument("--external_id", help="Optional override ID for external material")
    parser.add_argument("--include_external_in_universe", action="store_true", help="Append external material to universe_df. Usually not needed for Phase 1.")
    parser.add_argument("--force_rebuild_descriptor_cache", action="store_true", help="Force rebuilding descriptor cache. Usually leave off unless cache is stale.")
    parser.add_argument("--output_dir", required=True, help="Folder where query_profile.json will be written")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    profile = build_query_profile(
        jid=args.jid,
        external_json=args.external_json,
        external_id=args.external_id,
        include_external_in_universe=args.include_external_in_universe,
        force_rebuild_descriptor_cache=args.force_rebuild_descriptor_cache,
    )
    out_path = write_profile(profile, args.output_dir)
    print(f"Wrote Phase 1 query profile: {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
