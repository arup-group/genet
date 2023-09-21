"""Tests for `genet` CLI."""

from click.testing import CliRunner

from genet import cli


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.cli)
    assert result.exit_code == 0
    assert "GeNet Command Line Tool" in result.output
    help_result = runner.invoke(cli.cli, ["--help"])
    assert help_result.exit_code == 0
    assert "GeNet Command Line Tool." in help_result.output
