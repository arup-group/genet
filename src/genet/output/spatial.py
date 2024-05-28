import json
import logging
import math
import os
from itertools import chain

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

import genet.output.sanitiser as sanitiser
import genet.use.schedule as use_schedule
import genet.utils.persistence as persistence
from genet.utils.io import save_geodataframe
from genet.variables import EPSG4326


def modal_subset(row, modes):
    row_modes = set(row["modes"])
    if modes & row_modes:
        return True
    else:
        return False


def generate_geodataframes(graph):
    def line_geometry():
        from_node = nodes.loc[_u, :]
        to_node = nodes.loc[_v, :]
        return LineString(
            [
                (float(from_node["x"]), float(from_node["y"])),
                (float(to_node["x"]), float(to_node["y"])),
            ]
        )

    crs = graph.graph["crs"]

    node_ids, data = zip(*graph.nodes(data=True))
    geometry = [Point(float(d["x"]), float(d["y"])) for d in data]
    nodes = gpd.GeoDataFrame(data, index=node_ids, crs=crs, geometry=geometry)
    nodes.index = nodes.index.set_names(["index"])

    u, v, data = zip(*graph.edges(data=True))
    geometry = []
    for _u, _v, d in zip(u, v, data):
        try:
            geom = d["geometry"]
        except KeyError:
            geom = line_geometry()
        geometry.append(geom)
    links = gpd.GeoDataFrame(data, crs=crs, geometry=geometry)
    links["u"] = u
    links["v"] = v
    if "id" in links.columns:
        links = links.set_index("id", drop=False)
    links.index = links.index.set_names(["index"])

    return {"nodes": nodes, "links": links}


def generate_standard_outputs_for_schedule(
    schedule,
    output_dir: str,
    gtfs_day: str = "19700101",
    filetype: str = "parquet",
    schedule_network_factor=1.3,
    gdf_network_links=None,
):
    """Generates spatial files that can be used for generating standard visualisations.

    Args:
        schedule (genet.Schedule): Schedule to generate outputs for.
        output_dir (str): Path to folder where to save the file.
        gtfs_day (str, optional):
            Day in format YYYYMMDD for the network's schedule for consistency in visualisations,
            Defaults to "19700101" (1970-01-01).
        filetype (str, optional):
            The file type to save the GeoDataFrame to: geojson, geoparquet or shp are supported.
            Defaults to parquet format.
        schedule_network_factor (float, optional):
            Factor to apply to beeline distances between stops when computing speed.
        gdf_network_links (gpd.GeoDataFrame):
            GeoDataFrame of network links that are referenced in the Schedule.
    """
    logging.info("Generating spatial standard outputs for schedule")
    schedule_links = schedule.to_geodataframe()["links"].to_crs("epsg:4326")
    df = schedule.trips_with_stops_to_dataframe(gtfs_day=gtfs_day)
    df_all_modes_vph = None

    vph_dir = os.path.join(output_dir, "vehicles_per_hour")
    subgraph_dir = os.path.join(output_dir, "subgraphs")
    graph_mode_map = schedule.mode_graph_map()
    for mode in schedule.modes():
        logging.info(f"Generating vehicles per hour for {mode}")
        df_vph = use_schedule.generate_edge_vph_geodataframe(df[df["mode"] == mode], schedule_links)
        save_geodataframe(
            df_vph, filename=f"vehicles_per_hour_{mode}", output_dir=vph_dir, filetype=filetype
        )

        if df_all_modes_vph is None:
            df_vph["mode"] = mode
            df_all_modes_vph = df_vph
        else:
            df_vph["mode"] = mode
            df_all_modes_vph = pd.concat([df_all_modes_vph, df_vph])

        logging.info(f"Generating schedule graph for {mode}")
        schedule_subgraph = generate_geodataframes(schedule.subgraph(graph_mode_map[mode]))
        save_geodataframe(
            schedule_subgraph["links"].to_crs("epsg:4326"),
            filename=f"schedule_subgraph_links_{mode}",
            output_dir=subgraph_dir,
            filetype=filetype,
        )
        save_geodataframe(
            schedule_subgraph["nodes"].to_crs("epsg:4326"),
            filename=f"schedule_subgraph_nodes_{mode}",
            output_dir=subgraph_dir,
            filetype=filetype,
        )

    logging.info("Saving vehicles per hour for all PT modes")
    save_geodataframe(
        df_all_modes_vph,
        filename="vehicles_per_hour_all_modes",
        output_dir=vph_dir,
        filetype=filetype,
    )
    logging.info("Saving vehicles per hour for all PT modes for selected hour slices")
    for h in [7, 8, 9, 13, 16, 17, 18]:
        save_geodataframe(
            df_all_modes_vph[pd.to_datetime(df_all_modes_vph["hour"]).dt.hour == h],
            filename=f"vph_all_modes_within_{h - 1}_30-{h}_30",
            output_dir=vph_dir,
            filetype=filetype,
        )

    logging.info(
        f"Generating stop-to-stop speed outputs with network_factor={schedule_network_factor}"
    )
    speed_dir = os.path.join(output_dir, "speed")
    speeds_gdf = schedule.speed_geodataframe(
        network_factor=schedule_network_factor, gdf_network_links=gdf_network_links
    )
    save_geodataframe(
        speeds_gdf[
            ["service_id", "route_id", "mode", "from_stop", "to_stop", "routed_speed", "geometry"]
        ],
        filename="pt_network_speeds",
        output_dir=speed_dir,
        filetype=filetype,
    )
    speeds_gdf = gpd.GeoDataFrame(
        pd.merge(
            speeds_gdf.drop("geometry", axis=1),
            schedule_links[["u", "v", "geometry"]],
            left_on=["from_stop", "to_stop"],
            right_on=["u", "v"],
        ),
        crs=schedule_links.crs,
    )
    save_geodataframe(
        speeds_gdf[["service_id", "route_id", "mode", "from_stop", "to_stop", "speed", "geometry"]],
        filename="pt_speeds",
        output_dir=speed_dir,
        filetype=filetype,
    )

    logging.info("Generating csv for vehicles per hour for each service")
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=["service_id", "service_name", "mode"],
        output_path=os.path.join(vph_dir, "vph_per_service.csv"),
    )

    logging.info("Generating csv for vehicles per hour per stop")
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=["from_stop", "from_stop_name", "mode"],
        output_path=os.path.join(vph_dir, "vph_per_stop_departing_from.csv"),
    )
    use_schedule.vehicles_per_hour(
        df,
        aggregate_by=["to_stop", "to_stop_name", "mode"],
        output_path=os.path.join(vph_dir, "vph_per_stop_arriving_at.csv"),
    )

    logging.info("Generating csvs for trips per day")
    use_schedule.trips_per_day_per_service(df, output_dir=output_dir)
    df_trips_per_route = use_schedule.trips_per_day_per_route(df, output_dir=output_dir)

    # stop-to-stop trips per day aggregation
    aggregated_per_stops = use_schedule.aggregate_trips_per_day_per_route_by_end_stop_pairs(
        schedule, df_trips_per_route
    )
    aggregated_per_stops.to_csv(
        os.path.join(output_dir, "trips_per_day_per_route_aggregated_per_stop_id_pair.csv")
    )
    use_schedule.aggregate_by_stop_names(aggregated_per_stops).to_csv(
        os.path.join(output_dir, "trips_per_day_per_route_aggregated_per_stop_name_pair.csv")
    )


def generate_standard_outputs(
    n, output_dir, gtfs_day="19700101", filetype: str = "parquet", schedule_network_factor=1.3
):
    """Generates spatial files that can be used for generating standard visualisations.

    Args:
        n (genet.Network): Schedule to generate outputs for.
        output_dir (str): Path to folder where to save the file.
        gtfs_day (str, optional):
            Day in format YYYYMMDD for the network's schedule for consistency in visualisations,
            Defaults to "19700101" (1970-01-01).
        filetype (str, optional):
            The file type to save the GeoDataFrame to: geojson, geoparquet or shp are supported.
            Defaults to parquet format.
        schedule_network_factor (float, optional):
            Factor to apply to beeline distances between Schedule stops when computing speed.
    """
    logging.info(f"Generating spatial outputs for the entire network in {output_dir}")
    n.write_spatial(output_dir, epsg="epsg:4326", filetype=filetype)

    graph_links = n.to_geodataframe()["links"].to_crs("epsg:4326")

    logging.info("Generating geojson outputs for car/driving modal subgraph")
    graph_output_dir = os.path.join(output_dir, "graph")
    gdf_car = graph_links.loc[graph_links.apply(lambda x: modal_subset(x, {"car"}), axis=1), :]
    for attribute in ["freespeed", "capacity", "permlanes"]:
        try:
            save_geodataframe(
                gdf_car[[attribute, "geometry", "id"]],
                filename=f"car_{attribute}_subgraph",
                output_dir=graph_output_dir,
                filetype=filetype,
            )
        except KeyError:
            logging.warning(f"Your network is missing a vital attribute {attribute}")

    logging.info("Generating geojson outputs for different highway tags in car modal subgraph")
    highway_tags = n.link_attribute_data_under_key({"attributes": "osm:way:highway"})
    highway_tags = set(chain.from_iterable(highway_tags.apply(lambda x: persistence.setify(x))))
    for tag in highway_tags:
        tag_links = n.extract_links_on_edge_attributes(
            conditions={"attributes": {"osm:way:highway": tag}}, mixed_dtypes=True
        )
        save_geodataframe(
            graph_links[graph_links["id"].isin(tag_links)],
            filename=f"car_osm_highway_{tag}",
            output_dir=graph_output_dir,
            filetype=filetype,
        )

    for mode in n.modes():
        logging.info(f"Generating geometry-only geojson outputs for {mode} modal subgraph")
        gdf = graph_links[graph_links.apply(lambda x: modal_subset(x, {mode}), axis=1)]
        save_geodataframe(
            gdf[["geometry", "id"]],
            filename=f"subgraph_geometry_{mode}",
            output_dir=os.path.join(graph_output_dir, "geometry_only_subgraphs"),
            filetype=filetype,
        )

    # schedule outputs
    if n.schedule:
        generate_standard_outputs_for_schedule(
            n.schedule,
            output_dir=os.path.join(output_dir, "schedule"),
            gtfs_day=gtfs_day,
            filetype=filetype,
            schedule_network_factor=schedule_network_factor,
            gdf_network_links=graph_links,
        )

        logging.info("Generating PT network routes")
        gdf_routes = n.schedule_network_routes_geodataframe().to_crs("epsg:4326")
        save_geodataframe(
            gdf_routes,
            filename="schedule_network_routes_geodataframe",
            output_dir=os.path.join(output_dir, "routing"),
            filetype=filetype,
        )

    summary_report = n.summary_report()
    with open(os.path.join(output_dir, "summary_report.json"), "w", encoding="utf-8") as f:
        json.dump(sanitiser.sanitise_dictionary(summary_report), f, ensure_ascii=False, indent=4)


def generate_headway_geojson(n, gdf, output_dir, filename_suffix):
    headways = n.schedule.headway_stats()
    headways_gdf = gdf[["route_id", "geometry"]].merge(headways, how="right", on="route_id")
    save_geodataframe(headways_gdf.to_crs(EPSG4326), f"headway_stats_{filename_suffix}", output_dir)


def generate_speed_geojson(n, gdf, output_dir, filename_suffix):
    speeds = n.schedule.speed_geodataframe()
    # fill infinity by large number to show up in visualisations
    speeds.loc[speeds["speed"] == math.inf, "speed"] = 9999

    speeds = (
        speeds.groupby(["service_id", "route_id", "route_name", "mode"])
        .max()["speed"]
        .reset_index()
    )
    speeds_gdf = gdf[["route_id", "geometry"]].merge(speeds, how="right", on="route_id")
    save_geodataframe(speeds_gdf.to_crs(EPSG4326), f"max_speeds_{filename_suffix}", output_dir)
