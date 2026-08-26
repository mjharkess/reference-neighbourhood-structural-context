# **VALIDATION.md**

## **Reference-Neighbourhood Structural Context Framework**

**Version:** v0.1  
**Document role:** Plain-English summary of the verification and validation evidence for the initial Reference-Neighbourhood Fingerprint (RNF) and Candidate Context Analysis (CCA) release  
**Detailed evidence:** `Reference\_Neighbourhood\_Fingerprint\_Verification\_Workbook\_RV04\_Completed.xlsx`  
**Evidence status:** Initial representation verification, not complete scientific validation of the framework

## **1. Purpose**

This document explains the evidence collected so far for the Reference-Neighbourhood Structural Context Framework.

The current tests ask four practical questions:

1. Can the framework reproduce the same result when the same analysis is repeated?

2. Does changing the random seed materially change the result?

3. Does the framework behave differently on selected benchmark groups where different behaviour is expected?

4. Can an observed difference between materials be traced back to the underlying Reference-Neighbourhood Fingerprints and neighbourhood evidence?

All four verification areas recorded in the evidence workbook passed their defined tests.

A **PASS** means only that the particular verification test met its stated expectation. It does not mean that the framework as a whole has been scientifically proven or that all four research hypotheses have been established.

The current evidence is limited and intended to provide a credible starting point for publication and further testing.

## **2. Relationship to the Four Hypotheses**

The methodology defines four hypotheses.

### **H1 — Representation Reproducibility**

A stable and reproducible Reference-Neighbourhood Fingerprint can be produced for an individual material.

**Current position:** Supported within the scope tested.

### **H2 — Context Sensitivity**

Reference-Neighbourhood Fingerprints change in a meaningful and understandable way when materials occupy different structural contexts.

**Current position:** Preliminary support.

### **H3 — Comparative Utility**

Reference-Neighbourhood Fingerprints can help identify useful similarities, differences, and organisation within a group of candidate materials.

**Current position:** Preliminary support.

### **H4 — Incremental Information**

Reference-neighbourhood information provides useful information that is not already captured by conventional material descriptors.

**Current position:** Not established.

The current verification tests provide different levels of evidence for these hypotheses. In particular, passing the current tests does not answer H4. A separate comparison with conventional descriptors is required.

## **3. Verification Summary**

The evidence workbook contains four verification areas.

| **ID** | **Test** | **Result** | **What was observed** |
| :-: | :-: | :-: | :-: |
| **RV-01** | Repeatability | **PASS** | Repeating the same analysis produced identical outputs. |
| **RV-02** | Seed robustness | **PASS** | Changing the tested seed values did not materially change the contextual organisation. |
| **RV-03** | Known controls | **PASS** | The three benchmark groups behaved differently in the expected qualitative way. |
| **RV-04** | Interpretability | **PASS** | A selected contextual difference could be traced to observable RNF and neighbourhood differences. |

The appropriate overall conclusion is:

Within the cases tested, the framework is repeatable, stable under the seed changes examined, capable of producing different and coherent organisation across selected benchmark groups, and sufficiently inspectable for selected contextual differences to be traced to underlying evidence.

This is a verification result, not a claim that the framework is universally valid or superior to existing materials representations.

## **4. RV-01 — Repeatability**

### **Question**

If exactly the same analysis is run again under the same conditions, does the framework produce the same result?

### **Test**

The pipeline was run and then repeated using the same inputs and random seed. The resulting fingerprints, profiles, and outputs were compared.

### **Result**

**PASS**

The repeated outputs were recorded as identical.

### **What this tells us**

RV-01 provides direct evidence for H1 within the tested case: the implementation can reproduce its own result when the tested conditions are held constant.

### **What it does not tell us**

This test does not establish reproducibility:

- across different computers or operating systems;

- across different software versions;

- across different versions of the reference database; or

- across every possible material.

Those are broader reproducibility questions that can be tested later.

## **5. RV-02 — Seed Robustness**

### **Question**

Does changing the configured random seed materially change the result?

This matters because an analytical result should not depend strongly on an arbitrary seed unless randomness is intentionally part of the method.

### **Tests**

Two seed tests were recorded.

The first compared seeds **1, 481, and 999**. Candidate clusters, ordering, contextual organisation, and interpretation remained the same. Small numerical changes of about **0.001 or less** were recorded, but they did not change the scientific conclusion.

The second test compared seeds **11, 4811, and 9991** across ten candidates. Cluster membership and the contextual partition remained identical. Cluster numbers changed in some runs, but this was only a relabelling of the same groups.

### **Result**

**PASS**

### **What this tells us**

For the cases tested, changing the seed did not materially change the substantive result.

The candidate-pool process is designed to be deterministic. The seed is used only to resolve otherwise indistinguishable ranking ties. No such tie affected pool membership in these verification cases.

RV-02 therefore strengthens the evidence that the current results are not simply an artefact of the particular seed chosen.

### **What it does not tell us**

The test does not prove that seed choice can never matter. Other datasets could contain unresolved ties where the seed-based tie-break becomes active.

## **6. RV-03 — Known Controls**

### **Question**

Does the framework behave sensibly when applied to selected groups of materials expected to show different kinds of organisation?

Three benchmark groups were used:

- CdI₂;

- CoO₂; and

- NbSe₂.

CdI₂ was used as a negative control expected to remain predominantly one contextual group. CoO₂ and NbSe₂ were expected to contain more than one coherent contextual group.

### **CdI₂**

**Expected:** One dominant contextual regime.

**Observed:** Nine of the ten candidates formed one group. One candidate was placed in a separate singleton cluster.

The singleton was nevertheless extremely similar to the rest of the group, with an average combined-context similarity of approximately **0.997**, so it was not interpreted as evidence for a meaningful second regime.

**Result: PASS**

The framework therefore did not treat every cluster produced by the algorithm as automatically scientifically meaningful.

### **CoO₂**

**Expected:** More than one coherent contextual regime without fragmentation into many small groups.

**Observed:** Two groups were produced, containing **six and four candidates**. No singleton or spurious groups were recorded.

**Result: PASS**

### **NbSe₂**

**Expected:** More than one coherent contextual regime without fragmentation into many small groups.

**Observed:** Two groups were produced, again containing **six and four candidates**. The members of each group had very high internal contextual similarity.

The compact Structural Context Profiles remained similar across the groups, while the RNF-supported analysis separated them.

**Result: PASS**

### **What RV-03 tells us**

The framework did not impose the same pattern on every benchmark group. The negative control remained predominantly one contextual regime, while the two positive controls produced two coherent groups.

This provides preliminary evidence relevant to H2 and H3.

### **What it does not tell us**

The test does not prove that:

- the same behaviour will occur across all materials;

- the recovered groups are universally recognised scientific classes;

- the framework has a known statistical sensitivity or specificity; or

- RNF is better than conventional material descriptors.

The benchmark set is small and deliberately selected.

## **7. RV-04 — Interpretability**

### **Question**

When Candidate Context Analysis places two materials in different contextual groups, can that difference be traced to observable evidence rather than simply accepting the cluster labels?

### **Test**

Two NbSe₂ candidates were selected:

- `JVASP-580`; and

- `JVASP-93735`.

They have the same chemistry and the same broad family classifications and were analysed using the same quantities of evidence in the main retrieval pools.

Despite these similarities, they were assigned to different contextual groups. The verification examined whether their underlying reference-neighbourhood summaries also differed.

### **Observed evidence**

The two materials retrieved slightly different overall neighbourhoods:

| **Measure** | **JVASP-580** | **JVASP-93735** |
| :-: | :-: | :-: |
| Unique reference materials | 1,452 | 1,462 |
| Same-family / boundary overlap | 248 | 238 |
| Space group | P-6m2 | P6₃/mmc |
| Space-group number | 187 | 194 |

These numbers do not suggest that a difference of ten neighbours is inherently scientifically important. They show that the contextual distinction has observable representation-level evidence behind it.

### **Result**

**PASS**

### **What this tells us**

The separation between these two candidates was not merely an unexplained output from the clustering algorithm.

The materials have:

- the same chemistry;

- matched family classifications;

- equal evidence-pool sizes;

- different contextual assignments; and

- observable differences in their retrieved neighbourhoods.

The contextual distinction can therefore be investigated through the underlying RNF and neighbourhood evidence, providing preliminary interpretability evidence relevant to H2 and H3.

### **Important limitation**

RV-04 does **not** establish that the difference in crystallographic space group caused the difference in the retrieved neighbourhoods or the different contextual assignments.

The space groups demonstrate that the candidates are different crystallographic variants. The available evidence does not establish the causal chain between that structural difference and the retrieval result.

A stronger causal claim would require direct examination of the identities and distributions of the retrieved reference materials.

The PASS means:

Observable RNF and neighbourhood differences provide an interpretable basis for examining the contextual distinction.

It does not mean:

The space-group difference has been proven to cause the contextual distinction.

### **Provenance limitation**

Some provenance information was not recorded in the original RV-04 evidence, including the reference-corpus version, software version, seed, reviewer, date, and exact evidence filenames.

These details have been left as unrecorded rather than reconstructed after the event. This limits the auditability of RV-04 and should be corrected in future verification work.

## **8. What the Current Evidence Supports**

Taken together, RV-01 to RV-04 support a limited set of conclusions.

### **Repeatability**

The tested repeated execution produced identical outputs.

### **Robustness to the tested seeds**

Changing the seeds used in the recorded tests did not materially alter contextual organisation or interpretation.

### **Different behaviour across benchmark groups**

The framework did not produce the same clustering pattern in every case. The selected negative and positive controls showed different qualitative organisation.

### **Inspectability**

At least one selected contextual separation could be examined through the underlying RNF and retrieved-neighbourhood evidence rather than relying solely on a cluster label.

### **Exploratory comparative use**

The tested Candidate Context Analysis results provide preliminary evidence that RNFs can be used to organise and compare candidate materials.

These conclusions are narrower than claiming that the framework as a whole is scientifically validated.

## **9. What the Current Evidence Does Not Establish**

The current verification does **not** establish that:

- RNFs are better than conventional material descriptors;

- RNFs contain useful information unavailable from conventional descriptors;

- Candidate Context Analysis improves materials discovery;

- contextual clusters correspond to experimentally established material classes;

- contextual similarity predicts physical properties;

- Hub, Boundary, and Other are externally validated scientific categories;

- the current weights, thresholds, and other settings are optimal;

- results are robust to major changes in the reference database;

- the observed seed robustness applies to every possible dataset; or

- the crystallographic difference examined in RV-04 caused the observed retrieval differences.

These questions require additional evidence.

## **10. Main Limitations of the Current Verification**

### **Small benchmark set**

The verification uses a small number of deliberately selected cases. This is appropriate for checking an initial implementation, but not for making broad statistical claims.

### **Qualitative controls**

The expected behaviour of the benchmark groups is mainly qualitative. There is no large independent set of externally labelled contextual classes against which the framework can be scored.

### **Parameter sensitivity has not been systematically tested**

The current verification does not establish how much results would change if important weights, thresholds, clustering settings, or other parameters were varied.

### **Reference-corpus robustness has not been tested**

RNFs depend on the reference population. The current verification does not establish whether the same conclusions would survive substantial changes to that population.

### **Cross-platform and cross-version reproducibility has not been tested**

The repeatability test concerns the recorded execution conditions. It does not establish identical behaviour across software environments or database versions.

### **RV-04 provenance is incomplete**

Some information needed to reproduce the RV-04 test exactly was not recorded in the original evidence.

### **H4 remains untested**

The current verification does not compare RNF against an appropriate conventional-descriptor baseline and therefore cannot establish that RNF contributes additional useful information.

## **11. Current Evidence Position by Hypothesis**

| **Hypothesis** | **Current position** | **Main evidence** |
| :-: | :-: | :-: |
| **H1 — Representation Reproducibility** | Supported within tested scope | RV-01 and RV-02 |
| **H2 — Context Sensitivity** | Preliminary support | RV-03 and RV-04 |
| **H3 — Comparative Utility** | Preliminary support | RV-03 and RV-04 |
| **H4 — Incremental Information** | Not established | Conventional-descriptor baseline still required |

These descriptions intentionally use different levels of confidence. A PASS on an individual verification does not automatically turn the related research hypothesis into a proven statement.

## **12. Next Validation Priority**

The most important next experiment is the **conventional-descriptor baseline comparison** required to test H4.

The central question is:

Does the Reference-Neighbourhood Fingerprint provide useful organisation that is not already available from a simpler conventional description of the same materials?

The comparison should use the same candidate set and compare:

1. conventional material descriptors;

2. RNF-based representation; and

3. where useful, a combined representation.

The comparison should examine whether the methods identify the same or different:

- nearest neighbours;

- similarity relationships;

- candidate groups; and

- unusual or distinctive candidates.

Agreement is not automatically good or bad.

If the RNF largely reproduces the conventional baseline, that would weaken the case that it contains important additional information.

If it produces systematic, understandable differences, that would provide evidence in favour of H4.

If the differences are unstable or cannot be explained, that would weaken the case for H4.

The v0.1 methodology should remain fixed during this test so that the method is evaluated as published rather than changed after the result is known.

## **13. Future Verification Records**

Future verification should record enough information for another person to understand and reproduce what was done.

At minimum, each test should record:

- what question was tested;

- which materials or datasets were used;

- the reference dataset and version;

- the software or repository version;

- the important configuration settings;

- the seed, where relevant;

- the expected result;

- the observed result;

- the pass/fail rule;

- the evidence files;

- the date; and

- any important limitations.

A verification result is only as auditable as the evidence retained behind it.

## **14. Overall Conclusion**

All four verification areas in the current evidence workbook are recorded as **PASS**.

Within the cases tested, the evidence supports the conclusion that:

- the framework can reproduce its outputs;

- its substantive results are stable under the seed changes examined;

- it produces different and coherent contextual organisation across selected benchmark groups; and

- selected contextual differences can be traced to observable RNF and neighbourhood evidence.

This provides a reasonable verification basis for freezing and publishing an initial v0.1 implementation for further testing.

It does **not** establish that the framework is a validated replacement for conventional material descriptors or that it improves materials discovery.

The evidence position remains:

- **H1:** supported within the tested scope;

- **H2:** preliminary support;

- **H3:** preliminary support; and

- **H4:** not established.

The next major scientific question is whether the reference-neighbourhood representation adds useful information beyond simpler conventional representations.

