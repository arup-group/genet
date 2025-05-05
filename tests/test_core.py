"""Tests for `genet` package."""

import pytest

from genet import core


@pytest.mark.parametrize(
    ["initial_route", "mapping", "expected_route"],
    [
        (["foo"], {"foo": "bar"}, ["bar"]),
        (["foo"], {"foo": ["bar", "baz"]}, ["bar", "baz"]),
        (["foo", "bar"], {"foo": ["baz", "foobar"]}, ["baz", "foobar", "bar"]),
    ],
)
def test_replace_link_on_pt_route(initial_route, mapping, expected_route):
    new_route = core.replace_link_on_pt_route(initial_route, mapping)
    assert new_route == expected_route
