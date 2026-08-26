"""
Role prior inference engine.

Overview
--------
This module converts inexpensive structural-context evidence into interpretable
role priors. It consumes the outputs of ``cheap_evidence_metrics.py`` and
produces Hub, Boundary and Other prior scores together with supporting
diagnostics.

Architectural responsibilities
------------------------------
* Interpret evidence rather than generate it.
* Preserve separation between evidence and inference.
* Produce transparent role scores and diagnostic descriptors.
* Expose confidence, ambiguity and evidence-quality indicators.
* Avoid expensive calculations.

Pipeline position
-----------------
material_profile_builder
    -> candidate_pool_builder
    -> cheap_evidence_metrics
    -> role_prior_engine
    -> reporting / validation

Developer guidance
------------------
Scoring logic should remain deterministic and version-controlled. Thresholds
should be documented, calibration changes justified, and new diagnostics added
without changing the meaning of existing outputs unless intentionally versioned.
"""
#!/usr/bin/env python3
from __future__ import annotations

"""
role_prior_engine.py

Structural Context Inference Engine for the cheap-context-first project.

This transition release preserves the frozen v1 Hub/Boundary calculations while
adding a v2 Structural Context Profile that treats Local Context Support and
Structural Regime Contrast as independent relational measurements.

Phase 4:
- Computes lightweight role priors for the three core roles: Hub / Bridge / Boundary.
- Treats Outlier and No Strong Role as quality/interpretive flags rather than primary roles.
- Separates role score, strength band, confidence, evidence sufficiency, supporting evidence, contradictions, and quality flags.

Phase 5:
- Produces a paste-ready Markdown report.
- Produces CSV summaries and a JSON evidence record.

Inputs:
- query_profile.json from Phase 1 v1.1/v1.2
- evidence directory from Phase 3

Outputs:
- role_prior_summary.json
- role_plausibility_table.csv
- role_ranking.csv
- role_ranked_explanations.csv
- role_contradictions.csv
- role_strength_table.csv
- role_quality_flags.csv
- structural_context_report.md
- structural_context_summary.csv
- structural_context_evidence_record.json
- role_prior_config_used.json
"""

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd


SCHEMA_VERSION = "phase4_5.structural_context_inference.v4.0_transition"
PROFILE_V2_SCHEMA_VERSION = "phase1.structural_context_profile.v2"


POOL_METRICS_FILE = "pool_level_metrics.csv"
SUMMARY_FILE = "cheap_evidence_summary.json"
METRICS_FILE = "cheap_evidence_metrics.csv"
MISSING_FILE = "missing_value_report.csv"

SCORING_ROLES = ["hub", "bridge", "boundary"]
PRIMARY_ROLES = ["hub", "boundary", "other"]
CORE_ROLES = PRIMARY_ROLES  # Backwards-compatible exported name for downstream readers.
QUALITY_INDICATOR_ROLES = ["bridge", "outlier"]


@dataclass
class RolePriorConfig:
    strong_threshold: float = 0.70
    partial_threshold: float = 0.45
    confidence_high_threshold: float = 0.70
    confidence_partial_threshold: float = 0.45
    no_strong_role_margin: float = 0.08

    # Strength bands for the three core roles. These are interpretation thresholds,
    # not hard scientific truth handed down from a mountain.
    very_strong_strength_threshold: float = 0.85
    strong_strength_threshold: float = 0.70
    moderate_strength_threshold: float = 0.55
    weak_strength_threshold: float = 0.35
    ambiguous_role_margin: float = 0.08
    possible_outlier_threshold: float = 0.45

    warning_missing_rate_threshold: float = 0.25
    warning_pool_overlap_threshold: int = 0

    # Evidence sufficiency gate. This is deliberately separate from role scoring:
    # the engine must first decide whether it has enough meaningful contextual
    # evidence to assign *any* role at all.
    evidence_sufficiency_threshold: float = 0.55
    minimum_anchor_strength: float = 0.35
    minimum_family_specificity: float = 0.25
    minimum_structural_specificity: float = 0.40
    minimum_specific_anchor_for_strong_role: float = 0.40
    role_separation_threshold: float = 0.08
    contradiction_penalty_weight: float = 0.035
    contradiction_penalty_cap: float = 0.25

    # Phase 1 decision-layer overrides.
    # These do not change Hub/Boundary evidence scores. They prevent strong
    # Hub/Boundary evidence from being demoted to Other solely because generic
    # context flags are present. Generic flags remain visible as caution flags.
    high_core_score_override_threshold: float = 0.70
    high_core_confidence_override_threshold: float = 0.60

    # Canonical high-symmetry prototype calibration.
    # Without this, boundary pools can dominate for canonical Fd-3m spinels because
    # boundary pools are deliberately constructed from symmetry-contrast candidates.
    canonical_hub_bonus_weight: float = 0.10
    canonical_boundary_score_penalty: float = 0.16
    canonical_boundary_penalty_min_hub_context: float = 0.80

    # Structural Context Profile v2 confidence weights. These affect only the
    # new profile-level reliability diagnostic, not the frozen Hub/Boundary scores.
    profile_confidence_evidence_weight: float = 0.30
    profile_confidence_retrieval_weight: float = 0.20
    profile_confidence_pool_independence_weight: float = 0.15
    profile_confidence_ambiguity_weight: float = 0.15
    profile_confidence_measurement_weight: float = 0.20
    profile_confidence_low_threshold: float = 0.35
    profile_confidence_high_threshold: float = 0.70

    # Role scoring weights. These are intentionally simple and transparent.
    hub_weights: Dict[str, float] = field(default_factory=lambda: {
        "same_family_pool_size": 0.15,
        "same_composition_match": 0.10,
        "same_material_match": 0.10,
        "same_formula_match": 0.20,
        "same_prototype_match": 0.20,
        "same_family_stable_fraction": 0.10,
        "same_family_known_synthesized": 0.05,
        "negative_control_separation": 0.10,
        "canonical_prototype_bonus": 0.10,
    })
    bridge_weights: Dict[str, float] = field(default_factory=lambda: {
        "adjacent_pool_size": 0.12,
        "adjacent_unique_systems": 0.18,
        "adjacent_element_overlap": 0.18,
        "adjacent_family_entropy": 0.12,
        "adjacent_prototype_entropy": 0.15,
        "adjacent_variant_entropy": 0.10,
        "cross_pool_overlap": 0.05,
        "negative_control_separation": 0.10,
    })
    boundary_weights: Dict[str, float] = field(default_factory=lambda: {
        "boundary_pool_size": 0.10,
        "same_formula_or_prototype_context": 0.20,
        "different_spacegroup": 0.18,
        "different_crystal_system": 0.12,
        "different_structure_variant": 0.15,
        "symmetry_distance": 0.12,
        "symmetry_entropy": 0.05,
        "boundary_stability": 0.08,
    })
    outlier_weights: Dict[str, float] = field(default_factory=lambda: {
        "low_same_family_support": 0.25,
        "low_adjacent_support": 0.20,
        "negative_control_similarity": 0.20,
        "low_family_match": 0.20,
        "high_missingness": 0.15,
    })


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip01(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        if isinstance(x, float) and math.isnan(x):
            return 0.0
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return 0.0


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, str) and not x.strip():
            return default
        v = float(x)
        if math.isnan(v):
            return default
        return v
    except Exception:
        return default


def _norm_count(value: Any, target: float) -> float:
    if target <= 0:
        return 0.0
    return _clip01(_safe_float(value) / target)


def _weighted_score(components: Dict[str, float], weights: Dict[str, float]) -> float:
    total = sum(max(0.0, float(w)) for w in weights.values())
    if total <= 0:
        return 0.0
    score = 0.0
    for k, w in weights.items():
        score += _clip01(components.get(k, 0.0)) * max(0.0, float(w))
    return _clip01(score / total)


def _plausibility(score: float, confidence: float, cfg: RolePriorConfig) -> str:
    if confidence < cfg.confidence_partial_threshold:
        return "insufficient_evidence"
    if score >= cfg.strong_threshold and confidence >= cfg.confidence_partial_threshold:
        return "supported"
    if score >= cfg.partial_threshold:
        return "partial"
    return "not_supported"


def _strength_band(score: float, confidence: float, evidence_sufficiency_status: str, cfg: RolePriorConfig) -> str:
    """Convert a role score into an interpretable strength band.

    Insufficient global evidence no longer automatically erases strong
    Hub/Boundary-like evidence. If the score is high enough, the role can still
    be reported as moderate/strong with caution flags; otherwise it remains
    insufficient.
    """
    if evidence_sufficiency_status == "insufficient" and _clip01(score) < cfg.high_core_score_override_threshold:
        return "insufficient_evidence"
    if confidence < cfg.confidence_partial_threshold:
        return "insufficient_evidence"
    score = _clip01(score)
    confidence = _clip01(confidence)
    if score >= cfg.very_strong_strength_threshold and confidence >= cfg.confidence_high_threshold:
        return "very_strong"
    if score >= cfg.strong_strength_threshold:
        return "strong"
    if score >= cfg.moderate_strength_threshold:
        return "moderate"
    if score >= cfg.weak_strength_threshold:
        return "weak"
    return "very_weak"


def _strength_rank(strength: str) -> int:
    order = {
        "very_weak": 0,
        "weak": 1,
        "moderate": 2,
        "strong": 3,
        "very_strong": 4,
        "insufficient_evidence": -1,
    }
    return order.get(str(strength), -1)


def _quality_flag(flag: str, severity: str, reason: str, value: Any = None) -> Dict[str, Any]:
    return {
        "flag": flag,
        "severity": severity,
        "reason": reason,
        "value": value,
    }


def _confidence_from_metrics(pool_rows: List[Dict[str, Any]], missing_report: pd.DataFrame, cfg: RolePriorConfig) -> float:
    if not pool_rows:
        return 0.0
    pool_names = [str(r.get("pool_name")) for r in pool_rows]
    sizes = [_safe_float(r.get("n_candidates")) for r in pool_rows]
    size_quality = sum(1.0 for s in sizes if s > 0) / max(len(sizes), 1)

    missing_rates: List[float] = []
    if not missing_report.empty and "pool_name" in missing_report.columns and "missing_rate" in missing_report.columns:
        sub = missing_report[missing_report["pool_name"].astype(str).isin(pool_names)]
        if not sub.empty:
            missing_rates = [_safe_float(x) for x in sub["missing_rate"].tolist()]
    avg_missing = sum(missing_rates) / len(missing_rates) if missing_rates else 0.0
    missing_quality = 1.0 - _clip01(avg_missing)

    required_missing_col = "missing_required_columns"
    required_quality = 1.0
    bad_required = 0
    for r in pool_rows:
        val = r.get(required_missing_col)
        if val not in (None, "", "[]", [], float("nan")):
            if str(val).strip() not in ("[]", "nan", "None"):
                bad_required += 1
    if bad_required:
        required_quality = max(0.0, 1.0 - bad_required / max(len(pool_rows), 1))

    return _clip01(0.45 * size_quality + 0.35 * missing_quality + 0.20 * required_quality)


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _pool_row_map(pool_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if pool_df.empty or "pool_name" not in pool_df.columns:
        return {}
    return {str(row["pool_name"]): row.to_dict() for _, row in pool_df.iterrows()}


def _get(row_map: Dict[str, Dict[str, Any]], pool: str, metric: str, default: float = 0.0) -> float:
    return _safe_float(row_map.get(pool, {}).get(metric), default=default)


def _evidence_item(text: str, value: Any = None) -> Dict[str, Any]:
    return {"text": text, "value": value}


def _label_specificity(*labels: Any) -> float:
    """Return 0..1 estimate of whether family labels are specific enough to classify.

    Composition-only labels such as oxide/intermetallic are useful for filtering, but
    should not by themselves justify a strong structural-context role. More specific
    labels such as ABO3/perovskite_like/distorted_perovskite get higher credit.
    """
    generic = {
        "", "none", "null", "nan", "unknown", "generic", "other",
        "oxide", "chalcogenide", "sulfide", "selenide", "telluride",
        "intermetallic", "metal", "alloy", "organic", "molecular", "halide",
    }
    score = 0.0
    weights = [0.35, 0.45, 0.20]  # formula, prototype, variant
    for label, weight in zip(labels, weights):
        if label is None:
            continue
        text = str(label).strip().lower()
        if text and text not in generic and not text.startswith("unknown"):
            score += weight
    return _clip01(score)


def _structural_specificity(prototype_family: Any, structure_variant: Any) -> float:
    """Return 0..1 estimate of structure-specific context.

    Formula labels such as ABO3 or AB2 are useful, but they can still describe very broad
    stoichiometric classes. Strong non-outlier role assignment should normally require
    prototype or variant evidence, not formula alone.
    """
    return _label_specificity(None, prototype_family, structure_variant)



def _is_canonical_high_symmetry_hub_candidate(query: Dict[str, Any]) -> bool:
    """Detect cases where boundary evidence should not automatically dominate.

    The current use case is canonical cubic spinels: Fd-3m entries such as MgAl2O4,
    Co3O4, Fe3O4, and LiMn2O4. Their boundary pools are expected to contain many
    lower-symmetry variants, but that should not make the canonical prototype itself
    boundary-primary when same-family evidence is strong.
    """
    proto = str(query.get("prototype_family") or "").strip().lower()
    variant = str(query.get("structure_variant") or "").strip().lower()
    spg = int(_safe_float(query.get("spacegroup_number"), default=-1))

    if proto in {"spinel_like", "spinel", "normal_spinel", "inverse_spinel"}:
        if spg == 227 or "cubic" in variant:
            return True

    # Conservative extension for already-supported families. This helps canonical
    # cubic references without relaxing the evidence-sufficiency gate.
    if proto in {"perovskite_like", "fluorite_related"} and "cubic" in variant:
        return True

    return False


def _apply_context_gate_to_role(
    role: str,
    plausibility: str,
    score: float,
    family_specificity: float,
    structural_specificity: float,
    anchor_strength: float,
    cfg: RolePriorConfig,
) -> str:
    """Apply context cautions without destroying strong Hub/Boundary evidence.

    This function does not change raw scores. In earlier versions, generic family
    or structural context could suppress high-scoring Hub/Boundary cases into
    unsupported outcomes. Phase 1 now treats those issues as quality flags unless
    the Hub/Boundary score itself is weak. Bridge and outlier remain diagnostics.
    """
    if role == "outlier":
        return plausibility
    if plausibility not in {"supported", "partial"}:
        return plausibility

    # Strong Hub/Boundary evidence is allowed through with caution flags. This is
    # the key decision-layer fix: generic_overclaim_risk should warn reviewers,
    # not automatically turn a high-scoring Hub/Boundary into Other.
    if role in {"hub", "boundary"} and _clip01(score) >= cfg.high_core_score_override_threshold:
        return plausibility

    if family_specificity < cfg.minimum_family_specificity:
        return "not_supported_due_to_generic_context"
    if structural_specificity < cfg.minimum_structural_specificity:
        return "not_supported_due_to_weak_structural_context"
    if anchor_strength < cfg.minimum_specific_anchor_for_strong_role:
        return "not_supported_due_to_weak_anchor"
    return plausibility


def _role_specific_confidence(
    base_confidence: float,
    score: float,
    contradiction_count: int,
    family_specificity: float,
    structural_specificity: float,
    anchor_strength: float,
    role_gap: float,
    all_missing_rate: float,
) -> float:
    """Convert broad data-quality confidence into role-specific confidence."""
    specificity_quality = _clip01(0.35 * family_specificity + 0.45 * structural_specificity + 0.20 * anchor_strength)
    contradiction_quality = max(0.0, 1.0 - 0.10 * max(0, int(contradiction_count)))
    separation_quality = _clip01(role_gap / 0.25) if role_gap is not None else 0.0
    missing_quality = 1.0 - _clip01(all_missing_rate)
    return _clip01(
        0.30 * _clip01(base_confidence)
        + 0.25 * specificity_quality
        + 0.15 * _clip01(score)
        + 0.15 * contradiction_quality
        + 0.10 * separation_quality
        + 0.05 * missing_quality
    )


def _safe_gap(top_score: float, second_score: float) -> float:
    return max(0.0, _safe_float(top_score) - _safe_float(second_score))

def _mean_available(values: Iterable[Any]) -> float:
    vals: List[float] = []
    for v in values:
        try:
            if v is None:
                continue
            f = float(v)
            if math.isnan(f):
                continue
            vals.append(_clip01(f))
        except Exception:
            continue
    if not vals:
        return 0.0
    return _clip01(sum(vals) / len(vals))


def _balance_pair(a: Any, b: Any) -> float:
    """High when two available 0..1 signals are both strong and similar."""
    af = _safe_float(a, default=float("nan"))
    bf = _safe_float(b, default=float("nan"))
    if math.isnan(af) or math.isnan(bf):
        return 0.0
    af = _clip01(af)
    bf = _clip01(bf)
    return _clip01(min(af, bf) * (1.0 - abs(af - bf)))


def _normalized_entropy(values: Iterable[Any]) -> float:
    vals: List[float] = []
    for v in values:
        f = _safe_float(v, default=float("nan"))
        if not math.isnan(f) and f > 0:
            vals.append(float(f))
    if len(vals) <= 1:
        return 0.0
    total = sum(vals)
    if total <= 0:
        return 0.0
    probs = [v / total for v in vals if v > 0]
    entropy = -sum(p * math.log(p) for p in probs)
    return _clip01(entropy / math.log(len(probs)))


def _summary_metric_or_none(evidence_summary: Dict[str, Any], key: str) -> Optional[float]:
    """Read optional bridge/other diagnostics from newer cheap-evidence output.

    Falls back cleanly when older evidence directories are used. This keeps the
    stable Hub/Boundary scoring path unchanged while allowing richer Phase 1
    diagnostics. A rare compromise that does not immediately start a fire.
    """
    if not isinstance(evidence_summary, dict):
        return None
    for section_name in ("diagnostics", "concept_values", "bridge_evidence_profile"):
        section = evidence_summary.get(section_name, {})
        if isinstance(section, dict) and key in section:
            val = section.get(key)
            try:
                if val is None:
                    return None
                f = float(val)
                if math.isnan(f):
                    return None
                return _clip01(f)
            except Exception:
                return None
    role_signal = evidence_summary.get("role_signal_summary", {})
    if isinstance(role_signal, dict):
        bridge_ind = role_signal.get("bridge_indicators", {})
        if isinstance(bridge_ind, dict) and key in bridge_ind:
            return _clip01(_safe_float(bridge_ind.get(key)))
    return None


def _descriptor_row(descriptor: str, strength: str, reason: str, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "descriptor": descriptor,
        "strength": strength,
        "reason": reason,
        "metrics": metrics or {},
    }




def _clean_scalar(value: Any) -> Any:
    """Return JSON-friendly scalar values for profile outputs."""
    try:
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null"}:
        return None
    return text


def _profile_pool_row(pool_df: pd.DataFrame, pool_name: str) -> Dict[str, Any]:
    if pool_df.empty or "pool_name" not in pool_df.columns:
        return {}
    sub = pool_df[pool_df["pool_name"].astype(str) == pool_name]
    if sub.empty:
        return {}
    return {k: _clean_scalar(v) for k, v in sub.iloc[0].to_dict().items()}


def _profile_pool_summary(pool_df: pd.DataFrame, pool_name: str) -> Dict[str, Any]:
    r = _profile_pool_row(pool_df, pool_name)
    if not r:
        return {
            "pool_name": pool_name,
            "available": False,
            "size": 0,
        }
    # Prototype purity and family purity are deliberately descriptive proxies.
    # They summarise the retrieval evidence; they do not change role scoring.
    return {
        "pool_name": pool_name,
        "available": True,
        "size": int(_safe_float(r.get("n_candidates"), 0.0)),
        "empty_pool": bool(r.get("empty_pool")) if r.get("empty_pool") is not None else None,
        "dominant_chemical_system": r.get("dominant_chemical_system"),
        "dominant_composition_family": r.get("dominant_composition_family"),
        "dominant_formula_family": r.get("dominant_formula_family"),
        "dominant_prototype_family": r.get("dominant_prototype_family"),
        "dominant_structure_variant": r.get("dominant_structure_variant"),
        "dominant_spacegroup_number": r.get("dominant_spacegroup_number"),
        "dominant_spacegroup_symbol": r.get("dominant_spacegroup_symbol"),
        "dominant_crystal_system_code": r.get("dominant_crystal_system_code"),
        "same_formula_family_rate": _safe_float(r.get("same_formula_family_rate"), 0.0),
        "same_prototype_family_rate": _safe_float(r.get("same_prototype_family_rate"), 0.0),
        "same_structure_variant_rate": _safe_float(r.get("same_structure_variant_rate"), 0.0),
        "same_spacegroup_rate": _safe_float(r.get("same_spacegroup_rate"), 0.0),
        "same_crystal_system_rate": _safe_float(r.get("same_crystal_system_rate"), 0.0),
        "chemical_system_count": int(_safe_float(r.get("chemical_system_count"), 0.0)),
        "composition_family_count": int(_safe_float(r.get("composition_family_count"), 0.0)),
        "formula_family_count": int(_safe_float(r.get("formula_family_count"), 0.0)),
        "prototype_family_count": int(_safe_float(r.get("prototype_family_count"), 0.0)),
        "structure_variant_count": int(_safe_float(r.get("structure_variant_count"), 0.0)),
        "spacegroup_count": int(_safe_float(r.get("spacegroup_count"), 0.0)),
        "crystal_system_count": int(_safe_float(r.get("crystal_system_count"), 0.0)),
        "formula_family_entropy": _safe_float(r.get("formula_family_entropy"), 0.0),
        "prototype_family_entropy": _safe_float(r.get("prototype_family_entropy"), 0.0),
        "structure_variant_entropy": _safe_float(r.get("structure_variant_entropy"), 0.0),
        "spacegroup_entropy": _safe_float(r.get("spacegroup_entropy"), 0.0),
        "crystal_system_entropy": _safe_float(r.get("crystal_system_entropy"), 0.0),
        "query_similarity_score": _safe_float(r.get("query_similarity_score"), 0.0),
        "pool_diversity_score": _safe_float(r.get("pool_diversity_score"), 0.0),
        "structural_regime_diversity_score": _safe_float(r.get("structural_regime_diversity_score"), 0.0),
        "stable_fraction_ehull_le_0_1": _safe_float(r.get("stable_fraction_ehull_le_0_1"), 0.0),
        "known_synthesized_rate": _safe_float(r.get("known_synthesized_rate"), 0.0),
        "energy_above_hull_missing_rate": _safe_float(r.get("energy_above_hull_missing_rate"), 0.0),
        "known_synthesized_missing_rate": _safe_float(r.get("known_synthesized_missing_rate"), 0.0),
        "duplicate_candidate_count": int(_safe_float(r.get("duplicate_candidate_count"), 0.0)),
        "duplicate_formula_count": int(_safe_float(r.get("duplicate_formula_count"), 0.0)),
        "missing_required_columns": r.get("missing_required_columns"),
    }


def _profile_pool_context_summary(query: Dict[str, Any], evidence_summary: Dict[str, Any], pool_df: pd.DataFrame) -> Dict[str, Any]:
    # Prefer the Phase 3 Pool Context Summary when available. This keeps the
    # Structural Context Profile grounded in the evidence stage, while preserving
    # backward compatibility with older evidence directories that only contain
    # pool_level_metrics.csv.
    if isinstance(evidence_summary, dict):
        precomputed = evidence_summary.get("pool_context_summary")
        if isinstance(precomputed, dict) and precomputed:
            return precomputed

    pools = {
        name: _profile_pool_summary(pool_df, name)
        for name in ["same_family", "adjacent_family", "boundary_contrast", "wildcard", "negative_control"]
    }
    role_signal = evidence_summary.get("role_signal_summary", {}) if isinstance(evidence_summary, dict) else {}
    overlap = evidence_summary.get("overlap_summary", {}) if isinstance(evidence_summary, dict) else {}

    same = pools.get("same_family", {})
    boundary = pools.get("boundary_contrast", {})
    adjacent = pools.get("adjacent_family", {})
    neg = pools.get("negative_control", {})

    return {
        "retrieval_summary": {
            "reference_database": "JARVIS or configured Phase 1 material store",
            "query_jid": query.get("jid"),
            "external_id": query.get("external_id"),
            "formula": query.get("formula"),
            "chemical_system": query.get("chemical_system"),
            "composition_family": query.get("composition_family"),
            "formula_family": query.get("formula_family"),
            "prototype_family": query.get("prototype_family"),
            "structure_variant": query.get("structure_variant"),
            "spacegroup_number": query.get("spacegroup_number"),
            "spacegroup_symbol": query.get("spacegroup_symbol"),
            "candidate_retrieval_strategy": "same-family, adjacent-family, boundary-contrast, wildcard, and negative-control pools",
        },
        "structural_neighbourhood": {
            "same_family_pool_size": same.get("size", 0),
            "adjacent_family_pool_size": adjacent.get("size", 0),
            "boundary_contrast_pool_size": boundary.get("size", 0),
            "wildcard_pool_size": pools.get("wildcard", {}).get("size", 0),
            "negative_control_pool_size": neg.get("size", 0),
            "candidate_ids_in_multiple_pools": _safe_float(overlap.get("candidate_ids_in_multiple_pools"), 0.0) if isinstance(overlap, dict) else 0.0,
            "unique_candidate_count_across_all_pools": _safe_float(overlap.get("unique_candidate_count_across_all_pools"), 0.0) if isinstance(overlap, dict) else 0.0,
            "pairwise_candidate_overlap_counts": overlap.get("pairwise_candidate_overlap_counts", {}) if isinstance(overlap, dict) else {},
        },
        "neighbourhood_characterisation": {
            "same_family": same,
            "adjacent_family": adjacent,
            "boundary_contrast": boundary,
            "wildcard": pools.get("wildcard", {}),
            "negative_control": neg,
        },
        "context_evidence_summary": {
            "strongest_supporting_neighbourhood": "same_family" if _safe_float(same.get("query_similarity_score"), 0.0) >= _safe_float(boundary.get("query_similarity_score"), 0.0) else "boundary_contrast",
            "same_family_query_similarity_score": _safe_float(same.get("query_similarity_score"), 0.0),
            "adjacent_family_query_similarity_score": _safe_float(adjacent.get("query_similarity_score"), 0.0),
            "boundary_contrast_query_similarity_score": _safe_float(boundary.get("query_similarity_score"), 0.0),
            "negative_control_query_similarity_score": _safe_float(neg.get("query_similarity_score"), 0.0),
            "negative_control_separation_proxy": _clip01(1.0 - _safe_float(neg.get("query_similarity_score"), 0.0)),
            "retrieval_completeness_proxy": _clip01(_mean_available([
                _norm_count(same.get("size", 0), 500),
                _norm_count(adjacent.get("size", 0), 500),
                _norm_count(boundary.get("size", 0), 500),
                _norm_count(neg.get("size", 0), 100),
            ])),
            "role_signal_summary": role_signal,
            "overlap_summary": overlap,
        },
    }


def _context_strength_label(value: Any) -> str:
    v = _clip01(_safe_float(value, 0.0))
    if v >= 0.85:
        return "very_high"
    if v >= 0.70:
        return "high"
    if v >= 0.55:
        return "moderate"
    if v >= 0.35:
        return "low"
    return "very_low"


def _profile_context_measurements(
    hub_score: float,
    boundary_score: float,
    hub_confidence: float,
    boundary_confidence: float,
    evidence_sufficiency: Dict[str, Any],
    hub_boundary_diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    ambiguity = _clip01(1.0 - _safe_float(hub_boundary_diagnostics.get("absolute_hub_boundary_score_gap"), 0.0) / 0.25)
    neighbourhood_coherence = _clip01(_mean_available([
        hub_boundary_diagnostics.get("hub_same_family_coherence_proxy"),
        hub_boundary_diagnostics.get("hub_prototype_dominance_proxy"),
    ]))
    structural_diversity = _clip01(_mean_available([
        1.0 - _safe_float(hub_boundary_diagnostics.get("hub_same_family_coherence_proxy"), 0.0),
        _safe_float(hub_boundary_diagnostics.get("boundary_regime_separation_proxy"), 0.0),
    ]))
    return {
        "hub_strength": round(_clip01(hub_score), 6),
        "hub_strength_band": _context_strength_label(hub_score),
        "boundary_strength": round(_clip01(boundary_score), 6),
        "boundary_strength_band": _context_strength_label(boundary_score),
        "evidence_sufficiency": evidence_sufficiency,
        "evidence_sufficiency_score": evidence_sufficiency.get("score"),
        "evidence_sufficiency_status": evidence_sufficiency.get("status"),
        "neighbourhood_coherence": round(neighbourhood_coherence, 6),
        "context_ambiguity": round(ambiguity, 6),
        "context_ambiguity_band": _context_strength_label(ambiguity),
        "structural_diversity": round(structural_diversity, 6),
        "hub_boundary_score_gap": hub_boundary_diagnostics.get("signed_hub_minus_boundary_score_gap"),
        "absolute_hub_boundary_score_gap": hub_boundary_diagnostics.get("absolute_hub_boundary_score_gap"),
        "hub_confidence": round(_clip01(hub_confidence), 6),
        "boundary_confidence": round(_clip01(boundary_confidence), 6),
    }


def _profile_interpretation(record_like: Dict[str, Any]) -> Dict[str, Any]:
    final = record_like.get("final_assessment", {})
    case = record_like.get("case_diagnostic_summary", {})
    role_summary = record_like.get("role_explanation_summary", {})
    return {
        "primary_interpretation": final.get("primary_role"),
        "primary_interpretation_strength": final.get("primary_role_strength"),
        "primary_interpretation_score": final.get("primary_role_score"),
        "secondary_interpretation": final.get("secondary_role"),
        "secondary_descriptors": final.get("secondary_descriptors", []),
        "interpretation_rationale": {
            "hub_support_summary": role_summary.get("hub_support_summary") or case.get("hub_support_summary"),
            "hub_rejection_summary": role_summary.get("hub_rejection_summary") or case.get("hub_rejection_summary"),
            "boundary_support_summary": role_summary.get("boundary_support_summary") or case.get("boundary_support_summary"),
            "boundary_rejection_summary": role_summary.get("boundary_rejection_summary") or case.get("boundary_rejection_summary"),
            "hub_boundary_comparison_summary": role_summary.get("hub_boundary_comparison_summary"),
            "secondary_descriptor_explanation": role_summary.get("secondary_descriptor_explanation") or case.get("secondary_descriptor_explanation"),
            "other_classification_reason": role_summary.get("other_classification_reason") or case.get("other_classification_reason"),
        },
    }


def _profile_diagnostics(record_like: Dict[str, Any]) -> Dict[str, Any]:
    final = record_like.get("final_assessment", {})
    case = record_like.get("case_diagnostic_summary", {})
    return {
        "context_quality": {
            "classification_quality": final.get("classification_quality"),
            "primary_role_confidence": final.get("primary_role_confidence"),
            "evidence_sufficiency_status": record_like.get("evidence_sufficiency", {}).get("status"),
            "evidence_sufficiency_score": record_like.get("evidence_sufficiency", {}).get("score"),
        },
        "quality_flags": final.get("quality_flags", []),
        "quality_flag_details": record_like.get("quality_flags", []),
        "review_flags": {
            "no_strong_role_supported": final.get("no_strong_role_supported"),
            "possible_outlier": final.get("possible_outlier"),
            "ambiguous_core_roles": final.get("ambiguous_core_roles"),
            "hub_boundary_ambiguity_flag": case.get("hub_boundary_ambiguity_flag"),
        },
        "acceptance_diagnostics": {
            "phase1_status": "diagnostic_only_not_a_classification_gate",
            "review_recommendation": final.get("review_recommendation") or case.get("review_recommendation"),
        },
        "provenance": {
            "schema_version": record_like.get("schema_version"),
            "created_at_utc": record_like.get("created_at_utc"),
            "phase1_schema_version": record_like.get("inputs", {}).get("phase1_schema_version"),
            "phase3_schema_version": record_like.get("inputs", {}).get("phase3_schema_version"),
        },
    }



def _pool_independence(pool_context_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate pool independence from observed cross-pool candidate reuse.

    This is a reliability diagnostic. It does not alter Local Context Support or
    Structural Regime Contrast. A value of 1 means no retrieved candidate ID was
    reused across pools; 0 means overlap is at least as large as the unique
    candidate count. The raw overlap fields remain available for audit.
    """
    structural = pool_context_summary.get("structural_neighbourhood", {}) or {}
    repeated = max(0.0, _safe_float(structural.get("candidate_ids_in_multiple_pools"), 0.0))
    unique = max(0.0, _safe_float(structural.get("unique_candidate_count_across_all_pools"), 0.0))
    overlap_rate = _clip01(repeated / unique) if unique > 0 else 0.0
    return {
        "score": round(_clip01(1.0 - overlap_rate), 6),
        "pool_overlap_rate": round(overlap_rate, 6),
        "candidate_ids_in_multiple_pools": int(repeated),
        "unique_candidate_count_across_all_pools": int(unique),
        "definition": (
            "Inverse of the proportion of unique retrieved candidate IDs that occur in more than one pool. "
            "This is a pragmatic transition metric, not a final statistical independence test."
        ),
    }


def _profile_confidence_v2(
    evidence_sufficiency_score: Any,
    retrieval_completeness: Any,
    pool_independence_score: Any,
    context_ambiguity: Any,
    local_context_support_confidence: Any,
    structural_regime_contrast_confidence: Any,
    cfg: RolePriorConfig,
) -> Dict[str, Any]:
    """Compute confidence in the profile as a reference-relative inference.

    Formula (all components clipped to [0, 1]):
      0.30 * evidence sufficiency
    + 0.20 * retrieval completeness
    + 0.15 * pool independence
    + 0.15 * (1 - context ambiguity)
    + 0.20 * mean(two measurement confidences)

    This is intentionally distinct from the legacy primary-role confidence.
    """
    evidence = _clip01(evidence_sufficiency_score)
    retrieval = _clip01(retrieval_completeness)
    independence = _clip01(pool_independence_score)
    ambiguity_complement = _clip01(1.0 - _clip01(context_ambiguity))
    local_conf = _clip01(local_context_support_confidence)
    contrast_conf = _clip01(structural_regime_contrast_confidence)
    measurement_conf = _clip01((local_conf + contrast_conf) / 2.0)

    weights = {
        "evidence_sufficiency": max(0.0, cfg.profile_confidence_evidence_weight),
        "retrieval_completeness": max(0.0, cfg.profile_confidence_retrieval_weight),
        "pool_independence": max(0.0, cfg.profile_confidence_pool_independence_weight),
        "ambiguity_complement": max(0.0, cfg.profile_confidence_ambiguity_weight),
        "measurement_confidence_mean": max(0.0, cfg.profile_confidence_measurement_weight),
    }
    components = {
        "evidence_sufficiency": evidence,
        "retrieval_completeness": retrieval,
        "pool_independence": independence,
        "ambiguity_complement": ambiguity_complement,
        "measurement_confidence_mean": measurement_conf,
        "local_context_support_confidence": local_conf,
        "structural_regime_contrast_confidence": contrast_conf,
    }
    total_weight = sum(weights.values()) or 1.0
    score = sum(components[k] * w for k, w in weights.items()) / total_weight
    score = _clip01(score)
    if score >= cfg.profile_confidence_high_threshold:
        band = "high"
    elif score >= cfg.profile_confidence_low_threshold:
        band = "moderate"
    else:
        band = "low"
    return {
        "score": round(score, 6),
        "band": band,
        "components": {k: round(v, 6) for k, v in components.items()},
        "weights": {k: round(v / total_weight, 6) for k, v in weights.items()},
        "formula": (
            "weighted_mean(evidence_sufficiency, retrieval_completeness, pool_independence, "
            "1-context_ambiguity, mean(local_context_support_confidence, "
            "structural_regime_contrast_confidence))"
        ),
        "scope_note": (
            "Confidence in the reliability of the reference-relative profile under the selected corpus and "
            "retrieval method; not confidence in physical behaviour or scientific value."
        ),
    }


def _contextual_pattern_v2(
    local_context_support: float,
    structural_regime_contrast: float,
    profile_confidence: float,
    evidence_status: Any,
) -> Dict[str, Any]:
    """Create a joint, non-exclusive interpretation of the two core dimensions."""
    support = _clip01(local_context_support)
    contrast = _clip01(structural_regime_contrast)
    confidence = _clip01(profile_confidence)
    high = 0.70
    moderate = 0.55

    if str(evidence_status).lower() == "insufficient" or confidence < 0.35:
        code = "reliability_limited_context"
        label = "Reliability-limited structural context"
        summary = "The relational measurements are reported, but the available evidence does not support a robust interpretation."
    elif support >= high and contrast >= high:
        code = "well_supported_contrast_rich"
        label = "Well-supported, contrast-rich context"
        summary = "The candidate is strongly anchored in a coherent reference neighbourhood while related references also span distinct structural regimes."
    elif support >= high and contrast < moderate:
        code = "well_supported_low_contrast"
        label = "Well-supported, comparatively uniform context"
        summary = "The candidate is strongly represented by a coherent reference neighbourhood with limited structural-regime contrast."
    elif support < moderate and contrast >= high:
        code = "sparse_contrast_rich"
        label = "Sparse, contrast-rich context"
        summary = "The candidate has limited local contextual support but substantial contrast among retained related references."
    elif support < moderate and contrast < moderate:
        code = "weakly_contextualised"
        label = "Weakly contextualised in the selected corpus"
        summary = "Neither strong local support nor strong structural-regime contrast is established in the selected reference corpus."
    else:
        code = "mixed_context"
        label = "Mixed structural context"
        summary = "The candidate shows an intermediate combination of local support and structural-regime contrast."

    return {
        "code": code,
        "label": label,
        "summary": summary,
        "hub_like_interpretation": support >= high,
        "boundary_like_interpretation": contrast >= high,
        "interpretation_rule_version": "joint_context_quadrants.v1",
        "thresholds": {"high": high, "moderate": moderate, "minimum_profile_confidence": 0.35},
    }


def _build_structural_context_profile_v2(
    *,
    query: Dict[str, Any],
    query_profile: Dict[str, Any],
    evidence_summary: Dict[str, Any],
    pool_df: pd.DataFrame,
    legacy_profile: Dict[str, Any],
    cfg: RolePriorConfig,
    created_at_utc: str,
) -> Dict[str, Any]:
    """Build the v2 profile without changing any frozen v1 score calculation."""
    pool_context = legacy_profile.get("pool_context_summary", {}) or {}
    legacy_measurements = legacy_profile.get("measurements", {}) or {}
    pool_independence = _pool_independence(pool_context)
    retrieval = _clip01(
        (pool_context.get("context_evidence_summary", {}) or {}).get("retrieval_completeness_proxy")
    )
    evidence_score = _clip01(legacy_measurements.get("evidence_sufficiency_score"))
    ambiguity = _clip01(legacy_measurements.get("context_ambiguity"))
    local_support = _clip01(legacy_measurements.get("hub_strength"))
    contrast = _clip01(legacy_measurements.get("boundary_strength"))
    local_conf = _clip01(legacy_measurements.get("hub_confidence"))
    contrast_conf = _clip01(legacy_measurements.get("boundary_confidence"))
    profile_confidence = _profile_confidence_v2(
        evidence_sufficiency_score=evidence_score,
        retrieval_completeness=retrieval,
        pool_independence_score=pool_independence.get("score"),
        context_ambiguity=ambiguity,
        local_context_support_confidence=local_conf,
        structural_regime_contrast_confidence=contrast_conf,
        cfg=cfg,
    )
    pattern = _contextual_pattern_v2(
        local_context_support=local_support,
        structural_regime_contrast=contrast,
        profile_confidence=profile_confidence.get("score", 0.0),
        evidence_status=legacy_measurements.get("evidence_sufficiency_status"),
    )

    return {
        "schema_version": PROFILE_V2_SCHEMA_VERSION,
        "created_at_utc": created_at_utc,
        "schema_status": "transition_release",
        "scope_and_provenance": {
            "scope_note": (
                "A reference-relative description of how the candidate is represented within the selected structural corpus. "
                "It is not an intrinsic material property, physical-property prediction, synthesis prediction, novelty claim, "
                "DFT replacement, or candidate-ranking recommendation."
            ),
            "reference_corpus": evidence_summary.get("reference_corpus") or evidence_summary.get("dataset") or "not_recorded",
            "phase1_input_schema_version": query_profile.get("schema_version"),
            "phase3_input_schema_version": evidence_summary.get("schema_version"),
            "inference_engine_schema_version": SCHEMA_VERSION,
            "measurement_compatibility_note": (
                "Local Context Support equals the frozen v1 hub_strength calculation; Structural Regime Contrast equals the "
                "frozen v1 boundary_strength calculation; Structural Context Diversity equals the frozen v1 structural_diversity "
                "calculation in this transition release."
            ),
        },
        "query_material": query,
        "pool_context_summary": pool_context,
        "relational_measurements": {
            "local_context_support": round(local_support, 6),
            "local_context_support_band": legacy_measurements.get("hub_strength_band") or _context_strength_label(local_support),
            "local_context_support_confidence": round(local_conf, 6),
            "structural_regime_contrast": round(contrast, 6),
            "structural_regime_contrast_band": legacy_measurements.get("boundary_strength_band") or _context_strength_label(contrast),
            "structural_regime_contrast_confidence": round(contrast_conf, 6),
            "neighbourhood_coherence": legacy_measurements.get("neighbourhood_coherence"),
            "structural_context_diversity": legacy_measurements.get("structural_diversity"),
            "structural_context_diversity_status": "provisional_retained_v1_aggregation",
            "structural_context_diversity_definition": (
                "Transition metric retained unchanged from v1: mean of inverse same-family coherence and boundary-regime separation. "
                "Its aggregation must be documented and validated before being treated as a final scientific measurement."
            ),
        },
        "reliability_diagnostics": {
            "evidence_sufficiency": legacy_measurements.get("evidence_sufficiency"),
            "retrieval_completeness": {
                "score": round(retrieval, 6),
                "status": _context_strength_label(retrieval),
                "source": "pool_context_summary.context_evidence_summary.retrieval_completeness_proxy",
            },
            "pool_independence": pool_independence,
            "context_ambiguity": {
                "score": round(ambiguity, 6),
                "band": legacy_measurements.get("context_ambiguity_band") or _context_strength_label(ambiguity),
            },
            "profile_confidence": profile_confidence,
            "family_classification_uncertainty": {
                "status": "not_yet_formally_calculated",
                "available_query_family_fields": {
                    "composition_family": query.get("composition_family"),
                    "formula_family": query.get("formula_family"),
                    "prototype_family": query.get("prototype_family"),
                    "structure_variant": query.get("structure_variant"),
                },
            },
            "quality_flags": (legacy_profile.get("diagnostics", {}) or {}).get("quality_flags", []),
            "quality_flag_details": (legacy_profile.get("diagnostics", {}) or {}).get("quality_flag_details", []),
        },
        "interpretation": {
            "contextual_pattern": pattern,
            "readable_interpretations": {
                "hub_like": {
                    "applies": pattern.get("hub_like_interpretation"),
                    "definition": "High Local Context Support relative to the selected reference corpus.",
                },
                "boundary_like": {
                    "applies": pattern.get("boundary_like_interpretation"),
                    "definition": "High Structural Regime Contrast among related retrieved reference materials.",
                },
            },
            "legacy_role_interpretation": legacy_profile.get("interpretation"),
            "legacy_role_status": "deprecated_interpretive_compatibility_only",
        },
        "reproducibility": {
            "configuration": asdict(cfg),
            "legacy_profile_schema_version": legacy_profile.get("schema_version"),
        },
    }

def build_role_priors(
    query_profile: Dict[str, Any],
    evidence_summary: Dict[str, Any],
    pool_df: pd.DataFrame,
    missing_df: pd.DataFrame,
    cfg: RolePriorConfig,
) -> Dict[str, Any]:
    row = _pool_row_map(pool_df)
    query = {
        "jid": query_profile.get("identity", {}).get("jid") or query_profile.get("source", {}).get("jid"),
        "formula": query_profile.get("identity", {}).get("formula"),
        "chemical_system": query_profile.get("composition", {}).get("chemical_system"),
        "composition_family": query_profile.get("composition", {}).get("composition_family"),
        "formula_family": query_profile.get("family_classification", {}).get("formula_family"),
        "prototype_family": query_profile.get("family_classification", {}).get("prototype_family"),
        "structure_variant": query_profile.get("family_classification", {}).get("structure_variant"),
        "family_classification_confidence": query_profile.get("family_classification", {}).get("confidence"),
        "spacegroup_number": query_profile.get("structural_metadata", {}).get("spacegroup_number"),
        "spacegroup_symbol": query_profile.get("structural_metadata", {}).get("spacegroup_symbol"),
    }

    overlap = evidence_summary.get("overlap_summary", {}) if isinstance(evidence_summary, dict) else {}
    role_signal = evidence_summary.get("role_signal_summary", {}) if isinstance(evidence_summary, dict) else {}
    bridge_signal = role_signal.get("bridge_indicators", {}) if isinstance(role_signal, dict) else {}

    # Core component extraction
    same_n = _get(row, "same_family", "n_candidates")
    adj_n = _get(row, "adjacent_family", "n_candidates")
    boundary_n = _get(row, "boundary_contrast", "n_candidates")
    neg_n = _get(row, "negative_control", "n_candidates")

    same_family_match = _get(row, "same_family", "same_composition_family_rate")
    same_material_match = _get(row, "same_family", "same_material_family_rate")
    same_formula_match = _get(row, "same_family", "same_formula_family_rate")
    same_prototype_match = _get(row, "same_family", "same_prototype_family_rate")
    same_variant_match = _get(row, "same_family", "same_structure_variant_rate")
    same_stable = _get(row, "same_family", "stable_fraction_ehull_le_0_1")
    same_known = _get(row, "same_family", "known_synthesized_rate")
    neg_family = _get(row, "negative_control", "same_composition_family_rate")
    neg_material = _get(row, "negative_control", "same_material_family_rate")
    neg_formula = _get(row, "negative_control", "same_formula_family_rate")
    neg_prototype = _get(row, "negative_control", "same_prototype_family_rate")
    neg_variant = _get(row, "negative_control", "same_structure_variant_rate")
    neg_element_overlap = _get(row, "negative_control", "mean_element_overlap_fraction_query")
    neg_system = _get(row, "negative_control", "same_chemical_system_rate")
    neg_separation = 1.0 - _clip01(max(neg_family, neg_material, neg_formula, neg_prototype, neg_variant, neg_element_overlap, neg_system))

    adj_unique_systems = _get(row, "adjacent_family", "chemical_system_count")
    adj_elem_overlap = _get(row, "adjacent_family", "mean_element_overlap_fraction_query")
    adj_family_entropy = _get(row, "adjacent_family", "composition_family_entropy")
    adj_material_entropy = _get(row, "adjacent_family", "material_family_entropy")
    adj_formula_entropy = _get(row, "adjacent_family", "formula_family_entropy")
    adj_prototype_entropy = _get(row, "adjacent_family", "prototype_family_entropy")
    adj_variant_entropy = _get(row, "adjacent_family", "structure_variant_entropy")
    same_adj_overlap = _safe_float(
        overlap.get("same_family__adjacent_family")
        or overlap.get("same_adjacent")
        or bridge_signal.get("overlap_same_adjacent")
    )

    # Bridge/Other diagnostic metrics. These do NOT alter Hub or Boundary scoring.
    # They are used only to describe the new Phase 1 `Other` class and to preserve
    # useful bridge-like evidence without letting Bridge compete as a primary role.
    same_query_similarity = _get(row, "same_family", "query_similarity_score")
    adj_query_similarity = _get(row, "adjacent_family", "query_similarity_score")
    boundary_query_similarity = _get(row, "boundary_contrast", "query_similarity_score")
    wildcard_query_similarity = _get(row, "wildcard", "query_similarity_score")

    balanced_multi_pool_similarity = _summary_metric_or_none(evidence_summary, "balanced_multi_pool_similarity")
    if balanced_multi_pool_similarity is None:
        balanced_multi_pool_similarity = _mean_available([
            _balance_pair(same_query_similarity, adj_query_similarity),
            _balance_pair(adj_query_similarity, boundary_query_similarity),
        ])

    competing_membership_strength = _summary_metric_or_none(evidence_summary, "competing_membership_strength")
    if competing_membership_strength is None:
        competing_membership_strength = _mean_available([
            _normalized_entropy([same_query_similarity, adj_query_similarity, boundary_query_similarity, wildcard_query_similarity]),
            max(same_query_similarity, adj_query_similarity, boundary_query_similarity, wildcard_query_similarity),
            adj_query_similarity,
        ])

    structural_interpolation_score = _summary_metric_or_none(evidence_summary, "structural_interpolation_score")
    if structural_interpolation_score is None:
        structural_interpolation_score = _mean_available([
            _balance_pair(same_query_similarity, boundary_query_similarity),
            adj_query_similarity,
            _get(row, "adjacent_family", "structural_metadata_similarity_score"),
            _get(row, "boundary_contrast", "structural_regime_diversity_score"),
        ])

    coordination_transition_proxy = _summary_metric_or_none(evidence_summary, "coordination_transition_proxy")
    if coordination_transition_proxy is None:
        coordination_transition_proxy = _mean_available([
            _get(row, "adjacent_family", "structural_regime_diversity_score"),
            _get(row, "boundary_contrast", "structural_regime_diversity_score"),
            adj_elem_overlap,
            _get(row, "boundary_contrast", "structural_metadata_similarity_score"),
        ])

    bridge_evidence_entropy = _summary_metric_or_none(evidence_summary, "bridge_evidence_entropy")
    if bridge_evidence_entropy is None:
        bridge_evidence_entropy = _normalized_entropy([
            _norm_count(adj_n, 500),
            _norm_count(adj_unique_systems, 100),
            adj_elem_overlap,
            max(adj_family_entropy, adj_material_entropy, adj_formula_entropy),
            adj_prototype_entropy,
            adj_variant_entropy,
            balanced_multi_pool_similarity,
            competing_membership_strength,
            structural_interpolation_score,
            coordination_transition_proxy,
        ])

    bridge_diagnostic_strength = _mean_available([
        balanced_multi_pool_similarity,
        competing_membership_strength,
        structural_interpolation_score,
        coordination_transition_proxy,
        bridge_evidence_entropy,
    ])

    boundary_same_sg = _get(row, "boundary_contrast", "same_spacegroup_rate")
    boundary_same_crys = _get(row, "boundary_contrast", "same_crystal_system_rate")
    boundary_sym_dist = _get(row, "boundary_contrast", "mean_symmetry_distance")
    boundary_sg_entropy = _get(row, "boundary_contrast", "spacegroup_entropy")
    boundary_crys_entropy = _get(row, "boundary_contrast", "crystal_system_entropy")
    boundary_same_formula = _get(row, "boundary_contrast", "same_formula_family_rate")
    boundary_same_prototype = _get(row, "boundary_contrast", "same_prototype_family_rate")
    boundary_same_variant = _get(row, "boundary_contrast", "same_structure_variant_rate")
    boundary_variant_entropy = _get(row, "boundary_contrast", "structure_variant_entropy")
    boundary_stable = _get(row, "boundary_contrast", "stable_fraction_ehull_le_0_1")

    all_missing_rate = 0.0
    if not missing_df.empty and "missing_rate" in missing_df.columns:
        all_missing_rate = sum(_safe_float(x) for x in missing_df["missing_rate"].tolist()) / max(len(missing_df), 1)

    # Query-level specificity available before role scoring. These are used both for
    # evidence sufficiency and for suppressing overconfident labels on generic cases.
    formula_family = query.get("formula_family")
    prototype_family = query.get("prototype_family")
    structure_variant = query.get("structure_variant")
    family_specificity = _label_specificity(formula_family, prototype_family, structure_variant)
    structural_specificity = _structural_specificity(prototype_family, structure_variant)
    preliminary_anchor_strength = _clip01(max(
        same_formula_match,
        same_prototype_match,
        boundary_same_formula,
        boundary_same_prototype,
    ) * (0.45 + 0.55 * family_specificity))

    canonical_high_symmetry_hub_candidate = _is_canonical_high_symmetry_hub_candidate(query)
    canonical_hub_context_strength = _clip01(max(
        same_formula_match,
        same_prototype_match,
        same_variant_match,
        same_stable,
    ))

    components = {
        "hub": {
            "same_family_pool_size": _norm_count(same_n, 500),
            "same_composition_match": same_family_match,
            "same_material_match": same_material_match,
            "same_formula_match": same_formula_match,
            "same_prototype_match": same_prototype_match,
            "same_family_stable_fraction": same_stable,
            "same_family_known_synthesized": same_known,
            "negative_control_separation": neg_separation,
            "canonical_prototype_bonus": 1.0 if canonical_high_symmetry_hub_candidate else 0.0,
        },
        "bridge": {
            "adjacent_pool_size": _norm_count(adj_n, 500),
            "adjacent_unique_systems": _norm_count(adj_unique_systems, 100),
            "adjacent_element_overlap": adj_elem_overlap,
            "adjacent_family_entropy": _clip01(max(adj_family_entropy, adj_material_entropy, adj_formula_entropy)),
            "adjacent_prototype_entropy": _clip01(adj_prototype_entropy),
            "adjacent_variant_entropy": _clip01(adj_variant_entropy),
            "cross_pool_overlap": _norm_count(same_adj_overlap, 100),
            "negative_control_separation": neg_separation,
            "balanced_multi_pool_similarity_diagnostic": balanced_multi_pool_similarity,
            "competing_membership_strength_diagnostic": competing_membership_strength,
            "structural_interpolation_score_diagnostic": structural_interpolation_score,
            "coordination_transition_proxy_diagnostic": coordination_transition_proxy,
            "bridge_evidence_entropy_diagnostic": bridge_evidence_entropy,
        },
        "boundary": {
            "boundary_pool_size": _norm_count(boundary_n, 500),
            "same_formula_or_prototype_context": _clip01(max(boundary_same_formula, boundary_same_prototype)),
            "different_spacegroup": 1.0 - boundary_same_sg,
            "different_crystal_system": 1.0 - boundary_same_crys,
            "different_structure_variant": 1.0 - boundary_same_variant,
            "symmetry_distance": _norm_count(boundary_sym_dist, 100),
            "symmetry_entropy": _clip01(max(boundary_sg_entropy, boundary_crys_entropy, boundary_variant_entropy)),
            "boundary_stability": boundary_stable,
        },
        "outlier": {
            "low_same_family_support": 1.0 - _norm_count(same_n, 500),
            "low_adjacent_support": 1.0 - _norm_count(adj_n, 500),
            "negative_control_similarity": 1.0 - neg_separation,
            "low_family_match": 1.0 - same_family_match,
            "high_missingness": _clip01(all_missing_rate),
        },
    }

    weights = {
        "hub": cfg.hub_weights,
        "bridge": cfg.bridge_weights,
        "boundary": cfg.boundary_weights,
        "outlier": cfg.outlier_weights,
    }

    role_pool_dependencies = {
        "hub": ["same_family", "negative_control"],
        "bridge": ["adjacent_family", "same_family", "negative_control"],
        "boundary": ["boundary_contrast", "same_family"],
        "outlier": ["same_family", "adjacent_family", "negative_control", "wildcard"],
    }

    role_rows: List[Dict[str, Any]] = []
    contradictions_rows: List[Dict[str, Any]] = []
    role_records: Dict[str, Any] = {}

    for role in ["hub", "boundary", "bridge", "outlier"]:
        score = _weighted_score(components[role], weights[role])

        # Calibration: for canonical high-symmetry prototype references, boundary pools
        # are expected to find lower-symmetry contrast candidates. That is useful
        # boundary evidence for the neighbourhood, but it should not automatically
        # make the query itself boundary-primary when same-family hub context is strong.
        canonical_boundary_score_penalty = 0.0
        if (
            role == "boundary"
            and canonical_high_symmetry_hub_candidate
            and canonical_hub_context_strength >= cfg.canonical_boundary_penalty_min_hub_context
        ):
            canonical_boundary_score_penalty = float(cfg.canonical_boundary_score_penalty)
            score = _clip01(score - canonical_boundary_score_penalty)

        dep_rows = [row[p] for p in role_pool_dependencies[role] if p in row]
        base_confidence = _confidence_from_metrics(dep_rows, missing_df, cfg)

        support: List[Dict[str, Any]] = []
        contradictions: List[Dict[str, Any]] = []

        if role == "hub":
            support += [
                _evidence_item("Same-family pool is populated.", same_n),
                _evidence_item("Same-family composition-family match rate.", same_family_match),
                _evidence_item("Same-family formula-family match rate.", same_formula_match),
                _evidence_item("Same-family prototype-family match rate.", same_prototype_match),
                _evidence_item("Same-family structure-variant match rate.", same_variant_match),
                _evidence_item("Same-family stable fraction.", same_stable),
                _evidence_item("Negative control separation is strong.", neg_separation),
            ]
            if adj_unique_systems > 150:
                contradictions.append(_evidence_item("Adjacent-family pool contains many chemical systems, which weakens a simple single-family hub interpretation.", adj_unique_systems))
            if same_adj_overlap > 0:
                contradictions.append(_evidence_item("Same-family and adjacent-family pools overlap, so hub evidence is not fully independent.", same_adj_overlap))
            if canonical_high_symmetry_hub_candidate:
                support.append(_evidence_item("Query is a canonical high-symmetry prototype candidate; this strengthens hub interpretation.", query.get("spacegroup_symbol") or query.get("spacegroup_number")))
            if same_formula_match < 0.60 and same_prototype_match < 0.60:
                contradictions.append(_evidence_item("Same-family formula/prototype match rates are weak, so broad-family hub evidence may be inflated.", max(same_formula_match, same_prototype_match)))
        elif role == "bridge":
            support += [
                _evidence_item("Adjacent-family pool is populated.", adj_n),
                _evidence_item("Adjacent-family pool spans many chemical systems.", adj_unique_systems),
                _evidence_item("Adjacent-family element-overlap fraction is substantial.", adj_elem_overlap),
                _evidence_item("Adjacent-family prototype entropy.", adj_prototype_entropy),
                _evidence_item("Adjacent-family structure-variant entropy.", adj_variant_entropy),
                _evidence_item("Cross-pool overlap suggests connection between candidate groups.", same_adj_overlap),
                _evidence_item("Balanced multi-pool similarity diagnostic.", balanced_multi_pool_similarity),
                _evidence_item("Competing neighbourhood membership diagnostic.", competing_membership_strength),
                _evidence_item("Structural interpolation diagnostic.", structural_interpolation_score),
                _evidence_item("Coordination/structural transition diagnostic.", coordination_transition_proxy),
                _evidence_item("Bridge evidence entropy diagnostic.", bridge_evidence_entropy),
            ]
            if max(adj_family_entropy, adj_material_entropy, adj_formula_entropy, adj_prototype_entropy, adj_variant_entropy) <= 0.05:
                contradictions.append(_evidence_item("Adjacent-family pool has low family/prototype/variant entropy; it may be chemically broad but not structurally family-diverse.", max(adj_family_entropy, adj_material_entropy, adj_formula_entropy, adj_prototype_entropy, adj_variant_entropy)))
            if adj_elem_overlap < 0.30:
                contradictions.append(_evidence_item("Adjacent-family element overlap is weak.", adj_elem_overlap))
        elif role == "boundary":
            support += [
                _evidence_item("Boundary/contrast pool is populated.", boundary_n),
                _evidence_item("Boundary pool retains formula/prototype context.", max(boundary_same_formula, boundary_same_prototype)),
                _evidence_item("Boundary pool structure-variant match rate.", boundary_same_variant),
                _evidence_item("Boundary pool has low same-spacegroup rate.", boundary_same_sg),
                _evidence_item("Boundary pool has low same-crystal-system rate.", boundary_same_crys),
                _evidence_item("Mean symmetry distance is high.", boundary_sym_dist),
                _evidence_item("Boundary pool remains largely stable by hull threshold.", boundary_stable),
            ]
            if boundary_stable < 0.50:
                contradictions.append(_evidence_item("Boundary candidates are often unstable, reducing confidence.", boundary_stable))
            if boundary_same_sg > 0.50:
                contradictions.append(_evidence_item("Boundary pool does not strongly differ in space group.", boundary_same_sg))
            if max(boundary_same_formula, boundary_same_prototype) < 0.30:
                contradictions.append(_evidence_item("Boundary evidence is weakly anchored to the query formula/prototype family.", max(boundary_same_formula, boundary_same_prototype)))
            if canonical_boundary_score_penalty > 0:
                contradictions.append(_evidence_item("Query is a canonical high-symmetry prototype with strong same-family hub context; boundary evidence is treated as neighbourhood contrast rather than primary query role.", canonical_boundary_score_penalty))
        elif role == "outlier":
            support += [
                _evidence_item("Outlier score increases when same/adjacent support is weak.", components[role]["low_same_family_support"]),
                _evidence_item("Negative-control similarity component.", components[role]["negative_control_similarity"]),
                _evidence_item("Missingness component.", components[role]["high_missingness"]),
            ]
            if same_n >= 100:
                contradictions.append(_evidence_item("Same-family pool is large, arguing against outlier status.", same_n))
            if adj_n >= 100:
                contradictions.append(_evidence_item("Adjacent-family pool is large, arguing against isolation.", adj_n))
            if neg_separation > 0.80:
                contradictions.append(_evidence_item("Negative controls are cleanly separated, reducing outlier concern.", neg_separation))

        # General warnings
        if all_missing_rate > cfg.warning_missing_rate_threshold:
            contradictions.append(_evidence_item("Overall missing-value rate is high and weakens confidence.", all_missing_rate))

        raw_score = score
        contradiction_penalty = min(
            float(cfg.contradiction_penalty_cap),
            float(cfg.contradiction_penalty_weight) * float(len(contradictions)),
        )
        adjusted_score = _clip01(raw_score - contradiction_penalty)
        # Initial role confidence before final top-role gap is known.
        confidence = _role_specific_confidence(
            base_confidence=base_confidence,
            score=adjusted_score,
            contradiction_count=len(contradictions),
            family_specificity=family_specificity,
            structural_specificity=structural_specificity,
            anchor_strength=preliminary_anchor_strength,
            role_gap=0.0,
            all_missing_rate=all_missing_rate,
        )
        plaus = _plausibility(adjusted_score, confidence, cfg)
        plaus = _apply_context_gate_to_role(
            role=role,
            plausibility=plaus,
            score=adjusted_score,
            family_specificity=family_specificity,
            structural_specificity=structural_specificity,
            anchor_strength=preliminary_anchor_strength,
            cfg=cfg,
        )

        role_records[role] = {
            "role": role,
            "raw_prior_score": round(raw_score, 6),
            "prior_score": round(adjusted_score, 6),
            "contradiction_penalty": round(contradiction_penalty, 6),
            "canonical_boundary_score_penalty": round(canonical_boundary_score_penalty, 6),
            "base_confidence": round(base_confidence, 6),
            "confidence": round(confidence, 6),
            "plausibility": plaus,
            "components": {k: round(v, 6) for k, v in components[role].items()},
            "supporting_evidence": support,
            "contradictions": contradictions,
        }

        role_rows.append({
            "role": role,
            "raw_prior_score": round(raw_score, 6),
            "prior_score": round(adjusted_score, 6),
            "contradiction_penalty": round(contradiction_penalty, 6),
            "canonical_boundary_score_penalty": round(canonical_boundary_score_penalty, 6),
            "base_confidence": round(base_confidence, 6),
            "confidence": round(confidence, 6),
            "plausibility": plaus,
            "supporting_evidence_count": len(support),
            "contradiction_count": len(contradictions),
        })
        for c in contradictions:
            contradictions_rows.append({
                "role": role,
                "contradiction": c["text"],
                "value": c.get("value"),
            })

    sorted_roles = sorted(role_records.values(), key=lambda r: (r["prior_score"], r["confidence"]), reverse=True)
    top = sorted_roles[0] if sorted_roles else None
    second = sorted_roles[1] if len(sorted_roles) > 1 else None

    # ------------------------------------------------------------------
    # Phase 4.5: Evidence sufficiency gate
    # ------------------------------------------------------------------
    # This answers a different question from role scoring:
    # "Is the evidence good and specific enough to assign any role?"
    # Without this gate, generic materials can accumulate positive role evidence
    # and the engine overclaims on negative controls.
    # Reuse query-specificity values calculated before role scoring.
    anchor_strength = preliminary_anchor_strength

    # Evidence sufficiency should be based on the Phase 1 primary decision
    # candidates only: Hub and Boundary. Bridge and outlier are diagnostics and
    # must not decide whether a Hub/Boundary claim is defensible.
    core_for_sufficiency = sorted(
        [role_records[r] for r in ("hub", "boundary") if r in role_records],
        key=lambda r: (r.get("prior_score", 0.0), r.get("confidence", 0.0)),
        reverse=True,
    )
    top_core_for_sufficiency = core_for_sufficiency[0] if core_for_sufficiency else None
    second_core_for_sufficiency = core_for_sufficiency[1] if len(core_for_sufficiency) > 1 else None
    role_gap = _safe_gap(
        top_core_for_sufficiency["prior_score"] if top_core_for_sufficiency else 0.0,
        second_core_for_sufficiency["prior_score"] if second_core_for_sufficiency else 0.0,
    )
    role_separation = _clip01(role_gap / max(float(cfg.role_separation_threshold), 1e-12))
    evidence_quality = _confidence_from_metrics(list(row.values()), missing_df, cfg)
    missing_quality = 1.0 - _clip01(all_missing_rate)
    multi_pool = _safe_float(overlap.get("candidate_ids_in_multiple_pools"), 0.0)
    total_pool_entries = max(same_n + adj_n + boundary_n + _get(row, "wildcard", "n_candidates") + neg_n, 1.0)
    pool_independence = 1.0 - _clip01(multi_pool / total_pool_entries)

    evidence_sufficiency_score = _clip01(
        0.25 * anchor_strength
        + 0.20 * structural_specificity
        + 0.15 * neg_separation
        + 0.15 * evidence_quality
        + 0.10 * role_separation
        + 0.10 * missing_quality
        + 0.05 * pool_independence
    )

    sufficiency_reasons: List[str] = []
    sufficiency_warnings: List[str] = []
    if anchor_strength >= cfg.minimum_anchor_strength:
        sufficiency_reasons.append(f"Anchor strength is adequate ({anchor_strength:.3f}).")
    else:
        sufficiency_warnings.append(f"Anchor strength is weak ({anchor_strength:.3f}); family/prototype evidence may be too generic.")
    if family_specificity >= cfg.minimum_family_specificity:
        sufficiency_reasons.append(f"Family classification is specific enough ({family_specificity:.3f}).")
    else:
        sufficiency_warnings.append(f"Family classification is generic or missing ({family_specificity:.3f}).")
    if structural_specificity >= cfg.minimum_structural_specificity:
        sufficiency_reasons.append(f"Structural family/prototype context is specific enough ({structural_specificity:.3f}).")
    else:
        sufficiency_warnings.append(f"Structural family/prototype context is weak ({structural_specificity:.3f}); formula-only evidence is not enough for a strong role.")
    if neg_separation >= 0.70:
        sufficiency_reasons.append(f"Negative controls are well separated ({neg_separation:.3f}).")
    else:
        sufficiency_warnings.append(f"Negative-control separation is weak ({neg_separation:.3f}).")
    if role_gap >= cfg.role_separation_threshold:
        sufficiency_reasons.append(f"Top role is separated from second role by {role_gap:.3f}.")
    else:
        sufficiency_warnings.append(f"Top roles are near-tied; role separation is only {role_gap:.3f}.")
    if all_missing_rate > cfg.warning_missing_rate_threshold:
        sufficiency_warnings.append(f"Average missing-value rate is high ({all_missing_rate:.3f}).")

    # Generic context is now a caution flag, not an automatic veto, when the
    # strongest Phase 1 core role has high raw evidence. This preserves Hub and
    # Boundary wins/partials while still surfacing overclaim risk for review.
    generic_overclaim_risk = bool(
        (
            family_specificity < cfg.minimum_family_specificity
            or structural_specificity < cfg.minimum_structural_specificity
            or anchor_strength < cfg.minimum_specific_anchor_for_strong_role
        )
        and (top_core_for_sufficiency and top_core_for_sufficiency.get("role") in {"hub", "boundary"})
    )
    high_core_override_available = bool(
        top_core_for_sufficiency
        and _clip01(top_core_for_sufficiency.get("prior_score", 0.0)) >= cfg.high_core_score_override_threshold
        and _clip01(top_core_for_sufficiency.get("confidence", 0.0)) >= cfg.high_core_confidence_override_threshold
    )
    if generic_overclaim_risk:
        if high_core_override_available:
            sufficiency_warnings.append(
                "Generic or formula-only overclaim risk detected; preserving high-scoring Hub/Boundary evidence with caution flags."
            )
        else:
            evidence_sufficiency_score = min(evidence_sufficiency_score, cfg.evidence_sufficiency_threshold - 0.01)
            sufficiency_warnings.append("Generic or formula-only overclaim risk detected; suppressing weak role assignment.")

    evidence_sufficiency_status = (
        "sufficient" if evidence_sufficiency_score >= cfg.evidence_sufficiency_threshold else "insufficient"
    )
    if evidence_sufficiency_status == "insufficient" and high_core_override_available:
        evidence_sufficiency_status = "sufficient_with_caution"

    # Recompute role-specific confidence and plausibility now that role_gap is known,
    # then enforce the sufficiency/context gate. This prevents the table and the
    # final assessment from disagreeing.
    for rr in role_records.values():
        role = rr["role"]
        rr_conf = _role_specific_confidence(
            base_confidence=rr.get("base_confidence", rr.get("confidence", 0.0)),
            score=rr.get("prior_score", 0.0),
            contradiction_count=len(rr.get("contradictions", [])),
            family_specificity=family_specificity,
            structural_specificity=structural_specificity,
            anchor_strength=anchor_strength,
            role_gap=role_gap if role == (top["role"] if top else None) else 0.0,
            all_missing_rate=all_missing_rate,
        )
        rr["confidence"] = round(rr_conf, 6)
        rr_plaus = _plausibility(rr.get("prior_score", 0.0), rr_conf, cfg)
        rr_plaus = _apply_context_gate_to_role(
            role=role,
            plausibility=rr_plaus,
            score=rr.get("prior_score", 0.0),
            family_specificity=family_specificity,
            structural_specificity=structural_specificity,
            anchor_strength=anchor_strength,
            cfg=cfg,
        )
        if evidence_sufficiency_status == "insufficient" and role != "outlier":
            strong_core_evidence = bool(
                role in {"hub", "boundary"}
                and _clip01(rr.get("prior_score", 0.0)) >= cfg.high_core_score_override_threshold
                and _clip01(rr_conf) >= cfg.high_core_confidence_override_threshold
            )
            if not strong_core_evidence:
                rr_plaus = "not_supported_due_to_insufficient_context"
        rr["plausibility"] = rr_plaus

    role_rows = []
    contradictions_rows = []
    for rr in role_records.values():
        role_rows.append({
            "role": rr["role"],
            "raw_prior_score": rr["raw_prior_score"],
            "prior_score": rr["prior_score"],
            "contradiction_penalty": rr["contradiction_penalty"],
            "canonical_boundary_score_penalty": rr.get("canonical_boundary_score_penalty", 0.0),
            "base_confidence": rr.get("base_confidence"),
            "confidence": rr["confidence"],
            "plausibility": rr["plausibility"],
            "supporting_evidence_count": len(rr.get("supporting_evidence", [])),
            "contradiction_count": len(rr.get("contradictions", [])),
        })
        for c in rr.get("contradictions", []):
            contradictions_rows.append({
                "role": rr["role"],
                "contradiction": c["text"],
                "value": c.get("value"),
            })

    sorted_roles = sorted(role_records.values(), key=lambda r: (r["prior_score"], r["confidence"]), reverse=True)
    top = sorted_roles[0] if sorted_roles else None
    second = sorted_roles[1] if len(sorted_roles) > 1 else None

    supported = [r for r in sorted_roles if r["plausibility"] == "supported"]
    partial = [r for r in sorted_roles if r["plausibility"] == "partial"]

    no_strong_role = len(supported) == 0 or evidence_sufficiency_status == "insufficient"
    if no_strong_role:
        supported = []

    top_supported = supported[0] if supported else None
    second_supported = supported[1] if len(supported) > 1 else None

    ambiguous_supported_roles = False
    if not no_strong_role and top_supported and second_supported:
        # Compare supported roles, not merely raw top scores. A raw top role may have
        # been suppressed by the sufficiency/context gate.
        ambiguous_supported_roles = bool((top_supported["prior_score"] - second_supported["prior_score"]) < cfg.no_strong_role_margin)

    if no_strong_role:
        final_assessment = "no_strong_role_supported"
    elif ambiguous_supported_roles:
        final_assessment = "ambiguous_supported_roles"
    else:
        final_assessment = f"primary_role_supported:{top_supported['role']}"

    warnings = []
    if multi_pool > cfg.warning_pool_overlap_threshold:
        warnings.append(f"{int(multi_pool)} candidate IDs appear in multiple pools; role evidence is not fully independent.")
    if all_missing_rate > cfg.warning_missing_rate_threshold:
        warnings.append(f"Average missing-value rate is {all_missing_rate:.3f}; confidence should be treated cautiously.")
    warnings.extend(sufficiency_warnings)

    evidence_sufficiency = {
        "score": round(evidence_sufficiency_score, 6),
        "status": evidence_sufficiency_status,
        "threshold": cfg.evidence_sufficiency_threshold,
        "anchor_strength": round(anchor_strength, 6),
        "family_specificity": round(family_specificity, 6),
        "structural_specificity": round(structural_specificity, 6),
        "negative_control_separation": round(neg_separation, 6),
        "role_gap": round(role_gap, 6),
        "role_separation": round(role_separation, 6),
        "evidence_quality": round(evidence_quality, 6),
        "missing_quality": round(missing_quality, 6),
        "pool_independence": round(pool_independence, 6),
        "generic_overclaim_risk": generic_overclaim_risk,
        "canonical_high_symmetry_hub_candidate": canonical_high_symmetry_hub_candidate,
        "canonical_hub_context_strength": round(canonical_hub_context_strength, 6),
        "reasons": sufficiency_reasons,
        "warnings": sufficiency_warnings,
    }

    # ------------------------------------------------------------------
    # Phase 1 primary role model: Hub / Boundary / Other
    # ------------------------------------------------------------------
    # Hub and Boundary remain scored exactly as before. Bridge is retained as a
    # diagnostic/secondary-descriptor signal only; it no longer competes as a
    # primary role. `Other` is assigned when Hub/Boundary cannot be defended.
    primary_scored_roles = ["hub", "boundary"]
    core_sorted_roles = sorted(
        [role_records[r] for r in primary_scored_roles if r in role_records],
        key=lambda r: (r["prior_score"], r["confidence"]),
        reverse=True,
    )
    indicator_sorted_roles = sorted(
        [role_records[r] for r in QUALITY_INDICATOR_ROLES if r in role_records],
        key=lambda r: (r["prior_score"], r["confidence"]),
        reverse=True,
    )

    top_core = core_sorted_roles[0] if core_sorted_roles else None
    second_core = core_sorted_roles[1] if len(core_sorted_roles) > 1 else None
    top_core_score = float(top_core.get("prior_score", 0.0)) if top_core else 0.0
    second_core_score = float(second_core.get("prior_score", 0.0)) if second_core else 0.0
    core_role_gap = _safe_gap(top_core_score, second_core_score)
    core_role_separation = _clip01(core_role_gap / max(float(cfg.ambiguous_role_margin), 1e-12))
    ambiguous_core_roles = bool(top_core and second_core and core_role_gap < cfg.ambiguous_role_margin)

    # Strength bands for core roles.
    role_strength_table: List[Dict[str, Any]] = []
    role_ranking: List[Dict[str, Any]] = []
    ranked_explanations: List[Dict[str, Any]] = []

    for idx, rr in enumerate(core_sorted_roles, start=1):
        role = rr["role"]
        support_items = rr.get("supporting_evidence", []) or []
        contradiction_items = rr.get("contradictions", []) or []
        support_count = len(support_items)
        contradiction_count = len(contradiction_items)
        strength = _strength_band(
            score=float(rr.get("prior_score", 0.0)),
            confidence=float(rr.get("confidence", 0.0)),
            evidence_sufficiency_status=evidence_sufficiency_status,
            cfg=cfg,
        )
        explanation_strength = _clip01(
            0.50 * _clip01(float(rr.get("prior_score", 0.0)))
            + 0.25 * _clip01(float(rr.get("confidence", 0.0)))
            + 0.15 * _clip01(support_count / 8.0)
            + 0.10 * (1.0 - _clip01(contradiction_count / 8.0))
        )

        supported_bool = strength in {"strong", "very_strong"}
        partial_bool = strength in {"weak", "moderate"}

        rr["rank"] = idx
        rr["top_1"] = idx == 1
        rr["top_2"] = idx <= 2
        rr["strength_band"] = strength
        rr["supported"] = supported_bool
        rr["partial"] = partial_bool
        rr["unsupported"] = strength in {"very_weak", "insufficient_evidence"}
        rr["supporting_evidence_count"] = support_count
        rr["contradiction_count"] = contradiction_count
        rr["evidence_strength"] = round(explanation_strength, 6)
        rr["is_core_role"] = True
        rr["is_quality_indicator"] = False

        row_common = {
            "rank": idx,
            "role": role,
            "raw_prior_score": rr.get("raw_prior_score"),
            "prior_score": rr.get("prior_score"),
            "confidence": rr.get("confidence"),
            "strength_band": strength,
            "strength_rank": _strength_rank(strength),
            "plausibility": rr.get("plausibility"),
            "supported": supported_bool,
            "partial": partial_bool,
            "unsupported": rr["unsupported"],
            "top_1": rr["top_1"],
            "top_2": rr["top_2"],
            "evidence_strength": rr["evidence_strength"],
            "supporting_evidence_count": support_count,
            "contradiction_count": contradiction_count,
            "contradiction_penalty": rr.get("contradiction_penalty"),
            "canonical_boundary_score_penalty": rr.get("canonical_boundary_score_penalty", 0.0),
            "is_core_role": True,
            "is_quality_indicator": False,
        }
        role_ranking.append(row_common)
        role_strength_table.append({
            **row_common,
            "interpretation": (
                f"{role} is the #{idx} ranked core role with {strength} evidence."
            ),
        })

        top_support = support_items[:5]
        top_contradictions = contradiction_items[:5]
        ranked_explanations.append({
            "rank": idx,
            "role": role,
            "summary": (
                f"{role} ranked #{idx} among core roles with score {rr.get('prior_score')}, "
                f"confidence {rr.get('confidence')}, and strength `{strength}`."
            ),
            "strength_band": strength,
            "plausibility": rr.get("plausibility"),
            "evidence_strength": rr["evidence_strength"],
            "supporting_evidence": top_support,
            "contradictions": top_contradictions,
            "supporting_evidence_text": " | ".join(str(x.get("text", "")) for x in top_support),
            "contradiction_text": " | ".join(str(x.get("text", "")) for x in top_contradictions),
        })

    # Interpret outlier as a quality indicator, not as a primary role.
    outlier_record = role_records.get("outlier", {})
    outlier_score = float(outlier_record.get("prior_score", 0.0) or 0.0)
    outlier_confidence = float(outlier_record.get("confidence", 0.0) or 0.0)
    outlier_strength = _strength_band(outlier_score, outlier_confidence, evidence_sufficiency_status, cfg)
    if outlier_record:
        outlier_record["is_core_role"] = False
        outlier_record["is_quality_indicator"] = True
        outlier_record["strength_band"] = outlier_strength

    primary_role = top_core.get("role") if top_core else None
    secondary_role = second_core.get("role") if second_core else None
    primary_strength = top_core.get("strength_band") if top_core else "insufficient_evidence"
    primary_score = top_core.get("prior_score") if top_core else None
    primary_confidence = top_core.get("confidence") if top_core else None

    # Phase 1 decision rule: Other is a rejection state, not a third scored
    # role. Preserve the legacy Hub/Boundary evidence and treat `moderate` as
    # partial-but-defensible support rather than forcing it into Other.
    #
    # Hub/Boundary are therefore retained as the primary role when the strongest
    # core role reaches at least moderate evidence. Other is assigned only when
    # both Hub and Boundary fail the minimum defensibility test or when the
    # global evidence sufficiency gate fails.
    defensible_core_roles = [
        r for r in core_sorted_roles
        if r.get("strength_band") in {"moderate", "strong", "very_strong"}
    ]
    no_strong_role = bool(not defensible_core_roles)

    quality_flags: List[Dict[str, Any]] = []
    if no_strong_role:
        quality_flags.append(_quality_flag(
            "no_strong_role_supported",
            "high" if evidence_sufficiency_status == "insufficient" else "medium",
            "No Hub/Boundary role reaches at least moderate defensible support.",
            primary_strength,
        ))
    if evidence_sufficiency_status == "insufficient":
        quality_flags.append(_quality_flag(
            "insufficient_evidence",
            "high",
            "Evidence sufficiency score is below threshold.",
            evidence_sufficiency_score,
        ))
    if outlier_score >= cfg.possible_outlier_threshold:
        quality_flags.append(_quality_flag(
            "possible_outlier",
            "medium" if outlier_score < cfg.strong_threshold else "high",
            "Outlier indicator score is elevated, but it is treated as a quality flag rather than a primary role.",
            round(outlier_score, 6),
        ))
    if ambiguous_core_roles:
        quality_flags.append(_quality_flag(
            "ambiguous_top_roles",
            "medium",
            "The two strongest core roles are close in score.",
            round(core_role_gap, 6),
        ))
    if generic_overclaim_risk:
        quality_flags.append(_quality_flag(
            "generic_overclaim_risk",
            "medium" if high_core_override_available else "high",
            "Family/prototype/anchor evidence is generic; strong Hub/Boundary evidence is retained when present, but the claim should be reviewed.",
            round(anchor_strength, 6),
        ))
    if all_missing_rate > cfg.warning_missing_rate_threshold:
        quality_flags.append(_quality_flag(
            "high_missingness",
            "medium",
            "Average missing-value rate is high.",
            round(all_missing_rate, 6),
        ))
    if multi_pool > cfg.warning_pool_overlap_threshold:
        quality_flags.append(_quality_flag(
            "pool_overlap",
            "low" if multi_pool < 100 else "medium",
            "Candidate IDs appear in multiple pools; evidence is not fully independent.",
            int(multi_pool),
        ))
    if primary_strength in {"weak", "very_weak"}:
        quality_flags.append(_quality_flag(
            "weak_primary_role",
            "medium",
            "The highest-ranked core role is weak or very weak.",
            primary_strength,
        ))

    # Secondary descriptors for the `Other` class. These descriptors explain why
    # the material is not currently defended as Hub or Boundary. They do not
    # change Hub/Boundary scores.
    secondary_descriptors: List[Dict[str, Any]] = []
    if bridge_diagnostic_strength >= 0.45 and balanced_multi_pool_similarity >= 0.30 and competing_membership_strength >= 0.30:
        secondary_descriptors.append(_descriptor_row(
            "bridge-like",
            "moderate" if bridge_diagnostic_strength < 0.70 else "strong",
            "Shows balanced or competing evidence across multiple neighbourhoods, but Phase 1 does not treat Bridge as a validated primary role.",
            {
                "bridge_diagnostic_strength": round(bridge_diagnostic_strength, 6),
                "balanced_multi_pool_similarity": round(balanced_multi_pool_similarity, 6),
                "competing_membership_strength": round(competing_membership_strength, 6),
                "structural_interpolation_score": round(structural_interpolation_score, 6),
            },
        ))
    if competing_membership_strength >= 0.40 or bridge_evidence_entropy >= 0.55:
        secondary_descriptors.append(_descriptor_row(
            "mixed-membership",
            "moderate" if max(competing_membership_strength, bridge_evidence_entropy) < 0.70 else "strong",
            "Evidence is distributed across multiple pools rather than concentrated in one clear Hub or Boundary interpretation.",
            {
                "competing_membership_strength": round(competing_membership_strength, 6),
                "bridge_evidence_entropy": round(bridge_evidence_entropy, 6),
            },
        ))
    if primary_strength in {"weak", "very_weak"} or top_core_score < cfg.partial_threshold:
        secondary_descriptors.append(_descriptor_row(
            "weak-evidence",
            "moderate",
            "The strongest Hub/Boundary role is weak or below the partial-support threshold.",
            {"top_hub_boundary_score": round(top_core_score, 6), "top_hub_boundary_strength": primary_strength},
        ))
    if evidence_sufficiency_status == "insufficient":
        secondary_descriptors.append(_descriptor_row(
            "insufficient evidence",
            "strong",
            "Evidence sufficiency gate is below threshold; the engine should not defend Hub or Boundary.",
            {"evidence_sufficiency_score": round(evidence_sufficiency_score, 6)},
        ))
    if outlier_score >= cfg.possible_outlier_threshold:
        secondary_descriptors.append(_descriptor_row(
            "outlier-like",
            "moderate" if outlier_score < cfg.strong_threshold else "strong",
            "Outlier indicator is elevated, suggesting weak connection to the reference landscape.",
            {"outlier_indicator_score": round(outlier_score, 6)},
        ))
    if family_specificity < cfg.minimum_family_specificity or structural_specificity < cfg.minimum_structural_specificity:
        secondary_descriptors.append(_descriptor_row(
            "family-ambiguous",
            "moderate",
            "Family/prototype/structure-variant evidence is too generic or unstable for a confident primary role.",
            {
                "family_specificity": round(family_specificity, 6),
                "structural_specificity": round(structural_specificity, 6),
            },
        ))
    if same_formula_match >= 0.60 and same_variant_match < 0.50 and max(adj_variant_entropy, boundary_variant_entropy) >= 0.40:
        secondary_descriptors.append(_descriptor_row(
            "polymorph-sensitive",
            "moderate",
            "Formula-family evidence is present, but structure-variant evidence is diverse or unstable, so the role may depend on the selected polymorph/JARVIS entry.",
            {
                "same_formula_match": round(same_formula_match, 6),
                "same_structure_variant_match": round(same_variant_match, 6),
                "adjacent_variant_entropy": round(adj_variant_entropy, 6),
                "boundary_variant_entropy": round(boundary_variant_entropy, 6),
            },
        ))

    # De-duplicate descriptors while preserving first reason.
    seen_descriptors = set()
    secondary_descriptors = [d for d in secondary_descriptors if not (d["descriptor"] in seen_descriptors or seen_descriptors.add(d["descriptor"]))]
    secondary_descriptor_names = [d["descriptor"] for d in secondary_descriptors]

    if no_strong_role:
        primary_role = "other"
        primary_strength = "assigned"
        # Deliberately no Other score: Other is the rejection of unsupported
        # Hub/Boundary evidence, not a competing numeric role. Keep confidence
        # as an assignment/review indicator only.
        primary_score = None
        primary_confidence = round(_clip01(max(1.0 - top_core_score, 1.0 - evidence_sufficiency_score, outlier_score)), 6)
        secondary_role = top_core.get("role") if top_core else None
    else:
        secondary_descriptor_names = []
        secondary_descriptors = []

    flag_names = [f["flag"] for f in quality_flags]
    if evidence_sufficiency_status == "insufficient":
        classification_quality = "insufficient"
    elif any(f["severity"] == "high" for f in quality_flags):
        classification_quality = "caution"
    elif ambiguous_core_roles or primary_strength in {"weak", "moderate"}:
        classification_quality = "review"
    else:
        classification_quality = "good"

    supported = [r for r in core_sorted_roles if r.get("supported")]
    partial = [r for r in core_sorted_roles if r.get("partial")]
    unsupported_roles = [r["role"] for r in core_sorted_roles if r.get("unsupported")]
    top_2_roles = (["other"] + [r["role"] for r in core_sorted_roles[:1]]) if primary_role == "other" else [r["role"] for r in core_sorted_roles[:2]]

    if primary_role == "other":
        final_assessment = f"primary_role_supported:other;flags:no_supported_hub_or_boundary"
    else:
        final_assessment = f"primary_role_supported:{primary_role};strength:{primary_strength}"

    # Backwards-compatible plausibility table. It includes core-role strength bands
    # plus the outlier quality indicator row, but primary classification should use
    # core_role_profile / final_assessment, not the outlier row.
    role_rows = []
    for row_item in role_ranking:
        role_rows.append(row_item)
    if primary_role == "other":
        other_row = {
            "rank": 1,
            "role": "other",
            "raw_prior_score": primary_score,
            "prior_score": primary_score,
            "confidence": primary_confidence,
            "strength_band": "assigned",
            "strength_rank": _strength_rank("moderate"),
            "plausibility": "supported",
            "supported": True,
            "partial": False,
            "unsupported": False,
            "top_1": True,
            "top_2": True,
            "evidence_strength": primary_confidence,
            "supporting_evidence_count": len(secondary_descriptors),
            "contradiction_count": 0,
            "contradiction_penalty": 0.0,
            "canonical_boundary_score_penalty": 0.0,
            "is_core_role": True,
            "is_quality_indicator": False,
        }
        role_rows.insert(0, other_row)
        role_strength_table.insert(0, {
            **other_row,
            "interpretation": "Other is assigned because neither Hub nor Boundary is sufficiently defended; secondary descriptors explain the ambiguity.",
        })
    if outlier_record:
        role_rows.append({
            "rank": None,
            "role": "outlier",
            "raw_prior_score": outlier_record.get("raw_prior_score"),
            "prior_score": outlier_record.get("prior_score"),
            "confidence": outlier_record.get("confidence"),
            "strength_band": outlier_strength,
            "strength_rank": _strength_rank(outlier_strength),
            "plausibility": outlier_record.get("plausibility"),
            "supported": False,
            "partial": False,
            "unsupported": True,
            "top_1": False,
            "top_2": False,
            "evidence_strength": None,
            "supporting_evidence_count": len(outlier_record.get("supporting_evidence", [])),
            "contradiction_count": len(outlier_record.get("contradictions", [])),
            "contradiction_penalty": outlier_record.get("contradiction_penalty"),
            "canonical_boundary_score_penalty": outlier_record.get("canonical_boundary_score_penalty", 0.0),
            "is_core_role": False,
            "is_quality_indicator": True,
        })

    # ------------------------------------------------------------------
    # Hub vs Boundary diagnostics only.
    # ------------------------------------------------------------------
    # These fields explain the Hub/Boundary decision without changing any score,
    # threshold, strength band, or primary-role assignment. They are deliberately
    # computed after role scoring so they cannot quietly bias the result.
    hub_record = role_records.get("hub", {})
    boundary_record = role_records.get("boundary", {})
    hub_components = hub_record.get("components", {}) if isinstance(hub_record, dict) else {}
    boundary_components = boundary_record.get("components", {}) if isinstance(boundary_record, dict) else {}

    hub_score = _safe_float(hub_record.get("prior_score"), 0.0) if isinstance(hub_record, dict) else 0.0
    boundary_score = _safe_float(boundary_record.get("prior_score"), 0.0) if isinstance(boundary_record, dict) else 0.0
    hub_confidence = _safe_float(hub_record.get("confidence"), 0.0) if isinstance(hub_record, dict) else 0.0
    boundary_confidence = _safe_float(boundary_record.get("confidence"), 0.0) if isinstance(boundary_record, dict) else 0.0
    hub_strength = hub_record.get("strength_band") if isinstance(hub_record, dict) else None
    boundary_strength = boundary_record.get("strength_band") if isinstance(boundary_record, dict) else None
    hub_support_count = len(hub_record.get("supporting_evidence", []) or []) if isinstance(hub_record, dict) else 0
    boundary_support_count = len(boundary_record.get("supporting_evidence", []) or []) if isinstance(boundary_record, dict) else 0
    hub_contradiction_count = len(hub_record.get("contradictions", []) or []) if isinstance(hub_record, dict) else 0
    boundary_contradiction_count = len(boundary_record.get("contradictions", []) or []) if isinstance(boundary_record, dict) else 0

    signed_hub_minus_boundary_score_gap = hub_score - boundary_score
    signed_hub_minus_boundary_confidence_gap = hub_confidence - boundary_confidence
    diagnostic_winner_by_score = "hub" if signed_hub_minus_boundary_score_gap > 0 else ("boundary" if signed_hub_minus_boundary_score_gap < 0 else "tie")
    diagnostic_winner_by_confidence = "hub" if signed_hub_minus_boundary_confidence_gap > 0 else ("boundary" if signed_hub_minus_boundary_confidence_gap < 0 else "tie")

    hub_same_family_coherence_proxy = _clip01(_mean_available([
        hub_components.get("same_composition_match"),
        hub_components.get("same_material_match"),
        hub_components.get("same_formula_match"),
        hub_components.get("same_prototype_match"),
        hub_components.get("same_family_stable_fraction"),
        hub_components.get("same_family_known_synthesized"),
    ]))
    hub_prototype_dominance_proxy = _clip01(max(
        _safe_float(hub_components.get("same_prototype_match"), 0.0),
        _safe_float(hub_components.get("canonical_prototype_bonus"), 0.0),
    ))
    boundary_regime_separation_proxy = _clip01(_mean_available([
        boundary_components.get("different_spacegroup"),
        boundary_components.get("different_crystal_system"),
        boundary_components.get("different_structure_variant"),
        boundary_components.get("symmetry_distance"),
        boundary_components.get("symmetry_entropy"),
    ]))
    boundary_context_anchor_proxy = _clip01(_mean_available([
        boundary_components.get("same_formula_or_prototype_context"),
        boundary_components.get("boundary_stability"),
    ]))

    hub_boundary_explanation = []
    if ambiguous_core_roles:
        hub_boundary_explanation.append("Hub and Boundary are close in score; treat the top role as a reviewable interpretation rather than a clean separation.")
    if diagnostic_winner_by_score == "hub":
        hub_boundary_explanation.append("Hub has the higher adjusted score among the two primary roles.")
    elif diagnostic_winner_by_score == "boundary":
        hub_boundary_explanation.append("Boundary has the higher adjusted score among the two primary roles.")
    else:
        hub_boundary_explanation.append("Hub and Boundary have equal adjusted scores after rounding.")
    if hub_same_family_coherence_proxy >= boundary_regime_separation_proxy + 0.08:
        hub_boundary_explanation.append("Same-family coherence is stronger than boundary regime-separation evidence.")
    elif boundary_regime_separation_proxy >= hub_same_family_coherence_proxy + 0.08:
        hub_boundary_explanation.append("Boundary regime-separation evidence is stronger than same-family coherence.")
    else:
        hub_boundary_explanation.append("Same-family coherence and boundary regime-separation evidence are broadly balanced.")
    if hub_contradiction_count > boundary_contradiction_count:
        hub_boundary_explanation.append("Hub has more contradiction flags than Boundary.")
    elif boundary_contradiction_count > hub_contradiction_count:
        hub_boundary_explanation.append("Boundary has more contradiction flags than Hub.")

    hub_boundary_diagnostics = {
        "hub_score": round(hub_score, 6),
        "boundary_score": round(boundary_score, 6),
        "hub_confidence": round(hub_confidence, 6),
        "boundary_confidence": round(boundary_confidence, 6),
        "hub_strength_band": hub_strength,
        "boundary_strength_band": boundary_strength,
        "signed_hub_minus_boundary_score_gap": round(signed_hub_minus_boundary_score_gap, 6),
        "absolute_hub_boundary_score_gap": round(abs(signed_hub_minus_boundary_score_gap), 6),
        "signed_hub_minus_boundary_confidence_gap": round(signed_hub_minus_boundary_confidence_gap, 6),
        "absolute_hub_boundary_confidence_gap": round(abs(signed_hub_minus_boundary_confidence_gap), 6),
        "diagnostic_winner_by_score": diagnostic_winner_by_score,
        "diagnostic_winner_by_confidence": diagnostic_winner_by_confidence,
        "hub_supporting_evidence_count": hub_support_count,
        "boundary_supporting_evidence_count": boundary_support_count,
        "supporting_evidence_count_gap_hub_minus_boundary": hub_support_count - boundary_support_count,
        "hub_contradiction_count": hub_contradiction_count,
        "boundary_contradiction_count": boundary_contradiction_count,
        "contradiction_count_gap_hub_minus_boundary": hub_contradiction_count - boundary_contradiction_count,
        "hub_boundary_ambiguity_flag": bool(ambiguous_core_roles),
        "hub_boundary_score_gap_threshold": cfg.ambiguous_role_margin,
        "hub_same_family_coherence_proxy": round(hub_same_family_coherence_proxy, 6),
        "hub_prototype_dominance_proxy": round(hub_prototype_dominance_proxy, 6),
        "boundary_regime_separation_proxy": round(boundary_regime_separation_proxy, 6),
        "boundary_context_anchor_proxy": round(boundary_context_anchor_proxy, 6),
        "diagnostic_explanation": " ".join(hub_boundary_explanation),
    }

    # ------------------------------------------------------------------
    # Case-level diagnostic summaries only.
    # ------------------------------------------------------------------
    # These summaries are deliberately downstream of scoring. They format existing
    # evidence into review-friendly explanations and do not alter any score,
    # threshold, strength band, primary role, or secondary descriptor.

    def _item_texts(items: Any, limit: int = 3) -> str:
        if not isinstance(items, list):
            return ""
        texts: List[str] = []
        for item in items:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("reason") or item.get("summary") or "").strip()
                value = item.get("value")
                if text and value not in (None, ""):
                    text = f"{text} (value={value})"
            else:
                text = str(item).strip()
            if text:
                texts.append(text)
            if len(texts) >= limit:
                break
        return " | ".join(texts)

    def _role_support_summary(role: str) -> str:
        rr = role_records.get(role, {})
        if not isinstance(rr, dict):
            return "No role record available."
        text = _item_texts(rr.get("supporting_evidence", []), limit=3)
        if text:
            return text
        score = _safe_float(rr.get("prior_score"), 0.0)
        strength = rr.get("strength_band") or "unknown"
        return f"No strong supporting evidence items listed; score={score:.3f}, strength={strength}."

    def _role_rejection_summary(role: str) -> str:
        rr = role_records.get(role, {})
        if not isinstance(rr, dict):
            return "No role record available."
        text = _item_texts(rr.get("contradictions", []), limit=3)
        if text:
            return text
        strength = rr.get("strength_band") or "unknown"
        plaus = rr.get("plausibility") or "unknown"
        if role == primary_role:
            return f"Not rejected; selected as primary role with strength={strength}, plausibility={plaus}."
        return f"Not selected as primary role; strength={strength}, plausibility={plaus}."

    def _gap_band(abs_gap: float) -> str:
        if abs_gap < 0.03:
            return "very_ambiguous"
        if abs_gap < 0.08:
            return "ambiguous"
        if abs_gap < 0.15:
            return "moderately_separated"
        return "clearly_separated"

    def _secondary_descriptor_explanation() -> str:
        if not secondary_descriptors:
            return "No secondary descriptors assigned."
        parts: List[str] = []
        for desc in secondary_descriptors:
            if not isinstance(desc, dict):
                continue
            name = desc.get("descriptor") or desc.get("name")
            strength = desc.get("strength") or "unspecified"
            reason = desc.get("reason") or desc.get("summary") or "No reason recorded."
            parts.append(f"{name} ({strength}): {reason}")
        return " | ".join(parts) if parts else "Secondary descriptor details not available."

    def _other_classification_reason() -> str:
        if primary_role != "other":
            return "Not classified as Other."
        reasons: List[str] = []
        hub_band = str(hub_strength or "unknown")
        boundary_band = str(boundary_strength or "unknown")
        reasons.append(f"Hub strength={hub_band}; Boundary strength={boundary_band}.")
        if evidence_sufficiency.get("status") == "insufficient":
            reasons.append("Evidence sufficiency gate indicates insufficient contextual evidence.")
        if secondary_descriptor_names:
            reasons.append("Secondary descriptors explain the non-Hub/non-Boundary signal: " + ";".join(secondary_descriptor_names) + ".")
        if flag_names:
            reasons.append("Quality flags: " + ";".join(flag_names) + ".")
        return " ".join(reasons)

    def _review_recommendation() -> str:
        recs: List[str] = []
        abs_gap = abs(signed_hub_minus_boundary_score_gap)
        if primary_role == "hub" and ambiguous_core_roles:
            recs.append("Review Hub/Boundary ambiguity; Hub is primary but Boundary is close.")
        elif primary_role == "boundary" and ambiguous_core_roles:
            recs.append("Review Hub/Boundary ambiguity; Boundary is primary but Hub is close.")
        elif primary_role == "boundary" and boundary_score >= 0.70 and abs_gap >= cfg.ambiguous_role_margin:
            recs.append("Boundary assignment appears robust under current Phase 1 diagnostics.")
        elif primary_role == "hub" and hub_score >= 0.70 and abs_gap >= cfg.ambiguous_role_margin:
            recs.append("Hub assignment appears robust under current Phase 1 diagnostics.")
        elif primary_role == "other":
            recs.append("Review secondary descriptors and evidence sufficiency before treating this as a locked validation case.")
        if "generic_overclaim_risk" in flag_names:
            recs.append("Check whether the assignment depends on broad/generic family evidence.")
        if "polymorph_sensitive" in flag_names:
            recs.append("Check the selected JARVIS structure or external polymorph before literature-locking.")
        if not recs:
            recs.append("No special review recommendation beyond normal validation checks.")
        return " ".join(recs)

    score_gap_band = _gap_band(abs(signed_hub_minus_boundary_score_gap))
    confidence_gap_band = _gap_band(abs(signed_hub_minus_boundary_confidence_gap))
    hub_support_summary = _role_support_summary("hub")
    hub_rejection_summary = _role_rejection_summary("hub")
    boundary_support_summary = _role_support_summary("boundary")
    boundary_rejection_summary = _role_rejection_summary("boundary")
    other_reason = _other_classification_reason()
    sec_desc_explanation = _secondary_descriptor_explanation()
    review_recommendation = _review_recommendation()

    role_explanation_summary = {
        "jid": query.get("jid"),
        "external_id": query.get("external_id"),
        "formula": query.get("formula"),
        "primary_role": primary_role,
        "primary_role_strength": primary_strength,
        "classification_quality": classification_quality,
        "hub_support_summary": hub_support_summary,
        "hub_rejection_summary": hub_rejection_summary,
        "boundary_support_summary": boundary_support_summary,
        "boundary_rejection_summary": boundary_rejection_summary,
        "hub_boundary_comparison_summary": " ".join(hub_boundary_explanation),
        "other_classification_reason": other_reason,
        "secondary_descriptor_explanation": sec_desc_explanation,
        "review_recommendation": review_recommendation,
    }

    case_diagnostic_summary = {
        "jid": query.get("jid"),
        "external_id": query.get("external_id"),
        "formula": query.get("formula"),
        "primary_role": primary_role,
        "primary_role_strength": primary_strength,
        "primary_role_score": round(_safe_float(primary_score), 6),
        "primary_role_confidence": round(_safe_float(primary_confidence), 6),
        "secondary_role": secondary_role,
        "secondary_role_strength": second_core.get("strength_band") if second_core else None,
        "hub_score": round(hub_score, 6),
        "boundary_score": round(boundary_score, 6),
        "hub_confidence": round(hub_confidence, 6),
        "boundary_confidence": round(boundary_confidence, 6),
        "hub_boundary_score_gap": round(signed_hub_minus_boundary_score_gap, 6),
        "absolute_hub_boundary_score_gap": round(abs(signed_hub_minus_boundary_score_gap), 6),
        "hub_boundary_score_gap_band": score_gap_band,
        "hub_boundary_confidence_gap": round(signed_hub_minus_boundary_confidence_gap, 6),
        "absolute_hub_boundary_confidence_gap": round(abs(signed_hub_minus_boundary_confidence_gap), 6),
        "hub_boundary_confidence_gap_band": confidence_gap_band,
        "hub_boundary_ambiguity_flag": bool(ambiguous_core_roles),
        "diagnostic_winner_by_score": diagnostic_winner_by_score,
        "diagnostic_winner_by_confidence": diagnostic_winner_by_confidence,
        "hub_supporting_evidence_count": hub_support_count,
        "boundary_supporting_evidence_count": boundary_support_count,
        "hub_contradiction_count": hub_contradiction_count,
        "boundary_contradiction_count": boundary_contradiction_count,
        "hub_same_family_coherence_proxy": round(hub_same_family_coherence_proxy, 6),
        "hub_prototype_dominance_proxy": round(hub_prototype_dominance_proxy, 6),
        "boundary_regime_separation_proxy": round(boundary_regime_separation_proxy, 6),
        "boundary_context_anchor_proxy": round(boundary_context_anchor_proxy, 6),
        "hub_support_summary": hub_support_summary,
        "hub_rejection_summary": hub_rejection_summary,
        "boundary_support_summary": boundary_support_summary,
        "boundary_rejection_summary": boundary_rejection_summary,
        "other_classification_reason": other_reason,
        "secondary_descriptors": ";".join(secondary_descriptor_names),
        "secondary_descriptor_explanation": sec_desc_explanation,
        "quality_flags": ";".join(flag_names),
        "classification_quality": classification_quality,
        "evidence_sufficiency_status": evidence_sufficiency.get("status"),
        "evidence_sufficiency_score": evidence_sufficiency.get("score"),
        "review_recommendation": review_recommendation,
    }

    diagnostic_metrics_flat = {
        **hub_boundary_diagnostics,
        "balanced_multi_pool_similarity": round(_clip01(balanced_multi_pool_similarity), 6),
        "competing_membership_strength": round(_clip01(competing_membership_strength), 6),
        "structural_interpolation_score": round(_clip01(structural_interpolation_score), 6),
        "coordination_transition_proxy": round(_clip01(coordination_transition_proxy), 6),
        "bridge_evidence_entropy": round(_clip01(bridge_evidence_entropy), 6),
        "bridge_diagnostic_strength": round(_clip01(bridge_diagnostic_strength), 6),
        "same_family_query_similarity_score": round(_clip01(same_query_similarity), 6),
        "adjacent_family_query_similarity_score": round(_clip01(adj_query_similarity), 6),
        "boundary_contrast_query_similarity_score": round(_clip01(boundary_query_similarity), 6),
        "wildcard_query_similarity_score": round(_clip01(wildcard_query_similarity), 6),
    }


    structural_context_profile_shell = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": _now(),
        "query": query,
        "inputs": {
            "phase1_schema_version": query_profile.get("schema_version"),
            "phase3_schema_version": evidence_summary.get("schema_version"),
        },
        "evidence_sufficiency": evidence_sufficiency,
        "final_assessment": {
            "status": final_assessment,
            "primary_role": primary_role,
            "primary_role_strength": primary_strength,
            "primary_role_score": primary_score,
            "primary_role_confidence": primary_confidence,
            "secondary_role": secondary_role,
            "secondary_role_strength": second_core.get("strength_band") if second_core else None,
            "secondary_descriptors": secondary_descriptor_names,
            "classification_quality": classification_quality,
            "quality_flags": flag_names,
            "no_strong_role_supported": no_strong_role,
            "possible_outlier": any(f["flag"] == "possible_outlier" for f in quality_flags),
            "ambiguous_core_roles": ambiguous_core_roles,
            "review_recommendation": review_recommendation,
        },
        "quality_flags": quality_flags,
        "case_diagnostic_summary": case_diagnostic_summary,
        "role_explanation_summary": role_explanation_summary,
    }

    profile_created_at = _now()
    structural_context_profile = {
        "schema_version": "phase1.structural_context_profile.v1",
        "created_at_utc": profile_created_at,
        "scope_note": (
            "Legacy transition profile. This is a Phase 1 structural-context measurement report. It is not a property prediction, "
            "synthesis prediction, DFT replacement, or candidate-ranking recommendation."
        ),
        "query_material": query,
        "pool_context_summary": _profile_pool_context_summary(query, evidence_summary, pool_df),
        "measurements": _profile_context_measurements(
            hub_score=hub_score,
            boundary_score=boundary_score,
            hub_confidence=hub_confidence,
            boundary_confidence=boundary_confidence,
            evidence_sufficiency=evidence_sufficiency,
            hub_boundary_diagnostics=hub_boundary_diagnostics,
        ),
        "interpretation": _profile_interpretation(structural_context_profile_shell),
        "diagnostics": _profile_diagnostics(structural_context_profile_shell),
    }
    structural_context_profile_v2 = _build_structural_context_profile_v2(
        query=query,
        query_profile=query_profile,
        evidence_summary=evidence_summary,
        pool_df=pool_df,
        legacy_profile=structural_context_profile,
        cfg=cfg,
        created_at_utc=profile_created_at,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": _now(),
        "query": query,
        "configuration": asdict(cfg),
        "inputs": {
            "phase1_schema_version": query_profile.get("schema_version"),
            "phase3_schema_version": evidence_summary.get("schema_version"),
        },
        "role_records": role_records,
        "core_roles": CORE_ROLES,
        "core_role_profile": {
            "primary_role": primary_role,
            "primary_role_strength": primary_strength,
            "primary_role_score": primary_score,
            "primary_role_confidence": primary_confidence,
            "secondary_role": secondary_role,
            "secondary_role_strength": second_core.get("strength_band") if second_core else None,
            "secondary_role_score": second_core.get("prior_score") if second_core else None,
            "role_margin": round(core_role_gap, 6),
            "role_separation": round(core_role_separation, 6),
            "ambiguous_core_roles": ambiguous_core_roles,
            "classification_quality": classification_quality,
        },
        "role_ranking": role_ranking,
        "core_role_ranking": role_ranking,
        "top_2_roles": top_2_roles,
        "ranked_explanations": ranked_explanations,
        "role_strength_table": role_strength_table,
        "quality_flags": quality_flags,
        "quality_flag_names": flag_names,
        "quality_indicator_records": {
            "outlier": outlier_record,
        },
        "role_plausibility_table": role_rows,
        "role_contradictions": contradictions_rows,
        "evidence_sufficiency": evidence_sufficiency,
        "secondary_descriptors": secondary_descriptors,
        "secondary_descriptor_names": secondary_descriptor_names,
        "case_diagnostic_summary": case_diagnostic_summary,
        "role_explanation_summary": role_explanation_summary,
        "diagnostic_metrics": {
            "hub_boundary_diagnostics": hub_boundary_diagnostics,
            "bridge_evidence_profile": {
                "balanced_multi_pool_similarity": round(_clip01(balanced_multi_pool_similarity), 6),
                "competing_membership_strength": round(_clip01(competing_membership_strength), 6),
                "structural_interpolation_score": round(_clip01(structural_interpolation_score), 6),
                "coordination_transition_proxy": round(_clip01(coordination_transition_proxy), 6),
                "bridge_evidence_entropy": round(_clip01(bridge_evidence_entropy), 6),
                "bridge_diagnostic_strength": round(_clip01(bridge_diagnostic_strength), 6),
                "same_family_query_similarity_score": round(_clip01(same_query_similarity), 6),
                "adjacent_family_query_similarity_score": round(_clip01(adj_query_similarity), 6),
                "boundary_contrast_query_similarity_score": round(_clip01(boundary_query_similarity), 6),
                "wildcard_query_similarity_score": round(_clip01(wildcard_query_similarity), 6),
            },
            "flat": diagnostic_metrics_flat,
        },
        "hub_boundary_diagnostics": hub_boundary_diagnostics,
        "structural_context_profile": structural_context_profile,
        "structural_context_profile_v2": structural_context_profile_v2,
        "bridge_evidence_profile": {
            "balanced_multi_pool_similarity": round(_clip01(balanced_multi_pool_similarity), 6),
            "competing_membership_strength": round(_clip01(competing_membership_strength), 6),
            "structural_interpolation_score": round(_clip01(structural_interpolation_score), 6),
            "coordination_transition_proxy": round(_clip01(coordination_transition_proxy), 6),
            "bridge_evidence_entropy": round(_clip01(bridge_evidence_entropy), 6),
            "bridge_diagnostic_strength": round(_clip01(bridge_diagnostic_strength), 6),
        },
        "final_assessment": {
            "status": final_assessment,
            "primary_role": primary_role,
            "primary_role_strength": primary_strength,
            "primary_role_score": primary_score,
            "primary_role_confidence": primary_confidence,
            "secondary_role": secondary_role,
            "secondary_role_strength": second_core.get("strength_band") if second_core else None,
            "secondary_descriptors": secondary_descriptor_names,
            "secondary_descriptor_details": secondary_descriptors,
            "top_role_by_score": primary_role,
            "secondary_role_by_score": secondary_role,
            "top_2_roles": top_2_roles,
            "supported_roles": [r["role"] for r in supported],
            "partial_roles": [r["role"] for r in partial],
            "unsupported_roles": unsupported_roles,
            "no_strong_role_supported": no_strong_role,
            "possible_outlier": any(f["flag"] == "possible_outlier" for f in quality_flags),
            "quality_flags": flag_names,
            "classification_quality": classification_quality,
            "ambiguous_supported_roles": ambiguous_core_roles,
            "ambiguous_core_roles": ambiguous_core_roles,
            "hub_boundary_score_gap": hub_boundary_diagnostics.get("signed_hub_minus_boundary_score_gap"),
            "hub_boundary_confidence_gap": hub_boundary_diagnostics.get("signed_hub_minus_boundary_confidence_gap"),
            "hub_boundary_diagnostic_winner_by_score": hub_boundary_diagnostics.get("diagnostic_winner_by_score"),
            "hub_boundary_diagnostic_explanation": hub_boundary_diagnostics.get("diagnostic_explanation"),
            "outlier_indicator_score": round(outlier_score, 6),
            "outlier_indicator_strength": outlier_strength,
            "review_recommendation": review_recommendation,
            "other_classification_reason": other_reason,
            "secondary_descriptor_explanation": sec_desc_explanation,
        },
        "warnings": warnings,
        "source_evidence_summary": {
            "role_signal_summary": role_signal,
            "overlap_summary": overlap,
        },
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _md_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    if not rows:
        return ""
    out = []
    out.append("| " + " | ".join(columns) + " |")
    out.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for r in rows:
        vals = [str(r.get(c, "")) for c in columns]
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def generate_report(record: Dict[str, Any]) -> str:
    q = record.get("query", {})
    final = record.get("final_assessment", {})
    roles = record.get("role_records", {})
    role_table = record.get("role_plausibility_table", [])

    title = f"Structural Context Role Prior Report: {q.get('jid') or 'external_material'}"
    lines = [
        f"# {title}",
        "",
        "## Scope",
        "",
        "This report uses Phase 1 material profile data and Phase 3 cheap evidence metrics only. It does not use local-structure ranking, DFT, property prediction, or experimental validation. Apparently restraint survived another sprint.",
        "",
        "## Query Material",
        "",
        f"- JID: {q.get('jid')}",
        f"- Formula: {q.get('formula')}",
        f"- Chemical system: {q.get('chemical_system')}",
        f"- Composition family: {q.get('composition_family')}",
        f"- Formula family: {q.get('formula_family')}",
        f"- Prototype family: {q.get('prototype_family')}",
        f"- Structure variant: {q.get('structure_variant')}",
        f"- Space group: {q.get('spacegroup_number')} {q.get('spacegroup_symbol') or ''}".strip(),
        "",
        "## Structural Context Profile",
        "",
        "This section restructures the existing Phase 1 outputs as a Structural Context Profile: pool evidence, measurements, interpretation, and diagnostics. It does not change scoring.",
        "",
        "### Measurements",
        "",
        _md_table([record.get("structural_context_profile", {}).get("measurements", {})], ["hub_strength", "boundary_strength", "evidence_sufficiency_score", "evidence_sufficiency_status", "neighbourhood_coherence", "context_ambiguity", "structural_diversity", "hub_boundary_score_gap"]),
        "",
        "### Pool Context Summary",
        "",
        _md_table([record.get("structural_context_profile", {}).get("pool_context_summary", {}).get("structural_neighbourhood", {})], ["same_family_pool_size", "adjacent_family_pool_size", "boundary_contrast_pool_size", "wildcard_pool_size", "negative_control_pool_size", "candidate_ids_in_multiple_pools", "unique_candidate_count_across_all_pools"]),
        "",
        "### Interpretation",
        "",
        _md_table([record.get("structural_context_profile", {}).get("interpretation", {})], ["primary_interpretation", "primary_interpretation_strength", "primary_interpretation_score", "secondary_interpretation"]),
        "",
        "## Overall Assessment",
        "",
        f"- Status: `{final.get('status')}`",
        f"- Primary core role: `{final.get('primary_role')}`",
        f"- Primary role strength: `{final.get('primary_role_strength')}`",
        f"- Primary role score: `{final.get('primary_role_score')}`",
        f"- Primary role confidence: `{final.get('primary_role_confidence')}`",
        f"- Secondary scored role: `{final.get('secondary_role') or final.get('secondary_role_by_score')}`",
        f"- Secondary descriptors: `{';'.join(final.get('secondary_descriptors', []) or [])}`",
        f"- Top-2 primary/scored roles: `{';'.join(final.get('top_2_roles', []) or [])}`",
        f"- Supported core roles: `{';'.join(final.get('supported_roles', []) or [])}`",
        f"- Partial core roles: `{';'.join(final.get('partial_roles', []) or [])}`",
        f"- Classification quality: `{final.get('classification_quality')}`",
        f"- Quality flags: `{';'.join(final.get('quality_flags', []) or [])}`",
        f"- No strong role supported flag: `{final.get('no_strong_role_supported')}`",
        f"- Possible outlier flag: `{final.get('possible_outlier')}`",
        "",
        "## Evidence Sufficiency",
        "",
        f"- Status: `{record.get('evidence_sufficiency', {}).get('status')}`",
        f"- Score: `{record.get('evidence_sufficiency', {}).get('score')}`",
        f"- Threshold: `{record.get('evidence_sufficiency', {}).get('threshold')}`",
        f"- Anchor strength: `{record.get('evidence_sufficiency', {}).get('anchor_strength')}`",
        f"- Family specificity: `{record.get('evidence_sufficiency', {}).get('family_specificity')}`",
        f"- Structural specificity: `{record.get('evidence_sufficiency', {}).get('structural_specificity')}`",
        f"- Negative-control separation: `{record.get('evidence_sufficiency', {}).get('negative_control_separation')}`",
        "",
        "## Primary Role Strength Profile",
        "",
        _md_table(record.get("role_strength_table", []), ["rank", "role", "prior_score", "confidence", "strength_band", "supported", "partial", "top_1", "top_2", "interpretation"]),
        "",
        "## Hub vs Boundary Diagnostic Explanation",
        "",
        _md_table([record.get("hub_boundary_diagnostics", {})], ["hub_score", "boundary_score", "signed_hub_minus_boundary_score_gap", "hub_confidence", "boundary_confidence", "signed_hub_minus_boundary_confidence_gap", "hub_strength_band", "boundary_strength_band", "hub_boundary_ambiguity_flag", "diagnostic_winner_by_score"]),
        "",
        f"- Explanation: {record.get('hub_boundary_diagnostics', {}).get('diagnostic_explanation')}",
        "",
        "## Case-Level Diagnostic Summary",
        "",
        _md_table([record.get("case_diagnostic_summary", {})], ["primary_role", "primary_role_strength", "hub_boundary_score_gap", "hub_boundary_score_gap_band", "hub_boundary_ambiguity_flag", "classification_quality", "review_recommendation"]),
        "",
        f"- Hub support: {record.get('case_diagnostic_summary', {}).get('hub_support_summary')}",
        f"- Hub rejection/limitation: {record.get('case_diagnostic_summary', {}).get('hub_rejection_summary')}",
        f"- Boundary support: {record.get('case_diagnostic_summary', {}).get('boundary_support_summary')}",
        f"- Boundary rejection/limitation: {record.get('case_diagnostic_summary', {}).get('boundary_rejection_summary')}",
        f"- Other classification reason: {record.get('case_diagnostic_summary', {}).get('other_classification_reason')}",
        f"- Secondary descriptor explanation: {record.get('case_diagnostic_summary', {}).get('secondary_descriptor_explanation')}",
        "",
        "### Hub vs Boundary Evidence Shape",
        "",
        _md_table([record.get("hub_boundary_diagnostics", {})], ["hub_same_family_coherence_proxy", "hub_prototype_dominance_proxy", "boundary_regime_separation_proxy", "boundary_context_anchor_proxy", "hub_supporting_evidence_count", "boundary_supporting_evidence_count", "hub_contradiction_count", "boundary_contradiction_count"]),
        "",
        "## Secondary Descriptors",
        "",
        _md_table(record.get("secondary_descriptors", []), ["descriptor", "strength", "reason"]),
        "",
        "## Bridge-like Diagnostic Metrics",
        "",
        _md_table([record.get("bridge_evidence_profile", {})], ["balanced_multi_pool_similarity", "competing_membership_strength", "structural_interpolation_score", "coordination_transition_proxy", "bridge_evidence_entropy", "bridge_diagnostic_strength"]),
        "",
        "## Quality Flags",
        "",
    ]
    qflags = record.get("quality_flags", [])
    if qflags:
        lines.append(_md_table(qflags, ["flag", "severity", "reason", "value"]))
    else:
        lines.append("- No quality flags recorded.")
    lines += [
        "",
        "## Role Plausibility Table",
        "",
        _md_table(role_table, ["rank", "role", "raw_prior_score", "prior_score", "confidence", "strength_band", "plausibility", "supported", "partial", "top_1", "top_2", "is_core_role", "is_quality_indicator", "evidence_strength", "supporting_evidence_count", "contradiction_count"]),
        "",
        "## Evidence and Contradictions by Role",
        "",
    ]

    for role in ["hub", "boundary", "bridge", "outlier"]:
        rec = roles.get(role, {})
        lines += [
            f"### {role.title()}",
            "",
            f"- Prior score: `{rec.get('prior_score')}`",
            f"- Confidence: `{rec.get('confidence')}`",
            f"- Plausibility: `{rec.get('plausibility')}`",
            "",
            "Supporting evidence:",
        ]
        for item in rec.get("supporting_evidence", []):
            lines.append(f"- {item.get('text')} Value: `{item.get('value')}`")
        if not rec.get("supporting_evidence"):
            lines.append("- None recorded.")
        lines += ["", "Contradictions / weakening evidence:"]
        for item in rec.get("contradictions", []):
            lines.append(f"- {item.get('text')} Value: `{item.get('value')}`")
        if not rec.get("contradictions"):
            lines.append("- None recorded.")
        lines.append("")

    warnings = record.get("warnings", [])
    lines += ["## Warnings", ""]
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- No major warnings recorded.")
    lines += [
        "",
        "## Reproducibility",
        "",
        f"- Schema version: `{record.get('schema_version')}`",
        f"- Created at UTC: `{record.get('created_at_utc')}`",
        f"- Phase 1 input schema: `{record.get('inputs', {}).get('phase1_schema_version')}`",
        f"- Phase 3 input schema: `{record.get('inputs', {}).get('phase3_schema_version')}`",
        "",
    ]
    return "\n".join(lines)


def run(query_profile_path: Path, evidence_dir: Path, output_dir: Path, cfg: RolePriorConfig, legacy_outputs: bool = True) -> Dict[str, Any]:
    evidence_dir = evidence_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    query_profile = _load_json(query_profile_path.expanduser().resolve())
    summary_path = evidence_dir / SUMMARY_FILE
    pool_path = evidence_dir / POOL_METRICS_FILE
    missing_path = evidence_dir / MISSING_FILE

    missing_required = [p for p in [summary_path, pool_path] if not p.exists()]
    if missing_required:
        raise FileNotFoundError("Missing required Phase 3 input(s): " + ", ".join(str(p) for p in missing_required))

    evidence_summary = _load_json(summary_path)
    pool_df = _load_csv(pool_path)
    missing_df = _load_csv(missing_path)

    record = build_role_priors(query_profile, evidence_summary, pool_df, missing_df, cfg)

    # Canonical Structural Context Profile v2 outputs.
    profile_v2 = record.get("structural_context_profile_v2", {}) or {}
    (output_dir / "structural_context_profile_v2.json").write_text(json.dumps(profile_v2, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(output_dir / "structural_context_profile_v2_measurements.csv", [profile_v2.get("relational_measurements", {})])
    _write_csv(output_dir / "structural_context_profile_v2_reliability.csv", [{
        "evidence_sufficiency_score": ((profile_v2.get("reliability_diagnostics", {}).get("evidence_sufficiency") or {}).get("score")),
        "evidence_sufficiency_status": ((profile_v2.get("reliability_diagnostics", {}).get("evidence_sufficiency") or {}).get("status")),
        "retrieval_completeness": ((profile_v2.get("reliability_diagnostics", {}).get("retrieval_completeness") or {}).get("score")),
        "pool_independence": ((profile_v2.get("reliability_diagnostics", {}).get("pool_independence") or {}).get("score")),
        "pool_overlap_rate": ((profile_v2.get("reliability_diagnostics", {}).get("pool_independence") or {}).get("pool_overlap_rate")),
        "context_ambiguity": ((profile_v2.get("reliability_diagnostics", {}).get("context_ambiguity") or {}).get("score")),
        "profile_confidence": ((profile_v2.get("reliability_diagnostics", {}).get("profile_confidence") or {}).get("score")),
        "profile_confidence_band": ((profile_v2.get("reliability_diagnostics", {}).get("profile_confidence") or {}).get("band")),
        "quality_flags": ";".join(profile_v2.get("reliability_diagnostics", {}).get("quality_flags", []) or []),
    }])
    _write_csv(output_dir / "structural_context_profile_v2_interpretation.csv", [{
        "contextual_pattern_code": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("code"))),
        "contextual_pattern_label": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("label"))),
        "contextual_pattern_summary": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("summary"))),
        "hub_like_interpretation": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("hub_like_interpretation"))),
        "boundary_like_interpretation": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("boundary_like_interpretation"))),
    }])
    _write_csv(output_dir / "structural_context_profile_v2_summary.csv", [{
        "jid": (profile_v2.get("query_material", {}) or {}).get("jid"),
        "formula": (profile_v2.get("query_material", {}) or {}).get("formula"),
        **(profile_v2.get("relational_measurements", {}) or {}),
        "evidence_sufficiency_score": ((profile_v2.get("reliability_diagnostics", {}).get("evidence_sufficiency") or {}).get("score")),
        "evidence_sufficiency_status": ((profile_v2.get("reliability_diagnostics", {}).get("evidence_sufficiency") or {}).get("status")),
        "retrieval_completeness": ((profile_v2.get("reliability_diagnostics", {}).get("retrieval_completeness") or {}).get("score")),
        "pool_independence": ((profile_v2.get("reliability_diagnostics", {}).get("pool_independence") or {}).get("score")),
        "context_ambiguity": ((profile_v2.get("reliability_diagnostics", {}).get("context_ambiguity") or {}).get("score")),
        "profile_confidence": ((profile_v2.get("reliability_diagnostics", {}).get("profile_confidence") or {}).get("score")),
        "profile_confidence_band": ((profile_v2.get("reliability_diagnostics", {}).get("profile_confidence") or {}).get("band")),
        "contextual_pattern": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("code"))),
        "contextual_pattern_label": (((profile_v2.get("interpretation", {}).get("contextual_pattern") or {}).get("label"))),
    }])

    pattern = (profile_v2.get("interpretation", {}).get("contextual_pattern") or {})
    rel = profile_v2.get("relational_measurements", {}) or {}
    reliability = profile_v2.get("reliability_diagnostics", {}) or {}
    v2_report_lines = [
        "# Structural Context Profile v2",
        "",
        f"- Candidate: `{(profile_v2.get('query_material', {}) or {}).get('jid')}`",
        f"- Formula: `{(profile_v2.get('query_material', {}) or {}).get('formula')}`",
        f"- Contextual pattern: **{pattern.get('label')}**",
        f"- Profile confidence: `{(reliability.get('profile_confidence') or {}).get('score')}` ({(reliability.get('profile_confidence') or {}).get('band')})",
        "",
        "## Relational measurements",
        "",
        f"- Local Context Support: `{rel.get('local_context_support')}` ({rel.get('local_context_support_band')})",
        f"- Structural Regime Contrast: `{rel.get('structural_regime_contrast')}` ({rel.get('structural_regime_contrast_band')})",
        f"- Neighbourhood Coherence: `{rel.get('neighbourhood_coherence')}`",
        f"- Structural Context Diversity: `{rel.get('structural_context_diversity')}` (provisional retained v1 aggregation)",
        "",
        "## Interpretation",
        "",
        str(pattern.get("summary") or "No contextual-pattern summary available."),
        "",
        "## Scope",
        "",
        str((profile_v2.get("scope_and_provenance", {}) or {}).get("scope_note") or ""),
        "",
    ]
    (output_dir / "structural_context_report_v2.md").write_text("\n".join(v2_report_lines), encoding="utf-8")

    # Transition compatibility outputs. Enabled by default for one release and
    # suppressible with --no-legacy_outputs.
    if legacy_outputs:
        (output_dir / "role_prior_summary.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        (output_dir / "structural_context_profile.json").write_text(json.dumps(record.get("structural_context_profile", {}), indent=2, ensure_ascii=False), encoding="utf-8")
        (output_dir / "structural_context_profile_v1.json").write_text(json.dumps(record.get("structural_context_profile", {}), indent=2, ensure_ascii=False), encoding="utf-8")
        _write_csv(output_dir / "structural_context_profile_measurements.csv", [record.get("structural_context_profile", {}).get("measurements", {})])
        _write_csv(output_dir / "structural_context_profile_pools.csv", [
            {"section": "structural_neighbourhood", **(record.get("structural_context_profile", {}).get("pool_context_summary", {}).get("structural_neighbourhood", {}) or {})},
            *[
                {"section": f"pool_{name}", **(summary or {})}
                for name, summary in (record.get("structural_context_profile", {}).get("pool_context_summary", {}).get("neighbourhood_characterisation", {}) or {}).items()
            ],
        ])
        _write_csv(output_dir / "structural_context_profile_interpretation.csv", [record.get("structural_context_profile", {}).get("interpretation", {})])
        _write_csv(output_dir / "structural_context_profile_diagnostics.csv", [record.get("structural_context_profile", {}).get("diagnostics", {})])
    if legacy_outputs:
        _write_csv(output_dir / "role_plausibility_table.csv", record["role_plausibility_table"])
        _write_csv(output_dir / "role_ranking.csv", record.get("role_ranking", []))
        _write_csv(output_dir / "role_ranked_explanations.csv", [
            {
                "rank": r.get("rank"),
                "role": r.get("role"),
                "summary": r.get("summary"),
                "plausibility": r.get("plausibility"),
                "evidence_strength": r.get("evidence_strength"),
                "supporting_evidence_text": r.get("supporting_evidence_text"),
                "contradiction_text": r.get("contradiction_text"),
            }
            for r in record.get("ranked_explanations", [])
        ])
        _write_csv(output_dir / "role_contradictions.csv", record["role_contradictions"])
        _write_csv(output_dir / "role_strength_table.csv", record.get("role_strength_table", []))
        _write_csv(output_dir / "role_quality_flags.csv", record.get("quality_flags", []))
        _write_csv(output_dir / "secondary_descriptors.csv", record.get("secondary_descriptors", []))
        _write_csv(output_dir / "hub_boundary_diagnostics.csv", [record.get("hub_boundary_diagnostics", {})])
        _write_csv(output_dir / "diagnostic_metrics.csv", [record.get("diagnostic_metrics", {}).get("flat", {})])
        _write_csv(output_dir / "case_diagnostic_summary.csv", [record.get("case_diagnostic_summary", {})])
        _write_csv(output_dir / "role_explanation_summary.csv", [record.get("role_explanation_summary", {})])

        # Phase 5 outputs
        report = generate_report(record)
        (output_dir / "structural_context_report.md").write_text(report, encoding="utf-8")
        _write_csv(output_dir / "structural_context_summary.csv", [{
            "jid": record["query"].get("jid"),
            "formula": record["query"].get("formula"),
            "status": record["final_assessment"].get("status"),
            "evidence_sufficiency_status": record.get("evidence_sufficiency", {}).get("status"),
            "evidence_sufficiency_score": record.get("evidence_sufficiency", {}).get("score"),
            "structural_specificity": record.get("evidence_sufficiency", {}).get("structural_specificity"),
            "primary_role": record["final_assessment"].get("primary_role"),
            "primary_role_strength": record["final_assessment"].get("primary_role_strength"),
            "primary_role_score": record["final_assessment"].get("primary_role_score"),
            "primary_role_confidence": record["final_assessment"].get("primary_role_confidence"),
            "secondary_role": record["final_assessment"].get("secondary_role"),
            "secondary_descriptors": ";".join(record["final_assessment"].get("secondary_descriptors", [])),
            "supported_roles": ";".join(record["final_assessment"].get("supported_roles", [])),
            "partial_roles": ";".join(record["final_assessment"].get("partial_roles", [])),
            "no_strong_role_supported": record["final_assessment"].get("no_strong_role_supported"),
            "possible_outlier": record["final_assessment"].get("possible_outlier"),
            "quality_flags": ";".join(record["final_assessment"].get("quality_flags", [])),
            "classification_quality": record["final_assessment"].get("classification_quality"),
            "hub_boundary_score_gap": record.get("hub_boundary_diagnostics", {}).get("signed_hub_minus_boundary_score_gap"),
            "hub_boundary_confidence_gap": record.get("hub_boundary_diagnostics", {}).get("signed_hub_minus_boundary_confidence_gap"),
            "hub_boundary_ambiguity_flag": record.get("hub_boundary_diagnostics", {}).get("hub_boundary_ambiguity_flag"),
            "hub_boundary_diagnostic_winner_by_score": record.get("hub_boundary_diagnostics", {}).get("diagnostic_winner_by_score"),
            "hub_boundary_diagnostic_explanation": record.get("hub_boundary_diagnostics", {}).get("diagnostic_explanation"),
            "hub_boundary_score_gap_band": record.get("case_diagnostic_summary", {}).get("hub_boundary_score_gap_band"),
            "review_recommendation": record.get("case_diagnostic_summary", {}).get("review_recommendation"),
            "other_classification_reason": record.get("case_diagnostic_summary", {}).get("other_classification_reason"),
            "secondary_descriptor_explanation": record.get("case_diagnostic_summary", {}).get("secondary_descriptor_explanation"),
            "outlier_indicator_score": record["final_assessment"].get("outlier_indicator_score"),
            "bridge_diagnostic_strength": record.get("bridge_evidence_profile", {}).get("bridge_diagnostic_strength"),
            "balanced_multi_pool_similarity": record.get("bridge_evidence_profile", {}).get("balanced_multi_pool_similarity"),
            "competing_membership_strength": record.get("bridge_evidence_profile", {}).get("competing_membership_strength"),
            "structural_interpolation_score": record.get("bridge_evidence_profile", {}).get("structural_interpolation_score"),
            "coordination_transition_proxy": record.get("bridge_evidence_profile", {}).get("coordination_transition_proxy"),
            "bridge_evidence_entropy": record.get("bridge_evidence_profile", {}).get("bridge_evidence_entropy"),
            "warning_count": len(record.get("warnings", [])),
        }])
    evidence_record = {
        "schema_version": "phase5.structural_context_evidence_record.v1",
        "created_at_utc": _now(),
        "query": record.get("query"),
        "evidence_sufficiency": record.get("evidence_sufficiency"),
        "final_assessment": record.get("final_assessment"),
        "core_role_profile": record.get("core_role_profile"),
        "secondary_descriptors": record.get("secondary_descriptors"),
        "diagnostic_metrics": record.get("diagnostic_metrics"),
        "case_diagnostic_summary": record.get("case_diagnostic_summary"),
        "role_explanation_summary": record.get("role_explanation_summary"),
        "structural_context_profile": record.get("structural_context_profile"),
        "structural_context_profile_v2": record.get("structural_context_profile_v2"),
        "role_strength_table": record.get("role_strength_table"),
        "quality_flags": record.get("quality_flags"),
        "role_records": record.get("role_records"),
        "warnings": record.get("warnings"),
        "source_files": {
            "query_profile": str(query_profile_path),
            "evidence_dir": str(evidence_dir),
        },
    }
    (output_dir / "structural_context_evidence_record.json").write_text(json.dumps(evidence_record, indent=2, ensure_ascii=False), encoding="utf-8")

    # Repro config
    (output_dir / "role_prior_config_used.json").write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    return record


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 4 role priors + Phase 5 reporting for cheap structural-context evidence.")
    p.add_argument("--query_profile", required=True, help="Path to Phase 1 query_profile.json.")
    p.add_argument("--evidence_dir", required=True, help="Path to Phase 3 evidence directory.")
    p.add_argument("--output_dir", required=True, help="Output directory for Phase 4/5 outputs.")
    p.add_argument("--strong_threshold", type=float, default=0.70)
    p.add_argument("--partial_threshold", type=float, default=0.45)
    p.add_argument("--confidence_high_threshold", type=float, default=0.70)
    p.add_argument("--confidence_partial_threshold", type=float, default=0.45)
    p.add_argument("--evidence_sufficiency_threshold", type=float, default=0.55)
    p.add_argument("--minimum_anchor_strength", type=float, default=0.35)
    p.add_argument("--minimum_family_specificity", type=float, default=0.25)
    p.add_argument("--minimum_structural_specificity", type=float, default=0.40)
    p.add_argument("--minimum_specific_anchor_for_strong_role", type=float, default=0.40)
    p.add_argument("--role_separation_threshold", type=float, default=0.08)
    p.add_argument("--contradiction_penalty_weight", type=float, default=0.035)
    p.add_argument(
        "--legacy_outputs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Write the v1 profile and legacy role-oriented outputs during the transition release. "
            "Enabled by default; use --no-legacy_outputs to suppress the duplicate v1 profile files."
        ),
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point for the role prior engine."""
    args = parse_args(argv)
    cfg = RolePriorConfig(
        strong_threshold=args.strong_threshold,
        partial_threshold=args.partial_threshold,
        confidence_high_threshold=args.confidence_high_threshold,
        confidence_partial_threshold=args.confidence_partial_threshold,
        evidence_sufficiency_threshold=args.evidence_sufficiency_threshold,
        minimum_anchor_strength=args.minimum_anchor_strength,
        minimum_family_specificity=args.minimum_family_specificity,
        minimum_structural_specificity=args.minimum_structural_specificity,
        minimum_specific_anchor_for_strong_role=args.minimum_specific_anchor_for_strong_role,
        role_separation_threshold=args.role_separation_threshold,
        contradiction_penalty_weight=args.contradiction_penalty_weight,
    )
    try:
        record = run(Path(args.query_profile), Path(args.evidence_dir), Path(args.output_dir), cfg, legacy_outputs=args.legacy_outputs)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    final = record.get("final_assessment", {})
    print("Structural Context Inference complete.")
    print(f"Status: {final.get('status')}")
    print(f"Evidence sufficiency: {record.get('evidence_sufficiency', {}).get('status')} ({record.get('evidence_sufficiency', {}).get('score')})")
    profile_v2 = record.get("structural_context_profile_v2", {}) or {}
    print(f"Contextual pattern: {((profile_v2.get('interpretation', {}).get('contextual_pattern') or {}).get('label'))}")
    print(f"Profile confidence: {((profile_v2.get('reliability_diagnostics', {}).get('profile_confidence') or {}).get('score'))}")
    print(f"Output directory: {Path(args.output_dir).expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())