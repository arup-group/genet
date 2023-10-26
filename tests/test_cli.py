import os
import pytest
import importlib_resources
from click.testing import CliRunner

from genet import cli


GENET_ROOT_DIR = importlib_resources.files("genet").parent
EXAMPLE_DATA_DIR = GENET_ROOT_DIR / 'example_data'

EXAMPLE_NETWORK = EXAMPLE_DATA_DIR / 'pt2matsim_network' / 'network.xml'
EXAMPLE_SCHEDULE = EXAMPLE_DATA_DIR / 'pt2matsim_network' / 'schedule.xml'
EXAMPLE_VEHICLES = EXAMPLE_DATA_DIR / 'pt2matsim_network' / 'vehicles.xml'
PROJECTION = 'epsg:27700'

@pytest.fixture(scope="function")
def invoke_runner_and_check_files(tmpdir_factory):
    outdir = tmpdir_factory.mktemp("outdir")

    def _invoke_runner_and_check_files(
        func: str, args: list[str], expected_files: list = [], expected_files_on_fail: list = []
    ):
        _check_output_files_do_not_exist(expected_files)
        runner = CliRunner()
        result = runner.invoke(getattr(cli, func), args + [f'--output_dir={outdir}'])
        try:
            assert result.exit_code == 0, f"Script {func} failed."
        except AssertionError as e:
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

    return _invoke_runner_and_check_files


def test_add_elevation_to_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
         "add_elevation_to_network",
        args=[
            f'--network={EXAMPLE_NETWORK}',
            f'--projection={PROJECTION}',
            f'--elevation={EXAMPLE_DATA_DIR / "fitzrovia_elevation.tif"}',
            '--null_value=0',
        ],
        expected_files=[
            'link_slope_dictionary.json',
            'link_slopes.xml',
            'network.xml',
            'node_elevation_dictionary.json',
            os.path.join('supporting_outputs', 'link_slope.geojson'),
            os.path.join('supporting_outputs', 'node_elevation.geojson'),
            'validation_report_for_elevation.json'
        ]
    )


def test_auto_schedule_fixes(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "auto_schedule_fixes",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}',
            '--vehicle_scalings=1,10'
        ],
        expected_files=[
            'schedule.xml',
            'vehicles.xml',
            '1_perc_vehicles.xml',
            '10_perc_vehicles.xml',
        ]
    )


def test_generate_standard_outputs(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "generate_standard_outputs",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}'
        ],
        expected_files=[
            'network_nodes.geojson',
            'schedule_nodes.geojson',
            'summary_report.json',
            'network_links.geojson',
            'schedule_links.geojson',
            os.path.join('schedule', 'speed', 'pt_network_speeds.geojson'),
            os.path.join('schedule', 'speed', 'pt_speeds.geojson'),
            os.path.join('routing', 'schedule_network_routes_geodataframe.geojson')
        ]
    )


def test_inspect_google_directions_requests_for_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "inspect_google_directions_requests_for_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            '--subset_conditions=primary,motorway',
            f'--projection={PROJECTION}'
        ],
        expected_files=[
            'api_requests.json',
            os.path.join('subset', 'api_requests.json')
        ]
    )


def test_intermodal_access_egress_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "intermodal_access_egress_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}',
            '--pt_modes=bus',
            '--network_snap_modes=car',
            '--teleport_modes=bike',
            '--step_size=10',
            '--distance_threshold=20'
        ],
        expected_files=[
            'vehicles.xml',
            'schedule.xml',
            os.path.join('supporting_outputs', 'car_access_egress_links.geojson'),
            os.path.join('supporting_outputs', 'stops.geojson')
        ]
    )


def test_make_pt_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "make_pt_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--gtfs={os.path.join(EXAMPLE_DATA_DIR, "example_gtfs")}',
            '--gtfs_day=20190603',
            f'--projection={PROJECTION}',
            '--snapping_distance=40',
            '--processes=2'
        ],
        expected_files=[
            'vehicles.xml',
            'schedule.xml',
            'network.xml',
            'standard_outputs.zip'
        ]
    )


def test_make_road_only_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "make_road_only_network",
        args= [
            f'--osm={os.path.join(EXAMPLE_DATA_DIR, "example.osm")}',
            f'--osm_config={os.path.join(GENET_ROOT_DIR, "genet", "configs", "OSM", "slim_config.yml")}',
            '--connected_components=1',
            f'--projection={PROJECTION}',
            '--processes=2'
        ],
        expected_files=[
            'network.xml',
        ]
    )


def test_reproject_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "reproject_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            '--current_projection=epsg:27700',
            '--new_projection=epsg:4326',
            '--processes=2',

        ],
        expected_files=[
            'vehicles.xml',
            'schedule.xml',
            'network.xml',
        ]
    )


def test_scale_vehicles(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "scale_vehicles",
        args= [
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}',
            '--vehicle_scalings', '1,10',

        ],
        expected_files=[
            '1_perc_vehicles.xml',
            '10_perc_vehicles.xml'
        ]
    )


def test_separate_modes_in_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "separate_modes_in_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--projection={PROJECTION}',
            '--modes=bus',
            '--increase_capacity',

        ],
        expected_files=[
            'validation_report.json',
            'network.xml',
            os.path.join('supporting_outputs', 'mode_bus_after.geojson'),
            os.path.join('supporting_outputs', 'mode_bus_before.geojson'),
        ]
    )


def test_simplify_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "simplify_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}',
            '--processes=1',
            '--force_strongly_connected_graph',
            '--vehicle_scalings=1,10',

        ],
        expected_files=[
            'vehicles.xml',
            '1_perc_vehicles.xml',
            'schedule.xml',
            '10_perc_vehicles.xml',
            'validation_report.json',
            'network.xml',
            'standard_outputs.zip',
            'link_simp_map.json'
        ]
    )


def test_squeeze_external_area(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "squeeze_external_area",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--projection={PROJECTION}',
            f'--study_area={os.path.join(EXAMPLE_DATA_DIR, "Fitzrovia_polygon.geojson")}',
            '--freespeed=0.5',
            '--capacity=0.5',

        ],
        expected_files=[
            'network.xml',
            os.path.join('supporting_outputs', 'external_network_links.geojson'),
            os.path.join('supporting_outputs', 'capacity_before.geojson'),
            os.path.join('supporting_outputs', 'freespeed_after.geojson'),
            os.path.join('supporting_outputs', 'capacity_after.geojson'),
            os.path.join('supporting_outputs', 'freespeed_before.geojson'),
        ]
    )


def test_squeeze_urban_links(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "squeeze_urban_links",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--projection={PROJECTION}',
            f'--study_area={os.path.join(EXAMPLE_DATA_DIR, "Fitzrovia_polygon.geojson")}',
            f'--urban_geometries={os.path.join(EXAMPLE_DATA_DIR, "Fitzrovia_urban_polygon.geojson")}',
            '--freespeed', '0.5',
            '--capacity', '0.5',

        ],
        expected_files=[
            'network.xml',
            os.path.join('supporting_outputs', 'capacity_before.geojson'),
            os.path.join('supporting_outputs', 'freespeed_after.geojson'),
            os.path.join('supporting_outputs', 'urban_network_links.geojson'),
            os.path.join('supporting_outputs', 'capacity_after.geojson'),
            os.path.join('supporting_outputs', 'freespeed_before.geojson')
        ]
    )


def test_validate_network(invoke_runner_and_check_files):
    invoke_runner_and_check_files(
        "validate_network",
        args= [
            f'--network={EXAMPLE_NETWORK}',
            f'--schedule={EXAMPLE_SCHEDULE}',
            f'--vehicles={EXAMPLE_VEHICLES}',
            f'--projection={PROJECTION}',
        ],
        expected_files=['validation_report.json']
    )


def test_google_api_script_throws_error_without_api_key(invoke_runner_and_check_files):
    with pytest.raises(AssertionError) as excinfo:
        invoke_runner_and_check_files(
            "send_google_directions_requests_for_network",
            args= [
                f'--network={EXAMPLE_NETWORK}',
                f'--projection={PROJECTION}',
                '--requests_threshold=1',
                '--subset_conditions=primary,motorway',
                '--traffic_model=best_guess',
                '--departure_time=now'
            ],
            expected_files_on_fail=['api_requests.json']
        )

    assert excinfo.match('Script send_google_directions_requests_for_network failed.')
    assert excinfo.match('Number of requests exceeded the threshold')
