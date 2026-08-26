# Cheap Evidence Metrics Report

Schema: `phase3.structural_context_evidence.v2_pool_context_summary`
Created: `2026-08-09T14:17:10.546567+00:00`

## Query

- JID: `EXT-JVASP-28634-TEST`
- Formula: `MoW3(SeS3)2`
- Material type: `external`
- Dataset kind: `external_structure`

## Pool Summary

| Pool | N | Same composition family | Same prototype family | Prototype entropy | Same SG rate | Stable fraction | Known synthesized rate | Missing required rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| same_family | 500 | 0.0000 | 1.0000 | 0.0000 | 0.6260 | 0.6100 | 1.0000 |  |
| adjacent_family | 41 | 0.0000 | 0.0000 | 0.1654 | 0.0000 | 0.7317 | 1.0000 |  |
| boundary_contrast | 500 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.8600 | 1.0000 |  |
| wildcard | 100 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.9900 | 1.0000 |  |
| negative_control | 100 | 0.0000 | 0.0000 | 0.8505 | 0.0000 | 0.8900 | 1.0000 |  |

## Pool Context Summary

- Strongest supporting neighbourhood: `wildcard`
- Retrieval completeness proxy: `0.7705`
- Negative-control separation proxy: `0.7640`
- Candidate IDs in multiple pools: `117`

## Named Evidence Concepts

- `same_family_density`: `1.0000`
- `same_family_coherence`: `0.4680`
- `same_family_structural_coherence`: `0.8385`
- `adjacent_family_diversity`: `0.1654`
- `adjacent_relatedness`: `0.1250`
- `balanced_multi_pool_similarity`: `0.1853`
- `competing_membership_strength`: `0.6054`
- `structural_interpolation_score`: `0.3075`
- `coordination_transition_proxy`: `0.3943`
- `bridge_evidence_entropy`: `0.9160`
- `boundary_contrast_strength`: `0.8999`
- `boundary_symmetry_diversity`: `0.6673`
- `negative_control_separation`: `1.0000`
- `pool_overlap_rate`: `0.1041`
- `missingness_rate`: ``
- `stability_support`: `0.7979`
- `synthesis_support`: `1.0000`
- `hub_strength_evidence`: `0.8572`
- `bridge_strength_evidence`: `0.5379`
- `boundary_strength_evidence`: `0.8713`
- `core_role_strength_max`: `0.8713`
- `core_role_strength_mean`: `0.7555`
- `role_ambiguity_risk`: `0.9530`
- `no_strong_role_risk`: `0.1287`
- `possible_outlier_flag_evidence`: `0.0617`
- `overall_named_evidence_strength`: `0.7942`

## Lightweight Role Signal Summary

### Hub Indicators

- `same_family_pool_size`: `500`
- `same_family_composition_match_rate`: `0.0000`
- `same_family_material_match_rate`: `0.0000`
- `same_family_formula_match_rate`: `0.3400`
- `same_family_prototype_match_rate`: `1.0000`
- `same_family_structure_variant_match_rate`: `1.0000`
- `same_family_stable_fraction`: `0.6100`
- `same_family_known_synthesized_rate`: `1.0000`
- `negative_control_same_family_rate`: `0.0000`

### Bridge Indicators

- `adjacent_pool_size`: `41`
- `adjacent_family_entropy`: `0.1654`
- `adjacent_material_family_entropy`: `0.1654`
- `adjacent_formula_family_entropy`: `0.1654`
- `adjacent_prototype_family_entropy`: `0.1654`
- `adjacent_structure_variant_entropy`: `0.1654`
- `adjacent_mean_element_overlap_fraction`: `0.5000`
- `adjacent_unique_chemical_systems`: `6`
- `same_family_query_similarity_score`: `0.5434`
- `adjacent_query_similarity_score`: `0.2517`
- `boundary_query_similarity_score`: `0.5239`
- `adjacent_structural_regime_diversity_score`: `0.4517`
- `boundary_structural_regime_diversity_score`: `0.3336`
- `overlap_same_adjacent`: `0`

### Boundary Indicators

- `boundary_pool_size`: `500`
- `boundary_spacegroup_entropy`: `0.7820`
- `boundary_crystal_system_entropy`: `0.5526`
- `boundary_mean_symmetry_distance`: `139.3560`
- `boundary_same_formula_family_rate`: `0.2020`
- `boundary_same_prototype_family_rate`: `1.0000`
- `boundary_same_structure_variant_rate`: `1.0000`
- `boundary_same_spacegroup_rate`: `0.0000`
- `boundary_same_crystal_system_rate`: `0.0020`

### Outlier Indicators

- `same_family_pool_size`: `500`
- `adjacent_pool_size`: `41`
- `wildcard_pool_size`: `100`
- `negative_control_size`: `100`
- `negative_control_element_overlap`: `0.0000`
- `negative_control_same_chemical_system_rate`: `0.0000`

## Warnings

- 117 candidate IDs appear in multiple pools; Phase 3 metrics remain valid, but pool evidence is not fully independent.

## Scope Note

This report provides cheap structural-context evidence only. It does not assign final Hub, Boundary, Other, or downstream decision recommendations. That belongs in later interpretation layers.
