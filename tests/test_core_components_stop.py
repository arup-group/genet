from genet.schedule_elements import Stop
from tests.fixtures import stop_epsg_27700, assert_semantically_equal
from pyproj import Proj, Transformer


def test_initiate_stop_with_kwargs():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700', linkRefId='1')
    assert a.has_linkRefId()
    assert a.additional_attributes == ['linkRefId']


def test_reproject_stops_without_transformer():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    a.reproject('epsg:4326')

    assert_semantically_equal({'x': a.x, 'y': a.y}, {'x': 51.52370573323939, 'y': -0.14910908709500162})
    assert a.epsg == 'epsg:4326'


def test_reproject_stops_with_transformer():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:4326'))
    a.reproject('epsg:4326', transformer)

    assert_semantically_equal({'x': a.x, 'y': a.y}, {'x': 51.52370573323939, 'y': -0.14910908709500162})
    assert a.epsg == 'epsg:4326'


def test__repr__shows_projection():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    r = a.__repr__()
    assert 'epsg:27700' in r


def test__str__shows_info():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    assert 'epsg:27700' in a.__str__()
    assert str(a._round_lat()) in a.__str__()
    assert str(a._round_lon()) in a.__str__()


def test_print_shows_info(mocker):
    mocker.patch.object(Stop, 'info')
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    a.print()
    Stop.info.assert_called_once()


def test_info_shows_id_projection_and_lat_lon():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    info = a.info()
    assert a.id in info
    assert 'epsg:27700' in info
    assert str(a._round_lat()) in info
    assert str(a._round_lon()) in info


def test_add_additional_attributes_to_stops():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    a.add_additional_attributes({'isBlocking': True, 'name': 'Brunswick Place (Stop P)'})

    assert a.name == 'Brunswick Place (Stop P)'
    assert a.isBlocking == True


def test_iterating_through_additional_attribs():
    s = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700', additional_attrib_1='hey',
             additional_attrib_2='what?')
    assert set(s.iter_through_additional_attributes()) == {('additional_attrib_1', 'hey'), ('additional_attrib_2', 'what?')}


def test_stops_equal():
    a = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')
    b = Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')

    assert a == b


def test_stop_already_in_epsg_4326_gives_lat_lon():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')

    assert a.lat == a.x
    assert a.lon == a.y


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


def test_has_linkRefId_with_stop_which_has_linkRefId():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')
    a.add_additional_attributes({'linkRefId': '1234'})
    assert a.has_linkRefId()


def test_has_linkRefId_with_stop_with_missing_linkRefId():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')
    assert not a.has_linkRefId()


def test_has_id_with_stop_with_nice_id():
    a = Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')
    assert a.has_id()


def test_has_id_with_stop_with_bad_id():
    a = Stop(id='', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')
    assert not a.has_id()