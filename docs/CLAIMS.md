# **CLAIMS.md**

## **Reference-Neighbourhood Structural Context Framework**

**Version:** v0.1  
**Document role:** Defines what may and may not reasonably be claimed from the current evidence  
**Evidence basis:** `METHODOLOGY.md`, `VALIDATION.md`, and the v0.1 verification evidence  
**Claim status:** Initial claims for the v0.1 research release

## **1. Purpose**

This document sets the scientific claim boundary for v0.1 of the Reference-Neighbourhood Structural Context Framework.

**What can we reasonably say about the framework from the evidence currently available?**

The other project documents serve different purposes:

- `METHODOLOGY.md` explains what the framework does and the hypotheses being tested.

- `ARCHITECTURE.md` explains how the software implements the framework.

- `VALIDATION.md` explains what has actually been tested and what happened.

- `CLAIMS.md` defines what those results allow the project to say publicly.

The claims must follow the evidence. An interesting output, a plausible interpretation, or a capability present in the software is not by itself evidence for a scientific claim.

The v0.1 position is conservative. This release is intended to publish a reproducible and testable research framework, not present it as a completed or universally validated materials-discovery method.

## **2. What the Project Is Claiming About**

There are two main scientific outputs.

### **Reference-Neighbourhood Fingerprint**

The **Reference-Neighbourhood Fingerprint (RNF)** is the main representation produced for an individual material.

It describes a material through the reference materials retrieved around it.

The RNF is **reference-relative**. It depends on the reference population, retrieval method, available data, and configuration used to create it.

It should not be described as an intrinsic or experimentally measured property of the material.

### **Candidate Context Analysis**

**Candidate Context Analysis (CCA)** compares a group of candidate materials using their RNFs and related structural-context information.

It can identify similarities, differences, groups, unusual candidates, and other relationships within the analysed cohort.

These are analytical results produced by the framework. A CCA group or cluster should not automatically be described as a scientifically established material class.

### **Hub, Boundary, and Other**

The framework also produces **Hub**, **Boundary**, and **Other** labels and related diagnostics.

These are supporting interpretation tools inherited from an earlier stage of the project. They are not the main scientific output of v0.1 and are not claimed to be externally validated material classes.

## **3. How Claim Strength Is Described**

This document uses three main levels.

### **Supported within tested scope**

There is direct evidence supporting the claim in the cases tested.

The claim should not be generalised beyond those cases without further evidence.

### **Preliminary support**

The existing evidence is consistent with the claim and provides a reasonable initial basis for it, but remains limited.

### **Not established**

The evidence needed to make the claim has not yet been obtained.

A result can be supported in a small verification exercise without being established as a general scientific result.

## **4. C1 — Reproducible Outputs**

### **Claim**

**Under the fixed conditions tested, the framework can reproduce its Reference-Neighbourhood Fingerprints and associated outputs.**

**Status:** Supported within tested scope  
**Main evidence:** RV-01  
**Main hypothesis:** H1

The repeatability test ran the same analysis twice under the same conditions and recorded identical outputs.

This supports a claim of reproducibility for the conditions tested.

It does **not** establish that identical results will necessarily be obtained:

- on every computer or operating system;

- with different software versions;

- with a different reference database;

- after changing the methodology or configuration; or

- for every possible material.

The RNF is reproducible relative to defined analytical conditions. It is not an invariant property that must remain unchanged when those conditions change.

## **5. C2 — Robustness to the Seeds Tested**

### **Claim**

**For the verification cases examined, changing the random seed across the tested values did not materially change the contextual result.**

**Status:** Supported within tested scope  
**Main evidence:** RV-02

Two separate seed tests were performed.

Across the tested seeds, candidate organisation and interpretation remained unchanged. Small numerical differences were observed in one test, but they did not alter the scientific conclusion. In the other test, cluster numbers changed but the actual membership of the groups did not.

This supports the claim that the recorded results were not materially dependent on the particular seeds tested.

It does **not** establish that seed choice can never affect a result. Other datasets may contain ranking ties or other circumstances in which the seed becomes relevant.

## **6. C3 — Context-Sensitive Behaviour**

### **Claim**

**The framework showed coherent and different contextual behaviour across the selected benchmark groups.**

**Status:** Preliminary support  
**Main evidence:** RV-03  
**Main hypotheses:** H2 and H3

Three benchmark groups were examined.

The CdI₂ negative control remained predominantly one contextual group. CoO₂ and NbSe₂ each produced two coherent groups.

The framework therefore did not impose the same pattern on every benchmark cohort, providing preliminary support for the idea that RNF and CCA respond to differences in the context represented by the selected benchmark materials.

It does **not** establish:

- that the framework will behave correctly for every type of material;

- that every cluster assignment is scientifically correct;

- that the groups represent fundamental or universally accepted material classes;

- that the method has known sensitivity or specificity across materials space; or

- that it performs better than conventional material representations.

The current benchmark set is small and the expected behaviour is mainly qualitative.

## **7. C4 — Inspectable Contextual Differences**

### **Claim**

**Selected differences identified by Candidate Context Analysis can be traced to observable differences in the underlying Reference-Neighbourhood Fingerprints and retrieved neighbourhoods.**

**Status:** Preliminary support  
**Main evidence:** RV-04  
**Main hypotheses:** H2 and H3

RV-04 examined two NbSe₂ candidates that share the same chemistry and broad family classifications but were placed in different contextual groups.

Their retrieved neighbourhoods were measurably different.

The contextual distinction can therefore be investigated through the underlying representation rather than accepted simply because a clustering algorithm produced two labels. This supports a limited claim of **interpretability**.

It does **not** establish the physical cause of the difference.

In particular, the two materials have different crystallographic variants, but RV-04 does not prove that this difference caused the different retrieved neighbourhoods or contextual assignments.

C4 is an interpretability claim, not a claim that the framework has discovered a physical mechanism.

## **8. Position of the Four Hypotheses**

The claims above relate to the four hypotheses defined in `METHODOLOGY.md`.

| **Hypothesis** | **Current position** | **What may reasonably be said** |
| :-: | :-: | :-: |
| **H1 — Representation Reproducibility** | Supported within tested scope | The framework reproduced its outputs under the fixed conditions tested. |
| **H2 — Context Sensitivity** | Preliminary support | Selected benchmark and interpretability tests show context-sensitive and inspectable behaviour. |
| **H3 — Comparative Utility** | Preliminary support | CCA can organise and compare the tested candidate groups in an interpretable way. |
| **H4 — Incremental Information** | Not established | No positive claim should yet be made that RNF adds useful information beyond conventional descriptors. |

These hypotheses are separate. Evidence for H1 does not establish H2, H3, or H4.

Likewise, showing that CCA can organise candidate materials does not establish that it is better than conventional methods or improves materials discovery.

## **9. H4 Remains Open**

H4 is the most important major claim that v0.1 does **not** make.

H4 asks:

**Does the Reference-Neighbourhood Fingerprint provide useful information that is not already captured by conventional material descriptors?**

The current verification does not answer this question.

The NbSe₂ tests provide an indication that detailed RNF information can distinguish candidates when a smaller Structural Context Profile remains similar. However, the Structural Context Profile is not an adequate conventional-descriptor baseline.

A separate baseline comparison is required.

### **If H4 is supported**

A later release might reasonably make a claim such as:

**Within the tested candidate set, RNF identified useful distinctions that were not fully reproduced by the selected conventional-descriptor baseline.**

The wording would still need to remain specific to the experiment actually performed.

### **If H4 is not supported**

The appropriate conclusion would be that the RNF did not demonstrate meaningful additional information beyond the selected conventional descriptors in that test.

That result would not automatically invalidate H1 and could also leave parts of H2 and H3 intact.

A negative H4 result would instead change what can reasonably be claimed about the value added by the RNF.

## **10. Claims Not Made by v0.1**

The v0.1 release does **not** claim that:

- RNF is better than conventional material descriptors;

- RNF contains unique or independent information unavailable from conventional descriptors;

- RNF or CCA improves materials discovery;

- CCA clusters are experimentally established or uniquely correct material classes;

- contextual similarity predicts physical properties;

- the framework identifies physical mechanisms;

- Hub, Boundary, and Other are validated scientific material categories;

- the current settings, weights, thresholds, pool sizes, or clustering choices are optimal;

- the method has been validated across the complete JARVIS dataset or across materials space;

- results will remain unchanged if the reference population changes substantially;

- the tested seed robustness applies to every possible dataset;

- RNF is an intrinsic physical property of a material;

- the crystallographic difference examined in RV-04 caused the observed neighbourhood difference; or

- the current implementation is a proven or production-ready materials-discovery system.

These form the formal claim boundary, not merely cautious footnotes.

## **11. Materials-Discovery Claims**

The framework may eventually be useful for tasks such as:

- comparing candidate materials;

- identifying unusual candidates;

- reducing redundancy in candidate sets;

- prioritising materials for further analysis;

- examining outputs from generative models; or

- supporting experimental or computational selection.

These are potential uses, not demonstrated benefits.

The current evidence does not show that using RNF or CCA improves discovery rates, candidate quality, experimental success, property prediction, or another downstream outcome.

Any future claim of this kind should be supported by a dedicated experiment.

## **12. Appropriate Public Statements**

The following statements are consistent with the current evidence:

- “The framework constructs a reference-relative Reference-Neighbourhood Fingerprint for each material.”

- “The framework reproduced its outputs under the fixed verification conditions tested.”

- “The tested seed changes did not materially alter contextual organisation.”

- “Selected benchmark tests provide preliminary evidence of context-sensitive behaviour.”

- “Candidate Context Analysis produced coherent contextual organisation in the tested benchmark groups.”

- “Selected contextual distinctions can be investigated through underlying RNF and retrieved-neighbourhood evidence.”

- “Current evidence provides preliminary support for comparative use within the tested cohorts.”

- “Whether RNF adds useful information beyond conventional descriptors remains an open hypothesis.”

- “Materials-discovery benefit has not yet been demonstrated.”

Statements that should **not** be used for v0.1 include:

- “RNF outperforms conventional descriptors.”

- “RNF captures information unavailable to conventional descriptors.”

- “The framework discovers new materials.”

- “CCA identifies the true structural classes of materials.”

- “The framework predicts material properties.”

- “The method has been validated across materials space.”

- “The framework improves candidate selection.”

- “Hub, Boundary, and Other are validated material categories.”

- “RNF is an intrinsic property of a material.”

If later experiments justify stronger wording, that claim should belong to the later evidence state rather than being attributed retrospectively to v0.1.

## **13. Overall v0.1 Claim**

The recommended high-level description of the scientific position of v0.1 is:

The **Reference-Neighbourhood Structural Context Framework** is an experimental method for representing and comparing materials using the reference materials retrieved around them.


Its main per-material output is the **Reference-Neighbourhood Fingerprint (RNF)**. **Candidate Context Analysis (CCA)** compares these representations across groups of candidate materials.


Initial verification shows that the framework reproduced its outputs under the fixed conditions tested and that the tested seed changes did not materially alter the contextual results. Selected benchmark and interpretability tests provide preliminary evidence that the framework can produce coherent, context-sensitive, and inspectable organisation within the candidate groups examined.


The current evidence does not establish that RNF adds useful information beyond conventional material descriptors, improves materials-discovery decisions, predicts material properties, or identifies externally validated material classes.

Shorter descriptions may be used in the README, repository description, presentations, or later publications, but they should not strengthen this position.

## **14. When Claims Should Change**

`CLAIMS.md` describes a particular release and its evidence.

Later experiments may strengthen a claim, weaken it, narrow it, leave it unchanged, or provide evidence against one of the hypotheses.

When this happens, the earlier evidence should remain part of the project record.

A later release should:

1. record the new experiment in the validation evidence;

2. update the relevant hypothesis status;

3. update the claims for the new release; and

4. explain how the new evidence changes the previous position.

This preserves a visible relationship between **what was tested**, **what was observed**, and **what was claimed at the time**.

## **15. v0.1 Claim Summary**

| **Claim** | **Status** |
| :-: | :-: |
| The framework reproduced its outputs under the fixed conditions tested. | **Supported within tested scope** |
| Contextual organisation was robust to the seed variations tested. | **Supported within tested scope** |
| The framework showed coherent and different contextual behaviour in selected benchmark groups. | **Preliminary support** |
| Selected CCA distinctions can be traced to observable RNF and neighbourhood differences. | **Preliminary support** |
| RNF provides useful information beyond conventional descriptors. | **Not established** |
| RNF/CCA improves materials-discovery decisions. | **Not claimed** |
| Hub, Boundary, and Other are validated scientific material classes. | **Not claimed** |

The v0.1 claim is deliberately limited:

**The framework provides a reproducible, reference-relative representation and an inspectable way of comparing candidate materials that behaved coherently in the verification cases examined.**

Whether that representation adds useful information beyond simpler conventional descriptions remains the principal open scientific question.

