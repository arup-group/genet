

# NECESSARY NETWORK LINK ATTRIBUTES for use when saving genet.Network to matsim's network.xml
NECESSARY_NETWORK_LINK_ATTRIBUTES = ['id', 'from', 'to', 'length', 'freespeed', 'capacity', 'permlanes', 'oneway',
                                     'modes']

# NECESSARY STOP FACILITY ATTRIBUTES matsim's expected attributes for transit stops, used when saving schedule.xml
NECESSARY_STOP_FACILITY_ATTRIBUTES = ['id', 'x', 'y']
# ADDITIONAL STOP FACILITY ATTRIBUTES matsim's optional attributes for transit stops, used when saving schedule.xml
ADDITIONAL_STOP_FACILITY_ATTRIBUTES = ['linkRefId', 'isBlocking', 'name']


# EXTENDED_TYPE_DICT = {mode : [GTFS mode integers]}
# e.g. {"subway,metro" : [1, 400, 401 ,402, 403, 405]}
# https://developers.google.com/transit/gtfs/reference#routestxt
EXTENDED_TYPE_DICT = {
    "tram,streetcar,light rail": [0],
    "subway,metro": [1],
    "rail": [2],
    "bus": [3],
    "ferry": [4],
    "cable car": [5],
    "gondola,suspended cable car": [6],
    "funicular": [7]
}
# Now extended, mapping to basic modes
# https://developers.google.com/transit/gtfs/reference/extended-route-types
EXTENDED_TYPE_DICT['rail'].extend(list(range(100, 118)))
EXTENDED_TYPE_DICT['bus'].extend(list(range(200, 210)))
EXTENDED_TYPE_DICT['subway,metro'].extend(list(range(400, 406)))
EXTENDED_TYPE_DICT['bus'].extend(list(range(700, 718)))
EXTENDED_TYPE_DICT['bus'].append(800)
EXTENDED_TYPE_DICT['tram,streetcar,light rail'].extend(list(range(900, 908)))
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
# e.g. {1: "subway,metro", 400: "subway,metro", 401: "subway,metro", 402: "subway,metro", ...]}
EXTENDED_TYPE_MAP = dict(zip(new_keys, new_values))
del new_keys, new_values


# MODE_TYPES_MAP = {singular mode: combined mode from EXTENDED_TYPE_DICT}
# e.g. {"subway": "subway,metro", "metro": "subway,metro"}
MODE_TYPES_MAP = {}
for mode in EXTENDED_TYPE_DICT.keys():
    ms = mode.split(',')
    for m in ms:
        MODE_TYPES_MAP[m.lower()] = mode.lower()
