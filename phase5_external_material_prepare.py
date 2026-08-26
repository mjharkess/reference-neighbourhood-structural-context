from __future__ import annotations

"""
phase5_external_material_prepare.py

Small CLI for Phase 5 Steps 1-4. It ingests one external CIF/POSCAR/CONTCAR,
builds available LRT-compatible descriptors, validates descriptor coverage, and
writes the pre-retrieval external material package.
"""

import argparse
import json
from pathlib import Path

from external_descriptor_builder import build_external_descriptors
from external_material_ingestion import ingest_external_material
from external_material_schema import write_json
from external_material_validator import validate_external_material


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare an external material for LRT Phase 5 retrieval.")
    parser.add_argument("--external_structure", required=True, help="Path to CIF, POSCAR, or CONTCAR file.")
    parser.add_argument("--external_format", default=None, help="Optional explicit format: cif, poscar, contcar.")
    parser.add_argument("--external_id", default=None, help="Optional stable external material ID.")
    parser.add_argument("--external_label", default=None, help="Optional human-facing label.")
    parser.add_argument("--output_dir", default="phase5_external_material_run")
    parser.add_argument("--coordination_cutoff", type=float, default=3.0)
    parser.add_argument("--min_required_completeness", type=float, default=0.75)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    material = ingest_external_material(
        args.external_structure,
        external_format=args.external_format,
        external_id=args.external_id,
        external_label=args.external_label,
        output_dir=output_dir,
    )
    descriptors = build_external_descriptors(
        material,
        coordination_cutoff=args.coordination_cutoff,
        output_dir=output_dir,
    )
    validation = validate_external_material(
        material,
        descriptors,
        min_required_completeness=args.min_required_completeness,
        output_dir=output_dir,
    )

    status = {
        "external_id": material.external_id,
        "parse_status": material.parse_status,
        "validation_status": validation.validation_status,
        "can_run_retrieval": validation.can_run_retrieval,
        "outputs": {
            "external_material_profile": str(output_dir / "external_material_profile.json"),
            "external_descriptor_report": str(output_dir / "external_descriptor_report.json"),
            "external_descriptor_record": str(output_dir / "external_descriptor_record.json"),
            "external_validation_report": str(output_dir / "external_validation_report.json"),
        },
    }
    write_json(status, output_dir / "phase5_prepare_status.json")
    print(json.dumps(status, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
