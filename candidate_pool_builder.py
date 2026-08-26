"""
Candidate pool construction utilities.

Overview
--------
Builds deterministic candidate pools used by the Cheap Context First workflow.
The builder assembles structurally and chemically relevant comparison sets for a
query material while remaining computationally inexpensive.

Responsibilities
----------------
* Construct reproducible candidate pools.
* Preserve separation between evidence generation and role inference.
* Provide consistent inputs to downstream evidence and role analysis.
* Support both internal JARVIS materials and external material profiles.

Architectural role
------------------
This module sits between profile generation and evidence extraction. It is
responsible only for selecting suitable comparison candidates and must not
perform scoring, role assignment or physical-plausibility decisions.

Developer notes
---------------
Selection heuristics should remain deterministic where possible. Any future
extensions should preserve backwards compatibility with the profile schema and
avoid introducing expensive computations into the Phase 1 pipeline.
"""

from __future__ import annotations

"""
candidate_pool_builder.py

Phase 2 candidate pool builder for the LSF / structural-context project.

Purpose
-------
Build deterministic, configurable candidate pools for a query material profile
without running local-structure retrieval, DFT, role priors, or property prediction.

Inputs
------
- query_profile.json produced by material_profile_builder.py schema v1.1 or v1.2
- material_store.py in the same working folder, or importable on PYTHONPATH

Outputs
-------
output_dir/
  candidate_pool_summary.json
  pool_config_used.json
  same_family_pool.csv
  adjacent_family_pool.csv
  boundary_contrast_pool.csv
  wildcard_pool.csv
  negative_control_pool.csv

Phase 2 v1.1 adds optional formula/prototype/structure-variant family fields.

Typical usage
-------------
python3 candidate_pool_builder.py \
  --query_profile datastore/outputs/JVASP-20955/profile_v1_1/query_profile.json \
  --output_dir datastore/outputs/JVASP-20955/pools

Notes
-----
This is Phase 2 only. It constructs pools using cheap chemistry, metadata,
symmetry and physical/stability proxies. It deliberately does not score role
priors. That comes next, because apparently we are trying to build software
instead of a single script-shaped swamp.
"""

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

POOL_SCHEMA_VERSION = "phase2.candidate_pools.v1.1"

DEFAULT_POOL_SIZES = {
    "same_family": 500,
    "adjacent_family": 500,
    "boundary_contrast": 500,
    "wildcard": 100,
    "negative_control": 100,
}

DEFAULT_SEED = 451

POOL_FILE_NAMES = {
    "same_family": "same_family_pool.csv",
    "adjacent_family": "adjacent_family_pool.csv",
    "boundary_contrast": "boundary_contrast_pool.csv",
    "wildcard": "wildcard_pool.csv",
    "negative_control": "negative_control_pool.csv",
}

OUTPUT_COLUMNS = [
    "pool_name",
    "query_jid",
    "query_formula",
    "candidate_jid",
    "formula",
    "reduced_formula",
    "material_type",
    "dataset_kind",
    "chemical_system",
    "composition_family",
    "material_family",
    "formula_family",
    "prototype_family",
    "structure_variant",
    "family_confidence",
    "same_formula_family",
    "same_prototype_family",
    "same_structure_variant",
    "elements",
    "element_overlap_count",
    "element_overlap_fraction_query",
    "same_chemical_system",
    "same_composition_family",
    "same_material_family",
    "spacegroup_number",
    "spacegroup_symbol",
    "crystal_system_code",
    "symmetry_match",
    "symmetry_distance",
    "formation_energy",
    "formation_energy_peratom",
    "energy_above_hull",
    "known_synthesized",
    "stability_label",
    "selection_reason",
    "selection_score",
    "rank_in_pool",
    "missing_fields",
]


@dataclass

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
class CandidatePoolConfig:
    same_family_size: int = DEFAULT_POOL_SIZES["same_family"]
    adjacent_family_size: int = DEFAULT_POOL_SIZES["adjacent_family"]
    boundary_contrast_size: int = DEFAULT_POOL_SIZES["boundary_contrast"]
    wildcard_size: int = DEFAULT_POOL_SIZES["wildcard"]
    negative_control_size: int = DEFAULT_POOL_SIZES["negative_control"]
    seed: int = DEFAULT_SEED

    # Deterministic diversity controls.
    max_per_chemical_system_same_family: int = 50
    max_per_chemical_system_adjacent: int = 25
    max_per_chemical_system_boundary: int = 25
    max_per_chemical_system_wildcard: int = 10
    max_per_chemical_system_negative: int = 10

    # Cheap screen thresholds.
    stable_ehull_threshold: float = 0.10
    adjacent_min_element_overlap: int = 1
    negative_max_element_overlap: int = 0

    # Family-classifier behaviour. When enabled, candidates lacking rich family
    # labels are classified from formula + cheap symmetry metadata.
    enable_family_classifier: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "CandidatePoolConfig":
        return cls(
            same_family_size=int(args.same_family_size),
            adjacent_family_size=int(args.adjacent_family_size),
            boundary_contrast_size=int(args.boundary_contrast_size),
            wildcard_size=int(args.wildcard_size),
            negative_control_size=int(args.negative_control_size),
            seed=int(args.seed),
            max_per_chemical_system_same_family=int(args.max_per_chemical_system_same_family),
            max_per_chemical_system_adjacent=int(args.max_per_chemical_system_adjacent),
            max_per_chemical_system_boundary=int(args.max_per_chemical_system_boundary),
            max_per_chemical_system_wildcard=int(args.max_per_chemical_system_wildcard),
            max_per_chemical_system_negative=int(args.max_per_chemical_system_negative),
            stable_ehull_threshold=float(args.stable_ehull_threshold),
            adjacent_min_element_overlap=int(args.adjacent_min_element_overlap),
            negative_max_element_overlap=int(args.negative_max_element_overlap),
            enable_family_classifier=not bool(args.disable_family_classifier),
        )



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_json(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def write_json(payload: Mapping[str, Any], path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=_json_default)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if math.isnan(float(obj)):
            return None
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return str(obj)


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    s = str(value).strip()
    return s if s else None


def normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return None
        return bool(int(value))
    s = str(value).strip().lower()
    if s in {"true", "t", "yes", "y", "1", "synthesized", "known"}:
        return True
    if s in {"false", "f", "no", "n", "0", "unknown", "not_synthesized"}:
        return False
    return None


def to_element_list(value: Any, formula: Optional[str] = None) -> List[str]:
    if isinstance(value, list):
        return sorted({str(x) for x in value if str(x).strip()})
    if isinstance(value, tuple) or isinstance(value, set):
        return sorted({str(x) for x in value if str(x).strip()})
    if isinstance(value, str):
        # Handles stored list strings badly but safely enough for pool selection.
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped.replace("'", '"'))
                if isinstance(parsed, list):
                    return sorted({str(x) for x in parsed if str(x).strip()})
            except Exception:
                pass
        # If this is a chemical system like Ca-O-Ti.
        if "-" in stripped and all(part.strip() for part in stripped.split("-")):
            return sorted({part.strip() for part in stripped.split("-") if part.strip()})
    if formula:
        return parse_formula_elements(formula)
    return []


def parse_formula_elements(formula: str | None) -> List[str]:
    if not formula:
        return []
    # Lightweight parser for element symbols. Enough for candidate pooling.
    import re

    tokens = re.findall(r"[A-Z][a-z]?", str(formula))
    return sorted(set(tokens))



def import_family_classifier():
    """Import optional rule-based family classifier.

    The pool builder remains usable without it, but v1.2 profiles and richer
    pool evidence work better when material_family_classifier.py is present.
    """
    try:
        from material_family_classifier import classify_material_family
        return classify_material_family
    except Exception:
        return None


def classification_from_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    fc = payload.get("family_classification") or {}
    if not isinstance(fc, Mapping):
        fc = {}
    return {
        "material_family": safe_str(fc.get("material_family")),
        "formula_family": safe_str(fc.get("formula_family")),
        "prototype_family": safe_str(fc.get("prototype_family")),
        "structure_variant": safe_str(fc.get("structure_variant")),
        "family_confidence": safe_float(fc.get("confidence") or fc.get("family_confidence")),
    }

def get_query_context(query_profile: Mapping[str, Any]) -> Dict[str, Any]:
    identity = dict(query_profile.get("identity") or {})
    composition = dict(query_profile.get("composition") or {})
    structural = dict(query_profile.get("structural_metadata") or query_profile.get("symmetry") or {})
    candidate_inputs = dict(query_profile.get("candidate_pool_inputs") or {})
    compatibility = dict(query_profile.get("compatibility") or {})
    legacy = dict(compatibility.get("legacy_cheap_descriptors") or {})
    family_classification = classification_from_payload(query_profile)

    query_jid = safe_str(identity.get("jid")) or safe_str(query_profile.get("source", {}).get("jid")) or safe_str(identity.get("external_id"))
    query_formula = safe_str(identity.get("formula")) or safe_str(identity.get("reduced_formula"))
    query_elements = to_element_list(composition.get("elements") or legacy.get("elements"), formula=query_formula)
    chemical_system = safe_str(candidate_inputs.get("chemical_key")) or safe_str(composition.get("chemical_system")) or safe_str(legacy.get("chemical_system"))
    composition_family = (
        safe_str(candidate_inputs.get("composition_key"))
        or safe_str(composition.get("composition_family"))
        or safe_str(legacy.get("composition_family"))
    )
    material_family = (
        safe_str(family_classification.get("material_family"))
        or safe_str(candidate_inputs.get("family_key"))
        or safe_str(legacy.get("material_family"))
        or composition_family
    )
    formula_family = safe_str(family_classification.get("formula_family")) or safe_str(legacy.get("formula_family"))
    prototype_family = safe_str(family_classification.get("prototype_family")) or safe_str(legacy.get("prototype_family"))
    structure_variant = safe_str(family_classification.get("structure_variant")) or safe_str(legacy.get("structure_variant"))
    family_confidence = safe_float(family_classification.get("family_confidence"))

    return {
        "query_jid": query_jid,
        "query_formula": query_formula,
        "query_reduced_formula": safe_str(identity.get("reduced_formula")) or query_formula,
        "query_elements": query_elements,
        "query_element_set": set(query_elements),
        "chemical_system": chemical_system,
        "composition_family": composition_family,
        "material_family": material_family,
        "formula_family": formula_family,
        "prototype_family": prototype_family,
        "structure_variant": structure_variant,
        "family_confidence": family_confidence,
        "spacegroup_number": safe_float(candidate_inputs.get("symmetry_key"))
        if safe_float(candidate_inputs.get("symmetry_key")) is not None
        else safe_float(structural.get("spacegroup_number") or legacy.get("spacegroup_number")),
        "spacegroup_symbol": safe_str(structural.get("spacegroup_symbol") or legacy.get("spacegroup_symbol")),
        "crystal_system_code": safe_float(structural.get("crystal_system_code") or legacy.get("crystal_system_code")),
        "energy_above_hull": safe_float(query_profile.get("physical", {}).get("inputs", {}).get("energy_above_hull") or legacy.get("energy_above_hull")),
        "stability_key": safe_str(candidate_inputs.get("stability_key")),
        "is_external_material": bool(identity.get("is_external_material", False)),
    }


def import_material_store():
    try:
        from material_store import MaterialStoreConfig, build_material_store
    except Exception as exc:
        raise RuntimeError(
            "Could not import material_store.py. Put candidate_pool_builder.py in the same folder as "
            "material_store.py, or run from that folder. Original error: " + repr(exc)
        ) from exc
    return MaterialStoreConfig, build_material_store


def build_universe_dataframe(
    *,
    material_store_config: Optional[str],
    force_rebuild_descriptor_cache: bool,
    log_file: Optional[str],
) -> pd.DataFrame:
    MaterialStoreConfig, build_material_store = import_material_store()
    config = MaterialStoreConfig.from_json(material_store_config) if material_store_config else None
    store = build_material_store(
        config=config,
        force_rebuild_descriptor_cache=force_rebuild_descriptor_cache,
        log_file=log_file,
    )
    universe = store.get_universe_df(include_external=False)
    if universe is None or universe.empty:
        raise RuntimeError("MaterialStore returned an empty universe dataframe.")
    return universe.copy()


def prepare_universe(df: pd.DataFrame, *, enable_family_classifier: bool = True) -> pd.DataFrame:
    out = df.copy()
    if "jid" not in out.columns:
        raise ValueError("Universe dataframe must contain a jid column.")
    if "formula" not in out.columns:
        out["formula"] = None
    if "reduced_formula" not in out.columns:
        out["reduced_formula"] = out["formula"]
    if "chemical_system" not in out.columns:
        out["chemical_system"] = None
    if "composition_family" not in out.columns:
        out["composition_family"] = None
    if "material_family" not in out.columns:
        out["material_family"] = out["composition_family"]
    else:
        out["material_family"] = out["material_family"].where(out["material_family"].notna(), out.get("composition_family"))

    # Rich family fields added in Phase 2 v1.1. If not present in the universe,
    # infer them cheaply from formula + space group using material_family_classifier.py.
    for col in ["formula_family", "prototype_family", "structure_variant", "family_confidence"]:
        if col not in out.columns:
            out[col] = None

    classifier = import_family_classifier() if enable_family_classifier else None
    if classifier is not None:
        classified_values = []
        for _, row in out.iterrows():
            if safe_str(row.get("formula_family")) or safe_str(row.get("prototype_family")) or safe_str(row.get("structure_variant")):
                classified_values.append(None)
                continue
            material_payload = {
                "formula": safe_str(row.get("formula")),
                "reduced_formula": safe_str(row.get("reduced_formula")) or safe_str(row.get("formula")),
                "composition_family": safe_str(row.get("composition_family")),
                "material_family": safe_str(row.get("material_family")),
                "spacegroup_number": safe_float(row.get("spacegroup_number")),
                "spacegroup_symbol": safe_str(row.get("spacegroup_symbol")),
                "crystal_system_code": safe_float(row.get("crystal_system_code")),
            }
            try:
                result = classifier(material_payload)
            except Exception:
                result = None
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            if not isinstance(result, Mapping):
                result = {}
            classified_values.append(result)

        for idx, result in zip(out.index, classified_values):
            if not isinstance(result, Mapping):
                continue
            for col, key in [
                ("material_family", "material_family"),
                ("formula_family", "formula_family"),
                ("prototype_family", "prototype_family"),
                ("structure_variant", "structure_variant"),
                ("family_confidence", "confidence"),
            ]:
                value = result.get(key)
                if col == "family_confidence" and safe_float(out.at[idx, col]) is None:
                    out.at[idx, col] = safe_float(value)
                elif col != "family_confidence" and not safe_str(out.at[idx, col]):
                    out.at[idx, col] = safe_str(value)

    # Fallbacks preserve old behaviour if the classifier is unavailable.
    out["material_family"] = out["material_family"].where(out["material_family"].notna(), out.get("composition_family"))
    if "element_set" not in out.columns:
        if "elements" in out.columns:
            out["element_set"] = out["elements"]
        else:
            out["element_set"] = None

    out["candidate_jid"] = out["jid"].astype(str)
    out["formula"] = out["formula"].astype(object)
    out["reduced_formula"] = out["reduced_formula"].astype(object)
    out["candidate_elements"] = [
        to_element_list(v, formula=f)
        for v, f in zip(out.get("element_set", pd.Series([None] * len(out))), out.get("formula", pd.Series([None] * len(out))))
    ]
    return out


def annotate_against_query(df: pd.DataFrame, query: Mapping[str, Any], config: CandidatePoolConfig) -> pd.DataFrame:
    out = df.copy()
    q_elements: Set[str] = set(query.get("query_element_set") or set())
    q_chemical_system = safe_str(query.get("chemical_system"))
    q_comp_family = safe_str(query.get("composition_family"))
    q_mat_family = safe_str(query.get("material_family"))
    q_formula_family = safe_str(query.get("formula_family"))
    q_proto_family = safe_str(query.get("prototype_family"))
    q_structure_variant = safe_str(query.get("structure_variant"))
    q_sg = safe_float(query.get("spacegroup_number"))
    q_crys = safe_float(query.get("crystal_system_code"))

    element_overlaps = []
    element_fracs = []
    for els in out["candidate_elements"]:
        cand_set = set(els or [])
        overlap = len(q_elements & cand_set)
        element_overlaps.append(overlap)
        element_fracs.append(float(overlap / max(len(q_elements), 1)))

    out["element_overlap_count"] = element_overlaps
    out["element_overlap_fraction_query"] = element_fracs
    out["same_chemical_system"] = out["chemical_system"].astype(str).eq(str(q_chemical_system)) if q_chemical_system else False
    out["same_composition_family"] = out["composition_family"].astype(str).eq(str(q_comp_family)) if q_comp_family else False
    out["same_material_family"] = out["material_family"].astype(str).eq(str(q_mat_family)) if q_mat_family else False
    out["same_formula_family"] = out["formula_family"].astype(str).eq(str(q_formula_family)) if q_formula_family and "formula_family" in out.columns else False
    out["same_prototype_family"] = out["prototype_family"].astype(str).eq(str(q_proto_family)) if q_proto_family and "prototype_family" in out.columns else False
    out["same_structure_variant"] = out["structure_variant"].astype(str).eq(str(q_structure_variant)) if q_structure_variant and "structure_variant" in out.columns else False

    candidate_sg = pd.to_numeric(out.get("spacegroup_number"), errors="coerce") if "spacegroup_number" in out.columns else pd.Series(np.nan, index=out.index)
    candidate_crys = pd.to_numeric(out.get("crystal_system_code"), errors="coerce") if "crystal_system_code" in out.columns else pd.Series(np.nan, index=out.index)
    if q_sg is not None:
        out["symmetry_match"] = candidate_sg.eq(q_sg)
        out["symmetry_distance"] = (candidate_sg - q_sg).abs()
    elif q_crys is not None:
        out["symmetry_match"] = candidate_crys.eq(q_crys)
        out["symmetry_distance"] = (candidate_crys - q_crys).abs()
    else:
        out["symmetry_match"] = False
        out["symmetry_distance"] = np.nan

    ehull = pd.to_numeric(out.get("energy_above_hull"), errors="coerce") if "energy_above_hull" in out.columns else pd.Series(np.nan, index=out.index)
    known = out.get("known_synthesized", pd.Series([None] * len(out))).apply(normalize_bool)
    out["known_synthesized_bool"] = known
    out["is_stable_or_known"] = (ehull <= float(config.stable_ehull_threshold)) | (known == True)
    out["stability_label"] = np.where(out["is_stable_or_known"], "stable_or_known", "unknown_or_less_stable")

    return out


def missing_fields_for_row(row: pd.Series, fields: Sequence[str]) -> str:
    missing = []
    for f in fields:
        if f not in row.index:
            missing.append(f)
            continue
        v = row.get(f)
        if v is None:
            missing.append(f)
            continue
        try:
            if pd.isna(v):
                missing.append(f)
        except Exception:
            pass
    return ";".join(missing)


def deterministic_select(
    df: pd.DataFrame,
    *,
    pool_name: str,
    target_size: int,
    query: Mapping[str, Any],
    reason: str,
    score_column: str,
    max_per_chemical_system: int,
    seed: int,
) -> pd.DataFrame:
    if df is None or df.empty or target_size <= 0:
        return empty_pool(pool_name, query)

    work = df.copy()
    work["selection_score"] = pd.to_numeric(work[score_column], errors="coerce").fillna(0.0)
    # Tiny deterministic jitter only as a final tie-breaker, based on jid and seed.
    work["_stable_hash"] = work["candidate_jid"].astype(str).apply(lambda x: stable_hash_float(f"{seed}:{x}"))
    work = work.sort_values(
        by=["selection_score", "is_stable_or_known", "element_overlap_count", "_stable_hash", "candidate_jid"],
        ascending=[False, False, False, True, True],
        na_position="last",
    )

    selected_rows = []
    per_system: Dict[str, int] = {}
    for _, row in work.iterrows():
        chem = safe_str(row.get("chemical_system")) or "UNKNOWN"
        if max_per_chemical_system > 0 and per_system.get(chem, 0) >= max_per_chemical_system:
            continue
        selected_rows.append(row)
        per_system[chem] = per_system.get(chem, 0) + 1
        if len(selected_rows) >= int(target_size):
            break

    if not selected_rows:
        return empty_pool(pool_name, query)

    out = pd.DataFrame([r.to_dict() for r in selected_rows]).reset_index(drop=True)
    out["pool_name"] = pool_name
    out["query_jid"] = query.get("query_jid")
    out["query_formula"] = query.get("query_formula")
    out["selection_reason"] = reason
    out["rank_in_pool"] = np.arange(1, len(out) + 1)
    out["elements"] = out["candidate_elements"].apply(lambda x: ";".join(x or []))
    fields_for_missing = [
        "chemical_system",
        "composition_family",
        "material_family",
        "formula_family",
        "prototype_family",
        "structure_variant",
        "spacegroup_number",
        "crystal_system_code",
        "formation_energy",
        "energy_above_hull",
        "known_synthesized",
    ]
    out["missing_fields"] = out.apply(lambda r: missing_fields_for_row(r, fields_for_missing), axis=1)

    for col in OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = None
    return out.loc[:, OUTPUT_COLUMNS].copy()


def empty_pool(pool_name: str, query: Mapping[str, Any]) -> pd.DataFrame:
    out = pd.DataFrame(columns=OUTPUT_COLUMNS)
    return out


def stable_hash_float(text: str) -> float:
    import hashlib

    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return int(h, 16) / float(16**12)


def build_same_family_pool(universe: pd.DataFrame, query: Mapping[str, Any], cfg: CandidatePoolConfig) -> pd.DataFrame:
    q_jid = safe_str(query.get("query_jid"))
    q_formula = safe_str(query.get("query_reduced_formula")) or safe_str(query.get("query_formula"))
    work = universe.copy()
    if q_jid:
        work = work[work["candidate_jid"].astype(str) != q_jid]
    if q_formula and "reduced_formula" in work.columns:
        # Keep same formula out of same-family pool so validation is not a cheap self-composition party.
        work = work[work["reduced_formula"].astype(str) != str(q_formula)]

    mask = (
        work["same_prototype_family"]
        | work["same_formula_family"]
        | work["same_structure_variant"]
        | work["same_material_family"]
        | work["same_composition_family"]
        | work["same_chemical_system"]
    )
    cand = work[mask].copy()
    cand["same_family_score"] = (
        cand["same_chemical_system"].astype(float) * 4.0
        + cand["same_prototype_family"].astype(float) * 3.5
        + cand["same_formula_family"].astype(float) * 2.5
        + cand["same_structure_variant"].astype(float) * 2.0
        + cand["same_material_family"].astype(float) * 1.5
        + cand["same_composition_family"].astype(float) * 0.75
        + cand["element_overlap_fraction_query"].astype(float) * 2.0
        + cand["symmetry_match"].astype(float) * 0.75
        + cand["is_stable_or_known"].astype(float) * 0.5
    )
    return deterministic_select(
        cand,
        pool_name="same_family",
        target_size=cfg.same_family_size,
        query=query,
        reason="same rich family/formula/prototype/composition/chemical context",
        score_column="same_family_score",
        max_per_chemical_system=cfg.max_per_chemical_system_same_family,
        seed=cfg.seed,
    )


def build_adjacent_family_pool(universe: pd.DataFrame, query: Mapping[str, Any], cfg: CandidatePoolConfig) -> pd.DataFrame:
    q_jid = safe_str(query.get("query_jid"))
    work = universe.copy()
    if q_jid:
        work = work[work["candidate_jid"].astype(str) != q_jid]

    # Adjacent means chemically connected but not merely the exact same chemical system.
    mask = (
        (work["element_overlap_count"] >= int(cfg.adjacent_min_element_overlap))
        & (~work["same_chemical_system"])
        & (
            work["same_composition_family"]
            | work["same_material_family"]
            | work["same_formula_family"]
            | work["same_prototype_family"]
            | (work["element_overlap_fraction_query"] >= 0.34)
        )
        # Adjacent pool should not simply duplicate the exact same structure variant.
        & (~work["same_structure_variant"] | ~work["same_prototype_family"])
    )
    cand = work[mask].copy()
    cand["adjacent_family_score"] = (
        cand["element_overlap_fraction_query"].astype(float) * 3.0
        + cand["same_prototype_family"].astype(float) * 2.0
        + cand["same_formula_family"].astype(float) * 1.5
        + cand["same_material_family"].astype(float) * 1.0
        + cand["same_composition_family"].astype(float) * 0.75
        + cand["is_stable_or_known"].astype(float) * 0.75
        + (1.0 / (1.0 + pd.to_numeric(cand["symmetry_distance"], errors="coerce").fillna(50.0))) * 0.5
    )
    return deterministic_select(
        cand,
        pool_name="adjacent_family",
        target_size=cfg.adjacent_family_size,
        query=query,
        reason="shares elements or related family context but is not the same chemical system/variant",
        score_column="adjacent_family_score",
        max_per_chemical_system=cfg.max_per_chemical_system_adjacent,
        seed=cfg.seed,
    )


def build_boundary_contrast_pool(universe: pd.DataFrame, query: Mapping[str, Any], cfg: CandidatePoolConfig) -> pd.DataFrame:
    q_jid = safe_str(query.get("query_jid"))
    work = universe.copy()
    if q_jid:
        work = work[work["candidate_jid"].astype(str) != q_jid]

    # Boundary/contrast candidates should be related enough to compare but show symmetry/metadata difference.
    sym_dist = pd.to_numeric(work["symmetry_distance"], errors="coerce")
    different_sym = (~work["symmetry_match"]) & sym_dist.notna()
    related = (
        work["same_prototype_family"]
        | work["same_formula_family"]
        | work["same_composition_family"]
        | work["same_material_family"]
        | (work["element_overlap_count"] >= 1)
    )
    mask = related & different_sym
    cand = work[mask].copy()
    sym_dist = pd.to_numeric(cand["symmetry_distance"], errors="coerce").fillna(0.0)
    # Nonlinear cap so high space-group difference helps but does not dominate everything like a caffeinated integer.
    sym_component = np.minimum(sym_dist / 50.0, 2.0)
    cand["boundary_contrast_score"] = (
        sym_component
        + cand["element_overlap_fraction_query"].astype(float) * 1.5
        + cand["same_prototype_family"].astype(float) * 2.0
        + cand["same_formula_family"].astype(float) * 1.5
        + cand["same_material_family"].astype(float) * 0.75
        + cand["same_composition_family"].astype(float) * 0.5
        + (~cand["same_structure_variant"]).astype(float) * 0.75
        + cand["is_stable_or_known"].astype(float) * 0.5
    )
    return deterministic_select(
        cand,
        pool_name="boundary_contrast",
        target_size=cfg.boundary_contrast_size,
        query=query,
        reason="related formula/prototype/chemistry/family with different symmetry or variant metadata",
        score_column="boundary_contrast_score",
        max_per_chemical_system=cfg.max_per_chemical_system_boundary,
        seed=cfg.seed,
    )


def build_wildcard_pool(
    universe: pd.DataFrame,
    query: Mapping[str, Any],
    cfg: CandidatePoolConfig,
    already_selected: Set[str],
) -> pd.DataFrame:
    q_jid = safe_str(query.get("query_jid"))
    work = universe.copy()
    if q_jid:
        work = work[work["candidate_jid"].astype(str) != q_jid]
    if already_selected:
        work = work[~work["candidate_jid"].astype(str).isin(already_selected)]

    # Wildcards preserve some sanity: prefer stable/known materials with data, but not necessarily related.
    cand = work.copy()
    cand["wildcard_score"] = (
        cand["is_stable_or_known"].astype(float) * 2.0
        + cand["element_overlap_fraction_query"].astype(float) * 0.5
        + cand.get("formation_energy", pd.Series([np.nan] * len(cand))).apply(lambda x: 0.25 if safe_float(x) is not None else 0.0)
        + cand.get("spacegroup_number", pd.Series([np.nan] * len(cand))).apply(lambda x: 0.25 if safe_float(x) is not None else 0.0)
    )
    return deterministic_select(
        cand,
        pool_name="wildcard",
        target_size=cfg.wildcard_size,
        query=query,
        reason="deterministic stable/known wildcard sample outside selected pools",
        score_column="wildcard_score",
        max_per_chemical_system=cfg.max_per_chemical_system_wildcard,
        seed=cfg.seed + 17,
    )


def build_negative_control_pool(
    universe: pd.DataFrame,
    query: Mapping[str, Any],
    cfg: CandidatePoolConfig,
    already_selected: Set[str],
) -> pd.DataFrame:
    q_jid = safe_str(query.get("query_jid"))
    work = universe.copy()
    if q_jid:
        work = work[work["candidate_jid"].astype(str) != q_jid]
    if already_selected:
        work = work[~work["candidate_jid"].astype(str).isin(already_selected)]

    mask = (
        (work["element_overlap_count"] <= int(cfg.negative_max_element_overlap))
        & (~work["same_composition_family"])
        & (~work["same_material_family"])
        & (~work["same_formula_family"])
        & (~work["same_prototype_family"])
        & (~work["same_chemical_system"])
    )
    cand = work[mask].copy()
    if cand.empty:
        # Fallback: least related available candidates.
        cand = work.copy()
    cand["negative_control_score"] = (
        (1.0 - cand["element_overlap_fraction_query"].astype(float)) * 3.0
        + (~cand["same_composition_family"]).astype(float) * 1.0
        + (~cand["same_material_family"]).astype(float) * 1.0
        + (~cand["same_formula_family"]).astype(float) * 0.75
        + (~cand["same_prototype_family"]).astype(float) * 0.75
        + (~cand["same_chemical_system"]).astype(float) * 1.0
        + cand["is_stable_or_known"].astype(float) * 0.25
    )
    return deterministic_select(
        cand,
        pool_name="negative_control",
        target_size=cfg.negative_control_size,
        query=query,
        reason="deliberately unrelated chemistry/family control pool",
        score_column="negative_control_score",
        max_per_chemical_system=cfg.max_per_chemical_system_negative,
        seed=cfg.seed + 31,
    )


def selected_jids(*pools: pd.DataFrame) -> Set[str]:
    out: Set[str] = set()
    for pool in pools:
        if pool is not None and not pool.empty and "candidate_jid" in pool.columns:
            out.update(pool["candidate_jid"].astype(str).tolist())
    return out


def build_all_pools(universe: pd.DataFrame, query_profile: Mapping[str, Any], cfg: CandidatePoolConfig) -> Dict[str, pd.DataFrame]:
    query = get_query_context(query_profile)
    prepared = prepare_universe(universe, enable_family_classifier=bool(cfg.enable_family_classifier))
    annotated = annotate_against_query(prepared, query, cfg)

    same = build_same_family_pool(annotated, query, cfg)
    adjacent = build_adjacent_family_pool(annotated, query, cfg)
    boundary = build_boundary_contrast_pool(annotated, query, cfg)
    already = selected_jids(same, adjacent, boundary)
    wildcard = build_wildcard_pool(annotated, query, cfg, already_selected=already)
    already = selected_jids(same, adjacent, boundary, wildcard)
    negative = build_negative_control_pool(annotated, query, cfg, already_selected=already)

    return {
        "same_family": same,
        "adjacent_family": adjacent,
        "boundary_contrast": boundary,
        "wildcard": wildcard,
        "negative_control": negative,
    }


def pool_stats(pool: pd.DataFrame) -> Dict[str, Any]:
    if pool is None or pool.empty:
        return {
            "n_candidates": 0,
            "unique_chemical_systems": 0,
            "unique_composition_families": 0,
            "unique_formula_families": 0,
            "unique_prototype_families": 0,
            "unique_structure_variants": 0,
            "stable_or_known_count": 0,
            "mean_selection_score": None,
            "missing_field_rows": 0,
        }
    return {
        "n_candidates": int(len(pool)),
        "unique_chemical_systems": int(pool["chemical_system"].dropna().nunique()) if "chemical_system" in pool.columns else 0,
        "unique_composition_families": int(pool["composition_family"].dropna().nunique()) if "composition_family" in pool.columns else 0,
        "unique_formula_families": int(pool["formula_family"].dropna().nunique()) if "formula_family" in pool.columns else 0,
        "unique_prototype_families": int(pool["prototype_family"].dropna().nunique()) if "prototype_family" in pool.columns else 0,
        "unique_structure_variants": int(pool["structure_variant"].dropna().nunique()) if "structure_variant" in pool.columns else 0,
        "stable_or_known_count": int((pool["stability_label"] == "stable_or_known").sum()) if "stability_label" in pool.columns else 0,
        "mean_selection_score": safe_float(pd.to_numeric(pool.get("selection_score"), errors="coerce").mean()) if "selection_score" in pool.columns else None,
        "missing_field_rows": int(pool.get("missing_fields", pd.Series(dtype=str)).astype(str).ne("").sum()) if "missing_fields" in pool.columns else 0,
    }


def write_outputs(
    pools: Mapping[str, pd.DataFrame],
    *,
    query_profile: Mapping[str, Any],
    output_dir: str | Path,
    cfg: CandidatePoolConfig,
    query_profile_path: str | Path,
) -> Dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for pool_name, df in pools.items():
        filename = POOL_FILE_NAMES[pool_name]
        df.to_csv(out_dir / filename, index=False)

    query = get_query_context(query_profile)
    summary = {
        "schema_version": POOL_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_profile_path": str(query_profile_path),
        "query": {
            "query_jid": query.get("query_jid"),
            "query_formula": query.get("query_formula"),
            "chemical_system": query.get("chemical_system"),
            "composition_family": query.get("composition_family"),
            "material_family": query.get("material_family"),
            "formula_family": query.get("formula_family"),
            "prototype_family": query.get("prototype_family"),
            "structure_variant": query.get("structure_variant"),
            "family_confidence": query.get("family_confidence"),
            "spacegroup_number": query.get("spacegroup_number"),
            "spacegroup_symbol": query.get("spacegroup_symbol"),
            "crystal_system_code": query.get("crystal_system_code"),
            "is_external_material": query.get("is_external_material"),
        },
        "config": cfg.to_dict(),
        "pool_files": POOL_FILE_NAMES,
        "pool_counts": {name: int(len(df)) for name, df in pools.items()},
        "pool_stats": {name: pool_stats(df) for name, df in pools.items()},
        "deterministic_seed": int(cfg.seed),
        "notes": [
            "Phase 2 candidate pools only: no cheap evidence metrics, role-prior scoring, local-structure ranking, DFT, or property prediction has been run.",
            "Negative-control pool is written separately and should not be mixed with candidate evidence pools.",
            "Pool selection is deterministic for a fixed universe, query profile, configuration and seed.",
            "Phase 2 v1.1 uses richer family labels when available: formula_family, prototype_family and structure_variant.",
        ],
    }
    write_json(summary, out_dir / "candidate_pool_summary.json")
    write_json(cfg.to_dict(), out_dir / "pool_config_used.json")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic Phase 2 candidate pools for a material profile."
    )
    parser.add_argument("--query_profile", required=True, help="Path to query_profile.json produced by material_profile_builder.py")
    parser.add_argument("--output_dir", required=True, help="Directory where pool CSV/JSON outputs will be written")

    parser.add_argument("--material_store_config", default=None, help="Optional MaterialStoreConfig JSON path")
    parser.add_argument("--force_rebuild_descriptor_cache", action="store_true", help="Force rebuild of MaterialStore descriptor cache")
    parser.add_argument("--log_file", default=None, help="Optional log file for MaterialStore")

    parser.add_argument("--same_family_size", type=int, default=DEFAULT_POOL_SIZES["same_family"])
    parser.add_argument("--adjacent_family_size", type=int, default=DEFAULT_POOL_SIZES["adjacent_family"])
    parser.add_argument("--boundary_contrast_size", type=int, default=DEFAULT_POOL_SIZES["boundary_contrast"])
    parser.add_argument("--wildcard_size", type=int, default=DEFAULT_POOL_SIZES["wildcard"])
    parser.add_argument("--negative_control_size", type=int, default=DEFAULT_POOL_SIZES["negative_control"])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)

    parser.add_argument("--max_per_chemical_system_same_family", type=int, default=50)
    parser.add_argument("--max_per_chemical_system_adjacent", type=int, default=25)
    parser.add_argument("--max_per_chemical_system_boundary", type=int, default=25)
    parser.add_argument("--max_per_chemical_system_wildcard", type=int, default=10)
    parser.add_argument("--max_per_chemical_system_negative", type=int, default=10)

    parser.add_argument("--stable_ehull_threshold", type=float, default=0.10)
    parser.add_argument("--adjacent_min_element_overlap", type=int, default=1)
    parser.add_argument("--negative_max_element_overlap", type=int, default=0)
    parser.add_argument("--disable_family_classifier", action="store_true", help="Disable optional rule-based classification of candidate universe rows")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = CandidatePoolConfig.from_args(args)
    query_profile = load_json(args.query_profile)
    universe = build_universe_dataframe(
        material_store_config=args.material_store_config,
        force_rebuild_descriptor_cache=bool(args.force_rebuild_descriptor_cache),
        log_file=args.log_file,
    )
    pools = build_all_pools(universe, query_profile, cfg)
    summary = write_outputs(
        pools,
        query_profile=query_profile,
        output_dir=args.output_dir,
        cfg=cfg,
        query_profile_path=args.query_profile,
    )
    print(json.dumps({
        "status": "success",
        "schema_version": POOL_SCHEMA_VERSION,
        "output_dir": str(Path(args.output_dir).resolve()),
        "pool_counts": summary["pool_counts"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
