"""Regression tests for Deductions model (#349).

Gemini sometimes returns 'deductions' as the key name instead of 'reasons'.
The model_validator normalizes this before validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Deductions, build_evaluation_model
from roles import load_role


def test_deductions_accepts_reasons_key():
    d = Deductions(total=2.0, reasons="Missing tests")
    assert d.reasons == "Missing tests"
    assert d.total == 2.0


def test_deductions_accepts_deductions_key_as_alias():
    d = Deductions(total=3.0, deductions="No documentation")
    assert d.reasons == "No documentation"


def test_deductions_reasons_takes_priority_over_deductions():
    d = Deductions(total=1.0, reasons="Real reason", deductions="Alt reason")
    assert d.reasons == "Real reason"


def test_deductions_missing_both_keys_uses_default():
    d = Deductions(total=0.0)
    assert d.reasons == ""


def test_evaluation_model_validates_key_strengths_length():
    """min_length/max_length should be enforced (Pydantic v2 syntax)."""
    from pydantic import ValidationError

    role = load_role("software_engineering_intern")
    EvaluationData = build_evaluation_model(role)

    schema = EvaluationData.model_json_schema()
    props = schema.get("properties", {})

    ks = props.get("key_strengths", {})
    assert ks.get("minItems") == 1 or ks.get("minLength") == 1, (
        "key_strengths should enforce minimum length"
    )


if __name__ == "__main__":
    test_deductions_accepts_reasons_key()
    test_deductions_accepts_deductions_key_as_alias()
    test_deductions_reasons_takes_priority_over_deductions()
    test_deductions_missing_both_keys_uses_default()
    test_evaluation_model_validates_key_strengths_length()
    print("All tests passed!")
