from genet.schedule_elements import Stop
from tests.fixtures import stop_epsg_27700


def test_add_additional_attributes_to_stops():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    a.add_additional_attributes({'isBlocking': True, 'name': 'Brunswick Place (Stop P)'})

    assert a.name == 'Brunswick Place (Stop P)'
    assert a.isBlocking == True


def test_stops_equal():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    b = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')

    assert a == b


def test_stop_already_in_epsg_4326_gives_lat_lon():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')

    assert a.lon == a.x
    assert a.lat == a.y


def test_stops_exact():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')
    b = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')

    assert a.is_exact(b)


def test_stop_isin_exact_list(stop_epsg_27700):
    a = stop_epsg_27700

    assert a.isin_exact([stop_epsg_27700, stop_epsg_27700, stop_epsg_27700])


def test_route_is_not_in_exact_list(stop_epsg_27700):
    a = Stop(id='0', x=-3, y=52, epsg='epsg:4326')

    assert not a.isin_exact([stop_epsg_27700, stop_epsg_27700, stop_epsg_27700])