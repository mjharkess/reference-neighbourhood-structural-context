from __future__ import annotations

"""
external_descriptor_builder.py

Phase 5 Step 3: build LRT-compatible descriptors for an externally ingested
material. The builder is dependency-tolerant and produces explicit missing-field
reports rather than pretending every JARVIS descriptor can be reconstructed from
a CIF/POSCAR with divine certainty.
"""

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from external_material_schema import (
    ExternalDescriptorReport,
    ExternalMaterialRecord,
    LRT_OPTIONAL_PHYSICAL_FIELDS,
    LRT_REQUIRED_DESCRIPTOR_FIELDS,
    write_json,
)

CRYSTAL_SYSTEM_MAP: Dict[str, int] = {
    "triclinic": 1,
    "monoclinic": 2,
    "orthorhombic": 3,
    "tetragonal": 4,
    "trigonal": 5,
    "hexagonal": 6,
    "cubic": 7,
}

NONMETALS = {"H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Se", "Br", "I", "Te", "As", "Sb", "Bi"}


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


def classify_composition_family(elements: Sequence[str]) -> str:
    elems = list(elements or [])
    if not elems:
        return "unknown_composition"
    metal_count = sum(1 for e in elems if e not in NONMETALS)
    nonmetal_count = sum(1 for e in elems if e in NONMETALS)
    if metal_count and nonmetal_count:
        return "mixed_metal_nonmetal"
    if metal_count and not nonmetal_count:
        return "metallic_or_intermetallic"
    if nonmetal_count and not metal_count:
        return "nonmetallic"
    return "unknown_composition"


def _load_structure(record: ExternalMaterialRecord):
    try:
        from pymatgen.core import Structure  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError("pymatgen is required to build external descriptors") from exc
    if not record.raw_structure:
        raise ValueError("ExternalMaterialRecord.raw_structure is empty; run ingestion first")
    return Structure.from_dict(record.raw_structure)


def composition_reachability_features(formula: str) -> Dict[str, Any]:
    try:
        from pymatgen.core import Composition, Element  # type: ignore
        comp = Composition(formula).reduced_composition
        elements = sorted(str(el.symbol) for el in comp.elements)
        return {
            "reduced_formula": comp.reduced_formula,
            "chemical_system": "-".join(elements),
            "n_elements": int(len(elements)),
            "composition_family": classify_composition_family(elements),
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


def composition_property_features(formula: str) -> Dict[str, Optional[float]]:
    try:
        from pymatgen.core import Composition, Element  # type: ignore
        comp = Composition(formula)
        en_vals: List[float] = []
        radius_vals: List[float] = []
        valence_vals: List[float] = []
        for el in comp.elements:
            e = Element(el.symbol)
            if e.X is not None:
                en_vals.append(float(e.X))
            if getattr(e, "atomic_radius", None) is not None:
                radius_vals.append(float(e.atomic_radius))
            try:
                valence_vals.append(float(e.group))
            except Exception:
                pass
        return {
            "mean_electronegativity": float(np.mean(en_vals)) if en_vals else None,
            "electronegativity_range": float(max(en_vals) - min(en_vals)) if len(en_vals) >= 2 else None,
            "atomic_radius_mean": float(np.mean(radius_vals)) if radius_vals else None,
            "valence_electrons_mean": float(np.mean(valence_vals)) if valence_vals else None,
        }
    except Exception:
        return {
            "mean_electronegativity": None,
            "electronegativity_range": None,
            "atomic_radius_mean": None,
            "valence_electrons_mean": None,
        }


def coordination_stats(structure: Any, cutoff: float = 3.0) -> Dict[str, Optional[float]]:
    try:
        coords: List[int] = []
        for i, site in enumerate(structure):
            neighbours = structure.get_neighbors(site, cutoff)
            coords.append(int(len(neighbours)))
        arr = np.array(coords, dtype=float)
        if arr.size == 0:
            raise ValueError("empty coordination array")
        return {
            "coord_mean": float(arr.mean()),
            "coord_std": float(arr.std()),
            "coord_min": float(arr.min()),
            "coord_max": float(arr.max()),
            "frac_low_coord_sites": float(np.mean(arr <= 2)),
            "frac_high_coord_sites": float(np.mean(arr >= 8)),
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


def bonding_proxies(structure: Any, cutoff: float = 3.0) -> Dict[str, Optional[float]]:
    try:
        from pymatgen.core import Element  # type: ignore
        distances: List[float] = []
        en_diffs: List[float] = []
        for i, site in enumerate(structure):
            for neigh in structure.get_neighbors(site, cutoff):
                j = getattr(neigh, "index", None)
                if j is not None and j <= i:
                    continue
                d = safe_float(getattr(neigh, "nn_distance", None))
                if d is not None and d > 1e-8:
                    distances.append(d)
                    try:
                        en1 = Element(str(site.specie.symbol)).X
                        en2 = Element(str(neigh.specie.symbol)).X
                        if en1 is not None and en2 is not None:
                            en_diffs.append(abs(float(en1) - float(en2)))
                    except Exception:
                        pass
        d_arr = np.array(distances, dtype=float) if distances else np.array([], dtype=float)
        en_arr = np.array(en_diffs, dtype=float) if en_diffs else np.array([], dtype=float)
        if not d_arr.size:
            raise ValueError("no neighbour distances found")
        try:
            unique_elements = sorted({str(site.specie.symbol) for site in structure})
            ens = [float(Element(e).X) for e in unique_elements if Element(e).X is not None]
            ionicity = float(max(ens) - min(ens)) if ens else None
        except Exception:
            ionicity = None
        return {
            "bond_mean_en_diff": float(en_arr.mean()) if en_arr.size else None,
            "bond_std_en_diff": float(en_arr.std()) if en_arr.size else None,
            "bond_max_en_diff": float(en_arr.max()) if en_arr.size else None,
            "bond_length_mean": float(d_arr.mean()),
            "bond_length_std": float(d_arr.std()),
            "bond_length_range": float(d_arr.max() - d_arr.min()),
            "frac_short_bonds": float(np.mean(d_arr < 2.2)),
            "ionicity_proxy_comp": ionicity,
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


def build_external_descriptors(
    record: ExternalMaterialRecord,
    *,
    coordination_cutoff: float = 3.0,
    output_dir: Optional[str | Path] = None,
) -> ExternalDescriptorReport:
    warnings: List[str] = []
    errors: List[str] = []
    descriptors: Dict[str, Any] = {
        "jid": record.external_id,
        "external_id": record.external_id,
        "formula": record.formula,
        "material_type": "external",
        "dataset_kind": "external_structure",
        "external_source_file": record.source_file,
        "external_source_format": record.source_format,
    }

    if record.parse_status != "success":
        errors.append("Cannot build descriptors because external parse_status is not success")
    else:
        try:
            structure = _load_structure(record)
            formula = record.formula or str(structure.composition.reduced_formula)
            descriptors["formula"] = formula
            descriptors.update(composition_reachability_features(formula))
            descriptors.update(composition_property_features(formula))

            lattice = structure.lattice
            a, b, c = float(lattice.a), float(lattice.b), float(lattice.c)
            descriptors.update({
                "a_axis": a,
                "b_axis": b,
                "c_axis_cached": c,
                "c_over_a": float(c / a) if a else None,
                "c_over_b": float(c / b) if b else None,
                "max_axis_over_min_axis": float(max(a, b, c) / min(a, b, c)) if min(a, b, c) > 0 else None,
                "volume_per_atom": float(lattice.volume / len(structure)) if len(structure) else None,
            })

            frac = np.array([site.frac_coords for site in structure], dtype=float)
            cart = np.array([site.coords for site in structure], dtype=float)
            descriptors["frac_z_span"] = float(np.max(frac[:, 2]) - np.min(frac[:, 2])) if frac.size else None
            descriptors["cart_z_span_over_c"] = float((np.max(cart[:, 2]) - np.min(cart[:, 2])) / c) if cart.size and c > 1e-8 else None

            try:
                from pymatgen.symmetry.analyzer import SpacegroupAnalyzer  # type: ignore
                sga = SpacegroupAnalyzer(structure)
                descriptors["spacegroup_number"] = int(sga.get_space_group_number())
                descriptors["crystal_system_code"] = CRYSTAL_SYSTEM_MAP.get(str(sga.get_crystal_system()).lower())
                descriptors["n_symmetry_ops"] = int(len(sga.get_symmetry_operations()))
                try:
                    descriptors["is_centrosymmetric"] = int(bool(sga.is_laue()))
                except Exception:
                    descriptors["is_centrosymmetric"] = None
            except Exception as exc:
                warnings.append(f"Symmetry descriptors unavailable: {exc}")
                descriptors.update({
                    "spacegroup_number": None,
                    "crystal_system_code": None,
                    "n_symmetry_ops": None,
                    "is_centrosymmetric": None,
                })

            descriptors.update(coordination_stats(structure, cutoff=coordination_cutoff))
            descriptors.update(bonding_proxies(structure, cutoff=coordination_cutoff))
        except Exception as exc:
            errors.append(f"Descriptor construction failed: {exc}")

    # Explicit physical placeholders. The external material is structurally
    # comparable but not automatically physically validated.
    descriptors.setdefault("formation_energy", None)
    descriptors.setdefault("formation_energy_peratom", None)
    descriptors.setdefault("energy_above_hull", None)
    descriptors.setdefault("known_synthesized", None)

    for field in LRT_REQUIRED_DESCRIPTOR_FIELDS + LRT_OPTIONAL_PHYSICAL_FIELDS:
        descriptors.setdefault(field, None)

    missing_required = [f for f in LRT_REQUIRED_DESCRIPTOR_FIELDS if descriptors.get(f) is None]
    optional_missing = [f for f in LRT_OPTIONAL_PHYSICAL_FIELDS if descriptors.get(f) is None]
    generated = [f for f in LRT_REQUIRED_DESCRIPTOR_FIELDS if descriptors.get(f) is not None]
    completeness = len(generated) / max(1, len(LRT_REQUIRED_DESCRIPTOR_FIELDS))

    if optional_missing:
        warnings.append("External physical plausibility fields are unavailable unless supplied separately")

    report = ExternalDescriptorReport(
        external_id=record.external_id,
        descriptors=descriptors,
        generated_fields=generated,
        missing_fields=missing_required + optional_missing,
        required_fields_missing=missing_required,
        optional_fields_missing=optional_missing,
        descriptor_completeness=float(completeness),
        required_descriptor_completeness=float(completeness),
        warnings=warnings,
        errors=errors,
    )

    if output_dir:
        write_json(report.to_dict(), Path(output_dir) / "external_descriptor_report.json")
        write_json(descriptors, Path(output_dir) / "external_descriptor_record.json")
    return report
