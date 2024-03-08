
# Using GeNet as a Docker image

If you have [installed GeNet as a Docker image](installation.md#using-docker), you can follow the steps here to run the GeNet CLI and to run your own scripts.

## Using the cli inside a container

Use `docker run cml-genet genet ...` to run the command line scripts within the Docker image, e.g.:

```shell
docker run cml-genet genet simplify-network --network /path/to/network.xml [...]
```

!!! note
    You will reference data outside the docker container as inputs, the docker command will need the path to data
    mounted and be referenced according to the alias given, e.g.

    ```shell
    docker run -v /local/path/:/mnt/ cml-genet genet simplify-network --network /mnt/network.xml [...]
    ```

    If the input network file lives at `/local/path/network.xml`.

A full list of the available command line scripts is given on our [CLI page](api/cli.md).
You can also get a list of options directly from the image:

```shell
docker run cml-genet genet --help
```

to show the list of available commands, and e.g.

```shell
docker run cml-genet genet simplify-network --help
```

to show description of the command and parameters.

## Running custom script inside a container

Say you write a script `/local/path/my_genet_scripts/script.py` and you want to run it inside a docker container.
You will need to mount the local path to the container for the script to be found and use the generic `python`
as part of your command:

```shell
docker run -v /local/path/:/mnt/ cml-genet python /mnt/my_genet_scripts/script.py
```

!!! note
    If you reference data inside your script, or pass them as arguments to the script,
    they need to reference the aliased path inside the container.
    Here: `/mnt/`, rather than the path `/local/path/`.