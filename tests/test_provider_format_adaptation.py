"""The canonical structured-output 'format' is a pydantic model CLASS. Each
provider adapts it to what its SDK wants:
  - Ollama needs a JSON-schema dict.
  - Gemini's SDK natively converts a pydantic class (and rejects pydantic's
    raw JSON-schema dict, e.g. exclusiveMinimum / $ref).
A plain dict passed as format must still flow through untouched (back-compat).
"""

from models import OllamaProvider, build_gemini_request, EvaluationData


class _FakeOllama:
    def __init__(self):
        self.kw = None

    def chat(self, **kw):
        self.kw = kw
        return {"message": {"content": "{}"}}


def _ollama_with_fake():
    p = OllamaProvider()
    p.client = _FakeOllama()
    return p


def test_ollama_converts_pydantic_class_to_json_schema():
    p = _ollama_with_fake()
    p.chat(
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        options={},
        format=EvaluationData,
    )
    fmt = p.client.kw["format"]
    assert isinstance(fmt, dict)
    assert "properties" in fmt  # it's a real JSON schema, not the class


def test_ollama_passes_dict_format_through():
    p = _ollama_with_fake()
    schema = {"type": "object", "properties": {}}
    p.chat(
        model="m",
        messages=[{"role": "user", "content": "hi"}],
        options={},
        format=schema,
    )
    assert p.client.kw["format"] == schema


def test_gemini_request_passes_pydantic_class_as_response_schema():
    req = build_gemini_request(
        [{"role": "user", "content": "hi"}], {}, {"format": EvaluationData}
    )
    gen = req["generation_config"]
    assert gen["response_schema"] is EvaluationData
    assert gen["response_mime_type"] == "application/json"
