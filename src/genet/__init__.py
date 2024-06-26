"""Top-level module for genet."""

import pyproj

from genet.auxiliary_files import AuxiliaryFile
from genet.core import Network
from genet.input.read import (
    read_csv,
    read_geojson_network,
    read_gtfs,
    read_json,
    read_json_network,
    read_json_schedule,
    read_matsim,
    read_matsim_network,
    read_matsim_road_pricing,
    read_matsim_schedule,
    read_osm,
)
from genet.max_stable_set import MaxStableSet
from genet.schedule_elements import Route, Schedule, Service, Stop
from genet.use.road_pricing import Toll
from genet.utils import elevation, google_directions, graph_operations

__author__ = """Kasia Kozlowska"""  # triple quotes in case the name has quotes in it.
__email__ = "36536946+KasiaKoz@users.noreply.github.com"
__version__ = "4.0.0"

pyproj.network.set_network_enabled(False)
