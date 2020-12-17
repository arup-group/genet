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

Create and activate virtual environment

    virtualenv -p python3.7 venv
    source venv/bin/activate
    
before installing dependencies you may need to install a dependency of `rtree`: `libspatialindex-dev`, the command 
for linux:
    
    sudo apt-get install -y libspatialindex-dev
    
Finally install `GeNet` dependencies

    pip install -e .
    
### Testing

#### Run the unit tests (from root dir)

    python -m pytest -vv tests

#### Generate a unit test code coverage report

To generate XML & HTML coverage reports to `reports/coverage`:
    
    ./bash_scripts/code-coverage.sh

## Validation

### MATSim specific validation

You can generate a validation report for the genet Network encompassing validity of the network, schedule and routing
 (of the transit services in the schedule on the network). It aims to provide a good collection of checks known to have
 affected MatSim simulations in the past.
 
    >>> report = n.generate_validation_report()

The report is a simple dictionary with keys: `graph`, `schedule` and `routing`.

The `graph` section describes strongly connected components of the modal subgraphs, for modes that agents in MATSim
need to find routes on: `car`, and `walk` and `bike` if using the `multimodal.contrib`. In addition to this, it also
flags links of length 1km or longer that can be inspected separately.

    'graph': {'graph_connectivity': {'bike': {'number_of_connected_subgraphs': 1,
                                              'problem_nodes': {'dead_ends': [],
                                                                'unreachable_node': []}},
                                     'car': {'number_of_connected_subgraphs': 1,
                                              'problem_nodes': {'dead_ends': [],
                                                                'unreachable_node': []}},
                                     'walk': {'number_of_connected_subgraphs': 1,
                                              'problem_nodes': {'dead_ends': [],
                                                                'unreachable_node': []}}},
              'links_over_1km_length': []}

The `schedule` section describes correctness of the schedule on three levels:
    
- `schedule_level`: Overall look at the schedule validity. A `Schedule` is valid if:
    - all of its' services are valid
    - its' services are uniquely indexed
    
    Schedule `has_valid_services` if all services within the schedule are deemed valid. The invalid services are 
    flagged in `invalid_services` and the invalid stages of schedule validity are flagged in `invalid_stages`.
- `service_level`: Provides a look at validity of services within the schedule. It is indexed by service ids. Each
`Service` is valid if:
    - each of its' routes is valid
    - its' routes are uniquely indexed
    
    A service `has_valid_routes` if all routes within the service are deemed valid. The invalid routes are 
    flagged in `invalid_routes` and the invalid stages of service validity are flagged in `invalid_stages`.
- `route_level`: Provides a look at validity of each route within each service indexed by service id and route id
(or service id and the index in the `Service.routes` list if not uniquely indexed). Each `Route` is valid if it
    - has more than one `Stop`
    - has correctly ordered route (the stops (their link reference ids) and links a route refers to are in the same 
    order)
    - arrival and departure offsets are correct (each stop has one and they are correctly ordered temporally)
    - does not have self loops (there are no trips such as: Stop A -> Stop A)
    
    If a route satisfies the above `is_valid_route` is `True`. If not, the `invalid_stages` flag where the route
    did not satisfy validity conditions.

(Nb. The same dictionary can be generated by using `Schedule` object's own `generate_validation_report` method.)

    'schedule': {
     'schedule_level': {'has_valid_services': False,
                        'invalid_services': ['10314'],
                        'invalid_stages': ['not_has_valid_services'],
                        'is_valid_schedule': False},
     'service_level': {'10314': {'has_valid_routes': False,
                                 'invalid_routes': ['VJbd8660f05fe6f744e58a66ae12bd66acbca88b98',
                                                    'VJ042669cc08161b30efa3b508346b648613a95047'],
                                 'invalid_stages': ['not_has_valid_routes'],
                                 'is_valid_service': False},
                       '12430': {'has_valid_routes': True,
                                 'invalid_routes': [],
                                 'invalid_stages': [],
                                 'is_valid_service': True}},
     'route_level': {'10314': {'VJ042669cc08161b30efa3b508346b648613a95047': {'invalid_stages': ['not_has_correctly_ordered_route'],
                                                                              'is_valid_route': False},
                               'VJ37e93a6ebc1f8b2be99e4279776413113b7ce4c5': {'invalid_stages': [],
                                                                              'is_valid_route': True},
                               'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': {'invalid_stages': ['not_has_more_than_one_stop',
                                                                                                 'not_has_correctly_ordered_route',
                                                                                                 'not_has_valid_offsets'],
                                                                              'is_valid_route': False}},
                     '12430': {'VJ06420fdab0dfe5c8e7f2f9504df05cf6289cd7d3': {'invalid_stages': [],
                                                                              'is_valid_route': True},
                               'VJ06cd41dcd58d947097df4a8f33234ef423210154': {'invalid_stages': [],
                                                                              'is_valid_route': True}}}
     }

Finally, the `routing` section describes routing of the transit schedule services onto the network graph.
- `services_have_routes_in_the_graph`: all routes have network routes and the links they refer to exist in the graph,
are connected (to nodes of preceding link is the from node of the next link in the chain) and the `modes` saved on the
link data accept the mode of the route.
- `service_routes_with_invalid_network_route`: flags routes not satifying the above,
- `route_to_crow_fly_ratio`: gives ratio of the length of route to crow-fly distance between each of the stops along 
route. If the route is invalid, it will result in 0. If the route has only one stop it will result in 
`'Division by zero'`.

Example:

    'routing': {
      'services_have_routes_in_the_graph': False,
      'service_routes_with_invalid_network_route': [('10314', 'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'),
                                                    ('10314', 'VJc1917d79cd0c4f5f42519e362770d125c9f209c6'),
                                                    ('10314', 'VJ042669cc08161b30efa3b508346b648613a95047')],
      'route_to_crow_fly_ratio': {'10314': {'VJ042669cc08161b30efa3b508346b648613a95047': 0.0,
                                            'VJ37e93a6ebc1f8b2be99e4279776413113b7ce4c5': 0.9364835737183665,
                                            'VJ77530340dfe6e2a540002a6c7c283879d708dec6': 0.0,
                                            'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': 'Division by zero',
                                            'VJc1917d79cd0c4f5f42519e362770d125c9f209c6': 0.0,
                                            'VJfd74b67b9801ab3010f64fd130ec9ef9062470d3': 0.9364835737183665},
                                  '12430': {'VJ06420fdab0dfe5c8e7f2f9504df05cf6289cd7d3': 1.3239965103249995,
                                            'VJ06cd41dcd58d947097df4a8f33234ef423210154': 1.3239965103249995}}
     }

Something that is not included in the validity report (because MATSim doesn't insist on it being satified) is strong 
connectivity of PT. You can call `is_strongly_connected` on `Schedule` or the schedule components: `Service` and 
`Route`. The process builds a directed graph of stop connections (which you can build for inspection using 
`build_graph` on, again, `Schedule` or the schedule components: `Service` and `Route`).

    >>> n.schedule.is_strongly_connected()
    False
    >>> n.schedule.build_graph()
    <networkx.classes.digraph.DiGraph at 0x11d995750>

### Using Google Directions API for speed calculation

You can generate and send google directions API requests based on the network. The process will create a 'car' modal
subgraph and generate API requests for all edges in the subgraph. The number of requests is at most the number of edges
in the subgraph. The process simplifies edges using `osmnx` library's method to extract a chains of nodes with no
intersections, in this way reducing the number of requests. If your graph is already simplified, the number of requests
will be equal to the number of edges.
 You need to specify an upper bound for the number of requests you're happy to send, big networks 
generate many requests (even with the simplification) and you will be charged per request. You can generate
the requests first and inspect them before committing to running them.

    >>> api_requests = gn.google_directions.generate_requests(n=n)
    >>> len(api_requests)
    12345

To send requests to Google Direction API you need a key [(read more here)](https://developers.google.com/maps/documentation/directions/start).
After obtaining a key, you can:
 - pass it to the relevant function under `key` variable
 - set it as an environmental variable called `GOOGLE_DIR_API_KEY`
 - use AWS `Secrets Manager` [(read more here)](https://aws.amazon.com/secrets-manager/)
 
If passing the key directly to the function:

    >>> api_requests = gn.google_directions.send_requests_for_network(
            n=n, 
            key='google_directions_api_key',
            output_dir='../example_data/example_google_speed_data',
            traffic=True
        )

To set it as an environmental variable called `GOOGLE_DIR_API_KEY`, using command line:
    
    $ export GOOGLE_DIR_API_KEY='key'
    
    >>> api_requests = gn.google_directions.send_requests_for_network(
            n=n, 
            output_dir='../example_data/example_google_speed_data',
            traffic=True
        )

If you using AWS `Secrets Manager`, authenticate to your AWS account and then pass the `secret_name` and `region_name` 
to the `send_requests_for_network` 
method:

    >>> api_requests = gn.google_directions.send_requests_for_network(
            n=n, 
            output_dir='../example_data/example_google_speed_data',
            traffic=True,
            secret_name='secret_name', 
            region_name='region_name'
        )

This method will save derived results in the output directory provided, an example can be found here: 
`../example_data/example_google_speed_data`. It comprises of the google polyline of the response and speed derived from
distance and time taken to travel as well as information that was generated in order to make the response such as
the node ids in the network for which this response holds, the `path_nodes` which denote any extra nodes from the non
simplified chain of nodes/edges in the request, the polyline of the network path, encoded using the same polyline 
encoding as the Google request polyline; as well as spatial information about the origin and destination of the request
and timestamp.

You can read saved results:

    >>> api_requests = gn.google_directions.read_saved_api_results('../example_data/example_google_speed_data')

Once you have results, you can match them to the network:

    >>> google_edge_data = gn.google_directions.map_results_to_edges(api_requests)

This will create a dictionary of non-simplified edges to which the response data applies. This data can be applied to
the graph in the following way:

    >>> def modal_condition(value):
    >>>     return 'car' in value
    >>> _n.apply_attributes_to_edges(google_edge_data, conditions={'modes': modal_condition})
    
Resulting in two new data points in the relevant links: `google_speed` and `google_polyline`. You can compute
differences in speeds using:

    >>> def speed_difference(link_attribs):
            return link_attribs['freespeed'] - link_attribs['google_speed']
    
    >>> _n.apply_function_to_links(speed_difference, 'speed_difference')

Resulting in a new data point in the relevant links: `speed_difference`.

You can also choose to set google speed as the `freespeed` in the network. But be mindful if you use it for MATSim
simulations, `freespeed` denotes the maximum speed a vehicle can travel on a certain link, Google Directions API data
with `traffic=True` should be ran late at night/early morning ~4am local time to the network for any reliable results.
Otherwise you are adding traffic conditions to the network which should be simulated by demand (population) side of 
the model rather than supply (network).

    >>> def set_google_speed(link_attribs):
            return link_attribs['google_speed']
    
    >>> _n.apply_function_to_links(set_google_speed, 'freespeed')

### Standard outputs

You can generate a long list of outputs which are useful for validating and visualising the network and its schedule. 

    >>> n.generate_standard_outputs(output_dir='path/to/standard_outputs', gtfs_day='19700101')

Specifying `gtfs_day` is optional and only useful for generating visualisations which don't rise eyebrows.
In this bundle you get the following outputs:

    - network graph related
        - geojsons for car mode featuring 'freespeed', 'capacity', 'permlanes' (separately, because these can get large)
        - geojsons for all other modal subgraphs
    - schedule related
        - geojsons featuring schedule graph with vehicles per hour for every mode separately and all together (with 
        mode data present) in the schedule for all hours of the day, this can be used within kepler to animate across
        hours of the day. (Use 'filter' option on 'hour' field and click on the little clock)
        - the same as above for all modes together but subsetted for am/inter/pm peak within hours 7, 8, 9, 13, 16, 17, 
        18 for convenience (in case the big geojson may be too large to load in kepler)
        - png bar plots for vehicles per hour per:
            - PT service
            - PT stop
            (titles and file names include modes and human readable names for stops and services if present)

You can also generate standard outputs for schedule only:

    >>> n.schedule.generate_standard_outputs(output_dir='path/to/standard_outputs', gtfs_day='19700101')

### Routing

You can find shortest path between two nodes in the graph, using a modal subgraph or otherwise.

    >>> n.find_shortest_path(from_node, to_node)

will use the whole graph disregarding modes.

    >>> n.find_shortest_path(from_node, to_node, modes='car')

will compute a modal subgraph and use it for routing. You can also pass a list e.g. `['bike`, `walk`]`. 
If you have many node pair to process, it may be beneficial to
compute the modal subgraph of interest first and pass it to the method

    >>> car_g = n.modal_subgraph('car')
    >>> n.find_shortest_path(from_node, to_node, subgraph=car_g)

Specifying `'modes'` on top of giving the `subgraph` will also use given modes for preferential treatment if there is
ambiguity in which link should be chosen for the route (remember, there can be several links between the same two 
nodes). For example, if using mode `'bus'` and there are two links to choose from, one with modes: `['car', 'bus']` and
the other with just `['bus']`, preference will be given to the link dedicated to that mode. Otherwise, preference
will be given to links with higher `freespeed`.

You can also choose to return the chain of nodes instead:

    >>> n.find_shortest_path(from_node, to_node, return_nodes=True)

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