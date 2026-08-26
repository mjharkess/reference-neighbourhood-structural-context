# REPRODUCIBILITY.md

## Reference-Neighbourhood Structural Context Framework

**Version:** v0.1 Draft\
**Document role:** Environment, data reconstruction, execution,
and output-reproduction guide\
**Reference-data policy:** Rebuild from JARVIS on first execution\
**Reference implementation environment:** macOS, Python 3.13.12\
**Implementation basis:** 8 August 2026 frozen source-code bundle
and successful 9 August 2026 JARVIS/external example runs

# 1. Purpose

This document describes how to reconstruct the software environment
and reference-data state required to execute the
v0.1 Reference-Neighbourhood Structural Context Framework and
reproduce representative per-material and cohort-level outputs.

The purpose of this document is operational rather than evidential.

-   `METHODOLOGY.md` defines the scientific method.

-   `ARCHITECTURE.md` defines the software components and
    data contracts.

-   `VALIDATION.md` records the verification evidence.

-   `CLAIMS.md` defines the scientific claim boundary.

-   `EXTERNAL_INPUT.md` defines preparation and use of
    externally supplied materials.

-   `REPRODUCIBILITY.md` explains how another user can reconstruct
    and execute the released system.

A successful reproduction demonstrates that the documented
software/data procedure can be reconstructed and executed. It does not,
by itself, strengthen the scientific claims in `CLAIMS.md`.

# 2. Reproducibility Definition for v0.1

For v0.1, a reproduction is considered successful when a
clean installation using the documented source code, Python
environment, JARVIS reference data, configuration, and inputs can:

1.  construct or load the required JARVIS reference datasets;

2.  construct the descriptor cache;

3.  execute the per-material pipeline without failed cases for
    the selected reproduction input;

4.  produce the required Material Profile, candidate-pool,
    evidence, RNF, and Structural Context Profile artefacts;

5.  aggregate a batch into `structural_context_batch_summary.csv`;

6.  execute Candidate Context Analysis against the completed batch; and

7.  reproduce the expected qualitative analytical organisation,
    with exact equality required only where the implementation
    and verification define deterministic equality.

The RNF is reference-relative. Reproducibility therefore depends
not only on the source code but also on the reference corpus,
descriptor state, configuration, and schema versions.

# 3. Reference v0.1 Environment

The v0.1 development and reproduction environment supplied for
this release used:

    Python 3.13.12

The recorded package environment was:

    bibtexparser==1.4.4  
    certifi==2026.2.25  
    charset-normalizer==3.4.7  
    contourpy==1.3.3  
    cycler==0.12.1  
    et_xmlfile==2.0.0  
    faiss-cpu==1.13.2  
    fonttools==4.62.1  
    hdbscan==0.8.42  
    idna==3.11  
    jarvis-tools==2026.3.10  
    joblib==1.5.3  
    kiwisolver==1.5.0  
    llvmlite==0.47.0  
    matplotlib==3.10.8  
    monty==2026.2.18  
    mpmath==1.3.0  
    narwhals==2.18.1  
    networkx==3.6.1  
    numba==0.65.0  
    numpy==2.4.4  
    openpyxl==3.1.5  
    orjson==3.11.8  
    packaging==26.0  
    pacmap==0.9.1  
    palettable==3.3.3  
    pandas==3.0.2  
    pillow==12.2.0  
    plotly==6.6.0  
    pyarrow==23.0.1  
    pymatgen==2026.3.23  
    pymatgen-core==2026.3.9  
    pynndescent==0.6.0  
    pyparsing==3.3.2  
    python-dateutil==2.9.0.post0  
    requests==2.33.1  
    ruamel.yaml==0.19.1  
    scikit-learn==1.8.0  
    scipy==1.17.1  
    six==1.17.0  
    spglib==2.7.0  
    sympy==1.14.0  
    tabulate==0.10.0  
    threadpoolctl==3.6.0  
    toolz==1.1.0  
    tqdm==4.67.3  
    umap-learn==0.5.11  
    uncertainties==3.2.3  
    urllib3==2.6.3  
    xlsxwriter==3.2.9  
    xmltodict==1.0.4

This list is the complete `pip freeze` snapshot supplied from
the working v0.1 environment. It should be retained as an
environment record.

It should not automatically be interpreted as a minimal dependency
list. Some packages may be transitive dependencies or unrelated
packages present in the development environment. A future
`requirements.txt` may therefore be smaller, but any reduced dependency
specification should be tested from a clean environment before replacing
this snapshot as the reference reproduction environment.

# 4. Recommended Clean Environment Setup

A clean virtual environment is recommended.

Example:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

For exact reconstruction of the supplied Python package
environment, save the package list in Section 3 as a release environment
file such as:

    requirements-freeze-v0.1.txt

and install it with:

```bash
python -m pip install -r requirements-freeze-v0.1.txt
```

Confirm the interpreter:

```bash
python3 --version
```

Expected reference result:

    Python 3.13.12

The supplied evidence establishes macOS as the reference
development platform. Equivalent behaviour on other operating systems
has not yet been established by the current verification set.

# 5. Source-Code State

The reproduction procedure should use the frozen v0.1 source
set corresponding to the documented release.

The supplied 8 August 2026 freeze contains the principal modules:

    material_store.py  
    material_profile_builder.py  
    material_family_classifier.py  
    candidate_pool_builder.py  
    cheap_evidence_metrics.py  
    role_prior_engine.py  
    run_context_pipeline.py  
    batch_role_prior_runner_structural_context_v2.py  
    candidate_context_analysis_reference_neighbourhood.py  
    physical_plausibility.py  
    tools/lrt_phase3_utils.py  
      
    external_material_ingestion.py  
    external_descriptor_builder.py  
    external_material_validator.py  
    external_material_schema.py  
    phase5_external_material_prepare.py

A reproduction should record the repository release/tag or commit
used. Local source changes made after the release should not be
described as reproduction of v0.1 without explicitly documenting the
modification.

# 6. Reference Data Policy

## 6.1 Canonical Policy

The v0.1 reproducibility policy is:

> **Rebuild the reference datastore from JARVIS on first execution.**

Generated JARVIS raw-data caches and the material descriptor cache
are not required to be distributed as canonical repository inputs.

This policy tests reconstructability from the documented
upstream data-access path rather than requiring users to receive a
private copy of the developer's generated cache.

## 6.2 JARVIS Datasets Used by the Frozen Material Store

The frozen `material_store.py` obtains the following datasets
through `jarvis-tools`:

    dft_3d  
    dft_2d

The code writes local raw-data caches beneath the configured
data directory:

    datasets/jarvis_dft_3d_raw.json  
    datasets/jarvis_dft_2d_raw.json

The first clean execution may therefore require network access
while `jarvis-tools` obtains the upstream datasets.

Later runs can reuse the local raw-data files.

## 6.3 Descriptor Cache

The frozen Material Store constructs or loads:

    datasets/material_descriptor_cache.json

The supplied source records:

    descriptor cache version: 6  
    schema: phase3.descriptor_cache.v1

The descriptor cache is derived state and should be reproducible
from the JARVIS data and frozen source/configuration.

For a strict clean reproduction, begin without an existing
descriptor cache and allow the framework to construct it.

## 6.4 Important Reference-Data Qualification

The source records the JARVIS dataset names and the
`jarvis-tools` package version used in the supplied environment, but the
supplied material-store code does not embed an independent immutable
snapshot identifier for the upstream JARVIS dataset contents.

Consequently, a future upstream change to data returned under
`dft_3d` or `dft_2d` could affect exact reproduction even when the
framework source is unchanged.

For v0.1, users should therefore record at minimum:

-   `jarvis-tools` version;

-   date of reference-data retrieval;

-   generated raw-data cache files;

-   descriptor-cache manifest/version;

-   repository release/commit.

This limitation should be considered when interpreting exact
cross-time reproducibility.

# 7. Expected Schema Versions

The frozen implementation records explicit versions for major
persisted contracts.

The architecture/source review identifies the following v0.1 contracts:

    Material Profile:  
    phase1.material_profile.v1.2  
      
    Candidate Pools:  
    phase2.candidate_pools.v1.1  
      
    Evidence:  
    phase3.structural_context_evidence.v2_pool_context_summary  
      
    Reference-Neighbourhood Fingerprint:  
    phase3.reference_neighbourhood_fingerprint.v1  
      
    Structural Context Profile v2:  
    phase1.structural_context_profile.v2  
      
    Role inference:  
    phase4_5.structural_context_inference.v4.0_transition  
      
    Candidate Context Analysis:  
    candidate_context_analysis.phase1c2.reference_neighbourhood.v1

Candidate Context Analysis checks discovered RNFs for supported
schema compatibility.

Schema mismatches should be treated as a
reproduction/configuration problem rather than silently ignored.

# 8. Canonical Output Structure

A completed per-material run is expected to contain
stage-separated outputs:

    \<MATERIAL_ID\>/  
    ├── profile/  
    ├── pools/  
    ├── evidence/  
    ├── role_priors/  
    └── run_metadata.json

Important products include:

    profile/query_profile.json  
      
    pools/same_family_pool.csv  
    pools/adjacent_family_pool.csv  
    pools/boundary_contrast_pool.csv  
    pools/wildcard_pool.csv  
    pools/negative_control_pool.csv  
    pools/candidate_pool_summary.json  
    pools/pool_config_used.json  
      
    evidence/cheap_evidence_summary.json  
    evidence/reference_neighbourhood_fingerprint.json  
      
    role_priors/structural_context_profile_v2.json  
    role_priors/structural_context_profile_v2_summary.csv  
    role_priors/structural_context_profile_v2_reliability.csv

A completed batch is expected to produce batch-level
artefacts including:

    batch_manifest.json  
    batch_runtime_log.csv  
    batch_summary.csv  
    structural_context_batch_summary.csv  
    failed_cases.csv

A successful batch should record failed cases explicitly. In
the supplied canonical JARVIS and external example runs, `failed_count`
was zero.

# 9. Reproduction Exercise R1 --- JARVIS Batch

## 9.1 Purpose

R1 demonstrates reconstruction and execution of the standard
JARVIS-ID pathway.

The supplied known-good example batch contained 10 JARVIS materials
and completed successfully.

The recorded batch manifest reports:

    input_count:       10  
    completed_count:   10  
    success_count:     10  
    failed_count:      0  
    seed:              87  
    status:            success

The example run used default pool sizes and reused existing
stage/cache outputs where available.

## 9.2 Input File

The batch runner accepts a CSV or text file through:

    --input_ids

Recognised identifier columns include:

    jid  
    jarvis_id  
    material_id

A minimal example is:

    jid  
    JVASP-119589  
    JVASP-122407  
    JVASP-143116

For reproduction of the complete supplied example batch, use the same
10 JARVIS identifiers recorded in the release reproduction input file.

## 9.3 Portable Command

From the repository/source directory, a portable form is:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --input_ids ./examples/reproducibility/jarvis_ids.csv \
  --project_dir . \
  --output_dir ./reproduction_outputs/jarvis_batch \
  --seed 87
```

If an already constructed compatible datastore/cache is
intentionally being reused, the runner supports:

    --reuse_cache

For a strict first clean reconstruction, do not depend on a
pre-existing developer cache.

## 9.4 Successful Completion Checks

Confirm:

1.  the command exits successfully;

2.  `batch_manifest.json` records successful completion;

3.  `failed_cases.csv` contains no failed material records;

4.  each material directory contains a Material Profile;

5.  each material directory
    contains `reference_neighbourhood_fingerprint.json`;

6.  each material directory
    contains `structural_context_profile_v2.json`; and

7.  `structural_context_batch_summary.csv` is produced.

The supplied 10-material reference run completed all 10 cases with
no failures.

# 10. Reproduction Exercise R2 --- Candidate Context Analysis

## 10.1 Purpose

R2 demonstrates that completed per-material RNFs and Structural
Context Profiles can be consumed by the separate cohort-level Candidate
Context Analysis subsystem.

## 10.2 Portable Command

After R1 completes:

```bash
python3 candidate_context_analysis_reference_neighbourhood.py \
  --structural_context_summary ./reproduction_outputs/jarvis_batch/structural_context_batch_summary.csv \
  --batch_output_root ./reproduction_outputs/jarvis_batch \
  --output_dir ./reproduction_outputs/jarvis_batch/candidate_context_analysis \
  --top_k 5 \
  --seed 87
```

The exact CCA seed used for a published canonical reproduction should
be retained with the reproduction input/configuration. The supplied
JARVIS batch manifest establishes seed 87 for the batch stage.

## 10.3 Expected Product Classes

CCA should produce machine-readable cohort outputs covering areas
such as:

-   fingerprint discovery/inventory;

-   pairwise similarity;

-   Combined Context Similarity;

-   RNF similarity;

-   profile similarity;

-   chemistry-baseline similarity;

-   nearest contextual neighbours;

-   contextual clustering;

-   cluster summaries/representatives;

-   distinctiveness;

-   redundancy;

-   inter-cluster analysis;

-   profile/RNF discordance;

-   pairwise explainability;

-   coverage;

-   report and visualisations.

Exact filenames are defined by the frozen CCA implementation and
should be checked against the release output set.

# 11. Reproduction Exercise R3 --- External Materials

## 11.1 Purpose

R3 demonstrates that externally supplied structures can enter the same
analytical framework without requiring JARVIS identifiers.

The v0.1 reproduction set contains three supplied POSCAR structures:

```text
examples/reproducibility/POSCAR_JVASP-28634
examples/reproducibility/POSCAR_JVASP-86726
examples/reproducibility/POSCAR_JVASP-98550
```

The detailed external-input contract is defined in
`docs/EXTERNAL_INPUT.md` and `schemas/external_material.schema.json`.

## 11.2 Preparing the Supplied External Structures

Prepare each supplied POSCAR from the repository root:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure ./examples/reproducibility/POSCAR_JVASP-28634 \
  --external_format poscar \
  --external_id EXT-JVASP-28634-TEST \
  --output_dir ./external_prepared/EXT-JVASP-28634-TEST

python3 phase5_external_material_prepare.py \
  --external_structure ./examples/reproducibility/POSCAR_JVASP-86726 \
  --external_format poscar \
  --external_id EXT-JVASP-86726-TEST \
  --output_dir ./external_prepared/EXT-JVASP-86726-TEST

python3 phase5_external_material_prepare.py \
  --external_structure ./examples/reproducibility/POSCAR_JVASP-98550 \
  --external_format poscar \
  --external_id EXT-JVASP-98550-TEST \
  --output_dir ./external_prepared/EXT-JVASP-98550-TEST
```

These commands generate:

```text
external_prepared/EXT-JVASP-28634-TEST/external_descriptor_record.json
external_prepared/EXT-JVASP-86726-TEST/external_descriptor_record.json
external_prepared/EXT-JVASP-98550-TEST/external_descriptor_record.json
```

The generated records should satisfy the published external-material
schema before use. `external_prepared/` is generated state and need not
be committed.

## 11.3 External Batch Input

Use `examples/reproducibility/external_test.csv`. It should point to the
three generated records above.

The supplied successful external test recorded:

```text
input_count:       3
completed_count:   3
success_count:     3
failed_count:      0
seed:              4881
status:            success
```

## 11.4 External Batch Command

After all three preparation commands complete:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --external_json_list ./examples/reproducibility/external_test.csv \
  --project_dir . \
  --output_dir ./reproduction_outputs/external_batch \
  --seed 4881
```

The original successful development run used machine-specific absolute
paths. Those paths record the development environment; the command above
is the portable v0.1 reproduction command.

## 11.5 External Candidate Context Analysis

After the external batch completes:

```bash
python3 candidate_context_analysis_reference_neighbourhood.py \
  --structural_context_summary ./reproduction_outputs/external_batch/structural_context_batch_summary.csv \
  --batch_output_root ./reproduction_outputs/external_batch \
  --output_dir ./reproduction_outputs/external_batch/candidate_context_analysis \
  --top_k 5 \
  --seed 4881
```

The supplied reference run generated CCA outputs successfully for all
three external candidates.

## 11.6 Successful Completion Checks

Confirm that:

1.  all three POSCAR structures are converted to prepared external
    descriptor records;
2.  the generated records satisfy the external-material validation
    requirements;
3.  `external_test.csv` resolves to those generated records;
4.  the external batch exits successfully;
5.  `failed_cases.csv` contains no failed material records;
6.  `structural_context_batch_summary.csv` is produced; and
7.  Candidate Context Analysis completes against the three-material
    external cohort.

# 12. Exact Equality Versus Analytical Equivalence

Not every reproduction criterion should be reduced to byte-for-byte
file equality.

## 12.1 Deterministic Repeatability

RV-01 in `VALIDATION.md` records identical outputs when the
tested execution was repeated under identical conditions.

Where the complete software, data, cache, configuration, and
execution environment are fixed, exact equality is therefore an
appropriate target for deterministic outputs.

## 12.2 Seed Robustness

RV-02 records that changing the seed across the tested values did
not materially change contextual organisation.

One test recorded minor numerical variation of approximately 0.001
or less while candidate ordering, clusters, interpretation, and
scientific conclusion remained unchanged.

Another test recorded identical contextual partition and membership
with cluster-number permutation only.

Accordingly:

-   cluster numeric labels should not be treated as ordered
    scientific quantities;

-   equivalent cluster membership with permuted labels is
    analytically equivalent;

-   small documented numerical variation may be acceptable where it
    does not change the tested analytical conclusion.

## 12.3 Cross-Time Reference Reconstruction

Because the JARVIS data are rebuilt from upstream dataset names
rather than an independently embedded immutable dataset snapshot,
exact numerical equality across widely separated retrieval dates cannot
be guaranteed by the supplied v0.1 evidence.

Where exact equality fails after a later upstream retrieval,
first compare:

1.  `jarvis-tools` version;

2.  raw JARVIS cache contents;

3.  descriptor-cache manifest/version;

4.  repository release/commit;

5.  input files;

6.  configuration;

7.  schema versions.

# 13. Recommended Reproduction Record

A third party reproducing a published result should record:

    Framework release/tag:  
    Repository commit:  
    Operating system:  
    Python version:  
    pip environment / lock file:  
    jarvis-tools version:  
    JARVIS retrieval date:  
    Raw dft_3d cache identifier/checksum:  
    Raw dft_2d cache identifier/checksum:  
    Descriptor-cache version:  
    Descriptor-cache checksum:  
    Input file:  
    Seed:  
    Pool-size overrides:  
    Reuse-cache setting:  
    CCA top_k:  
    CCA configuration:  
    Start/end time:  
    Failed cases:  
    Output location:  
    Result:

Checksums are recommended for persisted raw-data and
descriptor-cache files when an exact reproduction record is required.

# 14. Troubleshooting Reproduction Failures

## 14.1 Missing JARVIS Data

On a clean first run, ensure that the environment can access
the upstream data source used by `jarvis-tools`.

The frozen Material Store will attempt to obtain:

    dft_3d  
    dft_2d

and then write local raw-data caches.

## 14.2 Descriptor Cache Problems

If the descriptor cache is absent, the framework should construct it.

If a cache is suspected to be stale or incompatible, use the
framework's force-rebuild capability rather than manually editing the
generated cache.

The batch runner records a `force_rebuild_descriptor_cache` option
in its manifest.

## 14.3 Missing Batch Summary

CCA requires:

    structural_context_batch_summary.csv

as well as access to the batch output root containing the
completed material directories and RNFs.

Do not invoke CCA against a partially completed batch that has
not generated this summary.

## 14.4 Missing RNFs

CCA discovers RNF files beneath the supplied batch output root.

Confirm that completed materials contain:

    evidence/reference_neighbourhood_fingerprint.json

and that the RNF schema is supported by the CCA version being used.

## 14.5 External Input Failure

For external materials:

1.  validate the source structure;

2.  run the preparation workflow;

3.  confirm the generated JSON
    satisfies `external_material.schema.json`;

4.  confirm `external_test.csv` or equivalent points to the
    generated JSON files;

5.  run the external batch;

6.  inspect `failed_cases.csv` and per-material outputs before
    running CCA.

Refer to `EXTERNAL_INPUT.md` for the detailed external-record
contract and validation rules.

## 14.6 Path Problems

The supplied development commands contain absolute macOS paths.

Published reproduction commands should use repository-relative
or user-selected paths.

The framework should not require another user to reproduce:

    /Users/filepath/Documents/Project/Python/

That path records the original execution environment; it is not part
of the scientific method.

# 15. Clean-Reproduction Procedure Before Release

Before tagging v0.1, the recommended release check is:

1.  create a clean directory or clean repository clone;

2.  create a new Python 3.13.12 virtual environment;

3.  install the frozen environment;

4.  confirm no pre-existing `datasets/` cache is being reused;

5.  allow the framework to retrieve JARVIS `dft_3d` and `dft_2d`;

6.  allow it to build descriptor cache version 6;

7.  run the canonical JARVIS reproduction batch;

8.  confirm zero failed cases;

9.  run CCA;

10. run the canonical external-material preparation/batch/CCA path;

11. confirm zero failed external cases;

12. compare the new outputs with the retained reference outputs
    using the criteria in Section 12;

13. record any platform, dependency, numerical, or
    upstream-data differences;

14. only then tag the release and freeze the reproduction documentation.

This clean-run check is important because a workflow that succeeds
only in a long-lived development directory may be relying on
unrecorded caches, files, or configuration.

# 16. Recommended Release Reproducibility Files

The repository should ideally include or generate the
following reproducibility support files:

    REPRODUCIBILITY.md  
    requirements-freeze-v0.1.txt  
      
    examples/  
    └── reproducibility/  
        ├── jarvis_ids.csv  
        ├── external_test.csv  
        ├── external/  
        │   ├── POSCAR or CIF example  
        │   └── prepared external JSON examples  
        └── README.md

The repository does not need to contain the generated JARVIS raw
caches or descriptor cache under the selected v0.1 policy.

For stronger archival reproducibility, release metadata may
additionally record checksums of the raw caches generated during the
final clean reproduction.

# 17. Known Reproducibility Limitations

The current v0.1 evidence has several limitations.

## 17.1 Reference Dataset Mutability

The framework reconstructs the reference corpus from named
upstream JARVIS datasets. The supplied code does not independently pin
those dataset contents to an immutable upstream snapshot identifier.

This is the principal limitation on exact long-term reconstruction.

## 17.2 Reference Platform

The supplied reference environment is macOS with Python 3.13.12.

Cross-platform equivalence has not yet been formally verified.

## 17.3 Complete Environment Versus Minimal Requirements

The supplied `pip freeze` is a complete
development-environment snapshot, not a proven minimal dependency
specification.

## 17.4 Numerical Libraries

Scientific Python libraries can exhibit small numerical
differences across platforms, binary builds, or library versions. The
current verification establishes the tested environment, not universal
bitwise equivalence.

## 17.5 Cohort Dependence

CCA outputs are cohort-relative. Adding or removing candidates
can legitimately alter cohort-level organisation,
clustering, distinctiveness, and redundancy.

A reproduction of a CCA result must therefore use the same
candidate cohort.

## 17.6 Configuration Dependence

RNF and CCA outputs depend on the documented configuration. A
changed pool size, weight, threshold, schema, seed, reference corpus,
or candidate cohort may constitute a new experiment rather than a
failed reproduction.

# 18. Reproducibility Versus Validation

Reproducibility and validation should remain separate.

A successful reproduction establishes that the implementation
and documented data procedure can be reconstructed.

It does not establish:

-   that RNF is superior to conventional descriptors;

-   that H4 is supported;

-   that CCA clusters are physically fundamental classes;

-   that downstream materials discovery improves;

-   that current weights are optimal; or

-   that the method generalises across materials space.

Those questions remain governed by `VALIDATION.md` and `CLAIMS.md`.

Conversely, a scientifically interesting result that cannot
be reconstructed from the documented release is a reproducibility
problem even if the underlying idea remains valid.

# 19. v0.1 Reproducibility Position

The v0.1 framework has a documented path for reconstructing:

-   the Python execution environment;

-   the JARVIS `dft_3d` and `dft_2d` reference data;

-   the local raw-data caches;

-   descriptor cache version 6;

-   per-material Material Profiles;

-   deterministic candidate pools;

-   evidence and RNFs;

-   Structural Context Profiles;

-   batch summaries;

-   Candidate Context Analysis;

-   and external-material execution from prepared external records.

The canonical reference-data policy is to rebuild from JARVIS on
first execution rather than distribute the developer's generated
datastore as a required input.

The strongest remaining limitation is that the upstream JARVIS
dataset contents are identified by dataset name and package/environment
state rather than by an independently pinned immutable dataset snapshot
in the supplied source. For that reason, the final v0.1 clean
reproduction should retain retrieval date and checksums for the
generated raw-data caches and descriptor cache.

Subject to that qualification, the architecture and supplied
example runs provide a complete operational route from clean environment
to RNF and CCA outputs for both JARVIS and external materials.

# 20. Summary

To reproduce v0.1:

    Clean Python 3.13.12 environment  
                │  
                ▼  
    Install frozen package environment  
                │  
                ▼  
    Use frozen v0.1 source  
                │  
                ▼  
    Retrieve JARVIS dft_3d + dft_2d  
                │  
                ▼  
    Build descriptor cache v6  
                │  
                ▼  
    Run JARVIS or external-material batch  
                │  
                ▼  
    Verify per-material RNF + SCP outputs  
                │  
                ▼  
    Verify structural_context_batch_summary.csv  
                │  
                ▼  
    Run Candidate Context Analysis  
                │  
                ▼  
    Compare outputs using documented  
    reproduction/equivalence criteria

This procedure defines the operational reproducibility boundary for
the planned v0.1 release.
