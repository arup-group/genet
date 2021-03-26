import genet.inputs_handler.gtfs_reader as gtfs_reader
import genet.schedule_elements as schedule_elements


def read_matsim(path_to_network: str, path_to_schedule: str = None, path_to_vehicles: str = None):
    """

    :param path_to_network: path to MATSim's network.xml file
    :param path_to_schedule: path to MATSim's schedule.xml file, optional
    :param path_to_vehicles: path to MATSim's vehicles.xml file, optional, expected to be passed with a schedule
    :return: genet.Network object
    """
    pass


def read_json(path: str):
    """

    :param path: path to json or geojson
    :return: genet.Network object
    """
    pass


def read_csv(path_to_csv: str):
    """

    :param path_to_csv: can be folder or zip of csv files, containing csv files with correct names and following the
        expected schema
    :return: genet.Network object
    """
    pass


def read_gtfs(path, day):
    """
    Reads from GTFS. The resulting services will not have network routes. Assumed to be in lat lon epsg:4326
    :param path: to GTFS folder or a zip file
    :param day: 'YYYYMMDD' to use from the gtfs
    :return:
    """
    schedule_graph = gtfs_reader.read_to_dict_schedule_and_stopd_db(path, day)
    return schedule_elements.Schedule(epsg='epsg:4326', _graph=schedule_graph)
