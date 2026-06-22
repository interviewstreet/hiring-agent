import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"


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


class CliLLMProvider:
    """LLM provider that routes chat requests through authenticated local CLIs.

    This lets the pipeline run using an already-authenticated local agent CLI
    session instead of Ollama, Gemini, or any API key. Backend-specific command
    shapes are kept in this class so Claude Code and Codex share the same
    prompt/schema/subprocess wrapper.

    Responses are wrapped to match Ollama's response shape so every existing
    consumer keeps working unchanged::

        {"message": {"content": "...model output..."}}
    """

    BACKENDS = {
        ModelProvider.CLAUDE_CODE.value: {
            "label": "Claude Code CLI",
            "default_command": "claude",
            "missing_help": (
                "Install it and sign in - an interactive `claude` session must "
                "be authenticated first (see https://claude.com/claude-code) - "
                "or set CLAUDE_CODE_COMMAND to the CLI's full path."
            ),
            "schema_output": "json_envelope",
            "supports_system_prompt": True,
        },
        ModelProvider.CODEX.value: {
            "label": "Codex CLI",
            "default_command": "codex",
            "missing_help": (
                "Install it and sign in with `codex login`, or set "
                "CODEX_COMMAND to the CLI's full path."
            ),
            "schema_output": "raw_json",
            "supports_system_prompt": False,
        },
    }

    def __init__(
        self,
        backend: str,
        command: Optional[str] = None,
        timeout: int = 300,
        model: Optional[str] = None,
    ):
        if backend not in self.BACKENDS:
            supported = ", ".join(sorted(self.BACKENDS))
            raise ValueError(
                f"Unsupported CLI backend '{backend}'. Use one of: {supported}"
            )

        self.backend = backend
        self.backend_config = self.BACKENDS[backend]
        self.command = command or self.backend_config["default_command"]
        self.timeout = timeout
        # Optional concrete model / alias. When None, the CLI uses its default.
        self.model = model or None

        # Fail fast with a clear, actionable message if the CLI is missing.
        command_path = shutil.which(self.command)
        if command_path is None:
            raise RuntimeError(
                f"{self.backend_config['label']} '{self.command}' was not found "
                f"on PATH. {self.backend_config['missing_help']}"
            )
        self.command_path = os.path.abspath(command_path)

    def _build_system_prompt(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Extract system messages for Claude's native system prompt flag."""
        system_parts = [
            m.get("content", "")
            for m in messages
            if m.get("role") == "system" and m.get("content")
        ]
        return "\n\n".join(system_parts) if system_parts else None

    def _format_json_schema(self, json_schema: Any = None) -> Optional[str]:
        """Return a compact, CLI-compatible JSON schema string."""
        if json_schema is None:
            return None
        if isinstance(json_schema, str):
            try:
                json_schema = json.loads(json_schema)
            except json.JSONDecodeError:
                return json_schema
        normalized_schema = self._normalize_json_schema(json_schema)
        return json.dumps(normalized_schema, separators=(",", ":"))

    def _normalize_json_schema(self, node: Any) -> Any:
        """Tighten Pydantic schemas for strict CLI structured-output validators."""
        if isinstance(node, list):
            return [self._normalize_json_schema(item) for item in node]
        if not isinstance(node, dict):
            return node

        normalized = {
            key: self._normalize_json_schema(value) for key, value in node.items()
        }
        properties = normalized.get("properties")
        if isinstance(properties, dict):
            normalized.setdefault("additionalProperties", False)
            normalized["required"] = list(properties.keys())
        return normalized

    def _build_prompt(
        self,
        messages: List[Dict[str, str]],
        requires_json: bool = False,
        include_system_prompt: bool = False,
    ) -> str:
        """Flatten non-system chat messages into a single prompt.

        Agent CLIs take a single prompt on stdin. For backends without a native
        system prompt flag, system messages are folded into the prompt.
        """
        convo_parts = []
        if include_system_prompt:
            system_prompt = self._build_system_prompt(messages)
            if system_prompt:
                convo_parts.append(f"System instructions:\n{system_prompt}")

        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if not content or role == "system":
                continue
            if role == "assistant":
                convo_parts.append(f"Assistant (previous turn):\n{content}")
            else:
                convo_parts.append(content)

        sections = ["\n\n".join(convo_parts)] if convo_parts else []

        if requires_json:
            sections.append(
                "Respond with a SINGLE valid JSON object and nothing else. "
                "Do not add explanations, comments, or prose. "
                "Do NOT wrap the JSON in Markdown code fences (no triple "
                "backticks of any kind). The response must strictly conform to "
                "the JSON Schema supplied to the CLI."
            )

        return "\n\n".join(sections)

    def _build_command(
        self,
        json_schema: Optional[str],
        system_prompt: Optional[str],
        temp_dir: str,
    ) -> tuple[list[str], str]:
        """Build backend-specific argv while sharing provider orchestration."""
        if self.backend == ModelProvider.CLAUDE_CODE.value:
            output_format = "json" if json_schema else "text"
            cmd = [
                self.command_path,
                "-p",
                "--input-format",
                "text",
                "--output-format",
                output_format,
                "--no-session-persistence",
                "--safe-mode",
            ]
            if system_prompt:
                cmd += ["--system-prompt", system_prompt]
            if json_schema:
                cmd += ["--json-schema", json_schema]
            if self.model:
                cmd += ["--model", self.model]
            # Keep --tools last: "" disables all tools and is variadic-safe at
            # the end of the argument list.
            cmd += ["--tools", ""]
            return cmd, os.path.expanduser("~")

        if self.backend == ModelProvider.CODEX.value:
            cmd = [
                self.command_path,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "-C",
                temp_dir,
            ]
            if json_schema:
                schema_path = os.path.join(temp_dir, "output_schema.json")
                with open(schema_path, "w", encoding="utf-8") as schema_file:
                    schema_file.write(json_schema)
                cmd += ["--output-schema", schema_path]
            if self.model:
                cmd += ["--model", self.model]
            cmd.append("-")
            return cmd, temp_dir

        raise RuntimeError(f"Unsupported CLI backend '{self.backend}'")

    def _extract_structured_content(self, content: str) -> str:
        """Normalize backend-specific structured-output envelopes to raw JSON."""
        if self.backend_config["schema_output"] == "json_envelope":
            try:
                cli_response = json.loads(content)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"{self.backend_config['label']} returned invalid JSON output "
                    "while structured output was requested.\n"
                    f"Stdout:\n{content}"
                ) from e

            if cli_response.get("is_error"):
                raise RuntimeError(
                    f"{self.backend_config['label']} reported an error while "
                    f"structured output was requested.\nResponse:\n{content}"
                )

            structured_output = cli_response.get("structured_output")
            if structured_output is None:
                result_text = cli_response.get("result")
                if result_text:
                    return str(result_text).strip()
                raise RuntimeError(
                    f"{self.backend_config['label']} did not include "
                    f"structured_output in its JSON response.\nResponse:\n{content}"
                )
            return json.dumps(structured_output, ensure_ascii=False)

        if self.backend_config["schema_output"] == "raw_json":
            try:
                return json.dumps(json.loads(content), ensure_ascii=False)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"{self.backend_config['label']} returned invalid JSON output "
                    "while structured output was requested.\n"
                    f"Stdout:\n{content}"
                ) from e

        raise RuntimeError(
            f"Unsupported schema output mode '{self.backend_config['schema_output']}'"
        )

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request through an authenticated local CLI.

        ``options`` (temperature / top_p / stream) is accepted for interface
        parity but ignored by CLI backends. ``kwargs["format"]`` is treated as
        a JSON schema and passed through each CLI's native schema mechanism.
        """
        json_schema = self._format_json_schema(kwargs.get("format"))
        supports_system_prompt = self.backend_config["supports_system_prompt"]
        prompt_text = self._build_prompt(
            messages,
            requires_json=bool(json_schema),
            include_system_prompt=not supports_system_prompt,
        )
        system_prompt = (
            self._build_system_prompt(messages) if supports_system_prompt else None
        )

        try:
            with tempfile.TemporaryDirectory(
                prefix=f"{self.backend}_provider_"
            ) as temp_dir:
                cmd, cwd = self._build_command(json_schema, system_prompt, temp_dir)
                result = subprocess.run(
                    cmd,
                    input=prompt_text,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=cwd,
                )
        except FileNotFoundError as e:
            raise RuntimeError(
                f"{self.backend_config['label']} '{self.command}' was not found. "
                f"{self.backend_config['missing_help']}"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"{self.backend_config['label']} timed out after {self.timeout}s. "
                "Increase the provider timeout if your prompts are large."
            ) from e

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(
                f"{self.backend_config['label']} exited with code "
                f"{result.returncode}.\n"
                f"Stderr:\n{stderr}"
            )

        content = (result.stdout or "").strip()
        if not content:
            stderr = (result.stderr or "").strip()
            detail = f"\nStderr:\n{stderr}" if stderr else ""
            raise RuntimeError(
                f"{self.backend_config['label']} returned an empty response.{detail}"
            )

        if json_schema:
            content = self._extract_structured_content(content)

        # Match Ollama's response shape so all consumers work unchanged.
        return {"message": {"role": "assistant", "content": content}}
