# [v3.0.0]

## What's Changed
* Addition of elevation and slope data to networks using DEM by @ana-kop in https://github.com/arup-group/genet/pull/115 and https://github.com/arup-group/genet/pull/120
* Daily CI builds by @mfitz in https://github.com/arup-group/genet/pull/116
* Vehicle capacity and pce scaling by @elizabethc-arup in https://github.com/arup-group/genet/pull/104
* Additional attributes for network and schedule elements by @KasiaKoz in https://github.com/arup-group/genet/pull/118
* Multimodal access/egress for PT stops by @KasiaKoz in https://github.com/arup-group/genet/pull/119
* **[Breaking changes]** New, **default**, representation of additional attributes by @KasiaKoz in https://github.com/arup-group/genet/pull/124
    * For backwards compatibility, use: `force_long_form_attributes=True` when reading the network and/or schedule objects
* **[Breaking changes]** folders renamed:
    * `inputs_handler` -> `input`
    * `outputs_handler` -> `output` 

# [v2.0.1-snapshot]

## What's Changed
* Loosen version constraints for various pytest-related dependencies by @mfitz in https://github.com/arup-group/genet/pull/114


**Full Changelog**: https://github.com/arup-group/genet/compare/v2.0.0-snapshot...v2.0.1-snapshot

# [v2.0.0-snapshot]

Not production ready. No release notes other than the automated ones generated from commits.

## What's Changed
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

## New Contributors
* @syhwawa made their first contribution in https://github.com/arup-group/genet/pull/88
* @ana-kop made their first contribution in https://github.com/arup-group/genet/pull/96

**Full Changelog**: https://github.com/arup-group/genet/compare/v1.0.0...v2.0.0-snapshot

# [v1.0.0]

# Initial release

This is the first release, please check documentation/wiki for the usage guide