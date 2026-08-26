"""
Material family classification utilities.

Overview
--------
This module identifies structural and compositional material families using
lightweight deterministic heuristics. Family classification provides semantic
context for downstream candidate-pool construction and evidence generation
without performing expensive crystallographic analysis.

Responsibilities
----------------
* Classify materials into supported structural families.
* Provide reproducible family labels and supporting metadata.
* Remain independent of downstream scoring and role inference.
* Support extension as additional material families are introduced.

Architectural role
------------------
This module is an upstream enrichment component used by
``material_profile_builder.py``. Its outputs are subsequently consumed by
candidate-pool construction and evidence generation but should not contain
pipeline-specific scoring logic.

Maintenance notes
-----------------
New family classifiers should be deterministic, well documented and added
without altering the behaviour of existing families. Where possible, preserve
backwards-compatible output fields so downstream modules remain stable.
"""
from __future__ import annotations

"""
material_family_classifier.py

Rule-based, cheap material-family classifier for Phase 1/2 of the LSF structural
context project.

Scope
-----
This module produces *evidence labels*, not ground truth. It is intentionally
conservative and emits confidence/warnings so downstream role-prior logic can
treat the labels as cheap evidence rather than divinely revealed crystallography,
which would be convenient but sadly unavailable.
"""

import math
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


CLASSIFIER_SCHEMA_VERSION = "phase1.material_family_classifier.v1.3_pyrochlore"


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _safe_int(value: Any) -> Optional[int]:
    if _is_missing(value):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _safe_str(value: Any) -> Optional[str]:
    if _is_missing(value):
        return None
    return str(value).strip()


def _normalise_symbol(symbol: str) -> str:
    if not symbol:
        return symbol
    return symbol[0].upper() + symbol[1:].lower()


def parse_formula_counts(formula: Any) -> Dict[str, float]:
    """
    Parse a simple chemical formula into element counts.

    Handles formulas like CaTiO3, Sr2TiO4, Ti3SiC2, Li10GeP2S12.
    It deliberately does not attempt full crystallographic formula grammar
    with parentheses/hydrates. If that arrives, it returns the best simple
    parse and lets the warning system do its job, because pretending otherwise
    would be software theatre.
    """
    text = _safe_str(formula)
    if not text:
        return {}

    # Remove charge-ish and whitespace noise.
    text = text.replace(" ", "").replace("_", "")
    text = re.sub(r"[\+\-]+$", "", text)

    tokens = re.findall(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)", text)
    counts: Dict[str, float] = defaultdict(float)
    for el, n in tokens:
        if not el:
            continue
        val = 1.0 if n in ("", None) else float(n)
        counts[_normalise_symbol(el)] += val
    return dict(counts)


def _integer_ratio(counts: Mapping[str, float]) -> Optional[Tuple[int, ...]]:
    vals = [float(v) for v in counts.values() if v is not None and float(v) > 0]
    if not vals:
        return None

    # Most JARVIS reduced formulas are already small integers. We keep this
    # intentionally simple and robust.
    rounded = [int(round(v)) for v in vals]
    if any(abs(v - r) > 1e-6 for v, r in zip(vals, rounded)):
        return None
    g = 0
    for r in rounded:
        g = math.gcd(g, r)
    if g <= 0:
        return None
    return tuple(sorted([int(r // g) for r in rounded]))


def _anonymous_formula_from_counts(counts: Mapping[str, float]) -> Optional[str]:
    ratio = _integer_ratio(counts)
    if not ratio:
        return None
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    parts = []
    for i, n in enumerate(ratio):
        if i >= len(letters):
            break
        parts.append(letters[i] + ("" if n == 1 else str(n)))
    return "".join(parts) if parts else None


def _has_element(counts: Mapping[str, float], element: str) -> bool:
    return _normalise_symbol(element) in counts


def _non_oxygen_elements(counts: Mapping[str, float]) -> Dict[str, float]:
    return {k: v for k, v in counts.items() if k != "O"}


def classify_material_family(material: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Return cheap family/prototype classification fields.

    Inputs may be a material-store row, a query profile flattened row, or any
    mapping with formula/composition/symmetry fields.
    """
    formula = (
        material.get("reduced_formula")
        or material.get("formula")
        or material.get("pretty_formula")
        or material.get("formula_pretty")
    )
    counts = parse_formula_counts(formula)
    elements = sorted(counts.keys()) if counts else list(material.get("elements") or [])
    composition_family = _safe_str(material.get("composition_family"))
    material_family_existing = _safe_str(material.get("material_family"))
    prototype_existing = _safe_str(material.get("prototype"))
    prototype_family_existing = _safe_str(material.get("prototype_family"))
    formula_anonymous_existing = _safe_str(material.get("formula_anonymous"))

    spg = _safe_int(material.get("spacegroup_number"))
    spg_symbol = _safe_str(material.get("spacegroup_symbol"))
    crystal_system_code = _safe_int(material.get("crystal_system_code"))

    evidence = []
    warnings = []

    if counts:
        evidence.append(f"parsed_formula_counts={dict(sorted(counts.items()))}")
    else:
        warnings.append("formula_counts_not_available")

    if composition_family:
        evidence.append(f"composition_family={composition_family}")

    oxygen_count = counts.get("O")
    non_o = _non_oxygen_elements(counts)
    total_distinct = len(counts)

    formula_family = formula_anonymous_existing
    if not formula_family and counts:
        formula_family = _anonymous_formula_from_counts(counts)

    # More semantically useful formula labels.
    if oxygen_count is not None:
        non_o_counts = sorted([int(round(v)) for v in non_o.values() if v is not None])
        o_int = int(round(oxygen_count))
        # ABO3: two non-oxygen elements, each 1, oxygen 3.
        if len(non_o_counts) == 2 and non_o_counts == [1, 1] and o_int == 3:
            formula_family = "ABO3"
            evidence.append("formula matches ABO3 oxide stoichiometry")
        elif len(non_o_counts) == 2 and non_o_counts == [1, 2] and o_int == 4:
            formula_family = "AB2O4"
            evidence.append("formula matches AB2O4 oxide stoichiometry")
        elif len(non_o_counts) == 1 and non_o_counts == [3] and o_int == 4:
            # Mixed-valence/inverse spinels such as Fe3O4 and Co3O4 reduce to
            # A3O4 even though crystallographically they are spinel-family
            # AB2O4 systems with cation valence/order complexity.
            formula_text_for_rule = _safe_str(formula) or ""
            if formula_text_for_rule.replace(" ", "") in {"Fe3O4", "Co3O4"}:
                formula_family = "AB2O4"
                evidence.append("formula matches mixed-valence A3O4 spinel stoichiometry")
        elif len(non_o_counts) == 2 and non_o_counts == [2, 2] and o_int == 7:
            formula_family = "A2B2O7"
            evidence.append("formula matches A2B2O7 oxide stoichiometry")
        elif len(non_o_counts) == 1 and non_o_counts == [1] and o_int == 2:
            formula_family = "AO2"
            evidence.append("formula matches AO2 binary oxide stoichiometry")
        elif len(non_o_counts) >= 1 and o_int > 0 and not formula_family:
            formula_family = "oxide_formula"
            evidence.append("formula contains oxygen")

    prototype_family = prototype_family_existing
    structure_variant = None
    classifier_family = material_family_existing or composition_family or "unknown"
    confidence = 0.35

    # Oxide family rules.
    is_oxide = (
        composition_family == "oxide"
        or _has_element(counts, "O")
        or (material_family_existing == "oxide")
    )

    if is_oxide and formula_family == "ABO3":
        prototype_family = prototype_family or "perovskite_like"
        classifier_family = "perovskite_like"
        confidence = max(confidence, 0.70)
        evidence.append("oxide ABO3 formula supports perovskite-like candidate family")

        if spg == 221 or (spg_symbol or "").upper() == "PM-3M":
            structure_variant = "ideal_cubic_perovskite"
            confidence = max(confidence, 0.82)
            evidence.append("spacegroup Pm-3m/221 supports ideal cubic perovskite variant")
        elif spg in {62, 63, 74} or (spg_symbol or "").lower() in {"pnma", "pbnm", "cmcm", "imma"}:
            structure_variant = "distorted_perovskite"
            confidence = max(confidence, 0.78)
            evidence.append("orthorhombic perovskite-associated spacegroup supports distorted perovskite variant")
        elif spg in {99, 107, 123, 127, 139, 140, 160, 161}:
            structure_variant = "polar_or_tetragonal_perovskite_candidate"
            confidence = max(confidence, 0.72)
            evidence.append("spacegroup is compatible with common distorted/polar perovskite variants")
        else:
            structure_variant = "perovskite_like_unknown_variant"
            warnings.append("ABO3 oxide detected but spacegroup does not identify a simple perovskite variant")

    elif is_oxide and formula_family == "AB2O4":
        # Spinel-derived oxides. AB2O4 stoichiometry alone is useful but not
        # sufficient for a strong structural claim; symmetry and known spinel
        # chemistries provide the extra context. This deliberately remains
        # rule-based and conservative rather than pretending to solve cation
        # ordering from formula alone, because that would be tiny crystallographic
        # fraud wearing a lab coat.
        prototype_family = prototype_family or "spinel_like"
        classifier_family = "spinel_like"
        confidence = max(confidence, 0.70)
        evidence.append("oxide AB2O4 formula supports spinel-like candidate family")

        symbol_norm = (spg_symbol or "").replace(" ", "").lower()
        non_o_elements = set(non_o.keys())

        canonical_spinel_formulas = {
            "MgAl2O4", "ZnAl2O4", "Co3O4", "Fe3O4", "LiMn2O4"
        }
        inverse_or_mixed_valence_spinel_formulas = {"Fe3O4", "Co3O4"}
        battery_spinel_formulas = {"LiMn2O4"}

        formula_text = _safe_str(formula) or ""
        compact_formula = formula_text.replace(" ", "")

        if compact_formula in canonical_spinel_formulas:
            confidence = max(confidence, 0.74)
            evidence.append("formula is a known reference spinel validation chemistry")

        if spg == 227 or symbol_norm == "fd-3m":
            structure_variant = "cubic_spinel"
            confidence = max(confidence, 0.86)
            evidence.append("spacegroup Fd-3m/227 supports canonical cubic spinel variant")
            if compact_formula in inverse_or_mixed_valence_spinel_formulas:
                structure_variant = "cubic_mixed_valence_or_inverse_spinel"
                confidence = max(confidence, 0.84)
                evidence.append("formula is commonly associated with mixed-valence/inverse spinel behaviour")
            elif compact_formula in battery_spinel_formulas:
                structure_variant = "cubic_battery_spinel"
                confidence = max(confidence, 0.84)
                evidence.append("LiMn2O4 chemistry supports battery-spinel context")
        elif spg in {10, 38, 51, 62, 63, 74, 160, 186} or symbol_norm in {
            "p2/m", "amm2", "pmma", "pnma", "cmcm", "imma", "r3m", "p63mc", "p6_3mc"
        }:
            structure_variant = "distorted_spinel_derivative"
            confidence = max(confidence, 0.80)
            evidence.append("lower-symmetry AB2O4 oxide supports distorted spinel-derivative variant")
            if compact_formula in battery_spinel_formulas:
                structure_variant = "distorted_battery_spinel_derivative"
                confidence = max(confidence, 0.82)
                evidence.append("LiMn2O4 lower-symmetry polymorph supports distorted battery-spinel context")
        else:
            structure_variant = "spinel_like_unknown_variant"
            warnings.append("AB2O4 oxide detected but spacegroup does not identify a simple spinel variant")

        if len(non_o_elements) != 2:
            warnings.append("AB2O4 spinel-like assignment made from reduced formula; cation ordering not resolved")

    elif is_oxide and formula_family == "A2B2O7":
        # Pyrochlore-derived oxides. A2B2O7 stoichiometry is a strong cheap
        # clue, but the role signal depends heavily on whether the material is
        # in the canonical cubic Fd-3m pyrochlore setting or a lower-symmetry
        # derivative / distorted variant. We keep this rule deliberately
        # evidence-based rather than pretending every A2B2O7 is a perfect
        # pyrochlore. Humanity may enjoy tidy labels; crystals have declined.
        prototype_family = prototype_family or "pyrochlore_like"
        classifier_family = "pyrochlore_like"
        confidence = max(confidence, 0.72)
        evidence.append("oxide A2B2O7 formula supports pyrochlore-like candidate family")

        symbol_norm = (spg_symbol or "").replace(" ", "").lower()
        compact_formula = (_safe_str(formula) or "").replace(" ", "")

        canonical_pyrochlore_formulas = {
            "Y2Ti2O7", "Gd2Ti2O7", "La2Zr2O7", "Nd2Zr2O7", "Sm2Zr2O7"
        }
        titanate_pyrochlore_formulas = {"Y2Ti2O7", "Gd2Ti2O7"}
        zirconate_pyrochlore_formulas = {"La2Zr2O7", "Nd2Zr2O7", "Sm2Zr2O7"}

        if compact_formula in canonical_pyrochlore_formulas:
            confidence = max(confidence, 0.76)
            evidence.append("formula is a known reference pyrochlore validation chemistry")
        if compact_formula in titanate_pyrochlore_formulas:
            evidence.append("rare-earth titanate chemistry supports canonical pyrochlore context")
        if compact_formula in zirconate_pyrochlore_formulas:
            evidence.append("rare-earth zirconate chemistry supports pyrochlore/defect-fluorite context")

        if spg == 227 or symbol_norm == "fd-3m":
            structure_variant = "cubic_pyrochlore"
            confidence = max(confidence, 0.86)
            evidence.append("spacegroup Fd-3m/227 supports canonical cubic pyrochlore variant")
        elif spg in {51, 62, 63, 74} or symbol_norm in {"pmma", "pnma", "pbnm", "cmcm", "imma"}:
            structure_variant = "distorted_pyrochlore_derivative"
            confidence = max(confidence, 0.80)
            evidence.append("lower-symmetry A2B2O7 oxide supports distorted pyrochlore-derivative variant")
        elif spg in {225, 216} or symbol_norm in {"fm-3m", "f-43m", "f4-3m"}:
            structure_variant = "defect_fluorite_or_disordered_pyrochlore_candidate"
            confidence = max(confidence, 0.76)
            evidence.append("fluorite-like high-symmetry A2B2O7 setting supports defect-fluorite/disordered-pyrochlore context")
        elif spg in {14, 137, 141, 160, 161}:
            structure_variant = "low_symmetry_pyrochlore_related_candidate"
            confidence = max(confidence, 0.72)
            evidence.append("A2B2O7 oxide has symmetry compatible with pyrochlore-related distortion")
        else:
            structure_variant = "pyrochlore_like_unknown_variant"
            warnings.append("A2B2O7 oxide detected but spacegroup does not identify a simple pyrochlore variant")

    elif is_oxide and formula_family in {"AO2", "AB2"}:
        # Fluorite-derived binary oxides. This rule is deliberately conservative:
        # it gives strong context only for known fluorite-related cations or common
        # fluorite/polymorph space groups. It does not claim all AO2 oxides are
        # fluorite-derived, because that would be taxonomy vandalism.
        fluorite_cations = {"Zr", "Hf", "Ce", "Th", "U", "Pu"}
        non_o_elements = set(non_o.keys())
        known_fluorite_cation = bool(non_o_elements & fluorite_cations)
        fluorite_spg = spg in {14, 137, 141, 225, 227}
        fluorite_symbol = (spg_symbol or "").replace(" ", "").lower() in {
            "p21/c", "p2_1/c", "p42/nmc", "p4_2/nmc", "i41/amd", "i4_1/amd", "fm-3m", "fd-3m"
        }
        if known_fluorite_cation or fluorite_spg or fluorite_symbol:
            prototype_family = prototype_family or "fluorite_related"
            classifier_family = "fluorite_related"
            confidence = max(confidence, 0.70 if known_fluorite_cation else 0.62)
            evidence.append("AO2 oxide chemistry supports possible fluorite-related family")
            if known_fluorite_cation:
                evidence.append("cation is commonly associated with fluorite-derived oxide polymorphs")

            symbol_norm = (spg_symbol or "").replace(" ", "").lower()
            if spg == 225 or symbol_norm == "fm-3m":
                structure_variant = "cubic_fluorite"
                confidence = max(confidence, 0.84)
                evidence.append("spacegroup Fm-3m/225 supports cubic fluorite variant")
            elif spg in {137, 141} or symbol_norm in {"p42/nmc", "p4_2/nmc", "i41/amd", "i4_1/amd"}:
                structure_variant = "tetragonal_fluorite_derivative"
                confidence = max(confidence, 0.78)
                evidence.append("tetragonal fluorite-derivative spacegroup detected")
            elif spg == 14 or symbol_norm in {"p21/c", "p2_1/c"}:
                structure_variant = "monoclinic_fluorite_derivative"
                confidence = max(confidence, 0.80)
                evidence.append("monoclinic fluorite-derivative spacegroup detected")
            elif spg == 227 or symbol_norm == "fd-3m":
                structure_variant = "defect_or_ordered_fluorite_related"
                confidence = max(confidence, 0.74)
                evidence.append("Fd-3m-like fluorite-related symmetry detected")
            else:
                structure_variant = "fluorite_related_unknown_variant"
                warnings.append("AO2 fluorite-related chemistry detected but variant is not identified from spacegroup")

    # Dichalcogenide-ish: AB2, one metal-like and chalcogen not O.
    chalcogens = {"S", "Se", "Te"}
    if not is_oxide and counts and any(el in counts for el in chalcogens):
        vals = sorted([int(round(v)) for v in counts.values()])
        if len(vals) == 2 and vals == [1, 2]:
            formula_family = formula_family or "AB2"
            prototype_family = prototype_family or "dichalcogenide_like"
            classifier_family = "dichalcogenide_like"
            structure_variant = structure_variant or "layered_chalcogenide_candidate"
            confidence = max(confidence, 0.62)
            evidence.append("AB2 chalcogenide formula supports dichalcogenide-like candidate family")

    # MAX phase rough rule: Mn+1AXn, often Ti3SiC2 etc.
    if counts and any(el in counts for el in {"C", "N"}) and total_distinct == 3:
        sorted_counts = sorted(int(round(v)) for v in counts.values())
        if sorted_counts in ([1, 2, 3], [1, 1, 2], [1, 3, 4]):
            prototype_family = prototype_family or "max_phase_like"
            classifier_family = "max_phase_like"
            structure_variant = structure_variant or "layered_carbide_nitride_candidate"
            confidence = max(confidence, 0.58)
            evidence.append("ternary carbide/nitride count pattern supports possible MAX-phase-like family")

    if not prototype_family:
        prototype_family = "unknown"
        warnings.append("prototype_family_not_available")

    if not formula_family:
        formula_family = "unknown"
        warnings.append("formula_family_not_available")

    if not structure_variant:
        structure_variant = "unknown"

    # If prototype was explicitly available, trust slightly more.
    if prototype_existing or prototype_family_existing:
        confidence = min(0.95, confidence + 0.08)
        evidence.append("existing prototype/prototype_family metadata available")

    result = {
        "schema_version": CLASSIFIER_SCHEMA_VERSION,
        "material_family": classifier_family,
        "composition_family": composition_family,
        "formula_family": formula_family,
        "prototype": prototype_existing,
        "prototype_family": prototype_family,
        "structure_variant": structure_variant,
        "confidence": round(float(max(0.0, min(1.0, confidence))), 4),
        "evidence": evidence,
        "warnings": warnings,
        "source_fields": {
            "formula": formula,
            "spacegroup_number": spg,
            "spacegroup_symbol": spg_symbol,
            "crystal_system_code": crystal_system_code,
            "existing_material_family": material_family_existing,
            "existing_prototype_family": prototype_family_existing,
            "existing_formula_anonymous": formula_anonymous_existing,
        },
    }
    return result


def flatten_family_classification(classification: Mapping[str, Any]) -> Dict[str, Any]:
    """Fields intended for insertion into flat material/profile rows."""
    return {
        "material_family": classification.get("material_family"),
        "formula_family": classification.get("formula_family"),
        "prototype": classification.get("prototype"),
        "prototype_family": classification.get("prototype_family"),
        "structure_variant": classification.get("structure_variant"),
        "family_classification_confidence": classification.get("confidence"),
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    payload = {"formula": sys.argv[1] if len(sys.argv) > 1 else "CaTiO3"}
    if len(sys.argv) > 2:
        payload["spacegroup_number"] = sys.argv[2]
    if len(sys.argv) > 3:
        payload["spacegroup_symbol"] = sys.argv[3]
    print(json.dumps(classify_material_family(payload), indent=2, sort_keys=True))