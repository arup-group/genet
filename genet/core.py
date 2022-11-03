import itertools
import json
import logging
import os
import traceback
import uuid
from copy import deepcopy
from typing import Union, List, Dict

import genet.auxiliary_files as auxiliary_files
import genet.exceptions as exceptions
import genet.modify.change_log as change_log
import genet.modify.graph as modify_graph
import genet.modify.schedule as modify_schedule
import genet.output.geojson as geojson
import genet.output.matsim_xml_writer as matsim_xml_writer
import genet.output.sanitiser as sanitiser
import genet.schedule_elements as schedule_elements
import genet.utils.dict_support as dict_support
import genet.utils.elevation as elevation
import genet.utils.graph_operations as graph_operations
import genet.utils.pandas_helpers as pd_helpers
import genet.utils.parallel as parallel
import genet.utils.persistence as persistence
import genet.utils.plot as plot
import genet.utils.simplification as simplification
import genet.utils.spatial as spatial
import genet.validate.network as network_validation
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from pyproj import Transformer
from s2sphere import CellId

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class Network:
    def __init__(self, epsg, **kwargs):
        self.epsg = epsg
        self.transformer = Transformer.from_crs(epsg, 'epsg:4326', always_xy=True)
        self.graph = nx.MultiDiGraph(name='Network graph', crs=epsg)
        self.attributes = {'crs': epsg}
        self.schedule = schedule_elements.Schedule(epsg)
        self.change_log = change_log.ChangeLog()
        self.auxiliary_files = {'node': {}, 'link': {}}
        # link_id_mapping maps between (usually string literal) index per edge to the from and to nodes that are
        # connected by the edge
        self.link_id_mapping = {}
        if kwargs:
            self.add_additional_attributes(kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__} instance at {id(self)}: with \ngraph: {nx.info(self.graph)} and " \
               f"\nschedule {self.schedule.info()}"

    def __str__(self):
        return self.info()

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        :param attribs: the additional attributes {attribute_name: attribute_value}
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__:
                setattr(self, k, v)
            else:
                logging.warning(
                    f"{self.__class__.__name__} already has an additional attribute: {k}. "
                    "Consider overwritting it instead.")

    def has_attrib(self, attrib_name):
        return attrib_name in self.__dict__

    def add(self, other):
        """
        This lets you add on `other` genet.Network to the network this method is called on.
        This is deliberately not a magic function to discourage `new_network = network_1 + network_2` (and memory
        goes out the window)
        :param other:
        :return:
        """
        if self.is_simplified() != other.is_simplified():
            raise RuntimeError('You cannot add simplified and non-simplified networks together')

        # consolidate coordinate systems
        if other.epsg != self.epsg:
            logging.info(f'Attempting to merge two networks in different coordinate systems. '
                         f'Reprojecting from {other.epsg} to {self.epsg}')
            other.reproject(other.epsg)
        # consolidate node ids
        other = graph_operations.consolidate_node_indices(self, other)
        # consolidate link ids
        other = graph_operations.consolidate_link_indices(self, other)

        # finally, once the node and link ids have been sorted, combine the graphs
        # nx.compose(left, right) overwrites data in left with data in right under matching ids
        self.graph = nx.compose(other.graph, self.graph)
        # finally, combine link_id_mappings
        self.link_id_mapping = {**other.link_id_mapping, **self.link_id_mapping}

        # combine schedules
        self.schedule.add(other.schedule)

        # merge change_log DataFrames
        self.change_log = self.change_log.merge_logs(other.change_log)

    def print(self):
        print(self.info())

    def info(self):
        return f"Graph info: {nx.info(self.graph)} \nSchedule info: {self.schedule.info()}"

    def plot(self, output_dir='', data=False):
        """
        Plots the network graph and schedule on kepler map.
        Ensure all prerequisites are installed https://docs.kepler.gl/docs/keplergl-jupyter#install
        :param output_dir: output directory for the image, if passed, will save plot to html
        :param data: Defaults to False, only the geometry and ID will be visible.
            True will visualise all data on the map (not suitable for large networks)
            A set of keys e.g. {'freespeed', 'capacity'}
        :return:
        """
        if not self.schedule:
            logging.warning('This Network does not have a PT schedule. Only the graph will be visualised.')
            return self.plot_graph(output_dir=output_dir)
        network_links = self.to_geodataframe()['links']
        schedule_routes = self.schedule_network_routes_geodataframe()

        if data is not True:
            network_links = sanitiser._subset_plot_gdf(data, network_links, base_keys={'id', 'geometry'})
            schedule_routes = sanitiser._subset_plot_gdf(data, schedule_routes, base_keys={'route_id', 'geometry'})

        m = plot.plot_geodataframes_on_kepler_map(
            {'network_links': sanitiser.sanitise_geodataframe(network_links),
             'schedule_routes': sanitiser.sanitise_geodataframe(schedule_routes)},
            kepler_config='network_with_pt'
        )
        if output_dir:
            persistence.ensure_dir(output_dir)
            m.save_to_html(file_name=os.path.join(output_dir, 'network_with_pt_routes.html'))
        return m

    def plot_graph(self, output_dir='', data=False):
        """
        Plots the network graph only on kepler map.
        Ensure all prerequisites are installed https://docs.kepler.gl/docs/keplergl-jupyter#install
        :param output_dir: output directory for the image, if passed, will save plot to html
        :param data: Defaults to False, only the geometry and ID will be visible.
            True will visualise all data on the map (not suitable for large networks)
            A set of keys e.g. {'freespeed', 'capacity'}
        :return:
        """
        network_links = self.to_geodataframe()['links']

        if data is not True:
            network_links = sanitiser._subset_plot_gdf(data, network_links, base_keys={'id', 'geometry'})

        m = plot.plot_geodataframes_on_kepler_map(
            {'network_links': sanitiser.sanitise_geodataframe(network_links)},
            kepler_config='network_with_pt'
        )
        if output_dir:
            persistence.ensure_dir(output_dir)
            m.save_to_html(file_name=os.path.join(output_dir, 'network_graph.html'))
        return m

    def plot_schedule(self, output_dir='', data=False):
        """
        Plots original stop connections in the network's schedule over the network graph on kepler map.
        Ensure all prerequisites are installed https://docs.kepler.gl/docs/keplergl-jupyter#install
        :param output_dir: output directory for the image, if passed, will save plot to html
        :param data: Defaults to False, only the geometry and ID will be visible.
            True will visualise all data on the map (not suitable for large networks)
            A set of keys e.g. {'freespeed', 'capacity'}
        :return:
        """
        network_links = self.to_geodataframe()['links']
        schedule_gdf = self.schedule.to_geodataframe()

        if data is not True:
            network_links = sanitiser._subset_plot_gdf(data, network_links, base_keys={'id', 'geometry'})
            schedule_gdf['links'] = sanitiser._subset_plot_gdf(data, schedule_gdf['links'],
                                                               base_keys={'route_id', 'geometry'})
            schedule_gdf['nodes'] = sanitiser._subset_plot_gdf(data, schedule_gdf['nodes'],
                                                               base_keys={'id', 'geometry'})

        m = plot.plot_geodataframes_on_kepler_map(
            {'network_links': sanitiser.sanitise_geodataframe(network_links),
             'schedule_links': sanitiser.sanitise_geodataframe(schedule_gdf['links']),
             'schedule_stops': sanitiser.sanitise_geodataframe(schedule_gdf['nodes'])},
            kepler_config='network_and_schedule'
        )
        if output_dir:
            persistence.ensure_dir(output_dir)
            m.save_to_html(file_name=os.path.join(output_dir, 'network_and_schedule.html'))
        return m

    def reproject(self, new_epsg, processes=1):
        """
        Changes projection of the network to new_epsg
        :param new_epsg: 'epsg:1234'
        :param processes: max number of process to split computation across
        :return:
        """
        # reproject nodes
        nodes_attribs = dict(self.nodes())
        new_nodes_attribs = parallel.multiprocess_wrap(
            data=nodes_attribs, split=parallel.split_dict, apply=modify_graph.reproj, combine=parallel.combine_dict,
            processes=processes, from_proj=self.epsg, to_proj=new_epsg)
        self.apply_attributes_to_nodes(new_nodes_attribs)

        # reproject geometries
        gdf_geometries = gpd.GeoDataFrame(self.link_attribute_data_under_keys(['geometry']), crs=self.epsg)
        gdf_geometries = gdf_geometries.to_crs(new_epsg)
        new_link_attribs = gdf_geometries.T.to_dict()
        self.apply_attributes_to_links(new_link_attribs)

        if self.schedule:
            self.schedule.reproject(new_epsg, processes)
        self.initiate_crs_transformer(new_epsg)
        self.graph.graph['crs'] = self.epsg

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        if epsg != 'epsg:4326':
            self.transformer = Transformer.from_crs(epsg, 'epsg:4326', always_xy=True)
        else:
            self.transformer = None

    def simplify(self, no_processes=1, keep_loops=False):
        """
        Simplifies network graph, retaining only nodes that are junctions
        :param no_processes: Number of processes to split some computation across. The method is pretty fast though
            and 1 process is often preferable --- there is overhead for splitting and joining the data.
        :param keep_loops: bool, defaults to False. Simplification often leads to self-loops, these will be removed
            unless keep_loops=True
        :return: None, updates Network object
        """
        if self.is_simplified():
            raise RuntimeError('This network has already been simplified. You cannot simplify the graph twice.')
        simplification.simplify_graph(self, no_processes)

        df = self.link_attribute_data_under_keys(keys=['from', 'to'])
        df = df[df['from'] == df['to']]
        loops = set(df.index)
        # pt stops can be loops
        pt_stop_loops = set(self.schedule.stop_attribute_data(keys=['linkRefId'])['linkRefId'])
        useless_self_loops = loops - pt_stop_loops
        if useless_self_loops:
            logging.warning(f'Simplification led to {len(loops)} self-loop links in the network. '
                            f'{len(useless_self_loops)} are not connected to the PT stops.')
            if not keep_loops:
                logging.info('The self-loops with no reference to PT stops will now be removed. '
                             'To disable this behaviour, use `keep_loops=True`. '
                             'Investigate the change log for more information about these links.')
                self.remove_links(useless_self_loops)
                # delete removed links from the simplification map
                self.link_simplification_map = {k: v for k, v in self.link_simplification_map.items() if
                                                v not in useless_self_loops}

        # mark graph as having been simplified
        self._mark_as_simplified()

    def _mark_as_simplified(self):
        self.attributes['simplified'] = True

    def is_simplified(self):
        if 'simplified' in self.attributes:
            # range of values for backwards compatibility
            return self.attributes['simplified'] in {'true', 'True', True}
        return False

    def node_attribute_summary(self, data=False):
        """
        Parses through data stored on nodes and gives a summary tree of the data stored on the nodes.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.nodes(), data=data)
        graph_operations.render_tree(root, data)

    def node_attribute_data_under_key(self, key):
        """
        Generates a pandas.Series object indexed by node ids, with data stored on the nodes under `key`
        :param key: either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        data = graph_operations.get_attribute_data_under_key(self.nodes(), key)
        return pd.Series(data, dtype=pd_helpers.get_pandas_dtype(data))

    def node_attribute_data_under_keys(self, keys: Union[list, set], index_name=None):
        """
        Generates a pandas.DataFrame object indexed by link ids, with data stored on the nodes under `key`
        :param keys: list of either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        return graph_operations.build_attribute_dataframe(self.nodes(), keys=keys, index_name=index_name)

    def link_attribute_summary(self, data=False):
        """
        Parses through data stored on links and gives a summary tree of the data stored on the links.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.links(), data=data)
        graph_operations.render_tree(root, data)

    def link_attribute_data_under_key(self, key: Union[str, dict]):
        """
        Generates a pandas.Series object indexed by link ids, with data stored on the links under `key`
        :param key: either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        return pd.Series(graph_operations.get_attribute_data_under_key(self.links(), key))

    def link_attribute_data_under_keys(self, keys: Union[list, set], index_name=None):
        """
        Generates a pandas.DataFrame object indexed by link ids, with data stored on the links under `key`
        :param keys: list of either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        return graph_operations.build_attribute_dataframe(self.links(), keys=keys, index_name=index_name)

    def extract_nodes_on_node_attributes(self, conditions: Union[list, dict], how=any, mixed_dtypes=True):
        """
        Extracts graph node IDs based on values of attributes saved on the nodes. Fails silently,
        assumes not all nodes have all of the attributes. In the case were the attributes stored are
        a list or set, like in the case of a simplified network (there will be a mix of objects that are sets and not)
        an intersection of values satisfying condition(s) is considered in case of iterable value, if not empty, it is
        deemed successful by default. To disable this behaviour set mixed_dtypes to False.
        :param conditions: {'attribute_key': 'target_value'} or nested
        {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

            - single value, string, int, float, where the edge_data[key] == value
                (if mixed_dtypes==True and in case of set/list edge_data[key], value is in edge_data[key])

            - list or set of single values as above, where edge_data[key] in [value1, value2]
                (if mixed_dtypes==True and in case of set/list edge_data[key],
                set(edge_data[key]) & set([value1, value2]) is non-empty)

            - for int or float values, two-tuple bound (lower_bound, upper_bound) where
              lower_bound <= edge_data[key] <= upper_bound
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] satisfies lower_bound <= item <= upper_bound)

            - function that returns a boolean given the value e.g.

            def below_exclusive_upper_bound(value):
                return value < 100

                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

        :param how : {all, any}, default any

        The level of rigour used to match conditions

            * all: means all conditions need to be met
            * any: means at least one condition needs to be met

        :param mixed_dtypes: True by default, used if values under dictionary keys queried are single values or lists of
        values e.g. as in simplified networks.
        :return: list of node ids in the network satisfying conditions
        """
        return graph_operations.extract_on_attributes(
            self.nodes(), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)

    def extract_links_on_edge_attributes(self, conditions: Union[list, dict], how=any, mixed_dtypes=True):
        """
        Extracts graph link IDs based on values of attributes saved on the edges. Fails silently,
        assumes not all links have those attributes. In the case were the attributes stored are
        a list or set, like in the case of a simplified network (there will be a mix of objects that are sets and not)
        an intersection of values satisfying condition(s) is considered in case of iterable value, if not empty, it is
        deemed successful by default. To disable this behaviour set mixed_dtypes to False.
        :param conditions: {'attribute_key': 'target_value'} or nested
        {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

            - single value, string, int, float, where the edge_data[key] == value
                (if mixed_dtypes==True and in case of set/list edge_data[key], value is in edge_data[key])

            - list or set of single values as above, where edge_data[key] in [value1, value2]
                (if mixed_dtypes==True and in case of set/list edge_data[key],
                set(edge_data[key]) & set([value1, value2]) is non-empty)

            - for int or float values, two-tuple bound (lower_bound, upper_bound) where
              lower_bound <= edge_data[key] <= upper_bound
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] satisfies lower_bound <= item <= upper_bound)

            - function that returns a boolean given the value e.g.

            def below_exclusive_upper_bound(value):
                return value < 100

                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

        :param how : {all, any}, default any

        The level of rigour used to match conditions

            * all: means all conditions need to be met
            * any: means at least one condition needs to be met

        :param mixed_dtypes: True by default, used if values under dictionary keys queried are single values or lists of
        values e.g. as in simplified networks.
        :return: list of link ids in the network satisfying conditions
        """
        return graph_operations.extract_on_attributes(
            self.links(), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)

    def links_on_modal_condition(self, modes: Union[str, list]):
        """
        Finds link IDs with modes or singular mode given in `modes`
        :param modes: string mode e.g. 'car' or a list of such modes e.g. ['car', 'walk']
        :return: list of link IDs
        """
        return self.extract_links_on_edge_attributes(conditions={'modes': modes}, mixed_dtypes=True)

    def nodes_on_modal_condition(self, modes: Union[str, list]):
        """
        Finds node IDs with modes or singular mode given in `modes`
        :param modes: string mode e.g. 'car' or a list of such modes e.g. ['car', 'walk']
        :return: list of link IDs
        """
        links = self.links_on_modal_condition(modes)
        nodes = {self.link(link)['from'] for link in links} | {self.link(link)['to'] for link in links}
        return list(nodes)

    def modal_subgraph(self, modes: Union[str, set, list]):
        return self.subgraph_on_link_conditions(conditions={'modes': modes}, mixed_dtypes=True)

    def nodes_on_spatial_condition(self, region_input):
        """
        Returns node IDs which intersect region_input
        :param region_input:
            - path to a geojson file, can have multiple features
            - string with comma separated hex tokens of Google's S2 geometry, a region can be covered with cells and
             the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/
             e.g. '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'
            - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects
        :return: node IDs
        """
        if not isinstance(region_input, str):
            # assumed to be a shapely.geometry input
            gdf = self.to_geodataframe()['nodes'].to_crs("epsg:4326")
            return self._find_ids_on_shapely_geometry(gdf, how='intersect', shapely_input=region_input)
        elif persistence.is_geojson(region_input):
            gdf = self.to_geodataframe()['nodes'].to_crs("epsg:4326")
            return self._find_ids_on_geojson(gdf, how='intersect', geojson_input=region_input)
        else:
            # is assumed to be hex
            return self._find_node_ids_on_s2_geometry(region_input)

    def links_on_spatial_condition(self, region_input, how='intersect'):
        """
        Returns link IDs which intersect region_input
        :param region_input:
            - path to a geojson file, can have multiple features
            - string with comma separated hex tokens of Google's S2 geometry, a region can be covered with cells and
             the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/
             e.g. '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'
            - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects
        :param how:
            - 'intersect' default, will return IDs of the Services whose at least one Stop intersects the
            region_input
            - 'within' will return IDs of the Services whose all of the Stops are contained within the region_input
        :return: link IDs
        """
        gdf = self.to_geodataframe()['links'].to_crs("epsg:4326")
        if not isinstance(region_input, str):
            # assumed to be a shapely.geometry input
            return self._find_ids_on_shapely_geometry(gdf, how, region_input)
        elif persistence.is_geojson(region_input):
            return self._find_ids_on_geojson(gdf, how, region_input)
        else:
            # is assumed to be hex
            return self._find_link_ids_on_s2_geometry(gdf, how, region_input)

    def subnetwork(self, links: Union[list, set], services: Union[list, set] = None,
                   strongly_connected_modes: Union[list, set] = None, n_connected_components: int = 1):
        """
        Subset a Network object using a collection of link IDs and (optionally) service IDs
        :param links: Link IDs to be retained in the new Network
        :param services: optional, collection of service IDs in the Schedule for subsetting.
        :param strongly_connected_modes: modes in the network that need to be strongly connected. For MATSim those
            are modes that agents are allowed to route on. Defaults to {'car', 'walk', 'bike'}
        :param n_connected_components: number of expected strongly connected components for
            `the strongly_connected_modes`. Defaults to 1, as that is what MATSim expects. Other number may be used
            if disconnected islands are expected, and then connected up using the `connect_components` method.
        :return: A new Network object that is a subset of the original
        """
        logging.info('Subsetting a Network will likely result in a disconnected network graph. A cleaner will be ran '
                     'that will remove links to make the resulting Network strongly connected for modes: '
                     'car, walk, bike.')
        subnetwork = Network(epsg=self.epsg)
        links = set(links)
        if self.schedule:
            if services:
                logging.info(
                    f'Schedule will be subsetted using given services: {services}. Links pertaining to their '
                    'network routes will also be retained.')
                subschedule = self.schedule.subschedule(services)
                routes = subschedule.route_attribute_data(keys=['route'])
                links = links | set(np.concatenate(routes['route'].values))
                subnetwork.schedule = subschedule
        subnetwork.graph = self.subgraph_on_link_conditions(conditions={'id': links})
        subnetwork.link_id_mapping = {k: v for k, v in self.link_id_mapping.items() if k in links}

        if strongly_connected_modes is None:
            logging.info("Param: strongly_connected_modes is defaulting to `{'car', 'walk', 'bike'}` "
                         "You can change this behaviour by passing the parameter.")
            strongly_connected_modes = {'car', 'walk', 'bike'}
        for mode in strongly_connected_modes:
            if not subnetwork.is_strongly_connected(modes=mode):
                logging.warning(f'The graph for mode {mode} is not strongly connected. '
                                f'The largest {n_connected_components} connected components will be extracted.')
                if n_connected_components > 1:
                    logging.info('Number of requested connected components is larger than 1. Consider using '
                                 '`connect_components` method to create modal graphs that are strongly connected.')
                subnetwork.retain_n_connected_subgraphs(n=n_connected_components, mode=mode)

        # TODO Inherit and subset Auxiliary files

        logging.info('Subsetted Network is ready - do not forget to validate and visualise your subset!')
        return subnetwork

    def subnetwork_on_spatial_condition(self, region_input, how='intersect',
                                        strongly_connected_modes: Union[list, set] = None,
                                        n_connected_components: int = 1):
        """
        Subset a Network object using a spatial bound
        :param region_input:
            - path to a geojson file, can have multiple features
            - string with comma separated hex tokens of Google's S2 geometry, a region can be covered with cells and
             the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/
             e.g. '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'
            - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects
        :param how:
            - 'intersect' default, will return IDs of the Services whose at least one Stop intersects the
            region_input
            - 'within' will return IDs of the Services whose all of the Stops are contained within the region_input
        :param strongly_connected_modes: modes in the network that need to be strongly connected. For MATSim those
            are modes that agents are allowed to route on. Defaults to {'car', 'walk', 'bike'}
        :param n_connected_components: number of expected strongly connected components for
            `the strongly_connected_modes`. Defaults to 1, as that is what MATSim expects. Other number may be used
            if disconnected islands are expected, and then connected up using the `connect_components` method.
        :return: A new Network object that is a subset of the original
        """
        if self.schedule:
            services_to_keep = self.schedule.services_on_spatial_condition(region_input=region_input, how=how)
        else:
            services_to_keep = None

        subset_links = set(self.links_on_spatial_condition(region_input=region_input, how=how))
        return self.subnetwork(links=subset_links, services=services_to_keep,
                               strongly_connected_modes=strongly_connected_modes,
                               n_connected_components=n_connected_components)

    def remove_mode_from_links(self, links: Union[set, list], mode: Union[set, list, str]):
        """
        Method to remove modes from links. Deletes links which have no mode left after the process.
        :param links: collection of link IDs to remove the mode from
        :param mode: which mode to remove
        :return: updates graph
        """

        def empty_modes(mode_attrib):
            if not mode_attrib:
                return True
            return False

        links = persistence.setify(links)
        mode = persistence.setify(mode)

        df = self.link_attribute_data_under_keys(['modes'])
        extra = links - set(df.index)
        if extra:
            logging.warning(f'The following links are not present: {extra}')

        df['modes'] = df['modes'].apply(lambda x: persistence.setify(x))

        df = df.loc[links & set(df.index)][df['modes'].apply(lambda x: bool(mode & x))]
        df['modes'] = df['modes'].apply(lambda x: x - mode)
        self.apply_attributes_to_links(df.T.to_dict())

        # remove links without modes
        no_mode_links = graph_operations.extract_on_attributes(
            self.links(),
            {'modes': empty_modes},
            mixed_dtypes=False
        )
        self.remove_links(no_mode_links)

    def retain_n_connected_subgraphs(self, n: int, mode: str):
        """
        Method to remove modes from link which do not belong to largest connected n components. Deletes links which
        have no mode left after the process.
        :param n: number of components to retain
        :param mode: which mode to consider
        :return: updates graph
        """
        modal_subgraph = self.modal_subgraph(mode)
        # calculate how many connected subgraphs there are
        connected_components = network_validation.find_connected_subgraphs(modal_subgraph)
        connected_components_nodes = []
        for i in range(0, n):
            connected_components_nodes += connected_components[i][0]
        connected_subgraphs_to_extract = modal_subgraph.subgraph(connected_components_nodes).copy().edges.data('id')
        diff_links = set([e[2] for e in modal_subgraph.edges.data('id')]) - set(
            [e[2] for e in connected_subgraphs_to_extract])
        logging.info(f'Extracting largest connected components resulted in mode: {mode} being deleted from '
                     f'{len(diff_links)} edges')
        self.remove_mode_from_links(diff_links, mode)

    def _find_ids_on_geojson(self, gdf, how, geojson_input):
        shapely_input = spatial.read_geojson_to_shapely(geojson_input)
        return self._find_ids_on_shapely_geometry(gdf=gdf, how=how, shapely_input=shapely_input)

    def _find_ids_on_shapely_geometry(self, gdf, how, shapely_input):
        if how == 'intersect':
            return list(gdf[gdf.intersects(shapely_input)]['id'])
        if how == 'within':
            return list(gdf[gdf.within(shapely_input)]['id'])
        else:
            raise NotImplementedError('Only `intersect` and `contain` options for `how` param.')

    def _find_node_ids_on_s2_geometry(self, s2_input):
        cell_union = spatial.s2_hex_to_cell_union(s2_input)
        return [_id for _id, s2_id in self.graph.nodes(data='s2_id') if cell_union.intersects(CellId(s2_id))]

    def _find_link_ids_on_s2_geometry(self, gdf, how, s2_input):
        gdf['geometry'] = gdf['geometry'].apply(lambda x: spatial.swap_x_y_in_linestring(x))
        gdf['s2_geometry'] = gdf['geometry'].apply(lambda x: spatial.generate_s2_geometry(x))
        gdf = gdf.set_index('id')
        links = gdf['s2_geometry'].T.to_dict()

        cell_union = spatial.s2_hex_to_cell_union(s2_input)
        if how == 'intersect':
            return [_id for _id, s2_geom in links.items() if
                    any([cell_union.intersects(CellId(s2_id)) for s2_id in s2_geom])]
        elif how == 'within':
            return [_id for _id, s2_geom in links.items() if
                    all([cell_union.intersects(CellId(s2_id)) for s2_id in s2_geom])]
        else:
            raise NotImplementedError('Only `intersect` and `within` options for `how` param.')

    def add_node(self, node: Union[str, int], attribs: dict, silent: bool = False):
        """
        Adds a node.
        :param node:
        :param attribs: must include spatial information x,y in epsg consistent with the network,
        or lat lon in epsg:4326
        :param silent: whether to mute stdout logging messages
        :return:
        """
        return self.add_nodes({node: attribs}, silent=silent)[0]

    def add_nodes(self, nodes_and_attribs: dict, silent: bool = False, ignore_change_log: bool = False):
        """
        Adds nodes, reindexes if indices are clashing with nodes already in the network
        :param nodes_and_attribs: {index_for_node: {attribute dictionary for that node}}
        :param silent: whether to mute stdout logging messages
        :param ignore_change_log: whether to ignore logging changes to the network in the changelog. False by default
        and not recommended. Only used when an alternative changelog event is being produced (e.g. simplification) to
        reduce changelog bloat.
        :return:
        """
        # check for spatial info
        for node_id, attribs in nodes_and_attribs.items():
            keys = set(attribs.keys())
            if not ({'lat', 'lon'}.issubset(keys) or {'x', 'y'}.issubset(keys)):
                raise RuntimeError(f'Cannot add Node `{node_id}` without spatial information. '
                                   f'Given attributes: `{keys}` are not sufficient. This method requires lat, lon '
                                   f'attributes in epsg:4326 or x, y in epsg of the network: {self.epsg}')

        # check for clashing node IDs
        clashing_node_ids = set(dict(self.nodes()).keys()) & set(nodes_and_attribs.keys())

        df_nodes = pd.DataFrame(nodes_and_attribs).T
        reindexing_dict = {}
        if ('id' not in df_nodes.columns) or (df_nodes['id'].isnull().any()):
            df_nodes['id'] = df_nodes.index
        if not {'lat', 'lon'}.issubset(set(df_nodes.columns)):
            df_nodes[['lon', 'lat']] = float('nan')
        if not {'x', 'y'}.issubset(set(df_nodes.columns)):
            df_nodes[['x', 'y']] = float('nan')
        if df_nodes[['lon', 'lat']].isnull().any().any():
            missing_lat_lon = df_nodes[['lon', 'lat']].isnull().T.any()
            df_nodes.loc[missing_lat_lon, ['lon', 'lat']] = pd.DataFrame(list(df_nodes.loc[missing_lat_lon].apply(
                lambda row: spatial.change_proj(row['x'], row['y'], self.transformer), axis=1)),
                columns=['lon', 'lat'], index=df_nodes.loc[missing_lat_lon].index
            )
        if df_nodes[['x', 'y']].isnull().any().any():
            missing_x_y = df_nodes[['x', 'y']].isnull().T.any()
            transformer = Transformer.from_crs('epsg:4326', self.epsg, always_xy=True)
            df_nodes.loc[missing_x_y, ['x', 'y']] = pd.DataFrame(list(df_nodes.loc[missing_x_y].apply(
                lambda row: spatial.change_proj(row['lon'], row['lat'], transformer), axis=1)),
                columns=['x', 'y'], index=df_nodes.loc[missing_x_y].index
            )

        nodes_and_attribs_to_add = dict_support.merge_complex_dictionaries(
            df_nodes[['x', 'y', 'lon', 'lat', 'id']].T.to_dict(), nodes_and_attribs)

        # pandas is terrible with large numbers so we update them/generate them here
        for node, attribs in nodes_and_attribs_to_add.items():
            if 's2_id' not in nodes_and_attribs[node]:
                attribs['s2_id'] = spatial.generate_index_s2(attribs['lat'], attribs['lon'])
        if clashing_node_ids:
            logging.warning("Some proposed IDs for nodes are already being used. New, unique IDs will be found.")
            reindexing_dict = dict(
                zip(clashing_node_ids, self.generate_indices_for_n_nodes(
                    len(nodes_and_attribs), avoid_keys=set(nodes_and_attribs.keys()))))
            for old_id, new_id in reindexing_dict.items():
                nodes_and_attribs_to_add[new_id] = nodes_and_attribs_to_add[old_id]
                nodes_and_attribs_to_add[new_id]['id'] = new_id
                del nodes_and_attribs_to_add[old_id]

        self.graph.add_nodes_from([(node_id, attribs) for node_id, attribs in nodes_and_attribs_to_add.items()])
        if not ignore_change_log:
            self.change_log = self.change_log.add_bunch(object_type='node',
                                                        id_bunch=list(nodes_and_attribs_to_add.keys()),
                                                        attributes_bunch=list(nodes_and_attribs_to_add.values()))
        if not silent:
            logging.info(f'Added {len(nodes_and_attribs)} nodes')
        return reindexing_dict, nodes_and_attribs_to_add

    def add_edge(self, u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None, attribs: dict = None,
                 silent: bool = False):
        """
        Adds an edge between u and v. If an edge between u and v already exists, adds an additional one. Generates
        link id. If you already have a link id, use the method to add_link.
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :param silent: whether to mute stdout logging messages
        :return:
        """
        link_id = self.generate_index_for_edge(silent=silent)
        self.add_link(link_id, u, v, multi_edge_idx, attribs, silent)
        if not silent:
            logging.info(f'Added edge from `{u}` to `{v}` with link_id `{link_id}`')
        return link_id

    def add_edges(self, edges_attributes: List[dict], silent: bool = False, ignore_change_log: bool = False):
        """
        Adds multiple edges, generates their unique link ids
        :param edges_attributes: List of edges, each item in list is a dictionary defining the edge attributes,
        contains at least 'from': node_id and 'to': node_id entries,
        :param silent: whether to mute stdout logging messages
        :param ignore_change_log: whether to ignore logging changes to the network in the changelog. False by default
        and not recommended. Only used when an alternative changelog event is being produced (e.g. simplification) to
        reduce changelog bloat.
        :return:
        """
        # check for compulsory attribs
        df_edges = pd.DataFrame(edges_attributes)
        if ('from' not in df_edges.columns) or (df_edges['from'].isnull().any()):
            raise RuntimeError('You are trying to add edges which are missing `from` (origin) nodes')
        if ('to' not in df_edges.columns) or (df_edges['to'].isnull().any()):
            raise RuntimeError('You are trying to add edges which are missing `to` (destination) nodes')

        df_edges['id'] = list(self.generate_indices_for_n_edges(len(df_edges)))
        df_edges = df_edges.set_index('id', drop=False)

        return self.add_links(df_edges.T.to_dict(), silent=silent, ignore_change_log=ignore_change_log)

    def add_link(self, link_id: Union[str, int], u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None,
                 attribs: dict = None, silent: bool = False):
        """
        Adds an link between u and v with id link_id, if available. If a link between u and v already exists,
        adds an additional one.
        :param link_id:
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :param silent: whether to mute stdout logging messages
        :return:
        """
        if link_id in self.link_id_mapping:
            new_link_id = self.generate_index_for_edge(silent=silent)
            logging.warning(f'`{link_id}` already exists. Generated a new unique_index: `{new_link_id}`')
            link_id = new_link_id

        if multi_edge_idx is None:
            multi_edge_idx = self.graph.new_edge_key(u, v)
        if self.graph.has_edge(u, v, multi_edge_idx):
            old_idx = multi_edge_idx
            multi_edge_idx = self.graph.new_edge_key(u, v)
            logging.warning(f'Changing passed multi_edge_idx: `{old_idx}` as there already exists an edge stored under'
                            f' that index. New multi_edge_idx: `{multi_edge_idx}`')
        if not isinstance(multi_edge_idx, int):
            raise RuntimeError('Multi index key needs to be an integer')

        self.link_id_mapping[link_id] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
        # TODO calculate length of link if not provided
        compulsory_attribs = {'from': u, 'to': v, 'id': link_id}
        if attribs is None:
            attribs = compulsory_attribs
        else:
            attribs = {**attribs, **compulsory_attribs}
        self.graph.add_edge(u, v, key=multi_edge_idx, **attribs)
        self.change_log.add(object_type='link', object_id=link_id, object_attributes=attribs)
        if not silent:
            logging.info(f'Added Link with index {link_id}, from node:{u} to node:{v}, under '
                         f'multi-index:{multi_edge_idx}, and data={attribs}')
        return link_id

    def add_links(self, links_and_attributes: Dict[str, dict], silent: bool = False, ignore_change_log: bool = False):
        """
        Adds multiple edges, generates their unique link ids
        :param links_and_attributes: Dictionary of link ids and corresponding edge attributes, each edge attributes
        contains at least 'from': node_id and 'to': node_id entries,
        :param silent: whether to mute stdout logging messages
        :param ignore_change_log: whether to ignore logging changes to the network in the changelog. False by default
        and not recommended. Only used when an alternative changelog event is being produced (e.g. simplification) to
        reduce changelog bloat.
        :return:
        """
        # check for compulsory attribs
        df_links = pd.DataFrame(links_and_attributes).T
        if ('from' not in df_links.columns) or (df_links['from'].isnull().any()):
            raise RuntimeError('You are trying to add links which are missing `from` (origin) nodes')
        if ('to' not in df_links.columns) or (df_links['to'].isnull().any()):
            raise RuntimeError('You are trying to add links which are missing `to` (destination) nodes')

        if ('id' not in df_links.columns) or (df_links['id'].isnull().any()):
            df_links['id'] = df_links.index

        # generate initial multi_edge_idxes for the links to be added
        if 'multi_edge_idx' not in df_links.columns:
            df_links['multi_edge_idx'] = df_links.apply(lambda x: self.graph.new_edge_key(x['from'], x['to']), axis=1)
            while df_links[['from', 'to', 'multi_edge_idx']].duplicated().any():
                df_links.loc[df_links[['from', 'to', 'multi_edge_idx']].duplicated(), 'multi_edge_idx'] += 1

        df_link_id_mapping = pd.DataFrame(self.link_id_mapping).T
        df_link_id_mapping['id'] = df_link_id_mapping.index
        if not df_link_id_mapping.empty:
            _df = pd.merge(df_links, df_link_id_mapping, how='left', on=('from', 'to', 'multi_edge_idx'),
                           suffixes=('_to_add', '_in_graph'))

            # generate new multi_edge_idx where it clashes with existing links
            def generate_unique_multi_idx(group):
                multi_idx_to_avoid = df_link_id_mapping[
                    (df_link_id_mapping['from'] == group.name[0]) & (df_link_id_mapping['to'] == group.name[1])][
                    'multi_edge_idx']
                while group['multi_edge_idx'].isin(multi_idx_to_avoid).any() \
                        | group['multi_edge_idx'].duplicated().any():
                    group.loc[(group['multi_edge_idx'].isin(multi_idx_to_avoid)) | (
                        group['multi_edge_idx'].duplicated()), 'multi_edge_idx'] += 1
                return group

            clashing_multi_idxs = _df[_df['id_in_graph'].notna()]['id_to_add']
            df_clashing_midx = _df[_df['id_to_add'].isin(clashing_multi_idxs)]
            clashing_multi_idxs = \
                _df[_df['from'].isin(df_clashing_midx['from']) & _df['to'].isin(df_clashing_midx['to'])]['id_to_add']

            df_links.loc[df_links['id'].isin(clashing_multi_idxs)] = df_links[
                df_links['id'].isin(clashing_multi_idxs)].groupby(['from', 'to']).apply(generate_unique_multi_idx)

            # generate unique indices if not
            clashing_link_ids = set(self.link_id_mapping.keys()) & set(links_and_attributes.keys())
            reindexing_dict = dict(
                zip(clashing_link_ids, self.generate_indices_for_n_edges(
                    len(clashing_link_ids),
                    avoid_keys=set(links_and_attributes.keys()))))
            clashing_mask = df_links['id'].isin(reindexing_dict.keys())
            df_links.loc[clashing_mask, 'id'] = df_links.loc[clashing_mask, 'id'].map(reindexing_dict)
            df_links = df_links.set_index('id', drop=False)
        else:
            reindexing_dict = {}

        # end with updated links_and_attributes dict
        add_to_link_id_mapping = df_links[['from', 'to', 'multi_edge_idx']].T.to_dict()
        df_links = df_links.drop('multi_edge_idx', axis=1)
        links_and_attributes = {_id: {k: v for k, v in m.items() if pd_helpers.notna(v)} for _id, m in
                                df_links.T.to_dict().items()}

        # update link_id_mapping
        self.link_id_mapping = {**self.link_id_mapping, **add_to_link_id_mapping}

        self.graph.add_edges_from(
            [(attribs['from'], attribs['to'], add_to_link_id_mapping[link]['multi_edge_idx'], attribs) for link, attribs
             in links_and_attributes.items()])
        if not ignore_change_log:
            self.change_log = self.change_log.add_bunch(
                object_type='link', id_bunch=list(links_and_attributes.keys()),
                attributes_bunch=list(links_and_attributes.values()))
        if not silent:
            logging.info(f'Added {len(links_and_attributes)} links')
        return reindexing_dict, links_and_attributes

    def reindex_node(self, node_id, new_node_id, silent: bool = False):
        # check if new id is already occupied
        if self.node_id_exists(new_node_id):
            new_node_id = self.generate_index_for_node()
        # extract link ids which will be affected byt the node relabel and change the from anf to attributes
        from_links = self.extract_links_on_edge_attributes(conditions={'from': node_id})
        self.apply_attributes_to_links({link: {'from': new_node_id} for link in from_links})
        to_links = self.extract_links_on_edge_attributes(conditions={'to': node_id})
        self.apply_attributes_to_links({link: {'to': new_node_id} for link in to_links})
        # update link_id_mapping
        for k in from_links:
            self.link_id_mapping[k]['from'] = new_node_id
        for k in to_links:
            self.link_id_mapping[k]['to'] = new_node_id

        new_attribs = deepcopy(self.node(node_id))
        new_attribs['id'] = new_node_id
        self.change_log.modify(object_type='node', old_id=node_id, new_id=new_node_id,
                               old_attributes=self.node(node_id), new_attributes=new_attribs)
        self.apply_attributes_to_node(node_id, new_attribs)
        self.graph = nx.relabel_nodes(self.graph, {node_id: new_node_id})
        self.update_node_auxiliary_files({node_id: new_node_id})
        if not silent:
            logging.info(f'Changed Node index from {node_id} to {new_node_id}')

    def reindex_link(self, link_id, new_link_id, silent: bool = False):
        # check if new id is already occupied
        if self.link_id_exists(new_link_id):
            new_link_id = self.generate_index_for_edge()
        new_attribs = deepcopy(self.link(link_id))
        new_attribs['id'] = new_link_id
        self.change_log.modify(object_type='link', old_id=link_id, new_id=new_link_id,
                               old_attributes=self.link(link_id), new_attributes=new_attribs)
        self.apply_attributes_to_link(link_id, new_attribs)
        self.link_id_mapping[new_link_id] = self.link_id_mapping[link_id]
        del self.link_id_mapping[link_id]
        self.update_link_auxiliary_files({link_id: new_link_id})
        if not silent:
            logging.info(f'Changed Link index from {link_id} to {new_link_id}')

    def subgraph_on_link_conditions(self, conditions, how=any, mixed_dtypes=True):
        """
        Gives a subgraph of network.graph based on matching conditions defined in conditions
        :param conditions as described in graph_operations.extract_links_on_edge_attributes
        :param how as described in graph_operations.extract_links_on_edge_attributes
        :param mixed_dtypes as described in graph_operations.extract_links_on_edge_attributes
        :return:
        """
        links = self.extract_links_on_edge_attributes(conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)
        edges_for_sub = [
            (self.link_id_mapping[link]['from'],
             self.link_id_mapping[link]['to'],
             self.link_id_mapping[link]['multi_edge_idx'])
            for link in links]
        return nx.MultiDiGraph(nx.edge_subgraph(self.graph, edges_for_sub))

    def modes(self):
        """
        Scans network for 'modes' attribute and returns list of all modes present in the network
        :return:
        """
        modes = set()
        for link, link_attribs in self.links():
            try:
                modes |= set(link_attribs['modes'])
            except KeyError:
                pass
        return modes

    def find_shortest_path(self, from_node, to_node, modes: Union[str, list, set] = None,
                           subgraph: nx.MultiDiGraph = None, return_nodes=False):
        """
        Finds shortest path between from and to nodes in the graph. If modes specified, finds shortest path in the
        modal subgraph (using links which have given modes stored under 'modes' key in link attributes). If computing
        a large number of routes on the same modal subgraph, it is best to find the subgraph using the `modal_subgraph`
        method and pass it under subgraph to avoid re-computing the subgraph every time.
        :param from_node: node id in the graph
        :param to_node: node id in the graph
        :param modes: string e.g. 'car' or list ['car', 'bike']
        :param subgraph: nx.MultiDiGraph, preferably the result of `modal_subgraph`
        :param return_nodes: If True, returns list of node ids defining a route (reminder: there can be more than one
        link between two nodes, by default this method will return a list of link ids that results in shortest journey)
        :return: list of link ids defining a route
        """
        if subgraph is not None:
            g = subgraph
        elif modes:
            g = self.modal_subgraph(modes)
        else:
            g = self.graph
        route = nx.shortest_path(g, source=from_node, target=to_node, weight='length')

        if return_nodes:
            return route
        else:
            return [graph_operations.find_shortest_path_link(dict(g[u][v]), modes=modes)
                    for u, v in zip(route[:-1], route[1:])]

    def apply_attributes_to_node(self, node_id, new_attributes, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param node_id: node id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :param silent: whether to mute stdout logging messages
        :return:
        """
        old_attributes = deepcopy(self.node(node_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = dict_support.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='node',
            old_id=node_id,
            new_id=node_id,
            old_attributes=self.node(node_id),
            new_attributes=new_attributes)
        nx.set_node_attributes(self.graph, {node_id: new_attributes})
        if not silent:
            logging.info(f'Changed Node attributes under index: {node_id}')

    def apply_attributes_to_nodes(self, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param new_attributes: keys are node ids and values are dictionaries of data to add/replace if present
        :return:
        """
        nodes = list(new_attributes.keys())
        old_attribs = [deepcopy(self.node(node)) for node in nodes]
        new_attribs = [{**self.node(node), **new_attributes[node]} for node in nodes]

        self.change_log = self.change_log.modify_bunch('node', nodes, old_attribs, nodes, new_attribs)

        nx.set_node_attributes(self.graph, dict(zip(nodes, new_attribs)))
        logging.info(f'Changed Node attributes for {len(nodes)} nodes')

    def apply_function_to_nodes(self, function, location: str):
        """
        Applies function to node attributes dictionary
        :param function: function of node attributes dictionary returning a value that should be stored
        under `location`
        :param location: where to save the results: string defining the key in the nodes attributes dictionary
        :return:
        """
        new_node_attribs = {}
        for node, node_attribs in self.nodes():
            try:
                new_node_attribs[node] = {location: function(node_attribs)}
            except KeyError:
                # Not all nodes/edges are required to have all the same attributes stored. Fail silently and only apply
                # to relevant nodes/edges
                pass
        self.apply_attributes_to_nodes(new_node_attribs)

    def apply_attributes_to_edge(self, u, v, new_attributes, conditions=None, how=any, silent: bool = False):
        """
        Applies attributes to edges (which optionally match certain criteria)
        :param u: from node
        :param v: to node
        :param new_attributes: attributes data to be applied
        :param conditions: graph_operations.Filter conditions
        :param how: graph_operations.Filter how
        :param silent: whether to mute stdout logging messages
        :return:
        """
        filter = graph_operations.Filter(conditions=conditions, how=how)

        for multi_idx, edge_attribs in self.edge(u, v).items():
            if filter.satisfies_conditions(edge_attribs):
                old_attributes = deepcopy(edge_attribs)

                # check if change is to nested part of node data
                if any(isinstance(v, dict) for v in new_attributes.values()):
                    new_attribs = dict_support.set_nested_value(old_attributes, new_attributes)
                else:
                    new_attribs = {**old_attributes, **new_attributes}

                edge = f'({u}, {v}, {multi_idx})'

                self.change_log.modify(
                    object_type='edge',
                    old_id=edge,
                    new_id=edge,
                    old_attributes=edge_attribs,
                    new_attributes=new_attribs)

                nx.set_edge_attributes(self.graph, {(u, v, multi_idx): new_attribs})
                if not silent:
                    logging.info(f'Changed Edge attributes under index: {edge}')

    def apply_attributes_to_edges(self, new_attributes: dict, conditions=None, how=any):
        """
        Applies new attributes for edges (optionally satisfying certain criteria)
        :param new_attributes: dictionary where keys are two tuples (u, v) where u is the from node and v is the to
        node. The value at the key are the new attributes to be applied to links on edge (u,v)
        :param conditions: graph_operations.Filter conditions
        :param how: graph_operations.Filter how
        :return:
        """
        filter = graph_operations.Filter(conditions=conditions, how=how)

        old_attribs = []
        new_attribs = []
        edge_tuples = []

        for (u, v), attribs_to_set in new_attributes.items():
            for multi_idx, edge_attribs in self.edge(u, v).items():
                if filter.satisfies_conditions(edge_attribs):
                    old_attribs.append(deepcopy(edge_attribs))
                    new_attribs.append(dict_support.set_nested_value(edge_attribs, attribs_to_set))
                    edge_tuples.append((u, v, multi_idx))

        edge_ids = list(map(str, edge_tuples))
        self.change_log = self.change_log.modify_bunch(
            object_type='edge',
            old_id_bunch=edge_ids,
            old_attributes=old_attribs,
            new_id_bunch=edge_ids,
            new_attributes=new_attribs
        )
        nx.set_edge_attributes(
            self.graph,
            dict(zip(edge_tuples, new_attribs)))

        logging.info(f'Changed Edge attributes for {len(edge_tuples)} edges')

    def apply_attributes_to_link(self, link_id, new_attributes, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param link_id: link id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :param silent: whether to mute stdout logging messages
        :return:
        """
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        old_attributes = deepcopy(self.link(link_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = dict_support.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='link',
            old_id=link_id,
            new_id=link_id,
            old_attributes=self.link(link_id),
            new_attributes=new_attributes)

        nx.set_edge_attributes(self.graph, {(u, v, multi_idx): new_attributes})
        if not silent:
            logging.info(f'Changed Link attributes under index: {link_id}')

    def apply_attributes_to_links(self, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param new_attributes: keys are link ids and values are dictionaries of data to add/replace if present
        :return:
        """
        links = list(new_attributes.keys())
        old_attribs = [deepcopy(self.link(link)) for link in links]
        new_attribs = [dict_support.set_nested_value(self.link(link), new_attributes[link]) for link in links]
        edge_tuples = [self.edge_tuple_from_link_id(link) for link in links]

        self.change_log = self.change_log.modify_bunch('link', links, old_attribs, links, new_attribs)
        nx.set_edge_attributes(
            self.graph,
            dict(zip(edge_tuples, new_attribs)))
        logging.info(f'Changed Link attributes for {len(links)} links')

    def apply_function_to_links(self, function, location: str):
        """
        Applies function to link attributes dictionary
        :param function: function of link attributes dictionary returning a value that should be stored
        under `location`
        :param location: where to save the results: string defining the key in the nodes attributes dictionary
        :return:
        """
        new_link_attribs = {}
        for link_id, link_attribs in self.links():
            try:
                new_link_attribs[link_id] = {location: function(link_attribs)}
            except KeyError:
                # Not all nodes/edges are required to have all the same attributes stored. Fail silently and only apply
                # to relevant nodes/edges
                pass
        number_of_links_not_affected = len(self.link_id_mapping) - len(new_link_attribs)
        if number_of_links_not_affected != 0:
            logging.info(f'{number_of_links_not_affected} out of {len(self.link_id_mapping)} links have not been '
                         f'affected by the function. Links affected: {list(new_link_attribs.keys())}')
        self.apply_attributes_to_links(new_link_attribs)

    def remove_node(self, node_id, silent: bool = False):
        """
        Removes the node n and all adjacent edges
        :param node_id:
        :param silent: whether to mute stdout logging messages
        :return:
        """
        self.change_log.remove(object_type='node', object_id=node_id, object_attributes=self.node(node_id))
        self.graph.remove_node(node_id)
        self.update_node_auxiliary_files({node_id: None})
        if not silent:
            logging.info(f'Removed Node under index: {node_id}')

    def remove_nodes(self, nodes, ignore_change_log=False, silent=False):
        """
        Removes several nodes and all adjacent edges
        :param nodes: list or set
        :param ignore_change_log: whether to ignore logging changes to the network in the changelog. False by default
        and not recommended. Only used when an alternative changelog event is being produced (e.g. simplification) to
        reduce changelog bloat.
        :param silent: whether to mute stdout logging messages
        :return:
        """
        if not ignore_change_log:
            self.change_log = self.change_log.remove_bunch(
                object_type='node', id_bunch=nodes, attributes_bunch=[self.node(node_id) for node_id in nodes])
        self.graph.remove_nodes_from(nodes)
        self.update_node_auxiliary_files(dict(zip(nodes, [None] * len(nodes))))
        if not silent:
            logging.info(f'Removed {len(nodes)} nodes.')

    def remove_link(self, link_id, silent: bool = False):
        """
        Removes the multi edge pertaining to link given
        :param link_id:
        :param silent: whether to mute stdout logging messages
        :return:
        """
        self.change_log.remove(object_type='link', object_id=link_id, object_attributes=self.link(link_id))
        u, v, multi_idx = self.edge_tuple_from_link_id(link_id)
        self.graph.remove_edge(u, v, multi_idx)
        del self.link_id_mapping[link_id]
        self.update_link_auxiliary_files({link_id: None})
        if not silent:
            logging.info(f'Removed link under index: {link_id}')

    def remove_links(self, links, ignore_change_log=False, silent=False):
        """
        Removes the multi edges pertaining to links given
        :param links: set or list
        :param ignore_change_log: whether to ignore logging changes to the network in the changelog. False by default
        and not recommended. Only used when an alternative changelog event is being produced (e.g. simplification) to
        reduce changelog bloat.
        :param silent: whether to mute stdout logging messages
        :return:
        """
        links = list(links)
        if not ignore_change_log:
            self.change_log = self.change_log.remove_bunch(
                object_type='link', id_bunch=links, attributes_bunch=[self.link(link_id) for link_id in links])
        self.graph.remove_edges_from([self.edge_tuple_from_link_id(link_id) for link_id in links])
        for link_id in links:
            del self.link_id_mapping[link_id]
        self.update_link_auxiliary_files(dict(zip(links, [None] * len(links))))
        if not silent:
            logging.info(f'Removed {len(links)} links')

    def is_strongly_connected(self, modes: Union[list, str, set] = None):
        if modes is None:
            g = self.graph
        else:
            g = self.modal_subgraph(modes)

        components = network_validation.find_connected_subgraphs(g)

        if len(components) == 1:
            return True
        elif len(components) == 0:
            logging.warning(
                f'The graph for modes: {modes} does not have any connected components.'
                ' This method returns True because if the graph is empty for this mode there is no reason to fail'
                ' this check.')
            return True
        else:
            return False

    def connect_components(self, modes: Union[list, str, set] = None, weight: float = 1.0):
        """
        Connect disconnected subgraphs in the Network graph. Use modes variable to consider a modal subgraph.
        For a strongly connected MATSim network use only a single (routable) mode at a time.
        :param modes: str, list or set or network modes to use for computing strongly connected subgraphs
        :param weight: weight to apply to `frespeed` and `capacity` for scaling, defaults to 1.
        :return: None, or links and their details if they were added to the Network.
        """
        if modes is None:
            g = self.graph
        else:
            g = self.modal_subgraph(modes)
            if isinstance(modes, str):
                modes = {modes}
            else:
                modes = set(modes)
        components = network_validation.find_connected_subgraphs(g)

        if len(components) == 1:
            logging.warning('This Graph has only one strongly connected component. No links will be added.')
        else:
            gdfs = self.to_geodataframe()
            gdf = gdfs['nodes'].to_crs('epsg:4326')
            components_gdfs = [gdf[gdf['id'].isin(component_nodes)] for component_nodes, len in components]

            closest_nodes = [
                spatial.nearest_neighbor(components_gdfs[i], components_gdfs[j], return_dist=True) for i, j in
                itertools.combinations(range(len(components_gdfs)), 2)
            ]
            closest_nodes_idx = [df['distance'].idxmin() for df in closest_nodes]
            closest_nodes = [(idx, df.loc[idx, 'id'], df.loc[idx, 'distance']) for idx, df in
                             zip(closest_nodes_idx, closest_nodes)]

            # TODO instead of deleting the last largest distance connection, check that it isnt too far off the others
            # some graphs may not be arranged in line or they could overlap
            closest_nodes = sorted(closest_nodes, key=lambda tup: tup[2])[:-1]

            # add links
            gdf_links = gdfs['links']
            links_to_add = []
            for u, v, dist in closest_nodes:
                links_df = gdf_links.loc[
                    (gdf_links['from'].isin({u, v}) | gdf_links['to'].isin({u, v})),
                    set(gdf_links.columns) & {'freespeed', 'capacity', 'modes'}
                ]
                links_data = links_df.mean()
                links_data = links_data * weight
                if modes is None:
                    links_data['modes'] = set().union(*links_df['modes'].tolist())
                else:
                    links_data['modes'] = modes
                links_data['permlanes'] = 1
                links_data['length'] = dist
                links_data['from'] = u
                links_data['to'] = v

                links_to_add.append(links_data.to_dict())

                links_data['from'] = v
                links_data['to'] = u

                links_to_add.append(links_data.to_dict())

            if links_to_add:
                links_to_add = dict(zip(self.generate_indices_for_n_edges(len(links_to_add)), links_to_add))
                self.add_links(links_to_add)
                return links_to_add
            else:
                logging.warning('No links are being added')

    def number_of_multi_edges(self, u, v):
        """
        number of multi edges on edge from u to v
        :param u: from node
        :param v: to node
        :return:
        """
        if self.graph.has_edge(u, v):
            return len(self.graph.edges(u, v))
        else:
            return 0

    def nodes(self):
        """
        :return:  Iterator through each node and its attrib (two-tuple)
        """
        for id, attrib in self.graph.nodes(data=True):
            yield id, attrib

    def node(self, node_id):
        """
        :return:  attribs of the 'node_id'
        """
        return self.graph.nodes[node_id]

    def edges(self):
        """
        :return: Iterator through each edge's from, to nodes and its attrib (three-tuple)
        """
        for u, v in self.graph.edges():
            yield u, v, self.edge(u, v)

    def edge(self, u, v):
        """
        :param u: from node of self.graph
        :param v: to node of self.graph
        :return:  attribs of the edge from u to  v
        """
        return dict(self.graph[u][v])

    def links(self):
        """
        :return: Iterator through each link id its attrib (two-tuple)
        """
        for link_id in self.link_id_mapping.keys():
            yield link_id, self.link(link_id)

    def edge_tuple_from_link_id(self, link):
        u, v = self.link_id_mapping[link]['from'], self.link_id_mapping[link]['to']
        multi_idx = self.link_id_mapping[link]['multi_edge_idx']
        return u, v, multi_idx

    def link(self, link_id):
        """
        :param link_id:
        :return:
        """
        u, v, multi_idx = self.edge_tuple_from_link_id(link_id)
        return dict(self.graph[u][v][multi_idx])

    def route_schedule(self, services: Union[list, set] = None, solver='cbc', allow_partial=True,
                       distance_threshold=30, step_size=10, additional_modes=None, allow_directional_split=False):
        """
        Method to find relationship between all Services in Schedule and the Network. It finds closest
        links in the Network for all stops and finds a network route (ordered list of links in the network) for all
        Route objects within each Service.

        It creates new stops: 'old_id:link:link_id' for an 'old_stop' which snapped to 'link_id'. It does not delete
        old stops.

        If there isn't a link available for snapping within threshold and under modal conditions, an artificial
        self-loop link will be created as well as any connecting links to that unsnapped stop. This can be switched off
        by setting allow_partial=False. It will raise PartialMaxStableSetProblem error instead.

        :param services: you can specify a list of services within the schedule to be snapped, defaults to all services
        :param solver: you can specify different mathematical solvers. Defaults to CBC, open source solver which can
        be found here: https://projects.coin-or.org/Cbc . Another good open source choice is GLPK:
        https://www.gnu.org/software/glpk/. You specify it as a string e.g. 'glpk', 'cbc', 'gurobi'.
        The solver needs to support MILP - mixed integer linear programming.
        :param allow_partial: Defaults to True. If there isn't a link available for snapping within threshold and,
        under modal conditions, an artificial self-loop link will be created as well as any connecting links to that
        unsnapped stop. If set to False and the problem is partial, it will raise PartialMaxStableSetProblem error
        instead.
        :param distance_threshold: in metres, upper bound for how far too look for links to snap to stops.
        Defaults to 30
        :param step_size: in metres, how much to increase search area for links (making this smaller than the distance
        threshold makes the problem less computationally heavy)
        :param additional_modes: By default the network subgraph considered for snapping and routing will be matching
        the service modes exactly e.g. just 'bus' mode. You can relax it by adding extra modes
        e.g. {'tram': {'car', 'rail'}, 'bus': 'car'} - either a set, list of just a single additional mode for a mode
        in the Schedule. This dictionary need not be exhaustive. Any other modes will be handled in the default way.
        Referencing modes present under 'modes' attribute of Network links.
        :param allow_directional_split: Defaults to False i.e. one link will be related to a stop in each Service.
        For some modes, e.g. rail, it may be beneficial to split this problem based on direction of travel. This usually
        results in stops snapping to multiple links. Routes' stops and their network routes are updated based on
        direction too. You may like to investigate directional split for different services using a Service object
        method: `split_graph`.
        :return: set of unsnapped services, empty if all snapped, updates Network object and the Schedule object within.
        """
        if self.schedule:
            logging.info('Building Spatial Tree')
            spatial_tree = spatial.SpatialTree(self)
            if additional_modes is None:
                additional_modes = {}
            else:
                for k, v in additional_modes.items():
                    additional_modes[k] = persistence.setify(v)

            changeset = None
            route_data = self.schedule.route_attribute_data(keys=['ordered_stops'])
            service_modes = self.schedule.route_attribute_data(keys=['mode'], index_name='route_id').reset_index()
            service_modes['service_id'] = service_modes['route_id'].map(
                self.schedule.graph().graph['route_to_service_map'])
            if services is not None:
                service_modes = service_modes.loc[service_modes['service_id'].isin(services), :]
            service_modes = service_modes.groupby('service_id')['mode'].apply(set).apply(list).reset_index()
            service_modes['mode'] = service_modes['mode'].apply(lambda x: tuple(sorted(x)))
            service_modes = service_modes.groupby('mode')['service_id'].apply(set).T.to_dict()

            unsnapped_services = set()
            for modes, service_ids in service_modes.items():
                modes = set(modes)
                buffed_modes = modes.copy()
                for m in modes & set(additional_modes.keys()):
                    buffed_modes |= additional_modes[m]

                try:
                    logging.info(f'Extracting Modal SubTree for modes: {modes}')
                    sub_tree = spatial_tree.modal_subtree(buffed_modes)
                except exceptions.EmptySpatialTree:
                    sub_tree = None
                    logging.warning(f'Services {service_ids} cannot be snapped to the Network with modes = {modes}. '
                                    'The modal graph is empty for those modes. Consider teleporting.')
                    unsnapped_services |= service_ids

                if sub_tree is not None:
                    for service_id in service_ids:
                        service = self.schedule[service_id]
                        logging.info(f'Routing Service {service.id} with modes = {modes}')
                        if allow_directional_split:
                            logging.info('Splitting Service graph')
                            routes, graph_groups = service.split_graph()
                            logging.info(f'Split Problem into {len(routes)}')
                        else:
                            routes = [set(service.route_ids())]
                            graph_groups = [service.reference_edges()]
                        service_g = service.graph()

                        for route_group, graph_group in zip(routes, graph_groups):
                            try:
                                mss = modify_schedule.route_pt_graph(
                                    pt_graph=nx.edge_subgraph(service_g, graph_group),
                                    network_spatial_tree=sub_tree,
                                    modes=modes,
                                    solver=solver,
                                    allow_partial=allow_partial,
                                    distance_threshold=distance_threshold,
                                    step_size=step_size)
                                if changeset is None:
                                    changeset = mss.to_changeset(route_data.loc[route_group, :])
                                else:
                                    changeset += mss.to_changeset(route_data.loc[route_group, :])
                            except Exception as e:  # noqa: F841
                                logging.error(f'\nRouting Service: `{service_id}` resulted in the following Exception:'
                                              f'\n{traceback.format_exc()}')
                                unsnapped_services.add(service_id)
            if changeset is not None:
                self._apply_max_stable_changes(changeset)
            return unsnapped_services
        else:
            logging.warning('Schedule object not found')

    def route_service(self, service_id, spatial_tree=None, solver='cbc', allow_partial=True, distance_threshold=30,
                      step_size=10, additional_modes=None, allow_directional_split=False):
        """
        Method to find relationship between the Service with ID 'service_id' in the Schedule and the Network.
        It finds closest links in the Network for all stops and finds a network route (ordered list of links in the
        network) for all Route objects within this Service.

        It creates new stops: 'old_id:link:link_id' for an 'old_stop' which snapped to 'link_id'. It does not delete
        old stops.

        If there isn't a link available for snapping within threshold and under modal conditions, an artificial
        self-loop link will be created as well as any connecting links to that unsnapped stop. This can be switched off
        by setting allow_partial=False. It will raise PartialMaxStableSetProblem error instead.

        :param service_id: ID of the Service object to snap and route
        :param spatial_tree: optional, if snapping more than one Service, it may be beneficcial to build the spatial
        tree which is used for snapping separately and pass it here. This is done simply by importing genet and passing
        the network object in the following way: genet.utils.spatial.SpatialTree(network_object)
        :param solver: you can specify different mathematical solvers. Defaults to CBC, open source solver which can
        be found here: https://projects.coin-or.org/Cbc . Another good open source choice is GLPK:
        https://www.gnu.org/software/glpk/. You specify it as a string e.g. 'glpk', 'cbc', 'gurobi'.
        The solver needs to support MILP - mixed integer linear programming.
        :param allow_partial: Defaults to True. If there isn't a link available for snapping within threshold and
        under modal conditions, an artificial self-loop link will be created as well as any connecting links to that
        unsnapped stop. If set to False and the problem is partial, it will raise PartialMaxStableSetProblem error
        instead.
        :param distance_threshold: in metres, upper bound for how far too look for links to snap to stops.
        Defaults to 30
        :param step_size: in metres, how much to increase search area for links (making this smaller than the distance
        threshold makes the problem less computationally heavy)
        :param additional_modes: string, set or list. By default the network subgraph considered for snapping and
        routing will be matching the service modes exactly e.g. just 'bus' mode. You can relax it by adding extra modes
        e.g. 'car' or {'car', 'rail'}. Referencing modes present under 'modes' attribute of Network links.
        :param allow_directional_split: Defaults to False i.e. one link will be related to a stop in each Service.
        For some modes, e.g. rail, it may be beneficial to split this problem based on direction of travel. This usually
        results in stops snapping to multiple links. Routes' stops and their network routes are updated based on
        direction too. You may like to investigate directional split for different services using a Service object
        method: `split_graph`.
        :return: None if successful, updates Network object and the Schedule object within. Returns service ID if
        unsuccesful.
        """
        if spatial_tree is None:
            spatial_tree = spatial.SpatialTree(self)
        additional_modes = persistence.setify(additional_modes)

        service = self.schedule[service_id]
        if allow_directional_split:
            routes, graph_groups = service.split_graph()
            logging.info(f'Splitting Problem into {len(routes)}')
        else:
            routes = [set(service.route_ids())]
            graph_groups = [service.reference_edges()]
        service_g = service.graph()
        changeset = None
        route_data = self.schedule.route_attribute_data(keys=['ordered_stops'])

        modes = service.modes()
        logging.info(f'Routing Service {service.id} with modes = {modes}')
        try:
            sub_tree = spatial_tree.modal_subtree(modes | additional_modes)
            for route_group, graph_group in zip(routes, graph_groups):
                mss = modify_schedule.route_pt_graph(
                    pt_graph=nx.edge_subgraph(service_g, graph_group),
                    network_spatial_tree=sub_tree,
                    modes=modes,
                    solver=solver,
                    allow_partial=allow_partial,
                    distance_threshold=distance_threshold,
                    step_size=step_size)
                if changeset is None:
                    changeset = mss.to_changeset(route_data.loc[route_group, :])
                else:
                    changeset += mss.to_changeset(route_data.loc[route_group, :])
            self._apply_max_stable_changes(changeset)
        except exceptions.EmptySpatialTree:
            logging.warning(f'Service {service.id} cannot be snapped to the Network with modes = {modes}. The '
                            f'modal graph is empty for those modes. Consider teleporting.')
            return service.id

    def teleport_service(self, service_ids: Union[str, list, set]):
        """
        Teleports service(s) of ID(s) given in `service_ids`
        :param service_ids: a Service ID or collection of them
        :return: None, updates Network and Schedule objects
        """

        def route_path(ordered_stops):
            path = []
            for u, v in zip(ordered_stops[:-1], ordered_stops[1:]):
                from_linkrefid = stop_linkrefids[u]['linkRefId']
                to_linkrefid = stop_linkrefids[v]['linkRefId']
                f_node = reference_links[from_linkrefid]['to']
                t_node = reference_links[to_linkrefid]['from']
                f_node_data = nodes[f_node]
                t_node_data = nodes[t_node]

                connecting_link = f'artificial_link===from:{f_node}===to:{t_node}'
                reference_links[connecting_link] = {
                    'id': connecting_link,
                    'from': f_node,
                    'to': t_node,
                    'modes': {routes_to_mode_map[route_id]['mode'] for route_id in g.nodes[u]['routes']} | {
                        routes_to_mode_map[route_id]['mode'] for route_id in g.nodes[v]['routes']},
                    'length': spatial.distance_between_s2cellids(f_node_data['s2_id'], t_node_data['s2_id']),
                    'freespeed': 44.44,
                    'capacity': 9999.0,
                    'permlanes': 1
                }

                pairwise_path = [from_linkrefid, connecting_link, to_linkrefid]
                if path:
                    if path[-1] == pairwise_path[0]:
                        path += pairwise_path[1:]
                    else:
                        path += pairwise_path
                else:
                    path.extend(pairwise_path)
            return path

        if isinstance(service_ids, str):
            service_ids = {service_ids}
        sub_graph_edges = set()
        for service_id in service_ids:
            sub_graph_edges |= self.schedule.service_reference_edges(service_id)
        g = nx.DiGraph(nx.edge_subgraph(self.schedule.graph(), sub_graph_edges))

        routes_to_mode_map = self.schedule.route_attribute_data(keys=['mode']).T.to_dict()
        nodes = {}
        reference_links = {}
        stop_linkrefids = {}
        for stop, data in g.nodes(data=True):
            if ('linkRefId' not in data) or (not self.has_link(data['linkRefId'])):
                nodes[stop] = {k: v for k, v in data.items() if k not in {'services', 'routes', 'epsg'}}

                link_id = f'artificial_link===from:{stop}===to:{stop}'
                reference_links[link_id] = {
                    'id': link_id,
                    'from': stop,
                    'to': stop,
                    'modes': {routes_to_mode_map[route_id]['mode'] for route_id in data['routes']},
                    'length': 1,
                    'freespeed': 44.44,
                    'capacity': 9999.0,
                    'permlanes': 1
                }

                stop_linkrefids[stop] = {'linkRefId': link_id}
            else:
                link_id = data['linkRefId']
                link_data = self.link(link_id)
                stop_linkrefids[stop] = {'linkRefId': link_id}
                reference_links[link_id] = link_data
                nodes[link_data['from']] = self.node(link_data['from'])
                nodes[link_data['to']] = self.node(link_data['to'])

        routes = self.schedule.route_attribute_data(keys='ordered_stops')
        _rs = [self.schedule.service_to_route_map()[service_id] for service_id in service_ids]
        routes = routes[routes.index.to_series().isin({item for sublist in _rs for item in sublist})]
        routes['route'] = routes['ordered_stops'].apply(lambda x: route_path(x))
        routes = routes.drop('ordered_stops', axis=1).T.to_dict()

        self.add_nodes({node: nodes[node] for node in set(nodes) - set(self.graph.nodes)})
        self.add_links({link: reference_links[link] for link in set(reference_links) - set(self.link_id_mapping)})
        self.schedule.apply_attributes_to_stops(stop_linkrefids)
        self.schedule.apply_attributes_to_routes(routes)

    def _apply_max_stable_changes(self, max_stable_set_changeset):
        self.schedule._graph.add_nodes_from(max_stable_set_changeset.new_stops.items())
        self.schedule._graph.add_edges_from(max_stable_set_changeset.new_pt_edges)

        self.schedule.apply_attributes_to_routes(max_stable_set_changeset.df_route_data.T.to_dict())

        if max_stable_set_changeset.new_nodes:
            self.add_nodes(max_stable_set_changeset.new_nodes)
        if max_stable_set_changeset.new_links:
            # generate some basic data
            for link, data in max_stable_set_changeset.new_links.items():
                _from = self.node(data['from'])
                _to = self.node(data['to'])
                data['length'] = spatial.distance_between_s2cellids(_from['s2_id'], _to['s2_id'])
                if data['length'] == 0:
                    data['length'] = 1
                data['freespeed'] = 44.44
                data['capacity'] = 9999.0
                data['permlanes'] = 1
            self.add_links(max_stable_set_changeset.new_links)
        self.apply_attributes_to_links(max_stable_set_changeset.additional_links_modes)

    def reroute(self, _id, additional_modes=None):
        """
        Finds network route for a Service of ID=_id or Route of ID=_id, if the Stops for that Route or Service are
        already snapped to the network (have linkRefId attributes). Checks that those linkRefIds are still in the
        network, logs a warning if not.
        :param _id: ID of Route or Service object. If Service, updated route attribute of all Routes contained within
        the Service object
        :param additional_modes: string, set or list. By default the network subgraph considered for snapping and
        routing will be matching the service modes exactly e.g. just 'bus' mode. You can relax it by adding extra modes
        e.g. 'car' or {'car', 'rail'}. Referencing modes present under 'modes' attribute of Network links.
        :return: None, updates the `route` attribute of `Route` object(s)
        """
        try:
            self._reroute_service(_id, additional_modes)
        except exceptions.ServiceIndexError:
            try:
                self._reroute_route(_id, additional_modes)
            except exceptions.RouteIndexError:
                logging.warning(f'Object of ID: `{_id}` was not found as a Route or Service in the Schedule')
                raise IndexError(f'Unrecognised Index `{_id}` in this context.')

    def _reroute_service(self, _id, additional_modes=None):
        service = self.schedule[_id]
        logging.info(f'Rerouting Service `{_id}`')
        for route_id in service.route_ids():
            self._reroute_route(route_id, additional_modes)

    def _reroute_route(self, _id, additional_modes=None):
        route = self.schedule.route(_id)
        logging.info(f'Checking `linkRefId`s of the Route: `{_id}` are present in the graph')
        linkrefids = [stop.linkRefId for stop in route.stops()]
        # sometimes consecutive stops share links (if the links are long or stops close together)
        # we dont need to route between them so we simplify the chain of linkrefids
        linkrefids = [linkrefids[0]] + [linkrefids[i] for i in range(1, len(linkrefids)) if
                                        linkrefids[i - 1] != linkrefids[i]]

        unrecognised_linkrefids = set(linkrefids) - set(self.link_id_mapping.keys())
        if not unrecognised_linkrefids:
            logging.info(f'Rerouting Route `{_id}`')
            modes = {route.mode} | persistence.setify(additional_modes)
            subgraph = self.modal_subgraph(modes)
            network_route = [linkrefids[0]]
            for from_stop_link_id, to_stop_link_id in zip(linkrefids[:-1], linkrefids[1:]):
                network_route += self.find_shortest_path(
                    self.link(from_stop_link_id)['to'],
                    self.link(to_stop_link_id)['from'],
                    subgraph=subgraph)
                network_route.append(to_stop_link_id)
            self.schedule.apply_attributes_to_routes({_id: {'route': network_route}})
            links_for_mode_add = {link_id for link_id in set(network_route) if
                                  not {route.mode}.issubset(persistence.setify(self.link(link_id)['modes']))}
            if links_for_mode_add:
                self.apply_attributes_to_links(
                    {link_id: {'modes': persistence.setify(self.link(link_id)['modes']) | {route.mode}} for link_id in
                     links_for_mode_add})
        else:
            logging.warning(f'Could not reroute Route of ID: `{_id}` due to some stops having unrecognised '
                            f'`linkRefId`s. Unrecognised link IDs: {unrecognised_linkrefids}. You will need to '
                            'use a different method to snap and route the Service object containing this Route.')

    def services(self):
        """
        Iterator returning Service objects
        :return:
        """
        for service in self.schedule.services():
            yield service

    def schedule_routes(self):
        """
        Iterator returning Route objects within the Schedule
        :return:
        """
        for route in self.schedule.routes():
            yield route

    def schedule_routes_nodes(self):
        routes = []
        for _route in self.schedule_routes():
            if _route.route:
                route_nodes = graph_operations.convert_list_of_link_ids_to_network_nodes(self, _route.route)
                if len(route_nodes) != 1:
                    logging.warning(f'The route: {_route.id} is disconnected. Consists of {len(route_nodes)} chunks.')
                    routes.extend(route_nodes)
                else:
                    routes.append(route_nodes[0])
        return routes

    def schedule_routes_links(self):
        routes = []
        for service_id, _route in self.schedule_routes():
            if _route.route:
                routes.append(_route.route)
        return routes

    def schedule_network_routes_geodataframe(self):
        if not self.schedule:
            logging.warning('Schedule in this Network is empty')
            return gpd.GeoDataFrame().set_crs(self.epsg)

        def combine_geometry(group):
            group = group.sort_values(by='route_sequence')
            geom = spatial.merge_linestrings(list(group['geometry']))
            group = group.iloc[0, :][{'route_id', 'route_short_name', 'mode', 'service_id'}]
            group['geometry'] = geom
            return group

        gdf_links = self.to_geodataframe()['links']
        routes = self.schedule.route_attribute_data(keys=['id', 'route_short_name', 'mode', 'route'])
        routes = routes.rename(columns={'id': 'route_id'})
        routes['route_sequence'] = routes['route'].apply(lambda x: list(range(len(x))))

        # expand on network route link sequence
        routes = pd.DataFrame({
            col: np.repeat(routes[col].values, routes['route'].str.len())
            for col in {'route_id', 'route_short_name', 'mode'}}
        ).assign(route=np.concatenate(routes['route'].values),
                 route_sequence=np.concatenate(routes['route_sequence'].values))
        routes['service_id'] = routes['route_id'].apply(
            lambda x: self.schedule.graph().graph['route_to_service_map'][x])

        # get geometry for link IDs
        routes = pd.merge(routes, gdf_links[['id', 'geometry']], left_on='route', right_on='id')
        routes = routes.groupby('route_id').apply(combine_geometry).reset_index(drop=True)
        return gpd.GeoDataFrame(routes).set_crs(self.epsg)

    def node_id_exists(self, node_id):
        if node_id in [i for i, attribs in self.nodes()]:
            logging.warning(f'{node_id} already exists.')
            return True
        return False

    def has_node(self, node_id):
        return self.graph.has_node(node_id)

    def has_nodes(self, node_id: list):
        return all([self.has_node(node_id) for node_id in node_id])

    def has_isolated_nodes(self) -> bool:
        return bool(self.isolated_nodes())

    def isolated_nodes(self) -> list:
        return list(nx.isolates(self.graph))

    def remove_isolated_nodes(self) -> None:
        if self.has_isolated_nodes():
            nodes_to_remove = self.isolated_nodes()
            logging.info(f'Found {len(nodes_to_remove)} isolated nodes to remove')
            self.remove_nodes(nodes_to_remove)
        else:
            logging.warning('This Network has no isolated nodes to remove')

    def has_edge(self, u, v):
        return self.graph.has_edge(u, v)

    def has_link(self, link_id: str):
        if link_id in self.link_id_mapping:
            link_edge = self.link_id_mapping[link_id]
            u, v, multi_idx = link_edge['from'], link_edge['to'], link_edge['multi_edge_idx']
            if self.graph.has_edge(u, v, multi_idx):
                return True
            else:
                logging.info(f'Link with id {link_id} is declared in the network with from_node: {u}, to_node: {v} '
                             f'and multi_index: {multi_idx} but this edge is not in the graph.')
                return False
        else:
            logging.info(f'Link with id {link_id} is not in the network.')
            return False

    def has_links(self, link_ids: list, conditions: Union[list, dict] = None, mixed_dtypes=True):
        """
        Whether the Network contains the links given in the link_ids list. If conditions is specified, checks whether
        the Network contains the links specified and those links match the attributes in the conditions dict.
        :param link_ids: list of link ids e.g. ['1', '102']
        :param conditions: confer graph_operations.Filter conditions
        :return:
        """
        has_all_links = all([self.has_link(link_id) for link_id in link_ids])
        if not conditions:
            return has_all_links
        elif has_all_links:
            filter = graph_operations.Filter(conditions, how=any, mixed_dtypes=mixed_dtypes)
            links_satisfy = [link_id for link_id in link_ids if filter.satisfies_conditions(self.link(link_id))]
            return set(links_satisfy) == set(link_ids)
        else:
            return False

    def has_valid_link_chain(self, link_ids: List[str]):
        for prev_link_id, next_link_id in zip(link_ids[:-1], link_ids[1:]):
            prev_link_id_to_node = self.link_id_mapping[prev_link_id]['to']
            next_link_id_from_node = self.link_id_mapping[next_link_id]['from']
            if prev_link_id_to_node != next_link_id_from_node:
                logging.info(f'Links {prev_link_id} and {next_link_id} are not connected')
                return False
        if not link_ids:
            logging.info('Links chain is empty')
            return False
        return True

    def route_distance(self, link_ids):
        if self.has_valid_link_chain(link_ids):
            distance = 0
            for link_id in link_ids:
                link_attribs = self.link(link_id)
                if 'length' in link_attribs:
                    distance += link_attribs['length']
                else:
                    length = spatial.distance_between_s2cellids(link_attribs['from'], link_attribs['to'])
                    link_attribs['length'] = length
                    distance += length
            return distance
        else:
            logging.warning(f'This route is invalid: {link_ids}')
            return 0

    def generate_index_for_node(self, avoid_keys: Union[list, set] = None, silent: bool = False):
        existing_keys = set([i for i, attribs in self.nodes()])
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id = max([int(i) for i in existing_keys]) + 1
        except ValueError:
            id = len(existing_keys) + 1
        if (id in existing_keys) or (str(id) in existing_keys):
            id = uuid.uuid4()
        if not silent:
            logging.info(f'Generated node id {id}.')
        return str(id)

    def generate_indices_for_n_nodes(self, n, avoid_keys: Union[list, set] = None):
        existing_keys = set([i for i, attribs in self.nodes()])
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id_set = set([str(max([int(i) for i in existing_keys]) + j) for j in range(1, n + 1)])
        except ValueError:
            id_set = set([str(len(existing_keys) + j) for j in range(1, n + 1)])
        if id_set & existing_keys:
            id_set = id_set - existing_keys
            id_set = id_set | set([str(uuid.uuid4()) for i in range(n - len(id_set))])
        logging.info(f'Generated {len(id_set)} node ids.')
        return id_set

    def link_id_exists(self, link_id):
        if link_id in self.link_id_mapping:
            logging.warning(f'{link_id} already exists.')
            return True
        return False

    def generate_index_for_edge(self, avoid_keys: Union[list, set] = None, silent: bool = False):
        _id = list(self.generate_indices_for_n_edges(n=1, avoid_keys=avoid_keys))[0]
        if not silent:
            logging.info(f'Generated link id {_id}.')
        return str(_id)

    def generate_indices_for_n_edges(self, n, avoid_keys: Union[list, set] = None):
        existing_keys = set(self.link_id_mapping.keys())
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        id_set = set(map(str, range(n))) - existing_keys
        _max = 0
        loop_no = 0

        while len(id_set) != n:
            if loop_no > 0:
                if not _max:
                    _max = n
                else:
                    _max += n
            missing_ns = n - len(id_set)
            id_set |= set(map(str, range(_max + 1, _max + missing_ns + 1))) - existing_keys
            loop_no += 1

        logging.info(f'Generated {len(id_set)} link ids.')
        return id_set

    def index_graph_edges(self):
        logging.warning('This method clears the existing link_id indexing')
        self.link_id_mapping = {}
        i = 0
        for u, v, multi_edge_idx in self.graph.edges:
            self.link_id_mapping[str(i)] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
            i += 1

    def has_schedule_with_valid_network_routes(self):
        routes = [route for route in self.schedule_routes()]
        if all([route.has_network_route() for route in routes]):
            return all([self.is_valid_network_route(route) for route in routes])
        return False

    def calculate_route_to_crow_fly_ratio(self, route: schedule_elements.Route):
        route_dist = self.route_distance(route.route)
        crowfly_dist = route.crowfly_distance()
        if crowfly_dist:
            return route_dist / crowfly_dist
        else:
            return 'Division by zero'

    def is_valid_network_route(self, route: schedule_elements.Route):
        if self.has_links(route.route):
            valid_link_chain = self.has_valid_link_chain(route.route)
            links_have_correct_modes = self.has_links(route.route, {'modes': route.mode}, mixed_dtypes=True)
            if not links_have_correct_modes:
                logging.info(f'Some link ids in Route: {route.id} don\'t accept the route\'s mode: {route.mode}')
            return valid_link_chain and links_have_correct_modes
        logging.info(f'Not all link ids in Route: {route.id} are in the graph.')
        return False

    def invalid_network_routes(self):
        return [route.id for route in self.schedule.routes() if
                not route.has_network_route() or not self.is_valid_network_route(route)]

    def generate_validation_report(self, modes_for_strong_connectivity=None, link_metre_length_threshold=1000):
        """
        Generates a dictionary with keys: 'graph', 'schedule' and 'routing' describing validity of the Network's
        underlying graph, the schedule services and then the intersection of the two which is the routing of schedule
        services onto the graph.
        :param modes_for_strong_connectivity: list of modes in the network that need to be checked for strong
            connectivity. Defaults to 'car', 'walk' and 'bike'
        :param link_metre_length_threshold: in meters defaults to 1000, i.e. 1km
        :return:
        """
        logging.info('Checking validity of the Network')
        logging.info('Checking validity of the Network graph')
        report = {}

        # describe network connectivity
        if modes_for_strong_connectivity is None:
            modes_for_strong_connectivity = ['car', 'walk', 'bike']
            logging.info(f'Defaulting to checking graph connectivity for modes: {modes_for_strong_connectivity}. '
                         'You can change this by passing a `modes_for_strong_connectivity` param')
        graph_connectivity = {}
        for mode in modes_for_strong_connectivity:
            graph_connectivity[mode] = self.check_connectivity_for_mode(mode)
        report['graph'] = {'graph_connectivity': graph_connectivity}

        isolated_nodes = self.isolated_nodes()
        report['graph']['isolated_nodes'] = {
            'number_of_nodes': len(isolated_nodes),
            'nodes': isolated_nodes
        }
        if self.has_isolated_nodes():
            logging.warning('This Network has isolated nodes! Consider cleaning it up with `remove_isolated_nodes`')

        # attribute checks
        conditions_toolbox = network_validation.ConditionsToolbox()
        report['graph']['link_attributes'] = {
            f'{k}_attributes': {} for k in conditions_toolbox.condition_names()}

        # checks on length attribute specifically
        def links_over_threshold_length(value):
            return value >= link_metre_length_threshold

        report['graph']['link_attributes']['links_over_1000_length'] = self.report_on_link_attribute_condition(
            'length', links_over_threshold_length)

        # more general attribute value checks
        non_testable = ['id', 'from', 'to', 's2_to', 's2_from', 'geometry']
        link_attributes = [graph_operations.parse_leaf(leaf) for leaf in
                           graph_operations.get_attribute_schema(self.links()).leaves]
        link_attributes = [attrib for attrib in link_attributes if attrib not in non_testable]
        for attrib in link_attributes:
            logging.info(f'Checking link values for `{attrib}`')
            for condition_name in conditions_toolbox.condition_names():
                links_satifying_condition = self.report_on_link_attribute_condition(
                    attrib, conditions_toolbox.get_condition_evaluator(condition_name))
                if links_satifying_condition['number_of']:
                    logging.warning(
                        f'{links_satifying_condition["number_of"]} of links have '
                        f'{condition_name} values for `{attrib}`')
                    if isinstance(attrib, dict):
                        attrib = dict_support.dict_to_string(attrib)
                    report['graph']['link_attributes'][f'{condition_name}_attributes'][
                        attrib] = links_satifying_condition

        if self.schedule:
            report['schedule'] = self.schedule.generate_validation_report()

            route_to_crow_fly_ratio = {}
            for service_id, route_ids in self.schedule.service_to_route_map().items():
                route_to_crow_fly_ratio[service_id] = {}
                for route_id in route_ids:
                    route_to_crow_fly_ratio[service_id][route_id] = self.calculate_route_to_crow_fly_ratio(
                        self.schedule.route(route_id))

            report['routing'] = {
                'services_have_routes_in_the_graph': self.has_schedule_with_valid_network_routes(),
                'service_routes_with_invalid_network_route': self.invalid_network_routes(),
                'route_to_crow_fly_ratio': route_to_crow_fly_ratio
            }
        return report

    def report_on_link_attribute_condition(self, attribute, condition):
        """
        :param attribute: one of the link attributes, e.g. 'length'
        :param condition: callable, condition for link[attribute] to satisfy
        :return:
        """
        if isinstance(attribute, dict):
            conditions = dict_support.nest_at_leaf(deepcopy(attribute), condition)
        else:
            conditions = {attribute: condition}

        links_satifying_condition = self.extract_links_on_edge_attributes(conditions=conditions)
        return {
            'number_of': len(links_satifying_condition),
            'percentage': len(links_satifying_condition) / self.graph.number_of_edges(),
            'link_ids': links_satifying_condition
        }

    def check_connectivity_for_mode(self, mode):
        logging.info(f'Checking network connectivity for mode: {mode}')
        G_mode = self.modal_subgraph(mode)
        con_desc = network_validation.describe_graph_connectivity(G_mode)
        no_of_components = con_desc["number_of_connected_subgraphs"]
        logging.info(f'The graph for mode: {mode} has: '
                     f'{no_of_components} connected components, '
                     f'{len(con_desc["problem_nodes"]["dead_ends"])} sinks/dead_ends and '
                     f'{len(con_desc["problem_nodes"]["unreachable_node"])} sources/unreachable nodes.')
        if no_of_components > 1:
            logging.warning(f'The graph has more than one connected component for mode {mode}! '
                            'If this is not expected, consider using the `connect_components` method to connect the '
                            'components, or `retain_n_connected_subgraphs` with `n=1` to extract the largest component')
        return con_desc

    def generate_standard_outputs(self, output_dir, gtfs_day='19700101', include_shp_files=False):
        """
        Generates geojsons that can be used for generating standard kepler visualisations.
        These can also be used for validating network for example inspecting link capacity, freespeed, number of lanes,
        the shape of modal subgraphs.
        :param output_dir: path to folder where to save resulting geojsons
        :param gtfs_day: day in format YYYYMMDD for the network's schedule for consistency in visualisations,
        defaults to 1970/01/01 otherwise
        :return: None
        """
        geojson.generate_standard_outputs(self, output_dir, gtfs_day, include_shp_files)
        logging.info('Finished generating standard outputs. Zipping folder.')
        persistence.zip_folder(output_dir)

    def read_auxiliary_link_file(self, file_path):
        aux_file = auxiliary_files.AuxiliaryFile(file_path)
        aux_file.attach({link_id for link_id, dat in self.links()})
        if aux_file.is_attached():
            self.auxiliary_files['link'][aux_file.filename] = aux_file
        else:
            logging.warning(f'Auxiliary file {file_path} failed to attach to {self.__name__} links')

    def read_auxiliary_node_file(self, file_path):
        aux_file = auxiliary_files.AuxiliaryFile(file_path)
        aux_file.attach({node_id for node_id, dat in self.nodes()})
        if aux_file.is_attached():
            self.auxiliary_files['node'][aux_file.filename] = aux_file
        else:
            logging.warning(f'Auxiliary file {file_path} failed to attach to {self.__name__} nodes')

    def update_link_auxiliary_files(self, id_map: dict):
        """
        :param id_map: dict map between old link ID and new link ID
        :return:
        """
        for name, aux_file in self.auxiliary_files['link'].items():
            aux_file.apply_map(id_map)

    def update_node_auxiliary_files(self, id_map: dict):
        """
        :param id_map: dict map between old node ID and new node ID
        :return:
        """
        for name, aux_file in self.auxiliary_files['node'].items():
            aux_file.apply_map(id_map)

    def write_auxiliary_files(self, output_dir):
        for id_type in {'node', 'link'}:
            for name, aux_file in self.auxiliary_files[id_type].items():
                aux_file.write_to_file(output_dir)

    def write_extras(self, output_dir):
        self.change_log.export(os.path.join(output_dir, 'network_change_log.csv'))
        self.write_auxiliary_files(os.path.join(output_dir, 'auxiliary_files'))

    def write_to_matsim(self, output_dir):
        """
        Writes Network and Schedule (if applicable) to MATSim xml format
        :param output_dir: output directory
        :return:
        """
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_matsim_network(output_dir, self)
        if self.schedule:
            self.schedule.write_to_matsim(output_dir)
        self.write_extras(output_dir)

    def to_json(self):
        _network = self.to_encoded_geometry_dataframe()
        return {'nodes': dict_support.dataframe_to_dict(_network['nodes'].T),
                'links': dict_support.dataframe_to_dict(_network['links'].T)}

    def write_to_json(self, output_dir):
        """
        Writes Network and Schedule (if applicable) to a single JSON file with nodes and links
        :param output_dir: output directory
        :return:
        """
        persistence.ensure_dir(output_dir)
        logging.info(f'Saving Network to JSON in {output_dir}')
        with open(os.path.join(output_dir, 'network.json'), 'w') as outfile:
            json.dump(sanitiser.sanitise_dictionary(self.to_json()), outfile)
        if self.schedule:
            self.schedule.write_to_json(output_dir)
        self.write_extras(output_dir)

    def write_to_geojson(self, output_dir, epsg: str = None):
        """
        Writes Network graph and Schedule (if applicable) to nodes and links geojson files.
        :param output_dir: output directory
        :param epsg: projection if the geometry is to be reprojected, defaults to own projection
        :return:
        """
        persistence.ensure_dir(output_dir)
        _network = self.to_geodataframe()
        if epsg is not None:
            _network['nodes'] = _network['nodes'].to_crs(epsg)
            _network['links'] = _network['links'].to_crs(epsg)
        logging.info(f'Saving Network to GeoJSON in {output_dir}')
        geojson.save_geodataframe(_network['nodes'], 'network_nodes', output_dir)
        geojson.save_geodataframe(_network['links'], 'network_links', output_dir)
        geojson.save_geodataframe(_network['nodes']['geometry'], 'network_nodes_geometry_only', output_dir)
        geojson.save_geodataframe(_network['links']['geometry'], 'network_links_geometry_only', output_dir)
        if self.schedule:
            self.schedule.write_to_geojson(output_dir, epsg)
        self.write_extras(output_dir)

    def to_geodataframe(self):
        """
        Generates GeoDataFrames of the Network graph in Network's crs
        :return: dict with keys 'nodes' and 'links', values are the GeoDataFrames corresponding to nodes and links
        """
        return geojson.generate_geodataframes(self.graph)

    def to_encoded_geometry_dataframe(self):
        _network = self.to_geodataframe()
        _network['nodes'] = pd.DataFrame(_network['nodes'])
        _network['links'] = pd.DataFrame(_network['links'])
        _network['nodes']['geometry'] = _network['nodes']['geometry'].apply(
            lambda row: [row.x, row.y])
        _network['links']['geometry'] = _network['links']['geometry'].apply(
            lambda x: spatial.encode_shapely_linestring_to_polyline(x))
        return _network

    def write_to_csv(self, output_dir, gtfs_day='19700101'):
        """
        Writes nodes and links tables for the Network and if there is a Schedule, exports it to a GTFS-like format.
        :param output_dir: output directory
        :param gtfs_day: defaults to 19700101, day which is represented in the Schedule
        :return:
        """
        network_csv_folder = os.path.join(output_dir, 'network')
        schedule_csv_folder = os.path.join(output_dir, 'schedule')
        persistence.ensure_dir(network_csv_folder)
        csv_network = self.to_encoded_geometry_dataframe()
        logging.info(f'Saving Network to CSV in {network_csv_folder}')
        csv_network['nodes'].to_csv(os.path.join(network_csv_folder, 'nodes.csv'))
        csv_network['links'].to_csv(os.path.join(network_csv_folder, 'links.csv'))
        if self.schedule:
            persistence.ensure_dir(schedule_csv_folder)
            self.schedule.write_to_csv(schedule_csv_folder, gtfs_day)
        self.write_extras(network_csv_folder)

    def get_node_elevation_dictionary(self, elevation_tif_file_path, null_value: float, run_validation=False):
        """
        Takes an elevation raster file in .tif format, and creates a dictionary with z-value for each network node;
        can then use self.apply_attributes_to_nodes() function to add elevation as a node attribute to the network
        :param elevation_tif_file_path: path to the elevation raster file in .tif format
        :param null_value: value that represents null in the elevation raster file
        :return: dict in format {node_id : {'z': z}}
        """
        img = elevation.get_elevation_image(elevation_tif_file_path)
        elevation_dict = {}

        for node_id, node_attribs in self.nodes():
            z = elevation.get_elevation_data(img, lat=node_attribs['lat'], lon=node_attribs['lon'])

            # zero values handling - may wish to add infilling based on nearby values later
            if z == null_value:
                z = 0
            elevation_dict[node_id] = {'z': z}

        if run_validation is True:
            report = elevation.validation_report_for_node_elevation(elevation_dict)
            logging.info(report['summary'])

        return elevation_dict

    def get_link_slope_dictionary(self, elevation_dict):
        """
        Takes a dictionary of z-value for each network node (as created by get_node_elevation_dictionary() function,
        calculates link slope and returns a dictionary of link IDs and their slopes; can then use
        self.apply_attributes_to_links() function to add slope as a link attribute to the network.
        :param elevation_dict: dict in format {node_id : {'z': z}}
        :return: dict in format {link_id : {'slope': slope}}, where slope is a float
        """
        slope_dict = {}

        for link in self.links():
            link_id = link[0]
            node_1 = self.link(link_id)['from']
            node_2 = self.link(link_id)['to']
            z_1 = elevation_dict[node_1]['z']
            z_2 = elevation_dict[node_2]['z']

            # TO-DO: calculate crow-fly distance between the 2 nodes instead of using routed distance
            length = self.link(link_id)['length']

            if length == 0:
                link_slope = 0
            else:
                # calculate slope by dividing the difference between elevations of two nodes by distance between them
                link_slope = (z_2 - z_1) / length

            slope_dict[link_id] = {'slope': link_slope}

        return slope_dict

    def summary(self):
        report = {}
        network_stats = {'Number of network links': nx.number_of_nodes(self.graph),
                         'Number of network nodes': nx.number_of_edges(self.graph)}
        report['network_graph_info'] = network_stats
        report['modes'] = {}
        report['modes']['Modes on network links'] = self.modes()

        # check for the old format, i.e. long-form attribute notation
        if len(graph_operations.get_attribute_data_under_key(
                self.links(), {'attributes': {'osm:way:highway': 'text'}}).values()) == 0:
            highway_tags = self.link_attribute_data_under_key({'attributes': 'osm:way:highway'})
            highway_tags = set(itertools.chain.from_iterable(highway_tags.apply(lambda x: persistence.setify(x))))
        else:
            highway_tags = self.link_attribute_data_under_key({'attributes': {'osm:way:highway': 'text'}})
            highway_tags = set(itertools.chain.from_iterable(highway_tags.apply(lambda x: persistence.setify(x))))

        osm_highway_tags = {}
        for tag in highway_tags:
            tag_links = self.extract_links_on_edge_attributes(conditions={'attributes': {'osm:way:highway': tag}},
                                                              mixed_dtypes=True)
            osm_highway_tags[tag] = len(tag_links)
        report['osm_highway_tags'] = {'Number of links by tag': osm_highway_tags}

        links_by_mode = {}
        for mode in self.modes():
            mode_links = self.extract_links_on_edge_attributes(conditions={'modes': mode}, mixed_dtypes=True)
            links_by_mode[mode] = len(mode_links)
        report['modes']['Number of links by mode'] = links_by_mode

        return report

    def summary_report(self):
        """
        Returns a report with summary statistics for the network and the schedule.
        """
        logging.info('Creating a summary report')
        report = {'network': self.summary()}

        if self.schedule:
            report['schedule'] = self.schedule.summary()

        return report
