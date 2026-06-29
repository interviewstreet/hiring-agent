"""Gemini's Schema type rejects some JSON-schema keywords that pydantic emits
(notably exclusiveMinimum/exclusiveMaximum from Field(gt=...)/Field(lt=...)),
which caused the live structured-output call to fail. Keep the response models
to the subset Gemini accepts: inclusive bounds only.
"""

import json

from models import EvaluationData


def test_response_model_avoids_unsupported_schema_keywords():
    schema_text = json.dumps(EvaluationData.model_json_schema())
    assert "exclusiveMinimum" not in schema_text
    assert "exclusiveMaximum" not in schema_text
