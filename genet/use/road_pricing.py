import os
import json
import logging
import pandas as pd
from lxml import etree as et
from lxml.etree import Element, SubElement, Comment
from tqdm import tqdm
from genet.utils import graph_operations


def extract_network_id_from_osm_csv(network, attribute_name, osm_csv_path, outpath):
    '''Parse a Network() object and find edges whose
    ['attributes'][attribute_name]['text'] is present in a list of OSM way ids
    :param network: a Network() object with attribute_name tags
    :param attribute_name: a string corresponding to the name of the link attribute of interest
    :param osm_csv_path: path to a .csv config file where OSM way ids are stored in column `osm_ids`
    :param outpath: path to a folder
    :return: None, but will write .csv and .json files to `outpath` location
    '''

    osm_df = pd.read_csv(osm_csv_path, dtype=str)
    osm_df['network_id'] = pd.Series(dtype=str)

    target_osm_ids = set(osm_df['osm_ids'].values)

    osm_to_network_dict = {}

    with tqdm(total=len(target_osm_ids)) as pbar:
        for target_id in target_osm_ids:
            links = graph_operations.extract_links_on_edge_attributes(
                    network,
                    conditions={'attributes': {attribute_name: {'text': target_id}}},
                )

            # links is now a list of strings
            if len(links) > 0:
                # store list of links in dictionary
                osm_to_network_dict[target_id] = links
                # mark the OSM id as "matched" in the dataframe
                osm_df.loc[osm_df['osm_ids'] == target_id, 'network_id'] = True
            else:
                # mark the OSM id as "ummatched" in the dataframe
                osm_df.loc[osm_df['osm_ids'] == target_id, 'network_id'] = False

            pbar.update(1)

    # check whether some of our OSM ids were not found
    unmatched_osm_df = osm_df[osm_df['network_id'] == 'no']
    if unmatched_osm_df.shape[0] > 0:
        # print unmatched ids
        logging.info('these OSM way ids did not find a match in the network.xml')
        logging.info(unmatched_osm_df['osm_ids'].values)
    # write dataframe as .csv and dictionary as .json
    osm_df.to_csv(os.path.join(outpath, 'osm_tolls_with_network_ids.csv'), index=False)
    with open(os.path.join(outpath, 'osm_to_network_ids.json'), 'w') as write_file:
        json.dump(osm_to_network_dict, write_file)


def write_xml(root, path):
    '''
    Write XML config for MATSim Road Pricing a given folder location.
    :param root: an 'lxml.etree._Element' object corresponding to the root of an XML tree
    :param path: location of destination folder for Road Pricing config
    :return: None
    '''
    tree = et.tostring(root,
                       pretty_print=True,
                       xml_declaration=False,
                       encoding='UTF-8')
    with open(os.path.join(path, 'roadpricing-file.xml'), 'wb') as file:
        file.write(b'<?xml version="1.0" ?>\n')
        file.write(b'<!DOCTYPE roadpricing SYSTEM "http://www.matsim.org/files/dtd/roadpricing_v1.dtd">\n')
        file.write(tree)


def build_tree_from_csv_json(csv_input, json_input):
    '''
    Build XML config for MATSim Road Pricing from .csv input
    :param csv_input:
    :return: an 'lxml.etree._Element' object
    '''

    roadpricing = Element("roadpricing", type="cordon", name="cordon-toll")
    description = SubElement(roadpricing, "description")
    description.text = "A simple cordon toll scheme"

    links = SubElement(roadpricing, "links")

    # CSV input
    tolled_links_df = pd.read_csv(csv_input, dtype={'osm_ids': str})
    # make sure all links from same toll are grouped together:
    tolled_links_df = tolled_links_df.sort_values(by='osm_refs')
    # remove the links whose osm_id were not matched to network_ids ('network_id' column is boolean)
    tolled_links_df = tolled_links_df[tolled_links_df['network_id']]

    # Time-of-day pricing:
    # links with multiple tolling amounts throughout the day appear as multiple rows in the .csv config
    # links with uniform pricing throughout the day appear only once in .csv config
    links_repeat = pd.concat(g for _, g in tolled_links_df.groupby('osm_ids') if len(g) > 1)
    links_no_repeat = tolled_links_df[~tolled_links_df.index.isin(links_repeat.index)]

    # JSON input
    with open(json_input, 'r') as f:
        osm_id_to_network_id_dict = json.load(f)

    # list to keep track of which Toll names we added as comments
    commented_tolls = []

    # links without time-of-day pricing:
    for index, row in links_no_repeat.iterrows():

        if str(row['osm_refs']) not in commented_tolls:
            links.append(Comment(' === '+str(row['osm_refs'])+' === '))
            commented_tolls.append(str(row['osm_refs']))

        # from the JSON input, obtain all network_ids that match this row's specific osm_id
        list_of_network_ids = osm_id_to_network_id_dict[row['osm_ids']]
        # network link in list_of_network_ids is matched with 1 row of links_no_repeat
        for net_id in list_of_network_ids:
            link = SubElement(links, "link", id=str(net_id))
            SubElement(link, "cost", start_time=str(row['start_time']),
                       end_time=str(row['end_time']), amount=str(row['toll_amount']))

    # links with time-of-day pricing:
    # get unique ids of these links and iterate through them
    unique_repeated_ids = links_repeat['osm_ids'].unique()
    for link_id in unique_repeated_ids:

        link_time_of_day_df = links_repeat[links_repeat['osm_ids'] == link_id]

        link_ref = link_time_of_day_df['osm_refs'].unique()[0]
        if link_ref not in commented_tolls:
            links.append(Comment(' === '+str(link_ref)+' === '))
            commented_tolls.append(str(link_ref))

        # from the JSON input, obtain all network_ids that match this row's specific osm_id
        list_of_network_ids = osm_id_to_network_id_dict[link_id]
        # each network link in list_of_network_ids is now matched with multiple rows of link_time_of_day_df
        for net_id in list_of_network_ids:
            link = SubElement(links, "link", id=str(net_id))
            for index, row in link_time_of_day_df.iterrows():
                SubElement(link, "cost", start_time=str(row['start_time']),
                           end_time=str(row['end_time']), amount=str(row['toll_amount']))

    return roadpricing
