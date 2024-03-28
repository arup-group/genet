import ast
import itertools
import json
import logging
import os
import time
from typing import Callable, Optional, Union

import polyline
import requests
from requests_futures.sessions import FuturesSession

import genet.output.geojson as geojson
import genet.utils.persistence as persistence
import genet.utils.secrets_vault as secrets_vault
import genet.utils.simplification as simplification
import genet.utils.spatial as spatial
from genet.core import Network

session = FuturesSession(max_workers=2)


def send_requests_for_network(
    n: Network,
    request_number_threshold: int,
    output_dir: str,
    departure_time: int,
    traffic_model: Optional[str] = None,
    key: Optional[str] = None,
    secret_name: Optional[str] = None,
    region_name: Optional[str] = None,
) -> dict:
    """Generates, sends and parses results from Google Directions API for the car modal subgraph for network n.

    You can pass your API key to this function under `key` variable.

    Alternatively, you can use AWS Secrets manager for storing your API and pass secret_name and region_name (make sure you are authenticated to your AWS account).

    You can also export an environmental variable in your terminal `$ export GOOGLE_DIR_API_KEY='your key'`.

    Args:
        n (Network): GeNet Network.
        request_number_threshold (int): max number of requests.
        output_dir (str): output directory where to save the google directions api parsed data.
        departure_time (int):
            specifies the desired time of departure, in seconds since midnight, January 1, 1970 UTC.
            i.e. unix time; if set to None, API will return results for average time-independent traffic conditions.
        traffic_model (Optional[str], optional):
            If given, specifies the assumptions to use when calculating time in traffic.
            For choices see https://developers.google.com/maps/documentation/directions/get-directions#traffic_model.
            Defaults to None.
        key (Optional[str], optional): API key. Defaults to None.
        secret_name (Optional[str], optional): If using AWS secrets manager, the name where your directions api key is stored. Defaults to None.
        region_name (Optional[str], optional): The AWS region you operate in. Defaults to None.

    Raises:
        RuntimeError: Can only make as many requests as `request_number`.

    Returns:
        dict: API request results.
    """
    logging.info("Generating Google Directions API requests")
    api_requests = generate_requests(n)

    dump_all_api_requests_to_json(api_requests, output_dir)

    if len(api_requests) > request_number_threshold:
        raise RuntimeError(
            f"Number of requests exceeded the threshold. Number of requests: {len(api_requests)}"
        )

    logging.info("Sending API requests")
    api_requests = send_requests(
        api_requests, departure_time, traffic_model, key, secret_name, region_name
    )
    logging.info("Parsing API requests")
    api_requests = parse_results(api_requests)

    dump_all_api_requests_to_json(api_requests, output_dir)
    return api_requests


def read_api_requests(file_path: str) -> dict:
    """Read the Google Directions API request results stored in the `file_path` JSON file.

    Args:
        file_path (str): path to the JSON file where the google directions api requests were saved.

    Returns:
        dict: Loaded API request results
    """
    api_requests = {}
    with open(file_path, "rb") as handle:
        json_dump = json.load(handle)
    for key in json_dump:
        try:
            json_dump[key] = ast.literal_eval(json_dump[key])
        except (ValueError, TypeError) as e:
            logging.warning(f"{str(key)} not processed due to {e}")
            continue
        api_requests[(json_dump[key]["path_nodes"][0], json_dump[key]["path_nodes"][-1])] = (
            json_dump[key]
        )
    return api_requests


def make_request(origin_attributes, destination_attributes, key, departure_time, traffic_model):
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": "{},{}".format(origin_attributes["lat"], origin_attributes["lon"]),
        "destination": "{},{}".format(destination_attributes["lat"], destination_attributes["lon"]),
        "key": key,
        "traffic_model": traffic_model,
    }
    current_unix_time = time.time()
    end_of_unix_time = 2147483646
    if departure_time == "now":
        params["departure_time"] = "now"
    elif (
        isinstance(departure_time, int)
        & (departure_time > current_unix_time)
        & (departure_time < end_of_unix_time)
    ):
        params["departure_time"] = departure_time
    else:
        raise RuntimeError(
            "The departure_time parameter value not recognised. The departure_time can be set "
            "to None (meaning API will return results for average time-independent traffic conditions)"
            ', "now", or some time in the future. If setting the departure_time to '
            "some time in the future, then it needs to be specified as an integer in seconds since "
            "midnight, January 1, 1970 UTC (i.e. unix time). It cannot be in the past."
        )
    return session.get(base_url, params=params)


def send_requests(
    api_requests: dict,
    departure_time: int,
    traffic_model: Optional[str] = None,
    key: Optional[str] = None,
    secret_name: Optional[str] = None,
    region_name: Optional[str] = None,
):
    if key is None:
        key = secrets_vault.get_google_directions_api_key(secret_name, region_name)
        if key is None:
            raise RuntimeError(
                "API key was not found. Make sure you are authenticated and pointing in the correct "
                "location if using AWS secrets manager, or that you have passed the correct key. "
                "If using `GOOGLE_DIR_API_KEY` environmental variable, make sure you have spelled it "
                "correctly. You can check this using `echo $GOOGLE_DIR_API_KEY` in the terminal you're "
                "using or  `!echo $GOOGLE_DIR_API_KEY` if using jupyter notebook cells. To export the "
                "key use: `export GOOGLE_DIR_API_KEY=key` (again, use ! at the beginning of the line in "
                "jupyter)."
            )
    for request_nodes, api_request_attribs in api_requests.items():
        api_request_attribs["timestamp"] = time.time()
        api_request_attribs["request"] = make_request(
            api_request_attribs["origin"],
            api_request_attribs["destination"],
            key,
            departure_time,
            traffic_model,
        )
    return api_requests


def generate_requests(n: Network, osm_tags: Union[Callable, list[str]] = all) -> dict:
    """Generates a dictionary describing pairs of nodes for which we need to request directions from Google directions API.

    Args:
        n (Network): GeNet network.
        osm_tags (Union[Callable, list[str]], optional): OSM tags to subset the network on. Defaults to all (no subsetting).

    Raises:
        RuntimeError: Can only subset on tags for non-simplified networks.

    Returns:
        dict: Generated requests.
    """
    if n.is_simplified():
        logging.info("Generating Google Directions API requests for a simplified network.")
        return _generate_requests_for_simplified_network(n)
    elif (n.is_simplified()) and (osm_tags != all):
        raise RuntimeError(
            "OSM tags can only be specified if the network used to generate the requests is not "
            "simplified. Please use a non-simplified network as input or set osm_tags=all."
        )
    else:
        logging.info("Generating Google Directions API requests for a non-simplified network.")
        return _generate_requests_for_non_simplified_network(n, osm_tags)


def _generate_requests_for_non_simplified_network(
    n: Network, osm_tags: Union[Callable, list[str]] = all
) -> dict:
    """Generates a dictionary describing pairs of nodes for which we need to request directions from Google directions API.

    For a non-simplified network.

    Args:
        n (Network): Non-simplified network n.
        osm_tags (Union[Callable, list[str]], optional):
            If given, a list of OSM tags to subset the network on, e.g. ['primary', 'secondary', 'tertiary'].
            Defaults to all (no subsetting).

    Returns:
        dict: Generated requests.
    """
    if osm_tags == all:
        g = n.modal_subgraph(modes="car")
    else:
        g = n.subgraph_on_link_conditions(
            conditions=[{"attributes": {"osm:way:highway": osm_tags}}, {"modes": "car"}],
            how=all,
            mixed_dtypes=True,
        )

    simple_paths = simplification._get_edge_groups_to_simplify(g)

    node_diff = set(g.nodes) - set(itertools.chain.from_iterable(simple_paths))
    non_simplified_edges = set(g.out_edges(node_diff)) | set(g.in_edges(node_diff))
    all_paths = list(non_simplified_edges) + simple_paths

    api_requests = {}
    for path in all_paths:
        request_nodes = (path[0], path[-1])
        api_requests[request_nodes] = {
            "path_nodes": path,
            "path_polyline": polyline.encode(
                [(n.node(node)["lat"], n.node(node)["lon"]) for node in path]
            ),
            "origin": n.node(request_nodes[0]),
            "destination": n.node(request_nodes[1]),
        }
    return api_requests


def _generate_requests_for_simplified_network(n: Network) -> dict:
    """Generates a dictionary describing pairs of nodes for which we need to request directions from Google directions API.

    For a simplified network.

    Args:
        n (Network): Simplified network n.

    Returns:
        dict: Generated requests.
    """
    gdf_links = geojson.generate_geodataframes(n.modal_subgraph(modes="car"))["links"].to_crs(
        "epsg:4326"
    )
    gdf_links["path_polyline"] = gdf_links["geometry"].apply(
        lambda x: spatial.swap_x_y_in_linestring(x)
    )
    gdf_links["path_polyline"] = gdf_links["path_polyline"].apply(
        lambda x: spatial.encode_shapely_linestring_to_polyline(x)
    )

    gdf_links["path_nodes"] = gdf_links.apply(lambda x: (x["from"], x["to"]), axis=1)
    gdf_links["origin"] = gdf_links["from"].apply(lambda x: n.node(x))
    gdf_links["destination"] = gdf_links["to"].apply(lambda x: n.node(x))

    return gdf_links.set_index(["from", "to"])[
        ["path_polyline", "path_nodes", "origin", "destination"]
    ].T.to_dict()


def parse_route(route: dict):
    def compute_speed():
        total_distance = sum([leg["distance"]["value"] for leg in legs])
        total_duration = 0
        for leg in legs:
            if "duration_in_traffic" in leg:
                total_duration += leg["duration_in_traffic"]["value"]
            else:
                logging.warning(
                    f'duration_in_traffic was not found for leg: from: {leg["start_location"]} '
                    f'to: {leg["end_location"]}'
                )
                total_duration += leg["duration"]["value"]
        if total_duration == 0:
            logging.warning(
                "Duration of 0 detected. Route polyline: {}".format(
                    route["overview_polyline"]["points"]
                )
            )
            return 0
        return total_distance / total_duration

    legs = route["legs"]
    if len(legs) > 1:
        logging.warning(
            "Response has more than one leg. This is not consistent with driving requests."
        )
    data = {
        "google_speed": compute_speed(),
        "google_polyline": route["overview_polyline"]["points"],
    }
    return data


def parse_routes(response: requests.Response, path_polyline: str) -> dict:
    """Parses response contents to infer speed.

    If response returned more than one route, it picks the one closest on average to the original request.

    Args:
        response (requests.Response): request content
        path_polyline (str): original request path encoded list of lat lon tuples

    Returns:
        dict: Parsed routes.
    """
    data: dict = {}

    if response.status_code == 200:
        content = response.json()
        if content["routes"]:
            if len(content["routes"]) > 1:
                for route in content["routes"]:
                    route_data = parse_route(route)
                    route_data["polyline_proximity"] = (
                        spatial.compute_average_proximity_to_polyline(
                            route_data["google_polyline"], path_polyline
                        )
                    )
                    if data:
                        # pick closest one
                        if data["polyline_proximity"] > route_data["polyline_proximity"]:
                            data = route_data
                    else:
                        data = route_data
            else:
                data = parse_route(content["routes"][0])
        else:
            logging.info(f"Request did not yield any routes. Status: {content['status']}")
            if "error_message" in content:
                logging.info(f"Error message: {content['error_message']}")
    else:
        logging.warning(
            f"Request was not successful. Status code {response.status_code}. "
            f"Content of the unsuccessful response: {response.json()}"
        )
    return data


def parse_results(api_requests: dict) -> dict:
    """Goes through all api requests and parses results.

    Args:
        api_requests (dict): generated and 'sent' api requests.

    Returns:
        dict: Requests with parsed results.
    """
    api_requests_with_response = {}
    for node_request_pair, api_requests_attribs in api_requests.items():
        path_polyline = api_requests_attribs["path_polyline"]
        request = api_requests_attribs["request"]
        del api_requests_attribs["request"]
        api_requests_attribs["request_payload"] = request.result().json()
        api_requests_attribs["parsed_response"] = parse_routes(request.result(), path_polyline)
        api_requests_with_response[node_request_pair] = api_requests_attribs
    return api_requests_with_response


def map_results_to_edges(api_requests):
    google_dir_api_edge_data = {}
    for node_request_pair, api_requests_attribs in api_requests.items():
        path_nodes = api_requests_attribs["path_nodes"]
        parsed_request_data = api_requests_attribs["parsed_response"]

        edges = set(zip(path_nodes[:-1], path_nodes[1:]))

        current_edges = set(google_dir_api_edge_data.keys())
        overlapping_edges = edges & current_edges
        left_overs = edges - overlapping_edges
        google_dir_api_edge_data = {
            **google_dir_api_edge_data,
            **dict(zip(left_overs, [parsed_request_data] * len(left_overs))),
        }
    return google_dir_api_edge_data


def dump_all_api_requests_to_json(api_requests, output_dir, output_file_name=None):
    # sanitise tuple keys
    new_d = {}
    for k, v in api_requests.items():
        new_d["{}".format(k)] = "{}".format(v)

    if output_file_name is None:
        output_file_name = "api_requests.json"

    persistence.ensure_dir(output_dir)
    logging.info(f"Saving Google Directions API requests to {output_dir}")
    with open(os.path.join(output_dir, output_file_name), "w") as fp:
        json.dump(new_d, fp)
