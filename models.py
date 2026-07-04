import threading
import time
from typing import List, Optional, Dict, Tuple, Any, Literal, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to the LLM provider."""
        ...


class Location(BaseModel):
    """Location information for JSON Resume format."""

    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    """Social profile information for JSON Resume format."""

    network: Optional[str] = None
    username: Optional[str] = None
    url: str


class Basics(BaseModel):
    """Basic information for JSON Resume format."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: Optional[List[Profile]] = None


class Work(BaseModel):
    """Work experience for JSON Resume format."""

    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Volunteer(BaseModel):
    """Volunteer experience for JSON Resume format."""

    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class Education(BaseModel):
    """Education information for JSON Resume format."""

    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: Optional[List[str]] = None


class Award(BaseModel):
    """Award information for JSON Resume format."""

    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    """Certificate information for JSON Resume format."""

    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    """Publication information for JSON Resume format."""

    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    """Skill information for JSON Resume format."""

    name: Optional[str] = None
    level: Optional[str] = None
    keywords: Optional[List[str]] = None


class Language(BaseModel):
    """Language information for JSON Resume format."""

    language: Optional[str] = None
    fluency: Optional[str] = None


class Interest(BaseModel):
    """Interest information for JSON Resume format."""

    name: Optional[str] = None
    keywords: Optional[List[str]] = None


class Reference(BaseModel):
    """Reference information for JSON Resume format."""

    name: Optional[str] = None
    reference: Optional[str] = None


class Project(BaseModel):
    """Project information for JSON Resume format."""

    name: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None
    url: Optional[str] = None
    technologies: Optional[List[str]] = None
    skills: Optional[List[str]] = None


class BasicsSection(BaseModel):
    """Basics section containing basic information."""

    basics: Optional[Basics] = None


class WorkSection(BaseModel):
    """Work section containing a list of work experiences."""

    work: Optional[List[Work]] = None


class EducationSection(BaseModel):
    """Education section containing a list of education entries."""

    education: Optional[List[Education]] = None


class SkillsSection(BaseModel):
    """Skills section containing a list of skill categories."""

    skills: Optional[List[Skill]] = None


class ProjectsSection(BaseModel):
    """Projects section containing a list of projects."""

    projects: Optional[List[Project]] = None


class AwardsSection(BaseModel):
    """Awards section containing a list of awards."""

    awards: Optional[List[Award]] = None


class JSONResume(BaseModel):
    """Complete JSON Resume format model."""

    basics: Optional[Basics] = None
    work: Optional[List[Work]] = None
    volunteer: Optional[List[Volunteer]] = None
    education: Optional[List[Education]] = None
    awards: Optional[List[Award]] = None
    certificates: Optional[List[Certificate]] = None
    publications: Optional[List[Publication]] = None
    skills: Optional[List[Skill]] = None
    languages: Optional[List[Language]] = None
    interests: Optional[List[Interest]] = None
    references: Optional[List[Reference]] = None
    projects: Optional[List[Project]] = None


class CategoryScore(BaseModel):
    score: float = Field(ge=0, description="Score achieved in this category")
    max: int = Field(gt=0, description="Maximum possible score")
    evidence: str = Field(min_length=1, description="Evidence supporting the score")


class Scores(BaseModel):
    open_source: CategoryScore
    self_projects: CategoryScore
    production: CategoryScore
    technical_skills: CategoryScore


class BonusPoints(BaseModel):
    total: float = Field(ge=0, le=20, description="Total bonus points")
    breakdown: str = Field(description="Breakdown of bonus points")


class Deductions(BaseModel):
    total: float = Field(
        ge=0,
        description="Total deduction points (stored as positive, applied as negative)",
    )
    reasons: str = Field(description="Reasons for deductions")


class EvaluationData(BaseModel):
    scores: Scores
    bonus_points: BonusPoints
    deductions: Deductions
    key_strengths: List[str] = Field(min_items=1, max_items=5)
    areas_for_improvement: List[str] = Field(min_items=1, max_items=5)


class JobDescriptionData(BaseModel):
    job_title: str
    required_skills: List[str]
    preferred_skills: List[str] = []
    years_of_experience: Optional[float] = None
    education_requirements: Optional[str] = None
    must_have_qualifications: List[str] = []
    industry: Optional[str] = None


class JobCategoryScore(BaseModel):
    score: float = Field(ge=0, le=100, description="Score for this category out of 100")
    evidence: str = Field(min_length=1, description="Evidence from the resume supporting this score")


class JobScores(BaseModel):
    skills_match: JobCategoryScore
    experience_match: JobCategoryScore
    job_title_alignment: JobCategoryScore
    education: JobCategoryScore
    resume_quality: JobCategoryScore
    missing_critical_requirements: JobCategoryScore


class LLMJobScores(BaseModel):
    experience_match: JobCategoryScore
    job_title_alignment: JobCategoryScore
    education: JobCategoryScore
    resume_quality: JobCategoryScore
    missing_critical_requirements: JobCategoryScore


class LLMJobEvaluationResponse(BaseModel):
    scores: LLMJobScores
    key_strengths: List[str] = Field(min_items=1, max_items=5)
    areas_for_improvement: List[str] = Field(min_items=1, max_items=5)


class ParseabilityResult(BaseModel):
    table_count: int = 0
    image_count: int = 0
    max_columns_detected: int = 1
    warnings: List[str] = []
    parseability_score: float = Field(ge=0, le=100)


class SeniorityAssessment(BaseModel):
    target_level: int
    target_label: str
    candidate_level: int
    candidate_label: str
    highest_level: int
    highest_label: str
    gap: int


class IndustryMatch(BaseModel):
    industry: str
    mention_count: int = 0
    matched_entries: List[str] = []


class MustHaveStatus(BaseModel):
    qualification: str
    status: Literal["found", "not_found", "unverifiable"]
    resolved: Optional[bool] = None


class SkillExperience(BaseModel):
    skill: str
    years: float = Field(ge=0)
    evidence: List[str] = []


class KeywordMatchResult(BaseModel):
    matched_required: List[str] = []
    missing_required: List[str] = []
    matched_preferred: List[str] = []
    missing_preferred: List[str] = []
    must_have_status: List[MustHaveStatus] = []
    coverage_score: float = Field(ge=0, le=100)
    gated: bool = False
    knockout_failed: bool = False
    skill_experience: Optional[List[SkillExperience]] = None
    estimated_total_years: Optional[float] = None


class ScoreSummary(BaseModel):
    summary: str


class JobEvaluationData(BaseModel):
    scores: JobScores
    semantic_match_score: float = Field(ge=0, le=100)
    weighted_total: float = Field(ge=0, le=100)
    key_strengths: List[str]
    areas_for_improvement: List[str]
    job_title: str
    keyword_match: Optional[KeywordMatchResult] = None
    seniority: Optional[SeniorityAssessment] = None
    jd_years_of_experience: Optional[float] = None
    weight_profile: str = "engineering"
    industry_match: Optional[IndustryMatch] = None
    score_summary: Optional[str] = None


class GitHubProfile(BaseModel):
    """Pydantic model for GitHub profile data."""

    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    avatar_url: Optional[str] = None
    blog: Optional[str] = None
    twitter_username: Optional[str] = None
    hireable: Optional[bool] = None


class OllamaProvider:
    """Ollama LLM provider implementation."""

    def __init__(self):
        import ollama

        self.client = ollama

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama."""

        ollama_options = options.copy() if options else {}

        # remove steam from ollama options
        ollama_options.pop("stream", None)

        # Add num_ctx 32K context window to options
        ollama_options["num_ctx"] = 32768

        # convert to chat params
        chat_params = {
            "model": model,
            "messages": messages,
            "options": ollama_options,
        }

        # add it to top level
        if "stream" in kwargs:
            chat_params["stream"] = kwargs["stream"]

        if "format" in kwargs:
            chat_params["format"] = kwargs["format"]

        return self.client.chat(**chat_params)


class GeminiRateLimiter:
    """Proactive client-side pacing for Gemini API calls.

    Sleeps before a request if it would arrive sooner than min_interval
    after the previous request, spreading calls out so the free-tier
    per-minute quota is rarely hit in the first place. This is separate
    from (and complementary to) the reactive 429 backoff in GeminiProvider.
    """

    def __init__(self, requests_per_minute: float):
        self.min_interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._last_request_time: Optional[float] = None
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            if self.min_interval <= 0 or self._last_request_time is None:
                self._last_request_time = time.monotonic()
                return

            wait = self._last_request_time + self.min_interval - time.monotonic()
            if wait > 0:
                print(
                    f"[GeminiProvider] Pacing: waiting {wait:.1f}s to stay under "
                    f"{60.0 / self.min_interval:.1f} req/min"
                )
                time.sleep(wait)

            self._last_request_time = time.monotonic()


def _get_gemini_rate_limiter() -> GeminiRateLimiter:
    global _GEMINI_RATE_LIMITER
    if _GEMINI_RATE_LIMITER is None:
        from config import GEMINI_REQUESTS_PER_MINUTE

        _GEMINI_RATE_LIMITER = GeminiRateLimiter(GEMINI_REQUESTS_PER_MINUTE)
    return _GEMINI_RATE_LIMITER


_GEMINI_RATE_LIMITER: Optional[GeminiRateLimiter] = None


class GeminiProvider:
    """Google Gemini API provider implementation."""

    def __init__(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.client = genai

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat request to Google Gemini API."""
        import re
        import time
        import random
        from google.api_core.exceptions import ResourceExhausted

        MAX_RETRIES = 5
        BASE_DELAY = 10.0  # seconds — base for exponential backoff
        MAX_DELAY = 120.0  # cap so we never wait more than 2 minutes

        # Map options to Gemini parameters
        generation_config = {}
        if options:
            if "temperature" in options:
                generation_config["temperature"] = options["temperature"]
            if "top_p" in options:
                generation_config["top_p"] = options["top_p"]

        # Create a Gemini model
        gemini_model = self.client.GenerativeModel(
            model_name=model, generation_config=generation_config
        )

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        for attempt in range(MAX_RETRIES):
            try:
                _get_gemini_rate_limiter().acquire()

                # Send the chat request
                response = gemini_model.generate_content(gemini_messages)

                # Convert Gemini response to Ollama-like format for compatibility
                return {"message": {"role": "assistant", "content": response.text}}

            except ResourceExhausted as e:
                if attempt == MAX_RETRIES - 1:
                    # All retries exhausted — re-raise the original exception.
                    # This surfaces unrecoverable quota errors (RPD, TPM, etc.)
                    # instead of silently failing or returning bad data.
                    raise

                # Parse the API-suggested retry delay from the error message
                match = re.search(r"retry[_ ]in\s+([\d.]+)s", str(e), re.IGNORECASE)
                api_hint = float(match.group(1)) if match else None

                # Exponential backoff: BASE_DELAY * 2^attempt, capped at MAX_DELAY
                exp_delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)

                # Prefer the API hint when it is shorter than our computed delay
                delay = api_hint if (api_hint and api_hint < exp_delay) else exp_delay

                # Add ±20% randomized jitter to avoid thundering herd
                sleep_time = round(delay * random.uniform(0.8, 1.2), 2)

                print(
                    f"[GeminiProvider] Rate limit hit "
                    f"(attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
