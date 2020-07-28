from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

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
    install_requires=[
        'networkx',
        's2sphere',
        'pyproj',
        'pytest-cov',
        'pytest',
        'pytest-mock',
        'dictdiffer==0.8.1',
        'pandas',
        'lxml',
        'xmltodict',
        'anytree',
        'osmnx==0.15.0',
        'osmread',
        'PyYAML',
        'boto3==1.14.16',
        'requests-futures==1.0.0',
        'polyline==1.4.0',
        'tqdm'
    ],
)
