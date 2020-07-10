import os
import json
import pandas as pd
from lxml import etree as et
from lxml.etree import Element, SubElement, Comment
from tqdm import tqdm

from genet.utils import graph_operations


# Below function should be deprecated - possibly replaced by an XML parser ?

# def extract_toll_ways_from_opl(path_opl):
#     '''
#     Given a .osm.opl file, extract the ids of toll ways
#     :param path_opl: path to the .osm.opl file
#     :return: list of OSM way ids matching criteria (str)
#     '''
#     # parse .osm.opl contents
#     with open(path_opl, 'r') as f:
#         contents = [line.rstrip('\n') for line in f]
#     # extract all OSM ways (lines starting with 'w')
#     ways = [line for line in contents if line[0] == 'w']

#     # extract toll ways from above OSM ways
#     toll_ways = []
#     with tqdm(total=len(ways)) as pbar:
#         for way in ways:
#             # below conditions are the result of iterations on Ireland OSM
#             # for another location, some unwanted ways could still persist
#             if all(['toll=yes' in way,
#                     'ferry' not in way,
#                     'highway=service' not in way,
#                     'highway=unclassified' not in way,
#                     'motor_vehicle=no' not in way,
#                     'access=private' not in way,
#                     'access=no' not in way]):
#                 toll_ways.append(way)
#             pbar.update(1)

#     # extract ids from toll ways
#     toll_ids = [item.split(' ')[0] for item in toll_ways]
#     # summary for user
#     print('{} toll ways extracted from {}'.format(len(toll_ids), path_opl))

#     return toll_ids

# #  user should check that they are happy with links (osmium getid - QGIS - OSM layer)
# # hence why we provide write_toll_ids() and read_toll_ids(), as user may
# # add some ids manually


def write_toll_ids(toll_ids, outpath):
    '''
    Given a list of way ids, write them to a file named 'toll_ids' where each is
    on a separate line. Such files can be used to subset a .osm.pbf with osmium
    e.g. `osmium getid -i toll_ids -r input.osm.pbf -o tolls.osm.pbf`
    :param toll_ids: list of way ids (str)
    :param outpath: path to destination folder
    :return: write a list of way ids e.g. `w123456` (str)

    the reason we are keeping the 'w' while writing the ids, is that they are
    required by the osmium command detailed above
    '''
    with open(os.path.join(outpath, 'toll_ids'), 'w') as f:
        for item in toll_ids:
            temp = item
            f.write("%s\n" % temp)


def read_toll_ids(path):
    '''
    Read a list of OSM way ids
    :param path: path to folder
    :return: a list of OSM way ids (without the `w` prefix) (str)
    '''
    with open(path, 'r') as f:
        osm_way_ids = [line.rstrip('\n') for line in f]
    # remove the `w` in front of each id number if present
    if osm_way_ids[0][0] == 'w':
        osm_way_ids = [item.split('w')[1] for item in osm_way_ids]
    # remove duplicates
    osm_way_ids = list(set(osm_way_ids))

    return osm_way_ids


def extract_network_id_from_osm_id(network, osm_way_ids):
    '''
    Parse a Network() object and find edges whose
    ['attributes']['osm:way:id']['text'] is present in osm_way_ids
    :param network: a Network() object with 'osm:way:id'
    :param osm_way_ids: a list of OSM way ids (without the `w` prefix) (str)
    :return: a list of network edge ids (str)
    '''

    # a notion of progress bar could be nice but it's tricky to implement here
    # as we don't know how long the loop will have to run for (see break clause)
    network_toll_ids = []
    edge_osm_ids = []

    for link_id, link_attribs in network.links():
        if 'attributes' in link_attribs.keys():
            edge_osm_id = link_attribs['attributes']['osm:way:id']['text']
            if type(edge_osm_id) is str:
                if edge_osm_id in osm_way_ids:
                    network_toll_ids.append(link_id)
                    edge_osm_ids.append(edge_osm_id)
            else:
                continue

        edge_osm_ids = list(set(edge_osm_ids))
        if edge_osm_ids == osm_way_ids:
            break

    print(len(network_toll_ids), ' network ids identified as matching OSM toll ids')
    print(len(osm_way_ids) - len(edge_osm_ids), ' OSM toll ids not found in network.xml')
    missing_osm_ways = [item for item in osm_way_ids if item not in edge_osm_ids]
    print('Unfound OSM ids are: ')
    print(missing_osm_ways)

    return network_toll_ids


def extract_network_id_from_osm_csv(network, attribute_name, osm_csv_path, outpath):
    '''Parse a Network() object and find edges whose
    ['attributes'][attribute_name]['text'] is present in a list of OSM way ids
    :param network: a Network() object with attribute_name tags
    :param attribute_name: a string corresponding to the name of the link attribute of interest
    :param osm_csv_path: path to a .csv config file where OSM way ids are stored in column `osm_ids`
    :param outpath: path to a .csv file to be written
    :return: None, but will write .csv and .json files to `outpath` location
    '''

    osm_df = pd.read_csv(osm_csv_path, dtype=str)
    osm_df['network_id'] = pd.Series(dtype=str)

    target_osm_ids = set(osm_df['osm_ids'].values)

    osm_to_network_dict = {}

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
            temp_index = osm_df[osm_df['osm_ids'] == target_id].index
            osm_df.loc[temp_index, 'network_id'] = 'yes'
        else:
            # mark the OSM id as "ummatched" in the dataframe
            temp_index = osm_df[osm_df['osm_ids'] == target_id].index
            osm_df.loc[temp_index, 'network_id'] = 'no'

    # check whether some of our OSM ids were not found
    unmatched_osm_df = osm_df[osm_df['network_id'] == 'no']
    if unmatched_osm_df.shape[0] > 0:
        # print unmatched ids
        print('these OSM way ids did not find a match in the network.xml')
        print(unmatched_osm_df['osm_ids'].values)
        # # remove the corresponding rows from the dataframe
        # print('these OSM way ids have been removed from the output saved at '+outpath)
        # osm_df = osm_df.drop(osm_df[osm_df['network_id'].isnull()].index)
    
    # write dataframe as .csv and dictionary as .json
    osm_df.to_csv(os.path.join(outpath, 'osm_tolls_with_network_ids.csv'), index=False)
    with open(os.path.join(outpath, 'osm_to_network_ids.json'), 'w') as write_file:
        json.dump(osm_to_network_dict, write_file)


# def extract_network_id_from_osm_csv(network, osm_csv_path, outpath):
#     '''Parse a Network() object and find edges whose
#     ['attributes']['osm:way:id']['text'] is present in a list of OSM way ids
#     :param network: a Network() object with 'osm:way:id'
#     :param osm_csv_path: path to a .csv config file where OSM way ids are stored in column `osm_ids`
#     :param outpath: path to a .csv file to be written
#     :return: None, but will write .csv file to `outpath` location
#     '''
#     osm_df = pd.read_csv(osm_csv_path, dtype=str)
#     # for each row in osm_df, we want to add a values 'network_id'
#     osm_df['network_id'] = pd.Series(dtype=str)

#     edge_osm_ids = set()
#     osm_ids = set(osm_df['osm_ids'].values)

#     for link_id, link_attribs in network.links():
#         if 'attributes' in link_attribs.keys():
#             # extract the OSM id associated to that Network link
#             # edge_osm_id = link_attribs['attributes']['osm:way:id']['text']
#             edge_osm_id = link_attribs['attributes']['osm:osmid']['text']
#             if str(edge_osm_id) in osm_ids:
#                 # if the OSM id associated to that Network link is one of the OSM toll ways we are interested in
#                 # then we extract the indices of all rows in the .csv where that OSM toll way appears
#                 temp_index = osm_df[osm_df['osm_ids'] == edge_osm_id].index
#                 if len(temp_index) > 1:
#                     osm_df.loc[temp_index, 'network_id'] = link_id
#                 else:
#                     temp_index = temp_index[0]
#                     osm_df.loc[temp_index, 'network_id'] = link_id

#                 edge_osm_ids.update(edge_osm_id)
#             else:
#                 continue

#         edge_osm_ids = set(edge_osm_ids)
#         if edge_osm_ids == osm_ids:
#             # if we have found all the OSM way ids, no need to go through the rest of the Network
#             break
#         # else:
#         #     print(len(osm_ids) - len(edge_osm_ids), ' OSM ways still to be found.')

#     # check whether some of our OSM ids were not found
#     unmatched_osm_df = osm_df[osm_df['network_id'].isnull()]
#     if unmatched_osm_df.shape[0] > 0:
#         # print unmatched ids
#         print('these OSM way ids did not find a match in the network.xml')
#         print(unmatched_osm_df['osm_ids'].values)
#         # remove the corresponding rows from the dataframe
#         print('these OSM way ids have been removed from the output saved at '+outpath)
#         osm_df = osm_df.drop(osm_df[osm_df['network_id'].isnull()].index)
#     # write back to .csv
#     osm_df.to_csv(outpath, index=False)


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


def build_tree(network_toll_ids):
    '''
    Build XML config for MATSim Road Pricing from given network link ids.
    :param network_toll_ids: a list of network edge ids (str)
    :return: an 'lxml.etree._Element' object
    '''
    # creat ETree root
    roadpricing = Element("roadpricing", type="cordon", name="cordon-toll")
    # <description
    description = SubElement(roadpricing, "description")
    description.text = "A simple cordon toll scheme"

    links = SubElement(roadpricing, "links")

    for link_id in network_toll_ids:
        SubElement(links, "link", id=link_id)

    # apply same cost to all links, regardless of vehicle type
    SubElement(roadpricing, "cost", start_time="00:00", end_time="23:59", amount="2.00")

    return roadpricing


def build_tree_from_csv(csv_input):
    '''
    Build XML config for MATSim Road Pricing from .csv input
    :param csv_input:
    :return: an 'lxml.etree._Element' object
    '''

    # creat ETree root
    roadpricing = Element("roadpricing", type="cordon", name="cordon-toll")
    # description
    description = SubElement(roadpricing, "description")
    description.text = "A simple cordon toll scheme"

    links = SubElement(roadpricing, "links")

    tolled_links_df = pd.read_csv(csv_input)
    # make sure all links from same toll are grouped together:
    tolled_links_df = tolled_links_df.sort_values(by='osm_refs')

    # remove references to 'DPT', we will hard-code its paramters below
    links_DPT = list(tolled_links_df[tolled_links_df['osm_refs'] == 'DPT']['network_id'].values)
    tolled_links_df = tolled_links_df[tolled_links_df['osm_refs'] != 'DPT']

    commented_tolls = []  # list to keep track of which Toll names we added as comments

    # all other tolls
    for index, row in tolled_links_df.iterrows():

        if str(row['osm_refs']) not in commented_tolls:
            links.append(Comment(' === '+str(row['osm_refs'])+' === '))
            commented_tolls.append(str(row['osm_refs']))

        link = SubElement(links, "link", id=str(row['network_id']))
        SubElement(link, "cost", start_time=str(row['start_time']),
                   end_time=str(row['end_time']), amount=str(row['toll_amount'])
                   )
    # DPT
    links.append(Comment(' === '+'DPT'+' === '))

    for link_id in links_DPT:

        link = SubElement(links, "link", id=str(link_id))
        SubElement(link, "cost", start_time="00:00", end_time="05:59", amount="3.00")
        SubElement(link, "cost", start_time="06:00", end_time="09:59", amount="10.00")
        SubElement(link, "cost", start_time="10:00", end_time="15:59", amount="3.00")
        SubElement(link, "cost", start_time="16:00", end_time="18:59", amount="10.00")
        SubElement(link, "cost", start_time="19:00", end_time="23:59", amount="3.00")

    return roadpricing
