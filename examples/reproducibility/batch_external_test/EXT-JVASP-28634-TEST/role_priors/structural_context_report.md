# Structural Context Role Prior Report: EXT-JVASP-28634-TEST

## Scope

This report uses Phase 1 material profile data and Phase 3 cheap evidence metrics only. It does not use local-structure ranking, DFT, property prediction, or experimental validation. Apparently restraint survived another sprint.

## Query Material

- JID: EXT-JVASP-28634-TEST
- Formula: MoW3(SeS3)2
- Chemical system: Mo-S-Se-W
- Composition family: mixed_metal_nonmetal
- Formula family: ABC3D3
- Prototype family: unknown
- Structure variant: unknown
- Space group: 156.0

## Structural Context Profile

This section restructures the existing Phase 1 outputs as a Structural Context Profile: pool evidence, measurements, interpretation, and diagnostics. It does not change scoring.

### Measurements

| hub_strength | boundary_strength | evidence_sufficiency_score | evidence_sufficiency_status | neighbourhood_coherence | context_ambiguity | structural_diversity | hub_boundary_score_gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.571818 | 0.827662 | 0.69638 | sufficient | 0.745834 | 0.0 | 0.63217 | -0.255844 |

### Pool Context Summary

| same_family_pool_size | adjacent_family_pool_size | boundary_contrast_pool_size | wildcard_pool_size | negative_control_pool_size | candidate_ids_in_multiple_pools | unique_candidate_count_across_all_pools |
| --- | --- | --- | --- | --- | --- | --- |
| 500 | 41 | 500 | 100 | 100 | 117 | 1124 |

### Interpretation

| primary_interpretation | primary_interpretation_strength | primary_interpretation_score | secondary_interpretation |
| --- | --- | --- | --- |
| boundary | strong | 0.827662 | hub |

## Overall Assessment

- Status: `primary_role_supported:boundary;strength:strong`
- Primary core role: `boundary`
- Primary role strength: `strong`
- Primary role score: `0.827662`
- Primary role confidence: `0.777212`
- Secondary scored role: `hub`
- Secondary descriptors: ``
- Top-2 primary/scored roles: `boundary;hub`
- Supported core roles: `boundary`
- Partial core roles: `hub`
- Classification quality: `good`
- Quality flags: `generic_overclaim_risk;pool_overlap`
- No strong role supported flag: `False`
- Possible outlier flag: `False`

## Evidence Sufficiency

- Status: `sufficient`
- Score: `0.69638`
- Threshold: `0.55`
- Anchor strength: `0.6425`
- Family specificity: `0.35`
- Structural specificity: `0.0`
- Negative-control separation: `1.0`

## Primary Role Strength Profile

| rank | role | prior_score | confidence | strength_band | supported | partial | top_1 | top_2 | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | boundary | 0.827662 | 0.777212 | strong | True | False | True | True | boundary is the #1 ranked core role with strong evidence. |
| 2 | hub | 0.571818 | 0.638835 | moderate | False | True | False | True | hub is the #2 ranked core role with moderate evidence. |

## Hub vs Boundary Diagnostic Explanation

| hub_score | boundary_score | signed_hub_minus_boundary_score_gap | hub_confidence | boundary_confidence | signed_hub_minus_boundary_confidence_gap | hub_strength_band | boundary_strength_band | hub_boundary_ambiguity_flag | diagnostic_winner_by_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.571818 | 0.827662 | -0.255844 | 0.638835 | 0.777212 | -0.138377 | moderate | strong | False | boundary |

- Explanation: Boundary has the higher adjusted score among the two primary roles. Boundary regime-separation evidence is stronger than same-family coherence.

## Case-Level Diagnostic Summary

| primary_role | primary_role_strength | hub_boundary_score_gap | hub_boundary_score_gap_band | hub_boundary_ambiguity_flag | classification_quality | review_recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| boundary | strong | -0.255844 | clearly_separated | False | good | Boundary assignment appears robust under current Phase 1 diagnostics. Check whether the assignment depends on broad/generic family evidence. |

- Hub support: Same-family pool is populated. (value=500.0) | Same-family composition-family match rate. (value=0.0) | Same-family formula-family match rate. (value=0.34)
- Hub rejection/limitation: Not selected as primary role; strength=moderate, plausibility=not_supported_due_to_weak_structural_context.
- Boundary support: Boundary/contrast pool is populated. (value=500.0) | Boundary pool retains formula/prototype context. (value=1.0) | Boundary pool structure-variant match rate. (value=1.0)
- Boundary rejection/limitation: Not rejected; selected as primary role with strength=strong, plausibility=supported.
- Other classification reason: Not classified as Other.
- Secondary descriptor explanation: No secondary descriptors assigned.

### Hub vs Boundary Evidence Shape

| hub_same_family_coherence_proxy | hub_prototype_dominance_proxy | boundary_regime_separation_proxy | boundary_context_anchor_proxy | hub_supporting_evidence_count | boundary_supporting_evidence_count | hub_contradiction_count | boundary_contradiction_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.491667 | 1.0 | 0.756007 | 0.93 | 7 | 7 | 0 | 0 |

## Secondary Descriptors



## Bridge-like Diagnostic Metrics

| balanced_multi_pool_similarity | competing_membership_strength | structural_interpolation_score | coordination_transition_proxy | bridge_evidence_entropy | bridge_diagnostic_strength |
| --- | --- | --- | --- | --- | --- |
| 0.18076 | 0.60539 | 0.301882 | 0.48806 | 0.903758 | 0.49597 |

## Quality Flags

| flag | severity | reason | value |
| --- | --- | --- | --- |
| generic_overclaim_risk | medium | Family/prototype/anchor evidence is generic; strong Hub/Boundary evidence is retained when present, but the claim should be reviewed. | 0.6425 |
| pool_overlap | medium | Candidate IDs appear in multiple pools; evidence is not fully independent. | 117 |

## Role Plausibility Table

| rank | role | raw_prior_score | prior_score | confidence | strength_band | plausibility | supported | partial | top_1 | top_2 | is_core_role | is_quality_indicator | evidence_strength | supporting_evidence_count | contradiction_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | boundary | 0.827662 | 0.827662 | 0.777212 | strong | supported | True | False | True | True | True | False | 0.839384 | 7 | 0 |
| 2 | hub | 0.571818 | 0.571818 | 0.638835 | moderate | not_supported_due_to_weak_structural_context | False | True | False | True | True | False | 0.676868 | 7 | 0 |
| None | outlier | 0.392975 | 0.322975 | 0.571509 | very_weak | not_supported | False | False | False | False | False | True | None | 3 | 2 |

## Evidence and Contradictions by Role

### Hub

- Prior score: `0.571818`
- Confidence: `0.638835`
- Plausibility: `not_supported_due_to_weak_structural_context`

Supporting evidence:
- Same-family pool is populated. Value: `500.0`
- Same-family composition-family match rate. Value: `0.0`
- Same-family formula-family match rate. Value: `0.34`
- Same-family prototype-family match rate. Value: `1.0`
- Same-family structure-variant match rate. Value: `1.0`
- Same-family stable fraction. Value: `0.61`
- Negative control separation is strong. Value: `1.0`

Contradictions / weakening evidence:
- None recorded.

### Boundary

- Prior score: `0.827662`
- Confidence: `0.777212`
- Plausibility: `supported`

Supporting evidence:
- Boundary/contrast pool is populated. Value: `500.0`
- Boundary pool retains formula/prototype context. Value: `1.0`
- Boundary pool structure-variant match rate. Value: `1.0`
- Boundary pool has low same-spacegroup rate. Value: `0.0`
- Boundary pool has low same-crystal-system rate. Value: `0.002`
- Mean symmetry distance is high. Value: `139.356`
- Boundary pool remains largely stable by hull threshold. Value: `0.86`

Contradictions / weakening evidence:
- None recorded.

### Bridge

- Prior score: `0.271848`
- Confidence: `0.59384`
- Plausibility: `not_supported`

Supporting evidence:
- Adjacent-family pool is populated. Value: `41.0`
- Adjacent-family pool spans many chemical systems. Value: `6.0`
- Adjacent-family element-overlap fraction is substantial. Value: `0.5`
- Adjacent-family prototype entropy. Value: `0.1654270339962668`
- Adjacent-family structure-variant entropy. Value: `0.1654270339962668`
- Cross-pool overlap suggests connection between candidate groups. Value: `0.0`
- Balanced multi-pool similarity diagnostic. Value: `0.1807604114077268`
- Competing neighbourhood membership diagnostic. Value: `0.6053902347226271`
- Structural interpolation diagnostic. Value: `0.3018815800163586`
- Coordination/structural transition diagnostic. Value: `0.48806006575706595`
- Bridge evidence entropy diagnostic. Value: `0.9037579966140619`

Contradictions / weakening evidence:
- None recorded.

### Outlier

- Prior score: `0.322975`
- Confidence: `0.571509`
- Plausibility: `not_supported`

Supporting evidence:
- Outlier score increases when same/adjacent support is weak. Value: `0.0`
- Negative-control similarity component. Value: `0.0`
- Missingness component. Value: `0.0625`

Contradictions / weakening evidence:
- Same-family pool is large, arguing against outlier status. Value: `500.0`
- Negative controls are cleanly separated, reducing outlier concern. Value: `1.0`

## Warnings

- 117 candidate IDs appear in multiple pools; role evidence is not fully independent.
- Structural family/prototype context is weak (0.000); formula-only evidence is not enough for a strong role.
- Generic or formula-only overclaim risk detected; preserving high-scoring Hub/Boundary evidence with caution flags.

## Reproducibility

- Schema version: `phase4_5.structural_context_inference.v4.0_transition`
- Created at UTC: `2026-08-09T14:17:10.774847+00:00`
- Phase 1 input schema: `phase1.material_profile.v1.2`
- Phase 3 input schema: `phase3.structural_context_evidence.v2_pool_context_summary`
