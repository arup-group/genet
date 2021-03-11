from pyproj import Transformer
from pandas import DataFrame
import genet.utils.spatial as spatial


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
