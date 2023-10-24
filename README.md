# Network Scenario Generator (GeNet)

[![DOI](https://zenodo.org/badge/265256468.svg)](https://zenodo.org/badge/latestdoi/265256468)


## Table of Contents
- [Overview](#overview)
- [Setup](#setup)
  * [Using Docker](#using-docker)
    + [Building the image](#build-the-image)
    + [Running GeNet from the container](#running-a-container-with-a-pre-baked-script)
  * [Installation as a Python Package](#installation-as-a-python-package)
    + [Native dependencies](#native-dependencies)
    + [A note on the mathematical solver](#a-note-on-the-mathematical-solver)
    + [Installing the native dependencies](#installing-the-native-dependencies)
    + [Install dev prereqs](#install-dev-prereqs)
    + [Install Python dependencies](#install-python-dependencies)
    + [Install GeNet in to the virtual environment](#install-genet-in-to-the-virtual-environment)
    + [Install Kepler dependencies](#install-kepler-dependencies)
- [Developing GeNet](#developing-genet)
  * [Unit tests](#unit-tests)
  * [Code coverage report](#generate-a-unit-test-code-coverage-report)
  * [Linting](#lint-the-python-code)
  * [Smoke testing Jupyter notebooks](#smoke-test-the-jupyter-notebooks)


## Overview

GeNet provides tools to represent and work with a multi-modal transport network with public transport (PT)
services. It is based on [MATSim's](https://www.matsim.org/) representation of such networks.

The goal of GeNet is to:
- Provide a formalised in-memory data structure for representing a multi-modal network with a PT service
- Enable using the data structure for tasks such as generating auxiliary MATSim files e.g. Road Pricing
- Simplify the process of modifying a network and provide a simple change log to track the differences between the input
and output networks.
- Provide validation methods to check for simple errors such as: whether a `Route` has more than one `Stop` or that the
underlying graph doesn't have any dead-ends or sources (a place which you can leave but cannot get back to).

The underlying 
network available to PT services (roads, railways, but also ferry/flight connections) uses a `networkx.MultiDiGraph`
with additional methods for `'links'` which are unique in `genet.Network` (`networkx.MultiDiGraph` accepts multiple 
edges between the same from and to node pair; referring to an edge in `networkx.MultiDiGraph` and `genet.Network`
has the same effects, i.e. the result is a dictionary indexed by the multi edge index). The PT services are 
represented through the `genet.Schedule` class which relies on other `genet` 
classes: the `Schedule` relies on a list of `genet.Service`'s, which in turn consists of a list of `genet.Route`'s.
Each `Route` class object has an attribute `stops` which consists of `genet.Stops` objects. The `Stops` carry spatial
information for the PT stop.


## Setup

GeNet CLI supports a number of different usage scenarios. For these you can use docker, which will save you the
work of installing GeNet locally:

### Using Docker
Docker is the recommended way to use GeNet if you do not plan to make any code changes.

#### Build the image

    docker build -t "cml-genet" .

#### Using the cli inside a container

    docker run cml-genet genet --help

to show the list of available commands, and e.g.

    docker run cml-genet genet simplify-network --help

to show description of the command and parameters:
```commandline
Usage: genet simplify-network [OPTIONS]

  Simplify a MATSim network by removing intermediate links from paths

Options:
  -n, --network PATH              Location of the input network.xml file
                                  [required]
  -s, --schedule PATH             Location of the input schedule.xml file
  -v, --vehicles PATH             Location of the input vehicles.xml file
  -p, --projection TEXT           The projection network is in, eg.
                                  "epsg:27700"  [required]
  -pp, --processes INTEGER        Number of parallel processes to split
                                  process across
  -vsc, --vehicle_scalings TEXT   Comma delimited list of scales for vehicles
  -od, --output_dir DIRECTORY     Output directory  [required]
  -fc, --force_strongly_connected_graph
                                  If True, checks for disconnected subgraphs
                                  for modes `walk`, `bike` and `car`. If there
                                  are more than one strongly connected
                                  subgraph, genet connects them with links at
                                  closest points in the graph. The links used
                                  to connect are weighted at 20% of
                                  surrounding freespeed and capacity values.
  --help                          Show this message and exit.
```

Note, you will reference data outside the docker container as inputs, the docker command will need the path to data
mounted and be referenced according to the alias given, e.g.

    docker run -v /local/path/:/mnt/ cml-genet genet simplify-network --network /mnt/network.xml [...]

If the input network file lives at `/local/path/network.xml`.

#### Running custom script inside a container

Say you write a script `/local/path/my_genet_scripts/script.py` and you want to run it inside a docker container. 
You will need to mount the local path to the container for the script to be found and use the generic `python` 
as part of your command:

    docker run -v /local/path/:/mnt/ cml-genet python /mnt/my_genet_scripts/script.py

Note, if you reference data inside your script, or pass them as arguments to the script, they need to reference the 
aliased path inside the container, here: `/mnt/`, rather than the path `/local/path/`.

### Installation as a Python Package / CLI

You can in your base installation of python or a virtual environment.
You can use GeNet's CLI to run pre-baked modifications or checks on networks.
You can also write your own python scripts, importing genet as a package, use IPython shell or Jupyter Notebook to load 
up a network, inspect or change it and save it out to file. Check out the 
[wiki pages](https://github.com/arup-group/genet/wiki/Functionality-and-Usage-Guide) and 
[example jupyter notebooks](https://github.com/arup-group/genet/tree/master/notebooks) 
for usage examples.

**Note:** if you plan only to _use_ GeNet rather than make code changes to it, you can avoid having to perform any
local installation by using [GeNet's Docker image](#using-docker). If you are going to make code changes or use GeNet's
CLI locally, follow the steps below:

#### Native dependencies
GeNet uses some Python libraries that rely on underlying native libraries for things like geospatial calculations and
linear programming solvers. Before you install GeNet's Python dependencies, you must first install these native
libraries.

#### A note on the mathematical solver
**Note**: The default CBC solver is pre-installed inside [GeNet's Docker image](#using-docker), which can save you some
installation effort

To use methods which snap public transit to the graph, GeNet uses a mathematical solver. If you won't be using such
functionality, you do not need to install this solver.
Methods default to [CBC](https://projects.coin-or.org/Cbc), an open source solver.
Another good open source choice is [GLPK](https://www.gnu.org/software/glpk/).
The solver you use needs to support MILP - mixed integer linear programming.

#### Installing the native dependencies
The commands for installing the necessary native libraries vary according to the operating system you are using, for
example:

| OS       | Commands |
|----------|----------|
|Mac OS    | `brew install spatialindex` <br/> `brew install gdal --HEAD` <br/> `brew install gdal` <br/> `brew tap coin-or-tools/coinor` <br/> `brew install coin-or-tools/coinor/cbc`|
|Ubuntu    | `sudo apt install libspatialindex-dev` <br/> `sudo apt install libgdal-dev` <br/> `sudo apt install coinor-cbc`|

#### Install dev prereqs
(Use equivalent linux or Windows package management as appropriate for your environment)

    brew install python3.7
    brew install virtualenv

#### Install Python dependencies
Create and activate a Python virtual environment

    virtualenv -p python3.7 venv
    source venv/bin/activate

#### Install GeNet in to the virtual environment
Finally, install `GeNet`'s Python dependencies

    pip install -e .

After installation, you should be able to successfully run the help command to see all possible commands:

    genet --help

To inspect a specific command, run e.g.:

    genet simplify-network --help

#### Install Kepler dependencies

Please follow [kepler's installation instructions](https://docs.kepler.gl/docs/keplergl-jupyter#install) to be able to 
use the visualisation methods. To see the maps in a jupyter notebook, make sure you enable widgets.
```
jupyter nbextension enable --py widgetsnbextension
```

## Developing GeNet

We welcome community contributions to GeNet; please see our [guide to contributing](CONTRIBUTING.md) and our
[community code of conduct](CODE_OF_CONDUCT.md). If you are making changes to the codebase, you should use the tools
described below to verify that the code still works. All of the following commands assume you are in the project's root
directory.

### Unit tests
To run unit tests within genet python environment:

    python -m pytest -vv tests

and within a docker container:

    docker run cml-genet python -m pytest -vv tests

### Generate a unit test code coverage report

To generate an HTML coverage report at `reports/coverage/index.html`:

    ./bash_scripts/code-coverage.sh

### Lint the python code

    ./bash_scripts/lint-check.sh

### Smoke test the Jupyter notebooks

    ./bash_scripts/notebooks-smoke-test.sh
