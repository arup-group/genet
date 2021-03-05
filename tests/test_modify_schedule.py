from pyproj import Transformer
from genet import Stop, Route
from genet.modify import schedule
from tests.fixtures import assert_semantically_equal


def test_reproj_stops():
    stops = {'26997928P': {'routes': ['10314_0'], 'id': '26997928P', 'x': 528464.1342843144, 'y': 182179.7435136598,
                           'epsg': 'epsg:27700', 'lat': 51.52393050617373, 'lon': -0.14967658860132668,
                           's2_id': 5221390302759871369, 'additional_attributes': [], 'services': ['10314']},
             '26997928P.link:1': {'routes': ['10314_0'], 'id': '26997928P.link:1', 'x': 528464.1342843144,
                                  'y': 182179.7435136598, 'epsg': 'epsg:27700', 'lat': 51.52393050617373,
                                  'lon': -0.14967658860132668, 's2_id': 5221390302759871369,
                                  'additional_attributes': [], 'services': ['10314']}}
    reprojected = schedule.reproj_stops(stops, 'epsg:4326')
    assert_semantically_equal(reprojected,
                              {'26997928P': {'x': -0.14967658860132668, 'y': 51.52393050617373, 'epsg': 'epsg:4326'},
                               '26997928P.link:1': {'x':-0.14967658860132668, 'y': 51.52393050617373,
                                                    'epsg': 'epsg:4326'}})
