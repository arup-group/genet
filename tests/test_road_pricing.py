import json
import os

import lxml
import pandas as pd
import pytest
from lxml.etree import Element
from pandas.testing import assert_frame_equal

from genet.inputs_handler import read
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
    yield read.read_matsim(path_to_network=network_xml_path, epsg='epsg:27700')

@pytest.fixture
def osm_network_snapping(network_object, tmpdir):
    return road_pricing.extract_network_id_from_osm_csv(
        network_object,
        'osm:way:id',
        'tests/test_data/road_pricing/osm_toll_id_ref.csv',
        tmpdir)

@pytest.fixture
def osm_tolls_df():
    return pd.DataFrame({'toll_amount': {0: '1.9', 1: '1.9', 2: '1.9', 3: '1.9', 4: '1.9', 5: '1.9', 6: '1.9', 7: '1.9',
                                  8: '1.9', 9: '1.9', 10: '1.9', 11: '1.9', 12: '1.9', 13: '1.9', 14: '1.9',
                                  15: '1.9', 16: '1.9', 17: '1.9', 18: '1.9', 19: '1.9', 20: '1.9', 21: '1.9',
                                  22: '1.9', 23: '1.9', 24: '1.9', 25: '1.9', 26: '1.9', 27: '1.9', 28: '1.9',
                                  29: '1.9', 30: '1.9', 31: '1.9', 32: '1.9', 33: '1.9', 34: '1.9', 35: '1.9',
                                  36: '1.9', 37: '1.9', 38: '1.9', 39: '1.9', 40: '1.9', 41: '1.9', 42: '1.9',
                                  43: '1.9', 44: '1.9', 45: '1.9', 46: '1.9', 47: '1.9', 48: '1.9', 49: '1.9',
                                  50: '1.9', 51: '1.9', 52: '1.9', 53: '1.9', 54: '1.9', 55: '1.9', 56: '1.9',
                                  57: '1.9', 58: '1.9', 59: '1.9', 60: '1.9', 61: '1.9', 62: '1.9', 63: '1.9',
                                  64: '1.9', 65: '1.9', 66: '1.9', 67: '1.9', 68: '1.9', 69: '1.9', 70: '1.9',
                                  71: '1.9', 72: '1.9', 73: '1.9', 74: '1.9', 75: '1.9', 76: '1.9', 77: '1.9',
                                  78: '1.9', 79: '1.9', 80: '1.9', 81: '1.9', 82: '1.9', 83: '2', 84: '2', 85: '2',
                                  86: '2', 87: '2', 88: '2', 89: '2', 90: '2', 91: '2', 92: '2', 93: '2', 94: '2',
                                  95: '2', 96: '2', 97: '2', 98: '2', 99: '2', 100: '2', 101: '2', 102: '2',
                                  103: '2', 104: '2', 105: '2', 106: '2', 107: '2', 108: '5', 109: '5', 110: '5',
                                  111: '5', 112: '5', 113: '5', 114: '5', 115: '5', 116: '5', 117: '5', 118: '5',
                                  119: '5', 120: '5', 121: '5', 122: '5', 123: '5', 124: '5', 125: '5', 126: '5',
                                  127: '5', 128: '5', 129: '5', 130: '5', 131: '8', 132: '8', 133: '8', 134: '8',
                                  135: '8', 136: '8', 137: '8', 138: '8', 139: '8', 140: '8', 141: '8', 142: '8',
                                  143: '8', 144: '8', 145: '8', 146: '8', 147: '8', 148: '8', 149: '8', 150: '8',
                                  151: '8', 152: '8', 153: '8', 154: '8', 155: '8', 156: '8', 157: '8'},
                  'osm_name': {i: 'noname' for i in range(158)},
                  'toll_id': {i: 'N6_Galway_Ballinasloe' for i in range(158)},
                  'start_time': {0: '00:00', 1: '00:00', 2: '00:00', 3: '00:00', 4: '00:00', 5: '00:00', 6: '00:00',
                                 7: '00:00', 8: '00:00', 9: '00:00', 10: '00:00', 11: '00:00', 12: '00:00',
                                 13: '00:00', 14: '00:00', 15: '00:00', 16: '00:00', 17: '00:00', 18: '00:00',
                                 19: '00:00', 20: '00:00', 21: '00:00', 22: '00:00', 23: '00:00', 24: '00:00',
                                 25: '00:00', 26: '00:00', 27: '00:00', 28: '00:00', 29: '00:00', 30: '00:00',
                                 31: '00:00', 32: '00:00', 33: '00:00', 34: '00:00', 35: '00:00', 36: '00:00',
                                 37: '00:00', 38: '00:00', 39: '00:00', 40: '00:00', 41: '00:00', 42: '00:00',
                                 43: '00:00', 44: '00:00', 45: '00:00', 46: '00:00', 47: '00:00', 48: '00:00',
                                 49: '00:00', 50: '00:00', 51: '00:00', 52: '00:00', 53: '00:00', 54: '00:00',
                                 55: '00:00', 56: '00:00', 57: '00:00', 58: '00:00', 59: '00:00', 60: '00:00',
                                 61: '00:00', 62: '00:00', 63: '00:00', 64: '00:00', 65: '00:00', 66: '00:00',
                                 67: '00:00', 68: '00:00', 69: '00:00', 70: '00:00', 71: '00:00', 72: '00:00',
                                 73: '00:00', 74: '00:00', 75: '00:00', 76: '00:00', 77: '00:00', 78: '00:00',
                                 79: '00:00', 80: '00:00', 81: '00:00', 82: '00:00', 83: '00:00', 84: '00:00',
                                 85: '00:00', 86: '00:00', 87: '00:00', 88: '00:00', 89: '00:00', 90: '00:00',
                                 91: '00:00', 92: '00:00', 93: '00:00', 94: '00:00', 95: '00:00', 96: '00:00',
                                 97: '00:00', 98: '00:00', 99: '00:00', 100: '00:00', 101: '00:00', 102: '00:00',
                                 103: '00:00', 104: '00:00', 105: '00:00', 106: '00:00', 107: '00:00', 108: '08:00',
                                 109: '08:00', 110: '08:00', 111: '08:00', 112: '08:00', 113: '08:00', 114: '08:00',
                                 115: '08:00', 116: '08:00', 117: '08:00', 118: '08:00', 119: '08:00', 120: '08:00',
                                 121: '08:00', 122: '08:00', 123: '08:00', 124: '08:00', 125: '08:00', 126: '08:00',
                                 127: '08:00', 128: '08:00', 129: '08:00', 130: '08:00', 131: '16:00', 132: '16:00',
                                 133: '16:00', 134: '16:00', 135: '16:00', 136: '16:00', 137: '16:00', 138: '16:00',
                                 139: '16:00', 140: '16:00', 141: '16:00', 142: '16:00', 143: '16:00', 144: '16:00',
                                 145: '16:00', 146: '16:00', 147: '16:00', 148: '16:00', 149: '16:00', 150: '16:00',
                                 151: '16:00', 152: '16:00', 153: '16:00', 154: '16:00', 155: '16:00', 156: '16:00',
                                 157: '16:00'},
                  'vehicle_type': {i: 'type2' for i in range(158)},
                  'notes': {i: float('nan') for i in range(158)},
                  'end_time': {0: '23:59', 1: '23:59', 2: '23:59', 3: '23:59', 4: '23:59', 5: '23:59', 6: '23:59',
                               7: '23:59', 8: '23:59', 9: '23:59', 10: '23:59', 11: '23:59', 12: '23:59',
                               13: '23:59', 14: '23:59', 15: '23:59', 16: '23:59', 17: '23:59', 18: '23:59',
                               19: '23:59', 20: '23:59', 21: '23:59', 22: '23:59', 23: '23:59', 24: '23:59',
                               25: '23:59', 26: '23:59', 27: '23:59', 28: '23:59', 29: '23:59', 30: '23:59',
                               31: '23:59', 32: '23:59', 33: '23:59', 34: '23:59', 35: '23:59', 36: '23:59',
                               37: '23:59', 38: '23:59', 39: '23:59', 40: '23:59', 41: '23:59', 42: '23:59',
                               43: '23:59', 44: '23:59', 45: '23:59', 46: '23:59', 47: '23:59', 48: '23:59',
                               49: '23:59', 50: '23:59', 51: '23:59', 52: '23:59', 53: '23:59', 54: '23:59',
                               55: '23:59', 56: '23:59', 57: '23:59', 58: '23:59', 59: '23:59', 60: '23:59',
                               61: '23:59', 62: '23:59', 63: '23:59', 64: '23:59', 65: '23:59', 66: '23:59',
                               67: '23:59', 68: '23:59', 69: '23:59', 70: '23:59', 71: '23:59', 72: '23:59',
                               73: '23:59', 74: '23:59', 75: '23:59', 76: '23:59', 77: '23:59', 78: '23:59',
                               79: '23:59', 80: '23:59', 81: '23:59', 82: '23:59', 83: '07:59', 84: '07:59',
                               85: '07:59', 86: '07:59', 87: '07:59', 88: '07:59', 89: '07:59', 90: '07:59',
                               91: '07:59', 92: '07:59', 93: '07:59', 94: '07:59', 95: '07:59', 96: '07:59',
                               97: '07:59', 98: '07:59', 99: '07:59', 100: '07:59', 101: '07:59', 102: '07:59',
                               103: '07:59', 104: '07:59', 105: '07:59', 106: '07:59', 107: '07:59', 108: '15:59',
                               109: '15:59', 110: '15:59', 111: '15:59', 112: '15:59', 113: '15:59', 114: '15:59',
                               115: '15:59', 116: '15:59', 117: '15:59', 118: '15:59', 119: '15:59', 120: '15:59',
                               121: '15:59', 122: '15:59', 123: '15:59', 124: '15:59', 125: '15:59', 126: '15:59',
                               127: '15:59', 128: '15:59', 129: '15:59', 130: '15:59', 131: '23:59', 132: '23:59',
                               133: '23:59', 134: '23:59', 135: '23:59', 136: '23:59', 137: '23:59', 138: '23:59',
                               139: '23:59', 140: '23:59', 141: '23:59', 142: '23:59', 143: '23:59', 144: '23:59',
                               145: '23:59', 146: '23:59', 147: '23:59', 148: '23:59', 149: '23:59', 150: '23:59',
                               151: '23:59', 152: '23:59', 153: '23:59', 154: '23:59', 155: '23:59', 156: '23:59',
                               157: '23:59'},
                  'network_link_id': {0: '1603', 1: '1604', 2: '1605', 3: '1606', 4: '2309', 5: '2310', 6: '2311',
                                      7: '2312', 8: '2313', 9: '2314', 10: '2315', 11: '2316', 12: '2317',
                                      13: '2318', 14: '2319', 15: '2320', 16: '2321', 17: '2322', 18: '2323',
                                      19: '2324', 20: '2325', 21: '2326', 22: '2327', 23: '2192', 24: '2193',
                                      25: '2194', 26: '5987', 27: '5988', 28: '5989', 29: '5990', 30: '5991',
                                      31: '5992', 32: '5993', 33: '5994', 34: '5995', 35: '5996', 36: '5997',
                                      37: '5998', 38: '5999', 39: '6000', 40: '6001', 41: '6002', 42: '6003',
                                      43: '6004', 44: '6005', 45: '6006', 46: '6007', 47: '5977', 48: '5978',
                                      49: '5979', 50: '5980', 51: '613', 52: '614', 53: '615', 54: '616', 55: '266',
                                      56: '380', 57: '381', 58: '307', 59: '308', 60: '309', 61: '310', 62: '311',
                                      63: '312', 64: '313', 65: '314', 66: '315', 67: '316', 68: '317', 69: '318',
                                      70: '319', 71: '320', 72: '321', 73: '322', 74: '323', 75: '324', 76: '325',
                                      77: '326', 78: '327', 79: '328', 80: '329', 81: '1122', 82: '1123',
                                      83: '1079', 84: '1080', 85: '1081', 86: '1082', 87: '1083', 88: '1084',
                                      89: '1085', 90: '1086', 91: '1087', 92: '1088', 93: '1089', 94: '1090',
                                      95: '1091', 96: '1092', 97: '1093', 98: '1094', 99: '1095', 100: '1096',
                                      101: '1097', 102: '1098', 103: '1099', 104: '4946', 105: '3986', 106: '4725',
                                      107: '4726', 108: '1079', 109: '1080', 110: '1081', 111: '1082', 112: '1083',
                                      113: '1084', 114: '1085', 115: '1086', 116: '1087', 117: '1088', 118: '1089',
                                      119: '1090', 120: '1091', 121: '1092', 122: '1093', 123: '1094', 124: '1095',
                                      125: '1096', 126: '1097', 127: '1098', 128: '1099', 129: '4946', 130: '3986',
                                      131: '4725', 132: '4726', 133: '1079', 134: '1080', 135: '1081', 136: '1082',
                                      137: '1083', 138: '1084', 139: '1085', 140: '1086', 141: '1087', 142: '1088',
                                      143: '1089', 144: '1090', 145: '1091', 146: '1092', 147: '1093', 148: '1094',
                                      149: '1095', 150: '1096', 151: '1097', 152: '1098', 153: '1099', 154: '4946',
                                      155: '3986', 156: '4725', 157: '4726'}}).sort_index(axis=1)


@pytest.fixture
def toll(osm_tolls_df):
    return road_pricing.Toll(osm_tolls_df)


@pytest.fixture
def road_pricing_xml_tree():
    path_csv = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'test_data/road_pricing/osm_tolls_with_network_ids.csv'))
    path_json = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'test_data/road_pricing/osm_to_network_ids.json'))
    xml_tree_root = road_pricing.build_tree_from_csv_json(path_csv, path_json)
    yield xml_tree_root


def test_merging_osm_and_network_snapping(osm_network_snapping, osm_tolls_df):
    osm_df, osm_to_network_dict = osm_network_snapping

    df_tolls = road_pricing.merge_osm_tolls_and_network_snapping(osm_df, osm_to_network_dict)
    assert_frame_equal(
        df_tolls.sort_index(axis=1),
        osm_tolls_df,
        check_dtype=False
    )


def test_instantiating_toll_class_from_osm_inputs(network_object, osm_tolls_df, tmpdir):
    osm_toll = road_pricing.road_pricing_from_osm(
        network_object,
        'osm:way:id',
        'tests/test_data/road_pricing/osm_toll_id_ref.csv',
        tmpdir
    )
    assert_frame_equal(
        osm_toll.df_tolls.sort_index(axis=1),
        osm_tolls_df,
        check_dtype=False
    )
    assert isinstance(osm_toll, road_pricing.Toll)


def test_saving_toll_to_csv_produces_correct_csv(toll, osm_tolls_df, tmpdir):
    expected_csv = os.path.join(tmpdir, 'road_pricing.csv')
    assert not os.path.exists(expected_csv)
    toll.write_to_csv(tmpdir)
    assert os.path.exists(expected_csv)
    df_from_csv = pd.read_csv(expected_csv, dtype=str)
    assert_frame_equal(
        df_from_csv.sort_index(axis=1),
        osm_tolls_df,
        check_dtype=False
    )


def test_saving_toll_to_xml_produces_xml_file(toll, tmpdir):
    # the content of the file is tested elsewhere
    expected_xml = os.path.join(tmpdir, 'roadpricing-file.xml')
    assert not os.path.exists(expected_xml)
    toll.write_to_xml(tmpdir)
    assert os.path.exists(expected_xml)


def test_saving_toll_to_xml_with_missing_toll_ids_produces_xml_file(toll, tmpdir):
    toll.df_tolls = toll.df_tolls.drop('toll_id', axis=1)
    assert not 'toll_id' in toll.df_tolls.columns
    # the content of the file is tested elsewhere
    expected_xml = os.path.join(tmpdir, 'roadpricing-file.xml')
    assert not os.path.exists(expected_xml)
    toll.write_to_xml(tmpdir)
    assert os.path.exists(expected_xml)


def test_building_tree_where_no_links_repeat(tmpdir):
    path_json = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'test_data/road_pricing/osm_to_network_ids_no_link_repeat.json'))
    path_csv = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'test_data/road_pricing/osm_tolls_with_network_ids_no_link_overlap.csv'))
    xml_tree_root = road_pricing.build_tree_from_csv_json(
        path_csv, path_json,
        toll_type='cordon', toll_scheme_name='cordon-toll', toll_description='A simple cordon toll scheme')
    road_pricing.write_xml(xml_tree_root, tmpdir)

    expected_xml = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'test_data/road_pricing/roadpricing-file_no_link_repeat.xml'))
    expected_xml_obj = lxml.etree.parse(expected_xml)
    generated_xml_obj = lxml.etree.parse(os.path.join(tmpdir, 'roadpricing-file.xml'))
    assert_xml_trees_equal(generated_xml_obj, expected_xml_obj)


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
    assert road_pricing_xml_tree.attrib == {'type': 'link', 'name': 'simple-toll'}
    assert len(road_pricing_xml_tree) == 2  # description, links

    descs = road_pricing_xml_tree.findall('description')
    assert len(descs) == 1
    assert descs[0].tag == 'description'
    assert descs[0].text == 'A simple toll scheme'

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
