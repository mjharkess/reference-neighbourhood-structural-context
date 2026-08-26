#!/usr/bin/env python3
"""
Context pipeline orchestration.

Overview
--------
Coordinates the end-to-end execution of the Cheap Context First pipeline.

Responsibilities
----------------
- Validate inputs.
- Invoke each processing stage in sequence.
- Manage intermediate artefacts.
- Preserve reproducible execution.
- Report execution status consistently.

Developer notes
---------------
This module is intentionally an orchestration layer. Scientific algorithms
should remain in the specialist modules that this runner invokes.
"""


from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence


SCHEMA_VERSION = "cheap_context_first.pipeline_wrapper.v4_reference_neighbourhood_fingerprint"

MappingLike = Dict[str, Any]


EXPECTED_OUTPUTS: Dict[str, List[str]] = {
    "material_profile_builder": [
        "query_profile.json",
    ],
    "candidate_pool_builder": [
        "same_family_pool.csv",
        "adjacent_family_pool.csv",
        "boundary_contrast_pool.csv",
        "wildcard_pool.csv",
        "negative_control_pool.csv",
        "candidate_pool_summary.json",
        "pool_config_used.json",
    ],
    "cheap_evidence_metrics": [
        "cheap_evidence_summary.json",
        "cheap_evidence_metrics.csv",
        "cheap_evidence_concepts.csv",
        "pool_level_metrics.csv",
        "pool_context_summary.json",
        "pool_context_summary.csv",
        "reference_neighbourhood_fingerprint.json",
        "missing_value_report.csv",
        "evidence_report.md",
    ],
    # The role-prior stage is handled dynamically because v2 outputs are always
    # required while legacy outputs are optional for the transition release.
}

ROLE_PRIOR_V2_OUTPUTS: List[str] = [
    "structural_context_profile_v2.json",
    "structural_context_profile_v2_measurements.csv",
    "structural_context_profile_v2_reliability.csv",
    "structural_context_profile_v2_interpretation.csv",
    "structural_context_profile_v2_summary.csv",
    "structural_context_report_v2.md",
]

ROLE_PRIOR_LEGACY_OUTPUTS: List[str] = [
    "role_prior_summary.json",
    "role_plausibility_table.csv",
    "role_contradictions.csv",
    "structural_context_report.md",
    "structural_context_summary.csv",
    "structural_context_evidence_record.json",
    "role_prior_config_used.json",
    "role_ranking.csv",
    "role_ranked_explanations.csv",
    "structural_context_profile.json",
    "structural_context_profile_v1.json",
]



def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def quote_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(x)) for x in cmd)


def script_path(scripts_dir: Path, filename: str) -> Path:
    return scripts_dir / filename


def ensure_script_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Required script not found: {path}\n"
            f"Place the script in --scripts_dir or pass the correct --scripts_dir."
        )
    if not path.is_file():
        raise FileNotFoundError(f"Required script path is not a file: {path}")


def write_json(path: Path, payload: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def check_expected_outputs(
    step_name: str,
    output_dir: Path,
    *,
    required_files: Sequence[str],
    dry_run: bool,
    strict: bool,
) -> Dict[str, Any]:
    """
    Check whether a pipeline stage produced the files expected by downstream stages.

    This is deliberately a wrapper-level check. The scientific logic still belongs
    in the underlying scripts; the wrapper merely prevents missing outputs from
    being silently carried into later stages, because silent failure is just
    technical debt wearing camouflage.
    """
    record: Dict[str, Any] = {
        "step": step_name,
        "checked_at_utc": utc_now(),
        "output_dir": str(output_dir),
        "required_files": list(required_files),
        "present_files": [],
        "missing_files": [],
        "status": "not_checked",
    }

    if dry_run:
        record["status"] = "dry_run_not_checked"
        return record

    for rel in required_files:
        path = output_dir / rel
        if path.exists() and path.is_file():
            record["present_files"].append(rel)
        else:
            record["missing_files"].append(rel)

    record["status"] = "complete" if not record["missing_files"] else "missing_outputs"

    if strict and record["missing_files"]:
        missing = ", ".join(record["missing_files"])
        raise FileNotFoundError(
            f"Step '{step_name}' completed but expected output file(s) were not found in {output_dir}: {missing}"
        )

    return record


def run_step(
    step_name: str,
    cmd: List[str],
    cwd: Optional[Path],
    dry_run: bool,
    continue_on_error: bool,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    started = utc_now()
    record: Dict[str, Any] = {
        "step": step_name,
        "command": quote_cmd(cmd),
        "started_at_utc": started,
        "finished_at_utc": None,
        "returncode": None,
        "status": "pending",
    }

    print(f"\n=== {step_name} ===")
    print(quote_cmd(cmd))

    if dry_run:
        record["finished_at_utc"] = utc_now()
        record["returncode"] = 0
        record["status"] = "dry_run"
        return record

    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=sys.stdout,
        stderr=sys.stderr,
        env=env,
    )
    record["finished_at_utc"] = utc_now()
    record["returncode"] = proc.returncode
    record["status"] = "success" if proc.returncode == 0 else "failed"

    if proc.returncode != 0 and not continue_on_error:
        raise RuntimeError(f"Step failed: {step_name} with return code {proc.returncode}")

    return record


def append_skip_record(step_name: str) -> Dict[str, Any]:
    return {
        "step": step_name,
        "status": "skipped_existing",
        "command": None,
        "returncode": 0,
        "started_at_utc": utc_now(),
        "finished_at_utc": utc_now(),
    }


def infer_run_id(args: argparse.Namespace) -> str:
    if args.jid:
        return args.jid
    if args.external_id:
        return args.external_id
    return "external_material"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full Cheap Context First pipeline for a JARVIS ID or an external material JSON."
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jid", help="JARVIS material ID, e.g. JVASP-20955")
    source.add_argument("--external_json", help="External material profile/descriptor JSON")

    parser.add_argument("--external_id", help="Optional external ID label, e.g. EXT-0001")
    parser.add_argument(
        "--include_external_in_universe",
        action="store_true",
        help="Forward to material_profile_builder.py. Usually leave off unless intentionally adding external material to universe.",
    )

    parser.add_argument(
        "--output_dir",
        required=True,
        help="Base output directory. Subfolders profile/, pools/, evidence/, role_priors/ will be created.",
    )
    parser.add_argument(
        "--scripts_dir",
        default=".",
        help="Directory containing material_profile_builder.py, candidate_pool_builder.py, cheap_evidence_metrics.py, role_prior_engine.py",
    )
    parser.add_argument(
        "--python",
        default=sys.executable or "python3",
        help="Python executable to use when launching pipeline scripts. Defaults to current Python.",
    )

    parser.add_argument("--force_rebuild_descriptor_cache", action="store_true", help="Forward to scripts that support descriptor-cache rebuild.")
    parser.add_argument("--material_store_config", default=None, help="Optional MaterialStoreConfig JSON for candidate_pool_builder.py")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed for candidate_pool_builder.py")

    # Optional pool size overrides. Defaults are left to candidate_pool_builder.py when not supplied.
    parser.add_argument("--same_family_size", type=int, default=None)
    parser.add_argument("--adjacent_family_size", type=int, default=None)
    parser.add_argument("--boundary_contrast_size", type=int, default=None)
    parser.add_argument("--wildcard_size", type=int, default=None)
    parser.add_argument("--negative_control_size", type=int, default=None)

    parser.add_argument("--skip_profile", action="store_true", help="Skip material_profile_builder.py if profile/query_profile.json already exists.")
    parser.add_argument("--skip_pools", action="store_true", help="Skip candidate_pool_builder.py if pools already exist.")
    parser.add_argument("--skip_evidence", action="store_true", help="Skip cheap_evidence_metrics.py only when every required evidence output, including reference_neighbourhood_fingerprint.json, already exists.")
    parser.add_argument("--skip_role_priors", action="store_true", help="Skip role_prior_engine.py if role priors already exist.")
    parser.add_argument("--dry_run", action="store_true", help="Print commands and write run metadata without executing commands.")
    parser.add_argument("--continue_on_error", action="store_true", help="Continue running subsequent steps if a step fails.")
    parser.add_argument(
        "--no_output_checks",
        action="store_true",
        help="Disable wrapper-level checks for expected output files after each stage.",
    )
    parser.add_argument(
        "--non_strict_output_checks",
        action="store_true",
        help="Record missing expected outputs in run_metadata.json but do not fail the pipeline.",
    )
    legacy_group = parser.add_mutually_exclusive_group()
    legacy_group.add_argument(
        "--legacy_outputs",
        dest="legacy_outputs",
        action="store_true",
        help="Ask role_prior_engine.py to write both Structural Context Profile v2 and legacy transition outputs (default).",
    )
    legacy_group.add_argument(
        "--no-legacy_outputs",
        dest="legacy_outputs",
        action="store_false",
        help="Ask role_prior_engine.py to write only Structural Context Profile v2 outputs.",
    )
    parser.set_defaults(legacy_outputs=True)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    scripts_dir = Path(args.scripts_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    profile_dir = output_dir / "profile"
    pools_dir = output_dir / "pools"
    evidence_dir = output_dir / "evidence"
    role_priors_dir = output_dir / "role_priors"

    profile_json = profile_dir / "query_profile.json"

    scripts = {
        "material_profile_builder": script_path(scripts_dir, "material_profile_builder.py"),
        "candidate_pool_builder": script_path(scripts_dir, "candidate_pool_builder.py"),
        "cheap_evidence_metrics": script_path(scripts_dir, "cheap_evidence_metrics.py"),
        "role_prior_engine": script_path(scripts_dir, "role_prior_engine.py"),
    }

    for path in scripts.values():
        ensure_script_exists(path)

    output_dir.mkdir(parents=True, exist_ok=True)

    output_checks_enabled = not bool(args.no_output_checks)
    strict_output_checks = output_checks_enabled and not bool(args.non_strict_output_checks) and not bool(args.continue_on_error)

    run_id = infer_run_id(args)
    metadata: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "source": {
            "jid": args.jid,
            "external_json": args.external_json,
            "external_id": args.external_id,
        },
        "paths": {
            "output_dir": str(output_dir),
            "profile_dir": str(profile_dir),
            "profile_json": str(profile_json),
            "pools_dir": str(pools_dir),
            "evidence_dir": str(evidence_dir),
            "reference_neighbourhood_fingerprint": str(evidence_dir / "reference_neighbourhood_fingerprint.json"),
            "role_priors_dir": str(role_priors_dir),
            "scripts_dir": str(scripts_dir),
            "scripts": {k: str(v) for k, v in scripts.items()},
        },
        "expected_outputs": {
            **EXPECTED_OUTPUTS,
            "role_prior_engine_v2": list(ROLE_PRIOR_V2_OUTPUTS),
            "role_prior_engine_legacy": list(ROLE_PRIOR_LEGACY_OUTPUTS) if args.legacy_outputs else [],
        },
        "options": {
            "force_rebuild_descriptor_cache": args.force_rebuild_descriptor_cache,
            "include_external_in_universe": args.include_external_in_universe,
            "material_store_config": args.material_store_config,
            "seed": args.seed,
            "pool_sizes": {
                "same_family_size": args.same_family_size,
                "adjacent_family_size": args.adjacent_family_size,
                "boundary_contrast_size": args.boundary_contrast_size,
                "wildcard_size": args.wildcard_size,
                "negative_control_size": args.negative_control_size,
            },
            "dry_run": args.dry_run,
            "continue_on_error": args.continue_on_error,
            "output_checks_enabled": output_checks_enabled,
            "strict_output_checks": strict_output_checks,
            "non_strict_output_checks": args.non_strict_output_checks,
            "legacy_outputs": args.legacy_outputs,
        },
        "steps": [],
        "output_checks": [],
    }

    def expected_outputs_for_step(step_name: str) -> List[str]:
        if step_name != "role_prior_engine":
            return list(EXPECTED_OUTPUTS[step_name])
        required = list(ROLE_PRIOR_V2_OUTPUTS)
        if args.legacy_outputs:
            required.extend(ROLE_PRIOR_LEGACY_OUTPUTS)
        return required

    def maybe_check(step_name: str, step_output_dir: Path) -> None:
        if not output_checks_enabled:
            return
        metadata["output_checks"].append(
            check_expected_outputs(
                step_name,
                step_output_dir,
                required_files=expected_outputs_for_step(step_name),
                dry_run=args.dry_run,
                strict=strict_output_checks,
            )
        )

    try:
        # Step 1: profile
        if args.skip_profile and profile_json.exists():
            metadata["steps"].append(append_skip_record("material_profile_builder"))
        else:
            cmd = [args.python, str(scripts["material_profile_builder"])]
            if args.jid:
                cmd += ["--jid", args.jid]
            else:
                cmd += ["--external_json", str(Path(args.external_json).expanduser())]
                if args.external_id:
                    cmd += ["--external_id", args.external_id]
                if args.include_external_in_universe:
                    cmd += ["--include_external_in_universe"]
            if args.force_rebuild_descriptor_cache:
                cmd += ["--force_rebuild_descriptor_cache"]
            cmd += ["--output_dir", str(profile_dir)]
            metadata["steps"].append(run_step("material_profile_builder", cmd, cwd=scripts_dir, dry_run=args.dry_run, continue_on_error=args.continue_on_error))
        maybe_check("material_profile_builder", profile_dir)

        # Step 2: pools
        if args.skip_pools and (pools_dir / "candidate_pool_summary.json").exists():
            metadata["steps"].append(append_skip_record("candidate_pool_builder"))
        else:
            cmd = [
                args.python,
                str(scripts["candidate_pool_builder"]),
                "--query_profile",
                str(profile_json),
                "--output_dir",
                str(pools_dir),
            ]
            if args.material_store_config:
                cmd += ["--material_store_config", str(Path(args.material_store_config).expanduser())]
            if args.force_rebuild_descriptor_cache:
                cmd += ["--force_rebuild_descriptor_cache"]
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
            metadata["steps"].append(run_step("candidate_pool_builder", cmd, cwd=scripts_dir, dry_run=args.dry_run, continue_on_error=args.continue_on_error))
        maybe_check("candidate_pool_builder", pools_dir)

        # Step 3: evidence
        # A skipped evidence stage is accepted only when the complete Phase 3
        # output contract exists. In particular, cached cases created before
        # Phase 1C.2 must be rerun when reference_neighbourhood_fingerprint.json
        # is absent.
        evidence_required = expected_outputs_for_step("cheap_evidence_metrics")
        evidence_outputs_complete = all((evidence_dir / name).is_file() for name in evidence_required)

        if args.skip_evidence and evidence_outputs_complete:
            metadata["steps"].append(append_skip_record("cheap_evidence_metrics"))
        else:
            if args.skip_evidence and not evidence_outputs_complete:
                missing = [name for name in evidence_required if not (evidence_dir / name).is_file()]
                print(
                    "\nEvidence skip requested, but required Phase 3 outputs are missing; "
                    "the evidence stage will run. Missing: " + ", ".join(missing),
                    file=sys.stderr,
                )
            cmd = [
                args.python,
                str(scripts["cheap_evidence_metrics"]),
                "--query_profile",
                str(profile_json),
                "--pool_dir",
                str(pools_dir),
                "--output_dir",
                str(evidence_dir),
            ]
            metadata["steps"].append(run_step("cheap_evidence_metrics", cmd, cwd=scripts_dir, dry_run=args.dry_run, continue_on_error=args.continue_on_error))
        maybe_check("cheap_evidence_metrics", evidence_dir)

        # Step 4: Structural Context Profile v2 / transition legacy outputs.
        # A skipped role-prior stage is accepted only when every output required
        # by the selected compatibility mode already exists.
        role_required = expected_outputs_for_step("role_prior_engine")
        role_outputs_complete = all((role_priors_dir / name).is_file() for name in role_required)
        if args.skip_role_priors and role_outputs_complete:
            metadata["steps"].append(append_skip_record("role_prior_engine"))
        else:
            if args.skip_role_priors and not role_outputs_complete:
                missing = [name for name in role_required if not (role_priors_dir / name).is_file()]
                print(
                    "\nRole-prior skip requested, but required v2/compatibility outputs are missing; "
                    "the role-prior stage will run. Missing: " + ", ".join(missing),
                    file=sys.stderr,
                )
            cmd = [
                args.python,
                str(scripts["role_prior_engine"]),
                "--query_profile",
                str(profile_json),
                "--evidence_dir",
                str(evidence_dir),
                "--output_dir",
                str(role_priors_dir),
                "--legacy_outputs" if args.legacy_outputs else "--no-legacy_outputs",
            ]
            metadata["steps"].append(run_step("role_prior_engine", cmd, cwd=scripts_dir, dry_run=args.dry_run, continue_on_error=args.continue_on_error))
        maybe_check("role_prior_engine", role_priors_dir)

        step_success = all(s.get("returncode", 1) == 0 for s in metadata["steps"])
        outputs_complete = all(c.get("status") in {"complete", "dry_run_not_checked"} for c in metadata.get("output_checks", []))
        metadata["finished_at_utc"] = utc_now()
        if step_success and outputs_complete:
            metadata["status"] = "success"
        elif step_success and not outputs_complete:
            metadata["status"] = "completed_with_missing_outputs"
        else:
            metadata["status"] = "completed_with_failures"

    except Exception as exc:
        metadata["finished_at_utc"] = utc_now()
        metadata["status"] = "failed"
        metadata["error"] = repr(exc)
        write_json(output_dir / "run_metadata.json", metadata)
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    write_json(output_dir / "run_metadata.json", metadata)

    print("\n=== Pipeline complete ===")
    print(f"Status:       {metadata['status']}")
    print(f"Run metadata: {output_dir / 'run_metadata.json'}")
    print(f"Profile:      {profile_json}")
    print(f"Pools:        {pools_dir}")
    print(f"Evidence:     {evidence_dir}")
    print(f"Reference fingerprint: {evidence_dir / 'reference_neighbourhood_fingerprint.json'}")
    print(f"Structural context: {role_priors_dir}")
    print(f"Legacy outputs:     {'enabled' if args.legacy_outputs else 'disabled'}")

    if metadata.get("output_checks"):
        missing = [
            f"{c.get('step')}: {', '.join(c.get('missing_files', []))}"
            for c in metadata["output_checks"]
            if c.get("missing_files")
        ]
        if missing:
            print("\nMissing expected outputs:")
            for item in missing:
                print(f"  - {item}")

    return 0 if metadata["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
