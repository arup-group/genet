import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import click
import geopandas as gpd
import pandas as pd
from pyproj import CRS

import genet
import genet.output.sanitiser as sanitiser
import genet.utils.spatial as spatial
from genet import google_directions, read_gtfs, read_matsim, read_matsim_schedule, read_osm
from genet.core import Network
from genet.output.geojson import (
    generate_headway_geojson,
    generate_speed_geojson,
    modal_subset,
    save_geodataframe,
)
from genet.utils.persistence import ensure_dir
from genet.variables import EPSG4326

logging.basicConfig(level=logging.INFO, format="%(levelname)-3s %(message)s")
logger = logging.getLogger(__name__)


def _to_json(dict_to_save: dict, filepath: Path) -> None:
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(sanitiser.sanitise_dictionary(dict_to_save), f, ensure_ascii=False, indent=4)


def _write_scaled_vehicles(schedule, list_of_scales, output_dir):
    for i in list_of_scales:
        scale = float(i) / 100
        schedule.scale_vehicle_capacity(scale, scale, output_dir)


def _generate_validation_report(network, output_dir: Path) -> None:
    logging.info("Generating validation report")
    report = network.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if network.schedule:
        logging.info(
            f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}'
        )
        if "vehicle level" in report["schedule"]:
            logging.info(
                f'Schedule vehicle level validation: {report["schedule"]["vehicle_level"]["vehicle_definitions_valid"]}'
            )
        logging.info(
            f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}'
        )

    _to_json(report, output_dir / "validation_report.json")

    logging.info("Generating summary report")
    summary_report = network.summary_report()
    _to_json(summary_report, output_dir / "summary_report.json")


def _read_network(
    path_to_network: Path,
    projection: str,
    path_to_schedule: Optional[Path] = None,
    path_to_vehicles: Optional[Path] = None,
) -> Network:
    logging.info("Reading in network at {}".format(path_to_network))
    if path_to_schedule is not None:
        logging.info(f"Reading in schedule at {path_to_schedule}")
        if path_to_vehicles is not None:
            logging.info(f"Reading in vehicles at {path_to_vehicles}")
        else:
            logging.info(
                "No vehicles file given with the Schedule, vehicle types will be based on the default."
            )
    else:
        logging.info(
            "You have not passed the schedule.xml file when reading your network. "
            "If your network is road only, that is fine, otherwise if you mix and match them, you will have a bad time."
        )

    network = read_matsim(
        path_to_network=path_to_network.as_posix(),
        epsg=projection,
        path_to_schedule=path_to_schedule.as_posix() if path_to_schedule is not None else None,
        path_to_vehicles=path_to_vehicles.as_posix() if path_to_vehicles is not None else None,
    )
    return network


def _cast_catchment(network_spatial_tree, df_stops, distance):
    return network_spatial_tree.closest_links(
        gdf_points=df_stops, distance_radius=distance
    ).dropna()


def _find_closest_links_by_step(
    network_spatial_tree, df_stops, step_size=10, distance_threshold=None
):
    def threshold_reached(d):
        if distance_threshold is not None:
            return d <= distance_threshold
        else:
            return True

    distance = step_size
    logging.info(f"Processing catchment: {distance}")
    nodes = _cast_catchment(
        network_spatial_tree=network_spatial_tree,
        df_stops=df_stops.loc[:, ["id", "geometry"]].copy(),
        distance=distance,
    )
    nodes["catchment"] = distance
    stop_ids = set(df_stops["id"])

    while set(nodes.index) != stop_ids and threshold_reached(distance):
        # increase distance by step size until all stops have closest links or reached threshold
        distance += step_size
        logging.info(
            f"Processing catchment: {distance}, {len(stop_ids - set(nodes.index))} stops remaining"
        )
        _df = _cast_catchment(
            network_spatial_tree=network_spatial_tree,
            df_stops=df_stops.loc[
                df_stops["id"].isin(stop_ids - set(nodes.index)), ["id", "geometry"]
            ].copy(),
            distance=distance,
        )
        _df["catchment"] = distance
        nodes = pd.concat([nodes, _df])
    return nodes


def _generate_modal_network_geojsons(network, modes, output_dir, filename_suffix):
    logging.info(f"Generating visual outputs {filename_suffix}")
    gdf = network.to_geodataframe()["links"].to_crs(EPSG4326)
    for mode in modes:
        _gdf = gdf[gdf["modes"].apply(lambda x: mode in x)]
        _gdf["modes"] = _gdf["modes"].apply(lambda x: ",".join(sorted(list(x))))
        save_geodataframe(_gdf, f"mode_{mode}_{filename_suffix}", output_dir)


@click.version_option()
@click.group()
def cli():
    """GeNet Command Line Tool."""
    pass


def xml_file(filename: str, required: bool = True):
    if not required:
        kwargs = {"default": None}
    else:
        kwargs = {}

    def wrapper(func):
        return click.option(
            f"-{filename[0]}",
            f"--{filename}",
            f"path_to_{filename}",
            help=f"Location of the input {filename}.xml file",
            type=click.Path(exists=True, path_type=Path),
            required=required,
            **kwargs,
        )(func)

    return wrapper


def projection(func):
    return click.option(
        "-p",
        "--projection",
        help='The projection network is in, eg. "epsg:27700"',
        type=str,
        required=True,
    )(func)


def output_dir(func):
    return click.option(
        "-od",
        "--output_dir",
        help="Output directory",
        type=click.Path(
            exists=False, file_okay=False, dir_okay=True, writable=True, path_type=Path
        ),
        required=True,
    )(func)


def osm(required: bool = True):
    if not required:
        kwargs = {"default": None}
    else:
        kwargs = {}
    path_type = click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path)

    def wrapper(func):
        func = click.option(
            "-o",
            "--osm",
            "path_to_osm",
            help="Location of the osm file",
            required=required,
            type=path_type,
            **kwargs,
        )(func)
        return click.option(
            "-oc",
            "--osm_config",
            "path_to_osm_config",
            help="Location of the config file defining what and how to read from the osm file",
            required=required,
            type=path_type,
            **kwargs,
        )(func)

    return wrapper


def gtfs(func):
    func = click.option(
        "-g",
        "--gtfs",
        "path_to_gtfs",
        help="Location of the gtfs zip file of folder with gtfs text files",
        required=True,
        type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
    )(func)
    return click.option(
        "-gd",
        "--gtfs_day",
        help="gtfs day to use in the format `YYYYMMDD`",
        required=True,
        type=str,
    )(func)


def processes(func):
    return click.option(
        "-pp",
        "--processes",
        help="Number of parallel processes to split process across",
        default=1,
        type=int,
        required=False,
    )(func)


def vehicle_scalings(func):
    return click.option(
        "-vsc",
        "--vehicle_scalings",
        help="Comma delimited list of scales for vehicles",
        required=False,
        type=str,
        default="1,10",
    )(func)


def subset_conditions(func):
    return click.option(
        "-sc",
        "--subset_conditions",
        help="Comma delimited list of values to subset the network by using attributes-osm:way:highway "
        "network attributes, e.g., `primary,motorway`"
        "{'attributes': {'osm:way:highway': VALUE(S)'}}",
        required=False,
        type=str,
        default=None,
    )(func)


def squeeze_args(func):
    func = click.option(
        "-sa",
        "--study_area",
        "path_to_study_area",
        help="Geojson or shp file that when read into geopandas produces a table with a geometry "
        "column that describes the area which should be left unaffected by speed and "
        "capacity factors.",
        required=False,
        type=click.Path(exists=True, path_type=Path),
        default=None,
    )(func)
    func = click.option(
        "-f",
        "--freespeed",
        help="Factor, e.g. 0.5, to reduce the 'freespeed' attribute for the roads being squeezed. "
        "The current value will be multiplied by this factor.",
        required=False,
        type=float,
        default=1,
    )(func)
    return click.option(
        "-c",
        "--capacity",
        help="Factor, e.g. 0.5, to reduce the 'capacity' attribute for the roads being squeezed. "
        "The current value will be multiplied by this factor.",
        required=False,
        type=float,
        default=1,
    )(func)


@cli.command()
@xml_file("network")
@projection
@output_dir
@click.option(
    "-el",
    "--elevation",
    "path_to_elevation",
    help="Path to the elevation tif file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
@click.option(
    "-nv",
    "--null_value",
    help="Value that represents null in the elevation tif file",
    default=0.0,
    type=float,
)
# this and below are negation flags.
# I.e., the default is True, defining this argument will set the boolean value of `write_elevation_to_network` to False.
@click.option(
    "-nwe",
    "--no-write_elevation_to_network",
    "write_elevation_to_network",
    help="Do not write node elevation data as attribute to the network",
    default=True,
    is_flag=True,
)
@click.option(
    "-nwsn",
    "--no-write_slope_to_network",
    "write_slope_to_network",
    help="Do not write link slope data as attribute to the network",
    default=True,
    is_flag=True,
)
@click.option(
    "-nwsoa",
    "--no-write_slope_to_object_attribute_file",
    "write_slope_to_object_attribute_file",
    help="Do not write link slope data to object attribute file",
    default=True,
    is_flag=True,
)
@click.option(
    "-nsj",
    "--no-save_jsons",
    "save_jsons",
    help="Do not save elevation and slope dictionaries and report",
    default=True,
    is_flag=True,
)
def add_elevation_to_network(
    path_to_network: Path,
    projection: str,
    path_to_elevation: Path,
    null_value: Any,
    output_dir: Path,
    write_elevation_to_network: bool,
    write_slope_to_network: bool,
    write_slope_to_object_attribute_file: bool,
    save_jsons: bool,
):
    """Add elevation data to network nodes, validate it, and calculate link slopes."""
    supporting_outputs = output_dir / "supporting_outputs"
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    network = _read_network(path_to_network, projection)

    logging.info("Creating elevation dictionary for network nodes")
    elevation = network.get_node_elevation_dictionary(
        elevation_tif_file_path=path_to_elevation.as_posix(), null_value=null_value
    )

    if save_jsons:
        _to_json(elevation, output_dir / "node_elevation_dictionary.json")

    logging.info("Validating the node elevation data")
    report = genet.elevation.validation_report_for_node_elevation(elevation)
    logging.info(report["summary"])

    if save_jsons:
        _to_json(report, output_dir / "validation_report_for_elevation.json")

    if write_elevation_to_network:
        logging.info("Adding node elevation as attribute to the network")
        node_attrib_dict = {}
        for node_id in elevation.keys():
            elevation_value = elevation[node_id]["z"]
            node_attrib_dict[node_id] = {"z": elevation_value}
        network.apply_attributes_to_nodes(node_attrib_dict)

        gdf_nodes = network.to_geodataframe()["nodes"]
        gdf_nodes = gdf_nodes[["id", "z", "geometry"]]
        save_geodataframe(gdf_nodes.to_crs(EPSG4326), "node_elevation", supporting_outputs)

    logging.info("Creating slope dictionary for network links")
    slope_dictionary = network.get_link_slope_dictionary(elevation_dict=elevation)

    if save_jsons:
        _to_json(slope_dictionary, output_dir / "link_slope_dictionary.json")

    if write_slope_to_network:
        logging.info("Adding link slope as an additional attribute to the network")
        attrib_dict = {}
        for link_id in slope_dictionary.keys():
            slope_value = slope_dictionary[link_id]["slope"]
            attrib_dict[link_id] = {
                "attributes": {
                    "slope": {"name": "slope", "class": "java.lang.String", "text": slope_value}
                }
            }
        network.apply_attributes_to_links(attrib_dict)

        gdf = network.to_geodataframe()["links"]
        df = pd.DataFrame(list(slope_dictionary.items()), columns=["id", "slope_tuple"])
        df["slope"] = [x["slope"] for x in df["slope_tuple"]]
        df = df[["id", "slope"]]
        gdf_links = pd.merge(gdf, df, on="id")
        save_geodataframe(gdf_links.to_crs(EPSG4326), "link_slope", supporting_outputs)

    if write_slope_to_object_attribute_file:
        genet.elevation.write_slope_xml(slope_dictionary, output_dir)

    logging.info("Writing the updated network")
    network.write_to_matsim(output_dir)


@cli.command()
@xml_file("network")
@xml_file("schedule")
@xml_file("vehicles", False)
@projection
@vehicle_scalings
@output_dir
def auto_schedule_fixes(
    path_to_network: Path,
    path_to_schedule: Path,
    path_to_vehicles: Optional[Path],
    projection: str,
    output_dir: Path,
    vehicle_scalings: Optional[str],
):
    """Script to check and correct, if needed, the speed and headway of services in the schedule.

    Checks and corrects for:
       - zero headways - we check that there are no 0 minute headways.
         that would mean two of the same trips start at the same time.
         To correct this we delete one of the trips, treating it as a duplicate.
       - infinite speeds - We calculate speed between each stop pair for services.
         We use the declared times at stops and crow-fly distance * 1.3 network factor.
         This is done also for routed modes like bus to simplify things,
         as we are only after infinite speeds which will show up whether we use the true route or not.
         Infinite speeds exist as a consequence of division by zero (time).
         This is corrected by recalculating the arrival and departure times at the problem stops;
         the times at other stops are kept the same as much as possible.
    """
    ensure_dir(output_dir)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.WARNING)
    network = _read_network(path_to_network, projection, path_to_schedule, path_to_vehicles)

    gdf = network.schedule_network_routes_geodataframe().to_crs(EPSG4326)

    logging.info("Checking for zero headways")
    if network.schedule.has_trips_with_zero_headways():
        generate_headway_geojson(network, gdf, output_dir, "before")
        network.schedule.fix_trips_with_zero_headways()
        generate_headway_geojson(network, gdf, output_dir, "after")
    else:
        logging.info("No trips with zero headways were found")

    logging.info("Checking for infinite speeds")
    if network.schedule.has_infinite_speeds():
        generate_speed_geojson(network, gdf, output_dir, "before")
        network.schedule.fix_infinite_speeds()
        generate_speed_geojson(network, gdf, output_dir, "after")
    else:
        logging.info("No routes with infinite speeds were found")

    logging.info(f"Saving network in {output_dir}")
    network.write_to_matsim(output_dir)
    if vehicle_scalings is not None:
        vehicle_scalings = [float(vsc) for vsc in vehicle_scalings.split(",")]
        logging.info("Generating scaled vehicles xml.")
        _write_scaled_vehicles(network.schedule, vehicle_scalings, output_dir)


@cli.command()
@xml_file("network")
@xml_file("schedule", False)
@xml_file("vehicles", False)
@projection
@output_dir
def generate_standard_outputs(
    path_to_network: Path,
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    projection: str,
    output_dir: Path,
):
    "Generate Standard outputs for a network and/or schedule"
    ensure_dir(output_dir)

    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.WARNING)

    network = _read_network(path_to_network, projection, path_to_schedule, path_to_vehicles)

    logging.info("Generating standard outputs")
    network.generate_standard_outputs(output_dir)


@cli.command()
@xml_file("network")
@projection
@output_dir
@subset_conditions
def inspect_google_directions_requests_for_network(
    path_to_network: Path, projection: str, output_dir: Path, subset_conditions: Optional[str]
):
    """Generate Google Directions API requests for a network for inspection"""

    network = _read_network(path_to_network, projection)

    logging.info("Generating requests for the network")
    api_requests = google_directions.generate_requests(n=network)
    logging.info(f"Generated {len(api_requests)} requests for the given network")

    if output_dir:
        logging.info(f"Saving results to {output_dir}")
        google_directions.dump_all_api_requests_to_json(api_requests, output_dir)

    if subset_conditions is not None:
        subset_conditions = subset_conditions.split(",")
        logging.info(
            f"Considering subset of the network satisfying attributes-osm:way:highway-{subset_conditions}"
        )
        links_to_keep = network.extract_links_on_edge_attributes(
            conditions={"attributes": {"osm:way:highway": subset_conditions}}
        )
        remove_links = set(network.link_id_mapping.keys()) - set(links_to_keep)
        network.remove_links(remove_links, silent=True)
        api_requests = google_directions.generate_requests(n=network)
        logging.info(f"Generated {len(api_requests)} requests for the subsetted network")

        if output_dir:
            sub_output_dir = output_dir / "subset"
            logging.info(f"Saving subset results to {sub_output_dir}")
            google_directions.dump_all_api_requests_to_json(api_requests, sub_output_dir)


@cli.command()
@xml_file("network")
@xml_file("schedule", False)
@xml_file("vehicles", False)
@projection
@output_dir
@click.option(
    "-pm",
    "--pt_modes",
    help="Comma delimited list of modes to subset stops of interest. A stop is linked to a mode "
    "via a transit route using that stop. Optional, otherwise considers all stops",
    required=False,
    type=str,
    default=None,
)
@click.option(
    "-nm",
    "--network_snap_modes",
    help="Comma delimited list of modes to subset the network graph. "
    "The links from this modal subgraph will be considered for the stop to graph "
    "relationship. Two new attributes (per mode) will be added to PT stops:"
    "xmodeAccessible = true and accessLinkId_xmode = link_id",
    required=False,
    type=str,
    default="car",
)
@click.option(
    "-tm",
    "--teleport_modes",
    help="Comma delimited list of (teleported) modes to enable for given PT stops "
    "No links will be found for these modes. One new attributes (per mode) will be added "
    "to PT stops: xmodeAccessible = true",
    required=False,
    type=str,
    default=None,
)
@click.option(
    "-ss",
    "--step_size",
    help="In metres. This process finds links in the nearest neighbourhood of a stop. The "
    "size of the neighbourhood increases by `step_size` value each time until it finds "
    "links to relate to stops.",
    required=False,
    default=25,
    type=float,
)
@click.option(
    "-dt",
    "--distance_threshold",
    help="In metres. This is the limit of how wide the search area for a link can be for each "
    "stop.",
    required=False,
    default=None,
    type=float,
)
def intermodal_access_egress_network(
    path_to_network: Path,
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    projection: str,
    output_dir: Path,
    pt_modes: Optional[str],
    network_snap_modes: Optional[str],
    teleport_modes: Optional[str],
    step_size: float,
    distance_threshold: Optional[float],
):
    """Process to add access and egress links for PT stops of given modes.

    Intended to generate PT schedules to work with SBB extensions in MATSim:
    https://github.com/matsim-org/matsim-libs/tree/master/contribs/sbb-extensions#intermodal-access-and-egress
    """

    supporting_outputs = output_dir / "supporting_outputs"
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    network = _read_network(path_to_network, projection, path_to_schedule, path_to_vehicles)

    logging.info(f"The following modes are present in the Schedule: {network.schedule.modes()}")
    df_stops = network.schedule.to_geodataframe()["nodes"].to_crs(EPSG4326)
    if pt_modes is not None:
        pt_modes = pt_modes.split(",")
        logging.info(f"Stops serving the following modes will be considered: {pt_modes}")
        stops_subset = network.schedule.stops_on_modal_condition(modes=pt_modes)
        df_stops = df_stops.loc[stops_subset]
        df_stops[["lat", "lon", "geometry"]].to_file(
            os.path.join(supporting_outputs, "stops.geojson"), driver="GeoJSON"
        )
        logging.info(f"Modal subsetting resulted in {len(df_stops)} stops to snap")

    if network_snap_modes is not None:
        network_snap_modes = network_snap_modes.split(",")
        logging.info("Building Spatial Tree")
        spatial_tree = spatial.SpatialTree(network)

        for snap_mode in network_snap_modes:
            logging.info(f"Snapping mode: {snap_mode}")
            sub_tree = spatial_tree.modal_subtree(modes={snap_mode})

            closest_links = _find_closest_links_by_step(
                network_spatial_tree=sub_tree,
                df_stops=df_stops,
                step_size=step_size,
                distance_threshold=distance_threshold,
            )

            # TODO There are multiple links to choose from, for the time being we are not precious about which link is selected.
            selected_links = closest_links.reset_index().groupby("index").first()
            if len(selected_links) != len(df_stops):
                logging.warning(
                    f"Only {len(selected_links)} out of {len(df_stops)} stops found a link to snap to. "
                    "Consider removing the distance threshold if you want all stops to find a nearest link."
                )

            # Let's create some handy geojson outputs to verify our snapping
            selected_links[["catchment", "geometry"]].to_file(
                os.path.join(supporting_outputs, f"{snap_mode}_stop_catchments.geojson"),
                driver="GeoJSON",
            )
            # join to get link geoms
            selected_links = selected_links.join(
                sub_tree.links[["link_id", "geometry"]],
                how="left",
                on="link_id",
                lsuffix="_left",
                rsuffix="",
            )
            selected_links[["geometry"]].to_file(
                os.path.join(supporting_outputs, f"{snap_mode}_access_egress_links.geojson"),
                driver="GeoJSON",
            )
            # get number of stops in each catchment
            catchment_value_counts = selected_links["catchment"].value_counts().to_dict()
            _to_json(
                catchment_value_counts,
                supporting_outputs / f"{snap_mode}_catchment_value_counts.json",
            )
            logging.info(f"Number of stops in each catchment bin: {catchment_value_counts}")

            # generate the data dictionaries for updating stops data
            access_link_id_tag = f"accessLinkId_{snap_mode}"
            accessible_tag = f"{snap_mode}Accessible"
            distance_catchment_tag = f"{snap_mode}_distance_catchment_tag"

            selected_links[access_link_id_tag] = selected_links["link_id"]
            selected_links[accessible_tag] = "true"
            selected_links[distance_catchment_tag] = selected_links["catchment"].astype(str)
            new_stops_data = selected_links[
                [access_link_id_tag, accessible_tag, distance_catchment_tag]
            ].T.to_dict()
            new_stops_data = {k: {"attributes": v} for k, v in new_stops_data.items()}

            network.schedule.apply_attributes_to_stops(new_stops_data)

    if teleport_modes is not None:
        teleport_modes = teleport_modes.split(",")
        for tele_mode in teleport_modes:
            logging.info(f"Adding access to mode: {tele_mode}")

            # generate the data dictionaries for updating stops data
            accessible_tag = f"{tele_mode}Accessible"
            df_stops[accessible_tag] = "true"
            new_stops_data = df_stops[[accessible_tag]].T.to_dict()
            new_stops_data = {k: {"attributes": v} for k, v in new_stops_data.items()}

            network.schedule.apply_attributes_to_stops(new_stops_data)

    logging.info("Writing the schedule.")
    network.schedule.write_to_matsim(output_dir)


@cli.command()
@xml_file("network", False)
@projection
@output_dir
@osm(required=False)
@gtfs
@processes
@click.option(
    "-sd",
    "--snapping_distance",
    help="Distance for snapping network nodes to transit stops",
    default=30,
    type=float,
    required=False,
)
def make_pt_network(
    path_to_network: Path,
    projection: str,
    output_dir: Path,
    path_to_osm: Path,
    path_to_osm_config: Path,
    path_to_gtfs: Path,
    gtfs_day: str,
    processes: int,
    snapping_distance: float,
):
    """Create a PT MATSim network"""

    ensure_dir(output_dir)

    if path_to_osm is not None:
        logging.info(f"Reading in network at {path_to_osm}")
        network = read_osm(path_to_osm, path_to_osm_config, num_processes=processes)
        logging.info("Simplifying network")
        network.simplify(no_processes=processes)
        logging.info(
            f"Simplification resulted in {len(network.link_simplification_map)} links being simplified."
        )
        _to_json(network.link_simplification_map, output_dir / "link_simp_map.json")

        network.write_to_matsim(output_dir)
    elif path_to_network is not None:
        network = _read_network(path_to_network, projection)
    else:
        raise NotImplementedError(
            "You need to pass an OSM file and config to create a Network or an existing MATSim "
            "network.xml. If your network exists in another format, write a script to use an "
            "appropriate reading method for that network."
        )

    logging.info(f"Reading GTFS at {path_to_gtfs} for day: {gtfs_day}")
    network.schedule = read_gtfs(path_to_gtfs, day=gtfs_day, epsg=projection)

    logging.info(
        f"Snapping and routing the schedule onto the network with distance threshold {snapping_distance}"
    )
    unsnapped_services = network.route_schedule(
        distance_threshold=snapping_distance, additional_modes={"bus": "car"}
    )
    logging.info(
        f"Snapping resulted in {len(unsnapped_services)} unsnapped services: {unsnapped_services}. Trying them again."
    )
    unsnapped_services = network.route_schedule(
        distance_threshold=snapping_distance,
        additional_modes={"bus": "car"},
        services=unsnapped_services,
    )
    logging.info(
        f"Second snapping attempt resulted in {len(unsnapped_services)} unsnapped services: {unsnapped_services}"
        "They will be teleported"
    )
    network.teleport_service(service_ids=unsnapped_services)
    _generate_validation_report(network, output_dir)

    network.generate_standard_outputs(os.path.join(output_dir, "standard_outputs"))

    logging.info(f"Writing results to {output_dir}")
    network.write_to_matsim(output_dir)


@cli.command()
@osm(required=True)
@projection
@processes
@output_dir
@click.option(
    "-cc",
    "--connected_components",
    help="Number of connected components within graph for modes `walk`,`bike`,`car`",
    type=int,
    default=1,
)
def make_road_only_network(
    projection: str,
    output_dir: Path,
    path_to_osm: Path,
    path_to_osm_config: Path,
    processes: int,
    connected_components: int,
):
    """Create a road-only MATSim network"""

    logging.info("Reading in network at {}".format(osm))
    network = read_osm(
        osm_file_path=path_to_osm,
        osm_read_config=path_to_osm_config,
        num_processes=processes,
        epsg=projection,
    )
    for mode in ["walk", "car", "bike"]:
        network.retain_n_connected_subgraphs(n=connected_components, mode=mode)
    network.write_to_matsim(output_dir)


@cli.command()
@xml_file("network")
@xml_file("schedule", False)
@xml_file("vehicles", False)
@processes
@output_dir
@click.option(
    "-cp",
    "--current_projection",
    help='The projection network is currently in, eg. "epsg:27700"',
    type=str,
    required=True,
)
@click.option(
    "-np",
    "--new_projection",
    help='The projection desired, eg. "epsg:27700"',
    type=str,
    required=True,
)
def reproject_network(
    path_to_network: Path,
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    processes: int,
    output_dir: Path,
    current_projection: str,
    new_projection: str,
):
    """Reproject a MATSim network"""

    network = _read_network(path_to_network, current_projection, path_to_schedule, path_to_vehicles)

    logging.info("Reprojecting the network.")

    start = time.time()
    network.reproject(new_projection, processes=processes)
    end = time.time()
    network.write_to_matsim(output_dir)

    logging.info(f"It took {round((end - start)/60, 3)} min to reproject the network.")


@cli.command()
@xml_file("schedule", False)
@xml_file("vehicles", False)
@projection
@vehicle_scalings
@output_dir
def scale_vehicles(
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    projection: str,
    output_dir: Path,
    vehicle_scalings: Optional[str],
):
    """Scale PT Schedule vehicles"""
    if vehicle_scalings is None:
        raise RuntimeError("No vehicle scalings given!")
    else:
        vehicle_scalings = [float(vsc) for vsc in vehicle_scalings.split(",")]
    ensure_dir(output_dir)
    logging.info("Reading in schedule at {}".format(path_to_schedule))
    s = read_matsim_schedule(
        path_to_schedule=path_to_schedule, path_to_vehicles=path_to_vehicles, epsg=projection
    )

    logging.info("Generating scaled vehicles xml.")
    _write_scaled_vehicles(s, vehicle_scalings, output_dir)


@cli.command()
@xml_file("network")
@projection
@subset_conditions
@output_dir
@click.option(
    "-t",
    "--requests_threshold",
    help="Max number of API requests you are happy to send. If exceeded, will fail without "
    "sending any",
    required=True,
    type=int,
)
@click.option(
    "-k",
    "--api_key",
    help="Google Directions API key if not using AWS secrets manager",
    required=False,
    type=str,
    default=None,
)
@click.option(
    "-sn",
    "--secret_name",
    help="Secret name in AWS Secrets manager, if not passing the API key directly",
    required=False,
    type=str,
    default=None,
)
@click.option(
    "-rn",
    "--region_name",
    help="Region name in AWS, if not passing the API key directly",
    required=False,
    type=str,
    default=None,
)
@click.option(
    "-tm",
    "--traffic_model",
    help="Google Directions API traffic model to consider when calculating time in traffic for choices. "
    "See https://developers.google.com/maps/documentation/directions/get-directions#traffic_model",
    required=False,
    default="best_guess",
)
@click.option(
    "-dp",
    "--departure_time",
    help="desired time of departure, in unix time, or `now` for current traffic conditions",
    required=False,
    default="now",
)
def send_google_directions_requests_for_network(
    path_to_network: Path,
    projection: str,
    output_dir: Path,
    subset_conditions: Optional[str],
    requests_threshold,
    api_key: Optional[str],
    secret_name: Optional[str],
    region_name: Optional[str],
    traffic_model: str,
    departure_time: str,
):
    """Generate and send Google Directions API requests"""

    network = _read_network(path_to_network, projection)

    if subset_conditions is not None:
        subset_conditions = subset_conditions.split(",")
        logging.info(
            f"Considering subset of the network satisfying attributes-osm:way:highway-{subset_conditions}"
        )
        links_to_keep = network.extract_links_on_edge_attributes(
            conditions={"attributes": {"osm:way:highway": subset_conditions}}
        )
        remove_links = set(network.link_id_mapping.keys()) - set(links_to_keep)
        network.remove_links(remove_links, silent=True)
        logging.info("Proceeding with the subsetted network")

    google_directions.send_requests_for_network(
        n=network,
        request_number_threshold=requests_threshold,
        output_dir=output_dir,
        traffic_model=traffic_model,
        key=api_key,
        secret_name=secret_name,
        region_name=region_name,
        departure_time=departure_time,
    )


@cli.command()
@xml_file("network")
@projection
@output_dir
@click.option(
    "-m",
    "--modes",
    help="Comma delimited list of modes to split from the network",
    type=str,
    required=True,
)
@click.option(
    "-ic",
    "--increase_capacity",
    help="Sets capacity on detached links to 9999",
    required=False,
    default=False,
    is_flag=True,
)
def separate_modes_in_network(
    path_to_network: Path, projection: str, output_dir: Path, modes: str, increase_capacity: bool
):
    """Generate new links, each for the use of a singular mode in a MATSim network.

    This creates separate modal subgraphs for the given modes.
    It can be used with MATSim to ensure the two modes do not come in contact.

    Examples:

        ```python
        [1] network.link("LINK_ID")
        [out] {"id": "LINK_ID", "modes": {"car", "bike"}, "freespeed": 5, ...}
        ```

        The new bike link will assume all the same attributes apart from the "modes":
        ```python
        [1] network.link("bike---LINK_ID")`
        [out] {"id": "bike---LINK_ID", "modes": {"bike"}, "freespeed": 5, ...}
        ```

        In the case when a link already has a single dedicated mode, no updates are made to the link ID.
        You can assume that all links that were in the network previously are still there, but their allowed modes may have changed.
        So, any simulation outputs may not be valid with this new network.
    """
    modes = modes.split(",")
    supporting_outputs = output_dir / "supporting_outputs"
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    network = _read_network(path_to_network, projection)
    logging.info(f"Number of links before separating graph: {len(network.link_id_mapping)}")

    _generate_modal_network_geojsons(network, modes, supporting_outputs, "before")

    for mode in modes:
        logging.info(f"Splitting links for mode: {mode}")
        df = network.link_attribute_data_under_key("modes")
        modal_links = network.links_on_modal_condition({mode})
        # leave the links that have a single mode as they are
        modal_links = set(modal_links) & set(df[df != {mode}].index)
        update_mode_links = {k: {"modes": df.loc[k] - {mode}} for k in modal_links}
        new_links = {
            f"{mode}---{k}": {**network.link(k), **{"modes": {mode}, "id": f"{mode}---{k}"}}
            for k in modal_links
        }
        network.apply_attributes_to_links(update_mode_links)
        network.add_links(new_links)
        if increase_capacity:
            logging.info(f"Increasing capacity for link of mode {mode} to 9999")
            mode_links = network.extract_links_on_edge_attributes({"modes": mode})
            df_capacity = network.link_attribute_data_under_keys(["capacity"]).loc[mode_links, :]
            df_capacity["capacity"] = 9999
            network.apply_attributes_to_links(df_capacity.T.to_dict())

    logging.info(f"Number of links after separating graph: {len(network.link_id_mapping)}")

    network.write_to_matsim(output_dir)

    logging.info("Generating validation report")
    report = network.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    _to_json(report, output_dir / "validation_report.json")

    _generate_modal_network_geojsons(network, modes, supporting_outputs, "after")


@cli.command()
@xml_file("network")
@xml_file("schedule", False)
@xml_file("vehicles", False)
@projection
@processes
@vehicle_scalings
@output_dir
@click.option(
    "-fc",
    "--force_strongly_connected_graph",
    help="If True, checks for disconnected subgraphs for modes `walk`, `bike` and `car`. "
    "If there are more than one strongly connected subgraph, genet connects them with links at closest points in the graph. "
    "The links used to connect are weighted at 20% of surrounding freespeed and capacity values.",
    default=False,
    is_flag=True,
)
def simplify_network(
    path_to_network: Path,
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    projection: str,
    processes: int,
    output_dir: Path,
    vehicle_scalings: str,
    force_strongly_connected_graph: bool,
):
    """Simplify a MATSim network by removing intermediate links from paths"""

    ensure_dir(output_dir)

    network = _read_network(path_to_network, projection, path_to_schedule, path_to_vehicles)

    logging.info("Simplifying the Network.")

    start = time.time()
    network.simplify(no_processes=processes)
    end = time.time()
    logging.info(f"This took {round((end - start) / 60, 3)} min.")

    logging.info(
        f"Simplification resulted in {len(network.link_simplification_map)} links being simplified."
    )
    _to_json(network.link_simplification_map, output_dir / "link_simp_map.json")

    logging.info("Checking for disconnected subgraphs")
    start = time.time()
    for mode in {"car", "bike", "walk"}:
        if not network.is_strongly_connected(modes={mode}):
            logging.info(f"The graph for {mode} mode is not strongly connected.")
            if force_strongly_connected_graph:
                logging.info("GeNet will now attempt to add links to connect the graph.")
                network.connect_components(modes={mode}, weight=1 / 5)
    end = time.time()
    logging.info(f"This took {round((end - start) / 60, 3)} min.")

    network.write_to_matsim(output_dir)

    if vehicle_scalings is not None:
        vehicle_scalings = [float(vsc) for vsc in vehicle_scalings.split(",")]
        logging.info("Generating scaled vehicles xml.")
        _write_scaled_vehicles(network.schedule, vehicle_scalings, output_dir)

    _generate_validation_report(network, output_dir)

    network.generate_standard_outputs(os.path.join(output_dir, "standard_outputs"))


@cli.command()
@xml_file("network")
@projection
@output_dir
@squeeze_args
def squeeze_external_area(
    path_to_network: Path,
    projection: str,
    output_dir: Path,
    path_to_study_area: Path,
    freespeed: float,
    capacity: float,
):
    """Changes `freespeed` and `capacity` values for links **outside** of the given `study_area` by given factors.

    To squeeze links within the study area, refer to the `squeeze_urban_links` command.
    """

    supporting_outputs = output_dir / "supporting_outputs"
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    network = _read_network(path_to_network, projection)

    logging.info(f"Reading in Study Area geometry at {path_to_study_area}")
    gdf_study_area = gpd.read_file(path_to_study_area)
    if gdf_study_area.crs != projection:
        logging.info(
            f"Projecting Study Area geometry from {str(gdf_study_area.crs)} to {projection}, "
            "to match the network projection"
        )
        gdf_study_area = gdf_study_area.to_crs(CRS(projection))
    if gdf_study_area.empty:
        raise RuntimeError("The Study Area was not found!!")

    logging.info("Finding links external to the study area")
    network_gdf = network.to_geodataframe()["links"]
    network_internal = gpd.sjoin(network_gdf, gdf_study_area, how="inner", predicate="intersects")
    external_links = set(network_gdf["id"].astype("str")) - set(
        network_internal["id"].astype("str")
    )

    logging.info("Finding car mode links")
    car_links = set(network.links_on_modal_condition("car"))

    logging.info("Finding minor road external links")
    links_to_squeeze = external_links.intersection(car_links)
    logging.info(
        f"{len(links_to_squeeze)} road links out of all {len(external_links)} external links and a total of "
        f"{len(car_links)} car mode links will be squeezed."
    )

    logging.info("Generating geojson of external road links")
    external_tag_gdf = network_gdf[network_gdf["id"].isin(set(links_to_squeeze))]
    save_geodataframe(
        external_tag_gdf[["id", "geometry"]].to_crs(EPSG4326),
        "external_network_links",
        supporting_outputs,
    )

    # THE SQUEEZE SECTION

    network_gdf = network_gdf.to_crs(EPSG4326)
    _gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {"car", "bus"}), axis=1)]
    save_geodataframe(
        _gdf[["id", "freespeed", "geometry"]],
        output_dir=supporting_outputs,
        filename="freespeed_before",
    )
    save_geodataframe(
        _gdf[["id", "capacity", "geometry"]],
        output_dir=supporting_outputs,
        filename="capacity_before",
    )

    network_gdf = network_gdf[network_gdf["id"].isin(links_to_squeeze)]
    if freespeed:
        logging.info(f"Changing freespeed by {freespeed * 100}%")
        network_gdf["freespeed"] = network_gdf["freespeed"] * freespeed
    if capacity:
        logging.info(f"Changing capacity by {capacity * 100}%")
        network_gdf["capacity"] = network_gdf["capacity"] * capacity

    network.apply_attributes_to_links(
        network_gdf[["id", "freespeed", "capacity"]].set_index("id").T.to_dict()
    )

    logging.info("Generating geojson outputs for visual validation")
    network_gdf = network.to_geodataframe()["links"]
    network_gdf = network_gdf.to_crs(EPSG4326)
    network_gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {"car", "bus"}), axis=1)]
    save_geodataframe(
        network_gdf[["id", "freespeed", "geometry"]],
        output_dir=supporting_outputs,
        filename="freespeed_after",
    )
    save_geodataframe(
        network_gdf[["id", "capacity", "geometry"]],
        output_dir=supporting_outputs,
        filename="capacity_after",
    )

    logging.info(f"Saving network to {output_dir}")
    network.write_to_matsim(output_dir)


@cli.command()
@xml_file("network")
@projection
@output_dir
@click.option(
    "-ug",
    "--urban_geometries",
    "path_to_urban_geometries",
    help="Geojson or shp file that when read into geopandas produces a table with columns: "
    '"label" (with at least some of the values in this column being a string: "urban") '
    'and "geometry" (polygons defining urban areas)',
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
@squeeze_args
def squeeze_urban_links(
    path_to_network: Path,
    projection: str,
    output_dir: Path,
    path_to_urban_geometries: Path,
    path_to_study_area: Path,
    freespeed: float,
    capacity: float,
):
    """Tag minor network links as urban, given geometries: `urban_geometries`.

    Minor links are defined as anything other than: osm way highway tags: motorway, motorway_link, trunk, trunk_link, primary, primary_link.
    Urban geometries are passed via geojson input with a specific format, see command arguments for description.
    Passing `study_area` subsets the urban geometries and links to be squeezed - only links in the study area will be tagged and squeezed.
    This is useful if your geometries covers a larger area.
    The script then reduces capacity and/or freespeed by a factor of current value on those links.

    To squeeze links outside the study area, refer to the `squeeze_external_area.py` command.
    """
    supporting_outputs = output_dir / "supporting_outputs"
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)
    network = _read_network(path_to_network, projection)

    # URBAN TAGGING SECTION

    logging.info(f"Reading in urban geometries at {path_to_urban_geometries}")
    gdf_urban = gpd.read_file(path_to_urban_geometries)
    if gdf_urban.crs != projection:
        logging.info(
            f"Projecting urban geometries from {str(gdf_urban.crs)} to {projection}, to match the network projection"
        )
        gdf_urban = gdf_urban.to_crs(CRS(projection))
    gdf_urban = gdf_urban[gdf_urban["label"] == "urban"]
    if gdf_urban.empty:
        raise RuntimeError('No areas labelled "urban" were found!!')
    if path_to_study_area is not None:
        logging.info(f"Reading in Study Area geometries at {path_to_study_area}")
        gdf_study_area = gpd.read_file(path_to_study_area)
        if gdf_study_area.crs != projection:
            logging.info(
                f"Projecting Study Area geometries from {str(gdf_study_area.crs)} to {projection}, to match the network projection"
            )
            gdf_study_area = gdf_study_area.to_crs(CRS(projection))
        logging.info("Subsetting urban geometries on study area")
        gdf_urban = gpd.sjoin(gdf_urban, gdf_study_area, how="inner", predicate="intersects").drop(
            columns=["index_right"]
        )

    logging.info("Finding urban links")
    network_gdf = network.to_geodataframe()["links"]
    network_urban = gpd.sjoin(network_gdf, gdf_urban, how="inner", predicate="intersects").drop(
        columns=["index_right"]
    )
    if path_to_study_area is not None:
        # subsetting gdf_urban on study area is not enough if it consists of polygons that extend beyond
        # but it does make it faster to work with gdf_urban if it was large to begin with
        network_urban = gpd.sjoin(network_gdf, gdf_study_area, how="inner", predicate="intersects")
    urban_links = set(network_urban["id"].astype("str"))

    logging.info("Finding major road links")
    major_links = set(
        network.extract_links_on_edge_attributes(
            conditions=[
                {"attributes": {"osm:way:highway": "motorway"}},
                {"attributes": {"osm:way:highway": "motorway_link"}},
                {"attributes": {"osm:way:highway": "trunk"}},
                {"attributes": {"osm:way:highway": "trunk_link"}},
                {"attributes": {"osm:way:highway": "primary"}},
                {"attributes": {"osm:way:highway": "primary_link"}},
            ],
            how=any,
        )
    )
    logging.info("Finding car mode links")
    car_links = set(network.links_on_modal_condition("car"))

    logging.info("Finding minor road urban links")
    links_to_tag = urban_links.intersection(car_links) - major_links
    logging.info(
        f"{len(links_to_tag)} minor road links out of all {len(urban_links)} urban links and a total of "
        f'{len(car_links)} car mode links will be tagged with the "urban" tag'
    )

    logging.info("Generating geojson of urban road links")
    urban_tag_gdf = network_gdf[network_gdf["id"].isin(set(links_to_tag))]
    save_geodataframe(
        urban_tag_gdf[["id", "geometry"]].to_crs(EPSG4326),
        "urban_network_links",
        supporting_outputs,
    )

    logging.info('Applying "urban" tag to links')
    network.apply_attributes_to_links(
        {link_id: {"attributes": {"urban": "True"}} for link_id in links_to_tag}
    )

    # THE SQUEEZE SECTION

    links_to_reduce = links_to_tag

    logging.info("Generating geojson outputs for visual validation")
    network_gdf = network_gdf.to_crs(EPSG4326)
    _gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {"car", "bus"}), axis=1)]
    save_geodataframe(
        _gdf[["id", "freespeed", "geometry"]],
        output_dir=supporting_outputs,
        filename="freespeed_before",
    )
    save_geodataframe(
        _gdf[["id", "capacity", "geometry"]],
        output_dir=supporting_outputs,
        filename="capacity_before",
    )

    network_gdf = network_gdf[network_gdf["id"].isin(links_to_reduce)]
    if freespeed:
        logging.info(f"Changing freespeed by {freespeed * 100}%")
        network_gdf["freespeed"] = network_gdf["freespeed"] * freespeed
    if capacity:
        logging.info(f"Changing capacity by {capacity * 100}%")
        network_gdf["capacity"] = network_gdf["capacity"] * capacity

    network.apply_attributes_to_links(
        network_gdf[["id", "freespeed", "capacity"]].set_index("id").T.to_dict()
    )

    logging.info("Generating geojson outputs for visual validation")
    network_gdf = network.to_geodataframe()["links"].to_crs(EPSG4326)
    network_gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {"car", "bus"}), axis=1)]
    save_geodataframe(
        network_gdf[["id", "freespeed", "geometry"]],
        output_dir=supporting_outputs,
        filename="freespeed_after",
    )
    save_geodataframe(
        network_gdf[["id", "capacity", "geometry"]],
        output_dir=supporting_outputs,
        filename="capacity_after",
    )

    logging.info(f"Saving network in {output_dir}")
    network.write_to_matsim(output_dir)


@cli.command()
@xml_file("network")
@xml_file("schedule", False)
@xml_file("vehicles", False)
@projection
@output_dir
def validate_network(
    path_to_network: Path,
    path_to_schedule: Optional[Path],
    path_to_vehicles: Optional[Path],
    projection: str,
    output_dir: Path,
):
    """Run MATSim specific validation methods on a MATSim network"""

    ensure_dir(output_dir)
    network = _read_network(path_to_network, projection, path_to_schedule, path_to_vehicles)
    _generate_validation_report(network, output_dir)
