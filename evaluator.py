from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from models import (
    JSONResume,
    EvaluationData,
    JobDescriptionData,
    JobScores,
    LLMJobEvaluationResponse,
    JobEvaluationData,
)
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

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise


class JobDescriptionEvaluator:
    WEIGHTS = {
        "skills_match": 0.30,
        "experience_match": 0.20,
        "semantic_match": 0.15,
        "job_title_alignment": 0.10,
        "education": 0.10,
        "resume_quality": 0.10,
        "missing_critical_requirements": 0.05,
    }

    def __init__(self, job_description: str, model_name: str = DEFAULT_MODEL, model_params: dict = None):
        if not job_description or not job_description.strip():
            raise ValueError("Job description cannot be empty")
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.job_description = job_description
        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.1, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self.provider = initialize_llm_provider(model_name)
        self._load_embedding_model()

    def _load_embedding_model(self):
        from sentence_transformers import SentenceTransformer
        logger.info("Loading Sentence Transformers model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    def extract_job_requirements(self) -> JobDescriptionData:
        prompt = self.template_manager.render_template(
            "job_description_extraction", job_description=self.job_description
        )
        if prompt is None:
            raise ValueError("Failed to render job_description_extraction template")

        chat_params = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured requirements from job descriptions. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "options": self.model_params,
        }

        response = self.provider.chat(**chat_params, format=JobDescriptionData.model_json_schema())
        response_text = extract_json_from_response(response["message"]["content"])
        return JobDescriptionData(**json.loads(response_text))

    def compute_semantic_score(self, resume_text: str) -> float:
        from sentence_transformers import util
        job_embedding = self.embedding_model.encode(self.job_description, convert_to_tensor=True)
        resume_embedding = self.embedding_model.encode(resume_text, convert_to_tensor=True)
        similarity = util.cos_sim(job_embedding, resume_embedding).item()
        return round(max(0.0, similarity) * 100, 1)

    def _score_resume(self, resume_text: str, job_data: JobDescriptionData) -> LLMJobEvaluationResponse:
        system_message = self.template_manager.render_template("job_evaluation_system_message")
        if system_message is None:
            raise ValueError("Failed to render job_evaluation_system_message template")

        criteria_prompt = self.template_manager.render_template(
            "job_evaluation_criteria",
            job_description=self.job_description,
            job_title=job_data.job_title,
            required_skills=job_data.required_skills,
            preferred_skills=job_data.preferred_skills,
            years_of_experience=job_data.years_of_experience,
            education_requirements=job_data.education_requirements,
            must_have_qualifications=job_data.must_have_qualifications,
            resume_text=resume_text,
        )
        if criteria_prompt is None:
            raise ValueError("Failed to render job_evaluation_criteria template")

        chat_params = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": criteria_prompt},
            ],
            "options": {
                "stream": False,
                "temperature": self.model_params.get("temperature", 0.1),
                "top_p": self.model_params.get("top_p", 0.9),
            },
        }

        response = self.provider.chat(**chat_params, format=LLMJobEvaluationResponse.model_json_schema())
        response_text = extract_json_from_response(response["message"]["content"])
        logger.info(f"Job evaluation LLM response: {response_text}")
        return LLMJobEvaluationResponse(**json.loads(response_text))

    def _compute_weighted_total(self, scores: JobScores, semantic_score: float) -> float:
        total = (
            scores.skills_match.score * self.WEIGHTS["skills_match"]
            + scores.experience_match.score * self.WEIGHTS["experience_match"]
            + semantic_score * self.WEIGHTS["semantic_match"]
            + scores.job_title_alignment.score * self.WEIGHTS["job_title_alignment"]
            + scores.education.score * self.WEIGHTS["education"]
            + scores.resume_quality.score * self.WEIGHTS["resume_quality"]
            + scores.missing_critical_requirements.score * self.WEIGHTS["missing_critical_requirements"]
        )
        return round(min(total, 100.0), 1)

    def evaluate(self, resume_text: str) -> JobEvaluationData:
        logger.info("Extracting requirements from job description...")
        job_data = self.extract_job_requirements()
        logger.info(f"Job title: {job_data.job_title} | Required skills: {job_data.required_skills}")

        logger.info("Computing semantic similarity score...")
        semantic_score = self.compute_semantic_score(resume_text)
        logger.info(f"Semantic match score: {semantic_score}")

        logger.info("Scoring resume against job requirements...")
        llm_result = self._score_resume(resume_text, job_data)

        weighted_total = self._compute_weighted_total(llm_result.scores, semantic_score)

        return JobEvaluationData(
            scores=llm_result.scores,
            semantic_match_score=semantic_score,
            weighted_total=weighted_total,
            key_strengths=llm_result.key_strengths,
            areas_for_improvement=llm_result.areas_for_improvement,
            job_title=job_data.job_title,
        )
