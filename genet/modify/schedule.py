from pyproj import Transformer
from pandas import DataFrame
import genet.utils.spatial as spatial
from genet.max_stable_set import MaxStableSet
from genet import exceptions
import logging


def reproj_stops(schedule_element_nodes: dict, new_epsg):
    """
    :param schedule_element_nodes: dict stop ids : stop data including x, y, epsg
    :param new_epsg: 'epsg:1234', the epsg stops are being projected to
    :return: dict: stop ids from schedule_element_nodes: changed stop data in dict format new x, y and epsg
    """
    transformers = {epsg: Transformer.from_crs(epsg, new_epsg, always_xy=True) for epsg in
                    DataFrame(schedule_element_nodes).T['epsg'].unique()}

    reprojected_node_attribs = {}
    for node_id, node_attribs in schedule_element_nodes.items():
        x, y = spatial.change_proj(node_attribs['x'], node_attribs['y'], transformers[node_attribs['epsg']])
        reprojected_node_attribs[node_id] = {'x': x, 'y': y, 'epsg': new_epsg}
    return reprojected_node_attribs


def route_pt_graph(pt_graph, network_spatial_tree, modes, solver='glpk', allow_partial=False, distance_threshold=30,
                   step_size=10):
    logging.info(f'Building Maximum Stable Set for PT graph with {pt_graph.number_of_nodes()} stops and '
                 f'{pt_graph.number_of_edges()} edges')
    mss = MaxStableSet(
        pt_graph=pt_graph,
        network_spatial_tree=network_spatial_tree,
        modes=modes,
        distance_threshold=distance_threshold,
        step_size=step_size
    )
    if mss.is_partial:
        if allow_partial:
            logging.warning('Maximum Stable Set problem to snap the PT graph to the network is partially '
                            'viable, meaning not all stops have found a link to snap to within the distance_threshold.'
                            'Partial snapping is ON, this problem will proceed to the solver.')
        else:
            raise exceptions.PartialMaxStableSetProblem('This Problem is partial. To allow partially snapped '
                                                        'solutions set `allow_partial=True`')
    logging.info('Passing problem to solver')
    mss.solve(solver=solver)
    mss.route_edges()
    if allow_partial and mss.is_partial:
        logging.info(f'Successfully snapped {pt_graph.number_of_nodes() - len(mss.unsolved_stops)} stops to network '
                     'links.')
    if mss.unsolved_stops:
        mss.fill_in_solution_artificially()
    return mss
