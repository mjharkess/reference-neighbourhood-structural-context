# Cheap Evidence Metrics Report

Schema: `phase3.structural_context_evidence.v2_pool_context_summary`
Created: `2026-08-09T13:42:01.273933+00:00`

## Query

- JID: `JVASP-143116`
- Formula: `Li7Mn2Co3O12`
- Material type: `bulk`
- Dataset kind: `dft_3d`

## Pool Summary

| Pool | N | Same composition family | Same prototype family | Prototype entropy | Same SG rate | Stable fraction | Known synthesized rate | Missing required rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| same_family | 500 | 1.0000 | 1.0000 | 0.0000 | 0.4680 | 0.9240 | 1.0000 |  |
| adjacent_family | 500 | 1.0000 | 0.0000 | 0.7080 | 0.0260 | 0.9100 | 1.0000 |  |
| boundary_contrast | 500 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.9720 | 1.0000 |  |
| wildcard | 100 | 1.0000 | 1.0000 | 0.0000 | 0.0100 | 1.0000 | 1.0000 |  |
| negative_control | 100 | 0.0000 | 0.0000 | 0.9765 | 0.0000 | 0.9500 | 1.0000 |  |

## Pool Context Summary

- Strongest supporting neighbourhood: `wildcard`
- Retrieval completeness proxy: `1.0000`
- Negative-control separation proxy: `0.7575`
- Candidate IDs in multiple pools: `68`

## Named Evidence Concepts

- `same_family_density`: `1.0000`
- `same_family_coherence`: `0.8300`
- `same_family_structural_coherence`: `0.7835`
- `adjacent_family_diversity`: `0.4109`
- `adjacent_relatedness`: `0.3579`
- `balanced_multi_pool_similarity`: `0.3722`
- `competing_membership_strength`: `0.7545`
- `structural_interpolation_score`: `0.3793`
- `coordination_transition_proxy`: `0.5432`
- `bridge_evidence_entropy`: `0.9570`
- `boundary_contrast_strength`: `0.9051`
- `boundary_symmetry_diversity`: `0.7527`
- `negative_control_separation`: `1.0000`
- `pool_overlap_rate`: `0.0417`
- `missingness_rate`: ``
- `stability_support`: `0.9515`
- `synthesis_support`: `1.0000`
- `hub_strength_evidence`: `0.9319`
- `bridge_strength_evidence`: `0.7024`
- `boundary_strength_evidence`: `0.8982`
- `core_role_strength_max`: `0.9319`
- `core_role_strength_mean`: `0.8442`
- `role_ambiguity_risk`: `0.8876`
- `no_strong_role_risk`: `0.0681`
- `possible_outlier_flag_evidence`: `0.0136`
- `overall_named_evidence_strength`: `0.8933`

## Lightweight Role Signal Summary

### Hub Indicators

- `same_family_pool_size`: `500`
- `same_family_composition_match_rate`: `1.0000`
- `same_family_material_match_rate`: `1.0000`
- `same_family_formula_match_rate`: `0.1500`
- `same_family_prototype_match_rate`: `1.0000`
- `same_family_structure_variant_match_rate`: `1.0000`
- `same_family_stable_fraction`: `0.9240`
- `same_family_known_synthesized_rate`: `1.0000`
- `negative_control_same_family_rate`: `0.0000`

### Bridge Indicators

- `adjacent_pool_size`: `500`
- `adjacent_family_entropy`: `0.0000`
- `adjacent_material_family_entropy`: `0.0000`
- `adjacent_formula_family_entropy`: `0.5985`
- `adjacent_prototype_family_entropy`: `0.7080`
- `adjacent_structure_variant_entropy`: `0.7483`
- `adjacent_mean_element_overlap_fraction`: `0.4315`
- `adjacent_unique_chemical_systems`: `225`
- `same_family_query_similarity_score`: `0.8096`
- `adjacent_query_similarity_score`: `0.4659`
- `boundary_query_similarity_score`: `0.7516`
- `adjacent_structural_regime_diversity_score`: `0.7718`
- `boundary_structural_regime_diversity_score`: `0.3763`
- `overlap_same_adjacent`: `0`

### Boundary Indicators

- `boundary_pool_size`: `500`
- `boundary_spacegroup_entropy`: `0.7418`
- `boundary_crystal_system_entropy`: `0.7636`
- `boundary_mean_symmetry_distance`: `149.8980`
- `boundary_same_formula_family_rate`: `0.0340`
- `boundary_same_prototype_family_rate`: `1.0000`
- `boundary_same_structure_variant_rate`: `1.0000`
- `boundary_same_spacegroup_rate`: `0.0000`
- `boundary_same_crystal_system_rate`: `0.0000`

### Outlier Indicators

- `same_family_pool_size`: `500`
- `adjacent_pool_size`: `500`
- `wildcard_pool_size`: `100`
- `negative_control_size`: `100`
- `negative_control_element_overlap`: `0.0000`
- `negative_control_same_chemical_system_rate`: `0.0000`

## Warnings

- 68 candidate IDs appear in multiple pools; Phase 3 metrics remain valid, but pool evidence is not fully independent.

## Scope Note

This report provides cheap structural-context evidence only. It does not assign final Hub, Boundary, Other, or downstream decision recommendations. That belongs in later interpretation layers.
