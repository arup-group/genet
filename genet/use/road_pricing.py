import os

from lxml import etree as et
from lxml.etree import Element, SubElement
from tqdm import tqdm


def extract_toll_ways_from_opl(path_opl):
    '''
    Given a .osm.opl file, extract the ids of toll ways
    :param path_opl: path to the .osm.opl file
    :return: list of OSM way ids matching criteria (str)
    '''
    # parse .osm.opl contents
    with open(path_opl, 'r') as f:
        contents = [line.rstrip('\n') for line in f]
    # extract all OSM ways
    ways = [line for line in contents if line[0] == 'w']

    # extract toll ways from above OSM ways
    toll_ways = []
    with tqdm(total=len(ways)) as pbar:
        for way in ways:
            # below conditions are the result of iterations on Ireland OSM
            # for another location, some unwanted ways could still persist
            if all(['toll=yes' in way,
                    'ferry' not in way,
                    'highway=service' not in way,
                    'highway=unclassified' not in way,
                    'motor_vehicle=no' not in way,
                    'access=private' not in way,
                    'access=no' not in way]):
                toll_ways.append(way)
            pbar.update(1)

    # extract ids from toll ways
    toll_ids = [item.split(' ')[0] for item in toll_ways]
    # summary for user
    print('{} toll ways extracted from {}'.format(len(toll_ids), path_opl))

    return toll_ids


#  user should check that they are happy with links (osmium getid - QGIS - OSM layer)
# hence why we provide write_toll_ids() and read_toll_ids(), as user may
# add some ids manually


def write_toll_ids(toll_ids, outpath):
    '''
    Given a list of way ids, write them to a file named 'toll_ids' where each is
    on a separate line. Such files can be used to subset a .osm.pbf with osmium
    e.g. `osmium getid -i toll_ids -r input.osm.pbf -o tolls.osm.pbf`
    :param toll_ids: list of way ids (str)
    :param outpath: path to destination folder
    :return: write a list of way ids e.g. `w123456` (str)
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


def extract_network_id_from_osm_id(n, osm_way_ids):
    '''
    Parse a Network() object and find edges whose
    ['attributes']['osm:way:id']['text'] is present in osm_way_ids
    :param n: a Network() object with 'osm:way:id'
    :param osm_way_ids: a list of OSM way ids (without the `w` prefix) (str)
    :return: a list of network edge ids (str)
    '''
    # a notion of progress bar could be nice but it's tricky to implement here
    # as we don't know how long the loop will have to run for (see break clause)
    network_toll_ids = []
    edge_osm_ids = []

    for link_id, link_attribs in n.links():
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


def write_xml(root, path):
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
