from genet import Stop, Route
from genet.modify import schedule
from tests.fixtures import assert_semantically_equal


def test_reproj():
    routes = [Route(
                route_short_name='12',
                mode='bus',
                stops=[Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
                       Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')],
                route=['1'],
                trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                arrival_offsets=['00:00:00', '00:02:00'],
                departure_offsets=['00:00:00', '00:02:00']
            )]
    reprojected_routes = schedule.reproj(routes, 'epsg:27700', 'epsg:4326')

    correct_x_y = {'x': 51.52393050617373, 'y': -0.14967658860132668}
    stop_1 = reprojected_routes[0].stops[0]
    assert_semantically_equal({'x': stop_1.x, 'y': stop_1.y}, correct_x_y)
    stop_2 = reprojected_routes[0].stops[1]
    assert_semantically_equal({'x': stop_2.x, 'y': stop_2.y}, correct_x_y)
