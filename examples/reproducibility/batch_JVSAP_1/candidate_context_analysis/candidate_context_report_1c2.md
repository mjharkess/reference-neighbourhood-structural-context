# Candidate Context Analysis: Phase 1C.2

## Scope

This report compares candidates through both their Structural Context Profile measurements and the reference neighbourhoods that produced those measurements. It is reference-corpus dependent and does not predict physical performance, intrinsic novelty, synthesis success, or scientific value.

## Run summary

- Input candidates: **10**
- Compatible fingerprints: **10**
- Candidates included in clustering: **10**
- Selected clusters: **1**
- Redundancy pairs: **45**
- Reference IDs represented across analysed candidates: **1632**

## Similarity model

Combined context similarity = 0.35 × profile similarity + 0.65 × reference-neighbourhood similarity.

Reference-neighbourhood similarity combines ranked reference identity (0.55), context-distribution similarity (0.30), and pool-feature similarity (0.15); these three weights are normalised internally.

Negative controls are excluded from the default neighbourhood similarity.

## Cluster summary

| cluster_id | cluster_size | representative_candidate_id | mean_within_cluster_similarity | unique_reference_union_count | dominant_composition_family | dominant_formula_family |
|---|---|---|---|---|---|---|
| 1 | 10 | JVASP-119589 | 1.0000 | 1632 | oxide | AB2C4D7 |

## Cluster representatives

| cluster_id | representative_candidate_id | representative_formula | mean_distance_to_cluster_members | candidate_reliability |
|---|---|---|---|---|
| 1 | JVASP-119589 | Li7Mn2Co3O12 | 0.0000 | 0.8844 |

## Strongest contextual redundancy pairs

| candidate_a | candidate_b | combined_context_similarity | profile_similarity | reference_neighbourhood_similarity | chemistry_baseline_similarity | pair_reliability |
|---|---|---|---|---|---|---|
| JVASP-119589 | JVASP-122407 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143116 | JVASP-118994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143566 | JVASP-140218 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143566 | JVASP-119423 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143566 | JVASP-144808 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143566 | JVASP-142153 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-143566 | JVASP-118994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-145157 | JVASP-140218 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-145157 | JVASP-119423 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-145157 | JVASP-144808 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-145157 | JVASP-142153 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-145157 | JVASP-118994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-140218 | JVASP-119423 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-140218 | JVASP-144808 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-140218 | JVASP-142153 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-140218 | JVASP-118994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-119423 | JVASP-144808 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-119423 | JVASP-142153 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-119423 | JVASP-118994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |
| JVASP-144808 | JVASP-142153 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.8844 |

## Profile–neighbourhood discordance

These pairs are important because similar final profile scores can conceal different reference neighbourhoods, and vice versa.

| candidate_a | candidate_b | profile_similarity | reference_neighbourhood_similarity | profile_neighbourhood_discordance | discordance_type | pair_reliability |
|---|---|---|---|---|---|---|
| JVASP-119589 | JVASP-122407 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143116 | JVASP-118994 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143566 | JVASP-140218 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143566 | JVASP-119423 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143566 | JVASP-144808 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143566 | JVASP-142153 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-143566 | JVASP-118994 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-145157 | JVASP-140218 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-145157 | JVASP-119423 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-145157 | JVASP-144808 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-145157 | JVASP-142153 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-145157 | JVASP-118994 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-140218 | JVASP-119423 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-140218 | JVASP-144808 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-140218 | JVASP-142153 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-140218 | JVASP-118994 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-119423 | JVASP-144808 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-119423 | JVASP-142153 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-119423 | JVASP-118994 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |
| JVASP-144808 | JVASP-142153 | 1.0000 | 1.0000 | 0.0000 | aligned | 0.8844 |

## Most contextually distinctive candidates

| candidate_id | nearest_candidate_distance | mean_distance_to_k_nearest | contextual_distinctiveness_percentile |
|---|---|---|---|
| JVASP-119589 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-122407 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-143116 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-143566 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-145157 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-140218 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-119423 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-144808 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-142153 | 0.0000 | 0.0000 | 0.5500 |
| JVASP-118994 | 0.0000 | 0.0000 | 0.5500 |

## Inter-cluster candidates

_None._

## Candidate-relative coverage

- Effective cluster count: **1.000**
- Mean unique references per candidate: **1632.0**
- Median unique references per candidate: **1632.0**

## Cluster-count diagnostics

_None._

## Similarity explainability

The similarity score is unchanged. The confidence and decomposition fields below describe how strongly the available fingerprint evidence supports each comparison.

| candidate_a | candidate_b | combined_context_similarity | similarity_confidence_label | context_signature_agreement_fraction | contextual_agreements | contextual_disagreements | entropy_interpretation | dominant_similarity_driver | scientific_interpretation |
|---|---|---|---|---|---|---|---|---|---|
| JVASP-119589 | JVASP-122407 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143116 | JVASP-118994 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143566 | JVASP-140218 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143566 | JVASP-119423 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143566 | JVASP-144808 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143566 | JVASP-142153 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-143566 | JVASP-118994 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-145157 | JVASP-140218 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-145157 | JVASP-119423 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-145157 | JVASP-144808 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-145157 | JVASP-142153 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-145157 | JVASP-118994 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-140218 | JVASP-119423 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-140218 | JVASP-144808 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| JVASP-140218 | JVASP-142153 | 1.0000 | moderate | 1.0000 | prototype family: perovskite_like \| structural regime: perovskite_like_unknown_variant \| material family: oxide \| formula family: ABO3 \| crystal system: 2 \| space group: C1m1 (No. 8) |  | The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). | The contextual signatures agree in 6 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like; structural regime: perovskite_like_unknown_variant; material family: oxide. The largest weighted contribution comes from ranked reference identities (36% of the available combined contribution). The compressed Structural Context Profile is consistent with the full reference-neighbourhood evidence. The two neighbourhoods have very similar diversity patterns. Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |

## Cluster explanations

| cluster_id | cluster_size | representative_candidate_id | mean_within_cluster_similarity | mean_similarity_confidence | mean_context_signature_agreement | dominant_prototype_family | dominant_structural_regime | dominant_material_family | dominant_formula_family | dominant_crystal_system | dominant_space_group | entropy_interpretation | scientific_interpretation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10 | JVASP-119589 | 1.0000 | 0.7735 | 1.0000 | perovskite_like | perovskite_like_unknown_variant | oxide | ABO3 | 2 | C1m1 (No. 8) | The representative neighbourhood is most concentrated at the material-family level (0.202) and most diverse at the prototype level (0.814). | Cluster 1 contains 10 candidates and is represented by JVASP-119589. Its representative neighbourhood is dominated by prototype family perovskite_like, structural regime perovskite_like_unknown_variant, material family oxide, formula family ABO3. Mean within-cluster similarity is 1.000, with mean explanation confidence 0.773. The dominant space-group signal is C1m1 (No. 8). The representative neighbourhood is most concentrated at the material-family level (0.202) and most diverse at the prototype level (0.814). This is a reference-relative description and not a physical classification. |

## Interpretation limits

- A cluster is a grouping under this specific corpus, retrieval procedure, fingerprint schema, and weighting configuration.
- Contextual distinctiveness is not intrinsic material novelty.
- Redundancy means similar reference-relative context, not interchangeable physical behaviour.
- Low-reliability candidates should be reviewed before their apparent isolation or transition status is interpreted.
