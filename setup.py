import os
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

requirementPath = "requirements.txt"
install_requires = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires = f.read().splitlines()

setup(
    name="genet",
    version="0.0.1",
    author="Kasia Kozlowska",
    author_email="",
    description="MATSim network scenario generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arup-group/genet",
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=install_requires,
)
