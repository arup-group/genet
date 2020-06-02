import os
from lxml.etree import Element

from genet.core import Network
from genet.use import road_pricing


def test_writes_toll_ids_to_expected_location(tmpdir):
    toll_ids = [str(i) for i in range(10)]
    road_pricing.write_toll_ids(toll_ids, tmpdir)

    expected_toll_id_file = os.path.join(tmpdir, 'toll_ids')
    assert os.path.exists(expected_toll_id_file)
    with open(expected_toll_id_file) as toll_file:
        lines = toll_file.readlines()
        assert len(lines) == len(toll_ids)
        for i, toll_id in enumerate(toll_ids):
            assert lines[i] == "{}\n".format(toll_id)


def test_read_toll_ids(path='tests/test_data/road_pricing/test_osm_toll_ids'):
    toll_ids = road_pricing.read_toll_ids(path)
    # check that returns a list
    assert isinstance(toll_ids, list)
    # check that all items in list are strings and don't start with 'w'
    for item in toll_ids:
        assert isinstance(item, str)
        assert item[0] != 'w'


def test_extract_toll_ways_from_opl(path_opl='tests/test_data/road_pricing/test.osm.opl'):
    toll_ids = road_pricing.extract_toll_ways_from_opl(path_opl)
    # check that returns a list
    assert isinstance(toll_ids, list)
    # check that all items in list are strings and start with 'w'
    for item in toll_ids:
        assert isinstance(item, str)
        assert item[0]=='w'


def test_extract_network_id_from_osm_id(path_network='tests/test_data/road_pricing/network.xml',
                                        path_osm_way_ids='tests/test_data/road_pricing/test_osm_toll_ids'):
    n = Network()
    n.read_matsim_network(path_network, epsg='epsg:27700')

    osm_way_ids = road_pricing.read_toll_ids(path_osm_way_ids)

    toll_ids = road_pricing.extract_network_id_from_osm_id(n, osm_way_ids)
    # check that returns a list
    assert isinstance(toll_ids, list)
    # check that the list is non-empty
    assert len(toll_ids) > 0
    # check that all items in list are strings
    for item in toll_ids:
        assert isinstance(item, str)
    # do we need to test whether the contents of `toll_ids` are indeed part of network `n` ?



# def test_write_xml(tmpdir):
#     root = Element("root", type="cordon", name="cordon-toll")
#     road_pricing.write_xml(root, tmpdir)

#     expected_xml = os.path.join(tmpdir, 'roadpricing-file.xml')
#     assert os.path.exists(expected_xml)

#     # parse xml and check:
#     # 1st line <?xml version="1.0" ?>
#     # 2nd line <!DOCTYPE roadpricing SYSTEM "http://matsim.org/files/dtd/roadpricing_v1.dtd"
#     # root cordon cordon-toll



# def test_build_tree(network_toll_ids='tests/test_data/road_pricing/network_toll_ids',
#                     xml_schema_dtd='tests/test_data/road_pricing/roadpricing_v1.dtd'):
#     root = road_pricing.build_tree(network_toll_ids)

#     # check type of root object
#     assert isinstance(root, ???)
#     # check DTD !!!
#     assert xml_schema_dtd
#     # do we need to check that links in `network_toll_ids` are present under <links> ?