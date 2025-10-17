from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from models import JSONResume, EvaluationData, CategoryScore
from llm_utils import initialize_llm_provider, extract_json_from_response
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
    def __init__(self, model_name: str = DEFAULT_MODEL, model_params: dict = None, role_description: Optional[str] = None):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self.role_description = role_description
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(self.model_name)

    def _load_evaluation_prompt(self, resume_text: str) -> str:
        criteria_template = self.template_manager.render_template(
            "resume_evaluation_criteria", text_content=resume_text
        )
        if criteria_template is None:
            raise ValueError("Failed to load resume evaluation criteria template")
        return criteria_template

    def evaluate_resume(self, resume_text: str) -> EvaluationData:
        self._last_resume_text = resume_text
        full_prompt = self._load_evaluation_prompt(resume_text)
        # logger.info(f"🔤 Evaluation prompt being sent: {full_prompt}")
        try:
            system_message = self.template_manager.render_template(
                "resume_evaluation_system_message"
            )
            if system_message is None:
                raise ValueError(
                    "Failed to load resume evaluation system message template"
                )

            # Prepare chat parameters
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

            # Add format parameter for structured output
            kwargs = {"format": EvaluationData.model_json_schema()}
            # Use the appropriate provider to make the API call
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = response["message"]["content"]
            response_text = extract_json_from_response(response_text)
            logger.error(f"🔤 Prompt response: {response_text}")

            evaluation_dict = json.loads(response_text)
            evaluation_data = EvaluationData(**evaluation_dict)

            # If role_description provided, perform a separate role-fit scoring call
            if self.role_description:
                role_fit_prompt = self.template_manager.render_template(
                    "role_fit", text_content=resume_text, role_description=self.role_description
                )
                if role_fit_prompt:
                    role_chat_params = {
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": "You score role fit strictly as JSON."},
                            {"role": "user", "content": role_fit_prompt},
                        ],
                        "options": {
                            "stream": False,
                            "temperature": self.model_params.get("temperature", 0.5),
                            "top_p": self.model_params.get("top_p", 0.9),
                        },
                    }
                    role_kwargs = {"format": CategoryScore.model_json_schema()}
                    role_resp = self.provider.chat(**role_chat_params, **role_kwargs)
                    role_text = extract_json_from_response(role_resp["message"]["content"])
                    role_data = CategoryScore(**json.loads(role_text))
                    # attach to scores if possible
                    if hasattr(evaluation_data, "scores") and evaluation_data.scores:
                        evaluation_data.scores.role_fit = role_data

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise
