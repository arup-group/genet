import os
import json
import lxml
from lxml.etree import Element
import pandas as pd
import pytest

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
                                                   "test_data/road_pricing/sample_cordon_road_pricing.xml"))
    yield lxml.etree.parse(sample_xml_path)

@pytest.fixture
def network_object():
    network_xml_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "test_data/road_pricing/network.xml"))
    n = Network(epsg='epsg:27700')
    n.read_matsim_network(network_xml_path)
    yield n

@pytest.fixture
def road_pricing_xml_tree():
    path_csv = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'test_data/road_pricing/osm_tolls_with_network_ids.csv'))
    path_json = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'test_data/road_pricing/osm_to_network_ids.json'))
    xml_tree_root = road_pricing.build_tree_from_csv_json(path_csv, path_json)
    yield xml_tree_root

def test_extract_network_id_from_osm_csv(tmpdir,
                                         network_object,
                                         attribute_name = 'osm:way:id',
                                         path_osm_csv = 'tests/test_data/road_pricing/osm_toll_id_ref.csv'
                                         ):

    road_pricing.extract_network_id_from_osm_csv(network_object,attribute_name, path_osm_csv, tmpdir)
    # check that returns .csv and .json files
    expected_csv_path = os.path.join(tmpdir, 'osm_tolls_with_network_ids.csv')
    expected_json_path = os.path.join(tmpdir, 'osm_to_network_ids.json')
    assert os.path.exists(expected_csv_path)
    assert os.path.exists(expected_json_path)
    # check that the files are non-empty
    expected_csv = pd.read_csv(expected_csv_path)
    with open(expected_json_path, 'r') as f:
        expected_json = json.load(f)
    assert expected_csv.shape[0] > 0
    assert (len(expected_json.keys()) > 0) and (len(expected_json.values()) > 0)
    # check that the relevant column of the .csv contains the expected values
    assert set(expected_csv['network_id'].unique()) == set([False, True])
    # check that the contents of the .json as expected
    test_json_path = 'tests/test_data/road_pricing/osm_to_network_ids.json'
    with open(test_json_path, 'r') as f:
        test_json = json.load(f)
    assert expected_json == test_json


def test_builds_valid_xml_tree_from_csv_json(road_pricing_dtd, road_pricing_xml_tree):
    assert isinstance(road_pricing_xml_tree, lxml.etree._Element)
    assert road_pricing_dtd.validate(road_pricing_xml_tree), \
        'Tree generated at is not valid against DTD due to {}'.format(road_pricing_dtd.error_log.filter_from_errors())


def test_builds_xml_tree_with_correct_content_from_csv_json(road_pricing_xml_tree):
    path_json = 'tests/test_data/road_pricing/osm_to_network_ids.json'

    assert road_pricing_xml_tree.tag == 'roadpricing'
    assert road_pricing_xml_tree.attrib == {'type': 'cordon', 'name': 'cordon-toll'}
    assert len(road_pricing_xml_tree) == 2  # description, links

    descs = road_pricing_xml_tree.findall('description')
    assert len(descs) == 1
    assert descs[0].tag == 'description'
    assert descs[0].text == 'A simple cordon toll scheme'

    costs = road_pricing_xml_tree.xpath('//cost')
    assert len(costs) == 158
    for cost in costs:
        assert cost.tag == 'cost'
        assert cost.attrib.keys() == ['start_time', 'end_time', 'amount']

    links = road_pricing_xml_tree.findall('links')
    assert len(links) == 1
    assert links[0].tag == 'links'

    with open(path_json, 'r') as f:
        test_json = json.load(f)
    all_network_ids = [item for sublist in test_json.values() for item in sublist]

    assert len(road_pricing_xml_tree.xpath('//link')) == len(all_network_ids)
    for link in road_pricing_xml_tree.xpath('//link'):
        assert link.tag == 'link'
        link_id = link.attrib['id']
        all_network_ids.remove(link_id)
    assert len(all_network_ids) == 0


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
