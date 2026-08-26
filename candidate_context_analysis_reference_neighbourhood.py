#!/usr/bin/env python3
"""
Candidate context analysis using reference neighbourhoods.

Overview
--------
This module provides the final explainability layer of the Cheap Context First
pipeline. It interprets previously generated structural-context evidence and
reference-neighbourhood fingerprints to produce an explainable narrative of a
candidate's structural position.

Responsibilities
----------------
* Analyse reference-neighbourhood fingerprints.
* Summarise neighbourhood coherence and diversity.
* Explain candidate placement relative to reference materials.
* Produce machine-readable and human-readable contextual outputs.
* Preserve separation between evidence generation and interpretation.

Maintenance notes
-----------------
This module should consume upstream artefacts rather than modify them. New
features should improve explainability and reporting while preserving
compatibility with the established fingerprint and role-prior schemas.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.stats import spearmanr
from sklearn.metrics import silhouette_score

SCHEMA_VERSION = "candidate_context_analysis.phase1c2.reference_neighbourhood.v1"
SUPPORTED_FINGERPRINT_SCHEMA = "phase3.reference_neighbourhood_fingerprint.v1"

CORE_PROFILE_FEATURES = [
    "local_context_support",
    "structural_regime_contrast",
    "neighbourhood_coherence",
    "structural_context_diversity",
]

RELIABILITY_FIELDS = [
    "evidence_sufficiency_score",
    "retrieval_completeness",
    "pool_independence",
    "profile_confidence",
]

ID_CANDIDATES = ["candidate_id", "case_id", "material_id", "jid", "external_id"]

POOL_ORDER = [
    "same_family",
    "adjacent_family",
    "boundary_contrast",
    "wildcard",
    "negative_control",
]

DEFAULT_POOL_WEIGHTS = {
    "same_family": 0.35,
    "adjacent_family": 0.20,
    "boundary_contrast": 0.30,
    "wildcard": 0.15,
    "negative_control": 0.00,
}

DISTRIBUTION_FIELDS = {
    "composition_family": 0.10,
    "material_family": 0.10,
    "formula_family": 0.15,
    "prototype_family": 0.20,
    "structure_variant": 0.20,
    "spacegroup_number": 0.15,
    "crystal_system_code": 0.10,
}

QUERY_MATCH_FIELDS = [
    "same_chemical_system_rate",
    "same_composition_family_rate",
    "same_material_family_rate",
    "same_formula_family_rate",
    "same_prototype_family_rate",
    "same_structure_variant_rate",
    "same_spacegroup_rate",
    "same_crystal_system_rate",
]

POOL_CONTEXT_FIELDS = [
    "query_similarity_score",
    "pool_diversity_score",
    "structural_regime_diversity_score",
    "missing_value_rate_required_columns",
    "stable_fraction_ehull_le_0_1",
    "known_synthesized_rate",
]


@dataclass(frozen=True)
class Config:
    structural_context_summary: Path
    batch_output_root: Path
    output_dir: Path
    fingerprint_name: str
    top_k: int
    n_clusters: Optional[int]
    max_clusters: int
    min_profile_confidence: float
    min_retrieval_completeness: float
    include_low_reliability: bool
    profile_weight: float
    identity_weight: float
    distribution_weight: float
    context_feature_weight: float
    include_negative_control: bool
    redundancy_similarity: float
    redundancy_min_component_similarity: float
    transition_margin: float
    matrix_mode: str
    max_full_matrix_candidates: int
    max_exact_candidates: int
    seed: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args(argv: Optional[Sequence[str]] = None) -> Config:
    p = argparse.ArgumentParser(
        description=(
            "Compare Structural Context Profiles using their shared and differing "
            "reference-neighbourhood fingerprints (Phase 1C.2)."
        )
    )
    p.add_argument("--structural_context_summary", required=True, type=Path)
    p.add_argument("--batch_output_root", required=True, type=Path)
    p.add_argument("--output_dir", required=True, type=Path)
    p.add_argument(
        "--fingerprint_name",
        default="reference_neighbourhood_fingerprint.json",
        help="Fingerprint filename under each candidate's evidence directory.",
    )
    p.add_argument("--top_k", type=int, default=5)
    p.add_argument("--n_clusters", type=int, default=None)
    p.add_argument("--max_clusters", type=int, default=8)
    p.add_argument("--min_profile_confidence", type=float, default=0.50)
    p.add_argument("--min_retrieval_completeness", type=float, default=0.50)
    p.add_argument(
        "--include_low_reliability",
        action="store_true",
        help="Include low-reliability profiles in clustering rather than withholding them for review.",
    )
    p.add_argument(
        "--profile_weight",
        type=float,
        default=0.35,
        help="Weight of the four Structural Context Profile measurements in combined similarity.",
    )
    p.add_argument("--identity_weight", type=float, default=0.55)
    p.add_argument("--distribution_weight", type=float, default=0.30)
    p.add_argument("--context_feature_weight", type=float, default=0.15)
    p.add_argument(
        "--include_negative_control",
        action="store_true",
        help="Include negative-control neighbour identity/distributions in fingerprint similarity.",
    )
    p.add_argument("--redundancy_similarity", type=float, default=0.90)
    p.add_argument("--redundancy_min_component_similarity", type=float, default=0.80)
    p.add_argument("--transition_margin", type=float, default=0.10)
    p.add_argument(
        "--matrix_mode",
        choices=["auto", "full", "none"],
        default="auto",
        help="Write square similarity matrices. Auto writes them up to --max_full_matrix_candidates.",
    )
    p.add_argument("--max_full_matrix_candidates", type=int, default=1000)
    p.add_argument(
        "--max_exact_candidates",
        type=int,
        default=2500,
        help="Safety limit for this exact O(n^2) implementation.",
    )
    p.add_argument("--seed", type=int, default=451)
    a = p.parse_args(argv)

    if a.top_k < 1:
        p.error("--top_k must be at least 1")
    if a.n_clusters is not None and a.n_clusters < 1:
        p.error("--n_clusters must be at least 1")
    if a.max_clusters < 2:
        p.error("--max_clusters must be at least 2")
    for name in [
        "profile_weight",
        "identity_weight",
        "distribution_weight",
        "context_feature_weight",
        "redundancy_similarity",
        "redundancy_min_component_similarity",
        "transition_margin",
        "min_profile_confidence",
        "min_retrieval_completeness",
    ]:
        value = float(getattr(a, name))
        if not 0.0 <= value <= 1.0:
            p.error(f"--{name} must be between 0 and 1")
    if a.max_full_matrix_candidates < 1 or a.max_exact_candidates < 2:
        p.error("Matrix and exact-analysis candidate limits must be positive")
    if a.profile_weight >= 1.0:
        p.error("--profile_weight must be below 1 so the reference fingerprint contributes")
    if (a.identity_weight + a.distribution_weight + a.context_feature_weight) <= 0:
        p.error("At least one fingerprint component weight must be positive")

    return Config(
        structural_context_summary=a.structural_context_summary.expanduser().resolve(),
        batch_output_root=a.batch_output_root.expanduser().resolve(),
        output_dir=a.output_dir.expanduser().resolve(),
        fingerprint_name=a.fingerprint_name,
        top_k=a.top_k,
        n_clusters=a.n_clusters,
        max_clusters=a.max_clusters,
        min_profile_confidence=a.min_profile_confidence,
        min_retrieval_completeness=a.min_retrieval_completeness,
        include_low_reliability=a.include_low_reliability,
        profile_weight=a.profile_weight,
        identity_weight=a.identity_weight,
        distribution_weight=a.distribution_weight,
        context_feature_weight=a.context_feature_weight,
        include_negative_control=a.include_negative_control,
        redundancy_similarity=a.redundancy_similarity,
        redundancy_min_component_similarity=a.redundancy_min_component_similarity,
        transition_margin=a.transition_margin,
        matrix_mode=a.matrix_mode,
        max_full_matrix_candidates=a.max_full_matrix_candidates,
        max_exact_candidates=a.max_exact_candidates,
        seed=a.seed,
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=json_safe), encoding="utf-8")


def json_safe(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    if pd.isna(value):
        return None
    return value


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except Exception:
        return None


def clip01(value: Any) -> Optional[float]:
    value = safe_float(value)
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def weighted_mean(values: Iterable[tuple[Optional[float], float]]) -> Optional[float]:
    available = [(float(v), float(w)) for v, w in values if v is not None and w > 0]
    if not available:
        return None
    total = sum(w for _, w in available)
    return sum(v * w for v, w in available) / total if total else None


def pick_id_column(df: pd.DataFrame) -> str:
    for col in ID_CANDIDATES:
        if col in df.columns and df[col].notna().any():
            return col
    raise ValueError(f"No candidate ID column found. Expected one of {ID_CANDIDATES}")


def prepare_summary(df: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, str]:
    missing = [c for c in CORE_PROFILE_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Structural context summary is missing core fields: {missing}")
    id_col = pick_id_column(df)
    work = df.copy()
    work["candidate_id"] = work[id_col].map(clean_text)
    if work["candidate_id"].eq("").any():
        raise ValueError("Candidate IDs must not be blank")
    if work["candidate_id"].duplicated().any():
        dupes = work.loc[work["candidate_id"].duplicated(False), "candidate_id"].tolist()
        raise ValueError(f"Candidate IDs must be unique. Duplicate examples: {dupes[:10]}")
    for col in CORE_PROFILE_FEATURES + RELIABILITY_FIELDS + ["context_ambiguity"]:
        if col not in work.columns:
            work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work["missing_core_feature_count"] = work[CORE_PROFILE_FEATURES].isna().sum(axis=1)
    work["low_profile_confidence"] = work["profile_confidence"].lt(cfg.min_profile_confidence).fillna(False)
    work["low_retrieval_completeness"] = work["retrieval_completeness"].lt(cfg.min_retrieval_completeness).fillna(False)
    return work, id_col


def discover_fingerprints(root: Path, filename: str) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    mapping: dict[str, Path] = {}
    inventory: list[dict[str, Any]] = []
    for path in sorted(root.rglob(filename)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            query = data.get("query", {}) if isinstance(data.get("query"), dict) else {}
            candidate_id = clean_text(query.get("jid") or query.get("external_id"))
            if not candidate_id:
                candidate_id = path.parents[1].name if path.parent.name == "evidence" else path.parent.name
            schema = data.get("schema_version")
            status = "compatible" if schema == SUPPORTED_FINGERPRINT_SCHEMA else "incompatible_schema"
            if candidate_id in mapping:
                status = "duplicate_candidate_fingerprint"
            else:
                mapping[candidate_id] = path
            inventory.append({
                "candidate_id": candidate_id,
                "fingerprint_path": str(path),
                "schema_version": schema,
                "status": status,
                "query_formula": query.get("formula"),
                "unique_reference_count": data.get("reference_neighbourhood", {}).get("unique_reference_count"),
            })
        except Exception as exc:
            inventory.append({
                "candidate_id": "",
                "fingerprint_path": str(path),
                "schema_version": None,
                "status": "unreadable",
                "error": repr(exc),
            })
    return mapping, inventory


def load_fingerprints(
    candidates: Sequence[str],
    mapping: Mapping[str, Path],
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    loaded: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for cid in candidates:
        path = mapping.get(cid)
        if path is None:
            rows.append({"candidate_id": cid, "status": "missing", "fingerprint_path": ""})
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            schema = data.get("schema_version")
            status = "compatible" if schema == SUPPORTED_FINGERPRINT_SCHEMA else "incompatible_schema"
            if status == "compatible":
                loaded[cid] = data
            ref = data.get("reference_neighbourhood", {})
            pools = ref.get("pools", {}) if isinstance(ref.get("pools"), dict) else {}
            available_pools = sum(bool(pools.get(name, {}).get("available")) for name in POOL_ORDER)
            rows.append({
                "candidate_id": cid,
                "status": status,
                "fingerprint_path": str(path),
                "schema_version": schema,
                "unique_reference_count": ref.get("unique_reference_count"),
                "available_pool_count": available_pools,
                "pool_count": len(POOL_ORDER),
                "fingerprint_completeness": available_pools / len(POOL_ORDER),
                "query_formula": data.get("query", {}).get("formula"),
            })
        except Exception as exc:
            rows.append({
                "candidate_id": cid,
                "status": "unreadable",
                "fingerprint_path": str(path),
                "error": repr(exc),
            })
    return loaded, pd.DataFrame(rows)


def rank_weight_map(ids: Sequence[Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for rank, raw in enumerate(ids, start=1):
        key = clean_text(raw)
        if not key or key in result:
            continue
        result[key] = 1.0 / math.log2(rank + 2.0)
    return result


def weighted_jaccard(a: Mapping[str, float], b: Mapping[str, float]) -> Optional[float]:
    keys = set(a) | set(b)
    if not keys:
        return None
    numerator = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    denominator = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    return numerator / denominator if denominator else None


def ordinary_jaccard(a: Iterable[Any], b: Iterable[Any]) -> Optional[float]:
    sa = {clean_text(x) for x in a if clean_text(x)}
    sb = {clean_text(x) for x in b if clean_text(x)}
    union = sa | sb
    if not union:
        return None
    return len(sa & sb) / len(union)


def distribution_fractions(pool: Mapping[str, Any], field: str) -> dict[str, float]:
    dist = pool.get("context_distributions", {}).get(field, {})
    values = dist.get("fractions", {}) if isinstance(dist, dict) else {}
    result: dict[str, float] = {}
    if isinstance(values, dict):
        for key, value in values.items():
            fv = safe_float(value)
            if fv is not None and fv >= 0:
                result[str(key)] = fv
    total = sum(result.values())
    if total > 0:
        result = {k: v / total for k, v in result.items()}
    return result


def jensen_shannon_similarity(a: Mapping[str, float], b: Mapping[str, float]) -> Optional[float]:
    if not a and not b:
        return None
    if not a or not b:
        return 0.0
    keys = sorted(set(a) | set(b))
    p = np.array([a.get(k, 0.0) for k in keys], dtype=float)
    q = np.array([b.get(k, 0.0) for k in keys], dtype=float)
    if p.sum() <= 0 or q.sum() <= 0:
        return 0.0
    p /= p.sum()
    q /= q.sum()
    m = 0.5 * (p + q)

    def kl(x: np.ndarray, y: np.ndarray) -> float:
        mask = x > 0
        return float(np.sum(x[mask] * np.log2(x[mask] / y[mask])))

    js = 0.5 * kl(p, m) + 0.5 * kl(q, m)
    return max(0.0, min(1.0, 1.0 - math.sqrt(max(0.0, js))))


def numeric_feature_similarity(a: Any, b: Any) -> Optional[float]:
    fa = clip01(a)
    fb = clip01(b)
    if fa is None and fb is None:
        return None
    if fa is None or fb is None:
        return 0.0
    return 1.0 - abs(fa - fb)


def count_similarity(a: Any, b: Any) -> Optional[float]:
    fa = safe_float(a)
    fb = safe_float(b)
    if fa is None and fb is None:
        return None
    if fa is None or fb is None:
        return 0.0
    if fa == 0 and fb == 0:
        return 1.0
    return min(fa, fb) / max(fa, fb) if max(fa, fb) > 0 else 1.0


def active_pool_weights(cfg: Config) -> dict[str, float]:
    weights = dict(DEFAULT_POOL_WEIGHTS)
    if cfg.include_negative_control:
        weights["same_family"] = 0.33
        weights["adjacent_family"] = 0.19
        weights["boundary_contrast"] = 0.28
        weights["wildcard"] = 0.15
        weights["negative_control"] = 0.05
    return weights


def profile_similarity(row_a: pd.Series, row_b: pd.Series) -> Optional[float]:
    diffs: list[float] = []
    for field in CORE_PROFILE_FEATURES:
        a = clip01(row_a.get(field))
        b = clip01(row_b.get(field))
        if a is None or b is None:
            continue
        diffs.append((a - b) ** 2)
    if not diffs:
        return None
    return max(0.0, 1.0 - math.sqrt(sum(diffs) / len(diffs)))


def reference_identity_similarity(
    fp_a: Mapping[str, Any], fp_b: Mapping[str, Any], cfg: Config
) -> tuple[Optional[float], Optional[float], dict[str, Optional[float]]]:
    pools_a = fp_a.get("reference_neighbourhood", {}).get("pools", {})
    pools_b = fp_b.get("reference_neighbourhood", {}).get("pools", {})
    pool_weights = active_pool_weights(cfg)
    details: dict[str, Optional[float]] = {}
    components: list[tuple[Optional[float], float]] = []
    for pool_name, weight in pool_weights.items():
        if weight <= 0:
            continue
        ids_a = pools_a.get(pool_name, {}).get("reference_ids_ranked", [])
        ids_b = pools_b.get(pool_name, {}).get("reference_ids_ranked", [])
        similarity = weighted_jaccard(rank_weight_map(ids_a), rank_weight_map(ids_b))
        details[f"{pool_name}_rank_weighted_jaccard"] = similarity
        components.append((similarity, weight))
    all_a = fp_a.get("reference_neighbourhood", {}).get("all_unique_reference_ids", [])
    all_b = fp_b.get("reference_neighbourhood", {}).get("all_unique_reference_ids", [])
    all_jaccard = ordinary_jaccard(all_a, all_b)
    pool_score = weighted_mean(components)
    identity = weighted_mean([(pool_score, 0.80), (all_jaccard, 0.20)])
    return identity, all_jaccard, details


def reference_distribution_similarity(
    fp_a: Mapping[str, Any], fp_b: Mapping[str, Any], cfg: Config
) -> tuple[Optional[float], dict[str, Optional[float]]]:
    pools_a = fp_a.get("reference_neighbourhood", {}).get("pools", {})
    pools_b = fp_b.get("reference_neighbourhood", {}).get("pools", {})
    pool_weights = active_pool_weights(cfg)
    pool_results: list[tuple[Optional[float], float]] = []
    details: dict[str, Optional[float]] = {}
    for pool_name, pool_weight in pool_weights.items():
        if pool_weight <= 0:
            continue
        pa = pools_a.get(pool_name, {})
        pb = pools_b.get(pool_name, {})
        field_results: list[tuple[Optional[float], float]] = []
        for field, field_weight in DISTRIBUTION_FIELDS.items():
            sim = jensen_shannon_similarity(
                distribution_fractions(pa, field), distribution_fractions(pb, field)
            )
            details[f"{pool_name}_{field}_distribution_similarity"] = sim
            field_results.append((sim, field_weight))
        pool_sim = weighted_mean(field_results)
        details[f"{pool_name}_distribution_similarity"] = pool_sim
        pool_results.append((pool_sim, pool_weight))
    return weighted_mean(pool_results), details


def reference_context_feature_similarity(
    fp_a: Mapping[str, Any], fp_b: Mapping[str, Any], cfg: Config
) -> tuple[Optional[float], dict[str, Optional[float]]]:
    pools_a = fp_a.get("reference_neighbourhood", {}).get("pools", {})
    pools_b = fp_b.get("reference_neighbourhood", {}).get("pools", {})
    pool_weights = active_pool_weights(cfg)
    pool_results: list[tuple[Optional[float], float]] = []
    details: dict[str, Optional[float]] = {}
    for pool_name, pool_weight in pool_weights.items():
        if pool_weight <= 0:
            continue
        pa = pools_a.get(pool_name, {})
        pb = pools_b.get(pool_name, {})
        values: list[tuple[Optional[float], float]] = []
        for field in QUERY_MATCH_FIELDS:
            sim = numeric_feature_similarity(
                pa.get("query_match_rates", {}).get(field),
                pb.get("query_match_rates", {}).get(field),
            )
            values.append((sim, 1.0))
        for field in POOL_CONTEXT_FIELDS:
            sim = numeric_feature_similarity(
                pa.get("pool_context_features", {}).get(field),
                pb.get("pool_context_features", {}).get(field),
            )
            values.append((sim, 1.0))
        values.append((count_similarity(pa.get("row_count"), pb.get("row_count")), 1.0))
        pool_sim = weighted_mean(values)
        details[f"{pool_name}_context_feature_similarity"] = pool_sim
        pool_results.append((pool_sim, pool_weight))
    return weighted_mean(pool_results), details


def chemical_system_set(row: pd.Series, fp: Mapping[str, Any]) -> set[str]:
    raw = clean_text(row.get("profile_chemical_system")) or clean_text(fp.get("query", {}).get("chemical_system"))
    return {x.strip() for x in raw.replace(",", "-").split("-") if x.strip()}


def chemistry_baseline_similarity(
    row_a: pd.Series, row_b: pd.Series, fp_a: Mapping[str, Any], fp_b: Mapping[str, Any]
) -> Optional[float]:
    elem = ordinary_jaccard(chemical_system_set(row_a, fp_a), chemical_system_set(row_b, fp_b))

    def exact(field: str, query_field: str) -> Optional[float]:
        a = clean_text(row_a.get(field)) or clean_text(fp_a.get("query", {}).get(query_field))
        b = clean_text(row_b.get(field)) or clean_text(fp_b.get("query", {}).get(query_field))
        if not a and not b:
            return None
        if not a or not b:
            return 0.0
        return 1.0 if a.lower() == b.lower() else 0.0

    return weighted_mean([
        (elem, 0.40),
        (exact("profile_composition_family", "composition_family"), 0.10),
        (exact("profile_formula_family", "formula_family"), 0.20),
        (exact("profile_prototype_family", "prototype_family"), 0.10),
        (exact("profile_structure_variant", "structure_variant"), 0.10),
        (exact("", "crystal_system_code"), 0.10),
    ])



EXPLAINABILITY_COVERAGE_WEIGHTS = {
    "material_families": 0.20,
    "formula_families": 0.10,
    "prototype_families": 0.25,
    "structure_variants": 0.25,
    "space_groups": 0.15,
    "crystal_systems": 0.05,
}

EXPLAINABILITY_ENTROPY_FIELDS = [
    "prototype_entropy_normalised",
    "material_family_entropy_normalised",
    "formula_family_entropy_normalised",
    "space_group_entropy_normalised",
]


def explainability_block(fp: Mapping[str, Any]) -> Mapping[str, Any]:
    block = fp.get("explainability_summary", {})
    return block if isinstance(block, Mapping) else {}


def fingerprint_signature(fp: Mapping[str, Any]) -> Mapping[str, Any]:
    block = explainability_block(fp)
    signatures = block.get("fingerprint_signature", {})
    if not isinstance(signatures, Mapping):
        return {}
    overall = signatures.get("overall", {})
    return overall if isinstance(overall, Mapping) else {}


def classification_coverage_map(fp: Mapping[str, Any]) -> Mapping[str, Any]:
    signature = fingerprint_signature(fp)
    coverage = signature.get("classification_coverage", {})
    if isinstance(coverage, Mapping):
        return coverage
    block = explainability_block(fp)
    coverage_root = block.get("classification_coverage", {})
    if isinstance(coverage_root, Mapping):
        overall = coverage_root.get("overall", {})
        return overall if isinstance(overall, Mapping) else {}
    return {}


def coverage_fraction(fp: Mapping[str, Any], field: str) -> Optional[float]:
    item = classification_coverage_map(fp).get(field, {})
    if not isinstance(item, Mapping):
        return None
    return clip01(item.get("classified_fraction"))


def explainability_coverage_score(fp: Mapping[str, Any]) -> Optional[float]:
    weighted: list[tuple[Optional[float], float]] = []
    for field, weight in EXPLAINABILITY_COVERAGE_WEIGHTS.items():
        weighted.append((coverage_fraction(fp, field), weight))
    return weighted_mean(weighted)


def pair_explainability_confidence(
    fp_a: Mapping[str, Any],
    fp_b: Mapping[str, Any],
    base_pair_reliability: float,
) -> tuple[float, str, Optional[float], Optional[float]]:
    coverage_a = explainability_coverage_score(fp_a)
    coverage_b = explainability_coverage_score(fp_b)
    if coverage_a is None or coverage_b is None:
        confidence = float(base_pair_reliability)
        label = "unavailable_coverage"
    else:
        coverage_pair = math.sqrt(max(0.0, coverage_a) * max(0.0, coverage_b))
        confidence = math.sqrt(max(0.0, base_pair_reliability) * coverage_pair)
        if confidence >= 0.80:
            label = "high"
        elif confidence >= 0.55:
            label = "moderate"
        else:
            label = "low"
    return float(confidence), label, coverage_a, coverage_b


def dominant_signature_label(fp: Mapping[str, Any], field: str) -> Optional[str]:
    entry = fingerprint_signature(fp).get(field)
    if not isinstance(entry, Mapping):
        return None
    if entry.get("label") is not None:
        return clean_text(entry.get("label"))
    if entry.get("value") is not None:
        return clean_text(entry.get("value"))
    number = entry.get("number")
    symbol = clean_text(entry.get("symbol"))
    if number is not None and symbol:
        return f"{symbol} (No. {number})"
    if number is not None:
        return f"space group {number}"
    return None


def context_signature_narrative(fp: Mapping[str, Any]) -> Optional[str]:
    signature = fingerprint_signature(fp)
    context = signature.get("context_signature", {})
    if not isinstance(context, Mapping):
        return None
    value = clean_text(context.get("narrative"))
    return value or None


def entropy_value(fp: Mapping[str, Any], field: str) -> Optional[float]:
    return clip01(fingerprint_signature(fp).get(field))


def compare_context_signatures(
    fp_a: Mapping[str, Any],
    fp_b: Mapping[str, Any],
) -> dict[str, Any]:
    fields = [
        "dominant_prototype_family",
        "dominant_structural_regime",
        "dominant_material_family",
        "dominant_formula_family",
        "dominant_space_group",
        "dominant_crystal_system",
    ]
    result: dict[str, Any] = {}
    agreement_count = 0
    comparable_count = 0
    for field in fields:
        a = dominant_signature_label(fp_a, field)
        b = dominant_signature_label(fp_b, field)
        agreement = None if a is None or b is None else (a == b)
        if agreement is not None:
            comparable_count += 1
            agreement_count += int(agreement)
        prefix = field.replace("dominant_", "")
        result[f"candidate_a_{prefix}"] = a
        result[f"candidate_b_{prefix}"] = b
        result[f"{prefix}_agreement"] = agreement
    result["context_signature_comparable_dimensions"] = comparable_count
    result["context_signature_agreement_count"] = agreement_count
    result["context_signature_agreement_fraction"] = (
        agreement_count / comparable_count if comparable_count else None
    )
    result["candidate_a_context_narrative"] = context_signature_narrative(fp_a)
    result["candidate_b_context_narrative"] = context_signature_narrative(fp_b)
    return result


def compare_entropy(
    fp_a: Mapping[str, Any],
    fp_b: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    differences: list[float] = []
    for field in EXPLAINABILITY_ENTROPY_FIELDS:
        a = entropy_value(fp_a, field)
        b = entropy_value(fp_b, field)
        difference = abs(a - b) if a is not None and b is not None else None
        result[f"candidate_a_{field}"] = a
        result[f"candidate_b_{field}"] = b
        result[f"{field}_absolute_difference"] = difference
        if difference is not None:
            differences.append(difference)
    result["mean_entropy_absolute_difference"] = (
        float(sum(differences) / len(differences)) if differences else None
    )
    return result


def similarity_decomposition(
    profile: Optional[float],
    identity: Optional[float],
    distribution: Optional[float],
    context_features: Optional[float],
    cfg: Config,
) -> dict[str, Optional[float]]:
    fingerprint_weight_total = (
        cfg.identity_weight + cfg.distribution_weight + cfg.context_feature_weight
    )
    identity_share = (
        cfg.identity_weight / fingerprint_weight_total if fingerprint_weight_total > 0 else 0.0
    )
    distribution_share = (
        cfg.distribution_weight / fingerprint_weight_total if fingerprint_weight_total > 0 else 0.0
    )
    context_share = (
        cfg.context_feature_weight / fingerprint_weight_total if fingerprint_weight_total > 0 else 0.0
    )

    raw = {
        "profile_weighted_contribution": (
            cfg.profile_weight * profile if profile is not None else None
        ),
        "reference_identity_weighted_contribution": (
            (1.0 - cfg.profile_weight) * identity_share * identity
            if identity is not None else None
        ),
        "reference_distribution_weighted_contribution": (
            (1.0 - cfg.profile_weight) * distribution_share * distribution
            if distribution is not None else None
        ),
        "reference_context_feature_weighted_contribution": (
            (1.0 - cfg.profile_weight) * context_share * context_features
            if context_features is not None else None
        ),
    }
    available = {k: v for k, v in raw.items() if v is not None}
    total = sum(available.values())
    for key, value in available.items():
        raw[key.replace("_weighted_contribution", "_contribution_fraction")] = (
            value / total if total > 0 else None
        )
    return raw



CONTEXT_DIMENSIONS = [
    ("prototype_family", "prototype family"),
    ("structural_regime", "structural regime"),
    ("material_family", "material family"),
    ("formula_family", "formula family"),
    ("crystal_system", "crystal system"),
    ("space_group", "space group"),
]


def _display_value(value: Any) -> Optional[str]:
    text_value = clean_text(value)
    return text_value if text_value else None


def _format_decimal(value: Any, digits: int = 3) -> str:
    number = safe_float(value)
    return "unavailable" if number is None else f"{number:.{digits}f}"


def _format_percent(value: Any, digits: int = 0) -> str:
    number = safe_float(value)
    return "unavailable" if number is None else f"{100.0 * number:.{digits}f}%"


def contextual_agreement_details(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return value-driven contextual agreements and disagreements for one pair."""
    agreements: list[str] = []
    disagreements: list[str] = []
    unavailable: list[str] = []
    checklist: list[str] = []

    for prefix, label in CONTEXT_DIMENSIONS:
        a = _display_value(row.get(f"candidate_a_{prefix}"))
        b = _display_value(row.get(f"candidate_b_{prefix}"))
        agreement = row.get(f"{prefix}_agreement")

        if a is None or b is None or agreement is None or pd.isna(agreement):
            unavailable.append(label)
            checklist.append(f"? {label}: unavailable")
            continue

        if bool(agreement):
            agreements.append(f"{label}: {a}")
            checklist.append(f"✓ {label}: {a}")
        else:
            disagreements.append(f"{label}: {a} versus {b}")
            checklist.append(f"✗ {label}: {a} versus {b}")

    return {
        "contextual_agreements": agreements,
        "contextual_disagreements": disagreements,
        "contextual_unavailable": unavailable,
        "contextual_agreement_checklist": checklist,
    }


def entropy_interpretation(row: Mapping[str, Any]) -> str:
    """Translate entropy evidence into a cautious human-readable comparison."""
    field_labels = [
        ("prototype_entropy_normalised", "prototype"),
        ("material_family_entropy_normalised", "material-family"),
        ("formula_family_entropy_normalised", "formula-family"),
        ("space_group_entropy_normalised", "space-group"),
    ]

    available: list[tuple[str, float, float, float]] = []
    for field, label in field_labels:
        a = safe_float(row.get(f"candidate_a_{field}"))
        b = safe_float(row.get(f"candidate_b_{field}"))
        if a is None or b is None:
            continue
        available.append((label, a, b, abs(a - b)))

    if not available:
        return "Neighbourhood-diversity interpretation is unavailable because entropy fields were not populated."

    mean_difference = sum(item[3] for item in available) / len(available)
    if mean_difference < 0.03:
        opening = "The two neighbourhoods have very similar diversity patterns."
    elif mean_difference < 0.12:
        opening = "The two neighbourhoods show modest differences in diversity."
    else:
        opening = "The two neighbourhoods show substantial differences in diversity."

    largest = max(available, key=lambda item: item[3])
    label, a_value, b_value, difference = largest

    consistency_notes: list[str] = []
    for current_label, a, b, _ in available:
        mean_value = (a + b) / 2.0
        if mean_value <= 0.15:
            consistency_notes.append(
                f"{current_label} assignments are highly concentrated in both neighbourhoods"
            )
        elif mean_value >= 0.70:
            consistency_notes.append(
                f"{current_label} assignments are diverse in both neighbourhoods"
            )

    parts = [opening]
    if difference >= 0.03:
        parts.append(
            f"The largest difference is in {label} diversity "
            f"({_format_decimal(a_value)} versus {_format_decimal(b_value)})."
        )
    if consistency_notes:
        parts.append(consistency_notes[0].capitalize() + ".")
    return " ".join(parts)


def profile_neighbourhood_interpretation(row: Mapping[str, Any]) -> str:
    profile = safe_float(row.get("profile_similarity"))
    neighbourhood = safe_float(row.get("reference_neighbourhood_similarity"))
    discordance = safe_float(row.get("profile_neighbourhood_discordance"))

    if profile is None or neighbourhood is None:
        return "Profile-to-neighbourhood consistency could not be assessed."

    if discordance is None:
        discordance = abs(profile - neighbourhood)

    if discordance < 0.05:
        return (
            "The compressed Structural Context Profile is consistent with the "
            "full reference-neighbourhood evidence."
        )
    if profile >= neighbourhood:
        return (
            "The compressed profile is more similar than the underlying "
            "reference neighbourhoods, indicating that profile compression hides "
            "some relational differences."
        )
    return (
        "The reference neighbourhoods are more similar than the compressed profiles, "
        "indicating that the profile emphasises differences not dominant in the "
        "retrieved-neighbour evidence."
    )


def dominant_similarity_driver(row: Mapping[str, Any]) -> str:
    components = [
        ("profile", safe_float(row.get("profile_contribution_fraction"))),
        (
            "ranked reference identities",
            safe_float(row.get("reference_identity_contribution_fraction")),
        ),
        (
            "neighbourhood-category distributions",
            safe_float(row.get("reference_distribution_contribution_fraction")),
        ),
        (
            "pool-context features",
            safe_float(row.get("reference_context_feature_contribution_fraction")),
        ),
    ]
    available = [(label, value) for label, value in components if value is not None]
    if not available:
        return "No dominant similarity component could be identified."
    label, value = max(available, key=lambda item: item[1])
    return (
        f"The largest weighted contribution comes from {label} "
        f"({_format_percent(value)} of the available combined contribution)."
    )


def scientific_pair_interpretation(row: Mapping[str, Any]) -> str:
    details = contextual_agreement_details(row)
    agreement_count = int(safe_float(row.get("context_signature_agreement_count")) or 0)
    comparable_count = int(safe_float(row.get("context_signature_comparable_dimensions")) or 0)
    agreements = details["contextual_agreements"]
    disagreements = details["contextual_disagreements"]

    parts: list[str] = []

    if comparable_count:
        parts.append(
            f"The contextual signatures agree in {agreement_count} of "
            f"{comparable_count} comparable dimensions."
        )

    if agreements:
        parts.append(
            "Shared signals include " + "; ".join(agreements[:3]) + "."
        )

    if disagreements:
        parts.append(
            "The principal reported differences are "
            + "; ".join(disagreements[:3])
            + "."
        )

    parts.append(dominant_similarity_driver(row))
    parts.append(profile_neighbourhood_interpretation(row))
    parts.append(entropy_interpretation(row))

    confidence = _display_value(row.get("similarity_confidence_label")) or "unreported"
    parts.append(
        f"The evidence confidence attached to this explanation is {confidence}."
    )
    return " ".join(parts)


def pair_explanation_short(row: Mapping[str, Any]) -> str:
    """Produce a concise value-driven explanation suitable for CSV scanning."""
    details = contextual_agreement_details(row)
    agreements = details["contextual_agreements"]
    disagreements = details["contextual_disagreements"]

    neighbourhood = safe_float(row.get("reference_neighbourhood_similarity"))
    identity = safe_float(row.get("reference_identity_similarity"))
    distribution = safe_float(row.get("reference_distribution_similarity"))

    parts: list[str] = []
    if neighbourhood is not None:
        if neighbourhood >= 0.95:
            parts.append("The retrieved reference neighbourhoods are very similar")
        elif neighbourhood >= 0.80:
            parts.append("The retrieved reference neighbourhoods are substantially similar")
        elif neighbourhood <= 0.50:
            parts.append("The retrieved reference neighbourhoods are markedly different")
        else:
            parts.append("The retrieved reference neighbourhoods show partial similarity")

    if agreements:
        parts.append("shared signals: " + "; ".join(agreements[:3]))
    if disagreements:
        parts.append("differences: " + "; ".join(disagreements[:2]))

    if identity is not None and identity >= 0.90:
        parts.append("ranked reference identities overlap strongly")
    elif identity is not None and identity <= 0.50:
        parts.append("ranked reference identities overlap weakly")

    if distribution is not None and distribution >= 0.90:
        parts.append("neighbourhood-category distributions are closely aligned")
    elif distribution is not None and distribution <= 0.60:
        parts.append("neighbourhood-category distributions differ")

    if not parts:
        parts.append("The available similarity components are closely balanced")

    confidence = _display_value(row.get("similarity_confidence_label")) or "unreported"
    return "; ".join(parts) + f". Evidence confidence: {confidence}."


def cluster_entropy_summary(
    representative_fp: Mapping[str, Any],
) -> str:
    signature = fingerprint_signature(representative_fp)
    values = {
        "prototype": safe_float(signature.get("prototype_entropy_normalised")),
        "material-family": safe_float(signature.get("material_family_entropy_normalised")),
        "formula-family": safe_float(signature.get("formula_family_entropy_normalised")),
        "space-group": safe_float(signature.get("space_group_entropy_normalised")),
    }
    available = {key: value for key, value in values.items() if value is not None}
    if not available:
        return "Entropy interpretation unavailable."

    lowest_name, lowest_value = min(available.items(), key=lambda item: item[1])
    highest_name, highest_value = max(available.items(), key=lambda item: item[1])

    return (
        f"The representative neighbourhood is most concentrated at the "
        f"{lowest_name} level ({lowest_value:.3f}) and most diverse at the "
        f"{highest_name} level ({highest_value:.3f})."
    )


def cluster_scientific_interpretation(
    cluster_id: Any,
    members: Sequence[str],
    representative: str,
    representative_fp: Mapping[str, Any],
    mean_similarity: float,
    mean_confidence: Optional[float],
) -> str:
    prototype = dominant_signature_label(
        representative_fp, "dominant_prototype_family"
    )
    regime = dominant_signature_label(
        representative_fp, "dominant_structural_regime"
    )
    material = dominant_signature_label(
        representative_fp, "dominant_material_family"
    )
    formula = dominant_signature_label(
        representative_fp, "dominant_formula_family"
    )
    space_group = dominant_signature_label(
        representative_fp, "dominant_space_group"
    )

    signals: list[str] = []
    if prototype:
        signals.append(f"prototype family {prototype}")
    if regime:
        signals.append(f"structural regime {regime}")
    if material:
        signals.append(f"material family {material}")
    if formula:
        signals.append(f"formula family {formula}")

    opening = (
        f"Cluster {cluster_id} contains {len(members)} candidates and is represented "
        f"by {representative}."
    )
    if signals:
        opening += " Its representative neighbourhood is dominated by " + ", ".join(signals) + "."

    similarity_text = (
        f" Mean within-cluster similarity is {mean_similarity:.3f},"
        f" with mean explanation confidence "
        f"{_format_decimal(mean_confidence)}."
    )

    crystallography = (
        f" The dominant space-group signal is {space_group}."
        if space_group
        else ""
    )

    return (
        opening
        + similarity_text
        + crystallography
        + " "
        + cluster_entropy_summary(representative_fp)
        + " This is a reference-relative description and not a physical classification."
    )


def build_pair_explanation(row: Mapping[str, Any]) -> str:
    return pair_explanation_short(row)


def pair_explainability_output(pairwise: pd.DataFrame) -> pd.DataFrame:
    if pairwise.empty:
        return pairwise.copy()
    preferred = [
        "candidate_a", "candidate_b",
        "combined_context_similarity", "reference_neighbourhood_similarity",
        "profile_similarity", "reference_identity_similarity",
        "reference_distribution_similarity",
        "reference_context_feature_similarity",
        "similarity_confidence", "similarity_confidence_label",
        "candidate_a_explainability_coverage",
        "candidate_b_explainability_coverage",
        "context_signature_agreement_count",
        "context_signature_comparable_dimensions",
        "context_signature_agreement_fraction",
        "contextual_agreements",
        "contextual_disagreements",
        "contextual_agreement_checklist",
        "mean_entropy_absolute_difference",
        "entropy_interpretation",
        "dominant_similarity_driver",
        "profile_neighbourhood_interpretation",
        "pair_explanation",
        "scientific_interpretation",
    ]
    remaining = [c for c in pairwise.columns if c not in preferred]
    return pairwise[[c for c in preferred if c in pairwise.columns] + remaining].copy()


def cluster_explainability_output(
    assignments: pd.DataFrame,
    representatives: pd.DataFrame,
    fingerprints: Mapping[str, Mapping[str, Any]],
    pairwise: pd.DataFrame,
) -> pd.DataFrame:
    if assignments.empty:
        return pd.DataFrame()

    representative_map = {}
    if not representatives.empty:
        for row in representatives.to_dict("records"):
            representative_map[row.get("cluster_id")] = row.get("representative_candidate_id")

    rows: list[dict[str, Any]] = []
    for cluster_id, group in assignments.groupby("cluster_id"):
        members = [str(v) for v in group["candidate_id"].tolist()]
        representative = str(representative_map.get(cluster_id) or members[0])
        fp = fingerprints.get(representative, {})
        signature = fingerprint_signature(fp)
        context = signature.get("context_signature", {})
        narrative = context.get("narrative") if isinstance(context, Mapping) else None

        within = pairwise[
            pairwise["candidate_a"].isin(members)
            & pairwise["candidate_b"].isin(members)
        ]
        mean_similarity = (
            float(within["combined_context_similarity"].mean())
            if not within.empty else 1.0
        )
        mean_confidence = (
            float(within["similarity_confidence"].mean())
            if not within.empty and "similarity_confidence" in within.columns else None
        )
        mean_signature_agreement = (
            float(within["context_signature_agreement_fraction"].mean())
            if not within.empty
            and "context_signature_agreement_fraction" in within.columns
            else None
        )
        mean_entropy_difference = (
            float(within["mean_entropy_absolute_difference"].mean())
            if not within.empty
            and "mean_entropy_absolute_difference" in within.columns
            else None
        )

        scientific_interpretation = cluster_scientific_interpretation(
            cluster_id=cluster_id,
            members=members,
            representative=representative,
            representative_fp=fp,
            mean_similarity=mean_similarity,
            mean_confidence=mean_confidence,
        )

        rows.append({
            "cluster_id": cluster_id,
            "cluster_size": len(members),
            "cluster_members": " | ".join(members),
            "representative_candidate_id": representative,
            "mean_within_cluster_similarity": mean_similarity,
            "mean_similarity_confidence": mean_confidence,
            "mean_context_signature_agreement": mean_signature_agreement,
            "mean_entropy_absolute_difference": mean_entropy_difference,
            "dominant_prototype_family": dominant_signature_label(
                fp, "dominant_prototype_family"
            ),
            "dominant_structural_regime": dominant_signature_label(
                fp, "dominant_structural_regime"
            ),
            "dominant_material_family": dominant_signature_label(
                fp, "dominant_material_family"
            ),
            "dominant_formula_family": dominant_signature_label(
                fp, "dominant_formula_family"
            ),
            "dominant_crystal_system": dominant_signature_label(
                fp, "dominant_crystal_system"
            ),
            "dominant_space_group": dominant_signature_label(
                fp, "dominant_space_group"
            ),
            "context_narrative": narrative,
            "entropy_interpretation": cluster_entropy_summary(fp),
            "scientific_interpretation": scientific_interpretation,
            "interpretation": scientific_interpretation,
        })
    return pd.DataFrame(rows)



def candidate_reliability(row: pd.Series, inventory_row: Mapping[str, Any]) -> float:
    values: list[float] = []
    for field in RELIABILITY_FIELDS:
        val = clip01(row.get(field))
        if val is not None:
            values.append(val)
    fp_complete = clip01(inventory_row.get("fingerprint_completeness"))
    if fp_complete is not None:
        values.append(fp_complete)
    return float(sum(values) / len(values)) if values else 0.0


def pair_reliability(a: float, b: float) -> float:
    return math.sqrt(max(0.0, a) * max(0.0, b))


def calculate_pair(
    cid_a: str,
    cid_b: str,
    row_a: pd.Series,
    row_b: pd.Series,
    fp_a: Mapping[str, Any],
    fp_b: Mapping[str, Any],
    reliability_a: float,
    reliability_b: float,
    cfg: Config,
) -> dict[str, Any]:
    prof = profile_similarity(row_a, row_b)
    identity, all_jaccard, identity_details = reference_identity_similarity(fp_a, fp_b, cfg)
    distribution, distribution_details = reference_distribution_similarity(fp_a, fp_b, cfg)
    context_features, context_details = reference_context_feature_similarity(fp_a, fp_b, cfg)
    fingerprint = weighted_mean([
        (identity, cfg.identity_weight),
        (distribution, cfg.distribution_weight),
        (context_features, cfg.context_feature_weight),
    ])
    combined = weighted_mean([
        (prof, cfg.profile_weight),
        (fingerprint, 1.0 - cfg.profile_weight),
    ])
    chemistry = chemistry_baseline_similarity(row_a, row_b, fp_a, fp_b)
    reliability = pair_reliability(reliability_a, reliability_b)
    similarity_confidence, similarity_confidence_label, coverage_a, coverage_b = (
        pair_explainability_confidence(fp_a, fp_b, reliability)
    )
    signature_details = compare_context_signatures(fp_a, fp_b)
    entropy_details = compare_entropy(fp_a, fp_b)
    decomposition = similarity_decomposition(
        prof, identity, distribution, context_features, cfg
    )
    discordance = abs(prof - fingerprint) if prof is not None and fingerprint is not None else None

    if prof is not None and fingerprint is not None:
        if prof >= 0.90 and fingerprint <= 0.50:
            discordance_type = "similar_profile_different_reference_neighbourhood"
        elif prof <= 0.65 and fingerprint >= 0.85:
            discordance_type = "different_profile_similar_reference_neighbourhood"
        elif prof > fingerprint:
            discordance_type = "profile_similarity_exceeds_neighbourhood_similarity"
        elif fingerprint > prof:
            discordance_type = "neighbourhood_similarity_exceeds_profile_similarity"
        else:
            discordance_type = "aligned"
    else:
        discordance_type = "insufficient_components"

    result = {
        "candidate_a": cid_a,
        "candidate_b": cid_b,
        "profile_similarity": prof,
        "reference_identity_similarity": identity,
        "all_reference_id_jaccard": all_jaccard,
        "reference_distribution_similarity": distribution,
        "reference_context_feature_similarity": context_features,
        "reference_neighbourhood_similarity": fingerprint,
        "combined_context_similarity": combined,
        "combined_context_distance": None if combined is None else 1.0 - combined,
        "chemistry_baseline_similarity": chemistry,
        "pair_reliability": reliability,
        "similarity_confidence": similarity_confidence,
        "similarity_confidence_label": similarity_confidence_label,
        "candidate_a_explainability_coverage": coverage_a,
        "candidate_b_explainability_coverage": coverage_b,
        "profile_neighbourhood_discordance": discordance,
        "discordance_type": discordance_type,
    }
    result.update(decomposition)
    result.update(signature_details)
    result.update(entropy_details)
    agreement_details = contextual_agreement_details(result)
    result["contextual_agreements"] = " | ".join(
        agreement_details["contextual_agreements"]
    )
    result["contextual_disagreements"] = " | ".join(
        agreement_details["contextual_disagreements"]
    )
    result["contextual_agreement_checklist"] = " | ".join(
        agreement_details["contextual_agreement_checklist"]
    )
    result["entropy_interpretation"] = entropy_interpretation(result)
    result["profile_neighbourhood_interpretation"] = (
        profile_neighbourhood_interpretation(result)
    )
    result["dominant_similarity_driver"] = dominant_similarity_driver(result)
    result["scientific_interpretation"] = scientific_pair_interpretation(result)
    result["pair_explanation"] = build_pair_explanation(result)
    result.update(identity_details)
    result.update({
        k: v for k, v in distribution_details.items()
        if k.endswith("_distribution_similarity") and k.count("_") <= 4
    })
    result.update(context_details)
    return result


def build_pairwise(
    work: pd.DataFrame,
    fingerprints: Mapping[str, Mapping[str, Any]],
    reliability: Mapping[str, float],
    cfg: Config,
) -> tuple[pd.DataFrame, list[str], dict[str, np.ndarray]]:
    ids = [cid for cid in work["candidate_id"].tolist() if cid in fingerprints]
    n = len(ids)
    if n > cfg.max_exact_candidates:
        raise ValueError(
            f"{n} fingerprint-complete candidates exceed --max_exact_candidates={cfg.max_exact_candidates}. "
            "This Phase 1C.2 implementation uses exact O(n^2) comparisons; use a smaller cohort or raise the limit deliberately."
        )
    index = work.set_index("candidate_id", drop=False)
    matrices = {
        "profile": np.eye(n, dtype=float),
        "identity": np.eye(n, dtype=float),
        "distribution": np.eye(n, dtype=float),
        "context_features": np.eye(n, dtype=float),
        "fingerprint": np.eye(n, dtype=float),
        "combined": np.eye(n, dtype=float),
        "chemistry": np.eye(n, dtype=float),
        "reliability": np.eye(n, dtype=float),
    }
    rows: list[dict[str, Any]] = []
    for i in range(n):
        cid_a = ids[i]
        for j in range(i + 1, n):
            cid_b = ids[j]
            pair = calculate_pair(
                cid_a,
                cid_b,
                index.loc[cid_a],
                index.loc[cid_b],
                fingerprints[cid_a],
                fingerprints[cid_b],
                reliability[cid_a],
                reliability[cid_b],
                cfg,
            )
            rows.append(pair)
            values = {
                "profile": pair["profile_similarity"],
                "identity": pair["reference_identity_similarity"],
                "distribution": pair["reference_distribution_similarity"],
                "context_features": pair["reference_context_feature_similarity"],
                "fingerprint": pair["reference_neighbourhood_similarity"],
                "combined": pair["combined_context_similarity"],
                "chemistry": pair["chemistry_baseline_similarity"],
                "reliability": pair["pair_reliability"],
            }
            for key, value in values.items():
                matrices[key][i, j] = matrices[key][j, i] = np.nan if value is None else float(value)
    return pd.DataFrame(rows), ids, matrices


def fill_similarity_matrix(matrix: np.ndarray) -> np.ndarray:
    out = matrix.copy()
    finite = out[np.isfinite(out)]
    fill = float(np.nanmedian(finite)) if finite.size else 0.0
    out[~np.isfinite(out)] = fill
    np.fill_diagonal(out, 1.0)
    return np.clip(out, 0.0, 1.0)


def choose_clusters(distance: np.ndarray, cfg: Config) -> tuple[int, np.ndarray, list[dict[str, Any]], Optional[np.ndarray]]:
    n = len(distance)
    if n == 0:
        return 0, np.array([], dtype=int), [], None
    if n == 1:
        return 1, np.array([1], dtype=int), [], None
    condensed = squareform(distance, checks=False)
    link = linkage(condensed, method="average")
    if cfg.n_clusters is not None:
        k = min(cfg.n_clusters, n)
        labels = fcluster(link, t=k, criterion="maxclust")
        return len(np.unique(labels)), labels, [], link
    if n < 3:
        return 1, np.ones(n, dtype=int), [], link
    upper = min(cfg.max_clusters, n - 1)
    diagnostics: list[dict[str, Any]] = []
    best_score = -math.inf
    best_labels = np.ones(n, dtype=int)
    best_k = 1
    for k in range(2, upper + 1):
        labels = fcluster(link, t=k, criterion="maxclust")
        unique = np.unique(labels)
        if len(unique) < 2 or len(unique) >= n:
            continue
        score = float(silhouette_score(distance, labels, metric="precomputed"))
        diagnostics.append({"requested_clusters": k, "actual_clusters": int(len(unique)), "silhouette_score": score})
        if score > best_score:
            best_score = score
            best_k = int(len(unique))
            best_labels = labels
    return best_k, best_labels, diagnostics, link


def classical_mds(distance: np.ndarray, dimensions: int = 2) -> np.ndarray:
    n = len(distance)
    if n == 0:
        return np.empty((0, dimensions))
    if n == 1:
        return np.zeros((1, dimensions))
    d2 = distance ** 2
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ d2 @ centering
    values, vectors = np.linalg.eigh(gram)
    order = np.argsort(values)[::-1]
    values = values[order]
    vectors = vectors[:, order]
    positive = np.maximum(values[:dimensions], 0.0)
    coords = vectors[:, :dimensions] * np.sqrt(positive)
    if coords.shape[1] < dimensions:
        coords = np.pad(coords, ((0, 0), (0, dimensions - coords.shape[1])))
    return coords


def write_matrix(path: Path, ids: Sequence[str], matrix: np.ndarray) -> None:
    df = pd.DataFrame(matrix, index=ids, columns=ids)
    df.index.name = "candidate_id"
    df.to_csv(path)


def nearest_neighbours(
    ids: Sequence[str],
    matrices: Mapping[str, np.ndarray],
    top_k: int,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    meta = metadata.set_index("candidate_id", drop=False)
    combined = fill_similarity_matrix(matrices["combined"])
    rows: list[dict[str, Any]] = []
    k = min(top_k, max(0, len(ids) - 1))
    for i, cid in enumerate(ids):
        order = np.argsort(-combined[i])
        order = [j for j in order if j != i][:k]
        for rank, j in enumerate(order, start=1):
            nid = ids[j]
            rows.append({
                "candidate_id": cid,
                "candidate_formula": meta.loc[cid].get("formula", meta.loc[cid].get("profile_formula", "")),
                "neighbour_rank": rank,
                "neighbour_id": nid,
                "neighbour_formula": meta.loc[nid].get("formula", meta.loc[nid].get("profile_formula", "")),
                "combined_context_similarity": combined[i, j],
                "combined_context_distance": 1.0 - combined[i, j],
                "profile_similarity": matrices["profile"][i, j],
                "reference_neighbourhood_similarity": matrices["fingerprint"][i, j],
                "reference_identity_similarity": matrices["identity"][i, j],
                "reference_distribution_similarity": matrices["distribution"][i, j],
                "chemistry_baseline_similarity": matrices["chemistry"][i, j],
                "pair_reliability": matrices["reliability"][i, j],
            })
    return pd.DataFrame(rows)


def cluster_outputs(
    ids: Sequence[str],
    labels: np.ndarray,
    combined_distance: np.ndarray,
    work: pd.DataFrame,
    fingerprints: Mapping[str, Mapping[str, Any]],
    reliability: Mapping[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    index = work.set_index("candidate_id", drop=False)
    assignment_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    representative_rows: list[dict[str, Any]] = []
    for cid, label in zip(ids, labels):
        row = index.loc[cid]
        assignment_rows.append({
            "candidate_id": cid,
            "formula": row.get("formula", row.get("profile_formula", "")),
            "cluster_id": int(label),
            "candidate_reliability": reliability[cid],
            **{f: row.get(f) for f in CORE_PROFILE_FEATURES},
            "profile_chemical_system": row.get("profile_chemical_system"),
            "profile_composition_family": row.get("profile_composition_family"),
            "profile_formula_family": row.get("profile_formula_family"),
            "profile_prototype_family": row.get("profile_prototype_family"),
        })
    assignments = pd.DataFrame(assignment_rows)

    for cluster_id in sorted(set(int(x) for x in labels)):
        idx = np.where(labels == cluster_id)[0]
        sub = combined_distance[np.ix_(idx, idx)]
        mean_dist = sub.mean(axis=1) if len(idx) else np.array([])
        best_local = min(
            range(len(idx)),
            key=lambda local: (float(mean_dist[local]), -reliability[ids[int(idx[local])]]),
        )
        rep_global = int(idx[best_local])
        rep_id = ids[rep_global]
        cluster_ids = [ids[int(i)] for i in idx]
        cluster_df = assignments[assignments["cluster_id"] == cluster_id]
        reference_union: set[str] = set()
        for cid in cluster_ids:
            reference_union.update(
                clean_text(x)
                for x in fingerprints[cid].get("reference_neighbourhood", {}).get("all_unique_reference_ids", [])
                if clean_text(x)
            )
        within = [1.0 - sub[i, j] for i in range(len(idx)) for j in range(i + 1, len(idx))]
        summary_rows.append({
            "cluster_id": cluster_id,
            "cluster_size": len(cluster_ids),
            "representative_candidate_id": rep_id,
            "mean_within_cluster_similarity": float(np.mean(within)) if within else 1.0,
            "unique_reference_union_count": len(reference_union),
            "dominant_composition_family": dominant_value(cluster_df.get("profile_composition_family")),
            "dominant_formula_family": dominant_value(cluster_df.get("profile_formula_family")),
            "median_candidate_reliability": float(cluster_df["candidate_reliability"].median()),
            **{f"median_{field}": float(pd.to_numeric(cluster_df[field], errors="coerce").median()) for field in CORE_PROFILE_FEATURES},
        })
        representative_rows.append({
            "cluster_id": cluster_id,
            "representative_candidate_id": rep_id,
            "representative_formula": index.loc[rep_id].get("formula", index.loc[rep_id].get("profile_formula", "")),
            "mean_distance_to_cluster_members": float(mean_dist[best_local]),
            "candidate_reliability": reliability[rep_id],
            "cluster_size": len(cluster_ids),
        })
    return assignments, pd.DataFrame(summary_rows), pd.DataFrame(representative_rows)


def dominant_value(series: Any) -> str:
    if series is None:
        return ""
    s = pd.Series(series).dropna().astype(str)
    return s.value_counts().index[0] if not s.empty else ""


class UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {x: x for x in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def redundancy_outputs(pairwise: pd.DataFrame, ids: Sequence[str], cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    if pairwise.empty:
        return pd.DataFrame(), pd.DataFrame()
    mask = (
        pairwise["combined_context_similarity"].ge(cfg.redundancy_similarity)
        & pairwise["profile_similarity"].ge(cfg.redundancy_min_component_similarity)
        & pairwise["reference_neighbourhood_similarity"].ge(cfg.redundancy_min_component_similarity)
    )
    pairs = pairwise.loc[mask].copy().sort_values("combined_context_similarity", ascending=False)
    uf = UnionFind(ids)
    for row in pairs.itertuples(index=False):
        uf.union(row.candidate_a, row.candidate_b)
    groups: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        groups[uf.find(cid)].append(cid)
    group_rows: list[dict[str, Any]] = []
    group_id = 0
    for members in sorted((v for v in groups.values() if len(v) > 1), key=lambda x: (-len(x), x)):
        group_id += 1
        group_rows.append({
            "redundancy_group_id": group_id,
            "group_size": len(members),
            "candidate_ids": ";".join(sorted(members)),
        })
        if not pairs.empty:
            in_group = pairs["candidate_a"].isin(members) & pairs["candidate_b"].isin(members)
            pairs.loc[in_group, "redundancy_group_id"] = group_id
    if not pairs.empty and "redundancy_group_id" in pairs:
        pairs["redundancy_group_id"] = pairs["redundancy_group_id"].astype("Int64")
    return pairs, pd.DataFrame(group_rows)


def distinctiveness_output(ids: Sequence[str], combined_similarity: np.ndarray, top_k: int) -> pd.DataFrame:
    sim = fill_similarity_matrix(combined_similarity)
    rows: list[dict[str, Any]] = []
    k = min(top_k, max(1, len(ids) - 1))
    raw: list[float] = []
    for i, cid in enumerate(ids):
        others = np.delete(sim[i], i)
        nearest = np.sort(others)[::-1][:k]
        mean_distance = float(np.mean(1.0 - nearest)) if len(nearest) else 0.0
        nearest_distance = float(1.0 - nearest[0]) if len(nearest) else 0.0
        raw.append(mean_distance)
        rows.append({
            "candidate_id": cid,
            "nearest_candidate_distance": nearest_distance,
            "mean_distance_to_k_nearest": mean_distance,
            "k": k,
        })
    ranks = pd.Series(raw).rank(method="average", pct=True).tolist()
    for row, rank in zip(rows, ranks):
        row["contextual_distinctiveness_percentile"] = float(rank)
    return pd.DataFrame(rows).sort_values("contextual_distinctiveness_percentile", ascending=False)


def intercluster_output(
    ids: Sequence[str], labels: np.ndarray, combined_similarity: np.ndarray, cfg: Config
) -> pd.DataFrame:
    sim = fill_similarity_matrix(combined_similarity)
    rows: list[dict[str, Any]] = []
    clusters = sorted(set(int(x) for x in labels))
    for i, cid in enumerate(ids):
        own = int(labels[i])
        cluster_scores: dict[int, float] = {}
        for cluster in clusters:
            idx = [j for j, lab in enumerate(labels) if int(lab) == cluster and (j != i or cluster != own)]
            cluster_scores[cluster] = float(np.mean(sim[i, idx])) if idx else 1.0 if cluster == own else 0.0
        own_score = cluster_scores.get(own, 0.0)
        alternatives = [(score, cluster) for cluster, score in cluster_scores.items() if cluster != own]
        best_other_score, best_other_cluster = max(alternatives, default=(0.0, 0))
        margin = own_score - best_other_score
        rows.append({
            "candidate_id": cid,
            "assigned_cluster_id": own,
            "mean_similarity_to_assigned_cluster": own_score,
            "best_alternative_cluster_id": best_other_cluster,
            "mean_similarity_to_best_alternative_cluster": best_other_score,
            "cluster_membership_margin": margin,
            "intercluster_candidate": bool(margin <= cfg.transition_margin),
            "transition_margin_threshold": cfg.transition_margin,
        })
    return pd.DataFrame(rows).sort_values("cluster_membership_margin")


def coverage_summary(
    ids: Sequence[str],
    fingerprints: Mapping[str, Mapping[str, Any]],
    pairwise: pd.DataFrame,
    labels: np.ndarray,
) -> dict[str, Any]:
    union: set[str] = set()
    frequency: Counter[str] = Counter()
    per_candidate: dict[str, set[str]] = {}
    for cid in ids:
        refs = {
            clean_text(x)
            for x in fingerprints[cid].get("reference_neighbourhood", {}).get("all_unique_reference_ids", [])
            if clean_text(x)
        }
        per_candidate[cid] = refs
        union.update(refs)
        frequency.update(refs)
    exclusive = {
        cid: sum(1 for ref in refs if frequency[ref] == 1)
        for cid, refs in per_candidate.items()
    }
    counts = Counter(int(x) for x in labels)
    total = sum(counts.values())
    probs = [v / total for v in counts.values()] if total else []
    entropy = -sum(p * math.log(p) for p in probs if p > 0)
    effective_clusters = math.exp(entropy) if probs else 0.0

    correlations: dict[str, Any] = {}
    if not pairwise.empty:
        for target in ["profile_similarity", "reference_neighbourhood_similarity", "combined_context_similarity"]:
            valid = pairwise[["chemistry_baseline_similarity", target]].dropna()
            if len(valid) >= 3:
                rho, p = spearmanr(valid["chemistry_baseline_similarity"], valid[target])
                correlations[target] = {"spearman_rho": float(rho), "p_value": float(p), "pair_count": len(valid)}

    pair_stats: dict[str, Any] = {}
    if not pairwise.empty:
        for field in [
            "profile_similarity",
            "reference_identity_similarity",
            "reference_distribution_similarity",
            "reference_neighbourhood_similarity",
            "combined_context_similarity",
            "chemistry_baseline_similarity",
        ]:
            vals = pd.to_numeric(pairwise[field], errors="coerce").dropna()
            pair_stats[field] = {
                "count": int(len(vals)),
                "mean": float(vals.mean()) if len(vals) else None,
                "median": float(vals.median()) if len(vals) else None,
                "min": float(vals.min()) if len(vals) else None,
                "max": float(vals.max()) if len(vals) else None,
            }

    return {
        "candidate_count": len(ids),
        "reference_union_count": len(union),
        "mean_unique_references_per_candidate": float(np.mean([len(x) for x in per_candidate.values()])) if per_candidate else 0.0,
        "median_unique_references_per_candidate": float(np.median([len(x) for x in per_candidate.values()])) if per_candidate else 0.0,
        "candidate_exclusive_reference_counts": exclusive,
        "cluster_count": len(counts),
        "cluster_sizes": dict(sorted(counts.items())),
        "effective_cluster_count": effective_clusters,
        "pairwise_similarity_statistics": pair_stats,
        "chemistry_context_correlations": correlations,
        "most_frequent_reference_ids": [
            {"reference_id": ref, "candidate_count": count, "candidate_fraction": count / len(ids)}
            for ref, count in frequency.most_common(25)
        ],
    }


def review_table(work: pd.DataFrame, inventory: pd.DataFrame, reliability: Mapping[str, float], cfg: Config) -> pd.DataFrame:
    inv = inventory.set_index("candidate_id", drop=False) if not inventory.empty else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for row in work.itertuples(index=False):
        cid = row.candidate_id
        reasons: list[str] = []
        status = inv.loc[cid].get("status") if not inv.empty and cid in inv.index else "missing"
        if status != "compatible":
            reasons.append(f"fingerprint_{status}")
        if getattr(row, "missing_core_feature_count", 0) > 0:
            reasons.append("missing_core_profile_measurements")
        if bool(getattr(row, "low_profile_confidence", False)):
            reasons.append("low_profile_confidence")
        if bool(getattr(row, "low_retrieval_completeness", False)):
            reasons.append("low_retrieval_completeness")
        if reasons:
            rows.append({
                "candidate_id": cid,
                "formula": getattr(row, "formula", getattr(row, "profile_formula", "")),
                "candidate_reliability": reliability.get(cid, 0.0),
                "review_reasons": ";".join(reasons),
                "fingerprint_status": status,
                "included_in_clustering": bool(cfg.include_low_reliability and status == "compatible" and getattr(row, "missing_core_feature_count", 1) == 0),
            })
    columns = [
        "candidate_id", "formula", "candidate_reliability", "review_reasons",
        "fingerprint_status", "included_in_clustering",
    ]
    return pd.DataFrame(rows, columns=columns)


def markdown_table(df: pd.DataFrame, columns: Sequence[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_None._"
    subset = df.loc[:, [c for c in columns if c in df.columns]].head(max_rows).copy()
    headers = list(subset.columns)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in subset.itertuples(index=False, name=None):
        vals = []
        for value in row:
            if isinstance(value, float):
                vals.append("" if math.isnan(value) else f"{value:.4f}")
            else:
                vals.append(str(value).replace("|", "\\|") if value is not None else "")
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_report(
    path: Path,
    cfg: Config,
    work: pd.DataFrame,
    inventory: pd.DataFrame,
    eligible_ids: Sequence[str],
    cluster_summary: pd.DataFrame,
    representatives: pd.DataFrame,
    redundancy_pairs: pd.DataFrame,
    discordance: pd.DataFrame,
    distinctiveness: pd.DataFrame,
    intercluster: pd.DataFrame,
    coverage: Mapping[str, Any],
    cluster_diagnostics: Sequence[Mapping[str, Any]],
    pair_explainability: Optional[pd.DataFrame] = None,
    cluster_explanations: Optional[pd.DataFrame] = None,
) -> None:
    lines = [
        "# Candidate Context Analysis: Phase 1C.2",
        "",
        "## Scope",
        "",
        "This report compares candidates through both their Structural Context Profile measurements and the reference neighbourhoods that produced those measurements. It is reference-corpus dependent and does not predict physical performance, intrinsic novelty, synthesis success, or scientific value.",
        "",
        "## Run summary",
        "",
        f"- Input candidates: **{len(work)}**",
        f"- Compatible fingerprints: **{int((inventory['status'] == 'compatible').sum()) if not inventory.empty else 0}**",
        f"- Candidates included in clustering: **{len(eligible_ids)}**",
        f"- Selected clusters: **{len(cluster_summary)}**",
        f"- Redundancy pairs: **{len(redundancy_pairs)}**",
        f"- Reference IDs represented across analysed candidates: **{coverage.get('reference_union_count', 0)}**",
        "",
        "## Similarity model",
        "",
        f"Combined context similarity = {cfg.profile_weight:.2f} × profile similarity + {1-cfg.profile_weight:.2f} × reference-neighbourhood similarity.",
        "",
        f"Reference-neighbourhood similarity combines ranked reference identity ({cfg.identity_weight:.2f}), context-distribution similarity ({cfg.distribution_weight:.2f}), and pool-feature similarity ({cfg.context_feature_weight:.2f}); these three weights are normalised internally.",
        "",
        "Negative controls are " + ("included" if cfg.include_negative_control else "excluded") + " from the default neighbourhood similarity.",
        "",
        "## Cluster summary",
        "",
        markdown_table(cluster_summary, [
            "cluster_id", "cluster_size", "representative_candidate_id",
            "mean_within_cluster_similarity", "unique_reference_union_count",
            "dominant_composition_family", "dominant_formula_family",
        ]),
        "",
        "## Cluster representatives",
        "",
        markdown_table(representatives, [
            "cluster_id", "representative_candidate_id", "representative_formula",
            "mean_distance_to_cluster_members", "candidate_reliability",
        ]),
        "",
        "## Strongest contextual redundancy pairs",
        "",
        markdown_table(redundancy_pairs, [
            "candidate_a", "candidate_b", "combined_context_similarity",
            "profile_similarity", "reference_neighbourhood_similarity",
            "chemistry_baseline_similarity", "pair_reliability",
        ]),
        "",
        "## Profile–neighbourhood discordance",
        "",
        "These pairs are important because similar final profile scores can conceal different reference neighbourhoods, and vice versa.",
        "",
        markdown_table(discordance, [
            "candidate_a", "candidate_b", "profile_similarity",
            "reference_neighbourhood_similarity", "profile_neighbourhood_discordance",
            "discordance_type", "pair_reliability",
        ]),
        "",
        "## Most contextually distinctive candidates",
        "",
        markdown_table(distinctiveness, [
            "candidate_id", "nearest_candidate_distance", "mean_distance_to_k_nearest",
            "contextual_distinctiveness_percentile",
        ]),
        "",
        "## Inter-cluster candidates",
        "",
        markdown_table(intercluster[intercluster.get("intercluster_candidate", False) == True] if not intercluster.empty else intercluster, [
            "candidate_id", "assigned_cluster_id", "best_alternative_cluster_id",
            "cluster_membership_margin", "intercluster_candidate",
        ]),
        "",
        "## Candidate-relative coverage",
        "",
        f"- Effective cluster count: **{coverage.get('effective_cluster_count', 0):.3f}**",
        f"- Mean unique references per candidate: **{coverage.get('mean_unique_references_per_candidate', 0):.1f}**",
        f"- Median unique references per candidate: **{coverage.get('median_unique_references_per_candidate', 0):.1f}**",
        "",
        "## Cluster-count diagnostics",
        "",
        markdown_table(pd.DataFrame(cluster_diagnostics), ["requested_clusters", "actual_clusters", "silhouette_score"]),
        "",
        "## Similarity explainability",
        "",
        "The similarity score is unchanged. The confidence and decomposition fields below describe how strongly the available fingerprint evidence supports each comparison.",
        "",
        markdown_table(
            pair_explainability.sort_values("combined_context_similarity", ascending=False).head(15)
            if pair_explainability is not None and not pair_explainability.empty
            else pd.DataFrame(),
            [
                "candidate_a", "candidate_b", "combined_context_similarity",
                "similarity_confidence_label",
                "context_signature_agreement_fraction",
                "contextual_agreements",
                "contextual_disagreements",
                "entropy_interpretation",
                "dominant_similarity_driver",
                "scientific_interpretation",
            ],
        ),
        "",
        "## Cluster explanations",
        "",
        markdown_table(
            cluster_explanations if cluster_explanations is not None else pd.DataFrame(),
            [
                "cluster_id", "cluster_size", "representative_candidate_id",
                "mean_within_cluster_similarity", "mean_similarity_confidence",
                "mean_context_signature_agreement",
                "dominant_prototype_family", "dominant_structural_regime",
                "dominant_material_family", "dominant_formula_family",
                "dominant_crystal_system", "dominant_space_group",
                "entropy_interpretation", "scientific_interpretation",
            ],
        ),
        "",
        "## Interpretation limits",
        "",
        "- A cluster is a grouping under this specific corpus, retrieval procedure, fingerprint schema, and weighting configuration.",
        "- Contextual distinctiveness is not intrinsic material novelty.",
        "- Redundancy means similar reference-relative context, not interchangeable physical behaviour.",
        "- Low-reliability candidates should be reviewed before their apparent isolation or transition status is interpreted.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_map(path: Path, coords: np.ndarray, ids: Sequence[str], labels: np.ndarray, reliability: Sequence[float]) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    sizes = 35 + 90 * np.asarray(reliability)
    scatter = ax.scatter(coords[:, 0], coords[:, 1], c=labels, s=sizes, alpha=0.8)
    for x, y, cid in zip(coords[:, 0], coords[:, 1], ids):
        ax.annotate(cid, (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Reference-aware context coordinate 1")
    ax.set_ylabel("Reference-aware context coordinate 2")
    ax.set_title("Candidate Context Map (Phase 1C.2)")
    ax.grid(True, alpha=0.25)
    fig.colorbar(scatter, ax=ax, label="Cluster ID")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_profile_vs_neighbourhood(path: Path, pairwise: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    if not pairwise.empty:
        ax.scatter(
            pairwise["profile_similarity"],
            pairwise["reference_neighbourhood_similarity"],
            s=25 + 55 * pairwise["pair_reliability"].fillna(0.0),
            alpha=0.65,
        )
        ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Structural Context Profile similarity")
    ax.set_ylabel("Reference-neighbourhood similarity")
    ax.set_title("Profile Similarity vs Reference-Neighbourhood Similarity")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_dendrogram(path: Path, link: Optional[np.ndarray], ids: Sequence[str]) -> None:
    fig, ax = plt.subplots(figsize=(max(10, len(ids) * 0.42), 7))
    if link is not None and len(ids) > 1:
        dendrogram(link, labels=list(ids), leaf_rotation=90, leaf_font_size=7, ax=ax)
    else:
        ax.text(0.5, 0.5, "Insufficient candidates for a dendrogram", ha="center", va="center")
        ax.set_axis_off()
    ax.set_title("Reference-Aware Candidate Context Dendrogram")
    ax.set_ylabel("Combined context distance")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_component_summary(path: Path, pairwise: pd.DataFrame) -> None:
    fields = [
        "profile_similarity",
        "reference_identity_similarity",
        "reference_distribution_similarity",
        "reference_context_feature_similarity",
        "reference_neighbourhood_similarity",
        "combined_context_similarity",
        "chemistry_baseline_similarity",
    ]
    medians = [pd.to_numeric(pairwise[f], errors="coerce").median() if f in pairwise else np.nan for f in fields]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(len(fields)), medians)
    ax.set_xticks(range(len(fields)))
    ax.set_xticklabels([f.replace("_", " ") for f in fields], rotation=35, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Median pairwise similarity")
    ax.set_title("Candidate Context Similarity Components")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main(argv: Optional[Sequence[str]] = None) -> int:
    cfg = parse_args(argv)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    if not cfg.structural_context_summary.is_file():
        raise FileNotFoundError(f"Structural context summary not found: {cfg.structural_context_summary}")
    if not cfg.batch_output_root.is_dir():
        raise NotADirectoryError(f"Batch output root not found: {cfg.batch_output_root}")

    summary = pd.read_csv(cfg.structural_context_summary)
    work, source_id_column = prepare_summary(summary, cfg)
    mapping, discovery_inventory = discover_fingerprints(cfg.batch_output_root, cfg.fingerprint_name)
    fingerprints, inventory = load_fingerprints(work["candidate_id"].tolist(), mapping)

    inventory = work[["candidate_id"]].merge(inventory, on="candidate_id", how="left")
    inventory["status"] = inventory["status"].fillna("missing")
    inventory.to_csv(cfg.output_dir / "fingerprint_inventory.csv", index=False)
    pd.DataFrame(discovery_inventory).to_csv(cfg.output_dir / "fingerprint_discovery_log.csv", index=False)

    inventory_index = inventory.set_index("candidate_id", drop=False)
    reliability: dict[str, float] = {}
    for row in work.itertuples(index=False):
        cid = row.candidate_id
        inv_row = inventory_index.loc[cid].to_dict() if cid in inventory_index.index else {}
        reliability[cid] = candidate_reliability(pd.Series(row._asdict()), inv_row)
    work["candidate_reliability"] = work["candidate_id"].map(reliability)

    review = review_table(work, inventory, reliability, cfg)
    review.to_csv(cfg.output_dir / "candidate_context_review_table_1c2.csv", index=False)

    fingerprint_complete_ids = [cid for cid in work["candidate_id"] if cid in fingerprints]
    if len(fingerprint_complete_ids) < 2:
        raise ValueError("At least two compatible reference-neighbourhood fingerprints are required")

    pairwise, ids, matrices = build_pairwise(work, fingerprints, reliability, cfg)
    pairwise.to_csv(cfg.output_dir / "candidate_pairwise_context_similarity_1c2.csv", index=False)
    pair_explainability = pair_explainability_output(pairwise)
    pair_explainability.to_csv(
        cfg.output_dir / "candidate_pairwise_explainability_1c2.csv",
        index=False,
    )

    eligible_set = set(
        work.loc[
            work["candidate_id"].isin(fingerprint_complete_ids)
            & work["missing_core_feature_count"].eq(0)
            & (
                cfg.include_low_reliability
                | (
                    ~work["low_profile_confidence"]
                    & ~work["low_retrieval_completeness"]
                )
            ),
            "candidate_id",
        ]
    )
    eligible_indices = [i for i, cid in enumerate(ids) if cid in eligible_set]
    eligible_ids = [ids[i] for i in eligible_indices]
    if len(eligible_ids) < 2:
        raise ValueError("Fewer than two candidates are eligible for clustering after reliability checks")

    combined_similarity = fill_similarity_matrix(matrices["combined"])
    combined_distance = 1.0 - combined_similarity
    eligible_distance = combined_distance[np.ix_(eligible_indices, eligible_indices)]
    selected_k, eligible_labels, cluster_diagnostics, link = choose_clusters(eligible_distance, cfg)

    assignments, cluster_summary, representatives = cluster_outputs(
        eligible_ids,
        eligible_labels,
        eligible_distance,
        work,
        fingerprints,
        reliability,
    )
    assignments.to_csv(cfg.output_dir / "candidate_context_clusters_1c2.csv", index=False)
    cluster_summary.to_csv(cfg.output_dir / "cluster_summary_1c2.csv", index=False)
    representatives.to_csv(cfg.output_dir / "cluster_representatives_1c2.csv", index=False)
    cluster_explanations = cluster_explainability_output(
        assignments,
        representatives,
        fingerprints,
        pairwise,
    )
    cluster_explanations.to_csv(
        cfg.output_dir / "cluster_context_explanations_1c2.csv",
        index=False,
    )

    nearest = nearest_neighbours(ids, matrices, cfg.top_k, work)
    nearest.to_csv(cfg.output_dir / "nearest_contextual_neighbours_1c2.csv", index=False)

    redundancy_pairs, redundancy_groups = redundancy_outputs(pairwise, eligible_ids, cfg)
    redundancy_pairs.to_csv(cfg.output_dir / "candidate_redundancy_pairs_1c2.csv", index=False)
    redundancy_groups.to_csv(cfg.output_dir / "candidate_redundancy_groups_1c2.csv", index=False)

    discordance = pairwise.sort_values("profile_neighbourhood_discordance", ascending=False).copy()
    discordance.to_csv(cfg.output_dir / "profile_neighbourhood_discordance.csv", index=False)

    eligible_combined = matrices["combined"][np.ix_(eligible_indices, eligible_indices)]
    distinctiveness = distinctiveness_output(eligible_ids, eligible_combined, cfg.top_k)
    distinctiveness.to_csv(cfg.output_dir / "contextually_distinct_candidates_1c2.csv", index=False)

    intercluster = intercluster_output(eligible_ids, eligible_labels, eligible_combined, cfg)
    intercluster.to_csv(cfg.output_dir / "intercluster_candidates_1c2.csv", index=False)

    coverage = coverage_summary(eligible_ids, fingerprints, pairwise[
        pairwise["candidate_a"].isin(eligible_ids) & pairwise["candidate_b"].isin(eligible_ids)
    ], eligible_labels)
    write_json(cfg.output_dir / "candidate_context_coverage_1c2.json", coverage)

    coords = classical_mds(eligible_distance, 2)
    summary_rows = assignments.merge(
        distinctiveness[["candidate_id", "contextual_distinctiveness_percentile", "mean_distance_to_k_nearest"]],
        on="candidate_id",
        how="left",
    ).merge(
        intercluster[["candidate_id", "cluster_membership_margin", "intercluster_candidate"]],
        on="candidate_id",
        how="left",
    )
    coord_map = {cid: coords[i] for i, cid in enumerate(eligible_ids)}
    summary_rows["context_coordinate_1"] = summary_rows["candidate_id"].map(lambda x: coord_map[x][0])
    summary_rows["context_coordinate_2"] = summary_rows["candidate_id"].map(lambda x: coord_map[x][1])
    summary_rows.to_csv(cfg.output_dir / "candidate_context_summary_1c2.csv", index=False)

    matrix_written = False
    if cfg.matrix_mode == "full" or (
        cfg.matrix_mode == "auto" and len(ids) <= cfg.max_full_matrix_candidates
    ):
        write_matrix(cfg.output_dir / "combined_context_similarity_matrix_1c2.csv", ids, matrices["combined"])
        write_matrix(cfg.output_dir / "reference_neighbourhood_similarity_matrix_1c2.csv", ids, matrices["fingerprint"])
        write_matrix(cfg.output_dir / "profile_similarity_matrix_1c2.csv", ids, matrices["profile"])
        write_matrix(cfg.output_dir / "chemistry_baseline_similarity_matrix_1c2.csv", ids, matrices["chemistry"])
        matrix_written = True

    plot_map(
        cfg.output_dir / "candidate_context_map_1c2.png",
        coords,
        eligible_ids,
        eligible_labels,
        [reliability[cid] for cid in eligible_ids],
    )
    plot_profile_vs_neighbourhood(
        cfg.output_dir / "profile_vs_reference_neighbourhood_similarity.png",
        pairwise,
    )
    plot_dendrogram(cfg.output_dir / "candidate_context_dendrogram_1c2.png", link, eligible_ids)
    plot_component_summary(cfg.output_dir / "candidate_context_similarity_components.png", pairwise)

    write_report(
        cfg.output_dir / "candidate_context_report_1c2.md",
        cfg,
        work,
        inventory,
        eligible_ids,
        cluster_summary,
        representatives,
        redundancy_pairs,
        discordance,
        distinctiveness,
        intercluster,
        coverage,
        cluster_diagnostics,
        pair_explainability,
        cluster_explanations,
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "scope_note": (
            "Reference-relative Candidate Context Analysis. Explainability outputs do not alter similarity or clustering. "
            "Outputs do not predict physical properties, "
            "intrinsic novelty, synthesis success, or candidate value."
        ),
        "inputs": {
            "structural_context_summary": str(cfg.structural_context_summary),
            "batch_output_root": str(cfg.batch_output_root),
            "source_id_column": source_id_column,
            "fingerprint_name": cfg.fingerprint_name,
            "supported_fingerprint_schema": SUPPORTED_FINGERPRINT_SCHEMA,
        },
        "configuration": asdict(cfg),
        "counts": {
            "input_candidates": len(work),
            "compatible_fingerprints": len(fingerprints),
            "pairwise_comparisons": len(pairwise),
            "clustering_candidates": len(eligible_ids),
            "selected_clusters": selected_k,
            "redundancy_pairs": len(redundancy_pairs),
            "review_candidates": len(review),
        },
        "cluster_selection_diagnostics": cluster_diagnostics,
        "matrix_outputs_written": matrix_written,
        "outputs": sorted(p.name for p in cfg.output_dir.iterdir() if p.is_file()),
    }
    write_json(cfg.output_dir / "candidate_context_analysis_1c2.json", manifest)

    print("Phase 1C.2 Candidate Context Analysis complete.")
    print(f"Input candidates:            {len(work)}")
    print(f"Compatible fingerprints:     {len(fingerprints)}")
    print(f"Pairwise comparisons:        {len(pairwise)}")
    print(f"Candidates clustered:        {len(eligible_ids)}")
    print(f"Selected clusters:           {selected_k}")
    print(f"Redundancy pairs:            {len(redundancy_pairs)}")
    print(f"Review candidates:           {len(review)}")
    print(f"Output directory:            {cfg.output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
