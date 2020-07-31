import s2sphere
from genet.utils import spatial
from tests.fixtures import *


def test_decode_polyline_to_s2_points():
    s2_list = spatial.decode_polyline_to_s2_points('ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ')
    assert s2_list == [5221390692712666847, 5221390692823346465, 5221390693003336431, 5221390693005239025,
                        5221390693026247929, 5221390693047976565, 5221390685911708669, 5221390685910265239,
                        5221390683049158953, 5221390683157459293, 5221390683301132839, 5221390683277381201,
                        5221390683276573369, 5221390683274586647]


def test_compute_average_proximity_to_polyline():
    poly_1 = 'ahmyHzvYkCvCuCdDcBrB'
    poly_2 = 'ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ'
    dist = spatial.compute_average_proximity_to_polyline(poly_1, poly_2)
    assert round(dist, 5) == round(1.306345084680333, 5)


def test_compute_average_proximity_to_polyline_when_they_are_the_same_line():
    poly_1 = 'ahmyHzvYkCvCuCdDcBrB'
    poly_2 = 'ahmyHzvYkCvCuCdDcBrB'
    dist = spatial.compute_average_proximity_to_polyline(poly_1, poly_2)
    assert dist == 0


def test_grabs_point_indexes_from_s2(mocker):
    mocker.patch.object(s2sphere.CellId, 'from_lat_lng', return_value=s2sphere.CellId(id_=123456789))
    point_index = spatial.grab_index_s2(53.483959, -2.244644)

    assert point_index == 123456789
    s2sphere.CellId.from_lat_lng.assert_called_once_with(s2sphere.LatLng.from_degrees(53.483959, -2.244644))


def test_delegates_distance_between_points_query_to_s2(mocker):
    mocker.patch.object(s2sphere.LatLng, 'get_distance', return_value=s2sphere.Angle(radians=3))
    distance = spatial.distance_between_s2cellids(
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.483959, -2.244644)),
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.583959, -2.344644)))

    earth_radius_metres = 6371008.8
    assert distance == 3 * earth_radius_metres
    s2sphere.LatLng.get_distance.assert_called_once()


def test_delegates_distance_between_int_points_query_to_s2(mocker):
    mocker.patch.object(s2sphere.LatLng, 'get_distance', return_value=s2sphere.Angle(radians=3))
    distance = spatial.distance_between_s2cellids(
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.483959, -2.244644)).id(),
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.583959, -2.344644)).id())

    earth_radius_metres = 6371008.8
    assert distance == 3 * earth_radius_metres
    s2sphere.LatLng.get_distance.assert_called_once()


def test_create_subsetting_area_with_two_cells_check_distance_from_centre_is_roughly_the_same_for_both():
    cap = spatial.create_subsetting_area([5221390301001263407, 5221390302696205321])
    cap_centre = s2sphere.CellId.from_point(cap.axis())
    dist_1 = cap_centre.to_lat_lng().get_distance(s2sphere.CellId(5221390301001263407).to_lat_lng()).radians
    dist_2 = cap_centre.to_lat_lng().get_distance(s2sphere.CellId(5221390302696205321).to_lat_lng()).radians
    assert cap.contains(s2sphere.CellId(5221390301001263407).to_point())
    assert cap.contains(s2sphere.CellId(5221390302696205321).to_point())
    assert round(dist_1, 8) == round(dist_2, 8)


def test_SpatialTree_adds_a_link():
    link, link_attrib = ('1', {
        'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
        's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
        'freespeed': "4.166666666666667", 'capacity': "600.0", 'permlanes': "1.0", 'oneway': "1",
        'modes': ['subway,metro', 'walk', 'car'], 'attributes': {
            'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
            'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
            'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
            'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}
        }})

    spatial_tree = spatial.SpatialTree([(link, link_attrib)])

    assert list(spatial_tree.edges) == [(5221390298638188544, '1'), (5764607523034234880, 5221642292959379456),
                                        (5221642292959379456, 5221378410168713216),
                                        (5221378410168713216, 5221390298638188544), (0, 5764607523034234880)]
    for node, node_attrib in list(spatial_tree.nodes(data=True)):
        assert_semantically_equal(node_attrib, link_attrib)


def test_SpatialTree_combines_link_list_attribs():
    spatial_tree = spatial.SpatialTree()

    links = [('1', {'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['subway,metro', 'walk', 'car']}),
             ('2', {'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['bike', 'walk', 'piggy_back']})]

    spatial_tree.add_links(links=links)

    assert_semantically_equal(list(spatial_tree.edges), [(5221390298638188544, '1'), (5221390298638188544, '2'),
                                                         (5764607523034234880, 5221642292959379456),
                                                         (5221642292959379456, 5221378410168713216),
                                                         (5221378410168713216, 5221390298638188544),
                                                         (0, 5764607523034234880)])
    for node, node_attrib in list(spatial_tree.nodes(data=True)):
        if node not in ['1', '2']:
            assert set(node_attrib['modes']) == {'subway,metro', 'car', 'bike', 'walk', 'piggy_back'}
        elif node == '1':
            assert set(node_attrib['modes']) == {'subway,metro', 'walk', 'car'}
        elif node == '2':
            assert set(node_attrib['modes']) == {'bike', 'walk', 'piggy_back'}


def test_SpatialTree_leaves():
    spatial_tree = spatial.SpatialTree()
    links = [('1', {'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['subway,metro', 'walk', 'car']}),
             ('2', {'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['bike', 'walk', 'piggy_back']})]
    spatial_tree.add_links(links=links)

    assert spatial_tree.leaves() == ['1', '2']


def test_SpatialTree_roots():
    spatial_tree = spatial.SpatialTree()
    links = [('1', {'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['subway,metro', 'walk', 'car']}),
             ('2', {'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['bike', 'walk', 'piggy_back']})]
    spatial_tree.add_links(links=links)

    assert spatial_tree.roots() == [0]


def test_SpatialTree_closest_edges():
    spatial_tree = spatial.SpatialTree()
    links = [('1', {'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['subway,metro', 'walk', 'car']}),
             ('2', {'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
                    'modes': ['bike', 'walk', 'piggy_back']})
             ]
    spatial_tree.add_links(links=links)

    assert_semantically_equal(spatial_tree.find_closest_links(5221390301001263407, 30), ['1', '2'])
