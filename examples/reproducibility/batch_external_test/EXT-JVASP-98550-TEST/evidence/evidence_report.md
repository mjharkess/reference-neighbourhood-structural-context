# Cheap Evidence Metrics Report

Schema: `phase3.structural_context_evidence.v2_pool_context_summary`
Created: `2026-08-09T14:17:45.090899+00:00`

## Query

- JID: `EXT-JVASP-98550-TEST`
- Formula: `Ba4CeMn3O12`
- Material type: `external`
- Dataset kind: `external_structure`

## Pool Summary

| Pool | N | Same composition family | Same prototype family | Prototype entropy | Same SG rate | Stable fraction | Known synthesized rate | Missing required rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| same_family | 500 | 0.0000 | 1.0000 | 0.0000 | 0.6940 | 0.9660 | 1.0000 |  |
| adjacent_family | 414 | 0.0000 | 0.0000 | 0.5927 | 0.0145 | 0.7440 | 1.0000 |  |
| boundary_contrast | 500 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.9800 | 1.0000 |  |
| wildcard | 100 | 0.0000 | 1.0000 | 0.0000 | 0.0200 | 0.9700 | 1.0000 |  |
| negative_control | 100 | 0.0000 | 0.0000 | 0.9988 | 0.0700 | 0.9400 | 1.0000 |  |

## Pool Context Summary

- Strongest supporting neighbourhood: `same_family`
- Retrieval completeness proxy: `0.9570`
- Negative-control separation proxy: `0.7452`
- Candidate IDs in multiple pools: `87`

## Named Evidence Concepts

- `same_family_density`: `1.0000`
- `same_family_coherence`: `0.4292`
- `same_family_structural_coherence`: `0.8505`
- `adjacent_family_diversity`: `0.3995`
- `adjacent_relatedness`: `0.1264`
- `balanced_multi_pool_similarity`: `0.1693`
- `competing_membership_strength`: `0.6035`
- `structural_interpolation_score`: `0.2910`
- `coordination_transition_proxy`: `0.4825`
- `bridge_evidence_entropy`: `0.9049`
- `boundary_contrast_strength`: `0.9149`
- `boundary_symmetry_diversity`: `0.7807`
- `negative_control_separation`: `1.0000`
- `pool_overlap_rate`: `0.0570`
- `missingness_rate`: ``
- `stability_support`: `0.9150`
- `synthesis_support`: `1.0000`
- `hub_strength_evidence`: `0.8768`
- `bridge_strength_evidence`: `0.6266`
- `boundary_strength_evidence`: `0.9027`
- `core_role_strength_max`: `0.9027`
- `core_role_strength_mean`: `0.8020`
- `role_ambiguity_risk`: `0.9136`
- `no_strong_role_risk`: `0.0973`
- `possible_outlier_flag_evidence`: `0.0195`
- `overall_named_evidence_strength`: `0.8430`

## Lightweight Role Signal Summary

### Hub Indicators

- `same_family_pool_size`: `500`
- `same_family_composition_match_rate`: `0.0000`
- `same_family_material_match_rate`: `0.0000`
- `same_family_formula_match_rate`: `0.1460`
- `same_family_prototype_match_rate`: `1.0000`
- `same_family_structure_variant_match_rate`: `1.0000`
- `same_family_stable_fraction`: `0.9660`
- `same_family_known_synthesized_rate`: `1.0000`
- `negative_control_same_family_rate`: `0.0000`

### Bridge Indicators

- `adjacent_pool_size`: `414`
- `adjacent_family_entropy`: `0.0619`
- `adjacent_material_family_entropy`: `0.0619`
- `adjacent_formula_family_entropy`: `0.5362`
- `adjacent_prototype_family_entropy`: `0.5927`
- `adjacent_structure_variant_entropy`: `0.7449`
- `adjacent_mean_element_overlap_fraction`: `0.5054`
- `adjacent_unique_chemical_systems`: `139`
- `same_family_query_similarity_score`: `0.6080`
- `adjacent_query_similarity_score`: `0.2398`
- `boundary_query_similarity_score`: `0.5592`
- `adjacent_structural_regime_diversity_score`: `0.7465`
- `boundary_structural_regime_diversity_score`: `0.3903`
- `overlap_same_adjacent`: `0`

### Boundary Indicators

- `boundary_pool_size`: `500`
- `boundary_spacegroup_entropy`: `0.8416`
- `boundary_crystal_system_entropy`: `0.7197`
- `boundary_mean_symmetry_distance`: `143.7480`
- `boundary_same_formula_family_rate`: `0.1260`
- `boundary_same_prototype_family_rate`: `1.0000`
- `boundary_same_structure_variant_rate`: `1.0000`
- `boundary_same_spacegroup_rate`: `0.0000`
- `boundary_same_crystal_system_rate`: `0.0000`

### Outlier Indicators

- `same_family_pool_size`: `500`
- `adjacent_pool_size`: `414`
- `wildcard_pool_size`: `100`
- `negative_control_size`: `100`
- `negative_control_element_overlap`: `0.0000`
- `negative_control_same_chemical_system_rate`: `0.0000`

## Warnings

- 87 candidate IDs appear in multiple pools; Phase 3 metrics remain valid, but pool evidence is not fully independent.

## Scope Note

This report provides cheap structural-context evidence only. It does not assign final Hub, Boundary, Other, or downstream decision recommendations. That belongs in later interpretation layers.
