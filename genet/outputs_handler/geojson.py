import os
import logging
import osmnx as ox
from geopandas import GeoDataFrame, GeoSeries
from networkx import MultiDiGraph
import genet.use.schedule as use_schedule
import genet.utils.persistence as persistence


def modal_subset(row, modes):
    row_modes = set(row['modes'])
    if modes & row_modes:
        return True
    else:
        return False


def generate_geodataframes(graph):
    if not isinstance(graph, MultiDiGraph):
        graph = MultiDiGraph(graph)
    gdf_nodes, gdf_links = ox.utils_graph.graph_to_gdfs(graph)
    gdf_nodes = gdf_nodes.to_crs("EPSG:4326")
    gdf_links = gdf_links.to_crs("EPSG:4326")
    return gdf_nodes, gdf_links


def sanitise_geodataframe(gdf):
    if isinstance(gdf, GeoSeries):
        gdf = GeoDataFrame(gdf)
    gdf = gdf.fillna('None')
    object_columns = gdf.select_dtypes(['object']).columns
    for col in object_columns:
        if gdf[col].apply(lambda x: isinstance(x, list)).any():
            gdf[col] = gdf[col].apply(lambda x: ','.join(x))
        elif gdf[col].apply(lambda x: isinstance(x, dict)).any():
            # TODO add support for dictionaries
            pass
    return gdf


def save_geodataframe(gdf, filename, output_dir):
    gdf = sanitise_geodataframe(gdf)
    persistence.ensure_dir(output_dir)
    gdf.to_file(os.path.join(output_dir, filename), driver='GeoJSON')


def save_network_to_geojson(n, output_dir):
    graph_nodes, graph_links = generate_geodataframes(n.graph)

    logging.info(f'Saving network graph nodes and links geojsons to {output_dir}')
    save_geodataframe(graph_nodes, 'network_nodes.geojson', output_dir)
    save_geodataframe(graph_links, 'network_links.geojson', output_dir)
    save_geodataframe(graph_nodes['geometry'], 'network_nodes_geometry_only.geojson', output_dir)
    save_geodataframe(graph_links['geometry'], 'network_links_geometry_only.geojson', output_dir)

    if n.schedule:
        schedule_nodes, schedule_links = generate_geodataframes(MultiDiGraph(n.schedule.graph()))
        logging.info(f'Saving schedule graph nodes and links geojsons to {output_dir}')
        save_geodataframe(schedule_nodes, 'schedule_nodes.geojson', output_dir)
        save_geodataframe(schedule_links, 'schedule_links.geojson', output_dir)
        save_geodataframe(schedule_nodes['geometry'], 'schedule_nodes_geometry_only.geojson', output_dir)
        save_geodataframe(schedule_links['geometry'], 'schedule_links_geometry_only.geojson', output_dir)


def generate_standard_outputs(n, output_dir, gtfs_day='19700101'):
    graph_nodes, graph_links = generate_geodataframes(n.graph)

    logging.info('Generating geojson outputs for car/driving modal subgraph')
    gdf_car = graph_links[graph_links.apply(lambda x: modal_subset(x, {'car'}), axis=1)]
    for attribute in ['freespeed', 'capacity', 'permlanes']:
        try:
            save_geodataframe(
                gdf_car[[attribute, 'geometry']],
                filename=f'car_{attribute}_subgraph.geojson',
                output_dir=output_dir)
        except KeyError:
            logging.warning(f'Your network is missing a vital attribute {attribute}')

    for mode in n.modes():
        logging.info(f'Generating geometry-only geojson outputs for {mode} modal subgraph')
        gdf = graph_links[graph_links.apply(lambda x: modal_subset(x, {mode}), axis=1)]
        save_geodataframe(
            gdf['geometry'],
            filename=f'{mode}_subgraph_geometry.geojson',
            output_dir=output_dir)

    # schedule outputs
    if n.schedule:
        logging.info('Generating geojson outputs for schedule')
        schedule_nodes, schedule_links = generate_geodataframes(n.schedule.graph())
        df = use_schedule.generate_trips_dataframe(n.schedule, gtfs_day=gtfs_day)

        graph_mode_map = n.schedule.mode_graph_map()
        for mode in n.schedule.modes():
            logging.info(f'Generating vehicles per hour for {mode}')
            save_geodataframe(
                use_schedule.generate_edge_vph_geodataframe(df[df['mode'] == mode], schedule_nodes, schedule_links),
                filename=f'{mode}_vehicles_per_hour.geojson',
                output_dir=output_dir)
            logging.info(f'Generating schedule graph for {mode}')
            schedule_subgraph_nodes, schedule_subgraph_links = generate_geodataframes(
                n.schedule.subgraph(graph_mode_map[mode]))
            save_geodataframe(
                schedule_subgraph_links,
                filename=f'{mode}_schedule_subgraph_links.geojson',
                output_dir=output_dir)
            save_geodataframe(
                schedule_subgraph_nodes,
                filename=f'{mode}_schedule_subgraph_nodes.geojson',
                output_dir=output_dir)
