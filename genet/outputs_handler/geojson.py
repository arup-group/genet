import os
import logging
import osmnx as ox
from geopandas import GeoDataFrame, GeoSeries


def modal_subset(row, modes):
    row_modes = set(row['modes'])
    if modes & row_modes:
        return True
    else:
        return False


def generate_geodataframes(graph):
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
    gdf.to_file(os.path.join(output_dir, filename), driver='GeoJSON')


def save_network_to_geojson(n, output_dir):
    gdf_nodes, gdf_links = generate_geodataframes(n.graph)

    logging.info(f'Saving nodes and links geojsons to {output_dir}')
    save_geodataframe(gdf_nodes, 'nodes.geojson', output_dir)
    save_geodataframe(gdf_links, 'links.geojson', output_dir)
    save_geodataframe(gdf_nodes['geometry'], 'nodes_geometry_only.geojson', output_dir)
    save_geodataframe(gdf_links['geometry'], 'links_geometry_only.geojson', output_dir)

    # TODO add schedule outputs
    return gdf_nodes, gdf_links


def generate_standard_outputs(n, output_dir):
    gdf_nodes, gdf_links = generate_geodataframes(n.graph)

    logging.info('Generating geojson outputs for car/driving modal subgraph')
    gdf_car = gdf_links[gdf_links.apply(lambda x: modal_subset(x, {'car'}), axis=1)]
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
        gdf = gdf_links[gdf_links.apply(lambda x: modal_subset(x, {mode}), axis=1)]
        save_geodataframe(
            gdf['geometry'],
            filename=f'{mode}_subgraph_geometry.geojson',
            output_dir=output_dir)

    # TODO add schedule outputs
