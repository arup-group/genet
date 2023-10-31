import pytest
from click.testing import CliRunner

import genet.use.recipes as gn_recipes
from genet import cli
from tests.test_recipes import RecipeDispenser


@pytest.fixture(scope="function")
def invoke_runner_and_check_delegation(tmpdir_factory, mocker):
    outdir = tmpdir_factory.mktemp("outdir")

    def _invoke_runner_and_check_delegation(
        func: str, cli_args: list[str], function_args: dict[str, str]
    ):
        mocker.patch.object(gn_recipes, func)

        runner = CliRunner()
        runner.invoke(getattr(cli, func), cli_args + [f"--output_dir={outdir}"])

        getattr(gn_recipes, func).assert_called_once_with(
            **{**function_args, **{"output_dir": outdir}}
        )

    return _invoke_runner_and_check_delegation


def test_add_elevation_to_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("add_elevation_to_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_auto_schedule_fixes(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("auto_schedule_fixes")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_generate_standard_outputs(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("generate_standard_outputs")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_inspect_google_directions_requests_for_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("inspect_google_directions_requests_for_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_intermodal_access_egress_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("intermodal_access_egress_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_make_pt_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("make_pt_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_make_road_only_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("make_road_only_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_reproject_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("reproject_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_scale_vehicles(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("scale_vehicles")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_separate_modes_in_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("separate_modes_in_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_simplify_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("simplify_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_squeeze_external_area(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("squeeze_external_area")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_squeeze_urban_links(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("squeeze_urban_links")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_validate_network(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("validate_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )


def test_google_api_script(invoke_runner_and_check_delegation):
    recipe = RecipeDispenser("send_google_directions_requests_for_network")
    invoke_runner_and_check_delegation(
        recipe.recipe_name, cli_args=recipe.cli_args, function_args=recipe.function_args
    )
