import os
from genet.utils import persistence


def test_creates_directories_when_required_on_ensure_check(tmpdir):
    new_dir_path = '{}/new_dir'.format(tmpdir)
    assert not os.path.isdir(new_dir_path)

    persistence.ensure_dir(new_dir_path)

    assert os.path.isdir(new_dir_path)


def test_does_not_overwrite_existing_dirs_on_ensure_check(tmpdir):
    new_dir_path = '{}/new_dir'.format(tmpdir)
    os.makedirs(new_dir_path)
    assert os.path.isdir(new_dir_path)
    dir_mod_time = os.path.getmtime(new_dir_path)

    persistence.ensure_dir(new_dir_path)

    assert os.path.isdir(new_dir_path)
    assert os.path.getmtime(new_dir_path) == dir_mod_time


def test_swallows_exceptions_making_new_directories(mocker):
    mocker.patch.object(os.path, 'exists', return_value=False)
    mocker.patch.object(os, 'makedirs', side_effect=PermissionError('BOOM!'))

    persistence.ensure_dir('/some/path/or/other')

    os.makedirs.assert_called_once()


def test_is_zip_identifies_zip():
    zip_dir = os.path.join('path', 'to', 'dir', 'file.zip')
    assert persistence.is_zip(zip_dir)


def test_is_zip_identifies_folder_isnt_zip():
    zip_dir = os.path.join('path', 'to', 'dir')
    assert not persistence.is_zip(zip_dir)


def test_set_nested_value_overwrites_current_value():
    d = {'attributes': {'some_osm_tag': 'hello'}}
    value = {'attributes': {'some_osm_tag': 'bye'}}
    return_d = persistence.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_osm_tag': 'bye'}}


def test_set_nested_value_adds_new_key_val_pair():
    d = {'attributes': {'some_osm_tag': 'hello'}}
    value = {'attributes': {'some_tag': 'bye'}}
    return_d = persistence.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_osm_tag': 'hello', 'some_tag': 'bye'}}


def test_set_nested_value_creates_new_nest_in_place_of_single_value():
    d = {'attributes': 1}
    value = {'attributes': {'some_tag': 'bye'}}
    return_d = persistence.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_tag': 'bye'}}


def test_set_nested_value_works_with_non_nested_dicts():
    d = {'attributes': 1}
    value = {'key': 2}
    return_d = persistence.set_nested_value(d, value)

    assert return_d == {'attributes': 1, 'key': 2}


def test_set_nested_value_replaces_values_with_non_nested_dicts():
    d = {'attributes': 1}
    value = {'attributes': 2}
    return_d = persistence.set_nested_value(d, value)

    assert return_d == {'attributes': 2}
