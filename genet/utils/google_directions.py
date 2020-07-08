import itertools
import logging
import osmnx as ox
from requests_futures.sessions import FuturesSession
import genet.utils.secrets_vault as secrets_vault
session = FuturesSession(max_workers=10)


def make_request(origin_attributes, destination_attributes, key):
    base_url = 'https://maps.googleapis.com/maps/api/directions/json'
    return session.get(
        base_url,
        params={
            'origin': '{},{}'.format(origin_attributes['lat'], origin_attributes['lon']),
            'destination': '{},{}'.format(destination_attributes['lat'], destination_attributes['lon']),
            'key': key
        })


def generate_requests(n):
    """
    Generates two dictionaries, both of them have keys that describe a pair of nodes for which we need to request
    directions from Google directions API
    :param n:
    :param secret_name:
    :param region_name:
    :return:
    """
    # TODO add car modal subgraph
    g = n.graph

    simple_paths = list(ox.simplification._get_paths_to_simplify(g))
    node_diff = set(g.nodes) - set(itertools.chain.from_iterable(simple_paths))
    non_simplified_edges = set(g.out_edges(node_diff)) | set(g.in_edges(node_diff))
    all_paths = list(non_simplified_edges) + simple_paths

    api_request_paths = zip([(path[0], path[-1]) for path in all_paths], all_paths)

    return api_request_paths


def send_requests(n, api_request_paths: dict = None, secret_name: str = None, region_name: str = None):
    key = secrets_vault.get_google_directions_api_key(secret_name, region_name)
    if key is None:
        raise RuntimeError('API key was not found. Make sure you are authenticated and pointing in the correct location'
                           'if using secrets manager, or that you have spelled the environmental variable correctly.'
                           'You can check this using `echo $GOOGLE_DIR_API_KEY` in the terminal you\'re using or '
                           '`!echo $GOOGLE_DIR_API_KEY` if using jupyter notebook cells. To export the key use: '
                           '`export GOOGLE_DIR_API_KEY=key` (again, use ! at the beginning of the line in jupyter).')

    if api_request_paths is None:
        api_request_paths = generate_requests(n)

    api_requests = {}
    for request_nodes, path in api_request_paths.items():
        origin = n.node(request_nodes[0])
        destination = n.node(request_nodes[1])
        api_requests[request_nodes] = make_request(origin, destination, key)

    return api_requests


def parse_route(route: dict):
    legs = route['legs']
    if len(legs) > 1:
        logging.warning('Response has more than one leg. This is not consistent with driving requests.')


def consolidate_routes():
    pass


def parse_routes(response):
    """
    Parses request contents to infer speeds and
    :param request: request content
    :return:
    """
    data = {}

    if response.status_code == 200:
        content = response.json()
        if content['routes']:
            for route in content['routes']:
                parse_route(route)
        else:
            logging.info('Request did not yield any routes. Status: {}'.format(content['status']))
            if 'error_message' in content:
                logging.info('Error message: {}'.format(content['error_message']))
    else:
        logging.warning('Request was not successful.')

    return data


def parse_results(api_request_paths, api_requests):
    """
    Generates a dictionary of all edges in values of api_request_paths with data harvest from the api for node pairs
    stored in keys of both api_request_paths and api_requests
    :param api_request_paths:
    :param api_requests:
    :return:
    """
    google_dir_api_edge_data = {}
    for node_request_pair, request in api_requests.items():
        parsed_request_data = parse_routes(request.result())
        path = api_request_paths[node_request_pair]
        edges = set(zip(path[:-1], path[1:]))
        current_edges = set(google_dir_api_edge_data.keys())
        overlapping_edges = edges & current_edges
        if overlapping_edges:
            pass
        else:
            google_dir_api_edge_data = dict(zip(edges, list(parsed_request_data)*len(edges)))
