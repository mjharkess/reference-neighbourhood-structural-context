from __future__ import annotations
"""
Shared utilities for Phase 3 LRT analysis.

Overview
--------
This module contains small, reusable infrastructure helpers used by the Phase 3
LRT workflow. The utilities cover logging, JSON artefact persistence, file
hashing, dataframe schema checks, deterministic ordering, and run metadata.

Design principles
-----------------
* Keep utility behaviour deterministic and side-effect-light.
* Centralise common persistence and validation behaviour.
* Fail clearly when required input schema is incomplete.
* Preserve reproducibility through stable sorting, hashing and run metadata.
* Avoid embedding domain-specific scientific or scoring logic in this module.

Architectural role
------------------
``lrt_phase3_utils.py`` is a supporting utility module rather than an analysis
stage. Phase 3 scripts may depend on these helpers for consistent operational
behaviour, but scientific interpretation should remain in the specialist
analysis modules.

Maintenance guidance
--------------------
Utilities added here should be broadly reusable within the Phase 3 workflow and
should have narrow, explicit responsibilities. Changes to serialisation,
sorting, hashing or metadata formats should be treated carefully because they
can affect reproducibility and compatibility with existing artefacts.
"""

"""
lrt_phase3_utils.py

Small shared utilities for Phase 3 hardening of the Local Relational Topology
retrieval framework.

The module is intentionally dependency-light. It centralizes common behaviours
that should not be copy-pasted across the retrieval runner, material store,
physical plausibility annotator, samplers, evaluators, and interpretation layer:

- stable JSON artifact writing
- deterministic dataframe sorting
- lightweight schema validation
- idempotent logging setup
- run/config metadata helpers

It does not alter any retrieval scores or scientific logic.
"""

import hashlib
import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

PHASE3_UTILS_SCHEMA_VERSION = "phase3.utils.v1"


def configure_logger(name: str, level: int = logging.INFO, log_file: Optional[str | Path] = None) -> logging.Logger:
    """Create or update a named logger without duplicating console handlers."""

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_lrt_console", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler._lrt_console = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(handler)
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(handler)
    return logger


def json_default(value: Any) -> Any:
    """JSON serializer for common scientific Python values."""

    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return asdict(value)
    if np is not None:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.ndarray,)):
            return value.tolist()
    return str(value)


def write_json_artifact(payload: Mapping[str, Any], path: str | Path) -> None:
    """Write a stable, sorted JSON artifact."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(payload), f, indent=2, sort_keys=True, default=json_default)


def read_json_artifact(path: str | Path) -> dict[str, Any]:
    """Read a JSON artifact."""

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_sha256(path: str | Path, block_size: int = 1024 * 1024) -> str:
    """Return SHA-256 for a file, useful in run metadata."""

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            h.update(block)
    return h.hexdigest()


def require_columns(df: Any, required: Iterable[str], label: str = "dataframe") -> None:
    """Raise a clear error when required columns are missing."""

    missing = [col for col in required if col not in getattr(df, "columns", [])]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def optional_columns_present(df: Any, optional: Iterable[str]) -> list[str]:
    """Return optional columns that are present in a dataframe-like object."""

    cols = set(getattr(df, "columns", []))
    return [col for col in optional if col in cols]


def deterministic_sort(df: Any, columns: Sequence[str], reset_index: bool = True) -> Any:
    """Return a dataframe sorted with a stable merge sort using present columns only."""

    if pd is None:
        raise RuntimeError("pandas is required for deterministic_sort().")
    present = [col for col in columns if col in df.columns]
    out = df.copy()
    if present:
        out = out.sort_values(present, kind="mergesort")
    if reset_index:
        out = out.reset_index(drop=True)
    return out


def run_metadata(
    *,
    run_label: str,
    config: Mapping[str, Any],
    schema_version: str,
    code_files: Optional[Sequence[str | Path]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build a compact run metadata payload."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "phase3_utils_schema_version": PHASE3_UTILS_SCHEMA_VERSION,
        "run_label": run_label,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": dict(config),
    }
    if code_files:
        payload["code_file_sha256"] = {
            str(Path(path).name): file_sha256(path) for path in code_files if Path(path).exists()
        }
    if extra:
        payload.update(dict(extra))
    return payload


__all__ = [
    "PHASE3_UTILS_SCHEMA_VERSION",
    "configure_logger",
    "json_default",
    "write_json_artifact",
    "read_json_artifact",
    "file_sha256",
    "require_columns",
    "optional_columns_present",
    "deterministic_sort",
    "run_metadata",
]
