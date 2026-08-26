# v0.1 Reproduction Examples

This directory contains the fixed example inputs used with the v0.1
reproduction procedure.

For the complete setup and reproduction procedure, see
[`../../docs/REPRODUCIBILITY.md`](../../docs/REPRODUCIBILITY.md).

## JARVIS reproduction cohort

`jarvis_ids.csv` contains the supplied 10-material JARVIS cohort used
for the v0.1 reference reproduction:

```text
JVASP-119589
JVASP-122407
JVASP-143116
JVASP-143566
JVASP-145157
JVASP-140218
JVASP-119423
JVASP-144808
JVASP-142153
JVASP-118994
```

From the repository root:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --input_ids ./examples/reproducibility/jarvis_ids.csv \
  --project_dir . \
  --output_dir ./outputs/jarvis_batch \
  --seed 87
```

Then run Candidate Context Analysis:

```bash
python3 candidate_context_analysis_reference_neighbourhood.py \
  --structural_context_summary ./outputs/jarvis_batch/structural_context_batch_summary.csv \
  --batch_output_root ./outputs/jarvis_batch \
  --output_dir ./outputs/jarvis_batch/candidate_context_analysis \
  --top_k 5 \
  --seed 87
```

## External-material examples

The reproduction directory contains three supplied source structures:

```text
POSCAR_JVASP-28634
POSCAR_JVASP-86726
POSCAR_JVASP-98550
```

Prepare each structure before running the external batch. For example:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure ./examples/reproducibility/POSCAR_JVASP-86726 \
  --external_format poscar \
  --external_id EXT-JVASP-86726-TEST \
  --output_dir ./external_prepared/EXT-JVASP-86726-TEST
```

Use the same pattern, including `--external_format poscar`, for the
other two POSCARs. The explicit format is required for these supplied
filenames because names such as `POSCAR_JVASP-86726` do not have a
recognized POSCAR/VASP suffix and are not named exactly `POSCAR`.
Prepared descriptor records are generated beneath `external_prepared/`
and should not be committed.

## External batch list

`external_test.csv` is intended to point to the generated external
descriptor records. Before running the batch, confirm that its paths
correspond to the preparation outputs, for example:

```text
external_prepared/EXT-JVASP-86726-TEST/external_descriptor_record.json
external_prepared/EXT-JVASP-28634-TEST/external_descriptor_record.json
external_prepared/EXT-JVASP-98550-TEST/external_descriptor_record.json
```

Then run:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --external_json_list ./examples/reproducibility/external_test.csv \
  --project_dir . \
  --output_dir ./outputs/external_batch \
  --seed 4881
```

Candidate Context Analysis can then be run against the resulting
external batch as described in the main README and `REPRODUCIBILITY.md`.

## Purpose of these files

These are fixed, inspectable inputs for checking that the published v0.1
repository can execute its documented workflows in a clean environment.
They are reproduction fixtures, not evidence that the selected materials
are representative of materials space or sufficient to establish the
broader scientific hypotheses.

Generated JARVIS reference data, descriptor caches, prepared external
records, and analysis outputs should remain outside version control as
specified by `.gitignore`.
