# Network Scenario Generator (GeNet)

This package provides tools to represent and work with a multi-modal transport network with public transport (PT)
services. It is based on [MATSim's](https://www.matsim.org/) representation of such networks. The underlying 
network available to PT services (roads, railways, but also ferry/flight connections) uses a `networkx.MultiDiGraph`
with additional methods for `'links'` which are unique in `genet.Network` (`networkx.MultiDiGraph` accepts multiple 
edges between the same from and to node pair; referring to an edge in `networkx.MultiDiGraph` and `genet.Network`
has the same effects, i.e. the result is a dictionary indexed by the multi edge index). The PT services are 
represented through `genet.Schedule` class which relies on other `genet` 
classes: the `Schedule` relies on a list of `genet.Service`'s, which in turns consists of a list of `genet.Route`'s.
Each `Route` class object has an attribute `stops` which consists of `genet.Stops` objects. The `Stops` carry spatial
information for the PT stop.

The goal of GeNet is to:
- Provide a formalised in-memory data structure for representing a multi-modal network with a PT service
- Enable using the data structure for tasks such as generating auxiliary MATSim files e.g. Road Pricing
- Simplify the process of modifying a network and provide simple change log to track the differences between the input
and output networks.
- Provide validation methods to check for simple errors such as: whether a `Route` has more than one `Stop` or that the
underlying graph doesn't have any dead-ends or sources (a place which you can leave but cannot get back to).

## Setup

To run pre-baked scripts that use genet in a number of different scenarios you can use docker:

### Using Docker
#### Build the image

    docker build -t "genet" .

#### Running a container with a pre-baked script

    docker run genet reproject_network.py -h
    
    usage: reproject_network.py [-h] -n NETWORK [-s SCHEDULE] -cp
                                CURRENT_PROJECTION -np NEW_PROJECTION
                                [-p PROCESSES] -od OUTPUT_DIR
    
    Reproject a MATSim network
    
    optional arguments:
      -h, --help            show this help message and exit
      -n NETWORK, --network NETWORK
                            Location of the network.xml file
      -s SCHEDULE, --schedule SCHEDULE
                            Location of the schedule.xml file
      -cp CURRENT_PROJECTION, --current_projection CURRENT_PROJECTION
                            The projection network is currently in, eg.
                            "epsg:27700"
      -np NEW_PROJECTION, --new_projection NEW_PROJECTION
                            The projection desired, eg. "epsg:27700"
      -p PROCESSES, --processes PROCESSES
                            The number of processes to split computation across
      -od OUTPUT_DIR, --output_dir OUTPUT_DIR
                            Output directory for the reprojected network

Otherwise, you can install `genet` as a python package, in your base installation of python or a virtual environment.
Run the pre-baked scripts, write your own scripts or use IPython shell or Jupyter Notebook to load up a network, 
inspect or change it and save it out to file.

#### Install dev prereqs (use equivalent linux or windows package management)

    brew install python3.7
    brew install virtualenv
    
#### Installation  

    virtualenv -p python3.7 venv
    source venv/bin/activate
    pip install -e .
    
### Testing

#### Run the unit tests (from root dir)

    python -m pytest -vv tests

#### Generate a unit test code coverage report

To generate XML & HTML coverage reports to `reports/coverage`:
    
    ./bash_scripts/code-coverage.sh

## Usage
This section goes through basic usage examples.

### Setting-up a Network object

Instantiate an empty network

    >>> import genet
    >>> n = genet.Network()
    >>> n
    
    <Network instance at 4683796240: with 
    graph: Name: 
    Type: MultiDiGraph
    Number of nodes: 0
    Number of edges: 0
     and 
    schedule Number of services: 0
    Number of unique routes: 0

You can now use methods to read in MATSim network files:

    >>> pt2matsim_network = 'path/to/network.xml'
    >>> pt2matsim_schedule = 'path/to/schedule.xml'
    
    >>> n.read_matsim_network(pt2matsim_network, epsg='epsg:27700')
    >>> n.read_matsim_schedule(pt2matsim_schedule, epsg='epsg:27700')
    >>> n
    
    <Network instance at 4683796240: with 
    graph: Name: 
    Type: MultiDiGraph
    Number of nodes: 1662
    Number of edges: 3166
    Average in degree:   1.9049
    Average out degree:   1.9049 and 
    schedule Number of services: 62
    Number of unique routes: 520
    
![GeNet Network diagram](images/genet_network.png)

### Using a Network object

Once you have a `genet.Network` object, you can use it to produce auxiliary files, analyse of modify the network.

#### Summary
The data saved on the edges of the graph can be nested. There are a couple of convenient methods that summarise the 
schema of the data found on the nodes and links to show you what the keys (and if `data=True`, also values) of those 
dictionaries look like. If `data=True`, the output shows up to 5 unique values stored in that location.

    >>> n.node_attribute_summary(data=True)
    
    attribute
    ├── id: ['293813458', '4582907654', '107829', '2833956947', '5607749654']
    ├── x: ['527677.5109120146', '529801.0659699676', '530238.1178740165', '527959.3321330055', '530629.5558489189']
    ├── y: ['181250.1252480651', '182424.5440813937', '181228.56259440206', '182169.2831176619', '181516.2234405568']
    ├── lon: [-0.15178558709839862, -0.15872448710537235, -0.13569068709168342, -0.13766218709633904, -0.13543658708819173]
    ├── lat: [51.51609983324067, 51.5182034332405, 51.51504733324089, 51.522253033239515, 51.522948433239556]
    └── s2_id: [5221390710015643649, 5221390314367946753, 5221366508477440003, 5221390682291777543, 5221390739236081673]

and for links,

    >>> n.link_attribute_summary()
    
    attribute
    ├── id
    ├── from
    ├── to
    ├── freespeed
    ├── capacity
    ├── permlanes
    ├── oneway
    ├── modes
    ├── s2_from
    ├── s2_to
    ├── length
    └── attributes
        ├── osm:way:access
        │   ├── name
        │   ├── class
        │   └── text
        ├── osm:way:highway
        │   ├── name
        │   ├── class
        │   └── text
        ├── osm:way:id
        │   ├── name
        │   ├── class
        │   └── text
        ├── osm:way:name
        │   ├── name
        │   ├── class
        │   └── text
        ...
        └── osm:way:service
            ├── name
            ├── class
            └── text


Once you see the general schema for the data stored on nodes and links, you may decide to look at or perform analysis 
on all of the data stored in the network under a particular key. A GeNet network has four methods (two for nodes and 
two for links) which generate:

- `pandas.Series` object, which stores the nodes or links data present at the specified key, indexed by the same index 
as the nodes or links.
- or `pandas.DatFrame` object if you want to exctract data under more than one key, indexed by the same index 
as the nodes or links.


    >>> s_freespeed = n.link_attribute_data_under_key('freespeed')
    >>> s_freespeed
    1                4.166667
    10               4.166667
    100              4.166667
    1000             4.166667
    1001             4.166667
                      ...    
    998              6.944444
    999              6.944444
    pt_1383_2634     5.000000
    pt_1383_3328    10.000000
    pt_1506_1663     5.000000
    Length: 3166, dtype: float64

then you can treat it as a `pandas` object and use their methods to analyse it, e.g.
    
    >>> s_freespeed.describe()
    count    3166.000000
    mean        9.522794
    std         7.723735
    min         2.777778
    25%         4.166667
    50%         4.166667
    75%        22.222222
    max        22.222222
    dtype: float64
    
And for more keys:

    >>> n.link_attribute_data_under_keys(['freespeed', {'attributes': {'osm:way:highway': 'text'}}]).head()

    |      |   freespeed | attributes::osm:way:highway::text   |
    |-----:|------------:|:------------------------------------|
    |    1 |     4.16667 | unclassified                        |
    |   10 |     4.16667 | unclassified                        |
    |  100 |     4.16667 | unclassified                        |
    | 1000 |     4.16667 | residential                         |
    | 1001 |     4.16667 | residential                         |

#### Extracting links of interest

You can extract the unique ids of links in the network which satisfy certain conditions pertaining to the
data being stored on graph edges.

    >>> links = genet.graph_operations.extract_links_on_edge_attributes(
            n,
            conditions= {'attributes': {'osm:way:highway': {'text': 'primary'}}},
        )
    >>> links[:5]
    ['1007', '1008', '1023', '1024', '103']

The function above gathers link ids which satisfy conditions 
to arbitrary level of nested-ness. It also allows quite flexible conditions---above we require that the link value
at `data['attributes']['osm:way:highway']['text'] == 'primary'`, where data is the data dictionary stored on that link.
You can also define a condition such that `data['attributes']['osm:way:highway']['text']` is one of the items in a 
list: `['primary', 'secondary', 'something else']`:

    >>> links = genet.graph_operations.extract_links_on_edge_attributes(
            n,
            conditions= {'attributes': {'osm:way:highway': {'text': ['primary', 'secondary', 'something else']}}},
        )

and many more. You can find the examples in the jupyter notebook: `notebooks/GeNet walk-through.ipynb`

### Modifying a Network object

`GeNet` supports some simple modifications like adding, reindexing and removing nodes and links and some involved 
modifications like changing the data stored under nodes or links (which will be discussed below). All of these 
changes get recorded in `n.change_log`.

#### 1.) Adding nodes/links

    >>> n.add_link(link_id='proposed_index', u='4356572310', v='5811263955')
    >>> n.add_node(node='proposed_index', attribs={'data':'some_data'})

The index passed is only a proposition. If a node or link under this link exists, a new, unique index will be 
generated.

#### 2.) Reindexing

To reindex a node or link:

    >>> n.reindex_node('proposed_index', 'another_index')
    >>> n.reindex_link('proposed_index', 'another_index')

#### 3.) Removing nodes/links

To remove a link or node:

    >>> n.remove_links('another_index')
    >>> n.remove_node('another_index')

#### 4.) Modifying data stored on nodes or edges:

Let's say you have extracted `genet.Network` link ids of interest, they are stored in the list `links` as above, and 
now you want to make changes to the network. Let's 
make changes to the nested OSM data stored on the links. We will replace the highway tags from to 
`'SOMETHING'`.

    >>> n.apply_attributes_to_links(links, {'attributes': {'osm:way:highway': {'text': 'SOMETHING'}}})
    
    >>> n.link('1007')
    
    {'id': '1007',
     'from': '4356572310',
     'to': '5811263955',
     'freespeed': 22.22222222222222,
     'capacity': 3000.0,
     'permlanes': 2.0,
     'oneway': '1',
     'modes': ['car'],
     's2_from': 5221390723045407809,
     's2_to': 5221390723040504387,
     'length': 13.941905154249884,
     'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
       'class': 'java.lang.String',
       'text': 'SOMETHING'},
      'osm:way:id': {'name': 'osm:way:id',
       'class': 'java.lang.Long',
       'text': '589660342'},
      'osm:way:lanes': {'name': 'osm:way:lanes',
       'class': 'java.lang.String',
       'text': '2'},
      'osm:way:name': {'name': 'osm:way:name',
       'class': 'java.lang.String',
       'text': 'Shaftesbury Avenue'},
      'osm:way:oneway': {'name': 'osm:way:oneway',
       'class': 'java.lang.String',
       'text': 'yes'}}}

The changes you make to the `Network` will be recorded in the `change_log` which is a `pandas.DataFrame`. This log
gets saved to a csv together with any `Network` outputs.

    >>> n.change_log.log
    
    |    | timestamp           | change_event   | object_type   |   old_id |   new_id | old_attributes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | new_attributes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | diff                                                                      |
    |---:|:--------------------|:---------------|:--------------|---------:|---------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------|
    |  0 | 2020-06-02 10:47:03 | modify         | link          |     1007 |     1007 | {'id': '1007', 'from': '4356572310', 'to': '5811263955', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390723045407809, 's2_to': 5221390723040504387, 'length': 13.941905154249884, 'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '589660342'}, 'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '2'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Shaftesbury Avenue'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}}                  | {'id': '1007', 'from': '4356572310', 'to': '5811263955', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390723045407809, 's2_to': 5221390723040504387, 'length': 13.941905154249884, 'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'SOMETHING'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '589660342'}, 'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '2'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Shaftesbury Avenue'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}}                  | [('change', 'attributes.osm:way:highway.text', ('primary', 'SOMETHING'))] |
    |  1 | 2020-06-02 10:47:03 | modify         | link          |     1008 |     1008 | {'id': '1008', 'from': '5811263955', 'to': '21665588', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390723040504387, 's2_to': 5221390723204000715, 'length': 25.86037080854938, 'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '614324183'}, 'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '2'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Shaftesbury Avenue'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}}                     | {'id': '1008', 'from': '5811263955', 'to': '21665588', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390723040504387, 's2_to': 5221390723204000715, 'length': 25.86037080854938, 'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'SOMETHING'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '614324183'}, 'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '2'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Shaftesbury Avenue'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}}                     | [('change', 'attributes.osm:way:highway.text', ('primary', 'SOMETHING'))] |
    |  2 | 2020-06-02 10:47:03 | modify         | link          |     1023 |     1023 | {'id': '1023', 'from': '1611125463', 'to': '108234', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['bus', 'car', 'pt'], 's2_from': 5221390319884366911, 's2_to': 5221390320040783993, 'length': 53.767011109096586, 'attributes': {'osm:relation:route': {'name': 'osm:relation:route', 'class': 'java.lang.String', 'text': 'bus'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '59718434'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Cavendish Place'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}} | {'id': '1023', 'from': '1611125463', 'to': '108234', 'freespeed': 22.22222222222222, 'capacity': 3000.0, 'permlanes': 2.0, 'oneway': '1', 'modes': ['bus', 'car', 'pt'], 's2_from': 5221390319884366911, 's2_to': 5221390320040783993, 'length': 53.767011109096586, 'attributes': {'osm:relation:route': {'name': 'osm:relation:route', 'class': 'java.lang.String', 'text': 'bus'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'SOMETHING'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '59718434'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Cavendish Place'}, 'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'}}} | [('change', 'attributes.osm:way:highway.text', ('primary', 'SOMETHING'))] |

### Validation

TBA

## Adding two networks

You can add one network to another. The network you're adding the other network too will be updated with the nodes, 
link and data from the other network. Before the network you are adding will go through a process of having it's node
and link indices consolidated to match the network it's being added to. The node ids are consolidated based on their
spatial information, i.e. the network-to-add will inherit the node ids from the main network if the nodes share the
`s2` index. The link ids and the multi index the edge is stored under in the graph are consolidated based on shared 
from and to nodes and modes and the modes stored in the links data.

For now, the method only supports non overlapping services.

    >>> n.add(other_network)

### Writing results

At the moment GeNet supports saving `Network` and `Schedule` objects to MATSim's `network.xml`, `schedule.xml` and
`vehicles.xml`.

    >>> n.write_to_matsim('/path/to/matsim/networks/genet_output'))
    
Saving a `Network` will result in `network.xml`, `schedule.xml` and `vehicles.xml` files if the Network has a non-empty 
`Schedule`.

Saving a `Schedule` will result in `schedule.xml` and `vehicles.xml` files.

You can check that a `Network` that had been read in from MATSim files results in semantically equal xml files 
(if not changes were applied to the `Network` of course)

    >>> from tests.xml_diff import assert_semantically_equal
    >>> assert_semantically_equal(
            pt2matsim_schedule, 
            '/path/to/matsim/networks/genet_output/schedule.xml')
            
            
    path/to/schedule.xml and /path/to/matsim/networks/genet_output/schedule.xml are semantically equal