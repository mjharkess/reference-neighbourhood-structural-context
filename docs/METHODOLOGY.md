# **Methodology**

## **Reference-Neighbourhood Structural Context Framework**

**Purpose:** To explain what the framework does, why it is being tested, and what can and cannot currently be concluded from it.

## **1. Purpose**

The Reference-Neighbourhood Structural Context Framework is an experimental way of describing and comparing materials.

Most materials analysis starts by describing a material directly, for example through its composition, crystal structure, symmetry, or calculated properties. This framework asks whether something useful can also be learned by looking at the **other materials that appear around it when a reference database is searched in a structured way**.

A material may be described partly by its own characteristics and partly by materials in a pool within a reference population.

The framework creates a **Reference-Neighbourhood Fingerprint (RNF)** for each material. The RNF records the character of the reference materials retrieved around it.

RNFs can then be compared across a group of candidate materials using **Candidate Context Analysis (CCA)**. This allows the framework to ask whether candidates occupy similar or different contexts within the reference population.

The framework also produces auxiliary labels such as **Hub**, **Boundary**, and **Other**. These were more important in earlier versions of the project and are now treated as supporting interpretations rather than the main output.

This document explains the method at a conceptual level. Detailed software behaviour belongs in `ARCHITECTURE.md`, test results in `VALIDATION.md`, and the claims supported by the current evidence in `CLAIMS.md`.

## **2. Research Question**

The project investigates the following broad question:

**Can useful information about a material be obtained from the reference neighbourhood that surrounds it, rather than only from descriptors of the material itself?**

The project does not assume that the answer is yes.

A reference-neighbourhood representation could be reproducible and interesting while still adding little or nothing to simpler conventional material descriptors. The methodology is therefore organised around four separate hypotheses.

## **3. Hypotheses**

### **H1 — Representation Reproducibility**

**Hypothesis:** A stable and reproducible Reference-Neighbourhood Fingerprint can be produced for an individual material.

If the same material is analysed again using the same reference data and settings, the framework should produce the same result.

This is the most basic requirement. If the representation cannot be reproduced, later interpretation has little value.

**Current position:** Initial testing supports H1 within the cases tested. This does not establish reproducibility under every possible configuration or dataset.

### **H2 — Context Sensitivity**

**Hypothesis:** Reference-Neighbourhood Fingerprints change in a meaningful and understandable way when materials occupy different structural contexts within the reference population.

The framework should not simply give every material essentially the same fingerprint, nor should it create differences that cannot be explained.

If two materials receive different contextual representations, it should be possible to inspect the underlying reference neighbourhoods and understand what produced the difference.

**Current position:** Initial tests provide preliminary support for H2. Broader testing is still required.

### **H3 — Comparative Utility**

**Hypothesis:** Reference-Neighbourhood Fingerprints can help identify useful similarities, differences, and organisation within a group of candidate materials.

This is tested mainly through Candidate Context Analysis.

For example, the analysis may indicate that some candidates occupy similar contexts, that another is relatively distinct, or that a candidate that appears similar under one form of description looks different when its reference neighbourhood is considered.

The word **useful** is deliberately limited here. It means useful for organising and examining candidate materials within the analysis, not that the method has been shown to improve real-world materials discovery.

**Current position:** Existing analyses provide preliminary support for H3, but systematic validation is incomplete.

### **H4 — Incremental Information**

**Hypothesis:** Reference-neighbourhood information provides useful information that is not already captured by conventional material descriptors.

This is the most important hypothesis that remains untested.

H1, H2, and H3 could all be supported while H4 is false. The framework might produce reproducible and understandable results but merely reorganise information already available from conventional descriptors.

A separate baseline comparison is therefore required.

**Current position:** H4 has not been established.

## **4. What the Framework Does**

At a high level, the process is:

1. take a candidate material;

2. create a lightweight description of it;

3. search a defined reference population for relevant materials;

4. organise the retrieved materials into a reference neighbourhood;

5. summarise that neighbourhood as a Reference-Neighbourhood Fingerprint;

6. compare fingerprints when analysing a group of candidates; and

7. produce interpretable outputs showing similarities, differences, and other patterns.

The process can be represented simply as:

`Material → Material Profile → Reference Retrieval → RNF → Candidate Context Analysis`

The distinction is between the **material itself** and the **reference neighbourhood constructed around it**.

## **5. Material Profile**

The process starts with a lightweight **Material Profile**.

The profile uses relatively inexpensive information already available to the framework. Depending on the material and source data, this can include:

- composition;

- structural or material family;

- symmetry;

- prototype or related structural grouping;

- coordination and bonding;

- dimensional or physical proxies; and

- other metadata used to retrieve relevant reference materials.

The Material Profile has two purposes: it provides a basic description of the candidate and information that the system can use to search the reference population.

The profile is not intended to be a complete scientific description of the material. Missing information remains missing rather than being treated as evidence.

Some classifications used in the profile, such as material family or prototype grouping, are produced by rules within the framework. These should be treated as working classifications, not scientific ground truth.

## **6. Reference Population and Neighbourhood**

The framework compares a candidate with a defined **reference corpus**. In the current project this is based on the JARVIS materials dataset.

The framework can also analyse an externally supplied material against this reference population. An external material does not have to be added to the reference corpus itself.

The system retrieves reference materials in several ways rather than searching for only one kind of similarity. Some searches favour close structural or family relationships, while others provide contrast or broader background examples.

The purpose is to build a neighbourhood with enough variation to show how the candidate sits within the reference population.

The exact retrieval rules, pool sizes, limits, and software settings are implementation details documented separately. They matter for reproducibility but are not necessary for understanding the central methodology.

### **Reference dependence**

An RNF is **not an intrinsic property of a material**.

It describes the material relative to:

- the reference corpus;

- the available data;

- the retrieval method; and

- the configuration of the framework.

If the reference population or methodology changes significantly, the RNF may also change.

The relevant dataset version and analytical configuration must therefore be recorded when results are produced.

## **7. Reference-Neighbourhood Fingerprint**

The **Reference-Neighbourhood Fingerprint (RNF)** is the main per-material output of the framework.

It summarises the neighbourhood retrieved around a candidate and contains enough information to address questions such as:

- Which reference materials were retrieved?

- Which types of reference material dominate the neighbourhood?

- How concentrated or diverse is the neighbourhood?

- How strongly does the candidate match different parts of the retrieved population?

- Are there competing or contrasting groups around the candidate?

- Which parts of the neighbourhood are responsible for the resulting representation?

The detailed implementation contains more fields and measurements than are described here. Those details are useful for software execution and technical investigation but are not necessary to understand the methodological claim.

The RNF is a **relational representation**: it describes the candidate through the pattern of reference materials surrounding it.

It should not be interpreted as an experimentally measured property or as proof that the candidate belongs to a particular scientific class.

## **8. Comparing Materials**

Two candidates can be compared using their reference-neighbourhood information.

The framework considers whether their neighbourhoods contain similar reference materials and have similar overall characteristics. It also uses a smaller summary of structural-context information derived during analysis.

These sources are combined to produce a measure of **contextual similarity**.

A high contextual similarity means that two candidates occupy similar positions according to the framework. A low similarity means that their contexts differ.

This does **not** automatically mean that the materials have similar or different physical properties. It means that they appear similar or different under this particular analytical representation.

The analysis therefore retains information that allows the user to inspect why two materials are judged similar or different.

## **9. Candidate Context Analysis**

**Candidate Context Analysis (CCA)** applies the framework to a group of candidate materials.

Its purpose is not to declare which material is scientifically “best”. It is to help organise a candidate set and identify relationships that may deserve further investigation.

CCA can be used to identify:

- candidates with similar contextual representations;

- candidates that are relatively distinct;

- groups of candidates with similar contexts;

- candidates that appear redundant within the analysed group;

- representative examples from a group; and

- cases where different forms of comparison disagree.

For example, two materials may appear similar from their direct profiles but have noticeably different reference neighbourhoods. Alternatively, materials with different direct descriptions may occupy similar reference-relative contexts.

Such disagreement is not automatically scientifically important. It is a **signal for investigation**.

CCA therefore provides a way of asking:

**Within this candidate set and this reference population, which materials occupy similar or different contexts, and what evidence explains those relationships?**

The resulting groups or clusters are analytical outputs. They should not automatically be treated as natural material classes, phases, or experimentally established categories.

## **10. Hub, Boundary, and Other**

Earlier versions of the project focused more heavily on assigning contextual roles. These roles remain available as an auxiliary interpretation layer.

### **Hub**

A **Hub** is intended to represent a material surrounded by a comparatively coherent reference neighbourhood.

### **Boundary**

A **Boundary** is intended to represent a material whose neighbourhood shows meaningful contrast between different contextual groups or regimes.

### **Other**

**Other** is used when the evidence does not satisfy the framework’s criteria for Hub or Boundary.

The framework also records secondary diagnostics for ambiguous, mixed, weak, bridge-like, outlier-like, or otherwise unusual cases.

These labels are useful for interpretation, but they are **not externally validated scientific material classes** and should not be treated as the primary scientific result of v0.1.

## **11. Evidence Before Interpretation**

A central design principle is to separate **evidence generation** from **interpretation**.

The framework first constructs profiles, retrieves reference materials, records neighbourhood evidence, and creates fingerprints. It then produces interpretations such as similarity, clustering, distinctiveness, or Hub/Boundary labels.

This separation allows an interpretation to be traced back to the evidence that produced it.

A user should be able to ask not merely:

“What label did the system give this material?”

but:

“What evidence caused the system to reach that interpretation?”

This does not guarantee that the interpretation is scientifically correct. It makes the framework’s reasoning more inspectable and testable.

## **12. Verification and Validation**

The project distinguishes between **verification** and broader **validation**.

Verification asks whether the software and representation behave as intended.

Validation asks whether the representation is scientifically useful for the claims being made.

The current verification programme includes four main tests:

### **RV-01 — Repeatability**

Checks whether the same analysis under the same conditions produces the same result.

This primarily provides evidence for H1.

### **RV-02 — Seed Robustness**

Checks how much results change when controlled randomisation settings are changed.

This helps determine whether results are reasonably stable rather than dependent on an arbitrary computational choice.

### **RV-03 — Known-Control Behaviour**

Uses selected control groups to check whether the framework responds differently to relatively uniform and more contextually varied examples.

This provides evidence relevant to H2 and H3.

### **RV-04 — Interpretability**

Examines selected cases and traces differences in the final analysis back to the underlying profiles and reference neighbourhoods.

This tests whether outputs can be investigated rather than appearing as unexplained numerical results.

Detailed tests, acceptance criteria, and results are recorded in `VALIDATION.md`.

## **13. Current Evidence Position**

The four hypotheses do not have the same evidence status.

| **Hypothesis** | **Current position** |
| :-: | :-: |
| **H1 — Representation Reproducibility** | Supported within the scope tested |
| **H2 — Context Sensitivity** | Preliminary support |
| **H3 — Comparative Utility** | Preliminary support; further validation required |
| **H4 — Incremental Information** | Not established |

The project should therefore not simply be described as “validated”.

The current evidence supports a narrower statement: the framework can generate reproducible reference-neighbourhood representations under the tested conditions, those representations show interpretable differences in selected tests, and they can be used to organise candidate cohorts.

This is useful evidence, but it is not the end of the scientific evaluation.

## **14. Conventional-Descriptor Baseline**

The next important test is a comparison with conventional material descriptors, intended primarily to address H4.

The central question is:

**Does the RNF reveal useful organisation that is not already available from a simpler conventional representation of the same candidates?**

The same candidate group should be analysed using:

1. conventional material descriptors;

2. the reference-neighbourhood representation; and

3. where useful, the combined representation.

The resulting similarity patterns and candidate groupings can then be compared.

Several outcomes are possible.

### **Strong agreement**

If conventional descriptors and RNFs produce essentially the same organisation, this would weaken the claim that RNFs provide additional information.

The RNF might still be useful as an interpretable relational representation, but a strong claim of incremental information would not be justified.

### **Systematic and explainable differences**

If the RNF repeatedly identifies differences that conventional descriptors do not, and those differences can be traced to understandable structural context, this would provide evidence in favour of H4.

It would not by itself prove that the RNF is superior. Further testing would still be required.

### **Unstable or unexplained differences**

If the RNF differs from the baseline but the differences are inconsistent or cannot be explained, this would weaken the case for H4 and may reveal weaknesses in the method.

The v0.1 methodology should remain fixed when this comparison is performed. Any changes suggested by the result should form a later version rather than being retrospectively inserted into v0.1.

## **15. What the Current Method Does Not Claim**

The v0.1 framework does **not** establish that:

- RNFs are better than conventional material descriptors;

- RNFs contain information unavailable from conventional descriptors;

- every cluster produced by CCA corresponds to a real physical or crystallographic class;

- the method works equally well across all types of materials;

- Hub, Boundary, and Other are scientifically validated material categories;

- contextual similarity predicts material properties;

- contextual difference establishes the physical cause of that difference; or

- the framework improves real-world materials discovery or candidate selection.

These are not minor qualifications. They define the boundary of what can reasonably be claimed from the current evidence.

## **16. Main Limitations**

### **Reference dependence**

Results depend on the reference population. Changing the reference dataset can change the neighbourhood and therefore the RNF.

### **Retrieval dependence**

Results also depend on how reference materials are selected. Retrieval rules are part of the methodology and must be recorded.

### **Input-data limitations**

The framework works with the information available to it. It cannot recover physical information absent from the underlying data merely by reorganising that data.

### **Analytical outputs are not ground truth**

Similarity scores, clusters, contextual roles, and other outputs are products of the framework. They are evidence for investigation, not direct experimental observations.

### **Limited validation**

Current verification uses selected controls and candidate groups. It does not demonstrate universal performance across materials space.

### **Parameter sensitivity**

The method contains settings, weights, and thresholds. Their wider sensitivity has not yet been systematically tested.

### **Conventional baseline pending**

H4 remains untested until the conventional-descriptor comparison is completed.

### **Downstream benefit pending**

The project has not yet shown that the framework improves property prediction, experimental prioritisation, candidate selection, or another real-world materials-discovery task.

## **17. Methodological Position of v0.1**

The purpose of v0.1 is to establish a clear and reproducible starting point before the strongest hypotheses are tested.

The release freezes:

- the basic idea of reference-neighbourhood representation;

- the method used to construct RNFs;

- the Candidate Context Analysis approach;

- the initial verification evidence; and

- the limits placed on the claims.

If the later conventional-descriptor comparison supports H4, that result can be reported against a methodology that existed before the result was known.

If it does not support H4, that result is equally informative.

The value of the v0.1 release does not depend on demonstrating that the framework is superior. Its purpose is to make the method sufficiently clear, reproducible, and testable that the central hypotheses can be evaluated without changing the rules after seeing the result.

## **18. Summary**

The Reference-Neighbourhood Structural Context Framework tests whether a material can be usefully described partly through the reference materials that surround it.

Its main per-material representation is the **Reference-Neighbourhood Fingerprint**. Its main cohort-level analysis is **Candidate Context Analysis**.

The project tests four hypotheses:

- **H1:** the fingerprint can be reproduced;

- **H2:** it responds meaningfully to differences in structural context;

- **H3:** it can help organise and compare candidate materials; and

- **H4:** it provides useful information beyond conventional descriptors.

Current evidence supports H1 within the tested scope and provides preliminary support for H2 and H3. H4 remains untested.

The framework should therefore be treated as an experimental and inspectable method for representing reference-relative material context, not as a proven replacement for conventional materials representations or a validated materials-discovery system.

