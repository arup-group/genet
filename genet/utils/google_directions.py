import itertools
import logging
import polyline
import osmnx as ox
import pickle
import os
import time
from requests_futures.sessions import FuturesSession
import genet.utils.secrets_vault as secrets_vault
import genet.utils.spatial as spatial
session = FuturesSession(max_workers=10)


def send_requests_for_road_network(n, output_dir, traffic=False, secret_name: str = None, region_name: str = None):
    api_requests = generate_requests(n)
    api_requests = send_requests(api_requests, secret_name, region_name, traffic)
    api_requests = parse_results(api_requests, output_dir)
    return api_requests


def make_request(origin_attributes, destination_attributes, key, traffic):
    base_url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': '{},{}'.format(origin_attributes['lat'], origin_attributes['lon']),
        'destination': '{},{}'.format(destination_attributes['lat'], destination_attributes['lon']),
        'key': key
        }
    if traffic:
        params['departure_time'] = 'now'
    return session.get(base_url, params=params)


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

    api_requests = {}
    for path in all_paths:
        request_nodes = (path[0], path[-1])
        api_requests[request_nodes] = {
            'path_nodes': path,
            'path_polyline': polyline.encode([(n.node(node)['lat'], n.node(node)['lon']) for node in path]),
            'origin': n.node(request_nodes[0]),
            'destination': n.node(request_nodes[1])
        }

    return api_requests


def send_requests(api_requests: dict, secret_name: str = None, region_name: str = None, traffic: bool = False):
    key = secrets_vault.get_google_directions_api_key(secret_name, region_name)
    if key is None:
        raise RuntimeError('API key was not found. Make sure you are authenticated and pointing in the correct location'
                           'if using secrets manager, or that you have spelled the environmental variable correctly.'
                           'You can check this using `echo $GOOGLE_DIR_API_KEY` in the terminal you\'re using or '
                           '`!echo $GOOGLE_DIR_API_KEY` if using jupyter notebook cells. To export the key use: '
                           '`export GOOGLE_DIR_API_KEY=key` (again, use ! at the beginning of the line in jupyter).')

    for request_nodes, api_request_attribs in api_requests.items():
        api_request_attribs['timestamp'] = time.time()
        api_request_attribs['request'] = make_request(
            api_request_attribs['origin'], api_request_attribs['destination'], key, traffic)

    return api_requests


def parse_route(route: dict):
    legs = route['legs']
    if len(legs) > 1:
        logging.warning('Response has more than one leg. This is not consistent with driving requests.')
    data = {
        'google_speed': sum([leg['distance']['value'] / leg['duration']['value'] for leg in legs]),
        'google_polyline': route['overview_polyline']['points']
    }
    return data


def parse_routes(response, path_polyline):
    """
    Parses request contents to infer speeds and
    :param request: request content
    :return:
    """
    data = {}

    if response.status_code == 200:
        content = response.json()
        if content['routes']:
            if len(content['routes']) > 1:
                for route in content['routes']:
                    route_data = parse_route(route)
                    route_data['polyline_proximity'] = spatial.compute_average_proximity_to_polyline(
                        route_data['google_polyline'], path_polyline)
                    if data:
                        # pick closest one
                        if data['polyline_proximity'] > route_data['polyline_proximity']:
                            data = route_data
                    else:
                        data = route_data
            else:
                data = parse_route(content['routes'][0])
        else:
            logging.info('Request did not yield any routes. Status: {}'.format(content['status']))
            if 'error_message' in content:
                logging.info('Error message: {}'.format(content['error_message']))
    else:
        logging.warning('Request was not successful.')

    return data


def parse_results(api_requests, output_dir):
    """
    Generates a dictionary of all edges in values of api_request_paths with data harvest from the api for node pairs
    stored in keys api_requests paths
    :param api_requests:
    :return:
    """
    for node_request_pair, api_requests_attribs in api_requests.items():
        path_polyline = api_requests_attribs['path_polyline']
        request = api_requests_attribs['request']
        api_requests_attribs['parsed_response'] = parse_routes(request.result(), path_polyline)
        save_result(api_requests_attribs, output_dir)
    return api_requests


def map_results_to_edges(api_requests):
    google_dir_api_edge_data = {}
    for node_request_pair, api_requests_attribs in api_requests.items():
        path_nodes = api_requests_attribs['path_nodes']
        parsed_request_data = api_requests_attribs['parsed_response']

        edges = set(zip(path_nodes[:-1], path_nodes[1:]))

        current_edges = set(google_dir_api_edge_data.keys())
        overlapping_edges = edges & current_edges
        left_overs = edges - overlapping_edges
        google_dir_api_edge_data = {**google_dir_api_edge_data,
                                    **dict(zip(left_overs, [parsed_request_data] * len(left_overs)))}
    return google_dir_api_edge_data


def save_result(api_requests_attribs, output_dir):
    del api_requests_attribs['request']
    with open(os.path.join(output_dir, '{}_{}.pickle'.format(
            api_requests_attribs['timestamp'],
            api_requests_attribs['parsed_response']['google_polyline'])), 'wb') as handle:
        pickle.dump(api_requests_attribs, handle, protocol=pickle.HIGHEST_PROTOCOL)
