import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from transform import transform_evaluation_response
from models import JSONResume, Basics, Location


def test_transform_evaluation_response_none_resume():
    row = transform_evaluation_response(file_name="candidate.pdf", resume_data=None)
    assert row["file_name"] == "candidate.pdf"
    assert row["name"] == ""
    assert row["email"] == ""
    assert row["phone"] == ""
    assert row["location"] == ""
    assert row["summary"] == ""
    for prefix in ["github", "linkedin", "twitter", "dev", "behance"]:
        assert row[f"{prefix}_url"] == ""
        assert row[f"{prefix}_username"] == ""


def test_transform_evaluation_response_empty_basics():
    resume = JSONResume(basics=None)
    row = transform_evaluation_response(file_name="candidate.pdf", resume_data=resume)
    assert row["name"] == ""
    assert row["location"] == ""
    assert "github_url" in row
    assert "linkedin_username" in row


def test_transform_evaluation_response_location_sanitization():
    # Only city
    loc1 = Location(city="Seattle", region=None)
    r1 = JSONResume(basics=Basics(name="Alice", location=loc1))
    row1 = transform_evaluation_response(resume_data=r1)
    assert row1["location"] == "Seattle"

    # Both city and region
    loc2 = Location(city="Seattle", region="WA")
    r2 = JSONResume(basics=Basics(name="Bob", location=loc2))
    row2 = transform_evaluation_response(resume_data=r2)
    assert row2["location"] == "Seattle, WA"

    # All None in location
    loc3 = Location(city=None, region=None)
    r3 = JSONResume(basics=Basics(name="Charlie", location=loc3))
    row3 = transform_evaluation_response(resume_data=r3)
    assert row3["location"] == ""
