import subprocess
import os
import pytest

GENET_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EXAMPLE_DATA_DIR = os.path.join(GENET_ROOT_DIR, 'example_data')

EXAMPLE_NETWORK = os.path.join(EXAMPLE_DATA_DIR, 'pt2matsim_network', 'network.xml')
EXAMPLE_SCHEDULE = os.path.join(EXAMPLE_DATA_DIR, 'pt2matsim_network', 'schedule.xml')
EXAMPLE_VEHICLES = os.path.join(EXAMPLE_DATA_DIR, 'pt2matsim_network', 'vehicles.xml')
PROJECTION = 'epsg:27700'

SCRIPTS = {
    'add_elevation_to_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--projection', PROJECTION,
            '--elevation', os.path.join(EXAMPLE_DATA_DIR, 'fitzrovia_elevation.tif'),
            '--null_value', '0',
            '--write_elevation_to_network', 'True',
            '--write_slope_to_network', 'True',
            '--write_slope_to_object_attribute_file', 'True',
            '--save_jsons', 'True'
        ],
        'expected_files': [
            'link_slope_dictionary.json',
            'link_slopes.xml',
            'network.xml',
            'node_elevation_dictionary.json',
            os.path.join('supporting_outputs', 'link_slope.geojson'),
            os.path.join('supporting_outputs', 'node_elevation.geojson'),
            'validation_report_for_elevation.json'
        ]
    },
    'auto_schedule_fixes.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION,
            '--vehicle_scalings', '1,10'
        ],
        'expected_files': [
            'schedule.xml',
            'vehicles.xml',
            '1_perc_vehicles.xml',
            '10_perc_vehicles.xml',
        ]
    },
    'generate_standard_outputs.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION
        ],
        'expected_files': [
            'network_nodes.geojson',
            'schedule_nodes.geojson',
            'summary_report.json',
            'network_links.geojson',
            'schedule_links.geojson',
            os.path.join('schedule', 'speed', 'pt_network_speeds.geojson'),
            os.path.join('schedule', 'speed', 'pt_speeds.geojson'),
            os.path.join('routing', 'schedule_network_routes_geodataframe.geojson')
        ]
    },
    'inspect_google_directions_requests_for_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--subset_conditions', 'primary,motorway',
            '--projection', PROJECTION
        ],
        'expected_files': [
            'api_requests.json',
            os.path.join('subset', 'api_requests.json')
        ]
    },
    'intermodal_access_egress_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION,
            '--pt_modes', 'bus',
            '--network_snap_modes', 'car',
            '--teleport_modes', 'bike',
            '--step_size', '10',
            '--distance_threshold', '20'
        ],
        'expected_files': [
            'vehicles.xml',
            'schedule.xml',
            os.path.join('supporting_outputs', 'car_access_egress_links.geojson'),
            os.path.join('supporting_outputs', 'stops.geojson')
        ]
    },
    'make_pt_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--gtfs', os.path.join(EXAMPLE_DATA_DIR, 'example_gtfs'),
            '--gtfs_day', '20190603',
            '--projection', PROJECTION,
            '--snapping_distance', '40',
            '--processes', '2',
            '--solver', 'cbc'
        ],
        'expected_files': [
            'vehicles.xml',
            'schedule.xml',
            'network.xml',
            'standard_outputs.zip'
        ]
    },
    'make_road_only_network.py': {
        'args': [
            '--osm', os.path.join(EXAMPLE_DATA_DIR, 'example.osm'),
            '--config', os.path.join(GENET_ROOT_DIR, 'genet', 'configs', 'OSM', 'slim_config.yml'),
            '--connected_components', '1',
            '--projection', PROJECTION,
            '--processes', '2'
        ],
        'expected_files': [
            'network.xml',
        ]
    },
    'reproject_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--current_projection', 'epsg:27700',
            '--new_projection', 'epsg:4326',
            '--processes', '2',

        ],
        'expected_files': [
            'vehicles.xml',
            'schedule.xml',
            'network.xml',
        ]
    },
    'scale_vehicles.py': {
        'args': [
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION,
            '--vehicle_scalings', '1,10',

        ],
        'expected_files': [
            '1_perc_vehicles.xml',
            '10_perc_vehicles.xml'
        ]
    },
    'separate_modes_in_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--projection', PROJECTION,
            '--modes', 'bus',
            '--increase_capacity', 'True',

        ],
        'expected_files': [
            'validation_report.json',
            'network.xml',
            os.path.join('supporting_outputs', 'mode_bus_after.geojson'),
            os.path.join('supporting_outputs', 'mode_bus_before.geojson'),
        ]
    },
    'simplify_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION,
            '--processes', '1',
            '--force_strongly_connected_graph', 'True',
            '--vehicle_scalings', '1,10',

        ],
        'expected_files': [
            'vehicles.xml',
            '1_perc_vehicles.xml',
            'schedule.xml',
            '10_perc_vehicles.xml',
            'validation_report.json',
            'network.xml',
            'standard_outputs.zip',
            'link_simp_map.json'
        ]
    },
    'squeeze_external_area.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--projection', PROJECTION,
            '--study_area', os.path.join(EXAMPLE_DATA_DIR, 'Fitzrovia_polygon.geojson'),
            '--freespeed', '0.5',
            '--capacity', '0.5',

        ],
        'expected_files': [
            'network.xml',
            os.path.join('supporting_outputs', 'external_network_links.geojson'),
            os.path.join('supporting_outputs', 'capacity_before.geojson'),
            os.path.join('supporting_outputs', 'freespeed_after.geojson'),
            os.path.join('supporting_outputs', 'capacity_after.geojson'),
            os.path.join('supporting_outputs', 'freespeed_before.geojson'),
        ]
    },
    'squeeze_urban_links.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--projection', PROJECTION,
            '--study_area', os.path.join(EXAMPLE_DATA_DIR, 'Fitzrovia_polygon.geojson'),
            '--urban_geometries', os.path.join(EXAMPLE_DATA_DIR, 'Fitzrovia_urban_polygon.geojson'),
            '--freespeed', '0.5',
            '--capacity', '0.5',

        ],
        'expected_files': [
            'network.xml',
            os.path.join('supporting_outputs', 'capacity_before.geojson'),
            os.path.join('supporting_outputs', 'freespeed_after.geojson'),
            os.path.join('supporting_outputs', 'urban_network_links.geojson'),
            os.path.join('supporting_outputs', 'capacity_after.geojson'),
            os.path.join('supporting_outputs', 'freespeed_before.geojson')
        ]
    },
    'validate_network.py': {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--schedule', EXAMPLE_SCHEDULE,
            '--vehicles', EXAMPLE_VEHICLES,
            '--projection', PROJECTION,
        ],
        'expected_files': [
            'validation_report.json'
        ]
    }
}


def run_process(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    lines = []
    while process.poll() is None:
        line = process.stderr.readline()
        lines.append(line)
    exit_code = process.poll()
    console_output = '\t' + "\t".join(lines)
    return exit_code, console_output


def check_output_files_do_not_exist(output_dir, files: list):
    for file in files:
        file_path = os.path.join(output_dir, file)
        assert not os.path.exists(file_path), f"File {file_path} exists but is not expected."


def check_output_files_exist(output_dir, files: list):
    for file in files:
        file_path = os.path.join(output_dir, file)
        assert os.path.exists(file_path), f"File {file_path} does not exist but is expected."


@pytest.mark.parametrize(
    "script", list(SCRIPTS.keys())
)
def test_integration_of_example_scripts(tmpdir, script):
    output_folder = os.path.join(tmpdir, f'script_{script.replace(".py", "")}')
    check_output_files_do_not_exist(output_folder, SCRIPTS[script]['expected_files'])
    command = f"python {os.path.join(os.path.dirname(__file__), '..', 'scripts', script)} "
    command = command + ' '.join(SCRIPTS[script]['args']) + ' --output_dir ' + output_folder

    exit_code, console_output = run_process(command)

    if exit_code != 0:
        raise AssertionError(f'Script {script} did not run successfully. Error message: \n\n{console_output}')
    else:
        check_output_files_exist(output_folder, SCRIPTS[script]['expected_files'])


def test_google_api_script_throws_error_without_api_key(tmpdir):
    script = 'send_google_directions_requests_for_network.py'
    script_info = {
        'args': [
            '--network', EXAMPLE_NETWORK,
            '--projection', PROJECTION,
            '--requests_threshold', '1',
            '--subset_conditions', 'primary,motorway',
            '--traffic_model', 'best_guess',
            '--departure_time', 'now'
        ],
        'expected_files': [
            'api_requests.json',
        ]
    }
    output_folder = os.path.join(tmpdir, f'script_{script.replace(".py", "")}')
    check_output_files_do_not_exist(output_folder, script_info['expected_files'])
    command = f"python {os.path.join(os.path.dirname(__file__), '..', 'scripts', script)} "
    command = command + ' '.join(script_info['args']) + ' --output_dir ' + output_folder

    exit_code, console_output = run_process(command)

    assert exit_code != 0, f'Script {script} is expected ot fail.'
    assert 'RuntimeError: Number of requests exceeded the threshold.' in console_output
    check_output_files_exist(output_folder, script_info['expected_files'])

