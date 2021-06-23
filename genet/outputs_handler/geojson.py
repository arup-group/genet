import os
import logging
from itertools import chain
from shapely.geometry import Point, LineString
import geopandas as gpd
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


def setify(x):
    if not isinstance(x, set):
        return {x}
    else:
        return x


def generate_geodataframes(graph):
    def line_geometry():
        from_node = nodes.loc[_u, :]
        to_node = nodes.loc[_v, :]
        return LineString(
            [(float(from_node['x']), float(from_node['y'])), (float(to_node['x']), float(to_node['y']))])

    crs = graph.graph['crs']['init']

    node_ids, data = zip(*graph.nodes(data=True))
    geometry = [Point(float(d['x']), float(d['y'])) for d in data]
    nodes = gpd.GeoDataFrame(data, index=node_ids, crs=crs, geometry=geometry)
    nodes.index = nodes.index.set_names(['index'])

    u, v, data = zip(*graph.edges(data=True))
    geometry = []
    for _u, _v, d in zip(u, v, data):
        try:
            geom = d['geometry']
        except KeyError:
            geom = line_geometry()
        geometry.append(geom)
    links = gpd.GeoDataFrame(data, crs=crs, geometry=geometry)
    links['u'] = u
    links['v'] = v
    if 'id' in links.columns:
        links = links.set_index('id', drop=False)
    links.index = links.index.set_names(['index'])

    return {'nodes': nodes, 'links': links}


def save_geodataframe(gdf, filename, output_dir, include_shp_files=False):
    if not gdf.empty:
        gdf = sanitiser.sanitise_geodataframe(gdf)
        persistence.ensure_dir(output_dir)
        gdf.to_file(os.path.join(output_dir, f'{filename}.geojson'), driver='GeoJSON')
        for col in [col for col in gdf.columns if is_datetime(gdf[col])]:
            gdf[col] = gdf[col].astype(str)
        if include_shp_files:
            shp_files = os.path.join(output_dir, 'shp_files')
            persistence.ensure_dir(shp_files)
            gdf.to_file(os.path.join(shp_files, f'{filename}.shp'))


def generate_standard_outputs_for_schedule(schedule, output_dir, gtfs_day='19700101', include_shp_files=False):
    logging.info('Generating geojson standard outputs for schedule')
    schedule_links = schedule.to_geodataframe()['links'].to_crs("epsg:4326")
    df = schedule.route_trips_with_stops_to_dataframe(gtfs_day=gtfs_day)
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
            output_dir=vph_dir,
            include_shp_files=include_shp_files
        )

        if df_all_modes_vph is None:
            df_vph['mode'] = mode
            df_all_modes_vph = df_vph
        else:
            df_vph['mode'] = mode
            df_all_modes_vph = df_all_modes_vph.append(df_vph)

        logging.info(f'Generating schedule graph for {mode}')
        schedule_subgraph = generate_geodataframes(
            schedule.subgraph(graph_mode_map[mode]))
        save_geodataframe(
            schedule_subgraph['links'].to_crs("epsg:4326"),
            filename=f'schedule_subgraph_links_{mode}',
            output_dir=subgraph_dir,
            include_shp_files=include_shp_files
        )
        save_geodataframe(
            schedule_subgraph['nodes'].to_crs("epsg:4326"),
            filename=f'schedule_subgraph_nodes_{mode}',
            output_dir=subgraph_dir,
            include_shp_files=include_shp_files
        )

    logging.info('Saving vehicles per hour for all PT modes')
    save_geodataframe(
        df_all_modes_vph,
        filename='vehicles_per_hour_all_modes',
        output_dir=vph_dir,
        include_shp_files=include_shp_files
    )
    logging.info('Saving vehicles per hour for all PT modes for selected hour slices')
    for h in [7, 8, 9, 13, 16, 17, 18]:
        save_geodataframe(
            df_all_modes_vph[df_all_modes_vph['hour'].dt.hour == h],
            filename=f'vph_all_modes_within_{h-1}:30-{h}:30',
            output_dir=vph_dir,
            include_shp_files=include_shp_files
        )

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
    df_trips_per_route = use_schedule.trips_per_day_per_route(df, output_dir=output_dir)

    # stop-to-stop trips per day aggregation
    aggregated_per_stops = use_schedule.aggregate_trips_per_day_per_route_by_end_stop_pairs(
        schedule, df_trips_per_route)
    aggregated_per_stops.to_csv(os.path.join(output_dir, 'trips_per_day_per_route_aggregated_per_stop_id_pair.csv'))
    use_schedule.aggregate_by_stop_names(aggregated_per_stops).to_csv(
        os.path.join(output_dir, 'trips_per_day_per_route_aggregated_per_stop_name_pair.csv'))


def generate_standard_outputs(n, output_dir, gtfs_day='19700101', include_shp_files=False):
    logging.info(f'Generating geojson outputs for the entire network in {output_dir}')
    n.write_to_geojson(output_dir)

    graph_links = n.to_geodataframe()['links'].to_crs("epsg:4326")

    logging.info('Generating geojson outputs for car/driving modal subgraph')
    graph_output_dir = os.path.join(output_dir, 'graph')
    gdf_car = graph_links[graph_links.apply(lambda x: modal_subset(x, {'car'}), axis=1)]
    for attribute in ['freespeed', 'capacity', 'permlanes']:
        try:
            save_geodataframe(
                gdf_car[[attribute, 'geometry', 'id']],
                filename=f'car_{attribute}_subgraph',
                output_dir=graph_output_dir,
                include_shp_files=include_shp_files)
        except KeyError:
            logging.warning(f'Your network is missing a vital attribute {attribute}')

    logging.info('Generating geojson outputs for different highway tags in car modal subgraph')
    highway_tags = n.link_attribute_data_under_key({'attributes': {'osm:way:highway': 'text'}})
    highway_tags = set(chain.from_iterable(highway_tags.apply(lambda x: setify(x))))
    for tag in highway_tags:
        tag_links = n.extract_links_on_edge_attributes(
            conditions={'attributes': {'osm:way:highway': {'text': tag}}},
            mixed_dtypes=True)
        save_geodataframe(
            graph_links[graph_links['id'].isin(tag_links)],
            filename=f'car_osm_highway_{tag}',
            output_dir=graph_output_dir,
            include_shp_files=include_shp_files
        )

    for mode in n.modes():
        logging.info(f'Generating geometry-only geojson outputs for {mode} modal subgraph')
        gdf = graph_links[graph_links.apply(lambda x: modal_subset(x, {mode}), axis=1)]
        save_geodataframe(
            gdf[['geometry', 'id']],
            filename=f'subgraph_geometry_{mode}',
            output_dir=os.path.join(graph_output_dir, 'geometry_only_subgraphs'),
            include_shp_files=include_shp_files
        )

    # schedule outputs
    if n.schedule:
        generate_standard_outputs_for_schedule(
            n.schedule,
            output_dir=os.path.join(output_dir, 'schedule'),
            gtfs_day=gtfs_day,
            include_shp_files=include_shp_files
        )
