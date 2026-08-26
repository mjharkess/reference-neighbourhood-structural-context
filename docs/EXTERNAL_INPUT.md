# External Material Input

## Reference-Neighbourhood Structural Context Framework

**Version:** v0.1 Draft\
**Document role:** External structure preparation, external
descriptor-record contract, validation, and integration with the main
analysis pipeline\
**Implementation basis:** Reconciled against the 8 August 2026 frozen
source-code bundle and the supplied external-material preparation
modules

------------------------------------------------------------------------

# 1. Purpose and Scope

The Reference-Neighbourhood Structural Context Framework supports
analysis of materials that are not already present as query records in
the configured JARVIS-backed material store.

The external-material workflow allows a user to:

1.  supply a crystalline structure in a supported structure-file format;
2.  parse the structure into a normalized external-material record;
3.  construct the inexpensive descriptors required by the framework
    where they can be derived from the structure;
4.  validate whether the resulting record contains sufficient
    information for reference retrieval;
5.  register the resulting external descriptor record with the
    `MaterialStore`;
6.  process the external material through the same Material Profile,
    candidate-pool, evidence, Reference-Neighbourhood Fingerprint (RNF),
    and Structural Context Profile (SCP) stages used for other query
    materials; and
7.  include multiple external candidates in batch and Candidate Context
    Analysis workflows.

The external material is normally treated as a **query object evaluated
against the existing reference corpus**. It is not, by default, added to
the reference universe. This preserves the intended reference-relative
interpretation: evaluating an external candidate should not
automatically change the corpus against which that candidate is
contextualised.

This document defines the implemented v0.1 external-input workflow. It
does not define a general crystallographic interchange standard, and it
does not claim that every descriptor available for a native JARVIS
material can be reconstructed from a structure file alone.

------------------------------------------------------------------------

# 2. Architectural Position

External-material preparation is an ingestion process upstream of the
common per-material analysis pipeline.

The implemented flow is:

```text
POSCAR / CONTCAR / CIF
        |
        v
phase5_external_material_prepare.py
        |
        +--> external_material_ingestion.py
        |       |
        |       +--> parse structure
        |       +--> establish external ID
        |       +--> record structure/provenance
        |
        +--> external_descriptor_builder.py
        |       |
        |       +--> composition descriptors
        |       +--> lattice/geometry descriptors
        |       +--> symmetry descriptors
        |       +--> coordination descriptors
        |       +--> bonding descriptors
        |
        +--> external_material_validator.py
                |
                +--> parse validation
                +--> geometry validation
                +--> descriptor-completeness validation
                +--> critical retrieval-field validation
        |
        v
external_descriptor_record.json
        |
        v
MaterialStore
        |
        v
Material Profile
        |
        v
Candidate Pools
        |
        v
Evidence + RNF
        |
        v
SCP / auxiliary role-prior outputs
        |
        v
optional Candidate Context Analysis
```

The preparation modules retain historical `Phase 5` / `LRT` terminology
in filenames, schema identifiers, comments, and command descriptions.
These names are implementation identifiers from the development history.
Within the current v0.1 architecture, the prepared external descriptor
record is an input to the Reference-Neighbourhood Structural Context
Framework.

------------------------------------------------------------------------

# 3. Supported Source Structure Formats

The supplied ingestion implementation supports:

-   `CIF`;
-   `POSCAR`;
-   `CONTCAR`; and
-   files with the `.vasp` suffix, which are treated as POSCAR input.

Format inference is based on the filename or suffix unless
`--external_format` is supplied explicitly.

For reproducible use, specify `--external_format` explicitly when the
filename does not unambiguously identify the structure format. For
example, a file named `POSCAR_JVASP-28634` has neither the exact
filename `POSCAR` nor a recognized POSCAR/VASP suffix, so it should be
supplied with `--external_format poscar`.

Supported explicit format values are:

```text
cif
poscar
contcar
```

The structure is parsed using:

```text
pymatgen.core.Structure.from_file
```

Accordingly, `pymatgen` is required for the external structure
preparation workflow. The descriptor builder also uses `numpy`.

A source structure that cannot be parsed successfully is not eligible to
proceed to retrieval.

------------------------------------------------------------------------

# 4. External Material Preparation CLI

The principal preparation entry point is:

```text
phase5_external_material_prepare.py
```

Its implemented arguments are:

  ------------------------------------------------------------------------------------------------------------
  Argument                                     Required Default                          Purpose
  ------------------------------- --------------------- -------------------------------- ---------------------
  `--external_structure`                            Yes ---                              Path to a CIF,
                                                                                         POSCAR, or CONTCAR
                                                                                         file

  `--external_format`                                No inferred                         Explicit format:
                                                                                         `cif`, `poscar`, or
                                                                                         `contcar`

  `--external_id`                                    No generated                        Stable identifier for
                                                                                         the external material

  `--external_label`                                 No `None`                           Optional human-facing
                                                                                         label retained in
                                                                                         provenance

  `--output_dir`                                     No `phase5_external_material_run`   Preparation output
                                                                                         directory

  `--coordination_cutoff`                            No `3.0`                            Distance cutoff used
                                                                                         by coordination and
                                                                                         bonding proxy
                                                                                         calculations

  `--min_required_completeness`                      No `0.75`                           Minimum
                                                                                         required-descriptor
                                                                                         completeness used by
                                                                                         validation
  ------------------------------------------------------------------------------------------------------------

A typical POSCAR preparation command is:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure ./POSCAR \
  --external_format poscar \
  --external_id EXT-0001 \
  --output_dir ./external_prepared/EXT-0001
```

The same workflow can be used for CIF input:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure ./candidate.cif \
  --external_id EXT-0002 \
  --output_dir ./external_prepared/EXT-0002
```

The preparation script prints a status summary and writes the
preparation artefacts described below.

------------------------------------------------------------------------

# 5. External Identifier

## 5.1 User-supplied identifier

A stable identifier can be supplied using:

```text
--external_id EXT-0001
```

Using a stable, unique identifier is recommended for reproducible batch
work and for joining outputs across pipeline stages.

## 5.2 Automatically generated identifier

If an identifier is not supplied, the ingestion code generates one in
the form:

```text
EXT-YYYYMMDD-XXXXXXXXXX
```

where the final component is derived from the first ten hexadecimal
characters of the SHA-256 digest of the source structure file.

Because the generated identifier contains the UTC date of preparation,
the same unchanged structure file prepared on different dates can
receive different automatically generated IDs. For durable published or
comparative workflows, an explicit stable `--external_id` is therefore
preferable.

------------------------------------------------------------------------

# 6. Structure Ingestion

`external_material_ingestion.py` converts the source structure into an
`ExternalMaterialRecord`.

For a successfully parsed structure, the ingestion stage records
information including:

-   external identifier;
-   source file;
-   source format;
-   formula;
-   reduced formula;
-   element list;
-   atom count;
-   species count;
-   lattice lengths;
-   lattice angles;
-   lattice volume;
-   parser identity;
-   parse status;
-   raw JSON-safe structure representation; and
-   provenance.

The parser is recorded as:

```text
pymatgen.Structure.from_file
```

The raw structure is retained using the `pymatgen` structure dictionary
representation so that descriptor construction can reconstruct the
parsed structure without reparsing the original source file.

------------------------------------------------------------------------

# 7. Provenance

The ingestion stage records provenance including:

```text
source_filename
source_path
source_sha256
external_label
parsed_at_utc
```

The SHA-256 digest provides a content-level identifier for the original
source file and can be used to check whether a structure file has
changed.

`source_path` and the later `external_source_file` field may contain an
absolute local filesystem path. Before publishing example output
records, users should consider replacing local absolute paths with
sanitized or repository-relative examples if disclosure of the original
filesystem location is undesirable.

Provenance should not be removed from actual analytical records merely
for cosmetic reasons where it is required to establish what input was
processed.

------------------------------------------------------------------------

# 8. Descriptor Construction

`external_descriptor_builder.py` constructs an external descriptor
record intended to be compatible with the descriptor expectations of the
main framework.

The generated record includes identity/provenance fields and, where
calculation succeeds, composition, symmetry, geometry, coordination, and
bonding information.

## 8.1 Identity and source fields

The builder initializes fields including:

```text
jid
external_id
formula
material_type
dataset_kind
external_source_file
external_source_format
```

For prepared external records:

```text
material_type = "external"
dataset_kind = "external_structure"
```

The generated `jid` is set to the external material identifier. It does
not imply that the material is a native JARVIS record.

## 8.2 Composition and retrieval fields

The preparation code derives, where possible:

```text
reduced_formula
chemical_system
n_elements
composition_family
metal_count
nonmetal_count
element_set
```

The current simple composition-family values generated by the external
descriptor builder are:

```text
mixed_metal_nonmetal
metallic_or_intermetallic
nonmetallic
unknown_composition
```

These fields are preparation/retrieval descriptors and should not be
interpreted as authoritative scientific classification.

## 8.3 Composition-property descriptors

The builder attempts to calculate:

```text
mean_electronegativity
electronegativity_range
atomic_radius_mean
valence_electrons_mean
```

These values are derived using element information available through
`pymatgen`.

## 8.4 Lattice and geometric descriptors

The builder calculates, where possible:

```text
a_axis
b_axis
c_axis_cached
c_over_a
c_over_b
max_axis_over_min_axis
volume_per_atom
frac_z_span
cart_z_span_over_c
```

These fields provide inexpensive geometric information used by the
broader profiling and retrieval framework.

## 8.5 Symmetry descriptors

Using `pymatgen.symmetry.analyzer.SpacegroupAnalyzer`, the builder
attempts to generate:

```text
spacegroup_number
crystal_system_code
n_symmetry_ops
is_centrosymmetric
```

The implemented crystal-system coding is:

  Crystal system     Code
  ---------------- ------
  triclinic             1
  monoclinic            2
  orthorhombic          3
  tetragonal            4
  trigonal              5
  hexagonal             6
  cubic                 7

If symmetry analysis fails, the relevant fields are retained as missing
and a warning is recorded.

## 8.6 Coordination descriptors

Using the configured coordination cutoff, default `3.0`, the builder
attempts to calculate:

```text
coord_mean
coord_std
coord_min
coord_max
frac_low_coord_sites
frac_high_coord_sites
```

The current implementation defines the low-coordination fraction using
coordination numbers less than or equal to 2 and the high-coordination
fraction using coordination numbers greater than or equal to 8.

The cutoff is a configured computational parameter, not a universal
chemical definition of coordination.

## 8.7 Bonding proxies

Using neighbours within the same configured cutoff, the builder attempts
to calculate:

```text
bond_mean_en_diff
bond_std_en_diff
bond_max_en_diff
bond_length_mean
bond_length_std
bond_length_range
frac_short_bonds
ionicity_proxy_comp
```

In the current implementation, `frac_short_bonds` is the fraction of
collected neighbour distances below `2.2`.

These quantities are inexpensive structural/compositional proxies used
by the framework. They should not be interpreted as a full bond-order or
electronic-structure analysis.

------------------------------------------------------------------------

# 9. Physical-Property Fields

A structure file alone does not establish every physical or
thermodynamic field that may be available for a database material.

The external descriptor builder therefore explicitly creates the
following fields with `null` values unless information is supplied
through another route:

```text
formation_energy
formation_energy_peratom
energy_above_hull
known_synthesized
```

A `null` value in these fields means that the value is unavailable from
the implemented external structure preparation process. It does **not**
mean zero, false, physically unstable, unsynthesizable, or negative
evidence.

The preparation workflow therefore permits structural comparison while
preserving the distinction between structure-derived information and
physical metadata that has not been established.

------------------------------------------------------------------------

# 10. Missing-Value Semantics

Missing descriptor information is represented using JSON `null`.

Within the external-input workflow, `null` should be interpreted as:

> the value was not available or was not successfully generated by the
> applicable preparation stage.

It must not automatically be interpreted as:

-   numeric zero;
-   Boolean false;
-   absence of a physical phenomenon;
-   evidence against a material family;
-   evidence of instability; or
-   evidence that a material is unsuitable.

The validation layer separately determines whether missing information
is sufficiently important to prevent retrieval.

------------------------------------------------------------------------

# 11. Preparation Artefacts

A successful invocation of `phase5_external_material_prepare.py` writes
the following files to the selected output directory:

```text
<OUTPUT_DIR>/
├── external_material_profile.json
├── external_descriptor_report.json
├── external_descriptor_record.json
├── external_validation_report.json
└── phase5_prepare_status.json
```

## 11.1 `external_material_profile.json`

Intermediate structure-ingestion record.

It contains the parsed structure summary, raw structure representation,
parser status, source information, warnings/errors, and provenance.

Schema identifier:

```text
phase5.external_material.v1
```

This is primarily a preparation-stage artefact rather than the preferred
direct input to the main pipeline.

## 11.2 `external_descriptor_report.json`

Descriptor-generation report containing:

-   `external_id`;
-   the nested `descriptors` object;
-   generated fields;
-   missing fields;
-   required fields missing;
-   optional fields missing;
-   descriptor completeness;
-   warnings; and
-   errors.

Schema identifier:

```text
phase5.external_descriptor.v1
```

The `MaterialStore` can normalize a payload containing a top-level
`descriptors` mapping, so this report-like structure is technically
registerable. For normal public use, however,
`external_descriptor_record.json` is the clearer hand-off artefact.

## 11.3 `external_descriptor_record.json`

The flattened descriptor dictionary generated for registration with the
main framework.

This is the **recommended hand-off file from external preparation to the
main v0.1 pipeline**.

## 11.4 `external_validation_report.json`

Records whether the prepared external material has sufficient valid
information to proceed to retrieval.

Schema identifier:

```text
phase5.external_validation.v1
```

## 11.5 `phase5_prepare_status.json`

Small orchestration summary containing:

-   external ID;
-   parse status;
-   validation status;
-   `can_run_retrieval`; and
-   paths to the preparation outputs.

This is useful for automation and human inspection but is not itself the
descriptor record consumed by the scientific pipeline.

------------------------------------------------------------------------

# 12. External Descriptor Record Contract

The main `MaterialStore` accepts either:

1.  a direct descriptor mapping such as
    `external_descriptor_record.json`; or
2.  a mapping with a top-level `descriptors` object, such as the
    descriptor-report structure.

For the direct descriptor-record route, the material must be
identifiable and must contain a formula.

## 12.1 Identifier requirement

The `MaterialStore` resolves the material identifier in this order:

```text
explicit external_id override
external_id
jid
id
```

At least one usable identifier must therefore be available, unless an
identifier is supplied explicitly by the caller.

The normalized store record sets:

```text
jid = resolved external identifier
```

and retains:

```text
external_id
```

## 12.2 Formula requirement

The store resolves formula as:

```text
formula
```

or, if `formula` is absent:

```text
reduced_formula
```

If neither is available, registration fails.

## 12.3 Normalized external fields

During registration, the store normalizes the record to include:

```text
material_type = "external"
dataset_kind = "external_structure"
is_external_material = true
external_registration_schema_version = "phase5.material_store_external.v1"
```

Where necessary it also maps:

```text
source_file   -> external_source_file
source_format -> external_source_format
```

and derives composition/reachability information when possible.

------------------------------------------------------------------------

# 13. Descriptor Fields Expected by the Material Store

The frozen `material_store.py` defines the following descriptor-required
columns:

```text
jid
formula
mean_electronegativity
electronegativity_range
atomic_radius_mean
valence_electrons_mean
spacegroup_number
crystal_system_code
n_symmetry_ops
is_centrosymmetric
coord_mean
coord_std
coord_min
coord_max
frac_low_coord_sites
frac_high_coord_sites
a_axis
b_axis
c_axis_cached
c_over_a
c_over_b
max_axis_over_min_axis
volume_per_atom
frac_z_span
cart_z_span_over_c
bond_mean_en_diff
bond_std_en_diff
bond_max_en_diff
bond_length_mean
bond_length_std
bond_length_range
frac_short_bonds
ionicity_proxy_comp
reduced_formula
chemical_system
n_elements
composition_family
metal_count
nonmetal_count
```

Registration normalization inserts missing expected fields with `null`
where necessary. Consequently, the existence of a key does not establish
that the corresponding descriptor is available.

The preparation code normally generates `n_elements`, `metal_count`, and
`nonmetal_count` as part of its composition reachability features.

### v0.1 implementation consistency note

`external_material_schema.py` states that its
`LRT_REQUIRED_DESCRIPTOR_FIELDS` list is copied from the Material Store
contract. In the supplied code, that preparation-stage list does **not**
include `n_elements`, `metal_count`, or `nonmetal_count`, although the
frozen `material_store.py` required-column set does include them.

The descriptor builder nevertheless generates these fields under normal
successful composition processing, and the external validator explicitly
treats `n_elements` as a critical retrieval field. This difference
should therefore be treated as a **known v0.1 contract-alignment issue**
rather than as permission to omit the fields deliberately.

For publication and schema purposes, the frozen Material Store contract
is the authoritative downstream registration expectation.

------------------------------------------------------------------------

# 14. Validation

`external_material_validator.py` determines whether a prepared external
material may proceed to retrieval.

The default minimum required-descriptor completeness is:

```text
0.75
```

Passing this percentage alone is not sufficient. The validator also
checks parse success, extracted elements, geometry, and critical
retrieval descriptors.

## 14.1 Validation statuses

The implemented statuses are:

```text
accepted
accepted_with_warnings
rejected_parse_failure
rejected_missing_required_descriptors
rejected_invalid_geometry
rejected_unsupported_species
```

## 14.2 Parse failure

If:

```text
parse_status != "success"
```

the material is assigned:

```text
rejected_parse_failure
```

and retrieval is not permitted.

## 14.3 Unsupported/missing species

If no elements were extracted from the parsed record, the material is
assigned:

```text
rejected_unsupported_species
```

and retrieval is not permitted.

## 14.4 Invalid geometry

The validator requires non-missing values for:

```text
a_axis
b_axis
c_axis_cached
volume_per_atom
```

If any are missing, the material is assigned:

```text
rejected_invalid_geometry
```

and retrieval is not permitted.

## 14.5 Critical retrieval fields

The current validator treats the following as critical:

```text
jid
formula
reduced_formula
chemical_system
composition_family
n_elements
element_set
a_axis
b_axis
c_axis_cached
c_over_a
c_over_b
max_axis_over_min_axis
volume_per_atom
frac_z_span
cart_z_span_over_c
coord_mean
coord_std
bond_length_mean
ionicity_proxy_comp
mean_electronegativity
electronegativity_range
```

If any critical field is missing, retrieval is rejected even if the
numerical completeness threshold would otherwise be met.

## 14.6 Missing required descriptors

A material is assigned:

```text
rejected_missing_required_descriptors
```

when either:

-   required descriptor completeness is below the configured threshold;
    or
-   one or more critical retrieval fields are missing.

## 14.7 Accepted with warnings

If required validation succeeds but optional physical fields or
descriptor warnings remain, the material is assigned:

```text
accepted_with_warnings
```

with:

```text
can_run_retrieval = true
```

The implemented recommendation is that retrieval may proceed but
physical plausibility should be treated as incomplete.

## 14.8 Accepted

A material that passes the required checks without the warning
conditions is assigned:

```text
accepted
```

with:

```text
can_run_retrieval = true
```

------------------------------------------------------------------------

# 15. Running the Prepared Material Through the Main Pipeline

After preparation, the recommended pipeline input is:

```text
external_descriptor_record.json
```

The single-material pipeline accepts either a native JARVIS ID or an
external JSON file through a mutually exclusive input interface.

A typical external-material run is:

```bash
python3 run_context_pipeline.py \
  --external_json ./external_prepared/EXT-0001/external_descriptor_record.json \
  --external_id EXT-0001 \
  --output_dir ./outputs/EXT-0001 \
  --scripts_dir .
```

The `--external_id` argument is optional when a suitable identifier is
already present in the JSON record, but supplying a stable explicit ID
can make the intended identity clearer.

The pipeline forwards the external record to the Material Profile
Builder, which registers it with the shared `MaterialStore` before
constructing the normal query profile.

------------------------------------------------------------------------

# 16. Reference-Universe Behaviour

By default, registering an external material does **not** add it to the
reference universe.

This is intentional.

The normal relationship is:

```text
external query material
        |
        v
existing JARVIS-backed reference universe
```

rather than:

```text
external query material
        |
        +--> automatically becomes a reference candidate
```

This prevents the act of submitting a candidate from automatically
changing the population against which it is evaluated.

The main pipeline exposes:

```text
--include_external_in_universe
```

but the implementation describes this as an option that should usually
be left off.

If enabled deliberately, the external row is appended to the universe.
The Material Store can optionally recompute feature statistics, but the
default behaviour keeps feature statistics anchored to the original
JARVIS universe.

For ordinary external-candidate analysis in v0.1, the recommended
setting is therefore:

```text
include_external_in_universe = false
```

------------------------------------------------------------------------

# 17. Batch External-Material Input

The batch runner supports external JSON inputs through either:

```text
--external_json_list
```

or:

```text
--external_json_dir
```

## 17.1 External JSON list

`--external_json_list` accepts a CSV or text-based input resolved by the
batch runner.

Recognized path fields include:

```text
external_json
json
path
file
filepath
value
```

Recognized identifier fields include:

```text
external_id
id
case_id
label
```

If no explicit external identifier is supplied, the JSON filename stem
is used.

A simple CSV can therefore use:

```csv
external_json,external_id,label
./external_prepared/EXT-0001/external_descriptor_record.json,EXT-0001,Candidate 1
./external_prepared/EXT-0002/external_descriptor_record.json,EXT-0002,Candidate 2
```

Relative JSON paths in a list are resolved relative to the list file's
directory.

## 17.2 External JSON directory

`--external_json_dir` discovers:

```text
*.json
```

files directly in the specified directory and creates one
external-material job per file.

Because the preparation directory contains several JSON artefacts per
material, users should **not point this option indiscriminately at a
directory containing all preparation outputs**. A dedicated directory
containing only the intended pipeline input records, normally
`external_descriptor_record.json` copies or suitably named equivalents,
is safer.

Otherwise the batch runner can quite obediently attempt to process JSON
files that were never intended to be candidate records, because software
remains committed to literalism.

## 17.3 Typical batch invocation

Conceptually:

```bash
python3 batch_role_prior_runner_structural_context_v2.py \
  --external_json_list ./external_candidates.csv \
  --project_dir . \
  --output_dir ./batch_external_outputs \
  --reuse_cache
```

Additional arguments required by a particular repository layout or run
configuration should follow the batch runner's CLI.

------------------------------------------------------------------------

# 18. Main Pipeline Acceptance Versus Preparation Validation

Two different validation boundaries exist and should not be confused.

## Preparation validation

`external_material_validator.py` performs detailed checks concerning:

-   parse success;
-   species extraction;
-   geometry;
-   descriptor completeness;
-   critical retrieval fields; and
-   optional missing information.

This determines `can_run_retrieval`.

## Material Store registration validation

`MaterialStore.validate_external_record()` is deliberately
lighter-weight. It normalizes the record and reports:

-   whether it can be registered;
-   missing descriptor-required fields;
-   missing framework feature fields; and
-   usable feature counts.

The Material Store's basic registration condition is essentially that a
usable identifier and formula can be established. This does **not** mean
that every registerable record is scientifically adequate for retrieval.

For the documented external-structure workflow, users should therefore
prepare and validate the structure first and proceed to the main
pipeline only when:

```text
can_run_retrieval = true
```

unless they are intentionally performing a diagnostic/development run.

------------------------------------------------------------------------

# 19. Failure Modes and Troubleshooting

## 19.1 Source file does not exist

Expected result:

```text
parse_status = "failed"
validation_status = "rejected_parse_failure"
```

Check the supplied path.

## 19.2 Unsupported source format

Expected result:

```text
parse_status = "failed"
```

Use CIF, POSCAR, or CONTCAR, or supply a correct explicit
`--external_format`.

## 19.3 `pymatgen` unavailable

Structure parsing and descriptor construction require `pymatgen`.

Install the project dependencies appropriate to the published repository
environment before running external preparation.

## 19.4 Structure cannot be parsed

The ingestion record will contain an error beginning with:

```text
Failed to parse structure with pymatgen:
```

Inspect the source structure for format, species, occupancy, lattice, or
coordinate problems.

## 19.5 Geometry descriptors missing

If `a_axis`, `b_axis`, `c_axis_cached`, or `volume_per_atom` is missing,
validation rejects the material as invalid geometry.

## 19.6 Critical retrieval descriptor missing

The material is rejected as:

```text
rejected_missing_required_descriptors
```

Inspect `external_descriptor_report.json` and
`external_validation_report.json` to identify the missing fields.

## 19.7 Optional physical fields are null

This is expected for structure-only preparation. It does not by itself
prevent retrieval.

## 19.8 Duplicate external identifier

The Material Store supports overwrite behaviour internally. For
reproducible public workflows, external IDs should nevertheless be
unique and stable rather than relying on accidental replacement.

## 19.9 External material unexpectedly appears in the reference universe

Check whether:

```text
--include_external_in_universe
```

was supplied. It should normally be omitted.

------------------------------------------------------------------------

# 20. Recommended Repository Placement

For a public v0.1 repository, the external-input material can be
organised as:

```text
repository/
├── README.md
├── METHODOLOGY.md
├── ARCHITECTURE.md
├── VALIDATION.md
├── CLAIMS.md
│
├── docs/
│   └── EXTERNAL_INPUT.md
│
├── schemas/
│   └── external_material.schema.json
│
├── examples/
│   └── external/
│       ├── POSCAR
│       └── external_descriptor_record.json
│
└── src/
    ├── phase5_external_material_prepare.py
    ├── external_material_ingestion.py
    ├── external_descriptor_builder.py
    ├── external_material_validator.py
    ├── external_material_schema.py
    └── ...
```

The exact source-code placement can be adapted to the final repository
structure, but the distinction between documentation, machine-readable
schema, examples, and implementation should remain clear.

------------------------------------------------------------------------

# 21. Recommended Public Workflow

For ordinary use, the recommended v0.1 workflow is:

```text
1. Obtain or generate a valid CIF/POSCAR/CONTCAR
                         |
                         v
2. Assign a stable external ID
                         |
                         v
3. Run phase5_external_material_prepare.py
                         |
                         v
4. Inspect phase5_prepare_status.json
                         |
                         v
5. Confirm can_run_retrieval = true
                         |
                         v
6. Use external_descriptor_record.json
   as --external_json
                         |
                         v
7. Run run_context_pipeline.py
                         |
                         v
8. Inspect Material Profile, pools,
   evidence, RNF and SCP outputs
                         |
                         v
9. Optionally aggregate multiple
   external candidates in a batch
                         |
                         v
10. Optionally run Candidate Context Analysis
```

This workflow keeps external structure preparation explicit and
auditable while allowing the downstream framework to operate through the
same common Material Store and persisted pipeline contracts used
elsewhere.

------------------------------------------------------------------------

# 22. Worked Minimal Example

Assume the repository contains:

```text
examples/external/POSCAR
```

Prepare the structure:

```bash
python3 phase5_external_material_prepare.py \
  --external_structure examples/external/POSCAR \
  --external_format poscar \
  --external_id EXT-EXAMPLE-001 \
  --output_dir example_prepared/EXT-EXAMPLE-001
```

Inspect:

```text
example_prepared/EXT-EXAMPLE-001/phase5_prepare_status.json
```

Proceed only when the status reports:

```json
{
  "can_run_retrieval": true
}
```

Then run the main pipeline using:

```bash
python3 run_context_pipeline.py \
  --external_json example_prepared/EXT-EXAMPLE-001/external_descriptor_record.json \
  --external_id EXT-EXAMPLE-001 \
  --output_dir example_outputs/EXT-EXAMPLE-001 \
  --scripts_dir .
```

The external candidate is then profiled and contextualised against the
configured reference universe using the normal per-material pipeline.

------------------------------------------------------------------------

# 23. Limitations

The v0.1 external-input implementation has several important
limitations.

1.  **Structure-derived information is not equivalent to database
    metadata.**\
    Formation energy, energy above hull, synthesis status, and related
    fields are not inferred merely because a structure can be parsed.

2.  **Coordination and bonding quantities are inexpensive proxies.**\
    They depend on the configured distance cutoff and should not be
    interpreted as high-fidelity electronic or chemical bonding
    calculations.

3.  **Symmetry extraction depends on `pymatgen` analysis.**\
    Failure to obtain symmetry descriptors is retained explicitly rather
    than replaced with invented values.

4.  **Descriptor completeness is not the sole admission criterion.**\
    Critical retrieval fields must also be present.

5.  **The external candidate is reference-relative.**\
    Its RNF and downstream contextual interpretation depend on the
    configured reference corpus, descriptor state, retrieval
    configuration, and software version.

6.  **Automatic external IDs are not inherently permanent.**\
    Because the generated ID includes the preparation date, explicit
    stable IDs are preferable for durable published analyses.

7.  **The preparation and Material Store required-field lists are not
    perfectly aligned in the supplied v0.1 code.**\
    `n_elements`, `metal_count`, and `nonmetal_count` are required
    columns in the frozen Material Store but are omitted from the
    preparation module's copied `LRT_REQUIRED_DESCRIPTOR_FIELDS` list.
    The normal descriptor builder generates these composition fields,
    and `n_elements` is separately checked by the validator. This should
    be retained as a known implementation-contract issue until the lists
    are reconciled and regression-tested.

8.  **The external workflow does not establish downstream scientific
    utility.**\
    Successful ingestion and RNF construction demonstrate that an
    external structure can be processed by the framework. They do not by
    themselves establish that the resulting contextual representation
    improves candidate selection, property prediction, experimental
    success, or materials discovery.

------------------------------------------------------------------------

# 24. Data-Contract and Versioning Summary

The supplied external workflow uses the following schema/version
identifiers:

  -------------------------------------------------------------------------
  Artefact / contract                 Version
  ----------------------------------- -------------------------------------
  External material ingestion record  `phase5.external_material.v1`

  External descriptor report          `phase5.external_descriptor.v1`

  External validation report          `phase5.external_validation.v1`

  Material Store external             `phase5.material_store_external.v1`
  registration                        

  Downstream Material Profile         `phase1.material_profile.v1.2`
  -------------------------------------------------------------------------

Changes that alter field meaning, required fields, validation semantics,
descriptor calculations, or external-universe behaviour should be
versioned explicitly rather than silently changing the v0.1 contract.

------------------------------------------------------------------------

# 25. Relationship to Other Documentation

This document defines the external-material input and preparation
interface.

-   `README.md` should provide only the quick-start external-material
    example and link here for the full contract.
-   `METHODOLOGY.md` should describe why and how external candidates are
    contextualised scientifically, without duplicating the detailed file
    format.
-   `ARCHITECTURE.md` should describe the external-ingestion boundary,
    Material Store responsibility, and relationship to the reference
    universe.
-   `VALIDATION.md` should record empirical verification of the
    external-material workflow where such tests form part of the release
    evidence.
-   `CLAIMS.md` should define what the demonstrated external-input
    capability does and does not justify claiming.
-   `external_material.schema.json` should provide the machine-readable
    schema for the recommended external descriptor-record hand-off
    contract.

The human-readable documentation and machine-readable schema should be
maintained together when the external input contract changes.

------------------------------------------------------------------------

# 26. v0.1 External-Input Contract

For the v0.1 release, the intended public contract can be summarized as
follows:

> A user may supply a crystalline structure as CIF, POSCAR, or CONTCAR
> to the external preparation workflow. The preparation code parses the
> structure, generates the available inexpensive descriptors, records
> missing information explicitly, validates retrieval readiness, and
> produces an `external_descriptor_record.json`. When validation reports
> `can_run_retrieval = true`, that descriptor record can be registered
> through the Material Store and processed as an external query by the
> normal Reference-Neighbourhood Structural Context pipeline. The
> external material remains outside the reference universe by default.

This contract defines an implemented ingestion and analysis pathway. It
does not imply that unavailable physical properties have been inferred,
that the external material has been experimentally validated, or that
the resulting contextual representation has demonstrated downstream
materials-discovery benefit.
