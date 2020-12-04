import os
import logging
import osmnx as ox
from networkx import MultiDiGraph
import genet.use.schedule as use_schedule
import genet.utils.persistence as persistence
import genet.outputs_handler.sanitiser as sanitiser
from pandas.api.types import is_datetime64_any_dtype as is_datetime


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


def save_geodataframe(gdf, filename, output_dir):
    if not gdf.empty:
        gdf = sanitiser.sanitise_geodataframe(gdf)
        persistence.ensure_dir(output_dir)
        gdf.to_file(os.path.join(output_dir, f'{filename}.geojson'), driver='GeoJSON')
        for col in [col for col in gdf.columns if is_datetime(gdf[col])]:
            gdf[col] = gdf[col].astype(str)
        shp_files = os.path.join(output_dir, 'shp_files')
        persistence.ensure_dir(shp_files)
        gdf.to_file(os.path.join(shp_files, f'{filename}.shp'))


def save_network_to_geojson(n, output_dir):
    graph_nodes, graph_links = generate_geodataframes(n.graph)

    logging.info(f'Saving network graph nodes and links geojsons to {output_dir}')
    save_geodataframe(graph_nodes, 'network_nodes', output_dir)
    save_geodataframe(graph_links, 'network_links', output_dir)
    save_geodataframe(graph_nodes['geometry'], 'network_nodes_geometry_only', output_dir)
    save_geodataframe(graph_links['geometry'], 'network_links_geometry_only', output_dir)

    if n.schedule:
        schedule_nodes, schedule_links = generate_geodataframes(MultiDiGraph(n.schedule.graph()))
        logging.info(f'Saving schedule graph nodes and links geojsons to {output_dir}')
        save_geodataframe(schedule_nodes, 'schedule_nodes', output_dir)
        save_geodataframe(schedule_links, 'schedule_links', output_dir)
        save_geodataframe(schedule_nodes['geometry'], 'schedule_nodes_geometry_only', output_dir)
        save_geodataframe(schedule_links['geometry'], 'schedule_links_geometry_only', output_dir)


def generate_standard_outputs_for_schedule(schedule, output_dir, gtfs_day='19700101'):
    logging.info('Generating geojson outputs for schedule')
    schedule_nodes, schedule_links = generate_geodataframes(schedule.graph())
    df = schedule.generate_trips_dataframe(gtfs_day=gtfs_day)
    df_all_modes_vph = None

    vph_dir = os.path.join(output_dir, 'vehicles_per_hour')
    subgraph_dir = os.path.join(output_dir, 'subgraphs')
    graph_mode_map = schedule.mode_graph_map()
    for mode in schedule.modes():
        logging.info(f'Generating vehicles per hour for {mode}')
        df_vph = use_schedule.generate_edge_vph_geodataframe(df[df['mode'] == mode], schedule_links)
        save_geodataframe(
            df_vph,
            filename=f'vehicles_per_hour_{mode}',
            output_dir=vph_dir)

        if df_all_modes_vph is None:
            df_vph['mode'] = mode
            df_all_modes_vph = df_vph
        else:
            df_vph['mode'] = mode
            df_all_modes_vph = df_all_modes_vph.append(df_vph)

        logging.info(f'Generating schedule graph for {mode}')
        schedule_subgraph_nodes, schedule_subgraph_links = generate_geodataframes(
            schedule.subgraph(graph_mode_map[mode]))
        save_geodataframe(
            schedule_subgraph_links,
            filename=f'schedule_subgraph_links_{mode}',
            output_dir=subgraph_dir)
        save_geodataframe(
            schedule_subgraph_nodes,
            filename=f'schedule_subgraph_nodes_{mode}',
            output_dir=subgraph_dir)

    logging.info('Saving vehicles per hour for all PT modes')
    save_geodataframe(
        df_all_modes_vph,
        filename='vehicles_per_hour_all_modes',
        output_dir=vph_dir)
    logging.info('Saving vehicles per hour for all PT modes for selected hour slices')
    for h in [7, 8, 9, 13, 16, 17, 18]:
        save_geodataframe(
            df_all_modes_vph[df_all_modes_vph['hour'].dt.hour == h],
            filename=f'vph_all_modes_within_{h-1}:30-{h}:30',
            output_dir=vph_dir)

    logging.info('Generating csv for vehicles per hour for each service')
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=['service', 'service_name', 'mode'],
        output_path=os.path.join(vph_dir, 'vph_per_service.csv'))

    logging.info('Generating csv for vehicles per hour per stop')
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=['from_stop', 'from_stop_name', 'mode'],
        output_path=os.path.join(vph_dir, 'vph_per_stop_departing_from.csv'))
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=['to_stop', 'to_stop_name', 'mode'],
        output_path=os.path.join(vph_dir, 'vph_per_stop_arriving_at.csv'))

    logging.info('Generating csvs for trips per day')
    use_schedule.trips_per_day_per_service(df, output_dir=output_dir)
    use_schedule.trips_per_day_per_route(df, output_dir=output_dir)


def generate_standard_outputs(n, output_dir, gtfs_day='19700101'):
    graph_nodes, graph_links = generate_geodataframes(n.graph)

    logging.info('Generating geojson outputs for car/driving modal subgraph')
    graph_output_dir = os.path.join(output_dir, 'graph')
    gdf_car = graph_links[graph_links.apply(lambda x: modal_subset(x, {'car'}), axis=1)]
    for attribute in ['freespeed', 'capacity', 'permlanes']:
        try:
            save_geodataframe(
                gdf_car[[attribute, 'geometry', 'id']],
                filename=f'car_{attribute}_subgraph',
                output_dir=graph_output_dir)
        except KeyError:
            logging.warning(f'Your network is missing a vital attribute {attribute}')

    for mode in n.modes():
        logging.info(f'Generating geometry-only geojson outputs for {mode} modal subgraph')
        gdf = graph_links[graph_links.apply(lambda x: modal_subset(x, {mode}), axis=1)]
        save_geodataframe(
            gdf[['geometry', 'id']],
            filename=f'subgraph_geometry_{mode}',
            output_dir=os.path.join(graph_output_dir, 'geometry_only_subgraphs'))

    # schedule outputs
    if n.schedule:
        generate_standard_outputs_for_schedule(
            n.schedule,
            output_dir=os.path.join(output_dir, 'schedule'),
            gtfs_day=gtfs_day)
