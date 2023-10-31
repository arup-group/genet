import os

import importlib_resources
import pytest

import genet.use.recipes as gn_recipes

GENET_ROOT_DIR = importlib_resources.files("genet").parent
EXAMPLE_DATA_DIR = GENET_ROOT_DIR / "example_data"


class RecipeDispenser:
    def __init__(self, recipe_name):
        self.recipe_name = recipe_name
        self.args_vault = {
            "network": EXAMPLE_DATA_DIR / "pt2matsim_network" / "network.xml",
            "schedule": EXAMPLE_DATA_DIR / "pt2matsim_network" / "schedule.xml",
            "vehicles": EXAMPLE_DATA_DIR / "pt2matsim_network" / "vehicles.xml",
            "projection": "epsg:27700",
            "elevation": EXAMPLE_DATA_DIR / "fitzrovia_elevation.tif",
            "null_value": 0.0,
            "vehicle_scalings": "1,10",
            "subset_conditions": "primary,motorway",
            "pt_modes": "bus",
            "network_snap_modes": "car",
            "teleport_modes": "bike",
            "step_size": 10,
            "distance_threshold": 20,
            "gtfs": EXAMPLE_DATA_DIR / "example_gtfs",
            "gtfs_day": "20190603",
            "snapping_distance": 40.0,
            "processes": 1,
            "osm": EXAMPLE_DATA_DIR / "example.osm",
            "osm_config": GENET_ROOT_DIR / "genet" / "configs" / "OSM" / "slim_config.yml",
            "connected_components": 1,
            "current_projection": "epsg:27700",
            "new_projection": "epsg:4326",
            "modes": "bus",
            "study_area": EXAMPLE_DATA_DIR / "Fitzrovia_polygon.geojson",
            "urban_geometries": EXAMPLE_DATA_DIR / "Fitzrovia_urban_polygon.geojson",
            "freespeed": 0.5,
            "capacity": 0.5,
            "requests_threshold": 1,
            "traffic_model": "best_guess",
            "departure_time": "now",
        }
        self.recipe_params = {
            "add_elevation_to_network": ["network", "projection", "elevation", "null_value"],
            "auto_schedule_fixes": [
                "network",
                "schedule",
                "vehicles",
                "projection",
                "vehicle_scalings",
            ],
            "generate_standard_outputs": ["network", "schedule", "vehicles", "projection"],
            "inspect_google_directions_requests_for_network": [
                "network",
                "subset_conditions",
                "projection",
            ],
            "intermodal_access_egress_network": [
                "network",
                "schedule",
                "vehicles",
                "projection",
                "pt_modes",
                "network_snap_modes",
                "teleport_modes",
                "step_size",
                "distance_threshold",
            ],
            "make_pt_network": [
                "network",
                "gtfs",
                "gtfs_day",
                "projection",
                "snapping_distance",
                "processes",
            ],
            "make_road_only_network": [
                "osm",
                "osm_config",
                "connected_components",
                "projection",
                "processes",
            ],
            "reproject_network": [
                "network",
                "schedule",
                "vehicles",
                "current_projection",
                "new_projection",
                "processes",
            ],
            "scale_vehicles": ["schedule", "vehicles", "projection", "vehicle_scalings"],
            "separate_modes_in_network": ["network", "projection", "modes"],
            "simplify_network": [
                "network",
                "schedule",
                "vehicles",
                "projection",
                "processes",
                "vehicle_scalings",
            ],
            "squeeze_external_area": [
                "network",
                "projection",
                "study_area",
                "freespeed",
                "capacity",
            ],
            "squeeze_urban_links": [
                "network",
                "projection",
                "study_area",
                "urban_geometries",
                "freespeed",
                "capacity",
            ],
            "validate_network": ["network", "schedule", "vehicles", "projection"],
            "send_google_directions_requests_for_network": [
                "network",
                "projection",
                "requests_threshold",
                "subset_conditions",
                "traffic_model",
                "departure_time",
            ],
        }

    def _get_function_arguments(self, params, auxiliary_args):
        _path_to = [
            "network",
            "schedule",
            "vehicles",
            "osm",
            "osm_config",
            "gtfs",
            "elevation",
            "study_area",
            "urban_geometries",
        ]
        _path_to = {param: f"path_to_{param}" for param in _path_to}
        _args = {_path_to.get(param, param): self.args_vault[param] for param in params}
        if auxiliary_args:
            _args = {**_args, **auxiliary_args}
        return _args

    @property
    def function_args(self) -> dict[str, str]:
        """
        Gives dictionary {function_param_name : argument_value} for a given recipe, for running recipe functions or
        checking cli ran the function with correct arguments
        """
        recipe_auxiliary_args = {
            "add_elevation_to_network": {
                "write_elevation_to_network": True,
                "write_slope_to_network": True,
                "write_slope_to_object_attribute_file": True,
                "save_jsons": True,
            },
            "make_pt_network": {"path_to_osm": None, "path_to_osm_config": None},
            "separate_modes_in_network": {"increase_capacity": True},
            "simplify_network": {"force_strongly_connected_graph": True},
            "send_google_directions_requests_for_network": {
                "api_key": None,
                "secret_name": None,
                "region_name": None,
            },
        }
        return self._get_function_arguments(
            self.recipe_params[self.recipe_name], recipe_auxiliary_args.get(self.recipe_name, {})
        )

    def _get_cli_args(self, params, flags):
        _args = [f"--{param}={self.args_vault[param]}" for param in params]
        if flags:
            _args = _args + [f"--{flag}" for flag in flags]
        return _args

    @property
    def cli_args(self) -> list[str]:
        """
        Gives list of arguments for given recipe for running recipe functions or checking cli ran
        the function with correct arguments
        """
        recipe_flags = {
            "separate_modes_in_network": ["increase_capacity"],
            "simplify_network": ["force_strongly_connected_graph"],
        }
        return self._get_cli_args(
            self.recipe_params[self.recipe_name], recipe_flags.get(self.recipe_name, [])
        )

    @property
    def expected_files(self) -> list[str]:
        """
        Gives list of expected files when running a given recipe function with function arguments
        """
        expected_files = {
            "add_elevation_to_network": [
                "link_slope_dictionary.json",
                "link_slopes.xml",
                "network.xml",
                "node_elevation_dictionary.json",
                os.path.join("supporting_outputs", "link_slope.geojson"),
                os.path.join("supporting_outputs", "node_elevation.geojson"),
                "validation_report_for_elevation.json",
            ],
            "auto_schedule_fixes": [
                "schedule.xml",
                "vehicles.xml",
                "1_perc_vehicles.xml",
                "10_perc_vehicles.xml",
            ],
            "generate_standard_outputs": [
                "network_nodes.geojson",
                "schedule_nodes.geojson",
                "summary_report.json",
                "network_links.geojson",
                "schedule_links.geojson",
                os.path.join("schedule", "speed", "pt_network_speeds.geojson"),
                os.path.join("schedule", "speed", "pt_speeds.geojson"),
                os.path.join("routing", "schedule_network_routes_geodataframe.geojson"),
            ],
            "inspect_google_directions_requests_for_network": [
                "api_requests.json",
                os.path.join("subset", "api_requests.json"),
            ],
            "intermodal_access_egress_network": [
                "vehicles.xml",
                "schedule.xml",
                os.path.join("supporting_outputs", "car_access_egress_links.geojson"),
                os.path.join("supporting_outputs", "stops.geojson"),
            ],
            "make_pt_network": [
                "vehicles.xml",
                "schedule.xml",
                "network.xml",
                "standard_outputs.zip",
            ],
            "make_road_only_network": ["network.xml"],
            "reproject_network": ["vehicles.xml", "schedule.xml", "network.xml"],
            "scale_vehicles": ["1_perc_vehicles.xml", "10_perc_vehicles.xml"],
            "separate_modes_in_network": [
                "validation_report.json",
                "network.xml",
                os.path.join("supporting_outputs", "mode_bus_after.geojson"),
                os.path.join("supporting_outputs", "mode_bus_before.geojson"),
            ],
            "simplify_network": [
                "vehicles.xml",
                "1_perc_vehicles.xml",
                "schedule.xml",
                "10_perc_vehicles.xml",
                "validation_report.json",
                "network.xml",
                "standard_outputs.zip",
                "link_simp_map.json",
            ],
            "squeeze_external_area": [
                "network.xml",
                os.path.join("supporting_outputs", "external_network_links.geojson"),
                os.path.join("supporting_outputs", "capacity_before.geojson"),
                os.path.join("supporting_outputs", "freespeed_after.geojson"),
                os.path.join("supporting_outputs", "capacity_after.geojson"),
                os.path.join("supporting_outputs", "freespeed_before.geojson"),
            ],
            "squeeze_urban_links": [
                "network.xml",
                os.path.join("supporting_outputs", "capacity_before.geojson"),
                os.path.join("supporting_outputs", "freespeed_after.geojson"),
                os.path.join("supporting_outputs", "urban_network_links.geojson"),
                os.path.join("supporting_outputs", "capacity_after.geojson"),
                os.path.join("supporting_outputs", "freespeed_before.geojson"),
            ],
            "validate_network": ["validation_report.json", "summary_report.json"],
            "send_google_directions_requests_for_network": [],
        }
        return expected_files[self.recipe_name]

    @property
    def expected_files_on_fail(self) -> list[str]:
        """
        Gives list of expected files when running a given recipe function that is expected to fail
        """
        if self.recipe_name == "send_google_directions_requests_for_network":
            return ["api_requests.json"]
        else:
            return []


@pytest.fixture(scope="function")
def invoke_function_and_check_files(tmpdir_factory):
    outdir = tmpdir_factory.mktemp("outdir")

    def _invoke_function_and_check_files(
        func: str,
        function_args: dict[str, str],
        expected_files: list = [],
        expected_files_on_fail: list = [],
    ):
        _check_output_files_do_not_exist(expected_files)
        try:
            getattr(gn_recipes, func)(**{**function_args, **{"output_dir": outdir}})
        except RuntimeError as e:
            _check_output_files_exist(expected_files_on_fail)
            raise e

        _check_output_files_exist(expected_files)

    def _check_output_files_do_not_exist(files: list):
        for file in files:
            file_path = os.path.join(outdir, file)
            assert not os.path.exists(file_path), f"File {file_path} exists but is not expected."

    def _check_output_files_exist(files: list):
        for file in files:
            file_path = os.path.join(outdir, file)
            assert os.path.exists(file_path), f"File {file_path} does not exist but is expected."

    return _invoke_function_and_check_files


def test_add_elevation_to_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("add_elevation_to_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_auto_schedule_fixes(invoke_function_and_check_files):
    recipe = RecipeDispenser("auto_schedule_fixes")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_generate_standard_outputs(invoke_function_and_check_files):
    recipe = RecipeDispenser("generate_standard_outputs")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_inspect_google_directions_requests_for_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("inspect_google_directions_requests_for_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_intermodal_access_egress_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("intermodal_access_egress_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_make_pt_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("make_pt_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_make_road_only_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("make_road_only_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_reproject_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("reproject_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_scale_vehicles(invoke_function_and_check_files):
    recipe = RecipeDispenser("scale_vehicles")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_separate_modes_in_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("separate_modes_in_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_simplify_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("simplify_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_squeeze_external_area(invoke_function_and_check_files):
    recipe = RecipeDispenser("squeeze_external_area")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_squeeze_urban_links(invoke_function_and_check_files):
    recipe = RecipeDispenser("squeeze_urban_links")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_validate_network(invoke_function_and_check_files):
    recipe = RecipeDispenser("validate_network")
    invoke_function_and_check_files(
        recipe.recipe_name, function_args=recipe.function_args, expected_files=recipe.expected_files
    )


def test_google_api_script_throws_error_without_api_key(invoke_function_and_check_files):
    recipe = RecipeDispenser("send_google_directions_requests_for_network")
    with pytest.raises(RuntimeError) as excinfo:
        invoke_function_and_check_files(
            recipe.recipe_name,
            function_args=recipe.function_args,
            expected_files=recipe.expected_files,
        )

    assert excinfo.match("Number of requests exceeded the threshold")
