import os
import logging
import osmnx as ox


def save_nodes_and_links_geojson(graph, output_dir):
    gdf_nodes, gdf_links = ox.utils_graph.graph_to_gdfs(graph)
    gdf_nodes = gdf_nodes.to_crs("EPSG:4326")
    gdf_links = gdf_links.to_crs("EPSG:4326")

    gdf_links['modes'] = gdf_links['modes'].apply(lambda x: ','.join(x))

    logging.info(f'Saving nodes and links geojsons to {output_dir}')
    gdf_nodes.to_file(os.path.join(output_dir, 'nodes.geojson'), driver='GeoJSON')
    gdf_links.to_file(os.path.join(output_dir, 'links.geojson'), driver='GeoJSON')
    gdf_nodes['geometry'].to_file(os.path.join(output_dir, 'nodes_geometry_only.geojson'), driver='GeoJSON')
    gdf_links['geometry'].to_file(os.path.join(output_dir, 'links_geometry_only.geojson'), driver='GeoJSON')
    return gdf_nodes, gdf_links
