from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from models import JSONResume, EvaluationData, EvaluationDataWithJD
from llm_utils import initialize_llm_provider, extract_json_from_response
from datetime import datetime
import logging
import json
import re

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120

from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)
from prompts.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class ResumeEvaluator:
    def __init__(self, model_name: str = DEFAULT_MODEL, model_params: dict = None):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def _render_evaluation_template(self, template_name: str, **kwargs) -> str:
        """Helper function to render and evaluation template."""
        criteria_template = self.template_manager.render_template(
            template_name, **kwargs
        )
        if criteria_template is None:
            raise ValueError(f"Failed to load template: {template_name}")
        return criteria_template

    def _load_evaluation_prompt(self, resume_text: str) -> str:
        """Helper function to load base evaluation prompt (for SDE Intern)."""
        return self._render_evaluation_template(
            "resume_evaluation_criteria", text_content=resume_text
        )

    def _load_evaluation_prompt_with_jd(self, resume_text: str, jd_text: str) -> str:
        """Helper function to load JD-augmented evaluation prompt."""
        metadata = f"Current Date: {datetime.now().isoformat()}"
        return self._render_evaluation_template(
            "jd_evaluation_criteria",
            text_content=resume_text,
            jd_text_content=jd_text,
            meta=metadata,
        )

    def _evaluate_prompt(
        self, system_template: str, prompt_template: str, **template_vars
    ) -> dict:
        """Assembles the evaluation prompt."""
        system_message = self.template_manager.render_template(system_template)
        if system_message is None:
            raise ValueError(f"Failed to load system template: {system_template}")

        full_prompt = self.template_manager.render_template(
            prompt_template, **template_vars
        )
        if full_prompt is None:
            raise ValueError(f"Failed to load prompt template: {prompt_template}")

        chat_params = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": full_prompt},
            ],
            "options": {
                "stream": False,
                "temperature": self.model_params.get("temperature", 0.5),
                "top_p": self.model_params.get("top_p", 0.9),
            },
        }

        kwargs = {"format": EvaluationData.model_json_schema()}
        response = self.provider.chat(**chat_params, **kwargs)

        response_text = extract_json_from_response(response["message"]["content"])
        logger.debug(f"LLM raw response: {response_text}")
        return json.loads(response_text)

    def evaluate_resume(self, resume_text: str) -> EvaluationData:
        """Default resume evaluation."""
        data = self._evaluate_prompt(
            system_template="resume_evaluation_system_message",
            prompt_template="resume_evaluation_criteria",
            text_content=resume_text,
        )
        return EvaluationData(**data)

    def evaluate_resume_with_jd(
        self, resume_text: str, jd_text: str
    ) -> EvaluationDataWithJD:
        """Evaluation with JD."""
        metadata = f"Current Date: {datetime.now().isoformat()}"
        data = self._evaluate_prompt(
            system_template="jd_system_message",
            prompt_template="jd_evaluation_criteria",
            text_content=resume_text,
            jd_text_content=jd_text,
            meta=metadata,
        )
        return EvaluationDataWithJD(**data)
