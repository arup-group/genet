import itertools
import logging
import os
from datetime import datetime, timedelta
from typing import List

import geopandas as gpd
import numpy as np
import pandas as pd

import genet.utils.spatial as spatial


def sanitise_time(time, gtfs_day="19700101"):
    time_list = time.split(":")
    if int(time_list[0]) >= 24:
        days = int(time_list[0]) // 24
        time_list[0] = int(time_list[0]) % 24
        if time_list[0] < 10:
            time_list[0] = "0{}".format(time_list[0])
        else:
            time_list[0] = str(time_list[0])
        return datetime.strptime(
            gtfs_day + " " + ":".join(time_list), "%Y%m%d %H:%M:%S"
        ) + timedelta(days=days)
    else:
        return datetime.strptime(gtfs_day + " " + time, "%Y%m%d %H:%M:%S")


def get_offset(time):
    time_list = time.split(":")
    return timedelta(
        seconds=int(time_list[0]) * 60 * 60 + int(time_list[1]) * 60 + int(time_list[2])
    )


def generate_edge_vph_geodataframe(df, gdf_links):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param gdf_links: geodataframe containing links of the schedule (element) graph
    :return:
    """
    df.loc[:, "hour"] = df["departure_time"].dt.round("H")
    groupby_cols = ["hour", "trip_id", "from_stop", "from_stop_name", "to_stop", "to_stop_name"]
    df = df.groupby(groupby_cols).count().reset_index()
    df.loc[:, "vph"] = 1
    groupby_cols.remove("trip_id")
    df = df.groupby(groupby_cols).sum().reset_index()

    cols_to_delete = df.columns.difference(groupby_cols + ["vph"])
    gdf = gdf_links.merge(df, left_on=["u", "v"], right_on=["from_stop", "to_stop"])
    gdf = gdf.drop(cols_to_delete.union(["u", "v", "routes", "services"]), axis=1)
    return gdf


def vehicles_per_hour(df, aggregate_by: list, output_path=""):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param aggregate_by:
    :param output_path: path for the frame with .csv extension
    :return:
    """
    df.loc[:, "hour"] = df["departure_time"].dt.round("H")
    df.loc[:, "hour"] = df["hour"].dt.hour
    df = df.groupby(["hour", "trip_id"] + aggregate_by).count().reset_index()
    df.loc[:, "vph"] = 1
    df = pd.pivot_table(
        df, values="vph", index=aggregate_by, columns=["hour"], aggfunc=np.sum
    ).reset_index()
    df = df.fillna(0)
    if output_path:
        df.to_csv(output_path)
    return df


def trips_per_day_per_service(df, output_dir=""):
    """
    Generates trips per day per service for a trips dataframe
    :param df: trips dataframe
    :param output_dir: directory to save `trips_per_day_per_service.csv`
    :return:
    """
    trips_per_day = (
        df.groupby(["service_id", "service_name", "route_id", "mode"])
        .nunique()["trip_id"]
        .reset_index()
    )
    trips_per_day = (
        trips_per_day.groupby(["service_id", "service_name", "mode"]).sum()["trip_id"].reset_index()
    )
    trips_per_day = trips_per_day.rename(columns={"trip_id": "number_of_trips"})
    if output_dir:
        trips_per_day.to_csv(os.path.join(output_dir, "trips_per_day_per_service.csv"))
    return trips_per_day


def trips_per_day_per_route(df, output_dir=""):
    """
    Generates trips per day per route for a trips dataframe
    :param df: trips dataframe
    :param output_dir: directory to save `trips_per_day_per_service.csv`
    :return:
    """
    trips_per_day = (
        df.groupby(["route_id", "route_name", "mode"]).nunique()["trip_id"].reset_index()
    )
    trips_per_day = trips_per_day.rename(columns={"trip_id": "number_of_trips"})
    if output_dir:
        trips_per_day.to_csv(os.path.join(output_dir, "trips_per_day_per_route.csv"))
    return trips_per_day


def aggregate_trips_per_day_per_route_by_end_stop_pairs(schedule, trips_per_day_per_route):
    def route_id_intersect(row):
        intersect = set(schedule.graph().nodes[row["station_A"]]["routes"]) & set(
            schedule.graph().nodes[row["station_B"]]["routes"]
        )
        if intersect:
            return intersect
        else:
            return float("nan")

    df = None
    for mode in schedule.modes():
        end_points = set()
        for route in schedule.routes():
            if route.mode == mode:
                end_points |= {route.ordered_stops[0], route.ordered_stops[-1]}
        df_stops = pd.DataFrame.from_records(
            list(itertools.combinations({schedule.stop(pt).id for pt in end_points}, 2)),
            columns=["station_A", "station_B"],
        )
        df_stops["station_A_name"] = df_stops["station_A"].apply(lambda x: schedule.stop(x).name)
        df_stops["station_B_name"] = df_stops["station_B"].apply(lambda x: schedule.stop(x).name)
        df_stops["mode"] = mode
        if df is None:
            df = df_stops
        else:
            df = pd.concat([df, df_stops])
    df["routes_in_common"] = df.apply(lambda x: route_id_intersect(x), axis=1)
    df = df.dropna()
    trips_per_day_per_route = trips_per_day_per_route.set_index("route_id")
    df["number_of_trips"] = df["routes_in_common"].apply(
        lambda x: sum([trips_per_day_per_route.loc[r_id, "number_of_trips"] for r_id in x])
    )
    return df


def aggregate_by_stop_names(df_aggregate_trips_per_day_per_route_by_end_stop_pairs):
    df = df_aggregate_trips_per_day_per_route_by_end_stop_pairs
    df = df[(df["station_A_name"] != "") & (df["station_B_name"] != "")]
    if not df.empty:
        df[["station_A_name", "station_B_name"]] = np.sort(
            df[["station_A_name", "station_B_name"]], axis=1
        )
        df = (
            df.groupby(["station_A_name", "station_B_name", "mode"])["number_of_trips"]
            .sum()
            .reset_index()
        )
    return df


def divide_network_route(route: List[str], stops_linkrefids: List[str]) -> List[List[str]]:
    """
    Divides into list of lists, the network route traversed by a PT service.
    E.g.
    route = ['a-a', 'a-b', 'b-b', 'b-c', 'c-c', 'c-d']
    stops_linkrefids = ['a-a', 'b-b', 'c-c']
    For a service with stops A, B, C, where the stops are snapped to network links 'a-a', 'b-b', 'c-c' respectively.
    This method will give you teh answer:
    [['a-a', 'a-b', 'b-b'], ['b-b', 'b-c', 'c-c']]
    i.e. the route between stops A and B, and B and C, in order.
    :param route: list of network link IDs (str)
    :param stops_linkrefids: List of network link IDs (str) that the stops on route are snapped to
    :return:
    """
    divided_route = [[]]
    for link_id in route:
        divided_route[-1].append(link_id)
        while stops_linkrefids and (link_id == stops_linkrefids[0]):
            divided_route.append([stops_linkrefids[0]])
            stops_linkrefids = stops_linkrefids[1:]
    return divided_route[1:-1]


def network_routed_distance_gdf(schedule, gdf_network_links):
    def combine_route(group):
        group = group.sort_values(by="sequence")
        geom = spatial.merge_linestrings(list(group["geometry"]))
        length = group["length"].sum()
        group = group.iloc[0, :][["id", "from_stop", "to_stop"]]
        group["geometry"] = geom
        group["network_distance"] = length
        return group

    # TODO speeds account for snapping to long links
    logging.warning(
        "Right now routed speeds do not account for services snapping to long network links. "
        "Be sure to account for that in your investigations and check the non-routed `pt_speeds`"
        "output as well."
    )

    routes_df = schedule.route_attribute_data(keys=["id", "network_links", "ordered_stops"])
    routes_df["linkrefids"] = routes_df.apply(
        lambda x: [
            schedule._graph.nodes[i]["linkRefId"]
            for i in schedule._graph.graph["routes"][x["id"]]["ordered_stops"]
        ],
        axis=1,
    )
    routes_df["network_links"] = routes_df.apply(
        lambda x: divide_network_route(x["network_links"], x["linkrefids"]), axis=1
    )
    routes_df.drop("linkrefids", axis=1, inplace=True)
    routes_df["ordered_stops"] = routes_df["ordered_stops"].apply(
        lambda x: list(zip(x[:-1], x[1:]))
    )
    stop_cols = np.concatenate(routes_df["ordered_stops"].values)
    route_cols = sum(routes_df["network_links"].values, [])
    # expand across stop pairs
    routes_df = pd.DataFrame(
        {
            col: np.repeat(routes_df[col].values, routes_df["ordered_stops"].str.len())
            for col in set(routes_df.columns) - {"ordered_stops", "network_links"}
        }
    ).assign(from_stop=stop_cols[:, 0], to_stop=stop_cols[:, 1], network_links=route_cols)
    # expand across route
    routes_df["sequence"] = routes_df["network_links"].apply(lambda x: list(range(len(x))))
    routes_df = pd.DataFrame(
        {
            col: np.repeat(routes_df[col].values, routes_df["network_links"].str.len())
            for col in set(routes_df.columns) - {"network_links", "sequence"}
        }
    ).assign(
        network_links=np.concatenate(routes_df["network_links"].values),
        sequence=np.concatenate(routes_df["sequence"].values),
    )
    routes_gdf = gdf_network_links[["length", "geometry"]].merge(
        routes_df, right_on="network_links", left_index=True
    )

    new_route = routes_gdf.groupby(["id", "from_stop", "to_stop"], as_index=False).apply(
        combine_route
    )

    return gpd.GeoDataFrame(new_route).set_crs(routes_gdf.crs)
