"""Tests for PII redaction applied before the evaluation LLM call (#1 fairness).

The evaluator must never receive the factors the rubric declares off-limits:
name, contact details, location, school name, and GPA. These tests pin that
the redaction blanks exactly those fields, preserves all technical signal, and
never mutates the caller's original resume_data (which the CSV/recruiter still
needs intact).
"""

from models import (
    JSONResume,
    Basics,
    Location,
    Profile,
    Work,
    Education,
    Skill,
    Project,
)
from transform import (
    redact_resume_for_evaluation,
    redact_github_data_for_evaluation,
    convert_json_resume_to_text,
    convert_github_data_to_text,
)


def _sample_resume() -> JSONResume:
    return JSONResume(
        basics=Basics(
            name="Jane Q. Candidate",
            email="jane@example.com",
            phone="+1-555-0100",
            url="https://janecandidate.dev",
            summary="Backend engineer who likes distributed systems.",
            location=Location(city="Austin", region="Texas", countryCode="US"),
            profiles=[
                Profile(
                    network="GitHub", username="janeqc", url="https://github.com/janeqc"
                ),
                Profile(
                    network="LinkedIn",
                    username="janeqc",
                    url="https://linkedin.com/in/janeqc",
                ),
            ],
        ),
        work=[
            Work(
                name="Acme Corp", position="SWE Intern", summary="Built a rate limiter."
            )
        ],
        education=[
            Education(
                institution="Prestige University",
                area="Computer Science",
                studyType="B.S.",
                score="3.9 GPA",
            )
        ],
        skills=[Skill(name="Python", keywords=["asyncio", "pytest"])],
        projects=[
            Project(name="DistKV", description="A toy distributed key-value store.")
        ],
    )


def test_redaction_blanks_forbidden_fields():
    redacted = redact_resume_for_evaluation(_sample_resume())

    assert redacted.basics.name in (None, "")
    assert redacted.basics.email in (None, "")
    assert redacted.basics.phone in (None, "")
    assert redacted.basics.location is None
    assert redacted.education[0].institution in (None, "")
    assert redacted.education[0].score in (None, "")


def test_redaction_preserves_technical_signal():
    redacted = redact_resume_for_evaluation(_sample_resume())

    # Education: degree subject and type are signal, not demographics.
    assert redacted.education[0].area == "Computer Science"
    assert redacted.education[0].studyType == "B.S."
    # Skills, work, projects, and summary carry the actual evaluation signal.
    assert redacted.skills[0].name == "Python"
    assert redacted.work[0].name == "Acme Corp"
    assert redacted.work[0].summary == "Built a rate limiter."
    assert redacted.projects[0].name == "DistKV"
    assert redacted.basics.summary == "Backend engineer who likes distributed systems."
    # Professional links remain (needed for GitHub enrichment + bonus scoring).
    assert redacted.basics.profiles is not None


def test_redaction_does_not_mutate_original():
    original = _sample_resume()
    redact_resume_for_evaluation(original)

    assert original.basics.name == "Jane Q. Candidate"
    assert original.basics.location is not None
    assert original.education[0].institution == "Prestige University"


def test_redacted_text_excludes_identity_keeps_signal():
    redacted = redact_resume_for_evaluation(_sample_resume())
    text = convert_json_resume_to_text(redacted)

    assert "Jane Q. Candidate" not in text
    assert "jane@example.com" not in text
    assert "Austin" not in text
    assert "Prestige University" not in text
    assert "3.9 GPA" not in text
    # Signal survives.
    assert "Python" in text
    assert "DistKV" in text


def test_github_redaction_blanks_name_keeps_repo_signal():
    github_data = {
        "profile": {
            "username": "janeqc",
            "name": "Jane Q. Candidate",
            "location": "Austin, TX",
            "company": "Acme Corp",
            "public_repos": 12,
            "followers": 30,
        },
        "projects": [
            {"name": "DistKV", "github_url": "https://github.com/janeqc/distkv"}
        ],
        "total_projects": 1,
    }

    redacted = redact_github_data_for_evaluation(github_data)
    text = convert_github_data_to_text(redacted)

    assert "Jane Q. Candidate" not in text
    # Username is the lookup key + not demographic; repo signal must survive.
    assert redacted["profile"]["username"] == "janeqc"
    assert "DistKV" in text
    # Original dict untouched.
    assert github_data["profile"]["name"] == "Jane Q. Candidate"
