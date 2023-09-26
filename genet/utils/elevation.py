import logging
import os

import numpy as np
import rioxarray
from lxml import etree


def get_elevation_image(elevation_tif):
    xarr_file = rioxarray.open_rasterio(elevation_tif)
    if str(xarr_file.rio.crs) != "EPSG:4326":
        xarr_file = xarr_file.rio.write_crs(4326, inplace=True)

    return xarr_file[0, :, :]


def get_elevation_data(img, lat, lon):
    output = img.sel(x=lon, y=lat, method="nearest")
    mt = output.values
    elevation_meters = mt.item()

    return elevation_meters


def validation_report_for_node_elevation(elev_dict, low_limit=-50, mont_blanc_height=4809):
    """
    Generates a validation report for the node elevation dictionary.
    :param elev_dict: contains node_id as key and elevation in meters as value
    :param low_limit: values below this param get flagged as possibly wrong; set at -50m (below sea level) by default,
    can optionally set a different value
    :param mont_blanc_height: values above this param get flagged as possibly wrong; defaults to 4809m,
    the height of Mont Blank, can optionally set a different value
    :return: dict, with 2 data subsets - summary statistics, and extreme values lists
    """

    elevation_list = []
    for node_id in elev_dict.keys():
        elevation_list.append(elev_dict[node_id]["z"])

    min_value = np.min(elevation_list)
    max_value = np.max(elevation_list)
    mean = np.mean(elevation_list)
    median = np.median(elevation_list)

    too_high = {}
    too_low = {}

    for node_id in elev_dict.keys():
        node_elev = elev_dict[node_id]["z"]
        if node_elev < low_limit:
            too_low[node_id] = node_elev
        elif node_elev > mont_blanc_height:
            too_high[node_id] = node_elev

    report = {
        "summary": {
            "total_nodes": len(elevation_list),
            "min_value": int(min_value),
            "max_value": int(max_value),
            "mean": int(mean),
            "median": int(median),
            "extremely_high_values_count": len(too_high),
            "extremely_low_values_count": len(too_low),
        },
        "values": {"extremely_high_values_dict": too_high, "extremely_low_values_dict": too_low},
    }

    return report


def write_slope_xml(link_slope_dictionary, output_dir):
    """
    Generates a link_slopes XML file.
    :param link_slope_dictionary: dictionary of link slopes in format {link_id: {'slope': slope_value}}
    :param output_dir: directory where the XML file will be written to
    """
    fname = os.path.join(output_dir, "link_slopes.xml")
    logging.info(f"Writing {fname}")

    with open(fname, "wb") as f, etree.xmlfile(f, encoding="UTF-8") as xf:
        xf.write_declaration(
            doctype='<!DOCTYPE objectAttributes SYSTEM "http://matsim.org/files/dtd/objectattributes_v1.dtd">'
        )
        with xf.element("objectAttributes"):
            for link_id, slope_dict in link_slope_dictionary.items():
                with xf.element("object", {"id": link_id}):
                    attrib = {"name": "slope", "class": "java.lang.Double"}
                    rec = etree.Element("attribute", attrib)
                    rec.text = str(slope_dict["slope"])
                    xf.write(rec)
