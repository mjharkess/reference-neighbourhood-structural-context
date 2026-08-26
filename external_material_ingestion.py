from __future__ import annotations

"""
external_material_ingestion.py

Phase 5 Step 2: ingest CIF/POSCAR/CONTCAR structures into the external material
schema without registering them in the JARVIS-backed material store yet.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from external_material_schema import ExternalMaterialRecord, write_json

SUPPORTED_EXTERNAL_FORMATS = {"cif", "poscar", "contcar"}


def infer_structure_format(path: str | Path, explicit_format: Optional[str] = None) -> str:
    if explicit_format:
        fmt = explicit_format.lower().strip().lstrip(".")
    else:
        name = Path(path).name.lower()
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix == "cif":
            fmt = "cif"
        elif name in {"poscar", "contcar"} or suffix in {"poscar", "contcar", "vasp"}:
            fmt = "poscar" if name != "contcar" else "contcar"
        else:
            fmt = suffix or "unknown"
    if fmt == "vasp":
        fmt = "poscar"
    return fmt


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_external_id(path: str | Path, prefix: str = "EXT") -> str:
    digest = file_sha256(path)[:10].upper()
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{date}-{digest}"


def _load_with_pymatgen(path: Path):
    try:
        from pymatgen.core import Structure  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency controlled by user env
        raise ImportError("pymatgen is required to parse external CIF/POSCAR files") from exc
    return Structure.from_file(str(path))


def _structure_to_summary(structure: Any) -> Dict[str, Any]:
    lattice = structure.lattice
    formula = getattr(structure.composition, "reduced_formula", None) or str(structure.composition)
    elements = sorted(str(el.symbol) for el in structure.composition.elements)
    return {
        "formula": str(formula),
        "reduced_formula": str(structure.composition.reduced_formula),
        "elements": elements,
        "atom_count": int(len(structure)),
        "species_count": int(len(elements)),
        "lattice": {
            "a": float(lattice.a),
            "b": float(lattice.b),
            "c": float(lattice.c),
            "alpha": float(lattice.alpha),
            "beta": float(lattice.beta),
            "gamma": float(lattice.gamma),
            "volume": float(lattice.volume),
        },
    }


def _structure_to_raw_payload(structure: Any) -> Dict[str, Any]:
    """Return a JSON-safe structure payload for later descriptor construction."""
    return structure.as_dict()


def ingest_external_material(
    structure_path: str | Path,
    *,
    external_format: Optional[str] = None,
    external_id: Optional[str] = None,
    external_label: Optional[str] = None,
    output_dir: Optional[str | Path] = None,
) -> ExternalMaterialRecord:
    path = Path(structure_path)
    fmt = infer_structure_format(path, external_format)
    ext_id = external_id or build_external_id(path)

    record = ExternalMaterialRecord(
        external_id=ext_id,
        source_file=str(path),
        source_format=fmt,
        provenance={
            "source_filename": path.name,
            "source_path": str(path),
            "source_sha256": file_sha256(path) if path.exists() else None,
            "external_label": external_label,
        },
    )

    if not path.exists():
        record.parse_status = "failed"
        record.errors.append(f"Source file does not exist: {path}")
        if output_dir:
            write_json(record.to_dict(), Path(output_dir) / "external_material_profile.json")
        return record

    if fmt not in SUPPORTED_EXTERNAL_FORMATS:
        record.parse_status = "failed"
        record.errors.append(f"Unsupported external structure format: {fmt}")
        if output_dir:
            write_json(record.to_dict(), Path(output_dir) / "external_material_profile.json")
        return record

    try:
        structure = _load_with_pymatgen(path)
        summary = _structure_to_summary(structure)
        record.formula = summary["formula"]
        record.reduced_formula = summary["reduced_formula"]
        record.elements = summary["elements"]
        record.atom_count = summary["atom_count"]
        record.species_count = summary["species_count"]
        record.lattice = summary["lattice"]
        record.structure_summary = summary
        record.raw_structure = _structure_to_raw_payload(structure)
        record.parser = "pymatgen.Structure.from_file"
        record.parse_status = "success"
        record.provenance["parsed_at_utc"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        record.parse_status = "failed"
        record.errors.append(f"Failed to parse structure with pymatgen: {exc}")

    if output_dir:
        write_json(record.to_dict(), Path(output_dir) / "external_material_profile.json")
    return record


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest an external CIF/POSCAR into the LRT Phase 5 schema.")
    parser.add_argument("structure_path")
    parser.add_argument("--external_format", default=None)
    parser.add_argument("--external_id", default=None)
    parser.add_argument("--external_label", default=None)
    parser.add_argument("--output_dir", default="phase5_external_material_run")
    args = parser.parse_args()

    result = ingest_external_material(
        args.structure_path,
        external_format=args.external_format,
        external_id=args.external_id,
        external_label=args.external_label,
        output_dir=args.output_dir,
    )
    print(result.to_dict())
