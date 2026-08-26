#!/usr/bin/env python3
"""
Batch structural-context pipeline runner.

Overview
--------
This module orchestrates execution of the structural-context pipeline across
multiple materials. It is responsible for scheduling batch execution,
maintaining reproducibility, recording progress, and collecting consolidated
outputs. Scientific calculations remain delegated to the underlying pipeline
modules.

Responsibilities
----------------
* Parse batch inputs.
* Execute each candidate deterministically.
* Support resumable execution where implemented.
* Record successes, failures and runtime information.
* Produce consolidated batch artefacts.

Architectural role
------------------
This is an orchestration layer only. It should coordinate processing rather
than implement evidence generation, role inference or physical-plausibility
logic.

Maintenance notes
-----------------
Future enhancements should favour operational improvements such as batching,
parallelism, checkpointing and reporting. Changes should preserve output schema
compatibility and deterministic behaviour whenever practical.

batch_role_prior_runner.py

Batch orchestrator for the Cheap Context First / role-prior pipeline.

Phase 1A scope
--------------
This runner deliberately wraps the existing single-material pipeline
(run_context_pipeline.py) rather than importing and refactoring the scientific
modules. That keeps Hub/Boundary/Other scoring untouched while adding batch
execution, resume support, runtime logging, failure logging, and combined
summaries.

Supported input modes
---------------------
1) JARVIS IDs from a CSV/text file:
   python3 batch_role_prior_runner.py --input_ids validation_ids.csv --project_dir . --output_dir batch_outputs --reuse_cache

2) External JSON profiles from a CSV/text file:
   python3 batch_role_prior_runner.py --external_json_list external_jsons.csv --project_dir . --output_dir batch_external_outputs --reuse_cache

3) External JSON profiles from a directory:
   python3 batch_role_prior_runner.py --external_json_dir external_profiles --project_dir . --output_dir batch_external_outputs --reuse_cache

Notes
-----
This structural-context-profile version preserves the existing legacy batch
summary while aggregating structural_context_profile_v2.json into
structural_context_batch_summary.csv. Legacy fields remain available in batch_summary.csv.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "cheap_context_first.batch_role_prior_runner.phase1a.structural_context_profile.v2.1"


# ---------------------------------------------------------------------------
# General utilities
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def quote_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(x)) for x in cmd)


def safe_slug(value: str, fallback: str = "case") -> str:
    value = str(value or "").strip()
    if not value:
        value = fallback
    value = value.replace(os.sep, "_")
    value = re.sub(r"[^A-Za-z0-9_.=-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("._")
    return value or fallback


def file_digest_short(path: Path, length: int = 10) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:length]


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: List[str] = []
        seen = set()
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

JID_RE = re.compile(r"^JVASP-\d+", re.IGNORECASE)


def read_text_or_csv(path: Path) -> List[Dict[str, str]]:
    """Read a CSV or newline-delimited file into row dictionaries.

    CSV files may contain headers. Text files may contain one material/path per
    line. Comments beginning with # are ignored.
    """
    text = path.read_text(encoding="utf-8-sig")
    non_empty = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not non_empty:
        return []

    # Treat as CSV if extension suggests it, or if first useful line has commas.
    if path.suffix.lower() in {".csv", ".tsv"} or ("," in non_empty[0]) or ("\t" in non_empty[0]):
        dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.excel
        reader = csv.DictReader(non_empty, dialect=dialect)
        if reader.fieldnames:
            return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]

    return [{"value": ln.strip()} for ln in non_empty]


def first_present(row: Dict[str, Any], names: Sequence[str]) -> str:
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        v = lowered.get(name.lower())
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def load_jid_jobs(path: Path) -> List[Dict[str, Any]]:
    rows = read_text_or_csv(path)
    jobs: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        jid = first_present(row, ["jid", "jarvis_id", "material_id", "id", "case_id", "value"])
        # In validation CSVs, case_id is not a JID, so prefer explicit jid-like columns first.
        explicit_jid = first_present(row, ["jid", "jarvis_id", "material_id"])
        if explicit_jid:
            jid = explicit_jid
        if not jid or not JID_RE.match(jid):
            # If the row's value contains a JID somewhere, extract it.
            match = JID_RE.search(" ".join(str(v) for v in row.values()))
            if match:
                jid = match.group(0).upper()
        if not jid or not JID_RE.match(jid):
            continue
        label = first_present(row, ["label", "case_id", "material", "formula", "name"])
        jobs.append(
            {
                "input_type": "jid",
                "jid": jid.upper(),
                "case_id": first_present(row, ["case_id", "validation_case_id"]) or jid.upper(),
                "label": label,
                "source_row_index": idx,
            }
        )
    return dedupe_jobs(jobs)


def load_external_json_jobs(path: Path) -> List[Dict[str, Any]]:
    rows = read_text_or_csv(path)
    jobs: List[Dict[str, Any]] = []
    base = path.parent
    for idx, row in enumerate(rows, start=1):
        p = first_present(row, ["external_json", "json", "path", "file", "filepath", "value"])
        if not p:
            continue
        json_path = Path(p).expanduser()
        if not json_path.is_absolute():
            json_path = (base / json_path).resolve()
        ext_id = first_present(row, ["external_id", "id", "case_id", "label"])
        if not ext_id:
            ext_id = json_path.stem
        jobs.append(
            {
                "input_type": "external_json",
                "external_json": str(json_path),
                "external_id": safe_slug(ext_id, json_path.stem),
                "case_id": first_present(row, ["case_id", "validation_case_id"]) or safe_slug(ext_id, json_path.stem),
                "label": first_present(row, ["label", "formula", "material", "name"]),
                "source_row_index": idx,
            }
        )
    return dedupe_jobs(jobs)


def load_external_json_dir(path: Path) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for idx, json_path in enumerate(sorted(path.glob("*.json")), start=1):
        ext_id = safe_slug(json_path.stem)
        jobs.append(
            {
                "input_type": "external_json",
                "external_json": str(json_path.resolve()),
                "external_id": ext_id,
                "case_id": ext_id,
                "label": json_path.stem,
                "source_row_index": idx,
            }
        )
    return dedupe_jobs(jobs)


def dedupe_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for job in jobs:
        if job["input_type"] == "jid":
            key = ("jid", job.get("jid"))
        else:
            key = ("external_json", str(job.get("external_json")))
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


# ---------------------------------------------------------------------------
# Output extraction
# ---------------------------------------------------------------------------

def maybe_read_first_csv_row(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                return {k: v for k, v in row.items()}
    except Exception:
        return {}
    return {}


def find_first(mapping: Dict[str, Any], names: Sequence[str]) -> Any:
    lower = {str(k).lower(): v for k, v in mapping.items()}
    for name in names:
        if name.lower() in lower and str(lower[name.lower()]).strip() != "":
            return lower[name.lower()]
    return ""



def nested_get(mapping: Dict[str, Any], path: Sequence[str], default: Any = "") -> Any:
    """Safely get a nested value from a JSON-like dictionary."""
    cur: Any = mapping
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur.get(key)
    if cur is None:
        return default
    return cur


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in [None, ""]:
            return value
    return ""


def extract_structural_context_profile_v2_fields(profile_v2: Dict[str, Any]) -> Dict[str, Any]:
    """Extract stable, batch-friendly fields from structural_context_profile_v2.json."""
    if not isinstance(profile_v2, dict) or not profile_v2:
        return {}

    query = profile_v2.get("query_material") or {}
    rel = profile_v2.get("relational_measurements") or {}
    reliability = profile_v2.get("reliability_diagnostics") or {}
    interpretation = profile_v2.get("interpretation") or {}
    pattern = interpretation.get("contextual_pattern") or {}
    evidence = reliability.get("evidence_sufficiency") or {}
    retrieval = reliability.get("retrieval_completeness") or {}
    independence = reliability.get("pool_independence") or {}
    ambiguity = reliability.get("context_ambiguity") or {}
    confidence = reliability.get("profile_confidence") or {}

    return {
        "profile_v2_schema_version": profile_v2.get("schema_version", ""),
        "profile_v2_created_at_utc": profile_v2.get("created_at_utc", ""),
        "profile_jid": first_non_empty(query.get("jid"), query.get("jarvis_id"), query.get("material_id")),
        "profile_formula": first_non_empty(query.get("formula"), query.get("reduced_formula")),
        "profile_chemical_system": query.get("chemical_system", ""),
        "profile_composition_family": query.get("composition_family", ""),
        "profile_formula_family": query.get("formula_family", ""),
        "profile_prototype_family": query.get("prototype_family", ""),
        "profile_structure_variant": query.get("structure_variant", ""),
        "profile_spacegroup_number": query.get("spacegroup_number", ""),
        "profile_spacegroup_symbol": query.get("spacegroup_symbol", ""),

        "local_context_support": rel.get("local_context_support", ""),
        "local_context_support_band": rel.get("local_context_support_band", ""),
        "local_context_support_confidence": rel.get("local_context_support_confidence", ""),
        "structural_regime_contrast": rel.get("structural_regime_contrast", ""),
        "structural_regime_contrast_band": rel.get("structural_regime_contrast_band", ""),
        "structural_regime_contrast_confidence": rel.get("structural_regime_contrast_confidence", ""),
        "neighbourhood_coherence": rel.get("neighbourhood_coherence", ""),
        "structural_context_diversity": rel.get("structural_context_diversity", ""),
        "structural_context_diversity_status": rel.get("structural_context_diversity_status", ""),

        "evidence_sufficiency_score": evidence.get("score", ""),
        "evidence_sufficiency_status": evidence.get("status", ""),
        "retrieval_completeness": retrieval.get("score", ""),
        "retrieval_completeness_status": retrieval.get("status", ""),
        "pool_independence": independence.get("score", ""),
        "pool_overlap_rate": independence.get("pool_overlap_rate", ""),
        "candidate_ids_in_multiple_pools": independence.get("candidate_ids_in_multiple_pools", ""),
        "unique_candidate_count_across_all_pools": independence.get("unique_candidate_count_across_all_pools", ""),
        "context_ambiguity": ambiguity.get("score", ""),
        "context_ambiguity_band": ambiguity.get("band", ""),
        "profile_confidence": confidence.get("score", ""),
        "profile_confidence_band": confidence.get("band", ""),
        "profile_quality_flags": stringify_cell(reliability.get("quality_flags", "")),

        "contextual_pattern": pattern.get("code", ""),
        "contextual_pattern_label": pattern.get("label", ""),
        "contextual_pattern_summary": pattern.get("summary", ""),
        "hub_like_interpretation": pattern.get("hub_like_interpretation", ""),
        "boundary_like_interpretation": pattern.get("boundary_like_interpretation", ""),

        # Explicit transition aliases for regression checks.
        "legacy_hub_strength": rel.get("local_context_support", ""),
        "legacy_boundary_strength": rel.get("structural_regime_contrast", ""),
        "legacy_structural_diversity": rel.get("structural_context_diversity", ""),
    }


def structural_context_batch_row(summary_row: Dict[str, Any]) -> Dict[str, Any]:
    """Return the v2 profile-centred subset for structural_context_batch_summary.csv."""
    keys = [
        "batch_index", "case_id", "label", "input_type", "jid", "external_id",
        "material_id", "formula", "profile_formula", "profile_chemical_system",
        "profile_composition_family", "profile_formula_family", "profile_prototype_family",
        "profile_structure_variant", "local_context_support", "local_context_support_band",
        "local_context_support_confidence", "structural_regime_contrast",
        "structural_regime_contrast_band", "structural_regime_contrast_confidence",
        "neighbourhood_coherence", "structural_context_diversity",
        "structural_context_diversity_status", "evidence_sufficiency_score",
        "evidence_sufficiency_status", "retrieval_completeness", "retrieval_completeness_status",
        "pool_independence", "pool_overlap_rate", "context_ambiguity", "context_ambiguity_band",
        "profile_confidence", "profile_confidence_band", "contextual_pattern",
        "contextual_pattern_label", "contextual_pattern_summary", "hub_like_interpretation",
        "boundary_like_interpretation", "profile_quality_flags", "output_dir",
    ]
    return {k: summary_row.get(k, "") for k in keys}


def extract_summary(case_output_dir: Path) -> Dict[str, Any]:
    """Extract legacy batch fields plus authoritative v2 profile fields."""
    role_dir = case_output_dir / "role_priors"
    evidence_dir = case_output_dir / "evidence"
    pools_dir = case_output_dir / "pools"
    profile_dir = case_output_dir / "profile"

    summary_json = read_json(role_dir / "role_prior_summary.json")
    evidence_record = read_json(role_dir / "structural_context_evidence_record.json")
    legacy_profile = read_json(role_dir / "structural_context_profile.json")
    profile_v2 = read_json(role_dir / "structural_context_profile_v2.json")
    profile = read_json(profile_dir / "query_profile.json")
    pool_summary = read_json(pools_dir / "candidate_pool_summary.json")
    evidence_summary = read_json(evidence_dir / "cheap_evidence_summary.json")

    structural_row = maybe_read_first_csv_row(role_dir / "structural_context_summary.csv")
    ranking_row = maybe_read_first_csv_row(role_dir / "role_ranking.csv")
    plausibility_row = maybe_read_first_csv_row(role_dir / "role_plausibility_table.csv")

    combined: Dict[str, Any] = {}
    for source in [summary_json, evidence_record, structural_row, ranking_row, plausibility_row, evidence_summary, profile]:
        if isinstance(source, dict):
            combined.update({k: v for k, v in source.items() if v not in [None, ""]})

    primary_role = find_first(combined, ["predicted_primary_role", "primary_role", "top_role", "role", "role_name", "context_role", "classification"])
    primary_score = find_first(combined, ["primary_role_score", "top_score", "score", "role_score", "plausibility_score"])
    hub_score = find_first(combined, ["hub_score", "hub", "hub_prior", "hub_plausibility"])
    boundary_score = find_first(combined, ["boundary_score", "boundary", "boundary_prior", "boundary_plausibility"])
    confidence = find_first(combined, ["confidence", "primary_role_confidence", "classification_confidence"])
    secondary_descriptors = find_first(combined, ["predicted_secondary_descriptors", "secondary_descriptors", "secondary_descriptor", "other_descriptors"])
    quality_flags = find_first(combined, ["quality_flags", "flags", "warnings"])
    formula = find_first(combined, ["formula", "reduced_formula", "chemical_formula", "pretty_formula"])
    material_id = find_first(combined, ["jid", "jarvis_id", "material_id", "external_id", "query_id"])

    def pool_count(name: str) -> Any:
        for obj in [pool_summary, evidence_summary, combined]:
            if not isinstance(obj, dict):
                continue
            for key in [name, f"{name}_count", f"n_{name}", f"{name}_n"]:
                if key in obj and obj[key] not in [None, ""]:
                    return obj[key]
            pools = obj.get("pools") or obj.get("pool_counts")
            if isinstance(pools, dict) and name in pools:
                val = pools[name]
                if isinstance(val, dict):
                    return val.get("count") or val.get("n") or ""
                return val
        return ""

    row = {
        "material_id": material_id,
        "formula": formula,
        "primary_role": primary_role,
        "primary_role_score": primary_score,
        "confidence": confidence,
        "hub_score": hub_score,
        "boundary_score": boundary_score,
        "secondary_descriptors": stringify_cell(secondary_descriptors),
        "quality_flags": stringify_cell(quality_flags),
        "same_family_count": pool_count("same_family"),
        "adjacent_family_count": pool_count("adjacent_family"),
        "boundary_contrast_count": pool_count("boundary_contrast"),
        "wildcard_count": pool_count("wildcard"),
        "negative_control_count": pool_count("negative_control"),
        "structural_context_profile_available": bool(legacy_profile),
        "structural_context_profile_v2_available": bool(profile_v2),
    }
    row.update(extract_structural_context_profile_v2_fields(profile_v2))
    legacy_meas = (legacy_profile.get("measurements") or {}) if isinstance(legacy_profile, dict) else {}
    row["legacy_hub_strength"] = legacy_meas.get("hub_strength", "")
    row["legacy_boundary_strength"] = legacy_meas.get("boundary_strength", "")
    row["legacy_structural_diversity"] = legacy_meas.get("structural_diversity", "")
    return row


def stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ";".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


# ---------------------------------------------------------------------------
# Batch execution
# ---------------------------------------------------------------------------

def build_pipeline_command(args: argparse.Namespace, job: Dict[str, Any], case_output_dir: Path) -> List[str]:
    cmd = [args.python, str(args.pipeline_script)]

    if job["input_type"] == "jid":
        cmd += ["--jid", job["jid"]]
    elif job["input_type"] == "external_json":
        cmd += ["--external_json", job["external_json"]]
        if job.get("external_id"):
            cmd += ["--external_id", job["external_id"]]
        if args.include_external_in_universe:
            cmd += ["--include_external_in_universe"]
    else:
        raise ValueError(f"Unsupported input_type: {job.get('input_type')}")

    cmd += ["--output_dir", str(case_output_dir)]
    cmd += ["--scripts_dir", str(args.scripts_dir)]
    cmd += ["--python", args.python]

    if args.material_store_config:
        cmd += ["--material_store_config", str(args.material_store_config)]
    if args.seed is not None:
        cmd += ["--seed", str(args.seed)]

    for name in [
        "same_family_size",
        "adjacent_family_size",
        "boundary_contrast_size",
        "wildcard_size",
        "negative_control_size",
    ]:
        val = getattr(args, name)
        if val is not None:
            cmd += [f"--{name}", str(val)]

    # Cache reuse in Phase 1A means: do not rebuild descriptors and reuse stage outputs when present.
    if args.force_rebuild_descriptor_cache:
        cmd += ["--force_rebuild_descriptor_cache"]
    if args.reuse_cache:
        # Reuse expensive upstream stages, but rerun role priors so the v2 profile is generated/refreshed.
        cmd += ["--skip_profile", "--skip_pools", "--skip_evidence"]
    elif args.skip_existing_stages:
        cmd += ["--skip_profile", "--skip_pools", "--skip_evidence", "--skip_role_priors"]

    if args.non_strict_output_checks:
        cmd += ["--non_strict_output_checks"]
    if args.no_output_checks:
        cmd += ["--no_output_checks"]
    if args.dry_run:
        cmd += ["--dry_run"]

    return cmd


def case_output_name(job: Dict[str, Any], index: int) -> str:
    if job["input_type"] == "jid":
        return safe_slug(job.get("jid") or f"case_{index:05d}")
    ext_id = job.get("external_id") or Path(str(job.get("external_json", "external"))).stem
    return safe_slug(ext_id or f"external_{index:05d}")


def is_case_complete(case_output_dir: Path) -> bool:
    role_dir = case_output_dir / "role_priors"
    profile_v2 = role_dir / "structural_context_profile_v2.json"
    metadata = case_output_dir / "run_metadata.json"
    if not profile_v2.exists() or not metadata.exists():
        return False
    meta = read_json(metadata)
    return meta.get("status") == "success"


def run_one_case(args: argparse.Namespace, job: Dict[str, Any], index: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    output_name = case_output_name(job, index)
    case_output_dir = args.output_dir / output_name
    case_output_dir.mkdir(parents=True, exist_ok=True)

    base_record: Dict[str, Any] = {
        "batch_index": index,
        "case_id": job.get("case_id", ""),
        "label": job.get("label", ""),
        "input_type": job.get("input_type", ""),
        "jid": job.get("jid", ""),
        "external_id": job.get("external_id", ""),
        "external_json": job.get("external_json", ""),
        "output_dir": str(case_output_dir),
        "started_at_utc": utc_now(),
        "finished_at_utc": "",
        "runtime_seconds": "",
        "status": "pending",
        "returncode": "",
        "command": "",
        "error": "",
    }

    if args.skip_completed and not args.force and is_case_complete(case_output_dir):
        summary = extract_summary(case_output_dir)
        base_record.update(
            {
                "finished_at_utc": utc_now(),
                "runtime_seconds": 0.0,
                "status": "skipped_completed",
                "returncode": 0,
            }
        )
        return base_record, {**base_record, **summary}

    cmd = build_pipeline_command(args, job, case_output_dir)
    base_record["command"] = quote_cmd(cmd)

    t0 = time.perf_counter()
    try:
        if args.dry_run:
            print(f"\n[{index}] DRY RUN {output_name}")
            print(quote_cmd(cmd))
            returncode = 0
        else:
            print(f"\n[{index}] Running {output_name}")
            print(quote_cmd(cmd))
            proc = subprocess.run(
                cmd,
                cwd=str(args.scripts_dir),
                text=True,
                stdout=None if not args.quiet else subprocess.DEVNULL,
                stderr=None if not args.quiet else subprocess.DEVNULL,
            )
            returncode = proc.returncode
        elapsed = round(time.perf_counter() - t0, 3)
        base_record.update(
            {
                "finished_at_utc": utc_now(),
                "runtime_seconds": elapsed,
                "status": "success" if returncode == 0 and (args.dry_run or is_case_complete(case_output_dir)) else "failed",
                "returncode": returncode,
            }
        )
        if returncode == 0 and not args.dry_run and not is_case_complete(case_output_dir):
            # The pipeline may return 0 only for success, but keep the check explicit.
            meta = read_json(case_output_dir / "run_metadata.json")
            base_record["error"] = f"Pipeline returned 0 but completion check failed. run_metadata status={meta.get('status', '')}"
        if returncode != 0:
            base_record["error"] = f"run_context_pipeline.py returned {returncode}"
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 3)
        base_record.update(
            {
                "finished_at_utc": utc_now(),
                "runtime_seconds": elapsed,
                "status": "failed",
                "returncode": "",
                "error": repr(exc),
            }
        )

    summary = extract_summary(case_output_dir) if base_record["status"] in {"success", "skipped_completed"} else {}
    return base_record, {**base_record, **summary}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch runner for run_context_pipeline.py. Phase 1A: JARVIS IDs and external JSON profiles."
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input_ids", help="CSV/text file containing JARVIS IDs. Recognised columns: jid, jarvis_id, material_id.")
    source.add_argument("--external_json_list", help="CSV/text file containing external JSON paths. Recognised columns: external_json, path, file.")
    source.add_argument("--external_json_dir", help="Directory containing external material JSON profiles.")

    parser.add_argument("--project_dir", required=True, help="Project directory containing run_context_pipeline.py and pipeline scripts.")
    parser.add_argument("--output_dir", required=True, help="Batch output directory.")
    parser.add_argument("--scripts_dir", default=None, help="Directory containing pipeline scripts. Defaults to --project_dir.")
    parser.add_argument("--pipeline_script", default=None, help="Path to run_context_pipeline.py. Defaults to --project_dir/run_context_pipeline.py.")
    parser.add_argument("--python", default=sys.executable or "python3", help="Python executable to use.")

    parser.add_argument("--reuse_cache", action="store_true", help="Reuse existing stage outputs by passing skip flags to run_context_pipeline.py.")
    parser.add_argument("--skip_existing_stages", action="store_true", help="Alias-like behaviour: pass skip flags for profile/pools/evidence/role priors.")
    parser.add_argument("--skip_completed", action="store_true", default=True, help="Skip cases with successful run_metadata.json and role_prior_summary.json. Default true.")
    parser.add_argument("--no_skip_completed", dest="skip_completed", action="store_false", help="Do not skip completed cases.")
    parser.add_argument("--force", action="store_true", help="Rerun cases even if completed.")
    parser.add_argument("--force_rebuild_descriptor_cache", action="store_true", help="Forward descriptor-cache rebuild to pipeline. Usually do NOT use in batch.")

    parser.add_argument("--material_store_config", default=None, help="Optional MaterialStoreConfig JSON forwarded to pipeline.")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed forwarded to candidate_pool_builder via pipeline.")
    parser.add_argument("--same_family_size", type=int, default=None)
    parser.add_argument("--adjacent_family_size", type=int, default=None)
    parser.add_argument("--boundary_contrast_size", type=int, default=None)
    parser.add_argument("--wildcard_size", type=int, default=None)
    parser.add_argument("--negative_control_size", type=int, default=None)

    parser.add_argument("--include_external_in_universe", action="store_true", help="Forward to external profile handling. Usually leave off.")
    parser.add_argument("--non_strict_output_checks", action="store_true", help="Forward to pipeline.")
    parser.add_argument("--no_output_checks", action="store_true", help="Forward to pipeline.")
    parser.add_argument("--dry_run", action="store_true", help="Print commands and write batch manifest/logs without executing pipeline stages.")
    parser.add_argument("--quiet", action="store_true", help="Suppress child pipeline stdout/stderr. Errors are still logged by return code.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of jobs to run for smoke tests.")
    parser.add_argument("--stop_on_failure", action="store_true", help="Stop batch after first failed case.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    args.project_dir = Path(args.project_dir).expanduser().resolve()
    args.scripts_dir = Path(args.scripts_dir).expanduser().resolve() if args.scripts_dir else args.project_dir
    args.output_dir = Path(args.output_dir).expanduser().resolve()
    args.pipeline_script = Path(args.pipeline_script).expanduser().resolve() if args.pipeline_script else (args.project_dir / "run_context_pipeline.py")

    if not args.pipeline_script.exists():
        parser.error(f"run_context_pipeline.py not found: {args.pipeline_script}")
    if not args.scripts_dir.exists():
        parser.error(f"scripts_dir not found: {args.scripts_dir}")

    if args.input_ids:
        jobs = load_jid_jobs(Path(args.input_ids).expanduser().resolve())
        input_source = str(Path(args.input_ids).expanduser().resolve())
    elif args.external_json_list:
        jobs = load_external_json_jobs(Path(args.external_json_list).expanduser().resolve())
        input_source = str(Path(args.external_json_list).expanduser().resolve())
    else:
        jobs = load_external_json_dir(Path(args.external_json_dir).expanduser().resolve())
        input_source = str(Path(args.external_json_dir).expanduser().resolve())

    if args.limit is not None:
        jobs = jobs[: max(0, args.limit)]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "status": "running",
        "input_source": input_source,
        "input_count": len(jobs),
        "project_dir": str(args.project_dir),
        "scripts_dir": str(args.scripts_dir),
        "pipeline_script": str(args.pipeline_script),
        "output_dir": str(args.output_dir),
        "python": args.python,
        "options": {
            "reuse_cache": args.reuse_cache,
            "skip_completed": args.skip_completed,
            "force": args.force,
            "force_rebuild_descriptor_cache": args.force_rebuild_descriptor_cache,
            "dry_run": args.dry_run,
            "seed": args.seed,
            "pool_sizes": {
                "same_family_size": args.same_family_size,
                "adjacent_family_size": args.adjacent_family_size,
                "boundary_contrast_size": args.boundary_contrast_size,
                "wildcard_size": args.wildcard_size,
                "negative_control_size": args.negative_control_size,
            },
        },
        "warnings": [],
    }

    if args.force_rebuild_descriptor_cache:
        manifest["warnings"].append("force_rebuild_descriptor_cache is enabled. This is usually slow and not recommended for large batches.")

    write_json(args.output_dir / "batch_manifest.json", manifest)

    runtime_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []
    structural_context_rows: List[Dict[str, Any]] = []
    failed_rows: List[Dict[str, Any]] = []

    batch_t0 = time.perf_counter()
    print(f"Batch jobs: {len(jobs)}")
    print(f"Output dir: {args.output_dir}")

    for index, job in enumerate(jobs, start=1):
        runtime, summary = run_one_case(args, job, index)
        runtime_rows.append(runtime)
        summary_rows.append(summary)
        structural_context_rows.append(structural_context_batch_row(summary))
        if runtime.get("status") == "failed":
            failed_rows.append(runtime)
            if args.stop_on_failure:
                break

        # Write incrementally so a long batch still leaves useful logs if interrupted.
        write_csv(args.output_dir / "batch_runtime_log.csv", runtime_rows)
        write_csv(args.output_dir / "batch_summary.csv", summary_rows)
        write_csv(args.output_dir / "structural_context_batch_summary.csv", structural_context_rows)
        write_csv(args.output_dir / "failed_cases.csv", failed_rows)

    elapsed = round(time.perf_counter() - batch_t0, 3)
    success_count = sum(1 for r in runtime_rows if r.get("status") == "success")
    skipped_count = sum(1 for r in runtime_rows if r.get("status") == "skipped_completed")
    failed_count = sum(1 for r in runtime_rows if r.get("status") == "failed")

    manifest.update(
        {
            "finished_at_utc": utc_now(),
            "runtime_seconds": elapsed,
            "status": "success" if failed_count == 0 else "completed_with_failures",
            "completed_count": len(runtime_rows),
            "success_count": success_count,
            "skipped_completed_count": skipped_count,
            "failed_count": failed_count,
            "outputs": {
                "batch_summary_csv": str(args.output_dir / "batch_summary.csv"),
                "structural_context_batch_summary_csv": str(args.output_dir / "structural_context_batch_summary.csv"),
                "batch_runtime_log_csv": str(args.output_dir / "batch_runtime_log.csv"),
                "failed_cases_csv": str(args.output_dir / "failed_cases.csv"),
            },
        }
    )
    write_json(args.output_dir / "batch_manifest.json", manifest)

    print("\n=== Batch complete ===")
    print(f"Status:   {manifest['status']}")
    print(f"Success:  {success_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Failed:   {failed_count}")
    print(f"Runtime:  {elapsed}s")
    print(f"Summary:  {args.output_dir / 'batch_summary.csv'}")
    print(f"Log:      {args.output_dir / 'batch_runtime_log.csv'}")
    print(f"Failures: {args.output_dir / 'failed_cases.csv'}")

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
