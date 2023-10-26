import argparse
import os
import sys

import nbformat
from nbconvert import MarkdownExporter
from traitlets.config import Config


def parse_args(cmd_args):
    arg_parser = argparse.ArgumentParser(
        description="Generate wiki markdown pages from Jupyter Notebook files"
    )
    arg_parser.add_argument(
        "-nd",
        "--notebook-directory",
        help="the path to the directory containing the notebooks",
        default=os.path.dirname(__file__),
    )
    arg_parser.add_argument(
        "-wd",
        "--wiki_directory",
        help="the path to the genet.wiki directory, you need to clone the genet.wiki prior to "
        "running",
        default=os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "genet.wiki"
        ),
    )
    return vars(arg_parser.parse_args(cmd_args))


def find_notebooks(notebooks_dir):
    notebook_paths = [f for f in os.listdir(notebooks_dir) if f.endswith(".ipynb")]
    notebook_paths.sort()
    return notebook_paths


if __name__ == "__main__":
    command_args = parse_args(sys.argv[1:])

    notebooks_dir = command_args["notebook_directory"]
    wiki_dir = command_args["wiki_directory"]

    c = Config()
    c.Application.log_level = "INFO"
    md_exporter = MarkdownExporter(config=c)

    notebooks = find_notebooks(command_args["notebook_directory"])
    for notebook in notebooks:
        print(f"Processing: {notebook}")
        with open(os.path.join(notebooks_dir, notebook)) as f:
            nb = nbformat.read(f, as_version=4)
            (body, resources) = md_exporter.from_notebook_node(nb)
        with open(os.path.join(wiki_dir, f"Usage:-{notebook[:-6]}.md".replace(" ", "-")), "w") as f:
            f.write(body)
