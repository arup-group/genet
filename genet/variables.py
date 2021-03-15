# NETWORK LINK ATTRIBUTES for use when saving genet.Network to matsim's network.xml
NECESSARY_NETWORK_LINK_ATTRIBUTES = ['id', 'from', 'to', 'length', 'freespeed', 'capacity', 'permlanes', 'modes']
OPTIONAL_NETWORK_LINK_ATTRIBUTES = ['oneway']

# NECESSARY STOP FACILITY ATTRIBUTES matsim's expected attributes for transit stops, used when saving schedule.xml
NECESSARY_STOP_FACILITY_ATTRIBUTES = ['id', 'x', 'y']
# ADDITIONAL STOP FACILITY ATTRIBUTES matsim's optional attributes for transit stops, used when saving schedule.xml
ADDITIONAL_STOP_FACILITY_ATTRIBUTES = ['linkRefId', 'isBlocking', 'name']


# EXTENDED_TYPE_DICT = {mode : [GTFS mode integers]}
# e.g. {"subway,metro" : [1, 400, 401 ,402, 403, 405]}
# https://developers.google.com/transit/gtfs/reference#routestxt
EXTENDED_TYPE_DICT = {
    "tram": [0],
    "subway": [1],
    "rail": [2],
    "bus": [3],
    "ferry": [4],
    "cablecar": [5],
    "gondola": [6],
    "funicular": [7]
}
# Now extended, mapping to basic modes
# https://developers.google.com/transit/gtfs/reference/extended-route-types
EXTENDED_TYPE_DICT['rail'].extend(list(range(100, 118)))
EXTENDED_TYPE_DICT['bus'].extend(list(range(200, 210)))
EXTENDED_TYPE_DICT['subway'].extend(list(range(400, 406)))
EXTENDED_TYPE_DICT['bus'].extend(list(range(700, 718)))
EXTENDED_TYPE_DICT['bus'].append(800)
EXTENDED_TYPE_DICT['tram'].extend(list(range(900, 908)))
EXTENDED_TYPE_DICT['ferry'].extend([1000, 1200, 1502])
EXTENDED_TYPE_DICT['funicular'].append(1400)
EXTENDED_TYPE_DICT['rail'].append(1503)
# there are a few other snowflakes in there which are not an obvious match to the basic modes, so let's skip for now


# ze old switcheroo, and flatten
new_keys = []
new_values = []
for key, value in EXTENDED_TYPE_DICT.items():
    for item in value:
        new_keys.append(item)
        new_values.append(key)

# EXTENDED_TYPE_MAP = {GTFS mode integer : mode}
# e.g. {1: "subway", 400: "subway", 401: "subway", 402: "subway", ...]}
EXTENDED_TYPE_MAP = dict(zip(new_keys, new_values))
del new_keys, new_values
