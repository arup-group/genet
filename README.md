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
    
    ./scripts/code-coverage.sh

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

    >>> network = 'path/to/network.xml'
    >>> schedule = 'path/to/schedule.xml'
    
    >>> n.read_matsim_network(network, epsg='epsg:27700')
    >>> n.read_matsim_schedule(schedule, epsg='epsg:27700')
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

### Using a Network object

Once you have a `genet.Network` object, you can use it to produce auxiliary files or analyse the network.
For example, you can extract the unique ids of links in the network which satisfy certain conditions pertaining to the
data being stored on graph edges.

    >>> links = genet.graph_operations.extract_links_on_edge_attributes(
            n,
            conditions= {'attributes': {'osm:way:highway': {'text': 'primary'}}},
        )
    >>> links[:5]
    ['1007', '1008', '1023', '1024', '103']

The data saved on the edges of the graph can be nested. The function above gathers link ids which satisfy conditions 
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

Let's say you have extracted `genet.Network` link ids of interest, they are stored in the list `links` as above, and 
now you want to make changes to the network. Let's 
make changes to the nested OSM data stored on the links. We will replace the highway tags from to 
`'SOMETHING'`.

    >>> n.modify_links(links, {'attributes': {'osm:way:highway': {'text': 'SOMETHING'}}})
    
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


### Writing results

At the moment GeNet supports saving `Network` and `Schedule` objects to MATSim's `network.xml`, `schedule.xml` and
`vehicles.xml`.

    >>> n.write_to_matsim('/path/to/matsim/networks/genet_output'))
    
Saving a `Network` will result in `network.xml`, `schedule.xml` and `vehicles.xml` files if the Network has a non-empty 
`Schedule`.

Saving a `Schedule` will result in `schedule.xml` and `vehicles.xml` files.