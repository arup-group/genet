import json
import logging
import os

import numpy as np
import pandas as pd
from lxml import etree as et
from lxml.etree import Element, SubElement, Comment
from tqdm import tqdm


class Toll:
    def __init__(self, df_tolls: pd.DataFrame = None):
        if df_tolls is None:
            self.df_tolls = pd.DataFrame(
                columns=[
                    'toll_id',  # optional, unique ID of the toll, based off OSM ref if applicable
                    'network_link_id',  # network link ID to be charged
                    'vehicle_type',  # optional, type of vehicle, does not persist to MATSim road pricing xml file
                    'toll_amount',  # cost to travel on that link
                    'start_time',  # start time for the toll
                    'end_time',  # end time for the toll
                    'osm_name',  # optional, if derived from OSM, human readable name of the road
                    'notes'  # optional, user notes
                ]
            )
        else:
            self.df_tolls = df_tolls

    def write_to_csv(self, output_dir, filename='road_pricing.csv'):
        """
        Exports all tolls to csv file
        :param output_dir: path to folder to receive the file
        :return: None
        """
        self.df_tolls.to_csv(os.path.join(output_dir, filename), index=False)

    def write_to_xml(self, output_dir, filename='roadpricing-file.xml', toll_type='link',
                     toll_scheme_name='simple-toll', toll_description='A simple toll scheme'):
        """
        Write toll to MATSim xml file
        :param output_dir: path to folder to receive the file
        :param toll_type: default 'link', other supported MATSim toll types: 'distance', 'cordon', 'area',
            more info: https://www.matsim.org/apidocs/core/0.3.0/org/matsim/roadpricing/package-summary.html
        :param toll_scheme_name: name to pass to xml file, useful for identifying multiple toll schemes
        :param toll_description: additional description of the toll to pass to the xml file
        :return: None
        """
        xml_tree = build_tree(
            self.df_tolls, toll_type=toll_type, toll_scheme_name=toll_scheme_name, toll_description=toll_description)
        write_xml(xml_tree, output_dir, filename=filename)


def road_pricing_from_osm(network, attribute_name, osm_csv_path, outpath):
    """
    Instantiates a Toll object from OSM csv config and network inputs

    Parse a genet.Network object and find edges whose
    ['attributes'][attribute_name]['text'] is present in a list of OSM way ids
    :param network: a genet.Network object with attribute_name tags
    :param attribute_name: a string corresponding to the name of the link attribute of interest
    :param osm_csv_path: path to a .csv config file where OSM way ids are stored in column `osm_ids`
    :param outpath: path to an outputs folder
    :return: osm_df which is also written to .csv and a mapping between OSM IDs and network link IDs osm_to_network_dict
     which is also saved to .json in the `outpath` location
    :return:
    """
    osm_df, osm_to_network_dict = extract_network_id_from_osm_csv(network, attribute_name, osm_csv_path, outpath)
    tolls_df = merge_osm_tolls_and_network_snapping(osm_df, osm_to_network_dict)
    return Toll(tolls_df)


def merge_osm_tolls_and_network_snapping(osm_df, osm_to_network_dict):
    # map OSM IDs to network link IDs
    osm_df['network_link_id'] = osm_df['osm_id'].map(osm_to_network_dict)
    # not all would have matched, we drop unmatched at this point (they get reported elsewhere)
    osm_df = osm_df[osm_df['network_link_id'].notna()]
    osm_df = osm_df.drop(['osm_id', 'network_id'], axis=1)
    df = pd.DataFrame({
        col: np.repeat(osm_df[col].values, osm_df['network_link_id'].str.len())
        for col in set(osm_df.columns) - {'network_link_id'}}
    ).assign(network_link_id=np.concatenate(osm_df['network_link_id'].values))
    df = df.rename(columns={'osm_ref': 'toll_id'})
    return df


def extract_network_id_from_osm_csv(network, attribute_name, osm_csv_path, outpath):
    """
    Parse a genet.Network object and find edges whose ['attributes'][attribute_name]['text'] is present in a list
    of OSM way ids
    :param network: a genet.Network object with attribute_name tags
    :param attribute_name: a string corresponding to the name of the link attribute of interest
    :param osm_csv_path: path to a .csv config file where OSM way ids are stored in column `osm_ids`
    :param outpath: path to a folder
    :return: osm_df which is also written to .csv and a mapping between OSM IDs and network link IDs
    osm_to_network_dict which is also saved to .json in the `outpath` location
    """

    osm_df = pd.read_csv(osm_csv_path)
    osm_df['network_id'] = pd.Series(dtype=str)

    target_osm_ids = set(osm_df['osm_id'].values)

    osm_to_network_dict = {}

    with tqdm(total=len(target_osm_ids)) as pbar:
        for target_id in target_osm_ids:
            links = network.extract_links_on_edge_attributes(
                conditions={'attributes': {attribute_name: target_id}},
            )

            # links is now a list of strings
            if len(links) > 0:
                # store list of links in dictionary
                osm_to_network_dict[target_id] = links
                # mark the OSM id as "matched" in the dataframe
                osm_df.loc[osm_df['osm_id'] == target_id, 'network_id'] = True
            else:
                # mark the OSM id as "ummatched" in the dataframe
                osm_df.loc[osm_df['osm_id'] == target_id, 'network_id'] = False

            pbar.update(1)

    # check whether some of our OSM ids were not found
    osm_df['network_id'] = osm_df['network_id'].fillna(False)
    unmatched_osm_df = osm_df[~osm_df['network_id']]
    if unmatched_osm_df.shape[0] > 0:
        # print unmatched ids
        logging.info(f'These OSM way IDs did not find a match in the network.xml: {unmatched_osm_df["osm_id"].values}')

    # write dataframe as .csv and dictionary as .json
    osm_df.to_csv(os.path.join(outpath, 'osm_tolls_with_network_ids.csv'), index=False)
    with open(os.path.join(outpath, 'osm_to_network_ids.json'), 'w') as write_file:
        json.dump(osm_to_network_dict, write_file)

    return osm_df, osm_to_network_dict


def write_xml(root, path, filename='roadpricing-file.xml'):
    """
    Write XML config for MATSim Road Pricing a given folder location.
    :param root: an 'lxml.etree._Element' object corresponding to the root of an XML tree
    :param path: location of destination folder for Road Pricing config
    :return: None
    """
    tree = et.tostring(root,
                       pretty_print=True,
                       xml_declaration=False,
                       encoding='UTF-8')
    with open(os.path.join(path, filename), 'wb') as file:
        file.write(b'<?xml version="1.0" ?>\n')
        file.write(b'<!DOCTYPE roadpricing SYSTEM "http://www.matsim.org/files/dtd/roadpricing_v1.dtd">\n')
        file.write(tree)


def build_tree_from_csv_json(csv_input, json_input, toll_type='link', toll_scheme_name='simple-toll',
                             toll_description='A simple toll scheme'):
    """
    Build XML config for MATSim Road Pricing from .csv and .json input
    :param csv_input: csv output from `extract_network_id_from_osm_csv` with additional columns: `vehicle_type`,
    `toll_amount`, `start_time` and `end_time` for each of the tolls required.
    :param json_input: json output from `extract_network_id_from_osm_csv`
    :return: an 'lxml.etree._Element' object
    """
    # CSV input
    osm_df = pd.read_csv(csv_input, dtype={'osm_id': str})
    # JSON input
    with open(json_input, 'r') as f:
        osm_to_network_dict = json.load(f)
    return build_tree(merge_osm_tolls_and_network_snapping(osm_df, osm_to_network_dict), toll_type=toll_type,
                      toll_scheme_name=toll_scheme_name, toll_description=toll_description)


def build_tree(df_tolls, toll_type='link', toll_scheme_name='simple-toll', toll_description='A simple toll scheme'):
    """
    Build XML config for MATSim Road Pricing from tolls DataFrame input
    :param df_tolls: pd.DataFrame(
                columns=[
                    'toll_id',  # optional, unique ID of the toll, based off OSM ref if applicable
                    'network_link_id',  # network link ID to be charged
                    'vehicle_type',  # optional, type of vehicle, does not persist to MATSim road pricing xml file
                    'toll_amount',  # cost to travel on that link
                    'start_time',  # start time for the toll
                    'end_time',  # end time for the toll
                    'osm_name',  # optional, if derived from OSM, human readable name of the road
                    'notes'  # optional, user notes
                ]
    :param toll_type: default 'link', other supported MATSim toll types: 'distance', 'cordon', 'area',
        more info: https://www.matsim.org/apidocs/core/0.3.0/org/matsim/roadpricing/package-summary.html
    :param toll_scheme_name: name to pass to xml file, useful for identifying multiple toll schemes
    :param toll_description: additional description of the toll to pass to the xml file
    :return: an 'lxml.etree._Element' object
    """

    roadpricing = Element("roadpricing", type=toll_type, name=toll_scheme_name)
    description = SubElement(roadpricing, "description")
    description.text = toll_description

    links = SubElement(roadpricing, "links")

    # make sure all links from same toll are grouped together:
    if 'toll_id' not in df_tolls.columns:
        # if not present just take it link by link
        df_tolls['toll_id'] = df_tolls['network_link_id']
    df_tolls = df_tolls.sort_values(by='toll_id')

    # Time-of-day pricing:
    # links with multiple tolling amounts throughout the day appear as multiple rows in the .csv config
    # links with uniform pricing throughout the day appear only once in .csv config
    try:
        links_repeat = pd.concat(g for _, g in df_tolls.groupby('network_link_id') if len(g) > 1)
    except ValueError:
        links_repeat = pd.DataFrame()
    links_no_repeat = df_tolls[~df_tolls.index.isin(links_repeat.index)]

    # list to keep track of which Toll names we added as comments
    commented_tolls = []

    # links without time-of-day pricing:
    for index, row in links_no_repeat.iterrows():

        if str(row['toll_id']) not in commented_tolls:
            links.append(Comment(' === ' + str(row['toll_id']) + ' === '))
            commented_tolls.append(str(row['toll_id']))

        link = SubElement(links, "link", id=str(row['network_link_id']))
        SubElement(link, "cost", start_time=str(row['start_time']),
                   end_time=str(row['end_time']), amount=str(row['toll_amount']))

    # links with time-of-day pricing:
    # get unique ids of these links and iterate through them
    if not links_repeat.empty:
        unique_repeated_ids = links_repeat['network_link_id'].unique()
        for link_id in unique_repeated_ids:

            link_time_of_day_df = links_repeat[links_repeat['network_link_id'] == link_id]

            link_ref = link_time_of_day_df['toll_id'].unique()[0]
            if link_ref not in commented_tolls:
                links.append(Comment(' === ' + str(link_ref) + ' === '))
                commented_tolls.append(str(link_ref))

            link = SubElement(links, "link", id=str(link_id))
            for index, row in link_time_of_day_df.iterrows():
                SubElement(link, "cost", start_time=str(row['start_time']),
                           end_time=str(row['end_time']), amount=str(row['toll_amount']))

    return roadpricing
