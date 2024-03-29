import os

from genet.utils import persistence


def test_creates_directories_when_required_on_ensure_check(tmpdir):
    new_dir_path = "{}/new_dir".format(tmpdir)
    assert not os.path.isdir(new_dir_path)

    persistence.ensure_dir(new_dir_path)

    assert os.path.isdir(new_dir_path)


def test_does_not_overwrite_existing_dirs_on_ensure_check(tmpdir):
    new_dir_path = "{}/new_dir".format(tmpdir)
    os.makedirs(new_dir_path)
    assert os.path.isdir(new_dir_path)
    dir_mod_time = os.path.getmtime(new_dir_path)

    persistence.ensure_dir(new_dir_path)

    assert os.path.isdir(new_dir_path)
    assert os.path.getmtime(new_dir_path) == dir_mod_time


def test_swallows_exceptions_making_new_directories(mocker):
    mocker.patch.object(os.path, "exists", return_value=False)
    mocker.patch.object(os, "makedirs", side_effect=PermissionError("BOOM!"))

    persistence.ensure_dir("/some/path/or/other")

    os.makedirs.assert_called_once()


def test_setifying_list_returns_expected_set():
    assert persistence.setify(["ABC", 2]) == {"ABC", 2}


def test_setifying_string_returns_expected_single_item_set():
    assert persistence.setify("ABC") == {"ABC"}


def test_setifying_set_makes_no_difference():
    assert persistence.setify({"ABC", 2}) == {"ABC", 2}


def test_setifying_none_returns_empty_set():
    assert persistence.setify(None) == set()


def test_listifying_list_makes_no_difference():
    assert persistence.listify(["ABC", 2]) == ["ABC", 2]


def test_listifying_string_returns_expected_single_item_list():
    assert persistence.listify("ABC") == ["ABC"]


def test_listifying_set_returns_expected_list():
    listified_set = persistence.listify({"ABC", 2})
    assert listified_set == ["ABC", 2] or listified_set == [2, "ABC"]


def test_listifying_none_returns_empty_list():
    assert persistence.listify(None) == []


def test_is_yml_identifies_yml():
    assert persistence.is_yml("path/to/dir/file.yml")


def test_is_yml_identifies_yaml():
    assert persistence.is_yml("path/to/dir/file.yaml")


def test_is_yml_identifies_non_yaml():
    assert not persistence.is_yml("path/to/dir/file.txt")


def test_is_yml_identifies_regular_string_isnt_yml():
    assert not persistence.is_yml("hello,darkness,my,old,friend")


def test_is_geojson_identifies_geojson():
    assert persistence.is_geojson(os.path.join("path", "to", "dir", "file.geojson"))


def test_is_geojson_identifies_regular_string_isnt_geojson():
    assert not persistence.is_geojson("hello,darkness,my,old,friend")


def test_is_csv_identifies_csv():
    zip_dir = os.path.join("path", "to", "dir", "file.csv")
    assert persistence.is_csv(zip_dir)


def test_is_csv_identifies_regular_string_isnt_csv():
    assert not persistence.is_csv("hello,darkness,my,old,friend")


def test_is_json_identifies_json():
    zip_dir = os.path.join("path", "to", "dir", "file.json")
    assert persistence.is_json(zip_dir)


def test_is_json_identifies_regular_string_isnt_json():
    assert not persistence.is_json("hello,darkness,my,old,friend")


def test_is_zip_identifies_zip():
    assert persistence.is_zip(os.path.join("path", "to", "dir", "file.zip"))


def test_is_zip_identifies_folder_isnt_zip():
    assert not persistence.is_zip(os.path.join("path", "to", "dir"))


def test_zipping_folder(tmpdir):
    folder = os.path.join(tmpdir, "folder_to_zip_up")
    persistence.ensure_dir(folder)

    with open(os.path.join(folder, "helloworld.txt"), "wb") as f:
        f.write(b"hello world")
        f.close()

    assert os.path.exists(os.path.join(folder, "helloworld.txt"))
    assert not os.path.exists(os.path.join(tmpdir, "folder_to_zip_up.zip"))

    persistence.zip_folder(folder)

    assert os.path.exists(os.path.join(tmpdir, "folder_to_zip_up.zip"))
