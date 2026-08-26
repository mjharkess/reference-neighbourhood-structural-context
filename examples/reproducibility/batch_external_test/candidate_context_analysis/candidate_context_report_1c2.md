# Candidate Context Analysis: Phase 1C.2

## Scope

This report compares candidates through both their Structural Context Profile measurements and the reference neighbourhoods that produced those measurements. It is reference-corpus dependent and does not predict physical performance, intrinsic novelty, synthesis success, or scientific value.

## Run summary

- Input candidates: **3**
- Compatible fingerprints: **3**
- Candidates included in clustering: **3**
- Selected clusters: **2**
- Redundancy pairs: **0**
- Reference IDs represented across analysed candidates: **3544**

## Similarity model

Combined context similarity = 0.35 × profile similarity + 0.65 × reference-neighbourhood similarity.

Reference-neighbourhood similarity combines ranked reference identity (0.55), context-distribution similarity (0.30), and pool-feature similarity (0.15); these three weights are normalised internally.

Negative controls are excluded from the default neighbourhood similarity.

## Cluster summary

| cluster_id | cluster_size | representative_candidate_id | mean_within_cluster_similarity | unique_reference_union_count | dominant_composition_family | dominant_formula_family |
|---|---|---|---|---|---|---|
| 1 | 2 | EXT-JVASP-98550-TEST | 0.5361 | 2606 | mixed_metal_nonmetal | ABC3D3 |
| 2 | 1 | EXT-JVASP-86726-TEST | 1.0000 | 1069 | metallic_or_intermetallic | ABC4 |

## Cluster representatives

| cluster_id | representative_candidate_id | representative_formula | mean_distance_to_cluster_members | candidate_reliability |
|---|---|---|---|---|
| 1 | EXT-JVASP-98550-TEST | Ba4CeMn3O12 | 0.2319 | 0.8865 |
| 2 | EXT-JVASP-86726-TEST | LuNi4Sn | 0.0000 | 0.8061 |

## Strongest contextual redundancy pairs

_None._

## Profile–neighbourhood discordance

These pairs are important because similar final profile scores can conceal different reference neighbourhoods, and vice versa.

| candidate_a | candidate_b | profile_similarity | reference_neighbourhood_similarity | profile_neighbourhood_discordance | discordance_type | pair_reliability |
|---|---|---|---|---|---|---|
| EXT-JVASP-28634-TEST | EXT-JVASP-98550-TEST | 0.9899 | 0.2918 | 0.6981 | similar_profile_different_reference_neighbourhood | 0.8580 |
| EXT-JVASP-86726-TEST | EXT-JVASP-28634-TEST | 0.9169 | 0.2707 | 0.6462 | similar_profile_different_reference_neighbourhood | 0.8181 |
| EXT-JVASP-86726-TEST | EXT-JVASP-98550-TEST | 0.9199 | 0.2944 | 0.6255 | similar_profile_different_reference_neighbourhood | 0.8453 |

## Most contextually distinctive candidates

| candidate_id | nearest_candidate_distance | mean_distance_to_k_nearest | contextual_distinctiveness_percentile |
|---|---|---|---|
| EXT-JVASP-86726-TEST | 0.4867 | 0.4949 | 1.0000 |
| EXT-JVASP-28634-TEST | 0.4639 | 0.4835 | 0.6667 |
| EXT-JVASP-98550-TEST | 0.4639 | 0.4753 | 0.3333 |

## Inter-cluster candidates

| candidate_id | assigned_cluster_id | best_alternative_cluster_id | cluster_membership_margin | intercluster_candidate |
|---|---|---|---|---|
| EXT-JVASP-98550-TEST | 1 | 2 | 0.0228 | True |
| EXT-JVASP-28634-TEST | 1 | 2 | 0.0393 | True |

## Candidate-relative coverage

- Effective cluster count: **1.890**
- Mean unique references per candidate: **1240.0**
- Median unique references per candidate: **1124.0**

## Cluster-count diagnostics

| requested_clusters | actual_clusters | silhouette_score |
|---|---|---|
| 2 | 2 | 0.0416 |

## Similarity explainability

The similarity score is unchanged. The confidence and decomposition fields below describe how strongly the available fingerprint evidence supports each comparison.

| candidate_a | candidate_b | combined_context_similarity | similarity_confidence_label | context_signature_agreement_fraction | contextual_agreements | contextual_disagreements | entropy_interpretation | dominant_similarity_driver | scientific_interpretation |
|---|---|---|---|---|---|---|---|---|---|
| EXT-JVASP-28634-TEST | EXT-JVASP-98550-TEST | 0.5361 | moderate | 0.1667 | crystal system: 5 | prototype family: dichalcogenide_like versus perovskite_like \| structural regime: layered_chalcogenide_candidate versus perovskite_like_unknown_variant \| material family: chalcogenide versus oxide \| formula family: ABC3D3 versus ABO3 \| space group: P3m1 (No. 156) versus R-3m (No. 166) | The two neighbourhoods show modest differences in diversity. The largest difference is in material-family diversity (0.559 versus 0.240). Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from profile (65% of the available combined contribution). | The contextual signatures agree in 1 of 6 comparable dimensions. Shared signals include crystal system: 5. The principal reported differences are prototype family: dichalcogenide_like versus perovskite_like; structural regime: layered_chalcogenide_candidate versus perovskite_like_unknown_variant; material family: chalcogenide versus oxide. The largest weighted contribution comes from profile (65% of the available combined contribution). The compressed profile is more similar than the underlying reference neighbourhoods, indicating that profile compression hides some relational differences. The two neighbourhoods show modest differences in diversity. The largest difference is in material-family diversity (0.559 versus 0.240). Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| EXT-JVASP-86726-TEST | EXT-JVASP-98550-TEST | 0.5133 | moderate | 0.1667 | prototype family: perovskite_like | structural regime: layered_chalcogenide_candidate versus perovskite_like_unknown_variant \| material family: intermetallic versus oxide \| formula family: ABC4 versus ABO3 \| crystal system: 7 versus 5 \| space group: F-43m (No. 216) versus R-3m (No. 166) | The two neighbourhoods show substantial differences in diversity. The largest difference is in material-family diversity (0.858 versus 0.240). Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from profile (63% of the available combined contribution). | The contextual signatures agree in 1 of 6 comparable dimensions. Shared signals include prototype family: perovskite_like. The principal reported differences are structural regime: layered_chalcogenide_candidate versus perovskite_like_unknown_variant; material family: intermetallic versus oxide; formula family: ABC4 versus ABO3. The largest weighted contribution comes from profile (63% of the available combined contribution). The compressed profile is more similar than the underlying reference neighbourhoods, indicating that profile compression hides some relational differences. The two neighbourhoods show substantial differences in diversity. The largest difference is in material-family diversity (0.858 versus 0.240). Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |
| EXT-JVASP-86726-TEST | EXT-JVASP-28634-TEST | 0.4969 | moderate | 0.1667 | structural regime: layered_chalcogenide_candidate | prototype family: perovskite_like versus dichalcogenide_like \| material family: intermetallic versus chalcogenide \| formula family: ABC4 versus ABC3D3 \| crystal system: 7 versus 5 \| space group: F-43m (No. 216) versus P3m1 (No. 156) | The two neighbourhoods show substantial differences in diversity. The largest difference is in formula-family diversity (0.259 versus 0.736). Prototype assignments are diverse in both neighbourhoods. | The largest weighted contribution comes from profile (65% of the available combined contribution). | The contextual signatures agree in 1 of 6 comparable dimensions. Shared signals include structural regime: layered_chalcogenide_candidate. The principal reported differences are prototype family: perovskite_like versus dichalcogenide_like; material family: intermetallic versus chalcogenide; formula family: ABC4 versus ABC3D3. The largest weighted contribution comes from profile (65% of the available combined contribution). The compressed profile is more similar than the underlying reference neighbourhoods, indicating that profile compression hides some relational differences. The two neighbourhoods show substantial differences in diversity. The largest difference is in formula-family diversity (0.259 versus 0.736). Prototype assignments are diverse in both neighbourhoods. The evidence confidence attached to this explanation is moderate. |

## Cluster explanations

| cluster_id | cluster_size | representative_candidate_id | mean_within_cluster_similarity | mean_similarity_confidence | mean_context_signature_agreement | dominant_prototype_family | dominant_structural_regime | dominant_material_family | dominant_formula_family | dominant_crystal_system | dominant_space_group | entropy_interpretation | scientific_interpretation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | EXT-JVASP-98550-TEST | 0.5361 | 0.7210 | 0.1667 | perovskite_like | perovskite_like_unknown_variant | oxide | ABO3 | 5 | R-3m (No. 166) | The representative neighbourhood is most concentrated at the material-family level (0.240) and most diverse at the prototype level (0.764). | Cluster 1 contains 2 candidates and is represented by EXT-JVASP-98550-TEST. Its representative neighbourhood is dominated by prototype family perovskite_like, structural regime perovskite_like_unknown_variant, material family oxide, formula family ABO3. Mean within-cluster similarity is 0.536, with mean explanation confidence 0.721. The dominant space-group signal is R-3m (No. 166). The representative neighbourhood is most concentrated at the material-family level (0.240) and most diverse at the prototype level (0.764). This is a reference-relative description and not a physical classification. |
| 2 | 1 | EXT-JVASP-86726-TEST | 1.0000 |  |  | perovskite_like | layered_chalcogenide_candidate | intermetallic | ABC4 | 7 | F-43m (No. 216) | The representative neighbourhood is most concentrated at the formula-family level (0.259) and most diverse at the prototype level (0.889). | Cluster 2 contains 1 candidates and is represented by EXT-JVASP-86726-TEST. Its representative neighbourhood is dominated by prototype family perovskite_like, structural regime layered_chalcogenide_candidate, material family intermetallic, formula family ABC4. Mean within-cluster similarity is 1.000, with mean explanation confidence unavailable. The dominant space-group signal is F-43m (No. 216). The representative neighbourhood is most concentrated at the formula-family level (0.259) and most diverse at the prototype level (0.889). This is a reference-relative description and not a physical classification. |

## Interpretation limits

- A cluster is a grouping under this specific corpus, retrieval procedure, fingerprint schema, and weighting configuration.
- Contextual distinctiveness is not intrinsic material novelty.
- Redundancy means similar reference-relative context, not interchangeable physical behaviour.
- Low-reliability candidates should be reviewed before their apparent isolation or transition status is interpreted.
