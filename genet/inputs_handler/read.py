

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
