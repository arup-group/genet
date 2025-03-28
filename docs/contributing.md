# Contributing

GeNet is an actively maintained and utilised project.

## How to contribute

to report issues, request features, or exchange with our community, just follow the links below.

__Is something not working?__

[:material-bug: Report a bug](https://github.com/arup-group/genet/issues/new?template=BUG-REPORT.yml "Report a bug in genet by creating an issue and a reproduction"){ .md-button }

__Missing information in our docs?__

[:material-file-document: Report a docs issue](https://github.com/arup-group/genet/issues/new?template=DOCS.yml "Report missing information or potential inconsistencies in our documentation"){ .md-button }

__Want to submit an idea?__

[:material-lightbulb-on: Request a change](https://github.com/arup-group/genet/issues/new?template=FEATURE-REQUEST.yml "Propose a change or feature request or suggest an improvement"){ .md-button }

__Have a question or need help?__

[:material-chat-question: Ask a question](https://github.com/arup-group/genet/discussions "Ask questions on our discussion board and get in touch with our community"){ .md-button }

## Developing genet

To find beginner-friendly existing bugs and feature requests you may like to start out with, take a look at our [good first issues](https://github.com/arup-group/genet/contribute).

### Setting up a development environment

To create a development environment for genet, with all libraries required for development and quality assurance installed, it is easiest to install genet using the [mamba](https://mamba.readthedocs.io/en/latest/index.html) package manager, as follows:

1. Install mamba with the [Mambaforge](https://github.com/conda-forge/miniforge#mambaforge) executable for your operating system.
2. Open the command line (or the "miniforge prompt" in Windows).
3. Download (a.k.a., clone) the genet repository: `git clone git@github.com:arup-group/genet.git`
4. Change into the `genet` directory: `cd genet`
5. Create the genet mamba environment: `mamba create -n genet -c conda-forge -c city-modelling-lab --file requirements/base.txt --file requirements/dev.txt`
6. Activate the genet mamba environment: `mamba activate genet`
7. Install the cml-genet package into the environment, in editable mode and ignoring dependencies (we have dealt with those when creating the mamba environment): `pip install --no-deps -e .`

All together:

--8<-- "README.md:docs-install-dev"

If installing directly with pip, you can install these libraries using the `dev` option, i.e., `pip install -e '.[dev]'`
Either way, you should add your environment as a jupyter kernel, so the example notebooks can run in the tests: `ipython kernel install --user --name=genet`
If you plan to make changes to the code then please make regular use of the following tools to verify the codebase while you work:

- `pre-commit`: run `pre-commit install` in your command line to load inbuilt checks that will run every time you commit your changes.
The checks are: 1. check no large files have been staged, 2. lint python files for major errors, 3. format python files to conform with the [PEP8 standard](https://peps.python.org/pep-0008/).
You can also run these checks yourself at any time to ensure staged changes are clean by calling `pre-commit`.
- `pytest` - run the unit test suite and check test coverage.

!!! note
    If you already have an environment called `genet` on your system (e.g., for a stable installation of the package), you will need to [chose a different environment name][choosing-a-different-environment-name].
    You will then need to add this as a pytest argument when running the tests: `pytest --nbmake-kernel=[my-env-name]`.

### Rapid-fire testing

The following options allow you to strip down the test suite to the bare essentials:

1. The test suite includes unit tests and integration tests (in the form of jupyter notebooks found in the `examples` directory).
The integration tests can be slow, so if you want to avoid them during development, you should run `pytest tests/`.
2. You can avoid generating coverage reports, by adding the `--no-cov` argument: `pytest --no-cov`.

All together:

``` shell
pytest tests/ --no-cov
```

!!! note
    If you are debugging failing tests using the `--pdb` flag, tests will only run on one thread instead of the default (which is the maximum number of threads your machine has available).
    This will slow down your tests, so do not use `--pdb` unless you are actively debugging.

## Updating the project when the template updates

This project has been built with [cruft](https://cruft.github.io/cruft/) based on the [Arup Cookiecutter template](https://github.com/arup-group/cookiecutter-pypackage).
When changes are made to the base template, they can be merged into this project by running `cruft update` from the  `genet` conda environment.

You may be prompted to do this when you open a Pull Request, if our automated checks identify that the template is newer than that used in the project.

## Submitting changes

--8<-- "CONTRIBUTING.md:docs"
