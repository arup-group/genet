import os

import lxml
import pytest
from lxml.etree import Element

from genet.core import Network
from genet.use import road_pricing

# paths in use assume we're in the repo's root, so make sure we always are
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(root_dir)


@pytest.fixture
def road_pricing_dtd():
    dtd_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data/road_pricing/roadpricing_v1.dtd"))
    yield lxml.etree.DTD(dtd_path)


@pytest.fixture
def road_pricing_sample_xml():
    sample_xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "test_data/road_pricing/sample_corden_road_pricing.xml"))
    yield lxml.etree.parse(sample_xml_path)


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
    # do we need to test whether the contents of `toll_ids` are indeed part of network `n` ? YES


def test_writes_well_formed_and_valid_road_pricing_xml_file(tmpdir, road_pricing_dtd, road_pricing_sample_xml):
    road_pricing.write_xml(road_pricing_sample_xml.getroot(), tmpdir)

    expected_xml = os.path.join(tmpdir, 'roadpricing-file.xml')
    assert os.path.exists(expected_xml)
    xml_obj = lxml.etree.parse(expected_xml)
    assert road_pricing_dtd.validate(xml_obj), \
        'Doc generated at {} is not valid against DTD due to {}'.format(expected_xml,
                                                                        road_pricing_dtd.error_log.filter_from_errors())


def test_writes_road_pricing_xml_file_with_expected_content(tmpdir, road_pricing_sample_xml):
    road_pricing.write_xml(road_pricing_sample_xml.getroot(), tmpdir)

    expected_xml = os.path.join(tmpdir, 'roadpricing-file.xml')
    assert os.path.exists(expected_xml)

    xml_obj = lxml.etree.parse(expected_xml)
    assert_xml_trees_equal(road_pricing_sample_xml, xml_obj)


def test_builds_valid_xml_tree_from_network_toll_ids(road_pricing_dtd):
    toll_ids = [str(i) for i in range(10)]

    xml_tree = road_pricing.build_tree(toll_ids)

    assert isinstance(xml_tree, lxml.etree._Element)
    assert road_pricing_dtd.validate(xml_tree), \
        'Tree generated at is not valid against DTD due to {}'.format(road_pricing_dtd.error_log.filter_from_errors())


def test_builds_xml_tree_with_correct_content_from_network_toll_ids():
    toll_ids = [str(i) for i in range(10)]

    xml_tree_root = road_pricing.build_tree(toll_ids)

    assert xml_tree_root.tag == 'roadpricing'
    assert xml_tree_root.attrib == {'type': 'cordon', 'name': 'cordon-toll'}
    assert len(xml_tree_root) == 3 # description, links, cost subelements

    descs = xml_tree_root.findall('description')
    assert len(descs) == 1
    assert descs[0].tag == 'description'
    assert descs[0].text == 'A simple cordon toll scheme'

    costs = xml_tree_root.findall('cost')
    assert len(costs) == 1
    assert costs[0].tag == 'cost'
    assert costs[0].attrib == {'start_time': '00:00', 'end_time': '23:59', 'amount': '2.00'}

    links = xml_tree_root.findall('links')
    assert len(links) == 1
    assert links[0].tag == 'links'

    assert len(links[0]) == len(toll_ids)
    for link in links[0]:
        assert link.tag == 'link'
        link_id = link.attrib['id']
        toll_ids.remove(link_id)
    assert len(toll_ids) == 0


###########################################################
# helper functions
###########################################################
def xml_elements_equal(e1, e2):
    if e1.tag != e2.tag: return False
    if e1.text != e2.text: return False
    if e1.tail != e2.tail: return False
    if e1.attrib != e2.attrib: return False
    if len(e1) != len(e2): return False

    return all(xml_elements_equal(c1, c2) for c1, c2 in zip(e1, e2))


def assert_xml_trees_equal(tree1, tree2):
    assert tree1.docinfo.doctype == tree2.docinfo.doctype
    assert tree1.docinfo.root_name == tree2.docinfo.root_name
    assert xml_elements_equal(tree1.getroot(), tree2.getroot())
