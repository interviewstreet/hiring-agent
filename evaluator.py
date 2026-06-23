from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from models import JSONResume, EvaluationData
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
    # High-value bonus claims that smaller models commonly fabricate. Maps a
    # human-readable claim to the keywords that signal it; the same keywords must
    # appear in the candidate's resume/GitHub text for the claim to be verifiable.
    VERIFIABLE_BONUS_CLAIMS = {
        "Google Summer of Code (GSoC)": ["gsoc", "google summer of code"],
        "Girl Script Summer of Code": ["girl script", "girlscript", "gssoc"],
        "Startup Founder/Co-founder": ["founder", "co-founder", "cofounder"],
    }

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

            evaluation_data = self._validate_bonus_points(
                evaluation_data, self._last_resume_text
            )

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise

    def _validate_bonus_points(
        self, evaluation_data: EvaluationData, input_text: str
    ) -> EvaluationData:
        """Zero out bonus points if any high-value claim cannot be verified.

        The LLM (especially smaller models) fabricates bonus claims such as GSoC
        or startup-founder experience that do not appear in the resume or GitHub
        data. A claim is unverifiable when its keyword shows up in the LLM's
        breakdown but nowhere in the input text. If any such claim is found, the
        bonus total is zeroed to prevent score inflation.
        """
        bonus = evaluation_data.bonus_points
        if not bonus or bonus.total <= 0:
            return evaluation_data

        breakdown_lower = (bonus.breakdown or "").lower()
        text_lower = (input_text or "").lower()

        unverifiable = [
            claim
            for claim, keywords in self.VERIFIABLE_BONUS_CLAIMS.items()
            if any(kw in breakdown_lower for kw in keywords)
            and not any(kw in text_lower for kw in keywords)
        ]

        if unverifiable:
            logger.warning(
                "⚠️ Zeroing bonus points: claim(s) not found in resume/GitHub data: "
                + ", ".join(unverifiable)
            )
            bonus.breakdown = (
                "Bonus points zeroed: unverifiable claim(s) not present in "
                f"resume/GitHub data: {', '.join(unverifiable)}. "
                f"Original breakdown: {bonus.breakdown}"
            )
            bonus.total = 0

        return evaluation_data
