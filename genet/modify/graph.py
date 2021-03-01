import genet.utils.spatial as spatial
from pyproj import Transformer


def reproj(nodes_dict, from_proj, to_proj):
    transformer = Transformer.from_crs(from_proj, to_proj, always_xy=True)
    new_attribs = {}
    for node, node_attrib in nodes_dict.items():
        x, y = spatial.change_proj(node_attrib['x'], node_attrib['y'], transformer)
        new_attribs[node] = {'x': x, 'y': y}
    return new_attribs
