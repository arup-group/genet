# Network Scenario Generator (GeNet)

[![DOI](https://zenodo.org/badge/265256468.svg)](https://zenodo.org/badge/latestdoi/265256468)

## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
  * [Using Docker](#using-docker--recommended-)
    + [Building the image](#build-the-image)
    + [Running GeNet from the container](#running-a-container-with-a-pre-baked-script)
  * [Installation as a Python Package](#installation-as-a-python-package--if-you-don-t-want-to-use-docker-)
    + [Native dependencies](#install-native-dependencies)
    + [A note on the mathematical solver](#a-note-on-the-mathematical-solver)
    + [Installing the native dependencies](#installing-the-native-dependencies-into-your-o-s)
    + [Install dev prereqs](#install-dev-prereqs--use-equivalent-linux-or-windows-package-management-)
    + [Install Python dependencies](#install-python-dependencies)
    + [Install GeNet in to the virtual environment](#install-genet-in-to-the-virtual-environment)
    + [Install Kepler dependencies](#install-kepler-dependencies)
- [Developing GeNet](#developing-genet)
  * [Unit tests](#run-the-unit-tests--from-root-dir-)
  * [Code coverage report](#generate-a-unit-test-code-coverage-report)
  * [Linting](#lint-the-python-code)
  * [Smoke testing Jupyter notebooks](#smoke-test-the-jupyter-notebooks)

## Overview

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

To run pre-baked scripts that use genet in a number of different scenarios you can use docker, which will save you the
work of installing GeNet locally:

### Using Docker (recommended)
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


### Installation as a Python Package (if you don't want to use Docker)

#### Install native dependencies
GeNet uses some Python libraries that rely on underlying native libraries for things like geospatial calculations and
linear programming solvers. Before you install GeNet's Python dependencies, you must first install these native
libraries.

**Note:** if you plan only to _use_ GeNet rather than make code changes to it, you can avoid having to perform any
local installation by using [GeNet's Docker image](#using-docker).

#### A note on the mathematical solver

**Note**: The default CBC solver is pre-installed inside GeNet's Docker image, which can save you some effort

To use methods which snap public transit to the graph, GeNet uses a mathematical solver. If you
won't be using such functionality, you do not need to install this solver.
Methods default to [CBC](https://projects.coin-or.org/Cbc), an open source solver.
Another good open source choice is [GLPK](https://www.gnu.org/software/glpk/).
The solver needs to support MILP - mixed integer linear programming.

#### Installing the native dependencies into your O/S
The commands for installing these native libraries vary according to the operating system you are using:

| OS       | Commands |
|----------|----------|
|Mac OS    | `brew install spatialindex` <br/> `brew install gdal --HEAD` <br/> `brew install gdal` <br/> `brew tap coin-or-tools/coinor` <br/> `brew install coin-or-tools/coinor/cbc`|
|Ubuntu    | `sudo apt install libspatialindex-dev` <br/> `sudo apt install libgdal-dev` <br/> `sudo apt install coinor-cbc`|

#### Install dev prereqs (use equivalent linux or windows package management)

    brew install python3.7
    brew install virtualenv

#### Install Python dependencies
Create and activate a Python virtual environment

    virtualenv -p python3.7 venv
    source venv/bin/activate

#### Install GeNet in to the virtual environment
Finally install `GeNet`'s Python dependencies

    pip install -e .

#### Install Kepler dependencies

Please follow [kepler's installation instructions](https://docs.kepler.gl/docs/keplergl-jupyter#install) to be able to 
use the visualisation methods. To see the maps in a jupyter notebook, make sure you enable widgets.
```
jupyter nbextension enable --py widgetsnbextension
```

    
## Developing GeNet

We welcome community contributions to GeNet; please see our [guide to contributing](CONTRIBUTING.md) and our
[community code of conduct](CODE_OF_CONDUCT.md). If you are making changes to the codebase, you should use these tools
to verify that the code still works.

### Run the unit tests (from root dir)

    python -m pytest -vv tests

### Generate a unit test code coverage report

To generate an HTML coverage report at `reports/coverage/index.html`:

    ./bash_scripts/code-coverage.sh

### Lint the python code

    ./bash_scripts/lint-check.sh

### Smoke test the Jupyter notebooks

    ./bash_scripts/notebooks-smoke-test.sh

