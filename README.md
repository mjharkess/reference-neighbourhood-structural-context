# **Reference-Neighbourhood Structural Context Framework**

An experimental framework for describing and comparing materials by looking at the **reference materials around them**, rather than only at the materials themselves.

The framework has two main outputs:

- the **Reference-Neighbourhood Fingerprint (RNF)**, which describes an individual material through its retrieved reference neighbourhood; and

- **Candidate Context Analysis (CCA)**, which compares RNFs across a group of candidate materials.

**v0.1 status:** Initial research release. The current evidence shows that the framework can reproduce its outputs under the conditions tested and provides preliminary evidence that it can identify and explain differences between selected groups of materials. It does **not** yet show that RNF adds useful information beyond conventional material descriptors or improves materials discovery.

## **1. The Basic Idea**

Alongside conventional material-centred descriptors, this project asks
whether an explicitly constructed reference neighbourhood can provide a
useful additional representation.

For each material, the framework searches a reference database for
relevant materials and records the character of the resulting
neighbourhood. This becomes the **Reference-Neighbourhood Fingerprint**.

When several candidate materials are being studied, **Candidate Context** **Analysis** compares their fingerprints to look for similarities,
differences, groups, unusual candidates, and other patterns.

The RNF is not an intrinsic physical property of a material. It depends
on the reference population and on how the neighbourhood is constructed.

### **Relationship to Existing Approaches**

Reference-relative materials analysis is not new. Previous approaches
have used structural fingerprints, structural-similarity search,
prototype matching, materials-space maps, local novelty measures, and
structural communities to describe or compare materials relative to
existing populations.

RN-SCF builds on this broader family of methods. Its specific focus is
the construction of an inspectable, query-centred reference
neighbourhood containing several deliberately different forms of
evidence, the persistence of information about that neighbourhood as a
**Reference-Neighbourhood Fingerprint (RNF)**, and the subsequent
comparison of RNFs across candidate groups through **Candidate Context** **Analysis (CCA)**.

The project does not currently claim that this representation contains
information unavailable from conventional material descriptors or
existing structural representations. Whether RNF provides useful
additional information is an empirical question addressed separately by
**H4**.

For the full methodology and discussion of the relationship to existing
methods, see [`METHODOLOGY.md`](docs/METHODOLOGY.md).

## **2. What the Project Is Testing**

The project is organised around four hypotheses.

| Hypothesis | Question | Current position |
| --- | --- | --- |
| **H1 — Reproducibility** | Can the same RNF be produced reliably under the same conditions? | **Supported within tested scope** |
| **H2 — Context sensitivity** | Do RNFs respond meaningfully to differences in structural context? | **Preliminary support** |
| **H3 — Comparative utility** | Can RNFs help organise and compare groups of candidate materials? | **Preliminary support** |
| **H4 — Additional information** | Does RNF provide useful information beyond conventional material descriptors? | **Not established** |


H4 is important because the framework could be reproducible and produce interesting comparisons while still adding little beyond simpler conventional descriptions.

A separate baseline experiment is planned to test H4.

Improved materials discovery is a possible future use of the framework. It is **not a claim of v0.1**.

## **3. How the Framework Works**

The process is:

```text
Material
  ↓
Lightweight Material Profile
  ↓
Search Reference Population
  ↓
Build Reference Neighbourhood
  ↓
Reference-Neighbourhood Fingerprint (RNF)
  ↓
Compare Candidate Materials
  ↓
Candidate Context Analysis (CCA)
```


### **Reference-Neighbourhood Fingerprint**

The **RNF** is the main output for an individual material.

It records information about the reference materials retrieved around that material, including how concentrated, diverse, similar, or contrasting the neighbourhood is.

The canonical persisted RNF is:

```
evidence/reference_neighbourhood_fingerprint.json
```

### **Candidate Context Analysis**

**CCA** compares a group of candidate materials using their RNFs and related structural-context information.

It can help identify:

- candidates with similar contexts;

- candidates that are relatively different;

- groups of related candidates;

- potentially redundant candidates;

- representative or unusual candidates; and

- evidence explaining why two candidates appear similar or different.

CCA groups are analytical outputs. They should not automatically be treated as experimentally established material classes.

### **Hub, Boundary, and Other**

The software also produces **Hub**, **Boundary**, and **Other** labels and related diagnostics.

These are supporting interpretation tools from an earlier stage of the project. They remain available, but they are not the main scientific output of v0.1 and are not claimed to be validated scientific categories.

## **4. What Has Been Tested**

The current verification programme contains four main tests.

| Test | Purpose | Result |
| --- | --- | --- |
| **RV-01 — Repeatability** | Check whether repeating the same analysis produces the same result. | **PASS** |
| **RV-02 — Seed robustness** | Check whether the tested random-seed changes materially alter the result. | **PASS** |
| **RV-03 — Known controls** | Check whether selected benchmark groups show the expected broad differences in organisation. | **PASS** |
| **RV-04 — Interpretability** | Check whether a selected CCA difference can be traced to underlying RNF and neighbourhood evidence. | **PASS** |


A **PASS** means that the particular verification test met its stated expectation. It does not mean that the framework as a whole has been scientifically proven.

The current evidence supports H1 within the tested scope and provides preliminary support for H2 and H3. H4 remains untested against the required conventional-descriptor baseline.

See [`VALIDATION.md`](docs/VALIDATION.md) for the evidence and [`CLAIMS.md`](docs/CLAIMS.md) for the formal claim boundary.

## **5. What v0.1 Does Not Claim**

The current release does **not** claim that:

- RNF is better than conventional material descriptors;

- RNF contains unique information unavailable from conventional descriptors;

- RNF or CCA improves materials discovery;

- CCA groups are true or uniquely correct scientific material classes;

- contextual similarity predicts physical properties;

- the framework identifies physical mechanisms;

- Hub, Boundary, and Other are validated scientific material categories;

- the current settings and parameters are optimal;

- the framework has been validated across all materials or the complete JARVIS corpus; or

- RNF is an intrinsic physical property of a material.

The intended v0.1 claim is narrower:

**The framework provides a reproducible, reference-relative** **representation and an inspectable way of comparing candidate materials** **that behaved coherently in the verification cases examined.**

## **6. Inputs and Outputs**

### **JARVIS materials**

A batch of JARVIS materials can be supplied as a CSV or text file containing material IDs.

For example:

```
`jid`

`JVASP-119589`

`JVASP-122407`

`JVASP-143116`
```

### **External materials**

The framework can also analyse external crystalline structures prepared from supported structure files such as POSCAR, CONTCAR, or CIF.

The external-material preparation step converts the structure into the form required by the framework.

See [`EXTERNAL_INPUT.md`](docs/EXTERNAL_INPUT.md) and [`external_material.schema.json`](schemas/external_material.schema.json) for the detailed input requirements.

### **Main outputs**

A normal analysis produces:

- a material profile;

- the retrieved reference pools;

- evidence summaries;

- the Reference-Neighbourhood Fingerprint;

- supporting structural-context outputs;

- run metadata; and

- batch summaries.

CCA then produces cohort-level comparison results.

The detailed file structure and data flow are documented in [`ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## **7. Quick Start**

The commands below show the main workflow. For a complete reproducible setup, including the Python environment, JARVIS reference data, descriptor cache, and package versions, use [`REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

### **Set up the Python environment**

The recorded v0.1 environment uses Python 3.13.12.

A clean virtual environment is recommended:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-freeze-v0.1.txt
```

### **Run the supplied 10-material JARVIS batch**

The repository includes the 10-material v0.1 reproduction cohort at `examples/reproducibility/jarvis_ids.csv`.

From the repository root, run:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --input_ids ./examples/reproducibility/jarvis_ids.csv \
  --project_dir . \
  --output_dir ./outputs/jarvis_batch \
  --seed 87
```

The first clean run may take longer because reference data or the descriptor cache may need to be obtained or built.

### **Run Candidate Context Analysis**

After the batch completes:

```bash
python3 candidate_context_analysis_reference_neighbourhood.py \
  --structural_context_summary ./outputs/jarvis_batch/structural_context_batch_summary.csv \
  --batch_output_root ./outputs/jarvis_batch \
  --output_dir ./outputs/jarvis_batch/candidate_context_analysis \
  --top_k 5 \
  --seed 87
```

This reads the per-material outputs and produces comparisons across the candidate group.

### **Analyse an external material**

First prepare the structure:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure ./POSCAR \
  --external_format poscar \
  --external_id EXT-0001 \
  --output_dir ./external_prepared/EXT-0001
```

Then follow the external-material batch procedure described in [`EXTERNAL_INPUT.md`](docs/EXTERNAL_INPUT.md) and `REPRODUCIBILITY.md`.

## **8. Documentation Guide**

| Document | What it is for |
| --- | --- |
| [`METHODOLOGY.md`](docs/METHODOLOGY.md) | Explanation of the idea, method, and H1–H4 hypotheses. |
| [`VALIDATION.md`](docs/VALIDATION.md) | What has been tested, what happened, and the limits of that evidence. |
| [`CLAIMS.md`](docs/CLAIMS.md) | What the current evidence does and does not allow the project to claim. |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Detailed software design, components, data flow, and implementation. |
| [`REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Environment setup, reference-data reconstruction, commands, and reproduction procedure. |
| [`EXTERNAL_INPUT.md`](docs/EXTERNAL_INPUT.md) | How external material structures are prepared and supplied to the framework. |
| [`external_material.schema.json`](schemas/external_material.schema.json) | Machine-readable definition of the external-material input format. |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Third-party software and data licensing and attribution. |
| [`CITATION.cff`](CITATION.cff) | Machine-readable citation information. |
| [`LICENSE`](LICENSE) | Apache License 2.0 for original project material. |


A reader trying to understand the research should normally start with this README and then read **Methodology → Validation → Claims**.

`ARCHITECTURE.md` and `REPRODUCIBILITY.md` are primarily for readers who want to understand or run the implementation.

## **9. Project Status and Next Experiment**

v0.1 is intended to freeze an initial version of the framework before its strongest open hypothesis is tested.

The next major experiment is the **conventional-descriptor baseline** **comparison for H4**:

**Does RNF reveal useful organisation that is not already available from** **a simpler conventional representation of the same candidate materials?**

If RNF produces systematic and understandable distinctions that the conventional baseline does not reproduce, that would provide evidence in favour of H4.

If it largely reproduces the baseline, or produces differences that are unstable or unexplained, the scientific claim should remain narrower.

Either result is useful because the v0.1 method and claim boundary have been defined before the comparison is performed.

Other future work may include broader benchmark testing, parameter-sensitivity analysis, reference-dataset robustness, cross-platform reproduction, and eventual tests of whether the framework improves real materials-selection decisions.

## **10. Reproducibility**

Reproducibility and scientific validation are treated separately.

The project records a reference Python environment and provides a frozen dependency list in `requirements-freeze-v0.1.txt`.

The detailed reproduction procedure is in [`REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

Because the framework depends on external reference data, a published analysis should record the relevant code release, candidate cohort, configuration, seed, reference-data state, and other information needed to reconstruct the analysis.

## **11. Citation**

Machine-readable citation information is provided in [`CITATION.cff`](CITATION.cff).

Until an archived release, DOI, or associated publication exists, users should cite the repository and the specific release or commit used.

**Author:** Michael Harkess

## **12. Licence and Third-Party Material**

Original project material is distributed under the **Apache License** **2.0**. See [`LICENSE`](LICENSE).

Third-party software and data remain subject to their own licences and terms. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

The project uses materials data and software from **NIST JARVIS /** **JARVIS-Tools**. The canonical v0.1 repository does not redistribute the generated JARVIS reference datastore; required reference data are reconstructed from the upstream source.

## **13. Release Status**

This README describes the planned **v0.1.0 initial research release**.

v0.1 is intended to publish a clear method, working implementation, evidence record, and claim boundary so that the more important scientific questions can be tested against a fixed starting point.

