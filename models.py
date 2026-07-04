from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


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

        if "format" in kwargs:
            chat_params["format"] = kwargs["format"]

        return self.client.chat(**chat_params)


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
        **kwargs,
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
                exp_delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)

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


class OpenRouterProvider:
    """OpenRouter (OpenAI-compatible) LLM provider implementation.

    OpenRouter exposes an OpenAI-compatible ``/chat/completions`` endpoint that
    proxies many hosted models (OpenAI, Anthropic, Google, Meta, DeepSeek, ...).
    Because the wire format matches what the rest of this codebase already uses
    (``system``/``user`` message roles), no message remapping is required.
    """

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request to OpenRouter and adapt the response.

        Returns an Ollama-shaped dict — ``{"message": {"content": ...}}`` — so
        callers stay provider-agnostic.
        """
        import time
        import random
        import requests

        options = options or {}

        payload: Dict[str, Any] = {"model": model, "messages": messages}
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        if "top_p" in options:
            payload["top_p"] = options["top_p"]

        # The rest of the codebase requests structured output via an Ollama-style
        # ``format`` kwarg (a JSON schema). OpenRouter's equivalent is
        # ``response_format``; JSON-object mode is the most broadly supported
        # option across the many models OpenRouter proxies.
        want_json = bool(kwargs.get("format"))
        if want_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Optional attribution headers recommended by OpenRouter.
            "X-Title": "hiring-agent",
        }

        url = f"{self.base_url}/chat/completions"

        MAX_RETRIES = 5
        BASE_DELAY = 5.0  # seconds — base for exponential backoff
        MAX_DELAY = 60.0  # cap so we never wait more than a minute

        for attempt in range(MAX_RETRIES):
            response = requests.post(url, headers=headers, json=payload, timeout=120)

            # Some models proxied by OpenRouter reject ``response_format``.
            # Fall back once by retrying the request without it.
            if response.status_code == 400 and "response_format" in payload:
                payload.pop("response_format", None)
                continue

            # Retry on rate limits (429) with exponential backoff + jitter.
            if response.status_code == 429 and attempt < MAX_RETRIES - 1:
                delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                sleep_time = round(delay * random.uniform(0.8, 1.2), 2)
                print(
                    f"[OpenRouterProvider] Rate limit hit "
                    f"(attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            response.raise_for_status()
            data = response.json()

            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(
                    f"Unexpected OpenRouter response shape: {data}"
                ) from exc

            return {"message": {"role": "assistant", "content": content}}

        # Retries exhausted (all attempts were 429s).
        raise RuntimeError(
            f"OpenRouter request failed after {MAX_RETRIES} attempts (rate limited)."
        )
