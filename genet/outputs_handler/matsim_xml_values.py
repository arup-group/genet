MATSIM_JOSM_DEFAULTS = {
    'motorway': {
        'permlanes': 2.0,
        'freespeed': 33.36,
        # 'freespeedFactor': 1.0,
        'capacity': 2000.0
    },
    'motorway_link': {
        'permlanes': 1.0,
        'freespeed': 22.22,
        # 'freespeedFactor': 1.0,
        'capacity': 1500.0
    },
    'trunk': {
        'permlanes': 1.0,
        'freespeed': 22.22,
        # 'freespeedFactor': 1.0,
        'capacity': 2000.0
    },
    'trunk_link': {
        'permlanes': 1.0,
        'freespeed': 13.89,
        # 'freespeedFactor': 1.0,
        'capacity': 1500.0},
    'primary': {
        'permlanes': 1.0,
        'freespeed': 22.22,
        # 'freespeedFactor': 1.0,
        'capacity': 1500.0},
    'primary_link': {
        'permlanes': 1.0,
        'freespeed': 16.68,
        # 'freespeedFactor': 1.0,
        'capacity': 1500.0},
    'secondary': {
        'permlanes': 1.0,
        'freespeed': 16.68,
        # 'freespeedFactor': 1.0,
        'capacity': 1000.0},
    'secondary_link': {
        'permlanes': 1.0,
        'freespeed': 16.68,
        # 'freespeedFactor': 1.0,
        'capacity': 1000.0},
    'tertiary': {
        'permlanes': 1.0,
        'freespeed': 12.5,
        # 'freespeedFactor': 1.0,
        'capacity': 600.0},
    'tertiary_link': {
        'permlanes': 1.0,
        'freespeed': 12.5,
        # 'freespeedFactor': 1.0,
        'capacity': 600.0},
    'minor': {
        'permlanes': 1.0,
        'freespeed': 12.5,
        # 'freespeedFactor': 1.0,
        'capacity': 600.0},
    'unclassified': {
        'permlanes': 1.0,
        'freespeed': 12.5,
        # 'freespeedFactor': 1.0,
        'capacity': 600.0},
    'residential': {
        'permlanes': 1.0,
        'freespeed': 8.34,
        # 'freespeedFactor': 1.0,
        'capacity': 600.0},
    'service': {
        'permlanes': 1.0,
        'freespeed': 4.17,
        # 'freespeedFactor': 1.0,
        'capacity': 300.0},
    'living_street': {
        'permlanes': 1.0,
        'freespeed': 4.17,
        # 'freespeedFactor': 1.0,
        'capacity': 300.0},
    'pedestrian': {
        'permlanes': 1.0,
        'freespeed': 1.34,
        # 'freespeedFactor': 1.0,
        'capacity': 300.0},
    'footway': {
        'permlanes': 1.0,
        'freespeed': 1.34,
        # 'freespeedFactor': 1.0,
        'capacity': 300.0},
    'steps': {
        'permlanes': 1.0,
        'freespeed': 1.34,
        # 'freespeedFactor': 1.0,
        'capacity': 300.0},
    'railway': {
        'permlanes': 1.0,
        'freespeed': 44.44,
        # 'freespeedFactor': 1.0,
        'capacity': 9999.0}
}


MODE_DICT = {
    "Tram,Streetcar,Light rail".lower(): 'Tram',
    "Subway,Metro".lower(): 'Underground Service',
    "Subway".lower(): 'Underground Service',
    "Metro".lower(): 'Underground Service',
    "Rail".lower(): 'Rail',
    "Bus".lower(): 'Bus',
    "Ferry".lower(): 'Ferry',
    "Cable car".lower(): 'Cable car',
    "Gondola,Suspended cable car".lower(): 'Gondola',
    "Funicular".lower(): 'Funicular'
}


VEHICLE_TYPES = {
    'Bus': {
        'capacity': {
            'seats': {'persons': '70'},
            'standingRoom': {'persons': '0'}
        },
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}
    },
    'Rail': {
        'capacity': {
            'seats': {'persons': '400'},
            'standingRoom': {'persons': '0'}
        },
        'length': {'meter': '200.0'},
        'width': {'meter': '2.8'},
        'accessTime': {'secondsPerPerson': '0.25'},
        'egressTime': {'secondsPerPerson': '0.25'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '27.1'}
    },
    'Underground Service': {
        'capacity': {
            'seats': {'persons': '300'},
            'standingRoom': {'persons': '0'}
        },
        'length': {'meter': '30.0'},
        'width': {'meter': '2.45'},
        'accessTime': {'secondsPerPerson': '0.1'},
        'egressTime': {'secondsPerPerson': '0.1'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '4.4'}
    },
    'Ferry': {
        'capacity': {
            'seats': {'persons': '250'},
            'standingRoom': {'persons': '0'}
        },
        'length': {'meter': '50.0'},
        'width': {'meter': '6.0'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '7.1'}
    },
    'Tram': {
        'capacity': {
            'seats': {'persons': '180'},
            'standingRoom': {'persons': '0'}
        },
        'length': {'meter': '36.0'},
        'width': {'meter': '2.4'},
        'accessTime': {'secondsPerPerson': '0.25'},
        'egressTime': {'secondsPerPerson': '0.25'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '5.2'}
    }
}
