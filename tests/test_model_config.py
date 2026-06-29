"""Guard the model config in prompt.py: every model with tuned parameters must
also declare a provider (and vice versa). A model present in one dict but not
the other silently falls back to defaults/Ollama, which is hard to notice.
"""

from prompt import MODEL_PARAMETERS, MODEL_PROVIDER_MAPPING


def test_parameter_and_provider_dicts_cover_the_same_models():
    assert set(MODEL_PARAMETERS) == set(MODEL_PROVIDER_MAPPING)
