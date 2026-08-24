from typing import List, Optional, Dict, Tuple, Any, Type, Protocol, runtime_checkable
from pydantic import BaseModel, Field, create_model, field_validator


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


class Deductions(BaseModel):
    total: float = Field(
        ge=0,
        description="Total deduction points (stored as positive, applied as negative)",
    )
    reasons: str = Field(description="Reasons for deductions")


def build_scores_model(categories) -> Type[BaseModel]:
    """Build a ``Scores`` model with one CategoryScore field per role category.

    Using ``create_model`` (rather than a loose ``Dict[str, CategoryScore]``)
    keeps the emitted JSON schema concrete — the exact category property names —
    so the LLM's structured output stays as constrained as the old fixed schema.
    """
    fields = {category.key: (CategoryScore, ...) for category in categories}
    return create_model("Scores", **fields)


def build_evaluation_model(role) -> Type[BaseModel]:
    """Build the full ``EvaluationData`` model for a given role.

    Categories/weights and the bonus cap come from the role definition, so each
    role scores against its own rubric.
    """
    scores_model = build_scores_model(role.categories)

    bonus_model = create_model(
        "BonusPoints",
        total=(
            float,
            Field(ge=0, le=role.bonus_max, description="Total bonus points"),
        ),
        breakdown=(str, Field(description="Breakdown of bonus points")),
    )

    return create_model(
        "EvaluationData",
        scores=(scores_model, ...),
        bonus_points=(bonus_model, ...),
        deductions=(Deductions, ...),
        key_strengths=(List[str], Field(min_items=1, max_items=5)),
        areas_for_improvement=(List[str], Field(min_items=1, max_items=5)),
    )


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


class OpenAICompatibleProvider:
    """Generic OpenAI-chat-compatible LLM provider.

    Works for Ollama (/v1), Gemini (/v1beta/openai), OpenAI, Groq, OpenRouter,
    DeepSeek, LM Studio, vLLM, etc. via a configurable base_url. Adapts the
    response to the {"message": {"content": ...}} shape the evaluator expects.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        structured_output: str = "json_schema",
        extra_body: Optional[Dict[str, Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.structured_output = structured_output
        self.extra_body = extra_body or {}

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        import requests
        import time
        import random

        options = options or {}
        body: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if "temperature" in options:
            body["temperature"] = options["temperature"]
        if "top_p" in options:
            body["top_p"] = options["top_p"]

        # Structured-output translation: evaluator passes format=<json schema>.
        if "format" in kwargs and self.structured_output != "none":
            schema = kwargs["format"]
            if self.structured_output == "json_schema":
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": schema},
                }
            elif self.structured_output == "json_object":
                body["response_format"] = {"type": "json_object"}

        body.update(self.extra_body)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/chat/completions"

        MAX_RETRIES = 5
        BASE_DELAY = 10.0  # seconds — base for exponential backoff
        MAX_DELAY = 120.0  # cap so we never wait more than 2 minutes
        # Transient server errors worth retrying with backoff. Unlike 429 these
        # rarely carry a Retry-After header, so we always use exponential backoff.
        RETRYABLE_SERVER_ERRORS = {500, 502, 503, 504}
        for attempt in range(MAX_RETRIES):
            response = requests.post(url, json=body, headers=headers, timeout=300)

            if response.status_code == 429 and attempt < MAX_RETRIES - 1:
                retry_after = response.headers.get("Retry-After")
                exp_delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                delay = float(retry_after) if retry_after else exp_delay
                sleep_time = round(delay * random.uniform(0.8, 1.2), 2)
                print(
                    f"[OpenAICompatibleProvider] Rate limit hit "
                    f"(attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            if (
                response.status_code in RETRYABLE_SERVER_ERRORS
                and attempt < MAX_RETRIES - 1
            ):
                exp_delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                sleep_time = round(exp_delay * random.uniform(0.8, 1.2), 2)
                print(
                    f"[OpenAICompatibleProvider] Transient server error "
                    f"{response.status_code} (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            response.raise_for_status()
            data = response.json()
            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise ValueError(f"Unexpected response shape from {url}: {data}")
            return {"message": {"role": "assistant", "content": content}}


class BedrockConverseProvider:
    """AWS Bedrock provider using the Converse API.

    Bedrock is not OpenAI-compatible over SigV4, so it needs its own transport
    rather than a different base_url. Three differences drive this class:

    1. Auth is SigV4, handled by botocore from the standard credential chain
       (env vars, ~/.aws/credentials, instance/task role). There is no API key,
       which is why providers.json declares no ``api_key_env`` for bedrock.
    2. ``system`` is a top-level parameter, not a message with role="system".
    3. There is no ``response_format``. Structured output is obtained by
       declaring a tool whose ``inputSchema.json`` is the caller's JSON schema
       and forcing ``toolChoice``, so the model must answer through it.

    Returns the same ``{"message": {"content": ...}}`` shape as
    OpenAICompatibleProvider, so pdf.py / evaluator.py / github.py are unchanged.
    In structured mode the tool input is serialized back to a JSON string, which
    keeps ``extract_json_from_response`` + ``json.loads`` working as-is.
    """

    #: Name of the synthetic tool used to carry structured output.
    TOOL_NAME = "emit_structured_response"

    def __init__(
        self,
        region: str,
        structured_output: str = "bedrock_tool",
        max_tokens: int = 8192,
        extra_body: Optional[Dict[str, Any]] = None,
    ):
        self.region = region
        self.structured_output = structured_output
        self.max_tokens = max_tokens
        self.extra_body = extra_body or {}
        self._client = None

    @property
    def client(self):
        """Lazily build the boto3 client so importing this module never needs boto3."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise ImportError(
                    "The bedrock provider requires boto3. Install it with "
                    "`pip install boto3` (it is pinned in requirements.txt)."
                ) from exc
            # Adaptive mode retries ThrottlingException with client-side rate
            # limiting, which is what Bedrock returns under on-demand pressure.
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
                config=Config(
                    retries={"max_attempts": 5, "mode": "adaptive"},
                    read_timeout=300,
                    connect_timeout=10,
                ),
            )
        return self._client

    @staticmethod
    def _split_messages(messages: List[Dict[str, str]]):
        """Split OpenAI-style messages into (system_blocks, converse_messages).

        Converse requires system prompts out-of-band and rejects consecutive
        messages with the same role, so same-role runs are merged.
        """
        system_blocks = []
        converse: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            text = msg.get("content") or ""
            if role == "system":
                if text:
                    system_blocks.append({"text": text})
                continue
            role = "assistant" if role == "assistant" else "user"
            if converse and converse[-1]["role"] == role:
                converse[-1]["content"][0]["text"] += "\n\n" + text
            else:
                converse.append({"role": role, "content": [{"text": text}]})
        # Converse requires the first message to be from the user.
        if not converse:
            converse = [{"role": "user", "content": [{"text": ""}]}]
        return system_blocks, converse

    @staticmethod
    def _parse_embedded_json(value, _depth=0):
        """Recursively parse values that are JSON objects/arrays sent as strings.

        Some models serialize nested tool-call fields as strings, e.g.
        ``{"bonus_points": "{\\"total\\": 3}"}`` instead of a nested object
        (observed on claude-haiku-4-5). Only strings that begin with ``{`` or
        ``[`` are considered, so prose fields such as ``evidence`` and
        ``breakdown`` are never touched.
        """
        import json as _json

        if _depth > 6:
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped[:1] in ("{", "["):
                # raw_decode rather than loads: claude-haiku-4-5 appends one
                # spurious closing brace to these strings, so the object is
                # complete but json.loads rejects the trailing character. Accept
                # the decoded prefix only when what follows is pure punctuation
                # noise — never when real content was dropped, which would mean
                # silently discarding part of a score.
                try:
                    parsed, end = _json.JSONDecoder().raw_decode(stripped)
                except ValueError:
                    return value
                if stripped[end:].strip(" \t\r\n,}]"):
                    return value
                return BedrockConverseProvider._parse_embedded_json(parsed, _depth + 1)
            return value
        if isinstance(value, dict):
            return {
                k: BedrockConverseProvider._parse_embedded_json(v, _depth + 1)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [
                BedrockConverseProvider._parse_embedded_json(v, _depth + 1)
                for v in value
            ]
        return value

    @staticmethod
    def _normalize_tool_input(payload, schema):
        """Repair two tool-input serialization quirks seen on Bedrock.

        Both were observed against the live API while scoring a real resume, and
        in both cases the model's *content* was correct — only its envelope was
        wrong, so repairing here is lossless rather than a guess:

        1. Envelope wrapping. claude-opus-5 returns the entire object nested
           under a single arbitrary key, e.g. ``{"parameter_name": {...}}`` or
           ``{"response": {...}}``. Unwrapped only when that lone key is not
           itself a schema property and the nested dict does contain schema
           properties, so a legitimate single-property response is left alone.

        2. Stringified nested values, handled by :meth:`_parse_embedded_json`.
        """
        if not isinstance(payload, dict):
            return payload

        properties = set((schema or {}).get("properties") or ())
        if properties and len(payload) == 1:
            (only_key,), (inner,) = payload.keys(), payload.values()
            if (
                only_key not in properties
                and isinstance(inner, dict)
                and properties & set(inner)
            ):
                payload = inner

        return BedrockConverseProvider._parse_embedded_json(payload)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        import json as _json

        options = options or {}
        system_blocks, converse_messages = self._split_messages(messages)

        inference_config: Dict[str, Any] = {"maxTokens": self.max_tokens}
        if "temperature" in options:
            inference_config["temperature"] = options["temperature"]
        if "top_p" in options:
            inference_config["topP"] = options["top_p"]

        request: Dict[str, Any] = {
            "modelId": model,
            "messages": converse_messages,
            "inferenceConfig": inference_config,
        }
        if system_blocks:
            request["system"] = system_blocks

        # Structured output: the caller's JSON schema becomes a forced tool call.
        wants_tool = "format" in kwargs and self.structured_output == "bedrock_tool"
        if wants_tool:
            request["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": self.TOOL_NAME,
                            "description": (
                                "Return the response as structured data matching "
                                "the provided schema."
                            ),
                            "inputSchema": {"json": kwargs["format"]},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": self.TOOL_NAME}},
            }

        request.update(self.extra_body)

        response = self.client.converse(**request)
        blocks = response.get("output", {}).get("message", {}).get("content", [])

        # Prefer the tool payload; fall back to concatenated text so that models
        # which ignore toolConfig (e.g. google.gemma-3-*) still return something
        # the shared JSON-extraction path can handle.
        for block in blocks:
            if "toolUse" in block:
                payload = self._normalize_tool_input(
                    block["toolUse"]["input"], kwargs.get("format")
                )
                return {
                    "message": {
                        "role": "assistant",
                        "content": _json.dumps(payload),
                    }
                }

        text = "".join(b["text"] for b in blocks if "text" in b)
        if not text:
            raise ValueError(
                f"Bedrock returned no text or toolUse content for model "
                f"'{model}'. stopReason={response.get('stopReason')!r}"
            )
        return {"message": {"role": "assistant", "content": text}}
