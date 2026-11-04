from typing import Any, Optional
from pydantic import BaseModel, ValidationError
from llm_utils import initialize_llm_provider, extract_json_from_response
import logging
import json

from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
)
from prompts.template_manager import TemplateManager

logger = logging.getLogger(__name__)

# Models occasionally emit truncated or otherwise unparseable JSON even with
# structured-output schemas (especially smaller local models). Retry a few
# times before failing the whole evaluation run.
_MAX_EVALUATION_ATTEMPTS = 3

# Tiny models often truncate before emitting these narrative fields. Fill
# placeholders so a repaired partial payload can still validate and score.
_DEFAULT_NARRATIVE_FIELDS = {
    "key_strengths": ["Not provided by model"],
    "areas_for_improvement": ["Not provided by model"],
}


class ResumeEvaluator:
    def __init__(
        self,
        role,
        evaluation_model,
        model_name: str = DEFAULT_MODEL,
        model_params: dict = None,
    ):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.role = role
        self.evaluation_model = evaluation_model
        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def _load_evaluation_prompt(self, resume_text: str) -> str:
        return self.template_manager.render_string(
            self.role.criteria_source, text_content=resume_text
        )

    def _chat_options_for_attempt(self, attempt: int) -> dict:
        """Raise temperature on retries so temp=0 does not repeat the same JSON."""
        options = {"stream": False, **self.model_params}
        if attempt > 1:
            base_temp = float(options.get("temperature", 0.0) or 0.0)
            options["temperature"] = min(0.8, base_temp + 0.3 * (attempt - 1))
        return options

    @staticmethod
    def _prepare_evaluation_dict(evaluation_dict: dict[str, Any]) -> dict[str, Any]:
        """Fill narrative fields tiny models often omit after truncation."""
        prepared = dict(evaluation_dict)
        for key, default in _DEFAULT_NARRATIVE_FIELDS.items():
            value = prepared.get(key)
            if not value:
                prepared[key] = list(default)
        return prepared

    def evaluate_resume(self, resume_text: str) -> BaseModel:
        self._last_resume_text = resume_text
        full_prompt = self._load_evaluation_prompt(resume_text)
        system_message = self.template_manager.render_string(
            self.role.system_message_source,
            bonus_rules=self.role.bonus_rules,
            bonus_max=self.role.bonus_max,
        )

        kwargs = {"format": self.evaluation_model.model_json_schema()}

        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_EVALUATION_ATTEMPTS + 1):
            try:
                chat_params = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": full_prompt},
                    ],
                    "options": self._chat_options_for_attempt(attempt),
                }
                response = self.provider.chat(**chat_params, **kwargs)
                response_text = extract_json_from_response(
                    response["message"]["content"]
                )
                logger.debug(f"🔤 Prompt response: {response_text}")

                evaluation_dict = self._prepare_evaluation_dict(
                    json.loads(response_text)
                )
                return self.evaluation_model(**evaluation_dict)

            except (json.JSONDecodeError, ValidationError, TypeError) as e:
                last_error = e
                logger.warning(
                    "Invalid evaluation output from %s (attempt %d/%d): %s",
                    self.model_name,
                    attempt,
                    _MAX_EVALUATION_ATTEMPTS,
                    e,
                )
                if attempt == _MAX_EVALUATION_ATTEMPTS:
                    logger.error(
                        "Exhausted %d attempts parsing evaluation JSON: %s",
                        _MAX_EVALUATION_ATTEMPTS,
                        e,
                    )
                    raise

            except Exception as e:
                logger.error(f"Error evaluating resume: {str(e)}")
                raise

        raise last_error  # pragma: no cover
