<!---
Changelog headings can be any of:

Added: for new features.
Changed: for changes in existing functionality.
Deprecated: for soon-to-be removed features.
Removed: for now removed features.
Fixed: for any bug fixes.
Security: in case of vulnerabilities.

Release headings should be of the form:
## [X.Y.Z] - YEAR-MONTH-DAY
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

* Fixed summary report:
  * Intermodal Access/Egress reporting is more general (not expecting just car and bike mode access to PT) [#204](https://github.com/arup-group/genet/pull/204)
  * Node/Links numbers were reported incorrectly (switched) [#207](https://github.com/arup-group/genet/pull/207)
* Fixed reading `java.lang.Array` types in MATSim xml files [#216](https://github.com/arup-group/genet/pull/216)
* Fixed problem snapping and routing PT services with stops whose names started with 'x' [#225](https://github.com/arup-group/genet/pull/225)
* Fixed issues saving geodataframes with missing geometry values, refined how geodataframes with empty values are saved to keep them more true to originals [#226](https://github.com/arup-group/genet/pull/226)

### Changed

* GeNet's pre-baked python scripts have been retired in favour of CLI [#194](https://github.com/arup-group/genet/pull/194)
* Support for python v3.11 [#192](https://github.com/arup-group/genet/pull/192) and v3.12 [#234](https://github.com/arup-group/genet/pull/234)
* **[Breaking change]** Updated to more accurate pyproj version [#192](https://github.com/arup-group/genet/pull/192)
* **[Breaking change]** Update `Route.route` _attribute_ to `Route.network_links` to differentiate it from the `Route.route` _method_. `Route` instantiation argument `route` is also now `network_links` [#231](https://github.com/arup-group/genet/pull/231)

## [v4.0.0] - 2023-08-22

### Added

* Validation for [intermodal access/egress for MATSim](https://github.com/matsim-org/matsim-libs/tree/master/contribs/sbb-extensions#intermodal-access-and-egress)
* GeNet Scripts for: [#179](https://github.com/arup-group/genet/pull/179)
  * automated PT Schedule fixing (zero headways and infinite speeds)
  * 'squeezing' (or reducing attribute values) speed and capacity on links defined by spatial boundaries
  * scaling vehicles (separately from any other operation, so it can be performed independently)
* Script to split modal subgraphs (so they have dedicated links) [#153](https://github.com/arup-group/genet/pull/153)
* Validation checks for zero and infinite speeds PT speeds + many convenience methods [#147](https://github.com/arup-group/genet/pull/147)
* Validation checks for zero headways and reporting on PT headway stats + many convenience methods [#146](https://github.com/arup-group/genet/pull/146)
* Validation checks for isolated nodes and method to remove all isolated nodes [#143](https://github.com/arup-group/genet/pull/143)
* Validation checks for infinite and negative values of attributes for a network [#141](https://github.com/arup-group/genet/pull/141)
* Functionality to split a link at a point, creating two links which preserve original geometry [#140](https://github.com/arup-group/genet/pull/140)
* Ability to use .tif files for elevation with any projection [#139](https://github.com/arup-group/genet/pull/139)
* Summary statistics to summarise data stored for a network and schedule [#136](https://github.com/arup-group/genet/pull/136)
* Script that adds elevation can also save node attributes [#134](https://github.com/arup-group/genet/pull/134)
* Script to parse example jupyter notebook to genet wiki pages (useful if you contribute to the project) [#129](https://github.com/arup-group/genet/pull/129)

### Fixed

* Schema breaking for nested lists (representing trips information, for example) when merging objects wholesale [#173](https://github.com/arup-group/genet/pull/173)
* Schema breaking when generating trips from headways [#159](https://github.com/arup-group/genet/pull/159)
* Small bugs in script that adds elevation [#134](https://github.com/arup-group/genet/pull/134) & [#170](https://github.com/arup-group/genet/pull/170)

### Changed

* GeNet Scripts got a re-vamp, making them more consistent in behaviour (output folder naming and minimal outputs (usually geojsons) tracking changes made by the scripts) [#179](https://github.com/arup-group/genet/pull/179)
* Length attribute is calculated automatically, using nodes' spatial information, if not provided [#161](https://github.com/arup-group/genet/pull/161)
* Elevation Script writes the MATSim slope file [#158](https://github.com/arup-group/genet/pull/158)
* **[Breaking change]** Spatial information is now compulsory when adding new nodes [#142](https://github.com/arup-group/genet/pull/142)

## [v3.0.0] - 2022-07-14

### Added

* Addition of elevation and slope data to networks using [STRM](https://srtm.csi.cgiar.org/srtmdata/) files
* Vehicle capacity and pce scaling
  * Conveniently save multiple `vehicle.xml` files for use with simulations at different scales: 1%, 5%, 10%, etc.
* Ability to read and write additional attributes for different network and schedule elements
  * Allows you to pass any data to network links and nodes, PT schedule stops, routes and services and have it be
  saved to the MATSim network
* Multimodal access/egress for PT stops
  * Script to add attributes to PT stops of various PT modes that allow agents to
  access via network or teleported modes

### Changed

* **[Breaking change]** New, **default**, representation of additional attributes
    ```python
    'attributes': {
      'osm:way:highway': 'primary'
    }
    ```
    Instead of:
    ```python
    'attributes': {
      'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}
    }
    ```
  * Crucially, this will affect methods that search for different values of OSM data, for example: find all links
  of `highway` type `primary`, or links with particular OSM IDs.
  * For backwards compatibility, use: `force_long_form_attributes=True` when reading the network and/or schedule
  objects
* **[Breaking change]** folders renamed:
  * `inputs_handler` -> `input`
  * `outputs_handler` -> `output`

## [v2.0.1-snapshot] - 2022-04-08

### Changed

* Loosen version constraints for various pytest-related dependencies by @mfitz in https://github.com/arup-group/genet/pull/114

**Full Changelog**: https://github.com/arup-group/genet/compare/v2.0.0-snapshot...v2.0.1-snapshot

## [v2.0.0-snapshot] - 2022-04-07

Not production ready. No release notes other than the automated ones generated from commits.

### Changed

* update readme by @KasiaKoz in https://github.com/arup-group/genet/pull/53
* Fix simplifications script's help message (LAB-990) by @mfitz in https://github.com/arup-group/genet/pull/54
* Make link 'oneway' attribute optional when writing networks to disk by @mfitz in https://github.com/arup-group/genet/pull/56
* Schedule usage and modification by @KasiaKoz in https://github.com/arup-group/genet/pull/57
* Lab 1046 ValueError: cannot set a frame with no defined index and a scalar by @KasiaKoz in https://github.com/arup-group/genet/pull/63
* Lab 1045 speed up validation by @KasiaKoz in https://github.com/arup-group/genet/pull/64
* Lab 865 persistent benchmarks by @KasiaKoz in https://github.com/arup-group/genet/pull/59
* Lab 1014 NZ overflow by @KasiaKoz in https://github.com/arup-group/genet/pull/62
* add checks for zero value attributes on links to validation report by @KasiaKoz in https://github.com/arup-group/genet/pull/67
* Mf lab 1051 notebook smoketests by @mfitz in https://github.com/arup-group/genet/pull/68
* Lab 583 support vehicles by @KasiaKoz in https://github.com/arup-group/genet/pull/58
* Lab 1075 split service by direction by @KasiaKoz in https://github.com/arup-group/genet/pull/65
* Spatial methods to support snapping to links by @KasiaKoz in https://github.com/arup-group/genet/pull/66
* update google directions sending script by @KasiaKoz in https://github.com/arup-group/genet/pull/69
* use sets in route and service indexing on schedule graph by @KasiaKoz in https://github.com/arup-group/genet/pull/70
* Fix multi edge simplify bug by @KasiaKoz in https://github.com/arup-group/genet/pull/76
* add missing always_xy=True to a couple of transformers by @KasiaKoz in https://github.com/arup-group/genet/pull/78
* Support for new data types when reading/writing networks by @KasiaKoz in https://github.com/arup-group/genet/pull/73
* Bump pyyaml from 5.3.1 to 5.4 by @dependabot in https://github.com/arup-group/genet/pull/71
* Bump pygments from 2.6.1 to 2.7.4 by @dependabot in https://github.com/arup-group/genet/pull/72
* Fix network simplification script by @mfitz in https://github.com/arup-group/genet/pull/79
* Fix scripts by @KasiaKoz in https://github.com/arup-group/genet/pull/80
* add vehicles arg to readme by @gac55 in https://github.com/arup-group/genet/pull/83
* Add manifest by @mfitz in https://github.com/arup-group/genet/pull/85
* Update requirements by @KasiaKoz in https://github.com/arup-group/genet/pull/86
* Lab 1226 Refine Road Pricing by @KasiaKoz in https://github.com/arup-group/genet/pull/84
* import cordon class to be available at the highest genet level by @KasiaKoz in https://github.com/arup-group/genet/pull/87
* required python dependencies by @syhwawa in https://github.com/arup-group/genet/pull/88
* Make S3 code bucket a CI build variable by @mfitz in https://github.com/arup-group/genet/pull/92
* Parallel unit tests by @KasiaKoz in https://github.com/arup-group/genet/pull/89
* Connect disconnected subgraphs by @KasiaKoz in https://github.com/arup-group/genet/pull/91
* PT network route GeoDataFrame and geojson output by @KasiaKoz in https://github.com/arup-group/genet/pull/90
* add reprojection param to general standard network geojson outputs by @KasiaKoz in https://github.com/arup-group/genet/pull/95
* Fix runtime warnings by @mfitz in https://github.com/arup-group/genet/pull/94
* Lab 1315 kepler viz by @KasiaKoz in https://github.com/arup-group/genet/pull/97
* Vehicle checks by @ana-kop in https://github.com/arup-group/genet/pull/96
* Minor changes to the fixture names that weren't commited earlier by @ana-kop in https://github.com/arup-group/genet/pull/100
* Lab 1077 max stable set by @KasiaKoz in https://github.com/arup-group/genet/pull/98
* Lab 1378 iron out goog api by @ana-kop in https://github.com/arup-group/genet/pull/101
* Osm read fix by @KasiaKoz in https://github.com/arup-group/genet/pull/99
* PT headways by @KasiaKoz in https://github.com/arup-group/genet/pull/102
* Sub network/schedule by @KasiaKoz in https://github.com/arup-group/genet/pull/103
* Bump ipython from 7.14.0 to 7.16.3 by @dependabot in https://github.com/arup-group/genet/pull/105
* upgrade protobuf by @KasiaKoz in https://github.com/arup-group/genet/pull/106
* Allow set attribute values prior to simplification by @KasiaKoz in https://github.com/arup-group/genet/pull/108
* Fix loopy simplification by @KasiaKoz in https://github.com/arup-group/genet/pull/107
* Update CONTRIBUTING.md by @mfitz in https://github.com/arup-group/genet/pull/109
* Upgrade nbconvert dependency version by @mfitz in https://github.com/arup-group/genet/pull/111
* Generalise road pricing type by @KasiaKoz in https://github.com/arup-group/genet/pull/110
* Reduce Docker image size by @mfitz in https://github.com/arup-group/genet/pull/113
* Add/Remove Services and Routes in groups by @KasiaKoz in https://github.com/arup-group/genet/pull/112

### New Contributors

* @syhwawa made their first contribution in https://github.com/arup-group/genet/pull/88
* @ana-kop made their first contribution in https://github.com/arup-group/genet/pull/96

**Full Changelog**: https://github.com/arup-group/genet/compare/v1.0.0...v2.0.0-snapshot

## [v1.0.0] - 2021-02-01

### Initial release

This is the first release, please check documentation/wiki for the usage guide