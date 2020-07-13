import pickle
import os
from genet.schedule_elements import Service, Route, Stop
from tests.fixtures import *


def test_pickling(tmpdir):
    stop = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    stop.add_additional_attributes({'extra': 'stuff'})
    _route = Route(route_short_name='Route Short Name', mode='MoDe',
              stops=[stop],
              trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
              arrival_offsets=['00:00:00'],
              departure_offsets=['00:00:00'],
              route=['1'], route_long_name='Route Long Name',
              id='ID', await_departure=[True])
    service = Service(id='1', routes=[_route], name='NaMe')

    pickle_path = os.path.join(tmpdir, 'service.pickle')
    with open(pickle_path, 'wb') as handle:
        pickle.dump(service, handle, protocol=pickle.HIGHEST_PROTOCOL)
    assert os.path.exists(pickle_path)
    with open(pickle_path, 'rb') as handle:
        service_from_pickle = pickle.load(handle)

    attributes = ['id', 'name']
    assert_semantically_equal({k: service_from_pickle.__dict__[k] for k in attributes},
                              {k: service.__dict__[k] for k in attributes})

    route_from_pickle = service_from_pickle.routes[0]
    attributes = ['route_short_name', 'mode', 'trips', 'arrival_offsets', 'departure_offsets', 'route',
                  'route_long_name', 'id', 'await_departure']
    assert_semantically_equal({k: route_from_pickle.__dict__[k] for k in attributes},
                              {k: _route.__dict__[k] for k in attributes})

    stop_from_pickle = service_from_pickle.routes[0].stops[0]
    attributes = ['additional_attributes', 'epsg', 'extra', 'id', 'lat', 'lon', 'x', 'y']
    assert_semantically_equal({k: stop_from_pickle.__dict__[k] for k in attributes},
                              {k: stop.__dict__[k] for k in attributes})


def test_services_equal(route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a == b


def test_services_exact(route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a.is_exact(b)


def test_route_isin_exact_list(test_service):
    a = test_service

    assert a.isin_exact([test_service, test_service])


def test_route_is_not_in_exact_list(similar_non_exact_test_route, test_service):
    a = Service(id='service',
                routes=[similar_non_exact_test_route])

    assert not a.isin_exact([test_service, test_service])