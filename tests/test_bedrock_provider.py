"""Tests for the AWS Bedrock transport.

These are offline: the Bedrock client is replaced with a fake that records the
request, so the whole translation layer is covered without AWS credentials or
network access.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import provider_for  # noqa: E402
from models import BedrockConverseProvider  # noqa: E402


class FakeConverseClient:
    """Records the last converse() request and returns a canned response."""

    def __init__(self, response):
        self.response = response
        self.last_request = None

    def converse(self, **kwargs):
        self.last_request = kwargs
        return self.response


def make_provider(response, **kwargs):
    provider = BedrockConverseProvider(region="us-east-1", **kwargs)
    provider._client = FakeConverseClient(response)
    return provider


def text_response(text):
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "stopReason": "end_turn",
    }


def tool_response(payload):
    return {
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "name": BedrockConverseProvider.TOOL_NAME,
                            "input": payload,
                        }
                    }
                ]
            }
        },
        "stopReason": "tool_use",
    }


# --------------------------------------------------------------------------
# Message translation
# --------------------------------------------------------------------------


def test_system_message_is_hoisted_out_of_messages():
    """Converse takes system out-of-band; a system role in messages is rejected."""
    provider = make_provider(text_response("ok"))
    provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[
            {"role": "system", "content": "You are a scorer."},
            {"role": "user", "content": "Score this."},
        ],
    )
    req = provider._client.last_request
    assert req["system"] == [{"text": "You are a scorer."}]
    assert req["messages"] == [{"role": "user", "content": [{"text": "Score this."}]}]
    assert all(m["role"] != "system" for m in req["messages"])


def test_consecutive_same_role_messages_are_merged():
    """Converse rejects two messages in a row with the same role."""
    provider = make_provider(text_response("ok"))
    provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[
            {"role": "user", "content": "first"},
            {"role": "user", "content": "second"},
        ],
    )
    assert provider._client.last_request["messages"] == [
        {"role": "user", "content": [{"text": "first\n\nsecond"}]}
    ]


def test_system_only_messages_still_produce_a_user_turn():
    """Converse requires at least one message, starting with the user."""
    provider = make_provider(text_response("ok"))
    provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[{"role": "system", "content": "only a system prompt"}],
    )
    msgs = provider._client.last_request["messages"]
    assert len(msgs) == 1 and msgs[0]["role"] == "user"


# --------------------------------------------------------------------------
# Inference config
# --------------------------------------------------------------------------


def test_options_map_to_inference_config_with_bedrock_names():
    """top_p becomes topP, and maxTokens is always sent."""
    provider = make_provider(text_response("ok"), max_tokens=1234)
    provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[{"role": "user", "content": "hi"}],
        options={"temperature": 0.1, "top_p": 0.9},
    )
    assert provider._client.last_request["inferenceConfig"] == {
        "maxTokens": 1234,
        "temperature": 0.1,
        "topP": 0.9,
    }


def test_single_sampling_param_is_not_padded_with_the_other():
    """A model declaring only temperature must not get topP invented for it."""
    provider = make_provider(text_response("ok"))
    provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "hi"}],
        options={"temperature": 0.1},
    )
    cfg = provider._client.last_request["inferenceConfig"]
    assert "temperature" in cfg
    assert "topP" not in cfg


def test_claude_bedrock_model_params_resolve_without_top_p():
    """Regression: pdf.py and evaluator.py used to force top_p into options,
    which made every Bedrock Anthropic call fail with a ValidationException."""
    from config import MODEL_PARAMETERS

    params = MODEL_PARAMETERS["us.anthropic.claude-haiku-4-5-20251001-v1:0"]
    assert "temperature" in params
    assert "top_p" not in params


def test_max_tokens_is_sent_even_with_no_options():
    provider = make_provider(text_response("ok"))
    provider.chat(
        model="amazon.nova-pro-v1:0", messages=[{"role": "user", "content": "hi"}]
    )
    assert "maxTokens" in provider._client.last_request["inferenceConfig"]


# --------------------------------------------------------------------------
# Structured output
# --------------------------------------------------------------------------


SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "number"}},
    "required": ["score"],
}


def test_format_kwarg_becomes_a_forced_tool_call():
    """The caller's JSON schema must arrive as inputSchema.json, tool forced."""
    provider = make_provider(tool_response({"score": 22}))
    provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=SCHEMA,
    )
    cfg = provider._client.last_request["toolConfig"]
    assert cfg["tools"][0]["toolSpec"]["inputSchema"]["json"] == SCHEMA
    assert cfg["toolChoice"] == {"tool": {"name": BedrockConverseProvider.TOOL_NAME}}


def test_tool_use_payload_is_returned_as_a_json_string():
    """Callers do json.loads on message.content, so the tool input is serialized."""
    provider = make_provider(tool_response({"score": 22, "max": 35}))
    result = provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=SCHEMA,
    )
    assert json.loads(result["message"]["content"]) == {"score": 22, "max": 35}
    assert result["message"]["role"] == "assistant"


# --- tool-input normalization: both quirks captured from the live API ---

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {"type": "object"},
        "bonus_points": {"type": "object"},
        "key_strengths": {"type": "array"},
    },
    "required": ["scores", "bonus_points", "key_strengths"],
}


@pytest.mark.parametrize("envelope", ["parameter_name", "response"])
def test_single_key_envelope_is_unwrapped(envelope):
    """claude-opus-5 nests the whole object under one arbitrary key."""
    inner = {
        "scores": {"open_source": {"score": 12}},
        "bonus_points": {"total": 4},
        "key_strengths": ["a"],
    }
    provider = make_provider(tool_response({envelope: inner}))
    result = provider.chat(
        model="us.anthropic.claude-opus-5",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    assert json.loads(result["message"]["content"]) == inner


def test_stringified_nested_object_is_parsed_back():
    """claude-haiku-4-5 emits nested objects as JSON strings."""
    provider = make_provider(
        tool_response(
            {
                "scores": {"open_source": {"score": 8}},
                "bonus_points": '{"total": 3, "breakdown": "LinkedIn +1"}',
                "key_strengths": '["backend depth"]',
            }
        )
    )
    result = provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    payload = json.loads(result["message"]["content"])
    assert payload["bonus_points"] == {"total": 3, "breakdown": "LinkedIn +1"}
    assert payload["key_strengths"] == ["backend depth"]


def test_stringified_object_with_one_extra_closing_brace_is_recovered():
    """Exact shape captured from claude-haiku-4-5: complete object, stray '}'."""
    provider = make_provider(
        tool_response(
            {
                "scores": '{"open_source": {"score": 8, "max": 35}}}',
                "bonus_points": '{"total": 3, "breakdown": "LinkedIn +1."}}',
                "key_strengths": '["backend depth"]]',
            }
        )
    )
    result = provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    payload = json.loads(result["message"]["content"])
    assert payload["scores"] == {"open_source": {"score": 8, "max": 35}}
    assert payload["bonus_points"] == {"total": 3, "breakdown": "LinkedIn +1."}
    assert payload["key_strengths"] == ["backend depth"]


def test_trailing_real_content_is_refused_rather_than_silently_truncated():
    """Dropping real content would silently corrupt a score. Leave it invalid
    so the caller's validation fails loudly instead."""
    corrupt = '{"total": 3} {"total": 99}'
    provider = make_provider(
        tool_response({"scores": {}, "bonus_points": corrupt, "key_strengths": ["a"]})
    )
    result = provider.chat(
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    assert json.loads(result["message"]["content"])["bonus_points"] == corrupt


def test_dollar_parameter_name_envelope_from_sonnet_5_is_unwrapped():
    """Literal template placeholder observed leaking as the envelope key."""
    inner = {
        "scores": {"open_source": {"score": 8}},
        "bonus_points": {"total": 4},
        "key_strengths": ["a"],
    }
    provider = make_provider(tool_response({"$PARAMETER_NAME": inner}))
    result = provider.chat(
        model="us.anthropic.claude-sonnet-5",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    assert json.loads(result["message"]["content"]) == inner


def test_prose_strings_are_never_reinterpreted_as_json():
    """evidence/breakdown are prose and must survive untouched."""
    payload_in = {
        "scores": {
            "open_source": {
                "score": 8,
                "evidence": "Uses {braces} mid-sentence [and brackets] here.",
            }
        },
        "bonus_points": {"total": 1, "breakdown": "LinkedIn profile: +1 point."},
        "key_strengths": ["Scaled throughput 10x"],
    }
    provider = make_provider(tool_response(payload_in))
    result = provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=EVAL_SCHEMA,
    )
    assert json.loads(result["message"]["content"]) == payload_in


def test_legitimate_single_property_response_is_not_unwrapped():
    """A schema with one property must not be mistaken for an envelope."""
    schema = {
        "type": "object",
        "properties": {"scores": {"type": "object"}},
        "required": ["scores"],
    }
    payload_in = {"scores": {"open_source": {"score": 8}}}
    provider = make_provider(tool_response(payload_in))
    result = provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[{"role": "user", "content": "score"}],
        format=schema,
    )
    assert json.loads(result["message"]["content"]) == payload_in


def test_normalization_is_a_noop_without_a_schema():
    """No format kwarg means no properties to reason about; pass through."""
    payload_in = {"anything": {"nested": 1}}
    provider = make_provider(tool_response(payload_in))
    result = provider.chat(
        model="amazon.nova-pro-v1:0", messages=[{"role": "user", "content": "hi"}]
    )
    assert json.loads(result["message"]["content"]) == payload_in


def test_structured_output_none_sends_no_tool_config():
    """google.gemma-3-* ignores toolConfig, so it is declared structured_output=none."""
    provider = make_provider(text_response('{"score": 1}'), structured_output="none")
    provider.chat(
        model="google.gemma-3-12b-it",
        messages=[{"role": "user", "content": "score"}],
        format=SCHEMA,
    )
    assert "toolConfig" not in provider._client.last_request


def test_prose_fallback_when_a_model_ignores_the_forced_tool():
    """A model that answers in text despite toolConfig must still return content."""
    provider = make_provider(text_response('{"score": 5}'))
    result = provider.chat(
        model="google.gemma-3-12b-it",
        messages=[{"role": "user", "content": "score"}],
        format=SCHEMA,
    )
    assert result["message"]["content"] == '{"score": 5}'


def test_empty_content_raises_with_the_stop_reason():
    """Silent empty responses are the worst failure mode; fail loudly instead."""
    provider = make_provider(
        {"output": {"message": {"content": []}}, "stopReason": "max_tokens"}
    )
    with pytest.raises(ValueError, match="max_tokens"):
        provider.chat(
            model="amazon.nova-pro-v1:0",
            messages=[{"role": "user", "content": "hi"}],
        )


# --------------------------------------------------------------------------
# Response shape contract — pdf.py / evaluator.py / github.py depend on this
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "response",
    [text_response("plain"), tool_response({"a": 1})],
)
def test_return_shape_matches_the_openai_provider_contract(response):
    provider = make_provider(response)
    result = provider.chat(
        model="amazon.nova-pro-v1:0",
        messages=[{"role": "user", "content": "hi"}],
        format=SCHEMA,
    )
    assert set(result) == {"message"}
    assert set(result["message"]) == {"role", "content"}
    assert isinstance(result["message"]["content"], str)


# --------------------------------------------------------------------------
# Registry resolution
# --------------------------------------------------------------------------


def test_bedrock_models_resolve_to_the_bedrock_transport():
    cfg = provider_for("us.anthropic.claude-haiku-4-5-20251001-v1:0")
    assert cfg["transport"] == "bedrock"
    assert cfg["structured_output"] == "bedrock_tool"
    assert cfg["region"]
    assert cfg["api_key"] is None


def test_existing_providers_still_default_to_the_openai_transport(monkeypatch):
    """Backward compatibility: entries with no `transport` key must not change."""
    # gemini declares api_key_env, and provider_for fail-fasts when it is unset,
    # so supply a dummy value to reach the transport assertion.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-test")
    for model in ("gemma4:latest", "gemini-2.0-flash"):
        assert provider_for(model)["transport"] == "openai"


def test_missing_api_key_still_fails_fast_for_keyed_providers(monkeypatch):
    """The bedrock change must not weaken credential validation elsewhere."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        provider_for("gemini-2.0-flash")


def test_per_model_structured_output_overrides_the_provider_default():
    """Capability is not uniform within a provider."""
    assert provider_for("google.gemma-3-12b-it")["structured_output"] == "none"
    assert provider_for("amazon.nova-pro-v1:0")["structured_output"] == "bedrock_tool"


def test_unknown_model_still_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        provider_for("no-such-model")


def test_anthropic_bedrock_models_do_not_declare_both_temperature_and_top_p():
    """Bedrock rejects temperature+top_p together for Anthropic models.

    Verified live: ValidationException "`temperature` and `top_p` cannot both be
    specified for this model." This is a registry-data invariant rather than a
    code path, so it is asserted here — a contributor adding an Anthropic model
    with both params gets a failing test instead of a mid-run crash.
    """
    from config import MODEL_PARAMETERS

    offenders = [
        model
        for model, params in MODEL_PARAMETERS.items()
        if "anthropic" in model
        and "temperature" in params
        and "top_p" in params
        and model
        in provider_for.__globals__["_config"]["providers"]["bedrock"]["models"]
    ]
    assert not offenders, (
        f"Bedrock Anthropic models must declare only one of temperature/top_p: "
        f"{offenders}"
    )
