# Contributing

When it comes to planning in the built environment, we think transparency is critical. The shape and operations of our shared infrastructure and public spaces impacts individuals’ access to employment opportunities, education, social communities, clean air, and safe mobility options.
We think open source, agent based models are the future for transparent, granular city planning. So we built GeNet which helps to make the process of modifying and validating MATSim transport networks a little less painful.

Thank you for considering contributing to GeNet! We're really excited to hear your opinions on the project and any ideas
you may have on how it can be better!

Please note we have a code of conduct. Please follow it in all your interactions with the project.

## Ways to Contribute

There are a number of ways you can contribute to the project. The major two are:
- Submitting a GitHub issue. This could involve:
    - Logging a bug or undesirable behaviour
    - Recording area of possible improvement
    - Requesting a change or addition of a new feature
- Contributing code. Our work is never done, if you have an idea how you could make GeNet better or if you think you
could generalise it:
    - You can outline the new feature or desired behaviour in a GitHub issue and send us an email on [citymodelling@arup.com](mailto:citymodelling@arup.com)
    to let us know you're willing to work on it. We may invite you for a brief rubber-ducking session to go through
    your idea in more detail. The aim is to mature your idea with one (or more) GeNet developers and to flag
    any possible blocks or implementation issues to be aware of.
    - Please follow advice below on Contributing Code, working in a branch and the Pull Request process.
    - You may continue to, and are encouraged to, keep in touch and reach out to us throughout your development work.

See this helpful site on [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/) for more ideas
 on how you could contribute. Get in touch with us via email [citymodelling@arup.com](mailto:citymodelling@arup.com).

## Submitting Issues

If you have an idea for an enhancement, a change or addition of new feature or behaviour for GeNet or a record of a bug
you can communicate this to us in detail through a written account as a GitHub issue on GeNet's [issues page](https://github.com/arup-group/genet/issues).

A good issue will outline the problem in a full written format. It is helpful to include screenshots, especially to
highlight any physical issues with the network. It is also helpful to include why you think the new feature would be
useful, what problem is it solving and whether there is a real-world cases study that would benefit from this
improvement.

In case of bugs, please provide the full error message, the OS and
information about the environment in which the process had been ran. It is also helpful to include a small
(if possible) set of data on which the problem can be recreated---at the very least, a thorough description of the
input data should be included.

See this page on [Creating an issue](https://github.com/arup-group/genet/issues) on GitHub to learn how to submit an
issue.

## Submitting changes

Look at the [development guide in our documentation](https://arup-group.github.io/genet/contributing) for information on how to get set up for development.

<!--- the "--8<--" html comments define what part of this file to add to the index page of the documentation -->
<!--- --8<-- [start:docs] -->

To contribute changes:

1. Fork the project on GitHub.
2. Create a feature branch to work on in your fork (`git checkout -b new-fix-or-feature`).
3. Test your changes using `pytest`.
4. Commit your changes to the feature branch (you should have `pre-commit` installed to ensure your code is correctly formatted when you commit changes).
5. Push the branch to GitHub (`git push origin new-fix-or-feature`).
6. On GitHub, create a new [pull request](https://github.com/arup-group/genet/pull/new/main) from the feature branch.

### Pull requests

Before submitting a pull request, check whether you have:

- Added your changes to `CHANGELOG.md`.
- Added or updated documentation for your changes.
- Added tests if you implemented new functionality or fixed a bug.

When opening a pull request, please provide a clear summary of your changes!

### Commit messages

Please try to write clear commit messages. One-line messages are fine for small changes, but bigger changes should look like this:

    A brief summary of the commit (max 50 characters)

    A paragraph or bullet-point list describing what changed and its impact,
    covering as many lines as needed.

### Code conventions

Start reading our code and you'll get the hang of it.

We mostly follow the official [Style Guide for Python Code (PEP8)](https://www.python.org/dev/peps/pep-0008/).

We have chosen to use the uncompromising code formatter [`black`](https://github.com/psf/black/) and the linter [`ruff`](https://beta.ruff.rs/docs/).
When run from the root directory of this repo, `pyproject.toml` should ensure that formatting and linting fixes are in line with our custom preferences (e.g., 100 character maximum line length).
The philosophy behind using `black` is to have uniform style throughout the project dictated by code.
Since `black` is designed to minimise diffs, and make patches more human readable, this also makes code reviews more efficient.
To make this a smooth experience, you should run `pre-commit install` after setting up your development environment, so that `black` makes all the necessary fixes to your code each time you commit, and so that `ruff` will highlight any errors in your code.
If you prefer, you can also set up your IDE to run these two tools whenever you save your files, and to have `ruff` highlight erroneous code directly as you type.
Take a look at their documentation for more information on configuring this.

We require all new contributions to have docstrings for all modules, classes and methods.
When adding docstrings, we request you use the [Google docstring style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

## Release checklist

### Pre-release

- [ ] Make sure all unit and integration tests pass (This is best done by creating a pre-release pull request).
- [ ] Re-run tutorial Jupyter notebooks (`pytest examples/ --overwrite`).
- [ ] Make sure documentation builds without errors (`mike deploy [version]`, where `[version]` is the current minor release of the form `X.Y`).
- [ ] Make sure the [changelog][changelog] is up-to-date, especially that new features and backward incompatible changes are clearly marked.

### Create release

- [ ] Bump the version number in `genet/__init__.py`
- [ ] Update the [changelog][changelog] with final version number of the form `vX.Y.Z`, release date, and github `compare` link (at the bottom of the page).
- [ ] Commit with message `Release vX.Y.Z`, then add a `vX.Y.Z` tag.
- [ ] Create a release pull request to verify that the conda package builds successfully.
- [ ] Once the PR is approved and merged, create a release through the GitHub web interface, using the same tag, titling it `Release vX.Y.Z` and include all the changelog elements that are *not* flagged as **internal**.

### Post-release

- [ ] Update the changelog, adding a new `[Unreleased]` heading.
- [ ] Update `genet/__init__.py` to the next version appended with `.dev0`, in preparation for the next main commit.

<!--- --8<-- [end:docs] -->

## Attribution

The Contribution Guide was adapted from [PurpleBooth's Template](https://gist.github.com/PurpleBooth/b24679402957c63ec426) and the [Calliope project's contribution guidelines](https://github.com/calliope-project/calliope/blob/main/CONTRIBUTING.md).
