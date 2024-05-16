
# Installation

## Using Docker

If you want to avoid Python environments, you can use a Docker image to run GeNet.
To build the image:

--8<-- "README.md:docs-install-docker"

Instructions for running GeNet from within the Docker image can be found [here](docker.md).

## Setting up a user environment

As a `genet` user, it is easiest to install using the [mamba](https://mamba.readthedocs.io/en/latest/index.html) package manager, as follows:

1. Install mamba with the [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge) executable for your operating system.
1. Open the command line (or the "miniforge prompt" in Windows).
1. Download (a.k.a., clone) the genet repository: `git clone git@github.com:{{ cookiecutter.repository_owner }}/genet.git`
1. Change into the `genet` directory: `cd genet`
1. Create the genet mamba environment: `mamba create -n genet -c conda-forge -c city-modelling-lab --file requirements/base.txt`
1. Activate the genet mamba environment: `mamba activate genet`
1. Install the cml-genet package into the environment, ignoring dependencies (we have dealt with those when creating the mamba environment): `pip install --no-deps .`

All together:

--8<-- "README.md:docs-install-user"

### Running the example notebooks

If you have followed the non-developer installation instructions above, you will need to install `jupyter` into your `genet` environment to run the [example notebooks](https://github.com/arup-group/genet/tree/main/examples):

``` shell
mamba install -n genet jupyter
```

With Jupyter installed, it's easiest to then add the environment as a jupyter kernel:

``` shell
mamba activate genet
ipython kernel install --user --name=genet
jupyter notebook
```

### Choosing a different environment name

If you would like to use a different name to `genet` for your mamba environment, the installation becomes (where `[my-env-name]` is your preferred name for the environment):

``` shell
mamba create -n [my-env-name] -c conda-forge -c city-modelling-lab --file requirements/base.txt
mamba activate [my-env-name]
ipython kernel install --user --name=[my-env-name]
```

## Setting up a development environment

The install instructions are slightly different to create a development environment compared to a user environment:

--8<-- "README.md:docs-install-dev"

For more detailed installation instructions specific to developing the genet codebase, see our [development documentation](contributing.md#setting-up-a-development-environment).

## A note on the mathematical solver

!!! note
    The default CBC solver is pre-installed inside [GeNet's Docker image](#using-docker), which can save you some installation effort.

To use methods which snap public transit to the graph, GeNet uses a mathematical solver.
If you won't be using such functionality, you do not need to install this solver.
Methods default to [CBC](https://projects.coin-or.org/Cbc), an open source solver.
On Non-Windows devices, you can install this solver (`coin-or-cbc`) along with your other requirements when creating the environment: `mamba create -n genet -c conda-forge -c city-modelling-lab coin-or-cbc --file requirements/base.txt`,
or install it after the fact `mamba install -n genet coin-or-cbc`

Any solver [supported by Pyomo](https://pyomo.readthedocs.io/en/stable/solving_pyomo_models.html#supported-solvers) can be used.
Another good open source choice is [GLPK](https://www.gnu.org/software/glpk/).
The solver you use needs to support MILP - mixed integer linear programming.
