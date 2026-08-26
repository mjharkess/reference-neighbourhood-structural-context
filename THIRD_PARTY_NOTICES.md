# THIRD_PARTY_NOTICES.md

## Reference-Neighbourhood Structural Context Framework

**Version:** v0.1 Draft\
**Project licence:** Apache License 2.0\
**Notice scope:** Direct third-party software dependencies identified
from the frozen 8 August 2026 source-code import graph, plus NIST JARVIS
reference data used by the framework\
**Verification date:** 9 August 2026

------------------------------------------------------------------------

# 1. Purpose

The Reference-Neighbourhood Structural Context Framework is licensed
under the Apache License, Version 2.0.

This file identifies third-party software and data sources directly used
by the frozen v0.1 implementation and records their applicable licensing
or attribution position.

The project's Apache-2.0 licence applies to the project's original
source code and documentation. It does not replace, modify, or supersede
the licences, copyright notices, terms of use, attribution requirements,
or disclaimers applicable to third-party software or data.

The frozen source-code import audit identified the following direct
external Python dependencies:

-   JARVIS-Tools (`jarvis`);
-   NumPy;
-   pandas;
-   pymatgen;
-   SciPy;
-   scikit-learn; and
-   Matplotlib.

Python standard-library modules and modules implemented within this
repository are not listed as third-party dependencies in this notice.

The full v0.1 development environment contains additional packages
recorded in `REPRODUCIBILITY.md` / the release environment freeze. Those
packages are not listed here merely because they happened to be
installed. This notice is intentionally based on direct imports in the
frozen project source.

------------------------------------------------------------------------

# 2. Distribution Assumption

The v0.1 source repository is intended to distribute the project's own
source code and documentation.

Third-party Python packages are expected to be installed independently
by users through the documented Python environment and are **not
vendored, copied, or bundled into this repository**.

Likewise, the project does **not** redistribute the generated JARVIS
reference datastore as part of the canonical v0.1 repository. Users
reconstruct the required reference data from the upstream JARVIS source
as described in `REPRODUCIBILITY.md`.

This distinction matters because redistribution of third-party source
code, binaries, data, or other materials may trigger additional notice,
licence-text, attribution, or other obligations under the relevant
upstream terms.

If a future release bundles third-party packages, compiled binaries,
copied source code, data snapshots, fonts, images, examples, or other
externally authored material, this notice must be reviewed and updated
before that release is distributed.

------------------------------------------------------------------------

# 3. Direct Third-Party Software Dependencies

## 3.1 JARVIS-Tools

**Imported package:** `jarvis`\
**Reference environment version:** `jarvis-tools==2026.3.10`\
**Upstream project:** NIST JARVIS-Tools\
**Maintainer/source:** National Institute of Standards and Technology
(NIST)\
**Licence / terms:** NIST Terms of Use for JARVIS-Tools

The JARVIS-Tools licence states that the software was developed by NIST
employees and is made available as a public service. Works of NIST
employees are not subject to copyright protection in the United States
under 17 U.S.C. §105, although foreign copyright may apply.

To the extent NIST may hold copyright, permission is granted to use,
copy, modify, create derivative works, and distribute the software and
documentation without fee on a non-exclusive basis, provided that the
NIST notice and disclaimer of warranty are preserved in copies.

**Upstream licence:**\
https://github.com/usnistgov/jarvis/blob/master/LICENSE.rst

**Project use:**\
The framework uses JARVIS-Tools for access to JARVIS material data and
related material/structure functionality.

**Attribution:**\
National Institute of Standards and Technology (NIST), JARVIS-Tools.

**Important:**\
This repository does not relicense JARVIS-Tools under Apache 2.0.

------------------------------------------------------------------------

## 3.2 NumPy

**Imported package:** `numpy`\
**Reference environment version:** `numpy==2.4.4`\
**Licence:** BSD 3-Clause / modified BSD licence\
**Copyright:** NumPy Developers and contributors

The NumPy licence permits redistribution and use in source and binary
forms, with or without modification, subject to preservation of the
required copyright notice, licence conditions, disclaimer, and
non-endorsement condition when redistribution occurs.

**Upstream licence:**\
https://numpy.org/doc/stable/license.html

**Project use:**\
Numerical arrays, numerical comparison, mathematical operations, and
analytical processing.

**Important:**\
NumPy is installed as an external dependency and is not relicensed by
this project.

------------------------------------------------------------------------

## 3.3 pandas

**Imported package:** `pandas`\
**Reference environment version:** `pandas==3.0.2`\
**Licence:** BSD 3-Clause\
**Copyright:** pandas/PyData contributors and other copyright holders
identified by the pandas project

The pandas licence permits redistribution and use in source and binary
forms, with or without modification, subject to the BSD 3-Clause
conditions.

**Upstream licence:**\
https://github.com/pandas-dev/pandas/blob/main/LICENSE

**Project use:**\
Tabular material data, candidate pools, summaries, batch outputs, and
cohort-analysis data structures.

**Important:**\
pandas itself includes or depends upon components with their own licence
notices. Because this repository does not redistribute pandas, those
upstream package notices remain part of the independently installed
pandas distribution. Any future bundling of pandas should preserve all
licence files supplied with the redistributed pandas package.

------------------------------------------------------------------------

## 3.4 pymatgen

**Imported package:** `pymatgen`\
**Reference environment versions:**\
- `pymatgen==2026.3.23` - `pymatgen-core==2026.3.9`

**Licence:** MIT License\
**Maintainer/source:** Materials Project / pymatgen Development Team

Pymatgen is released under the MIT License, which permits use, copying,
modification, distribution, sublicensing, and sale subject to
preservation of the applicable copyright and permission notice.

**Upstream project:**\
https://pymatgen.org/

**Project use:**\
Crystal-structure parsing and materials/structure analysis required by
the material-store, evidence, and external-material workflows.

**Important:**\
The framework does not distribute VASP pseudopotential/POTCAR data. Such
data are subject to separate VASP licensing arrangements and are not
required to be included in this repository for the documented v0.1
framework workflow.

------------------------------------------------------------------------

## 3.5 SciPy

**Imported package:** `scipy`\
**Reference environment version:** `scipy==1.17.1`\
**Licence:** BSD 3-Clause\
**Copyright:** SciPy developers and contributors

SciPy is distributed under the BSD 3-Clause licence.

**Upstream licence:**\
https://github.com/scipy/scipy/blob/main/LICENSE.txt

**Project use:**\
Scientific numerical routines used by Candidate Context Analysis.

**Important:**\
SciPy distributions may contain or link to bundled components carrying
additional compatible licence notices. Because this repository does not
redistribute SciPy binaries or source, those notices remain with the
separately installed SciPy distribution. A future binary bundle or
vendored distribution must reproduce the applicable notices supplied
with that SciPy package.

------------------------------------------------------------------------

## 3.6 scikit-learn

**Imported package:** `sklearn`\
**Reference environment version:** `scikit-learn==1.8.0`\
**Licence:** BSD 3-Clause\
**Copyright:** scikit-learn developers and contributors

Scikit-learn is distributed under the BSD 3-Clause licence.

**Upstream licence:**\
https://github.com/scikit-learn/scikit-learn/blob/main/COPYING

**Project use:**\
Clustering, dimensionality reduction / analytical transformations, and
related comparison functions used in the material-store and Candidate
Context Analysis paths.

**Important:**\
scikit-learn is installed as an external dependency and is not
relicensed by this project.

------------------------------------------------------------------------

## 3.7 Matplotlib

**Imported package:** `matplotlib`\
**Reference environment version:** `matplotlib==3.10.8`\
**Licence:** Matplotlib licence, based on the Python Software Foundation
licence and using BSD-compatible code\
**Copyright:** Matplotlib Development Team and contributors

Matplotlib's current project documentation states that it uses
BSD-compatible code and that its licence is based on the Python Software
Foundation licence.

**Upstream licence:**\
https://matplotlib.org/stable/project/license.html

**Project use:**\
Generation of Candidate Context Analysis figures and visual analytical
outputs.

**Important:**\
Matplotlib is installed as an external dependency and is not relicensed
by this project.

------------------------------------------------------------------------

# 4. NIST JARVIS Reference Data

## 4.1 Use in This Project

The framework uses JARVIS material data as the reference population from
which the v0.1 reference datastore is reconstructed.

The frozen material-store workflow obtains the named JARVIS datasets:

``` text
dft_3d
dft_2d
```

through JARVIS-Tools and creates local derived cache files as described
in `REPRODUCIBILITY.md`.

The canonical v0.1 repository does **not** redistribute those generated
JARVIS raw-data caches or the generated material descriptor cache.

## 4.2 Upstream Terms Remain Applicable

JARVIS data are obtained from NIST/JARVIS upstream sources. The
project's Apache-2.0 licence does not apply to upstream JARVIS data.

NIST publishes general copyright, fair-use, and licensing guidance for
NIST data and software and recommends explicit acknowledgement of NIST
as the source of NIST software/data where applicable.

NIST also notes that some NIST-hosted or NIST-provided materials may
contain third-party rights or may be governed by more specific terms.
Users remain responsible for complying with the terms applicable to the
data they obtain from the upstream source.

**NIST licensing guidance:**\
https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications

**JARVIS-Tools:**\
https://github.com/usnistgov/jarvis

## 4.3 Recommended Attribution

Publications, reports, or redistributed derived datasets produced using
JARVIS reference data should appropriately acknowledge NIST/JARVIS and
cite the relevant JARVIS dataset/software publications required by the
upstream project.

A suitable repository-level acknowledgement is:

> This project uses materials data obtained through NIST
> JARVIS/JARVIS-Tools. JARVIS data are not distributed as part of this
> repository; the reference datastore is reconstructed from the upstream
> JARVIS source. JARVIS/NIST data and software remain subject to their
> applicable upstream terms. The National Institute of Standards and
> Technology should be acknowledged as the source where applicable.

This acknowledgement is informational and does not replace any more
specific citation or attribution requested by NIST/JARVIS.

------------------------------------------------------------------------

# 5. Compatibility with the Project's Apache-2.0 Licence

The direct dependencies identified in the frozen v0.1 source are
permissively licensed or distributed under NIST public-service terms.

The repository's use of these packages as separately installed
dependencies does not require the project's own original source code to
adopt their licences.

The project may therefore license its original source under **Apache
License 2.0**, subject to the following boundaries:

1.  Apache 2.0 applies only to material for which the project has the
    right to grant that licence.
2.  Third-party packages retain their original licences and notices.
3.  JARVIS/NIST materials retain the applicable upstream terms.
4.  Third-party software or data should not be copied into the
    repository without first reviewing the redistribution obligations
    for that specific material.
5.  If future distributions bundle dependencies, the corresponding
    licence texts, notices, copyright statements, and any other required
    attribution should accompany the bundled material.

This file is intended to document the current third-party position and
is not legal advice.

------------------------------------------------------------------------

# 6. Packages Present in the Reproduction Environment but Not Directly Imported

The reference v0.1 `pip freeze` contains additional packages beyond
those listed above.

Examples include dependency packages and scientific/environment
utilities such as `joblib`, `threadpoolctl`, `python-dateutil`,
`pillow`, `packaging`, `numba`, `llvmlite`, `networkx`, and others.

They are retained in the v0.1 environment record for reproducibility but
are not individually listed in this document solely because they were
present in the environment.

Many are transitive dependencies of the direct packages above.

If the project later directly imports one of these packages, vendors it,
bundles it in a binary distribution, or otherwise redistributes it,
`THIRD_PARTY_NOTICES.md` should be reviewed and updated accordingly.

------------------------------------------------------------------------

# 7. No Third-Party Relicensing

Nothing in the project's `LICENSE` file or this notice should be
interpreted as:

-   relicensing JARVIS-Tools;
-   relicensing JARVIS/NIST data;
-   relicensing NumPy;
-   relicensing pandas;
-   relicensing pymatgen;
-   relicensing SciPy;
-   relicensing scikit-learn;
-   relicensing Matplotlib; or
-   granting permissions the project does not hold.

Use and redistribution of each third-party component remain governed by
its applicable upstream terms.

------------------------------------------------------------------------

# 8. Redistribution Review Trigger

This notice should be reviewed before any release that:

-   vendors third-party Python source;
-   distributes Python wheels or an application bundle containing
    third-party binaries;
-   packages a complete Python environment;
-   redistributes JARVIS data or generated raw-data snapshots;
-   distributes third-party example data;
-   incorporates third-party code directly into project source files;
-   adds a dependency under copyleft or otherwise materially different
    licence terms; or
-   changes the project's primary licence.

A source-only repository that declares external dependencies has a
materially different third-party-notice burden from a packaged
application that redistributes those dependencies.

------------------------------------------------------------------------

# 9. Verification Record

The direct dependency list in this notice was derived from an import
audit of the frozen 8 August 2026 project source.

External top-level imports found in the frozen source were:

``` text
jarvis
matplotlib
numpy
pandas
pymatgen
scipy
sklearn
```

The applicable upstream licence positions were checked against official
project/NIST sources on 9 August 2026.

This verification should be repeated if dependency versions, source
imports, packaging strategy, or upstream licence terms materially
change.

------------------------------------------------------------------------

# 10. Summary

For v0.1:

  ------------------------------------------------------------------------
  Component            Reference version Licence / terms  Distribution in
                                                          repository
  ---------------- --------------------- ---------------- ----------------
  JARVIS-Tools                 2026.3.10 NIST JARVIS      Not bundled
                                         Terms of Use     

  NumPy                            2.4.4 BSD 3-Clause     Not bundled

  pandas                           3.0.2 BSD 3-Clause     Not bundled

  pymatgen                     2026.3.23 MIT              Not bundled

  pymatgen-core                 2026.3.9 MIT              Not bundled

  SciPy                           1.17.1 BSD 3-Clause     Not bundled

  scikit-learn                     1.8.0 BSD 3-Clause     Not bundled

  Matplotlib                      3.10.8 Matplotlib /     Not bundled
                                         PSF-based,       
                                         BSD-compatible   

  JARVIS reference    `dft_3d`, `dft_2d` Applicable       Not
  data                                   NIST/JARVIS      redistributed;
                                         upstream data    reconstructed
                                         terms            upstream
  ------------------------------------------------------------------------

The project's own source and documentation are distributed under Apache
License 2.0. Third-party components and data remain governed by their
respective upstream terms.
