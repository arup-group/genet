import itertools
import logging
import polyline
import osmnx as ox
import pickle
import os
import time
import json
from requests_futures.sessions import FuturesSession
import genet.utils.secrets_vault as secrets_vault
import genet.utils.spatial as spatial
import genet.utils.persistence as persistence
session = FuturesSession(max_workers=10)


def send_requests_for_network(n, request_number_threshold: int, output_dir, traffic: bool = False,
                              key: str = None, secret_name: str = None, region_name: str = None):
    """
    Generates, sends and parses results from Google Directions API for the car modal subgraph for network n.
    You can pass your API key to this function under `key` variable. Alternatively, you can use AWS Secrets manager
    for storing your API and pass secret_name and region_name (make sure you are authenticated to your AWS account).
    You can also export an environmental variable in your terminal $ export GOOGLE_DIR_API_KEY='your key'
    :param n: genet.Network
    :param request_number_threshold: max number of requests
    :param output_dir: output directory where to save the google directions api parsed data
    :param traffic: bool, whether to request traffic based information from the directions api
    :param key: API key
    :param secret_name: if using aws secrets manager, the name where your directions api key is stored
    :param region_name: the aws region you operate in
    :return:
    """
    logging.info('Generating Google Directions API requests')
    api_requests = generate_requests(n)

    persistence.ensure_dir(output_dir)
    logging.info(f'Saving Google Directions API requests to {output_dir}')
    with open(os.path.join(output_dir, 'api_requests.json'), 'w') as fp:
        json.dump(api_requests, fp)

    if len(api_requests) > request_number_threshold:
        raise RuntimeError(f'Number of requests exceeded the threshold. Number of requests: {len(api_requests)}')

    logging.info('Sending API requests')
    api_requests = send_requests(api_requests, key, secret_name, region_name, traffic)
    logging.info('Parsing API requests')
    api_requests = parse_results(api_requests, output_dir)

    logging.info(f'Saving Google Directions API requests to {output_dir}')
    with open(os.path.join(output_dir, 'api_requests.json'), 'w') as fp:
        json.dump(api_requests, fp)
    return api_requests


def read_saved_api_results(output_dir):
    """
    Read parsed Google Directions API requests in output_dir
    :param output_dir: output directory where the google directions api parsed data was saved
    :return:
    """
    api_requests = {}
    for file in os.listdir(output_dir):
        if file.endswith(".pickle"):
            response = os.path.join(output_dir, file)
            with open(response, 'rb') as handle:
                response_attribs = pickle.load(handle)
            api_requests[(response_attribs['path_nodes'][0], response_attribs['path_nodes'][-1])] = response_attribs
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
    :param n: genet.Network
    :return:
    """
    g = n.modal_subgraph(modes='car')

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


def send_requests(api_requests: dict, key: str = None, secret_name: str = None, region_name: str = None,
                  traffic: bool = False):
    if key is None:
        key = secrets_vault.get_google_directions_api_key(secret_name, region_name)
        if key is None:
            raise RuntimeError('API key was not found. Make sure you are authenticated and pointing in the correct '
                               'location if using AWS secrets manager, or that you have passed the correct key. '
                               'If using `GOOGLE_DIR_API_KEY` environmental variable, make sure you have spelled it '
                               'correctly. You can check this using `echo $GOOGLE_DIR_API_KEY` in the terminal you\'re '
                               'using or  `!echo $GOOGLE_DIR_API_KEY` if using jupyter notebook cells. To export the '
                               'key use: `export GOOGLE_DIR_API_KEY=key` (again, use ! at the beginning of the line in '
                               'jupyter).')

    for request_nodes, api_request_attribs in api_requests.items():
        api_request_attribs['timestamp'] = time.time()
        api_request_attribs['request'] = make_request(
            api_request_attribs['origin'], api_request_attribs['destination'], key, traffic)

    return api_requests


def parse_route(route: dict):
    def compute_speed():
        total_distance = sum([leg['distance']['value'] for leg in legs])
        total_duration = sum([leg['duration']['value'] for leg in legs])
        if total_duration == 0:
            logging.warning('Duration of 0 detected. Route polyline: {}'.format(route['overview_polyline']['points']))
            return 0
        return total_distance / total_duration

    legs = route['legs']
    if len(legs) > 1:
        logging.warning('Response has more than one leg. This is not consistent with driving requests.')
    data = {
        'google_speed': compute_speed(),
        'google_polyline': route['overview_polyline']['points']
    }
    return data


def parse_routes(response, path_polyline):
    """
    Parses response contents to infer speed. If response returned more than one route, it picks the one closest on
    average to the original request
    :param response: request content
    :param path_polyline: original request path encoded list of lat lon tuples
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
            logging.info(f"Request did not yield any routes. Status: {content['status']}")
            if 'error_message' in content:
                logging.info(f"Error message: {content['error_message']}")
    else:
        logging.warning(f'Request was not successful. Status code {response.status_code}. '
                        f'Content of the unsuccessful response: {response.json()}')
    return data


def parse_results(api_requests, output_dir):
    """
    Goes through all api requests, parses and pickles results to output_dir
    :param api_requests: generated and 'sent' api requests
    :param output_dir: output directory for parsed pickles of each api request
    :return:
    """
    persistence.ensure_dir(output_dir)
    for node_request_pair, api_requests_attribs in api_requests.items():
        path_polyline = api_requests_attribs['path_polyline']
        request = api_requests_attribs['request']
        api_requests_attribs['parsed_response'] = parse_routes(request.result(), path_polyline)
        pickle_result(api_requests_attribs, output_dir)
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


def pickle_result(api_requests_attribs, output_dir):
    del api_requests_attribs['request']
    with open(os.path.join(output_dir, '{}_{}.pickle'.format(
            api_requests_attribs['timestamp'],
            api_requests_attribs['parsed_response']['google_polyline'])), 'wb') as handle:
        pickle.dump(api_requests_attribs, handle, protocol=pickle.HIGHEST_PROTOCOL)
