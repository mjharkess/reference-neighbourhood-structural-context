from __future__ import annotations

"""
external_material_validator.py

Phase 5 Step 4: validate whether an ingested external material has enough clean
structure and descriptor coverage to be admitted into LRT retrieval.
"""

from pathlib import Path
from typing import List, Optional

from external_material_schema import (
    ExternalDescriptorReport,
    ExternalMaterialRecord,
    ExternalValidationReport,
    VALIDATION_ACCEPTED,
    VALIDATION_ACCEPTED_WITH_WARNINGS,
    VALIDATION_REJECTED_INVALID_GEOMETRY,
    VALIDATION_REJECTED_MISSING_REQUIRED_DESCRIPTORS,
    VALIDATION_REJECTED_PARSE_FAILURE,
    VALIDATION_REJECTED_UNSUPPORTED_SPECIES,
    write_json,
)

CRITICAL_RETRIEVAL_FIELDS = [
    "jid",
    "formula",
    "reduced_formula",
    "chemical_system",
    "composition_family",
    "n_elements",
    "element_set",
    "a_axis",
    "b_axis",
    "c_axis_cached",
    "c_over_a",
    "c_over_b",
    "max_axis_over_min_axis",
    "volume_per_atom",
    "frac_z_span",
    "cart_z_span_over_c",
    "coord_mean",
    "coord_std",
    "bond_length_mean",
    "ionicity_proxy_comp",
    "mean_electronegativity",
    "electronegativity_range",
]

GEOMETRY_FIELDS = ["a_axis", "b_axis", "c_axis_cached", "volume_per_atom"]


def validate_external_material(
    record: ExternalMaterialRecord,
    descriptor_report: ExternalDescriptorReport,
    *,
    min_required_completeness: float = 0.75,
    output_dir: Optional[str | Path] = None,
) -> ExternalValidationReport:
    warnings: List[str] = []
    errors: List[str] = []

    warnings.extend(record.warnings or [])
    warnings.extend(descriptor_report.warnings or [])
    errors.extend(record.errors or [])
    errors.extend(descriptor_report.errors or [])

    descriptors = descriptor_report.descriptors or {}

    if record.parse_status != "success":
        status = VALIDATION_REJECTED_PARSE_FAILURE
        can_run = False
        recommended_action = "Fix the source structure file or provide a supported CIF/POSCAR/CONTCAR."
    elif not record.elements:
        status = VALIDATION_REJECTED_UNSUPPORTED_SPECIES
        can_run = False
        errors.append("No supported species/elements were extracted from the structure.")
        recommended_action = "Check element labels, occupancies, and parser support."
    elif any(descriptors.get(f) is None for f in GEOMETRY_FIELDS):
        status = VALIDATION_REJECTED_INVALID_GEOMETRY
        can_run = False
        errors.append("Required lattice/geometry descriptors are missing.")
        recommended_action = "Check lattice vectors, periodic structure validity, and atom coordinates."
    else:
        missing_critical = [f for f in CRITICAL_RETRIEVAL_FIELDS if descriptors.get(f) is None]
        if missing_critical:
            errors.append(f"Missing critical retrieval descriptors: {missing_critical}")
        if descriptor_report.required_descriptor_completeness < min_required_completeness or missing_critical:
            status = VALIDATION_REJECTED_MISSING_REQUIRED_DESCRIPTORS
            can_run = False
            recommended_action = "Add descriptor support or relax validator thresholds only for diagnostic runs."
        elif descriptor_report.optional_fields_missing or descriptor_report.warnings:
            status = VALIDATION_ACCEPTED_WITH_WARNINGS
            can_run = True
            recommended_action = "Retrieval may proceed, but physical plausibility should be treated as incomplete."
        else:
            status = VALIDATION_ACCEPTED
            can_run = True
            recommended_action = "Retrieval may proceed."

    report = ExternalValidationReport(
        external_id=record.external_id,
        validation_status=status,
        can_run_retrieval=can_run,
        parse_status=record.parse_status,
        descriptor_status="complete" if not descriptor_report.required_fields_missing else "incomplete",
        descriptor_completeness=descriptor_report.descriptor_completeness,
        required_descriptor_completeness=descriptor_report.required_descriptor_completeness,
        required_fields_missing=list(descriptor_report.required_fields_missing),
        optional_fields_missing=list(descriptor_report.optional_fields_missing),
        warnings=warnings,
        errors=errors,
        recommended_action=recommended_action,
    )

    if output_dir:
        write_json(report.to_dict(), Path(output_dir) / "external_validation_report.json")
    return report
