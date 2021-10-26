# Network Scenario Generator (GeNet)

[![DOI](https://zenodo.org/badge/265256468.svg)](https://zenodo.org/badge/latestdoi/265256468)

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
    
    usage: reproject_network.py [-h] -n NETWORK [-s SCHEDULE] [-v VEHICLES] -cp
                                CURRENT_PROJECTION -np NEW_PROJECTION
                                [-p PROCESSES] -od OUTPUT_DIR
    
    Reproject a MATSim network
    
    optional arguments:
      -h, --help            show this help message and exit
      -n NETWORK, --network NETWORK
                            Location of the network.xml file
      -s SCHEDULE, --schedule SCHEDULE
                            Location of the schedule.xml file
      -v VEHICLES, --vehicles VEHCILES
      							  Location of the vehicles.xml file
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
inspect or change it and save it out to file. Check out the 
[wiki pages](https://github.com/arup-group/genet/wiki/Functionality-and-Usage-Guide) and 
[example jupyter notebooks](https://github.com/arup-group/genet/tree/master/notebooks) 
for usage examples.

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

Please follow [kepler's installation instructions](https://docs.kepler.gl/docs/keplergl-jupyter#install) to be able to 
use the visualisation methods. To see the maps in a jupyter notebook, make sure you enable widgets.
```
jupyter nbextension enable --py widgetsnbextension
```

### Unit Testing

#### Run the unit tests (from root dir)

    python -m pytest -vv tests

#### Generate a unit test code coverage report

To generate XML & HTML coverage reports to `reports/coverage`:
    
    ./bash_scripts/code-coverage.sh
