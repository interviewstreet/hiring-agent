import os
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from transform import transform_parsed_data, transform_organizations


def test_transform_volunteer_alias_keys():
    # 1. Standard "volunteer" key
    data_with_volunteer = {
        "basics": {"name": "Jane Doe"},
        "volunteer": [
            {
                "organization": "Open Source Initiative",
                "position": "Contributor",
                "startDate": "2023-01",
                "endDate": "2024-01",
                "summary": "Reviewed and submitted PRs",
                "highlights": ["Fixed 5 bugs", "Wrote documentation"],
            }
        ],
    }
    res = transform_parsed_data(data_with_volunteer)
    vol = res.get("volunteer", [])
    assert len(vol) == 1
    assert vol[0]["organization"] == "Open Source Initiative"
    assert vol[0]["position"] == "Contributor"
    assert vol[0]["startDate"] == "2023-01"
    assert vol[0]["endDate"] == "2024-01"
    assert vol[0]["summary"] == "Reviewed and submitted PRs"
    assert vol[0]["highlights"] == ["Fixed 5 bugs", "Wrote documentation"]

    # 2. "volunteering" key
    data_with_volunteering = {
        "basics": {"name": "John Smith"},
        "volunteering": [
            {
                "name": "Community Tech",
                "role": "Mentor",
            }
        ],
    }
    res2 = transform_parsed_data(data_with_volunteering)
    vol2 = res2.get("volunteer", [])
    assert len(vol2) == 1
    assert vol2[0]["organization"] == "Community Tech"
    assert vol2[0]["position"] == "Mentor"
    assert vol2[0]["endDate"] == "Present"

    # 3. Traditional "organizations" key
    data_with_orgs = {
        "basics": {"name": "Alice"},
        "organizations": [
            {
                "name": "Robotics Club",
                "role": "Team Lead",
            }
        ],
    }
    res3 = transform_parsed_data(data_with_orgs)
    vol3 = res3.get("volunteer", [])
    assert len(vol3) == 1
    assert vol3[0]["organization"] == "Robotics Club"
    assert vol3[0]["position"] == "Team Lead"


def test_csv_empty_file_guard_logic():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = os.path.join(tmpdir, "test_eval.csv")

        # Case 1: File does not exist -> file_exists is False
        file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
        assert not file_exists

        # Case 2: File exists but is 0 bytes (e.g. touched or empty stub) -> file_exists must still be False!
        Path(csv_file).touch()
        assert os.path.exists(csv_file)
        file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
        assert not file_exists

        # Case 3: File has content -> file_exists is True
        with open(csv_file, "w") as f:
            f.write("header1,header2\n")
        file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0
        assert file_exists
