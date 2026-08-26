# ARCHITECTURE.md

## Reference-Neighbourhood Structural Context Framework

**Version:** v0.1 Draft\
**Document role:** Software architecture, component
responsibilities, data flow, persisted contracts, provenance, and
extension boundaries

# 1. Purpose and Architectural Scope

The Reference-Neighbourhood Structural Context Framework is a
modular materials-analysis system for constructing inexpensive,
explainable, reference-relative structural context for crystalline
materials.

The architecture supports two principal analytical products:

1.  a **Reference-Neighbourhood Fingerprint (RNF)** for an
    individual material; and

2.  **Candidate Context Analysis (CCA)** for comparing and organising
    a cohort of materials using RNF information together with a
    compact Structural Context Profile (SCP).

The framework does not attempt to predict material properties
directly. Instead, it constructs structured context from inexpensive
descriptors, controlled reference retrieval, and explicit intermediate
evidence. More expensive calculations, learned representations, property
models, or generative systems are treated as potential downstream
consumers rather than prerequisites.

The architecture deliberately separates:

-   material ingestion and shared data access;

-   query-centred material profiling;

-   deterministic reference-neighbourhood construction;

-   evidence and RNF generation;

-   Structural Context Profile generation and auxiliary
    role interpretation;

-   batch orchestration and aggregation;

-   cross-candidate comparison;

-   reliability, provenance, and explainability;

-   human-facing reporting.

Each major stage has a defined responsibility and communicates
through persisted data contracts or explicit command-line interfaces
rather than requiring the scientific algorithms to be tightly coupled.

This document describes **how the software is organised**.
The scientific hypotheses and interpretation of the outputs are defined
in `METHODOLOGY.md`; validation evidence belongs in `VALIDATION.md`;
and the claims justified by that evidence belong in `CLAIMS.md`.

# 2. Architectural Identity and Design Principles

## 2.1 Cheap Context First

The framework follows a **Cheap Context First** design philosophy.

The system attempts to construct useful structural context
before resorting to expensive calculations or machine-learning models.
This leads directly to several architectural choices:

-   use inexpensive descriptors and cached data where possible;

-   preserve deterministic and reproducible execution;

-   retain intermediate evidence rather than collapsing immediately to
    a categorical decision;

-   separate representation generation from interpretation;

-   preserve explainability at material, pairwise, and cohort levels;

-   expose machine-readable outputs suitable for later
    downstream systems.

## 2.2 Representation Before Interpretation

The architecture treats the RNF as a first-class
persisted representation rather than merely an intermediate artefact on
the way to Hub/Boundary/Other classification.

The principal per-material flow is therefore:

    Material  
       │  
       ▼  
    Material Profile  
       │  
       ▼  
    Reference Candidate Pools  
       │  
       ▼  
    Evidence Generation  
       │  
       ├──────────────► Reference-Neighbourhood Fingerprint (RNF)  
       │  
       └──────────────► Evidence Summary  
                             │  
                             ▼  
                      Role Prior Engine  
                             │  
                             ├── Structural Context Profile (SCP)  
                             └── Auxiliary role-prior interpretation

The RNF exists independently as a persisted output of the
evidence stage. The role-prior stage does not create the RNF.

## 2.3 Evidence Before Decision

Evidence generation is separated from interpretation and
role assignment.

`cheap\_evidence\_metrics.py` constructs evidence, pool-level
summaries, contextual features, explainability information, and the
RNF. `role\_prior\_engine.py` consumes upstream information to generate
the SCP and auxiliary role-prior outputs.

This separation allows the evidence and RNF to be inspected,
compared, or reused without requiring acceptance of the role-prior
interpretation layer.

## 2.4 Reference-Relative Analysis

The framework distinguishes between:

-   information intrinsic or directly attached to the query
    material; and

-   information derived from the query's relationship to a
    configured reference corpus.

The RNF is therefore reference-relative and must retain
sufficient provenance to identify the corpus, upstream schemas, and
retrieval conditions under which it was generated.

## 2.5 Explicit Data Contracts

The system uses persisted JSON, CSV, and Markdown artefacts
as interfaces between major stages.

This has several benefits:

-   stages can be inspected independently;

-   outputs can be reused without rerunning every preceding stage;

-   failures can be isolated;

-   schema versions can be recorded;

-   cohort analysis can discover completed per-material outputs;

-   downstream tools can consume machine-readable products
    without importing the scientific modules directly.

# 3. Architectural Requirements Derived from the Methodology

The scientific methodology implies the following software requirements.

The system must:

1.  generate a reproducible per-material RNF under fixed
    analytical conditions;

2.  distinguish the broad Material Profile from the compact SCP and
    from the RNF;

3.  retain the reference corpus and retrieval configuration as part
    of representation provenance;

4.  construct reference pools reproducibly;

5.  persist RNF information independently of auxiliary
    role classification;

6.  retain SCP and RNF contributions separately during
    pairwise analysis;

7.  support pairwise decomposition into profile,
    reference-identity, reference-distribution, and
    reference-context-feature contributions;

8.  support cohort-level analysis including nearest
    neighbours, clustering, distinctiveness, redundancy, inter-cluster
    analysis, and explainability;

9.  expose reliability and evidence-completeness information rather
    than silently treating incomplete cases as equivalent to complete
    cases;

10. support both JARVIS materials and externally supplied
    material records;

11. permit batch execution with failure isolation and reuse of
    completed stage outputs;

12. preserve machine-readable provenance sufficient to reproduce
    or audit an analysis;

13. keep auxiliary Hub/Boundary/Other interpretation separate from
    the core RNF representation;

14. permit later comparison against conventional descriptor
    baselines without redesigning the per-material pipeline.

The formal H1-H4 research hypotheses are intentionally not
duplicated here. They are maintained in `METHODOLOGY.md` so that
scientific claims do not drift independently across architecture
documentation.

# 4. System Context

At the highest level, the framework accepts material
inputs, contextualises them against a reference corpus, persists
per-material representations, and optionally performs cohort analysis.

                            ┌───────────────────────┐  
                            │   Material Inputs     │  
                            │                       │  
                            │  • JARVIS identifier  │  
                            │  • external material  │  
                            └───────────┬───────────┘  
                                        │  
                                        ▼  
                             ┌─────────────────────┐  
                             │   Material Store    │  
                             │ reference data +    │  
                             │ cached descriptors  │  
                             └──────────┬──────────┘  
                                        │  
                                        ▼  
                             ┌─────────────────────┐  
                             │ Per-Material        │  
                             │ Context Pipeline    │  
                             └──────────┬──────────┘  
                                        │  
                        ┌───────────────┴────────────────┐  
                        ▼                                ▼  
               ┌───────────────────┐           ┌───────────────────┐  
               │ RNF               │           │ SCP + auxiliary   │  
               │ primary relational│           │ role-prior output │  
               │ representation    │           └─────────┬─────────┘  
               └─────────┬─────────┘                     │  
                         └──────────────┬────────────────┘  
                                        ▼  
                             ┌─────────────────────┐  
                             │ Candidate Context   │  
                             │ Analysis            │  
                             └──────────┬──────────┘  
                                        │  
                                        ▼  
                             Similarity / clusters /  
                             distinctiveness /  
                             redundancy /  
                             explainability

Candidate Context Analysis is not merely the final stage of
a single-material pipeline. It is a separate cohort-level consumer
of outputs produced for multiple materials.

# 5. Three-Level Execution Architecture

The current implementation is best understood as three execution layers.

## 5.1 Level A: Per-Material Pipeline

`run\_context\_pipeline.py` orchestrates the processing of one
query material.

The frozen implementation invokes specialist scripts as
subprocesses rather than importing and refactoring their scientific
logic into the orchestration layer. This deliberately keeps
orchestration separate from the scientific modules.

The stage sequence is:

1.  `material\_profile\_builder.py`

2.  `candidate\_pool\_builder.py`

3.  `cheap\_evidence\_metrics.py`

4.  `role\_prior\_engine.py`

The per-material output directory is divided into stable stage folders:

    \<MATERIAL\_ID\>/  
    ├── profile/  
    ├── pools/  
    ├── evidence/  
    ├── role\_priors/  
    └── run\_metadata.json

The pipeline wrapper checks expected outputs for completed stages
and supports explicit stage skipping when reusable artefacts already
exist.

## 5.2 Level B: Batch Orchestration

`batch\_role\_prior\_runner\_structural\_context\_v2.py` orchestrates
multiple per-material runs by invoking `run\_context\_pipeline.py`.

The batch layer is responsible for operational concerns rather
than scientific scoring. These include:

-   accepting multiple material jobs;

-   creating one output area per material;

-   forwarding project, configuration, seed, and cache/reuse options;

-   recording runtime and execution status;

-   isolating failed cases;

-   aggregating successful material outputs into batch summaries;

-   producing the structural-context summary consumed by
    cohort analysis.

Conceptually:

    Batch Input  
        │  
        ▼  
    Batch Runner  
        │  
        ├── Material A ──► run\_context\_pipeline.py ──► A outputs  
        ├── Material B ──► run\_context\_pipeline.py ──► B outputs  
        ├── Material C ──► run\_context\_pipeline.py ──► C outputs  
        │  
        ▼  
    Batch Aggregation  
        │  
        ├── batch manifest / runtime information  
        ├── failed cases  
        ├── batch summary  
        └── structural-context batch summary

A failed material need not invalidate the persisted outputs
of successful material runs.

## 5.3 Level C: Cohort Analysis

`candidate\_context\_analysis\_reference\_neighbourhood.py` is a
separate cohort-level analysis program.

It requires:

-   a structural-context summary for the candidate cohort;

-   a batch output root from which compatible RNFs can be discovered;

-   an output directory for cohort analysis.

The program discovers `reference\_neighbourhood\_fingerprint.json`
files beneath the batch output root, validates their schema
compatibility, joins them to the candidate cohort, evaluates
eligibility/reliability, and performs pairwise and cohort-level
analysis.

This layer therefore consumes completed per-material
representations rather than participating in their construction.

# 6. High-Level Component Architecture

                                  BATCH ORCHESTRATION  
                                          │  
                                          ▼  
                        batch\_role\_prior\_runner\_structural\_context\_v2.py  
                                          │  
                                          ▼  
                               run\_context\_pipeline.py  
                                          │  
              ┌───────────────────────────┼────────────────────────────┐  
              │                           │                            │  
              ▼                           ▼                            ▼  
    material\_profile\_builder.py   candidate\_pool\_builder.py   cheap\_evidence\_metrics.py  
              │                           │                            │  
              │                           │                            ├── evidence summaries  
              │                           │                            └── RNF  
              │                           │                                  │  
              │                           │                                  │  
              └───────────────────────────┴───────────────┐                  │  
                                                          ▼                  │  
                                                 role\_prior\_engine.py        │  
                                                          │                  │  
                                                          ├── SCP v2         │  
                                                          └── auxiliary      │  
                                                              role outputs   │  
                                                          │                  │  
                                                          └────────┬─────────┘  
                                                                   ▼  
                                          candidate\_context\_analysis\_reference\_neighbourhood.py  
                                                                   │  
                                ┌──────────────────────────────────┼─────────────────────────────┐  
                                ▼                                  ▼                             ▼  
                         pairwise comparison                cohort organisation           explainability

Supporting modules sit beneath these stages:

    material\_store.py  
        └── shared dataset access, cached descriptors, external-material registration  
      
    material\_family\_classifier.py  
        └── rule-based material/family classification  
      
    physical\_plausibility.py  
        └── physical plausibility and annotation helpers  
      
    tools/lrt\_phase3\_utils.py  
        └── retained Phase-3 support utility; kept outside the primary pipeline modules

The exact dependency pattern is not a single strict tree.
Some scientific modules use supporting modules directly, while
the orchestration layers invoke major processing stages through
subprocess boundaries.

# 7. Material Ingestion and Shared Data Infrastructure

## 7.1 Material Store

`material\_store.py` provides shared data infrastructure for
the framework.

Its architectural role includes access to the material universe
and cached descriptors required by profiling and candidate selection.
It also provides the common data-access layer used to avoid
embedding dataset-specific access logic independently in each scientific
stage.

The material store is infrastructure, not a scientific inference engine.

## 7.2 JARVIS Materials

For a JARVIS material, the query is resolved against the
configured material data source and converted into the canonical
information required by the Material Profile Builder.

## 7.3 External Materials

The framework also supports externally supplied material records.

At architectural level, external material ingestion is separated
from the reference universe:

    JARVIS ID ─────────────────────┐  
                                   │  
                                   ▼  
                             Material Store  
                                   │  
    External material record ──────┘  
                                   │  
                                   ▼  
                            Material Profile

An external material may be analysed as a query without
necessarily being inserted into the reference universe. This prevents
the candidate being evaluated from automatically changing the corpus
against which it is contextualised.

Where external structures are converted from formats such as POSCAR
into the external record format, that conversion is an ingestion
concern upstream of the common profiling and retrieval architecture.

## 7.4 Material Family Classification

`material\_family\_classifier.py` provides rule-based family
and structural classification used by the profile and retrieval layers.

The classifier supplies derived evidence and retrieval keys.
Its classifications are not treated architecturally as immutable
ground truth; they are versioned inputs to later retrieval and
interpretation.

## 7.5 Physical Plausibility

`physical\_plausibility.py` supplies physical
annotation/plausibility functionality used by other modules.

In the current architecture, physical plausibility is
an annotation/evidence-support concern rather than the principal
mechanism that defines reference-neighbourhood membership. Any future
change that makes physical plausibility directly control retrieval
should be treated as a methodological and architectural change rather
than a silent implementation detail.

# 8. Per-Material Pipeline

## 8.1 Stage 1: Material Profile Builder

**Module:** `material\_profile\_builder.py`\
**Schema:** `phase1.material\_profile.v1.2` in the frozen
implementation\
**Primary persisted output:** `profile/query\_profile.json`

The Material Profile Builder constructs the canonical
broad query-centred representation used by downstream stages.

The Material Profile contains inexpensive material information
and derived retrieval/classification fields. It is broader than
the four-dimensional Structural Context Profile generated later by the
Role Prior Engine.

Architectural responsibilities include:

-   resolve the query material through the shared
    material infrastructure;

-   assemble inexpensive descriptor groups;

-   apply or incorporate material-family classification where available;

-   derive retrieval keys required by candidate selection;

-   record profile schema/version information;

-   persist a machine-readable query profile.

The Material Profile is an upstream data contract and
retrieval scaffold. It is not the RNF and is not the SCP.

## 8.2 Stage 2: Candidate Pool Builder

**Module:** `candidate\_pool\_builder.py`\
**Schema:** `phase2.candidate\_pools.v1.1` in the frozen implementation\
**Primary persisted outputs:**

    pools/  
    ├── same\_family\_pool.csv  
    ├── adjacent\_family\_pool.csv  
    ├── boundary\_contrast\_pool.csv  
    ├── wildcard\_pool.csv  
    ├── negative\_control\_pool.csv  
    ├── candidate\_pool\_summary.json  
    └── pool\_config\_used.json

The Candidate Pool Builder constructs the structured
reference neighbourhood used by evidence generation.

The current architecture separates reference retrieval into:

-   same-family;

-   adjacent-family;

-   boundary/contrast;

-   wildcard;

-   negative-control.

The stage is responsible for deterministic selection, ranking,
pool membership, and recording the configuration used.

The pool outputs are explicit data contracts. Downstream
evidence generation consumes the persisted pools rather than
reconstructing candidate selection implicitly.

## 8.3 Stage 3: Cheap Evidence Metrics and RNF Generation

**Module:** `cheap\_evidence\_metrics.py`\
**Evidence
schema:** `phase3.structural\_context\_evidence.v2\_pool\_context\_summary`\
**RNF schema:** `phase3.reference\_neighbourhood\_fingerprint.v1`

This stage is the principal evidence-generation layer.

Primary persisted outputs expected by the frozen pipeline
wrapper include:

    evidence/  
    ├── cheap\_evidence\_summary.json  
    ├── cheap\_evidence\_metrics.csv  
    ├── cheap\_evidence\_concepts.csv  
    ├── pool\_level\_metrics.csv  
    ├── pool\_context\_summary.json  
    ├── pool\_context\_summary.csv  
    ├── reference\_neighbourhood\_fingerprint.json  
    ├── missing\_value\_report.csv  
    └── evidence\_report.md

The stage calculates pool-level evidence, contextual
summaries, missing-data information, explainability information, and the
RNF.

### RNF as a first-class product

`reference\_neighbourhood\_fingerprint.json` is a primary
persisted per-material representation.

It is not merely a temporary input to role scoring. It can be
discovered and consumed directly by Candidate Context Analysis.

Architecturally, the RNF preserves relational information about
the query's retrieved reference neighbourhood, including ranked
reference identity and aggregate contextual information, together with
provenance and schema information.

The pipeline wrapper explicitly treats the RNF as a
required evidence-stage output. The evidence stage is therefore
incomplete for current v0.1 purposes if the RNF is absent.

## 8.4 Stage 4: Role Prior Engine and Structural Context Profile

**Module:** `role\_prior\_engine.py`\
**Inference
schema:** `phase4\_5.structural\_context\_inference.v4.0\_transition`\
**SCP v2 schema:** `phase1.structural\_context\_profile.v2`

The Role Prior Engine consumes the query profile and evidence outputs
to generate a compact Structural Context Profile and
auxiliary interpretation.

The v0.1 architecture distinguishes two output groups.

### Canonical/current SCP v2 outputs

The frozen pipeline wrapper always expects:

    role\_priors/  
    ├── structural\_context\_profile\_v2.json  
    ├── structural\_context\_profile\_v2\_measurements.csv  
    ├── structural\_context\_profile\_v2\_reliability.csv  
    ├── structural\_context\_profile\_v2\_interpretation.csv  
    ├── structural\_context\_profile\_v2\_summary.csv  
    └── structural\_context\_report\_v2.md

The SCP v2 is the current compact structural-context representation
used to summarise:

-   local context support;

-   structural regime contrast;

-   neighbourhood coherence;

-   structural context diversity;

together with reliability and interpretation information.

### Legacy transition outputs

The frozen implementation can also write legacy outputs
for compatibility during the transition release, including
role-prior summaries, rankings, contradictions, legacy
structural-context profiles, configuration records, and reports.

These outputs preserve the earlier Hub/Boundary/Other
interpretation layer.

Architecturally, that role-prior layer is **auxiliary**. It is not
the definition of the RNF and should not be treated as the
primary scientific endpoint of the current framework.

# 9. Candidate Context Analysis Architecture

## 9.1 Purpose

Candidate Context Analysis is the cohort-level analytical subsystem.

**Module:** `candidate\_context\_analysis\_reference\_neighbourhood.py`\
**Schema:** `candidate\_context\_analysis.phase1c2.reference\_neighbourhood.v1`\
**Supported RNF schema in the frozen
implementation:** `phase3.reference\_neighbourhood\_fingerprint.v1`

CCA compares multiple completed candidate analyses rather
than constructing per-material RNFs.

## 9.2 Input Discovery

The program receives a structural-context summary and a batch
output root.

It recursively discovers RNF files using the configured
fingerprint filename, records discovery information, detects duplicates
or missing fingerprints, checks schema compatibility, and constructs an
inventory of candidate fingerprints.

This discovery layer is important because CCA is deliberately
decoupled from a hard-coded list of individual material directories.

## 9.3 Candidate Eligibility and Reliability

Before exact pairwise analysis, CCA evaluates whether candidates
have the information required for the requested analysis.

Eligibility can consider:

-   RNF availability and schema compatibility;

-   fingerprint completeness;

-   Structural Context Profile completeness;

-   profile confidence;

-   retrieval completeness;

-   evidence sufficiency;

-   pool independence;

-   configured reliability thresholds.

Incomplete or low-reliability cases can therefore be identified
rather than silently treated as equivalent to fully supported
candidates.

## 9.4 Pairwise Comparison Engine

For each eligible pair, CCA can calculate separate components including:

-   Structural Context Profile similarity;

-   reference-identity similarity;

-   reference-distribution similarity;

-   reference-context-feature similarity;

-   overall Reference-Neighbourhood Similarity;

-   Combined Context Similarity;

-   chemistry-baseline similarity;

-   reliability;

-   explainability confidence;

-   profile-neighbourhood discordance.

The architecture deliberately preserves component scores rather
than exposing only a single combined number.

    Candidate A RNF ──┐  
                      ├──► RNF comparison ───────────────┐  
    Candidate B RNF ──┘                                  │  
                                                         ├──► Combined Context Similarity  
    Candidate A SCP ──┐                                  │  
                      ├──► SCP comparison ───────────────┘  
    Candidate B SCP ──┘  
      
    Chemistry/classification information ──► diagnostic baseline

Combined Context Similarity is therefore not synonymous with
RNF similarity. It is a configured integration of SCP and RNF
information.

## 9.5 Cohort Organisation

The pairwise matrices support higher-level cohort analysis including:

-   contextual nearest neighbours;

-   hierarchical clustering;

-   cluster summaries;

-   cluster representatives;

-   contextual distinctiveness;

-   redundancy pairs and groups;

-   inter-cluster candidates;

-   profile/RNF discordance analysis.

These are cohort-relative analytical products. They are not
persisted per-material properties and may change when the candidate
cohort changes.

## 9.6 Explainability

CCA generates explanatory information at pairwise and cluster levels.

The architecture allows an analyst to inspect whether a relationship
is driven mainly by:

-   SCP similarity;

-   shared reference identity;

-   similar contextual distributions;

-   similar pool-level contextual features;

-   or a combination of these factors.

This keeps the cohort analysis auditable rather than reducing it
to opaque clustering output.

## 9.7 Computational Boundary

CCA performs exact pairwise analysis and therefore has
approximately quadratic pairwise scaling with candidate count.

The implementation includes a maximum-exact-candidate safety
boundary. This makes the current subsystem suitable for candidate-cohort
analysis rather than unrestricted all-against-all comparison across the
full reference database.

A future approximate or indexed large-scale comparison engine should
be treated as a separate extension rather than silently changing
the semantics of the current exact analysis.

# 10. Core Data Contracts and Artefact Classes

The framework uses persisted artefacts as stable interfaces
between major stages.

## 10.1 Canonical Machine-Readable Products

Stage Primary product Architectural role

Material profiling `query\_profile.json` Broad query-centred Material
Profile

Candidate retrieval pool CSVs + `candidate\_pool\_summary.json`
Structured reference neighbourhood

Evidence `cheap\_evidence\_summary.json` Aggregated evidence state

Evidence `reference\_neighbourhood\_fingerprint.json` Primary
per-material relational representation

Role/SCP `structural\_context\_profile\_v2.json` Compact
Structural Context Profile

Batch structural-context batch summary Cohort-level SCP/input index

CCA analysis JSON/CSV outputs Pairwise and cohort analytical products

## 10.2 Tabular Analysis Products

CSV outputs are used for:

-   pool membership and ranking;

-   evidence metrics;

-   pool-level context;

-   SCP measurements/reliability/interpretation;

-   batch summaries;

-   pairwise similarities;

-   similarity matrices;

-   nearest neighbours;

-   clusters;

-   distinctiveness;

-   redundancy;

-   inter-cluster analysis;

-   fingerprint inventory and discovery diagnostics.

## 10.3 Diagnostic and Provenance Products

Examples include:

-   `pool\_config\_used.json`;

-   `role\_prior\_config\_used.json` when legacy transition outputs
    are enabled;

-   `run\_metadata.json`;

-   batch manifest/runtime/failure information;

-   missing-value reports;

-   fingerprint inventory/discovery logs;

-   reliability and contradiction outputs.

## 10.4 Human-Facing Products

Markdown reports and generated plots are human-facing interpretations
of the machine-readable products.

They are not intended to replace the canonical JSON/CSV data contracts.

Downstream programmatic consumers should use the
machine-readable artefacts rather than parse Markdown reports.

# 11. Module Responsibilities and Dependency Boundaries

## 11.1 Primary Modules

Module Primary architectural responsibility

`material\_store.py` Shared material data infrastructure,
reference-universe access, cached descriptors, external-material support

`material\_family\_classifier.py` Rule-based
material/family classification

`physical\_plausibility.py` Physical plausibility and annotation support

`tools/lrt\_phase3\_utils.py` Retained Phase-3 support utility; not a
primary pipeline stage

`material\_profile\_builder.py` Canonical Material Profile construction

`candidate\_pool\_builder.py` Deterministic
multi-pool reference-neighbourhood construction

`cheap\_evidence\_metrics.py` Evidence generation,
pool-context summaries, explainability, RNF generation

`role\_prior\_engine.py` SCP v2
generation, reliability/interpretation, auxiliary role-prior analysis

`run\_context\_pipeline.py` Single-material orchestration
and stage-output validation

`batch\_role\_prior\_runner\_structural\_context\_v2.py` Multi-material
orchestration, reuse, runtime/failure tracking, batch aggregation

candidate_context_analysis_reference_neighbourhood.py RNF/SCP discovery,
pairwise comparison, cohort analysis, explainability and reporting

## 11.2 Status of `tools/lrt_phase3_utils.py`

`lrt_phase3_utils.py` is retained in the v0.1 repository under `tools/`.

Its architectural status is **supporting utility code**, rather than a
primary scientific stage or orchestration entry point. It is kept
because it forms part of the frozen implementation/support set and may
be required by Phase-3-related workflows or supporting operations.

The module should therefore not be removed merely because it does not
appear as a top-level stage in the principal RNF/CCA execution diagrams.
At the same time, its presence should not be interpreted as defining a
separate scientific output, data contract, or mandatory pipeline stage.

For v0.1, the publication position is therefore:

-   retain `tools/lrt_phase3_utils.py`;
-   classify it as supporting utility code;
-   keep it outside the principal source-module sequence;
-   do not assign it an independent methodological claim or persisted
    output contract; and
-   if later dependency analysis establishes that it is obsolete, remove
    it only as an explicit post-v0.1 maintenance change with appropriate
    regression testing.

## 11.2 Orchestration Boundaries

The frozen `run\_context\_pipeline.py` intentionally uses
subprocess execution for the four major per-material scientific stages.

Conceptually:

    run\_context\_pipeline.py  
        │  
        ├── subprocess: material\_profile\_builder.py  
        ├── subprocess: candidate\_pool\_builder.py  
        ├── subprocess: cheap\_evidence\_metrics.py  
        └── subprocess: role\_prior\_engine.py

The batch runner similarly invokes `run\_context\_pipeline.py` as
a subprocess.

This architecture avoids moving scientific algorithms into
the orchestration modules and allows each stage to remain
independently executable.

## 11.4 Supporting Dependencies

The specialist modules use shared infrastructure where required.

A simplified dependency view is:

    material\_store.py  
          ▲  
          │  
    material\_profile\_builder.py ─────► material\_family\_classifier.py  
          │  
          └──────────────────────────► physical\_plausibility.py  
      
    candidate\_pool\_builder.py ───────► material\_store.py  
          └──────────────────────────► material\_family\_classifier.py  
      
    cheap\_evidence\_metrics.py ───────► physical\_plausibility.py  
          └── consumes persisted profile + pool artefacts  
      
    role\_prior\_engine.py  
          └── consumes persisted profile + evidence artefacts  
      
    candidate\_context\_analysis\_reference\_neighbourhood.py  
          └── consumes batch structural-context summary + discovered RNFs

This diagram is intentionally architectural rather than an
exhaustive function-level call graph. Low-level standard-library and
third-party imports are outside its scope.

# 12. Configuration, Versioning and Provenance

## 12.1 Schema Versioning

The frozen source explicitly versions major data contracts.

Examples include:

    Material Profile:        phase1.material\_profile.v1.2  
    Candidate Pools:         phase2.candidate\_pools.v1.1  
    Evidence:                phase3.structural\_context\_evidence.v2\_pool\_context\_summary  
    RNF:                     phase3.reference\_neighbourhood\_fingerprint.v1  
    SCP v2:                  phase1.structural\_context\_profile.v2  
    Role inference:          phase4\_5.structural\_context\_inference.v4.0\_transition  
    CCA:                     candidate\_context\_analysis.phase1c2.reference\_neighbourhood.v1

CCA also declares the RNF schema it supports and checks
discovered fingerprints for compatibility.

Schema changes that alter meaning or structure should therefore
be explicit rather than silently overwriting an existing contract.

## 12.2 Analysis Provenance

A reproducible analysis depends on more than the material identifier.

Relevant provenance includes:

-   query material and input type;

-   reference corpus and descriptor state;

-   Material Profile schema;

-   pool-builder schema and configuration;

-   random seed where applicable;

-   evidence and RNF schemas;

-   role/SCP schema and configuration;

-   batch-run configuration;

-   CCA weighting and reliability configuration;

-   candidate cohort;

-   software version/freeze.

Where possible, this information should be retained in
machine-readable run metadata and configuration artefacts.

## 12.3 Configuration as Part of the Representation

The RNF is conditional on the reference corpus and
retrieval/fingerprint configuration.

CCA outputs are additionally conditional on the candidate cohort
and comparison configuration.

Consequently, outputs produced under materially different
configurations should not be assumed to be interchangeable merely
because their filenames match.

# 13. Batch Execution, Failure Isolation and Reuse

## 13.1 Stage Reuse

`run\_context\_pipeline.py` supports explicit skip controls for
completed stages.

The frozen implementation includes controls for reusing:

-   an existing Material Profile;

-   existing candidate pools;

-   completed evidence outputs;

-   completed role-prior/SCP outputs.

Evidence reuse requires all required evidence outputs, including
the RNF, to be present before the evidence stage can be treated as
complete.

## 13.2 Batch Cache Reuse

The batch runner exposes a reuse option that forwards
stage-skip behaviour to the single-material pipeline.

This permits repeated batch work without recomputing every
completed material stage when the relevant artefacts already exist.

Reuse should only be performed when the persisted artefacts
are compatible with the intended configuration. File existence alone is
not a scientific guarantee of configuration equivalence.

## 13.3 Failure Isolation

Batch execution records material-level failures separately
from successful runs.

The architectural intent is that:

-   a material failure is recorded explicitly;

-   successful material artefacts remain available;

-   batch summaries can distinguish completed and failed cases;

-   later diagnosis does not require discarding the entire batch.

## 13.4 Runtime and Manifest Information

Batch-level operational outputs should record enough information
to reconstruct what was attempted and what completed.

Typical batch-level artefacts include:

    batch\_manifest.json  
    batch\_runtime\_log.csv  
    batch\_summary.csv  
    structural\_context\_batch\_summary.csv  
    failed\_cases.csv

The exact set may evolve, but the architectural distinction
between per-material scientific artefacts and
batch-level operational/aggregation artefacts should be retained.

# 14. Output Directory Architecture

A typical batch run follows this conceptual structure:

    \<BATCH\_OUTPUT\_ROOT\>/  
    ├── batch\_manifest.json  
    ├── batch\_runtime\_log.csv  
    ├── batch\_summary.csv  
    ├── structural\_context\_batch\_summary.csv  
    ├── failed\_cases.csv  
    │  
    ├── \<MATERIAL\_ID\_1\>/  
    │   ├── profile/  
    │   │   └── query\_profile.json  
    │   ├── pools/  
    │   │   ├── same\_family\_pool.csv  
    │   │   ├── adjacent\_family\_pool.csv  
    │   │   ├── boundary\_contrast\_pool.csv  
    │   │   ├── wildcard\_pool.csv  
    │   │   ├── negative\_control\_pool.csv  
    │   │   ├── candidate\_pool\_summary.json  
    │   │   └── pool\_config\_used.json  
    │   ├── evidence/  
    │   │   ├── cheap\_evidence\_summary.json  
    │   │   ├── pool\_context\_summary.json  
    │   │   ├── reference\_neighbourhood\_fingerprint.json  
    │   │   └── ...  
    │   ├── role\_priors/  
    │   │   ├── structural\_context\_profile\_v2.json  
    │   │   ├── structural\_context\_profile\_v2\_summary.csv  
    │   │   ├── structural\_context\_profile\_v2\_reliability.csv  
    │   │   └── ...  
    │   └── run\_metadata.json  
    │  
    ├── \<MATERIAL\_ID\_2\>/  
    │   └── ...  
    │  
    └── candidate\_context\_analysis/  
        ├── fingerprint\_inventory.csv  
        ├── fingerprint\_discovery\_log.csv  
        ├── pairwise / matrix outputs  
        ├── nearest-neighbour outputs  
        ├── cluster outputs  
        ├── distinctiveness outputs  
        ├── redundancy outputs  
        ├── discordance / explainability outputs  
        ├── plots  
        └── report

CCA may be written to another explicitly selected output directory;
it is shown beneath the batch root here to illustrate the
logical relationship rather than impose a mandatory filesystem location.

# 15. Repository Structure

The published repository should distinguish source code,
scientific documentation, validation material, tests, and examples.

A recommended v0.1 structure is:

    repository/  
    ├── README.md  
    ├── METHODOLOGY.md  
    ├── ARCHITECTURE.md  
    ├── VALIDATION.md  
    ├── CLAIMS.md  
    ├── LICENSE  
    ├── CITATION.cff  
    ├── .gitignore  
    │  
    ├── src/  
    │   ├── material\_store.py  
    │   ├── material\_profile\_builder.py  
    │   ├── material\_family\_classifier.py  
    │   ├── candidate\_pool\_builder.py  
    │   ├── cheap\_evidence\_metrics.py  
    │   ├── role\_prior\_engine.py  
    │   ├── run\_context\_pipeline.py  
    │   ├── batch\_role\_prior\_runner\_structural\_context\_v2.py  
    │   ├── candidate\_context\_analysis\_reference\_neighbourhood.py  
    │   └── physical\_plausibility.py  
    │  
    ├── tools/  
    │   └── lrt\_phase3\_utils.py  
    │  
    ├── validation/  
    │   └── verification and validation artefacts  
    │  
    ├── examples/  
    │   └── small reproducible example inputs/outputs  
    │  
    ├── tests/  
    │   └── automated or smoke-test material  
    │  
    └── docs/  
        └── supplementary developer/reference documentation

This is a recommended publication layout rather than a statement
that the current frozen source bundle already uses these directories.

Repository restructuring should not change module behaviour during
the v0.1 publication freeze without rerunning the relevant smoke tests.

# 16. Architectural Boundaries

The repository documentation should maintain clear responsibilities.

## `README.md`

Purpose, installation, quick start, minimal usage examples,
repository navigation, and high-level claim boundary.

## `METHODOLOGY.md`

Scientific method, representation definitions, hypotheses,
similarity logic, interpretation, validation strategy, limitations, and
planned baseline comparison.

## `ARCHITECTURE.md`

Software components, orchestration, data flow, persisted
contracts, module responsibilities, versioning, provenance, failure
boundaries, and extension points.

## `VALIDATION.md`

Verification and validation design, datasets, procedures,
results, limitations, and evidence status.

## `CLAIMS.md`

The claims that are justified by the current evidence and the
claims that are explicitly not made.

Architecture documentation should not independently redefine
scientific hypotheses or upgrade validation conclusions.

# 17. Extension Points

The architecture is deliberately modular so that later work can
extend the framework without requiring wholesale replacement.

Potential extension points include:

## 17.1 Additional Material Families

`material\_family\_classifier.py` can be extended with
additional family/prototype logic, provided schema and behavioural
changes are versioned and regression-tested.

## 17.2 Alternative Retrieval Strategies

New candidate pools or retrieval rules can be added, but changes
that alter RNF semantics require explicit
methodology/configuration versioning and should not silently reuse
incompatible RNF schemas.

## 17.3 Alternative RNF Comparison

CCA can support additional comparison components or
weighting strategies, provided existing components remain inspectable
and the changed configuration is recorded.

## 17.4 Conventional-Descriptor Baseline

The planned H4 baseline can be implemented as a parallel
cohort representation and comparison path without altering RNF
construction.

Conceptually:

    Same Candidate Cohort  
            │  
            ├── RNF/SCP representation ──► contextual comparison  
            │  
            └── conventional descriptors ─► baseline comparison  
      
                         compare organisation

This separation is desirable because it allows H4 to be tested
without changing the representation being evaluated.

## 17.5 Large-Cohort Approximation

Future approximate nearest-neighbour or indexed comparison may
improve scaling beyond exact quadratic CCA.

Such an extension should be architecturally separate from the exact
v0.1 comparison engine so that approximation error and semantic changes
can be evaluated explicitly.

## 17.6 Downstream Materials-Discovery Consumers

Future property models, simulation workflows,
candidate-selection systems, or generative materials tools may consume
RNF/CCA outputs.

These are downstream integrations, not current
architectural requirements for generating the v0.1 representation.

# 18. Reproducibility and Operational Guarantees

The framework promotes reproducibility through:

-   deterministic or explicitly seeded candidate selection;

-   persisted stage outputs;

-   explicit schema versions;

-   configuration records;

-   run metadata;

-   separation of per-material and batch-level artefacts;

-   compatibility checking in cohort analysis;

-   machine-readable evidence and representations;

-   explicit failure reporting;

-   reusable completed stages;

-   human-readable reports that can be traced back to
    machine-readable products.

These mechanisms support reproducibility, but they do not remove
the need to preserve the reference dataset, descriptor state,
software version, and configuration used for a published experiment.

# 19. Architectural Status of v0.1

The v0.1 architecture represents a transition from an
earlier role-classification-centred design to a
representation-centred framework.

The principal architectural position is now:

    Material  
       │  
       ▼  
    Material Profile  
       │  
       ▼  
    Reference Retrieval  
       │  
       ▼  
    Evidence  
       │  
       ├────────► RNF ───────────────────────────────┐  
       │                                             │  
       └────────► Role Prior Engine ─► SCP ──────────┤  
                                                     ▼  
                                          Candidate Context Analysis  
                                                     │  
                              ┌──────────────────────┼─────────────────────┐  
                              ▼                      ▼                     ▼  
                          similarity             clustering          explainability

The RNF is the primary persisted relational representation.

The SCP is a compact derived representation that remains
analytically useful and contributes to Combined Context Similarity.

Hub/Boundary/Other role-prior outputs remain available as an
auxiliary interpretation layer for continuity and diagnostics, but they
no longer define the principal scientific identity of the framework.

Candidate Context Analysis is a separate cohort-level subsystem
that consumes completed RNF and SCP information and produces
contextual organisation, comparison, and explanation.

This separation is the central architectural feature of the
current framework.

# 20. Summary

The Reference-Neighbourhood Structural Context Framework is
organised around explicit separation of concerns:

-   shared material infrastructure supplies query and reference data;

-   the Material Profile Builder constructs the broad
    query-centred representation;

-   the Candidate Pool Builder creates a deterministic
    structured reference neighbourhood;

-   Cheap Evidence Metrics generates inspectable evidence and
    the first-class RNF;

-   the Role Prior Engine generates the compact SCP and auxiliary
    role interpretations;

-   the single-material and batch runners provide
    orchestration, persistence, reuse, and failure isolation;

-   Candidate Context Analysis compares completed
    candidate representations at cohort level;

-   schema versioning and provenance preserve the conditions under
    which representations were generated.

The architecture is therefore no longer best understood as a
pipeline culminating in Hub/Boundary/Other inference.

It is a **representation-and-analysis architecture** in which the RNF
is the principal per-material relational product and Candidate
Context Analysis is the principal cohort-level analytical consumer,
while the SCP and role-prior machinery remain explicit, useful, but
separable interpretation layers.
