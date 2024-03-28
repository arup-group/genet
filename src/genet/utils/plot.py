from copy import deepcopy
from typing import Optional, Union

import geopandas as gpd
import keplergl


def plot_geodataframes_on_kepler_map(
    gdfs: dict[str, gpd.GeoDataFrame],
    height: int = 750,
    kepler_config: Optional[Union[dict, str]] = None,
) -> keplergl.KeplerGl:
    """Plots geodataframes on a kepler map.

    Args:
        gdfs (dict[str, gpd.GeoDataFrame]): {'gdf name': gdf} dictionary of geodataframes.
        height (int, optional): height for the kepler map. Defaults to 750.
        kepler_config (Optional[dict | str], optional): If given, kepler config or one of the keys in the predefined configs in KEPLER_CONFIGS. Defaults to None.

    Returns:
        keplergl.KeplerGl: Kepler plot object
    """
    if isinstance(kepler_config, str) and kepler_config in KEPLER_CONFIGS:
        kepler_config = KEPLER_CONFIGS[kepler_config]
    elif isinstance(kepler_config, dict):
        kepler_config = kepler_config
    else:
        kepler_config = {}
    return keplergl.KeplerGl(data=gdfs, height=height, config=kepler_config)


KEPLER_CONFIGS = {
    "base_config": {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {},
                        "compareMode": False,
                        "compareType": "absolute",
                        "enabled": True,
                    },
                    "brush": {"size": 0.5, "enabled": False},
                    "geocoder": {"enabled": False},
                    "coordinate": {"enabled": False},
                },
                "layerBlending": "normal",
                "splitMaps": [],
                "animationConfig": {"currentTime": None, "speed": 1},
            },
            "mapStyle": {
                "styleType": "dark",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": False,
                    "road": True,
                    "border": False,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False,
                },
                "threeDBuildingColor": [9.665468314072013, 17.18305478057247, 31.1442867897876],
                "mapStyles": {},
            },
        },
    }
}
LAYERS = {
    "network_links": {
        "fieldsToShow": {
            "network_links": [
                {"name": "id", "format": None},
                {"name": "from", "format": None},
                {"name": "to", "format": None},
                {"name": "freespeed", "format": None},
                {"name": "capacity", "format": None},
            ]
        },
        "layer": {
            "id": "network_links",
            "type": "geojson",
            "config": {
                "dataId": "network_links",
                "label": "network_links",
                "color": [227, 227, 227],
                "highlightColor": [252, 242, 26, 255],
                "columns": {"geojson": "geometry"},
                "isVisible": True,
                "visConfig": {
                    "opacity": 0.8,
                    "strokeOpacity": 0.8,
                    "thickness": 0.5,
                    "strokeColor": None,
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": True,
                    "filled": False,
                    "enable3d": False,
                    "wireframe": False,
                },
                "hidden": False,
                "textLabel": [
                    {
                        "field": None,
                        "color": [255, 255, 255],
                        "size": 18,
                        "offset": [0, 0],
                        "anchor": "start",
                        "alignment": "center",
                    }
                ],
            },
            "visualChannels": {
                "colorField": None,
                "colorScale": "quantize",
                "strokeColorField": None,
                "strokeColorScale": "quantize",
                "sizeField": None,
                "sizeScale": "linear",
                "heightField": None,
                "heightScale": "linear",
                "radiusField": None,
                "radiusScale": "linear",
            },
        },
    },
    "schedule_routes": {
        "fieldsToShow": {
            "schedule_routes": [
                {"name": "route_id", "format": None},
                {"name": "mode", "format": None},
                {"name": "route_short_name", "format": None},
                {"name": "service_id", "format": None},
            ]
        },
        "layer": {
            "id": "schedule_routes",
            "type": "geojson",
            "config": {
                "dataId": "schedule_routes",
                "label": "schedule_routes",
                "color": [30, 150, 190],
                "highlightColor": [252, 242, 26, 255],
                "columns": {"geojson": "geometry"},
                "isVisible": True,
                "visConfig": {
                    "opacity": 0.8,
                    "strokeOpacity": 0.49,
                    "thickness": 1.8,
                    "strokeColor": None,
                    "strokeColorRange": {
                        "name": "Uber Viz Qualitative 4",
                        "type": "qualitative",
                        "category": "Uber",
                        "colors": [
                            "#12939A",
                            "#DDB27C",
                            "#88572C",
                            "#FF991F",
                            "#F15C17",
                            "#223F9A",
                            "#DA70BF",
                            "#125C77",
                            "#4DC19C",
                            "#776E57",
                            "#17B8BE",
                            "#F6D18A",
                            "#B7885E",
                            "#FFCB99",
                            "#F89570",
                            "#829AE3",
                            "#E79FD5",
                            "#1E96BE",
                            "#89DAC1",
                            "#B3AD9E",
                        ],
                    },
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": True,
                    "filled": False,
                    "enable3d": False,
                    "wireframe": False,
                },
                "hidden": False,
                "textLabel": [
                    {
                        "field": None,
                        "color": [255, 255, 255],
                        "size": 18,
                        "offset": [0, 0],
                        "anchor": "start",
                        "alignment": "center",
                    }
                ],
            },
            "visualChannels": {
                "colorField": None,
                "colorScale": "quantize",
                "strokeColorField": {"name": "mode", "type": "string"},
                "strokeColorScale": "ordinal",
                "sizeField": None,
                "sizeScale": "linear",
                "heightField": None,
                "heightScale": "linear",
                "radiusField": None,
                "radiusScale": "linear",
            },
        },
    },
    "schedule_links": {
        "fieldsToShow": {
            "schedule_links": [{"name": "u", "format": None}, {"name": "v", "format": None}]
        },
        "layer": {
            "id": "schedule_links",
            "type": "geojson",
            "config": {
                "dataId": "schedule_links",
                "label": "schedule_links",
                "color": [249, 168, 37],
                "highlightColor": [252, 242, 26, 255],
                "columns": {"geojson": "geometry"},
                "isVisible": True,
                "visConfig": {
                    "opacity": 0.8,
                    "strokeOpacity": 0.8,
                    "thickness": 0.5,
                    "strokeColor": None,
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": True,
                    "filled": False,
                    "enable3d": False,
                    "wireframe": False,
                },
                "hidden": False,
                "textLabel": [
                    {
                        "field": None,
                        "color": [255, 255, 255],
                        "size": 18,
                        "offset": [0, 0],
                        "anchor": "start",
                        "alignment": "center",
                    }
                ],
            },
            "visualChannels": {
                "colorField": None,
                "colorScale": "quantize",
                "strokeColorField": None,
                "strokeColorScale": "quantize",
                "sizeField": None,
                "sizeScale": "linear",
                "heightField": None,
                "heightScale": "linear",
                "radiusField": None,
                "radiusScale": "linear",
            },
        },
    },
    "schedule_stops": {
        "fieldsToShow": {
            "schedule_stops": [
                {"name": "id", "format": None},
                {"name": "x", "format": None},
                {"name": "y", "format": None},
                {"name": "name", "format": None},
                {"name": "linkRefId", "format": None},
            ]
        },
        "layer": {
            "id": "schedule_stops",
            "type": "point",
            "config": {
                "dataId": "schedule_stops",
                "label": "schedule_stops",
                "color": [249, 95, 37],
                "highlightColor": [252, 242, 26, 255],
                "columns": {"lat": "lat", "lng": "lon", "altitude": None},
                "isVisible": True,
                "visConfig": {
                    "opacity": 0.8,
                    "strokeOpacity": 0.8,
                    "thickness": 0.5,
                    "strokeColor": None,
                    "radius": 10,
                    "sizeRange": [0, 10],
                    "radiusRange": [0, 50],
                    "heightRange": [0, 500],
                    "elevationScale": 5,
                    "enableElevationZoomFactor": True,
                    "stroked": False,
                    "filled": True,
                    "enable3d": False,
                    "wireframe": False,
                },
                "hidden": False,
                "textLabel": [
                    {
                        "field": {"name": "name", "type": "string"},
                        "color": [255, 255, 255],
                        "size": 11,
                        "offset": [0, 0],
                        "anchor": "start",
                        "alignment": "center",
                    }
                ],
            },
            "visualChannels": {
                "colorField": None,
                "colorScale": "quantize",
                "strokeColorField": None,
                "strokeColorScale": "quantize",
                "sizeField": None,
                "sizeScale": "linear",
                "heightField": None,
                "heightScale": "linear",
                "radiusField": None,
                "radiusScale": "linear",
            },
        },
    },
}

KEPLER_CONFIGS["network_with_pt"] = deepcopy(KEPLER_CONFIGS["base_config"])
KEPLER_CONFIGS["network_with_pt"]["config"]["visState"]["layers"] = [
    LAYERS["network_links"]["layer"],
    LAYERS["schedule_routes"]["layer"],
]
KEPLER_CONFIGS["network_with_pt"]["config"]["visState"]["interactionConfig"]["tooltip"][
    "fieldsToShow"
] = {**LAYERS["network_links"]["fieldsToShow"], **LAYERS["schedule_routes"]["fieldsToShow"]}

KEPLER_CONFIGS["schedule"] = deepcopy(KEPLER_CONFIGS["base_config"])
KEPLER_CONFIGS["schedule"]["config"]["visState"]["layers"] = [
    LAYERS["schedule_links"]["layer"],
    LAYERS["schedule_stops"]["layer"],
]
KEPLER_CONFIGS["schedule"]["config"]["visState"]["interactionConfig"]["tooltip"]["fieldsToShow"] = {
    **LAYERS["schedule_links"]["fieldsToShow"],
    **LAYERS["schedule_stops"]["fieldsToShow"],
}

KEPLER_CONFIGS["network_and_schedule"] = deepcopy(KEPLER_CONFIGS["base_config"])
KEPLER_CONFIGS["network_and_schedule"]["config"]["visState"]["layers"] = [
    LAYERS["network_links"]["layer"],
    LAYERS["schedule_links"]["layer"],
    LAYERS["schedule_stops"]["layer"],
]
KEPLER_CONFIGS["network_and_schedule"]["config"]["visState"]["interactionConfig"]["tooltip"][
    "fieldsToShow"
] = {
    **LAYERS["network_links"]["fieldsToShow"],
    **LAYERS["schedule_links"]["fieldsToShow"],
    **LAYERS["schedule_stops"]["fieldsToShow"],
}
