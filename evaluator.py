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

# Maps bonus category keys to keywords and point values for validation
BONUS_KEYWORD_MAP = {
    "gsoc": {
        "keywords": ["google summer of code", "gsoc"],
        "points": 5,
        "label": "Google Summer of Code (GSoC)"
    },
    "girlscript": {
        "keywords": ["girl script summer of code", "girlscript", "gssoc"],
        "points": 3,
        "label": "Girl Script Summer of Code"
    },
    "startup_founder": {
        "keywords": ["founder", "co-founder", "cofounder"],
        "points": 4,
        "label": "Startup Founder/Co-founder"
    },
}

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

    def _load_evaluation_prompt(self, resume_text: str) -> str:
        criteria_template = self.template_manager.render_template(
            "resume_evaluation_criteria", text_content=resume_text
        )
        if criteria_template is None:
            raise ValueError("Failed to load resume evaluation criteria template")
        return criteria_template

    def validate_bonus_points(
        self,
        evaluation_data: EvaluationData,
        resume_text: str,
    ) -> EvaluationData:
        """
        Cross-reference each bonus claim against the actual resume text.
        Removes any bonus that cannot be verified, recalculates total.
        """
        resume_lower = resume_text.lower()
        breakdown_text = evaluation_data.bonus_points.breakdown.lower()

        # Sum of points the LLM claimed for hallucination-prone categories
        claimed_hallucination_points = 0
        validated_hallucination_points = 0
        validated_breakdown_parts = []

        for key, info in BONUS_KEYWORD_MAP.items():
            category_mentioned = any(kw in breakdown_text for kw in info["keywords"])
            if not category_mentioned:
                continue

            claimed_hallucination_points += info["points"]

            found_in_resume = any(kw in resume_lower for kw in info["keywords"])
            if found_in_resume:
                validated_hallucination_points += info["points"]
                validated_breakdown_parts.append(
                    f"{info['label']}: +{info['points']} pts"
                )
                logger.info(f"Bonus verified in resume: {info['label']}")
            else:
                logger.warning(
                    f"Hallucinated bonus removed: '{info['label']}' "
                    f"not found in resume text."
                )

        # Preserve non-hallucination-prone bonus (portfolio, LinkedIn, blog)
        other_points = max(
            0,
            evaluation_data.bonus_points.total - claimed_hallucination_points
        )

        validated_total = min(
            validated_hallucination_points + other_points,
            MAX_BONUS_POINTS
        )

        new_breakdown = (
            "; ".join(validated_breakdown_parts) + (
                f"; Other: +{other_points} pts" if other_points > 0 else ""
            )
            if (validated_breakdown_parts or other_points > 0)
            else "No verifiable bonus achievements found"
        )

        evaluation_dict = evaluation_data.model_dump()
        evaluation_dict["bonus_points"]["total"] = validated_total
        evaluation_dict["bonus_points"]["breakdown"] = new_breakdown
        return EvaluationData(**evaluation_dict)

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
            evaluation_data = self.validate_bonus_points(evaluation_data, resume_text)

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise
