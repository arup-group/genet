import networkx as nx
from pyproj import Proj, Transformer
from genet.inputs_handler import matsim_reader


class Network:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.spatial_tree = SpatialTree()
        self.schedule = dict()
        self.modes = []
        self.epsg = ''
        self.transformer = ''

    def read_matsim_network(self, path, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))
        self.graph, self.node_id_mapping, self.link_id_mapping = matsim_reader.read_network(path, self.transformer)

    def read_matsim_schedule(self, path, epsg):
        pass


class SpatialTree(nx.DiGraph):
    """
    Class which represents a nx.MultiDiGraph as a spatial tree
    hierarchy based on s2 cell levels
    """
    def __init__(self):
        super().__init__()
