import logging
from pathlib import Path
from typing import Any, Optional

import click

logging.basicConfig(level=logging.INFO, format="%(levelname)-3s %(message)s")
logger = logging.getLogger(__name__)


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
    from genet.use.cli import add_elevation_to_network

    add_elevation_to_network(
        path_to_network,
        projection,
        path_to_elevation,
        null_value,
        output_dir,
        write_elevation_to_network,
        write_slope_to_network,
        write_slope_to_object_attribute_file,
        save_jsons,
    )


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
    """Command to check and correct, if needed, the speed and headway of services in the schedule.

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
    from genet.use.cli import auto_schedule_fixes

    auto_schedule_fixes(
        path_to_network,
        path_to_schedule,
        path_to_vehicles,
        projection,
        output_dir,
        vehicle_scalings,
    )


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
    """Generate Standard outputs for a network and/or schedule"""
    from genet.use.cli import generate_standard_outputs

    generate_standard_outputs(
        path_to_network, path_to_schedule, path_to_vehicles, projection, output_dir
    )


@cli.command()
@xml_file("network")
@projection
@output_dir
@subset_conditions
def inspect_google_directions_requests_for_network(
    path_to_network: Path, projection: str, output_dir: Path, subset_conditions: Optional[str]
):
    """Generate Google Directions API requests for a network for inspection"""
    from genet.use.cli import inspect_google_directions_requests_for_network

    inspect_google_directions_requests_for_network(
        path_to_network, projection, output_dir, subset_conditions
    )


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
    from genet.use.cli import intermodal_access_egress_network

    intermodal_access_egress_network(
        path_to_network,
        path_to_schedule,
        path_to_vehicles,
        projection,
        output_dir,
        pt_modes,
        network_snap_modes,
        teleport_modes,
        step_size,
        distance_threshold,
    )


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
    from genet.use.cli import make_pt_network

    make_pt_network(
        path_to_network,
        projection,
        output_dir,
        path_to_osm,
        path_to_osm_config,
        path_to_gtfs,
        gtfs_day,
        processes,
        snapping_distance,
    )


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
    from genet.use.cli import make_road_only_network

    make_road_only_network(
        projection, output_dir, path_to_osm, path_to_osm_config, processes, connected_components
    )


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
    from genet.use.cli import reproject_network

    reproject_network(
        path_to_network,
        path_to_schedule,
        path_to_vehicles,
        processes,
        output_dir,
        current_projection,
        new_projection,
    )


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
    from genet.use.cli import scale_vehicles

    scale_vehicles(path_to_schedule, path_to_vehicles, projection, output_dir, vehicle_scalings)


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
    from genet.use.cli import send_google_directions_requests_for_network

    send_google_directions_requests_for_network(
        path_to_network,
        projection,
        output_dir,
        subset_conditions,
        requests_threshold,
        api_key,
        secret_name,
        region_name,
        traffic_model,
        departure_time,
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
    from genet.use.cli import separate_modes_in_network

    separate_modes_in_network(path_to_network, projection, output_dir, modes, increase_capacity)


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
    from genet.use.cli import simplify_network

    simplify_network(
        path_to_network,
        path_to_schedule,
        path_to_vehicles,
        projection,
        processes,
        output_dir,
        vehicle_scalings,
        force_strongly_connected_graph,
    )


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
    from genet.use.cli import squeeze_external_area

    squeeze_external_area(
        path_to_network, projection, output_dir, path_to_study_area, freespeed, capacity
    )


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
    from genet.use.cli import squeeze_urban_links

    squeeze_urban_links(
        path_to_network,
        projection,
        output_dir,
        path_to_urban_geometries,
        path_to_study_area,
        freespeed,
        capacity,
    )


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
    from genet.use.cli import validate_network

    validate_network(path_to_network, path_to_schedule, path_to_vehicles, projection, output_dir)
