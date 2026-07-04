from typing import Dict, List, Optional, Tuple, Any, Type, Callable
from pydantic import BaseModel, Field, field_validator
from models import (
    JSONResume,
    EvaluationData,
    JobDescriptionData,
    JobScores,
    JobCategoryScore,
    LLMJobEvaluationResponse,
    JobEvaluationData,
    KeywordMatchResult,
    SeniorityAssessment,
    ScoreSummary,
)
from llm_utils import initialize_llm_provider, extract_json_from_response
from keyword_matching import (
    compute_keyword_match,
    build_skills_evidence,
    compute_industry_mentions,
    apply_knockout_resolutions,
    KNOCKOUT_CAP,
)
from seniority import assess_seniority
from weight_profiles import get_profile, DEFAULT_PROFILE
from config import DEVELOPMENT_MODE
import logging
import json
import re
import os
import hashlib

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120

# Bump whenever job_evaluation_criteria.jinja or its inputs change materially,
# so warm jobevalcache_* entries produced by an older prompt version are not
# silently served after a prompt upgrade.
PROMPT_VERSION = "2"

# Bump whenever why_this_score.jinja changes materially.
SUMMARY_PROMPT_VERSION = "1"

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


def _hash_key(*parts: str) -> str:
    digest = hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _read_llm_cache(path: str, model_cls: Type[BaseModel]) -> Optional[BaseModel]:
    if not DEVELOPMENT_MODE or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as cache_file:
            cached_data = json.load(cache_file)
        return model_cls(**cached_data)
    except Exception as e:
        logger.warning(f"⚠️ Warning: Invalid cache file {path}: {e}. Ignoring cache and re-running LLM call.")
        try:
            os.remove(path)
        except Exception as delete_err:
            logger.warning(f"Failed to delete invalid cache file {path}: {delete_err}")
        return None


def _write_llm_cache(path: str, model_obj: BaseModel) -> None:
    if not DEVELOPMENT_MODE:
        return
    try:
        os.makedirs("cache", exist_ok=True)
        with open(path, "w", encoding="utf-8") as cache_file:
            json.dump(model_obj.model_dump(), cache_file, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to write cache file {path}: {e}")


class JobDescriptionEvaluator:
    def __init__(
        self,
        job_description: str,
        model_name: str = DEFAULT_MODEL,
        model_params: dict = None,
        weight_profile: str = DEFAULT_PROFILE,
    ):
        if not job_description or not job_description.strip():
            raise ValueError("Job description cannot be empty")
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.job_description = job_description
        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.1, "top_p": 0.9}
        )
        self.weight_profile = weight_profile
        self.weights = get_profile(weight_profile)
        self.template_manager = TemplateManager()
        self.provider = initialize_llm_provider(model_name)
        self._load_embedding_model()

    def _load_embedding_model(self):
        from sentence_transformers import SentenceTransformer
        logger.info("Loading Sentence Transformers model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    def extract_job_requirements(self) -> JobDescriptionData:
        cache_path = f"cache/jdreqcache_{_hash_key(self.model_name, self.job_description)}.json"
        cached = _read_llm_cache(cache_path, JobDescriptionData)
        if cached is not None:
            logger.info(f"Loaded job requirements from cache {cache_path}")
            return cached

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
        job_data = JobDescriptionData(**json.loads(response_text))
        _write_llm_cache(cache_path, job_data)
        return job_data

    def compute_semantic_score(self, resume_text: str) -> float:
        from sentence_transformers import util
        job_embedding = self.embedding_model.encode(self.job_description, convert_to_tensor=True)
        resume_embedding = self.embedding_model.encode(resume_text, convert_to_tensor=True)
        similarity = util.cos_sim(job_embedding, resume_embedding).item()
        return round(max(0.0, similarity) * 100, 1)

    def _score_resume(
        self,
        resume_text: str,
        job_data: JobDescriptionData,
        keyword_result: KeywordMatchResult,
        seniority: Optional[SeniorityAssessment] = None,
    ) -> LLMJobEvaluationResponse:
        cache_path = (
            f"cache/jobevalcache_{_hash_key(self.model_name, PROMPT_VERSION, self.job_description)}"
            f"_{_hash_key(resume_text)}.json"
        )
        cached = _read_llm_cache(cache_path, LLMJobEvaluationResponse)
        if cached is not None:
            logger.info(f"Loaded job evaluation from cache {cache_path}")
            return cached

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
            matched_required=keyword_result.matched_required,
            missing_required=keyword_result.missing_required,
            missing_preferred=keyword_result.missing_preferred,
            seniority=seniority,
            industry=job_data.industry,
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
        evaluation_response = LLMJobEvaluationResponse(**json.loads(response_text))
        _write_llm_cache(cache_path, evaluation_response)
        return evaluation_response

    def generate_score_summary(self, evaluation: JobEvaluationData) -> Optional[str]:
        try:
            canonical_payload = json.dumps(
                evaluation.model_dump(exclude={"score_summary"}), sort_keys=True, ensure_ascii=False
            )
            cache_path = (
                f"cache/summarycache_{_hash_key(self.model_name, SUMMARY_PROMPT_VERSION, canonical_payload)}.json"
            )
            cached = _read_llm_cache(cache_path, ScoreSummary)
            if cached is not None:
                logger.info(f"Loaded score summary from cache {cache_path}")
                return cached.summary

            prompt = self.template_manager.render_template(
                "why_this_score",
                job_title=evaluation.job_title,
                weight_profile=evaluation.weight_profile,
                weighted_total=evaluation.weighted_total,
                scores=evaluation.scores,
                semantic_match_score=evaluation.semantic_match_score,
                keyword_match=evaluation.keyword_match,
                seniority=evaluation.seniority,
                key_strengths=evaluation.key_strengths,
                areas_for_improvement=evaluation.areas_for_improvement,
            )
            if prompt is None:
                raise ValueError("Failed to render why_this_score template")

            chat_params = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a technical recruiter explaining a match score to a hiring manager. Return only the paragraph.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": self.model_params.get("temperature", 0.1),
                    "top_p": self.model_params.get("top_p", 0.9),
                },
            }

            response = self.provider.chat(**chat_params)
            summary = response["message"]["content"].strip()
            _write_llm_cache(cache_path, ScoreSummary(summary=summary))
            return summary
        except Exception as e:
            logger.warning(f"Failed to generate score summary: {e}")
            return None

    def _compute_weighted_total(self, scores: JobScores, semantic_score: float) -> float:
        total = (
            scores.skills_match.score * self.weights["skills_match"]
            + scores.experience_match.score * self.weights["experience_match"]
            + semantic_score * self.weights["semantic_match"]
            + scores.job_title_alignment.score * self.weights["job_title_alignment"]
            + scores.education.score * self.weights["education"]
            + scores.resume_quality.score * self.weights["resume_quality"]
            + scores.missing_critical_requirements.score * self.weights["missing_critical_requirements"]
        )
        return round(min(total, 100.0), 1)

    def evaluate(
        self,
        resume_text: str,
        resume_data: Optional[JSONResume] = None,
        knockout_resolver: Optional[Callable[[str], Optional[bool]]] = None,
    ) -> JobEvaluationData:
        logger.info("Extracting requirements from job description...")
        job_data = self.extract_job_requirements()
        logger.info(f"Job title: {job_data.job_title} | Required skills: {job_data.required_skills}")

        logger.info("Computing deterministic keyword match...")
        keyword_result = compute_keyword_match(job_data, resume_text, resume_data)
        logger.info(
            f"Keyword coverage: {keyword_result.coverage_score} | "
            f"Missing required: {keyword_result.missing_required}"
        )

        keyword_result = apply_knockout_resolutions(keyword_result, knockout_resolver)
        if keyword_result.knockout_failed:
            logger.info("A must-have qualification was rejected by the reviewer — capping score.")

        logger.info("Assessing job-title seniority...")
        seniority = assess_seniority(job_data.job_title, resume_data)
        if seniority:
            logger.info(
                f"Seniority: target={seniority.target_label} | candidate={seniority.candidate_label} "
                f"| gap={seniority.gap}"
            )

        industry_match = compute_industry_mentions(job_data.industry, resume_data)

        logger.info("Computing semantic similarity score...")
        semantic_score = self.compute_semantic_score(resume_text)
        logger.info(f"Semantic match score: {semantic_score}")

        logger.info("Scoring resume against job requirements...")
        llm_result = self._score_resume(resume_text, job_data, keyword_result, seniority)

        scores = JobScores(
            skills_match=JobCategoryScore(
                score=keyword_result.coverage_score,
                evidence=build_skills_evidence(keyword_result),
            ),
            experience_match=llm_result.scores.experience_match,
            job_title_alignment=llm_result.scores.job_title_alignment,
            education=llm_result.scores.education,
            resume_quality=llm_result.scores.resume_quality,
            missing_critical_requirements=llm_result.scores.missing_critical_requirements,
        )

        weighted_total = self._compute_weighted_total(scores, semantic_score)
        if keyword_result.knockout_failed:
            weighted_total = min(weighted_total, KNOCKOUT_CAP)

        result = JobEvaluationData(
            scores=scores,
            semantic_match_score=semantic_score,
            weighted_total=weighted_total,
            key_strengths=llm_result.key_strengths,
            areas_for_improvement=llm_result.areas_for_improvement,
            job_title=job_data.job_title,
            keyword_match=keyword_result,
            seniority=seniority,
            jd_years_of_experience=job_data.years_of_experience,
            weight_profile=self.weight_profile,
            industry_match=industry_match,
        )

        logger.info("Generating score summary...")
        result.score_summary = self.generate_score_summary(result)

        return result
