# Contributing

Thank you for considering contributing to GeNet! We're really excited to hear your opinions on the project and any ideas
you may have on how it can be better! Please discuss the change you wish to make via GitHub issue,
e-mail ([citymodelling@arup.com](mailto:citymodelling@arup.com)), or any other method with the owners of 
this repository before making a change. 

Please note we have a code of conduct. Please follow it in all your interactions with the project.

## Pull Request Process

1. All new work is done in a branch taken from master, details can be found here:
[feature branch workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow)
2. Ensure your work is covered by unit tests to the required percentage level. This script 
[`bash_scripts/code-coverage.sh`](https://github.com/arup-group/genet/blob/master/bash_scripts/code-coverage.sh)
 will help both in checking that the coverage level is satisfied and investigating places in code that have not been 
 covered by the tests (via an output file `reports/coverage/index.html` which can be viewed in a browser).
3. Provide [docstrings](https://www.python.org/dev/peps/pep-0257/) for new methods 
4. Perform linting locally using ```flake8 . --max-line-length 120 --count  --show-source --statistics --exclude=scripts,tests```
5. Add or update dependencies in `requirements.txt` if applicable
6. Ensure the CI build pipeline (Actions tab in GitHub) completes successfully for your branch. The pipeline performs 
automated PEP8 checks and runs unit tests in a fresh environment, as well as installation of all dependencies.
7. Add to or generate a new jupyter notebook in `notebooks` directory which takes the user through your new feature or
change.
8. Add section in the `README.md` which shows usage of your new feature. This can be paraphrased from the jupyter
notebook.
9. If the feature is to be used in an automated workflow through the docker image, create a script in the `scripts`
directory. Please use existing scripts as templates.
10. Submit your Pull Request, describing the feature, linking to any relevant GitHub issues and request review from at 
least two developers.
11. You may merge the Pull Request in once you have the sign-off of two other developers, or if you 
do not have permission to do that, you may request one of the reviewers to merge it for you.

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or
advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic
  address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

### Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in
response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or
reject comments, commits, code, wiki edits, issues, and other contributions
that are not aligned to this Code of Conduct, or to ban temporarily or
permanently any contributor for other behaviors that they deem inappropriate,
threatening, offensive, or harmful.

### Scope

This Code of Conduct applies both within project spaces and in public spaces
when an individual is representing the project or its community. Examples of
representing a project or community include using an official project e-mail
address, posting via an official social media account, or acting as an appointed
representative at an online or offline event. Representation of a project may be
further defined and clarified by project maintainers.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported by contacting the project team at [citymodelling@arup.com](mailto:citymodelling@arup.com). All
complaints will be reviewed and investigated and will result in a response that
is deemed necessary and appropriate to the circumstances. The project team is
obligated to maintain confidentiality with regard to the reporter of an incident.
Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good
faith may face temporary or permanent repercussions as determined by other
members of the project's leadership.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at [http://contributor-covenant.org/version/1/4][version]

[homepage]: http://contributor-covenant.org
[version]: http://contributor-covenant.org/version/1/4/