# Technical Methodology Supplement

## Reference-Neighbourhood Structural Context Framework

**Document status:** Technical supplement to the v0.1 Methodology  
**Companion document:** `METHODOLOGY.md`  
**Purpose:** To record methodological definitions, parameters, comparison rules, reliability controls, and cohort-analysis procedures that are intentionally omitted from the plain-English Methodology.

---

## 1. Purpose and document boundary

The main `METHODOLOGY.md` explains the scientific idea, hypotheses, evidence position, limitations, and intended interpretation of the Reference-Neighbourhood Structural Context Framework in plain English.

This supplement provides the additional technical detail needed to understand how the methodology is operationalised. It does not replace the main Methodology and should not be read as a software-architecture document.

The intended document split is:

- `METHODOLOGY.md` — what the method is, why it is being tested, and what can currently be concluded;
- `TECHNICAL_METHODOLOGY_SUPPLEMENT.md` — technical definitions, analytical rules, parameters, calculations, and methodological controls;
- `ARCHITECTURE.md` — software components, implementation structure, data flow, and code responsibilities;
- `VALIDATION.md` — verification and validation tests, acceptance criteria, results, and evidence;
- `CLAIMS.md` — claims justified by the evidence available for the release.

Where implementation behaviour and this document differ, the frozen release implementation and its recorded provenance determine what was actually executed. Such a difference should be treated as a documentation or version-control issue rather than silently reconciled.

---

## 2. Technical terminology and representations

The framework uses three related but distinct representations.

### 2.1 Material Profile

The **Material Profile**, denoted conceptually as `P(M)`, is the broad intrinsic or query-centred representation of material `M`.

It contains inexpensive available information concerning composition, structural or material family, symmetry, physical proxies, dimensional characteristics, coordination, bonding, metadata, and retrieval keys.

Its main methodological functions are to:

1. describe the query material before reference-neighbourhood analysis;
2. provide inputs for reference retrieval and candidate-pool construction; and
3. provide interpretive context for downstream analysis.

It is not the Reference-Neighbourhood Fingerprint and should not be conflated with the smaller Structural Context Profile.

### 2.2 Structural Context Profile

The **Structural Context Profile (SCP)**, denoted `S(M)`, is a compact four-dimensional derived representation comprising:

- local context support;
- structural regime contrast;
- neighbourhood coherence; and
- structural context diversity.

The SCP is used as one component of candidate-to-candidate comparison.

### 2.3 Reference-Neighbourhood Fingerprint

The **Reference-Neighbourhood Fingerprint (RNF)**, denoted conceptually as `R(M)`, is the detailed relational representation generated from the structured reference neighbourhood retrieved around the query.

For query material `M`, reference corpus `D`, retrieval configuration `θ_R`, and fingerprint configuration `θ_F`, the representation can be written conceptually as:

`RNF(M | D, θ_R, θ_F)`

This notation is important. An RNF is conditional on the reference corpus and methodology. It is not an invariant physical property of the material.

### 2.4 Similarity measures

The framework distinguishes:

- **Reference-Neighbourhood Similarity (RNS):** similarity between two RNFs;
- **Structural Context Profile similarity:** similarity between two SCPs; and
- **Combined Context Similarity (CCS):** the configured combination of SCP similarity and RNS used for most cohort-level analysis.

These quantities should not be treated as interchangeable.

---

## 3. Material profiling

### 3.1 Inputs

A query may enter the framework as:

1. an existing JARVIS material identifier; or
2. an externally supplied material registered through the external-material workflow.

An external material can be analysed as a query without automatically becoming part of the reference corpus. This prevents the material being evaluated from silently altering the population against which it is contextualised.

### 3.2 Descriptor groups

Where available, the Material Profile organises inexpensive information into the following groups:

- composition;
- material and structural family;
- symmetry;
- physical proxies;
- dimensional descriptors;
- coordination descriptors; and
- bonding descriptors.

Missing information remains missing. Absence of a descriptor is not interpreted as positive or negative evidence about structural context.

### 3.3 Derived classifications

The profiling stage may derive working classifications including:

- material family;
- formula family;
- prototype;
- prototype family;
- structure variant; and
- classification confidence.

These are operational classifications used for retrieval and interpretation. They are not treated as scientific ground truth.

### 3.4 Retrieval keys

The profile derives retrieval keys where the required information is available. These can include:

- family key;
- material-family key;
- formula-family key;
- structure-variant key;
- chemical-system key;
- composition key;
- prototype key;
- symmetry key; and
- a simple stability or known-material indicator.

The use of multiple keys allows retrieval to represent several forms of relatedness rather than forcing all reference selection through a single similarity definition.

---

## 4. Reference corpus and candidate-pool construction

### 4.1 Reference-relative analysis

Structural context is defined relative to a specified reference corpus. The corpus name, version, relevant preprocessing state, and descriptor provenance are therefore part of the analytical conditions.

The query is excluded from reference retrieval where necessary to prevent trivial self-retrieval.

### 4.2 Retrieval pools

The current methodology constructs five functionally different pools:

1. **same-family pool**;
2. **adjacent-family pool**;
3. **boundary/contrast pool**;
4. **wildcard pool**; and
5. **negative-control pool**.

These pools are not five independent estimates of one quantity. Each has a different methodological purpose.

#### Same-family pool

The same-family pool seeks relatively close structural or compositional references using the available family classification and inexpensive evidence. It is intended to characterise local contextual support and variation within a related regime.

Where appropriate, exact same-formula matches are restricted so that the pool does not collapse into a trivial collection of compositionally identical materials.

#### Adjacent-family pool

The adjacent-family pool broadens retrieval beyond the closest family assignment while retaining meaningful structural or compositional relatedness. It is intended to expose neighbouring regimes.

Exact structural duplication may be restricted where appropriate so that this pool contributes information not already supplied by the same-family pool.

#### Boundary/contrast pool

The boundary/contrast pool deliberately retrieves informative contrast. Dissimilarity is therefore not automatically treated as retrieval failure.

Its purpose is to expose alternative nearby or relevant regimes and provide evidence about how the query differs from them.

#### Wildcard pool

The wildcard pool provides a deterministic broader sample outside the principal selected pools, subject to the implemented eligibility rules.

It reduces the extent to which the fingerprint is determined only by assumptions embedded in family-based and contrast-based retrieval.

#### Negative-control pool

The negative-control pool deliberately selects references with unrelated chemistry and/or family context.

It acts as a background control. Negative-control references remain recorded in the RNF but are excluded from default Reference-Neighbourhood Similarity. They can be included through an explicit analysis option.

### 4.3 Deterministic selection and provenance

Eligible references are ranked using inexpensive selection evidence and deterministic ordering. Stable tie-breaking is used where otherwise equivalent candidates need to be ordered.

For selected references, the framework records information including:

- pool membership;
- rank;
- selection score; and
- selection reason.

The retrieval result therefore preserves not only which references were selected but also how they entered the neighbourhood.

### 4.4 Pool overlap

The pools are not assumed to be independent. The framework records:

- reference membership by pool;
- references appearing in multiple pools;
- pairwise pool overlap;
- total unique reference count; and
- pool-independence information used in downstream reliability assessment.

Overlap is treated as observable methodological information rather than silently removed.

---

## 5. Reference-Neighbourhood Fingerprint contents

The RNF retains both individual reference identity and aggregate neighbourhood structure.

### 5.1 Provenance

Where available, fingerprint provenance includes:

- query-profile schema;
- candidate-pool schema;
- reference-corpus name and version;
- reference-corpus material count;
- descriptor-cache provenance;
- candidate-pool seed; and
- evidence or fingerprint schema version.

### 5.2 Query metadata

The RNF records compact query metadata such as:

- material identifier;
- formula;
- material and dataset type;
- chemical system;
- composition family;
- material family;
- formula family;
- prototype family;
- structure variant;
- space group; and
- crystal system.

These fields support interpretation but do not constitute the main relational content of the RNF.

### 5.3 Pool-level representation

For each pool, the fingerprint can record:

- pool availability;
- retrieved row count;
- unique-reference count;
- duplicate-reference count;
- ranked reference identifiers;
- compact neighbour records;
- contextual-variable distributions;
- query-match rates;
- pool-context features;
- dominant contextual categories; and
- missing-data information.

### 5.4 Ranked identity

Reference identities are retained in ranked order. The ranking allows highly ranked shared references to contribute more strongly to later identity comparison than references appearing much further down the list.

The fingerprint also records the union of unique reference identifiers, reference-to-pool membership, multi-pool references, and pool overlap.

### 5.5 Categorical distributions

Where available, categorical distributions are recorded for variables including:

- chemical system;
- composition family;
- material family;
- formula family;
- prototype family;
- structure variant;
- space-group number;
- crystal-system code;
- selection reason; and
- stability label.

This allows two candidates to have similar neighbourhood structure even if they do not retrieve exactly the same material identifiers.

### 5.6 Numerical summaries

Pool-level summaries can include:

- candidate selection score;
- query-element overlap;
- symmetry distance;
- energy above hull; and
- formation energy per atom.

These are retained where available.

### 5.7 Query-match rates

For each pool, the RNF can record the proportion of references matching the query on dimensions including:

- chemical system;
- composition family;
- material family;
- formula family;
- prototype family;
- structure variant;
- space group; and
- crystal system.

### 5.8 Pool-context features

Derived pool-level features include, where available:

- query-similarity score;
- pool-diversity score;
- structural-regime-diversity score;
- missing-value rate for required columns;
- fraction satisfying the implemented energy-above-hull stability criterion; and
- known-synthesised rate.

### 5.9 Explainability summaries

The RNF includes non-scoring summaries of dominant contextual regimes and classification coverage.

These summaries do not alter retrieval or similarity scores. Their function is to make the representation inspectable after it has been generated.

---

## 6. Reference-Neighbourhood Similarity

Candidate Context Analysis compares RNFs through three principal components:

1. reference-identity similarity;
2. reference-distribution similarity; and
3. reference-context-feature similarity.

The components are calculated by pool and aggregated using configured pool weights.

### 6.1 Default pool weights

| Pool | Default weight |
|---|---:|
| Same family | 0.35 |
| Adjacent family | 0.20 |
| Boundary/contrast | 0.30 |
| Wildcard | 0.15 |
| Negative control | 0.00 |

The negative-control pool is therefore excluded from default RNS. An explicit alternative mode may include it with a small weight and rebalance the remaining pool weights.

These values are methodological parameters, not physical constants.

### 6.2 Reference-identity similarity

Within each active pool, a reference at rank `r` receives decreasing rank importance proportional to:

`1 / log2(r + 2)`

The two ranked reference lists are compared using weighted Jaccard similarity.

The implementation also calculates ordinary Jaccard similarity across the union of all unique retrieved reference identifiers.

The final identity component is:

`Identity similarity = 0.80 × pool-aware ranked similarity + 0.20 × all-reference Jaccard similarity`

This preserves both pool-specific ranked overlap and broader identity overlap.

### 6.3 Reference-distribution similarity

The framework separately compares categorical neighbourhood distributions. The current fields and default within-pool weights are:

| Context field | Weight |
|---|---:|
| Composition family | 0.10 |
| Material family | 0.10 |
| Formula family | 0.15 |
| Prototype family | 0.20 |
| Structure variant | 0.20 |
| Space-group number | 0.15 |
| Crystal-system code | 0.10 |

Distribution similarity is based on Jensen-Shannon divergence transformed to a zero-to-one similarity scale.

Field-level similarities are aggregated within each pool and then across pools using the active pool weights.

### 6.4 Reference-context-feature similarity

The third component compares compact numerical characteristics of the retrieved pools.

It includes available query-match rates and pool-context features such as:

- query-similarity score;
- pool-diversity score;
- structural-regime-diversity score;
- missing-value rate;
- stability fraction;
- known-synthesised rate; and
- pool size.

For bounded numerical features, similarity is based on absolute difference. Pool size is compared proportionally.

Available feature similarities are averaged within each pool and then combined using the active pool weights.

### 6.5 Overall RNS

The default combination is:

`RNS = 0.55 × identity similarity + 0.30 × distribution similarity + 0.15 × context-feature similarity`

The weights are configurable.

The current method therefore places greatest weight on whether candidates retrieve the same ranked references, while still allowing similar contextual distributions and pool characteristics to contribute where exact reference identity differs.

---

## 7. Structural Context Profile and Combined Context Similarity

### 7.1 SCP similarity

The SCP comparison uses the four bounded measurements:

- local context support;
- structural regime contrast;
- neighbourhood coherence; and
- structural context diversity.

Similarity is calculated from the root-mean-square difference between available measurements and transformed to a zero-to-one scale.

SCP similarity is deliberately retained separately from RNS.

### 7.2 Combined Context Similarity

The default cohort-level comparison is:

`CCS = 0.35 × SCP similarity + 0.65 × RNS`

The corresponding distance is:

`Combined Context Distance = 1 - CCS`

The RNF contribution is required to remain non-zero.

Because CCS combines two representations, outputs based on CCS should not be described as results of the RNF alone. The separate component scores are retained so that their respective contributions can be inspected.

### 7.3 Chemistry baseline

The analysis also calculates a lightweight chemistry-baseline similarity using chemical-system and related classification information.

This is a diagnostic comparator only. It is not the conventional-descriptor baseline required to test H4.

### 7.4 Profile-neighbourhood discordance

The framework records the absolute difference between SCP similarity and RNS.

Descriptive categories distinguish cases such as:

- high SCP similarity but substantially lower RNS;
- lower SCP similarity but high RNS;
- SCP similarity exceeding RNS;
- RNS exceeding SCP similarity; and
- broadly aligned representations.

Discordance is an analytical target because it identifies cases in which compact profile information and detailed relational information organise candidates differently.

It is not evidence, by itself, that either representation is scientifically superior.

---

## 8. Reliability and evidence sufficiency

Candidate-level reliability incorporates information concerning:

- evidence sufficiency;
- retrieval completeness;
- pool independence;
- profile confidence; and
- completeness of the four SCP measurements.

Pairwise reliability is derived from the reliability of the two candidates.

The framework also records whether sufficient fingerprint explainability information exists to interpret a pairwise result.

Candidates failing configured reliability requirements may be withheld from clustering while remaining available for inspection. This prevents incomplete or poorly supported representations from silently determining cohort structure.

Reliability measures qualify the analytical result. They do not transform a weakly supported comparison into a strongly supported one.

---

## 9. Candidate Context Analysis

Candidate Context Analysis (CCA) applies the comparison framework to a defined candidate cohort.

### 9.1 Pairwise comparison

For each eligible candidate pair, CCA calculates or records:

- SCP similarity;
- reference-identity similarity;
- reference-distribution similarity;
- reference-context-feature similarity;
- RNS;
- CCS;
- chemistry-baseline similarity;
- pair reliability;
- explainability confidence; and
- profile-neighbourhood discordance.

These pairwise values form the basis of nearest-neighbour analysis, clustering, distinctiveness, redundancy, and several diagnostic outputs.

### 9.2 Contextual nearest neighbours

For each candidate, other cohort members are ranked by CCS.

The nearest-neighbour output retains the principal component similarities rather than reporting only the combined value. This allows a high combined similarity to be distinguished from a superficially similar score produced by conflicting component behaviour.

Nearest neighbours are nearest under this framework. They are not necessarily nearest under crystallographic distance, chemistry, physical properties, or another external representation.

### 9.3 Contextual clustering

CCA converts CCS into Combined Context Distance and applies hierarchical agglomerative clustering using average linkage.

If the analyst specifies the number of clusters, that number is used subject to cohort size.

If not, the implementation evaluates candidate cluster counts from two up to the configured maximum and selects the solution with the highest silhouette score calculated from the precomputed contextual-distance matrix.

The current default maximum number of clusters is **8**.

The resulting groups are contextual clusters under the implemented representation. They are not automatically material families, crystallographic classes, phases, or other ground-truth categories.

### 9.4 Cluster summaries

For each cluster, the analysis can report:

- cluster size;
- mean within-cluster similarity;
- union of retrieved reference identifiers;
- dominant composition family;
- dominant formula family;
- median candidate reliability; and
- median values of the four SCP measurements.

### 9.5 Cluster representatives

A representative is selected as the candidate with the lowest mean contextual distance to the other cluster members. Reliability acts as a secondary preference where required.

This is a medoid-like contextual exemplar. It is not necessarily the most stable, experimentally important, synthesizable, physically typical, or scientifically valuable material.

### 9.6 Contextual distinctiveness

For each candidate, the framework calculates:

- distance to the nearest candidate;
- mean distance to a configured number of nearest candidates; and
- a within-cohort percentile of contextual distinctiveness.

Distinctiveness is explicitly cohort-relative. Adding or removing candidates can change the percentile and its interpretation.

A high distinctiveness score does not establish intrinsic scientific novelty.

### 9.7 Redundancy

Under the current default configuration, a candidate pair is treated as contextually redundant only when all three conditions hold:

- `CCS ≥ 0.90`;
- `SCP similarity ≥ 0.80`; and
- `RNS ≥ 0.80`.

Pairs satisfying the criteria are connected into redundancy groups.

This deliberately requires agreement across the combined representation and both major components. Contextual redundancy does not imply crystallographic identity or scientific interchangeability.

### 9.8 Inter-cluster candidates

For each clustered candidate, the framework compares:

- mean similarity to the assigned cluster; and
- mean similarity to the most similar alternative cluster.

The difference is the cluster-membership margin.

Candidates with a margin less than or equal to the configured transition threshold are labelled inter-cluster candidates. The current default threshold is **0.10**.

This identifies ambiguous positions under the contextual clustering representation. It does not establish a physical transition state, bridge material, or scientifically meaningful boundary.

### 9.9 Explainability

Pairwise explanation can identify whether similarity is driven primarily by:

- SCP similarity;
- shared reference identity;
- similar contextual distributions;
- similar pool-level contextual features; or
- a combination of these.

Cluster-level explanation can use representative candidates and RNF summaries to describe dominant contextual regimes, family or prototype organisation, symmetry organisation, neighbourhood diversity, and within-cluster similarity.

These explanations expose the evidence underlying the analytical result. They do not convert an analytical grouping into an externally validated scientific conclusion.

---

## 10. Auxiliary role-prior analysis

The earlier development of the project focused more strongly on contextual roles. These remain available but are auxiliary to the RNF/CCA methodology.

### 10.1 Hub

A **Hub** interpretation is intended to indicate a comparatively coherent reference neighbourhood, for example where evidence shows strong family or prototype coherence and limited internal variation under the implemented metrics.

### 10.2 Boundary

A **Boundary** interpretation is intended to indicate meaningful contrast or separation between relevant contextual regimes or candidate pools.

### 10.3 Other

**Other** is used where evidence does not satisfy the acceptance criteria for Hub or Boundary. It should not be interpreted as a homogeneous scientific class.

### 10.4 Secondary diagnostics

The auxiliary layer can also record descriptors concerning:

- ambiguity;
- mixed evidence;
- bridge-like behaviour;
- weak evidence;
- polymorph sensitivity;
- outlier-like behaviour;
- family ambiguity; and
- related evidence-quality or contextual conditions.

Detailed scoring logic belongs with the frozen implementation and architecture/source documentation. The scientific status of these outputs is deliberately limited: they are contextual interpretations, not externally validated material classes.

---

## 11. Methodological parameters and sensitivity

The framework contains configurable parameters, including:

- retrieval and pool settings;
- pool weights;
- RNS component weights;
- SCP/RNF combination weights;
- reliability thresholds;
- clustering limits;
- redundancy thresholds; and
- transition thresholds.

These values are methodological choices rather than physical constants.

The current v0.1 configuration should be frozen for experiments intended to evaluate the central hypotheses. Future sensitivity analysis should test whether principal conclusions remain stable under reasonable parameter perturbation.

Useful sensitivity targets include:

- nearest-neighbour relationships;
- contextual clusters;
- distinctiveness rankings;
- redundancy groups;
- profile-neighbourhood discordance; and
- inter-cluster classifications.

The method is also reference-corpus dependent. Future robustness analysis should consider controlled reference subsampling, corpus expansion, database-version changes, and the effect of highly represented material families.

---

## 12. Provenance and reproducibility requirements

A reproducible analysis should identify, at minimum:

- query material and input representation;
- reference corpus and corpus version;
- Material Profile and descriptor state;
- retrieval and candidate-pool configuration;
- seed and deterministic tie-breaking behaviour where applicable;
- RNF schema and fingerprint configuration;
- pairwise comparison and similarity configuration;
- candidate cohort for cohort-relative outputs;
- clustering settings;
- thresholds; and
- reliability settings.

RNFs or CCA outputs generated under materially different configurations should not be assumed to be directly interchangeable without an explicit compatibility or sensitivity assessment.

This requirement follows directly from the reference-relative nature of the framework.

---

## 13. Computational scope

CCA currently performs exact pairwise candidate comparison and therefore scales approximately quadratically with cohort size.

The implementation includes a safety limit for exact analysis, and full square similarity matrices may be suppressed for large cohorts.

The present method should therefore be understood primarily as a candidate-cohort analysis framework, not as an unrestricted all-against-all comparison method for very large materials databases.

Scaling to substantially larger candidate populations would require additional computational design.

---

## 14. Verification, validation, and methodological freeze

The framework separates verification from broader scientific validation.

The initial verification programme comprises:

- **RV-01 — Repeatability:** same input and configuration should reproduce the same output;
- **RV-02 — Seed Robustness:** controlled seed changes are used to assess representation stability;
- **RV-03 — Known-Control Behaviour:** selected controls test whether the method responds differently to relatively uniform and contextually varied cases; and
- **RV-04 — Interpretability:** selected differences are traced back to profiles, RNFs, and retrieved neighbourhood evidence.

Detailed acceptance criteria and results belong in `VALIDATION.md`.

The planned conventional-descriptor baseline is a separate experiment intended principally to test H4. The v0.1 methodology should remain fixed when that comparison is performed. Changes suggested by the result should be introduced in a later version rather than retrospectively modifying the method used to generate the baseline result.

---

## 15. Interpretation boundaries

The technical machinery described here does not change the claim boundaries stated in the main Methodology.

In particular:

- an RNF is reference-relative, not an intrinsic material property;
- high CCS does not establish similarity of physical properties;
- low CCS does not establish a physical cause of difference;
- contextual clusters are analytical groups, not automatically natural scientific classes;
- contextual distinctiveness is not intrinsic novelty;
- contextual redundancy is not scientific interchangeability;
- inter-cluster status is not proof of a physical transition or bridge state;
- role-prior labels are auxiliary interpretations;
- parameter values and thresholds require sensitivity evaluation;
- H4 remains dependent on a separate conventional-descriptor baseline; and
- downstream materials-discovery benefit has not been established.

The purpose of the technical specification is therefore not to strengthen the scientific claims. It is to make the analytical procedure sufficiently explicit that the claims, tests, and future comparisons can be understood and reproduced.
