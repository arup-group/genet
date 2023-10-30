import os

from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

requirementPath = "requirements.txt"
install_requires = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires = f.read().splitlines()

setup(
    name="genet",
    version="4.0.0",
    author="Kasia Kozlowska",
    author_email="",
    description="MATSim network scenario generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arup-group/genet",
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=install_requires,
    include_package_data=True,
    entry_points={"console_scripts": ["genet = genet.cli:cli"]},
)
