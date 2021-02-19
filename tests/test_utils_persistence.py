import os
from genet.utils import persistence
from tests.fixtures import assert_semantically_equal


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


def test_is_yml_identifies_yml():
    zip_dir = os.path.join('path', 'to', 'dir', 'file.yml')
    assert persistence.is_yml(zip_dir)


def test_is_yml_identifies_regular_string_isnt_yml():
    assert not persistence.is_yml('hello,darkness,my,old,friend')


def test_is_yml_identifies_a_dictionary_isnt_yml():
    assert not persistence.is_yml({'hello': "i'm not a yml file"})


def test_is_geojson_identifies_geojson():
    zip_dir = os.path.join('path', 'to', 'dir', 'file.geojson')
    assert persistence.is_geojson(zip_dir)


def test_is_geojson_identifies_regular_string_isnt_geojson():
    assert not persistence.is_geojson('hello,darkness,my,old,friend')


def test_is_zip_identifies_zip():
    zip_dir = os.path.join('path', 'to', 'dir', 'file.zip')
    assert persistence.is_zip(zip_dir)


def test_is_zip_identifies_folder_isnt_zip():
    zip_dir = os.path.join('path', 'to', 'dir')
    assert not persistence.is_zip(zip_dir)


def test_zipping_folder(tmpdir):

    folder = os.path.join(tmpdir, 'folder_to_zip_up')
    persistence.ensure_dir(folder)

    with open(os.path.join(folder, 'helloworld.txt'), 'wb') as f:
        f.write(b'hello world')
        f.close()

    assert os.path.exists(os.path.join(folder, 'helloworld.txt'))
    assert not os.path.exists(os.path.join(tmpdir, 'folder_to_zip_up.zip'))

    persistence.zip_folder(folder)

    assert os.path.exists(os.path.join(tmpdir, 'folder_to_zip_up.zip'))
