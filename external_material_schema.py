from __future__ import annotations

"""
external_material_schema.py

Phase 5 external-material schema objects for the Local Relational Topology
retrieval framework.

These classes define the hand-off contract for Steps 1-4 of the Phase 5 MVP:
external structure ingestion, descriptor construction, and validation before any
retrieval against the JARVIS anchor universe is attempted.
"""

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

PHASE5_EXTERNAL_SCHEMA_VERSION = "phase5.external_material.v1"
PHASE5_DESCRIPTOR_SCHEMA_VERSION = "phase5.external_descriptor.v1"
PHASE5_VALIDATION_SCHEMA_VERSION = "phase5.external_validation.v1"


# These are intentionally copied from the current material_store contract so the
# Phase 5 modules can be imported even in environments where jarvis-tools is not
# installed yet. The full runtime should still compare these fields against the
# live material_store.py constants during integration testing.
LRT_REQUIRED_DESCRIPTOR_FIELDS: List[str] = [
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
    "composition_family",
]

LRT_NUMERIC_DESCRIPTOR_FIELDS: List[str] = sorted(
    f for f in LRT_REQUIRED_DESCRIPTOR_FIELDS
    if f not in {"jid", "formula", "reduced_formula", "chemical_system", "composition_family"}
)

LRT_OPTIONAL_PHYSICAL_FIELDS: List[str] = [
    "formation_energy",
    "formation_energy_peratom",
    "energy_above_hull",
    "known_synthesized",
]

VALIDATION_ACCEPTED = "accepted"
VALIDATION_ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
VALIDATION_REJECTED_PARSE_FAILURE = "rejected_parse_failure"
VALIDATION_REJECTED_MISSING_REQUIRED_DESCRIPTORS = "rejected_missing_required_descriptors"
VALIDATION_REJECTED_INVALID_GEOMETRY = "rejected_invalid_geometry"
VALIDATION_REJECTED_UNSUPPORTED_SPECIES = "rejected_unsupported_species"


@dataclass
class ExternalMaterialRecord:
    external_id: str
    source_file: str
    source_format: str
    formula: Optional[str] = None
    reduced_formula: Optional[str] = None
    elements: List[str] = field(default_factory=list)
    atom_count: Optional[int] = None
    species_count: Optional[int] = None
    lattice: Dict[str, Optional[float]] = field(default_factory=dict)
    structure_summary: Dict[str, Any] = field(default_factory=dict)
    parser: Optional[str] = None
    parse_status: str = "pending"
    descriptor_status: str = "pending"
    validation_status: str = "pending"
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    raw_structure: Optional[Dict[str, Any]] = None
    schema_version: str = PHASE5_EXTERNAL_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ExternalMaterialRecord":
        data = dict(payload or {})
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ExternalDescriptorReport:
    external_id: str
    descriptors: Dict[str, Any]
    generated_fields: List[str]
    missing_fields: List[str]
    required_fields_missing: List[str]
    optional_fields_missing: List[str]
    descriptor_completeness: float
    required_descriptor_completeness: float
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    schema_version: str = PHASE5_DESCRIPTOR_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExternalValidationReport:
    external_id: str
    validation_status: str
    can_run_retrieval: bool
    parse_status: str
    descriptor_status: str
    descriptor_completeness: float
    required_descriptor_completeness: float
    required_fields_missing: List[str]
    optional_fields_missing: List[str]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    schema_version: str = PHASE5_VALIDATION_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def json_default(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "item"):
        return obj.item()
    return str(obj)


def write_json(payload: Any, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=json_default)
        f.write("\n")
