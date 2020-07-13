import os
import pickle
from genet.schedule_elements import Route, Stop
from tests.fixtures import stop_epsg_27700, route, assert_semantically_equal


def test_pickling(tmpdir):
    stop = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    stop.add_additional_attributes({'extra': 'stuff'})
    route = Route(route_short_name='Route Short Name', mode='MoDe',
              stops=[stop],
              trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
              arrival_offsets=['00:00:00'],
              departure_offsets=['00:00:00'],
              route=['1'], route_long_name='Route Long Name',
              id='ID', await_departure=[True])

    pickle_path = os.path.join(tmpdir, 'route.pickle')
    with open(pickle_path, 'wb') as handle:
        pickle.dump(route, handle, protocol=pickle.HIGHEST_PROTOCOL)
    assert os.path.exists(pickle_path)
    with open(pickle_path, 'rb') as handle:
        route_from_pickle = pickle.load(handle)

    attributes = ['route_short_name', 'mode', 'trips', 'arrival_offsets', 'departure_offsets', 'route',
                  'route_long_name', 'id', 'await_departure']
    assert_semantically_equal({k: route_from_pickle.__dict__[k] for k in attributes},
                              {k: route.__dict__[k] for k in attributes})

    stop_from_pickle = route_from_pickle.stops[0]

    attributes = ['additional_attributes', 'epsg', 'extra', 'id', 'lat', 'lon', 'x', 'y']
    assert_semantically_equal({k: stop_from_pickle.__dict__[k] for k in attributes},
                              {k: stop.__dict__[k] for k in attributes})


def test_routes_equal(stop_epsg_27700):
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    b = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={},
        arrival_offsets=[],
        departure_offsets=[])

    assert a == b


def test_routes_exact():
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    b = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    assert a.is_exact(b)


def test_route_isin_exact_list(route):
    a = route

    assert a.isin_exact([route, route, route])


def test_route_is_not_in_exact_list(route, stop_epsg_27700):
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={},
        arrival_offsets=[],
        departure_offsets=[])

    assert not a.isin_exact([route, route, route])
