import os

from genet.use import road_pricing


def test_writes_toll_ids_to_expected_location(tmpdir):
    toll_ids = [str(i) for i in range(10)]
    road_pricing.write_toll_ids(toll_ids, tmpdir)

    expected_toll_id_file = os.path.join(tmpdir, 'toll_ids')
    assert os.path.exists(expected_toll_id_file)
    with open(expected_toll_id_file) as toll_file:
        lines = toll_file.readlines()
        assert len(lines) == len(toll_ids)
        for i, toll_id in enumerate(toll_ids):
            assert lines[i] == "{}\n".format(toll_id)