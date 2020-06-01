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

    >>> import genet as gn
    >>> n = gn.Network()
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



### Validation


### Writing results
