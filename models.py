import re
import time
import random
from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
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
        **kwargs,
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
    # ge=1 (not gt=0) so the JSON schema emits the inclusive `minimum`
    # keyword; Gemini's Schema type rejects `exclusiveMinimum`. Equivalent for
    # integers. See tests/test_schema_gemini_compat.py.
    max: int = Field(ge=1, description="Maximum possible score")
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
        **kwargs,
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

        if "format" in kwargs and kwargs["format"] is not None:
            fmt = kwargs["format"]
            # The canonical format is a pydantic model class; Ollama wants a
            # JSON-schema dict. A dict (or "json") is passed through untouched.
            if isinstance(fmt, type) and issubclass(fmt, BaseModel):
                fmt = fmt.model_json_schema()
            chat_params["format"] = fmt

        return self.client.chat(**chat_params)


def build_gemini_request(
    messages: List[Dict[str, str]],
    options: Optional[Dict[str, Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Translate the unified chat call into google-genai request pieces.

    Returns a dict with three keys:
      - ``system_instruction``: the concatenated system message(s), or None.
        Gemini takes the system prompt as a dedicated field rather than a
        conversation turn -- the legacy code mislabeled it as a "model" turn,
        which degraded instruction-following.
      - ``contents``: the non-system turns, with role "assistant" mapped to
        Gemini's "model".
      - ``generation_config``: temperature/top_p plus, when a ``format`` schema
        is supplied, ``response_mime_type``/``response_schema`` so structured
        output is enforced the same way Ollama enforces ``format``.
    """
    options = options or {}
    kwargs = kwargs or {}

    system_parts = [
        m["content"] for m in messages if m.get("role") == "system" and m.get("content")
    ]
    system_instruction = "\n\n".join(system_parts) if system_parts else None

    contents = []
    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": msg["content"]}]})

    generation_config: Dict[str, Any] = {}
    if "temperature" in options:
        generation_config["temperature"] = options["temperature"]
    if "top_p" in options:
        generation_config["top_p"] = options["top_p"]
    if kwargs.get("format"):
        generation_config["response_mime_type"] = "application/json"
        generation_config["response_schema"] = kwargs["format"]

    return {
        "system_instruction": system_instruction,
        "contents": contents,
        "generation_config": generation_config,
    }


class GeminiProvider:
    """Google Gemini provider built on the google-genai SDK."""

    MAX_RETRIES = 5
    BASE_DELAY = 10.0  # seconds — base for exponential backoff
    MAX_DELAY = 120.0  # cap so we never wait more than 2 minutes

    def __init__(self, api_key: str, client: Any = None):
        # ``client`` is injectable for testing; in production we build the real
        # google-genai client from the API key.
        if client is not None:
            self.client = client
        else:
            from google import genai

            self.client = genai.Client(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request to Gemini, returning an Ollama-compatible dict."""
        from google.genai import types
        from google.genai import errors

        req = build_gemini_request(messages, options, kwargs)
        config = types.GenerateContentConfig(
            system_instruction=req["system_instruction"],
            **req["generation_config"],
        )

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=req["contents"],
                    config=config,
                )
                # Normalize to the Ollama-like shape the rest of the code expects.
                return {"message": {"role": "assistant", "content": response.text}}

            except errors.APIError as e:
                # Only 429 (rate limit / resource exhausted) is retriable; let
                # everything else surface immediately.
                if getattr(e, "code", None) != 429 or attempt == self.MAX_RETRIES - 1:
                    raise

                # Parse the API-suggested retry delay from the error message.
                match = re.search(r"retry[_ ]in\s+([\d.]+)s", str(e), re.IGNORECASE)
                api_hint = float(match.group(1)) if match else None

                # Exponential backoff: BASE_DELAY * 2^attempt, capped at MAX_DELAY.
                exp_delay = min(self.BASE_DELAY * (2**attempt), self.MAX_DELAY)

                # Prefer the API hint when it is shorter than our computed delay.
                delay = api_hint if (api_hint and api_hint < exp_delay) else exp_delay

                # Add ±20% randomized jitter to avoid thundering herd.
                sleep_time = round(delay * random.uniform(0.8, 1.2), 2)

                print(
                    f"[GeminiProvider] Rate limit hit "
                    f"(attempt {attempt + 1}/{self.MAX_RETRIES}). "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
