import os
import json
import time
import shutil
import logging
import subprocess
from typing import List, Optional, Dict, Tuple, Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from enum import Enum

logger = logging.getLogger(__name__)

# Timeout (in seconds) applied to CLI based providers. Override with the
# LLM_CLI_TIMEOUT environment variable.
try:
    CLI_TIMEOUT = int(os.getenv("LLM_CLI_TIMEOUT", "300"))
except ValueError:
    CLI_TIMEOUT = 300


class ModelProvider(Enum):
    """Enum for supported model providers."""

    OLLAMA = "ollama"
    GEMINI = "gemini"  # Google Gemini HTTP API
    CLAUDE = "claude"  # Anthropic Claude HTTP API
    CLAUDE_CLI = "claude_cli"  # Claude Code command-line tool
    GEMINI_CLI = "gemini_cli"  # Gemini command-line tool


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

        # Send the chat request
        response = gemini_model.generate_content(gemini_messages)

        # Convert Gemini response to Ollama-like format for compatibility
        return {"message": {"role": "assistant", "content": response.text}}


def _split_system_and_user(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    """Split chat messages into a combined system string and a user-prompt string.

    All call sites in this project send exactly one system + one user message,
    so this is a single-turn helper: any non-system message is treated as
    user/prompt text. It is intentionally not meant for multi-turn histories
    that include assistant turns (those would be folded into the prompt); the
    CLI backends are one-shot and cannot consume a multi-message conversation
    anyway.
    """
    system_parts: List[str] = []
    user_parts: List[str] = []
    for msg in messages or []:
        content = msg.get("content") or ""
        if not content:
            continue
        if msg.get("role") == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)
    return "\n\n".join(system_parts), "\n\n".join(user_parts)


def _augment_prompt_with_schema(
    prompt: str, json_schema: Optional[Dict[str, Any]]
) -> str:
    """Append a strict JSON-only instruction describing the expected schema.

    Ollama enforces the ``format`` schema natively; the API/CLI providers below
    instead steer the model via the prompt (the same approach the Gemini API
    provider relies on) so that ``extract_json_from_response`` can parse it.
    """
    if not json_schema:
        return prompt
    return (
        prompt + "\n\nIMPORTANT: Respond with ONLY a single valid JSON object that "
        "conforms to the following JSON Schema. Do not include any prose, "
        "explanations, comments, or Markdown code fences.\n\nJSON Schema:\n"
        + json.dumps(json_schema)
    )


def _resolve_cli_command(command: str) -> List[str]:
    """Resolve a CLI command name to an argv prefix runnable via subprocess.

    Handles the Windows case where npm-installed CLIs are ``.cmd``/``.bat``
    shims that ``CreateProcess`` cannot launch directly (they must go through
    ``cmd /c``).
    """
    resolved = shutil.which(command)
    if resolved is None:
        raise FileNotFoundError(
            f"Could not find the '{command}' CLI on PATH. Install it (and log in), "
            f"or point the matching *_CLI_COMMAND environment variable at its full path."
        )
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved]


def _cli_subprocess_env(
    strip_keys: Optional[Tuple[str, ...]],
) -> Optional[Dict[str, str]]:
    """Copy the current environment minus ``strip_keys`` (or None to inherit).

    Used to keep API-key env vars away from the CLI subprocesses so they
    authenticate with their own interactive (subscription) login.
    """
    if not strip_keys:
        return None
    return {k: v for k, v in os.environ.items() if k not in strip_keys}


def _run_cli(
    cmd: List[str],
    prompt: str,
    timeout: int,
    label: str,
    attempts: int = 2,
    env: Optional[Dict[str, str]] = None,
) -> str:
    """Run a CLI provider command, feeding ``prompt`` over stdin, return stdout.

    Retries a few times on failure since CLI backends are prone to transient
    "overloaded"/rate-limit errors.
    """
    last_detail = "no output"
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                env=env,
            )
        except FileNotFoundError as e:
            # Missing binary is not transient, so fail fast.
            raise RuntimeError(f"{label} CLI could not be executed: {e}") from e
        except subprocess.TimeoutExpired:
            last_detail = f"timed out after {timeout} seconds"
        else:
            if result.returncode == 0:
                return result.stdout or ""
            # `claude --output-format json` reports failures on stdout (a JSON
            # envelope with is_error/result), so surface both streams.
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            last_detail = (stderr or stdout or "no output")[:1500]

        if attempt < attempts:
            logger.warning(
                f"⚠️ {label} CLI attempt {attempt}/{attempts} failed: "
                f"{last_detail[:200]}; retrying..."
            )
            time.sleep(2 * attempt)

    raise RuntimeError(f"{label} CLI failed after {attempts} attempt(s): {last_detail}")


def _parse_claude_cli_output(stdout: str) -> str:
    """Extract the assistant text from `claude -p --output-format json` output.

    Falls back to the raw text if the output is not the expected JSON envelope.
    """
    text = stdout.strip()
    if not text:
        return text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text  # plain text output (e.g. --output-format text)
    if isinstance(data, dict):
        if data.get("is_error"):
            detail = data.get("result") or data.get("error") or data
            raise RuntimeError(f"Claude CLI reported an error: {detail}")
        result = data.get("result")
        if isinstance(result, str):
            return result
    return text


class AnthropicProvider:
    """Anthropic Claude HTTP API provider implementation."""

    def __init__(self, api_key: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request to the Anthropic Messages API."""
        system_text, user_text = _split_system_and_user(messages)
        user_text = _augment_prompt_with_schema(user_text, kwargs.get("format"))

        options = options or {}
        params: Dict[str, Any] = {
            "model": model,
            # max_tokens is required by the Anthropic API.
            "max_tokens": int(options.get("max_tokens", 8192)),
            "messages": [{"role": "user", "content": user_text}],
        }
        if system_text:
            params["system"] = system_text
        if "temperature" in options:
            params["temperature"] = options["temperature"]
        if "top_p" in options:
            params["top_p"] = options["top_p"]

        response = self.client.messages.create(**params)

        # Concatenate all text blocks from the response.
        content = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text"
        )

        # Convert to Ollama-like format for compatibility.
        return {"message": {"role": "assistant", "content": content}}


# A short, non-agentic system prompt used to REPLACE Claude Code's default
# coding-agent system prompt when driving it as a plain LLM. This avoids
# re-sending the large (~20k token) agent prompt on every call and stops the
# model from behaving like a coding agent (which can fail in headless mode).
_CLI_DEFAULT_SYSTEM_PROMPT = (
    "You are a precise data-extraction and evaluation engine. Follow the user's "
    "instructions exactly and respond with only what they ask for."
)

# API-key env vars that make the CLIs use external-API-key auth. The *_cli
# providers strip these so the CLI authenticates with its own interactive
# (subscription) login; otherwise a stray or placeholder key in the
# environment (e.g. copied from .env.example) causes 401 "Invalid API key".
_CLAUDE_CLI_AUTH_ENV_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
_GEMINI_CLI_AUTH_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY")


class ClaudeCLIProvider:
    """Claude Code CLI provider (invokes the local `claude` binary).

    Runs ``claude -p`` as a lean, non-agentic one-shot: it replaces the default
    coding-agent system prompt (``--system-prompt``) and disables all tools
    (``--tools ""``) so it behaves like a plain text-in/JSON-out model. By
    default it authenticates with your ``claude`` login and ignores any
    ``ANTHROPIC_API_KEY`` in the environment (set ``use_cli_auth=False`` to let
    the CLI pick up the API key instead).
    """

    def __init__(
        self,
        command: str = "claude",
        timeout: int = CLI_TIMEOUT,
        disable_tools: bool = True,
        system_prompt: str = _CLI_DEFAULT_SYSTEM_PROMPT,
        use_cli_auth: bool = True,
    ):
        self._argv = _resolve_cli_command(command)
        self.timeout = timeout
        self.disable_tools = disable_tools
        self.system_prompt = system_prompt
        self.use_cli_auth = use_cli_auth

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request through the Claude Code CLI in print mode."""
        system_text, user_text = _split_system_and_user(messages)
        user_text = _augment_prompt_with_schema(user_text, kwargs.get("format"))
        # Keep the (large, possibly special-charactered) task instructions on
        # stdin so nothing fragile ends up on the command line.
        prompt = f"{system_text}\n\n{user_text}" if system_text else user_text

        cmd = self._argv + ["-p", "--output-format", "json"]
        if self.system_prompt:
            cmd += ["--system-prompt", self.system_prompt]
        if self.disable_tools:
            cmd += ["--tools", ""]
        if model:
            cmd += ["--model", model]

        env = _cli_subprocess_env(
            _CLAUDE_CLI_AUTH_ENV_VARS if self.use_cli_auth else None
        )
        stdout = _run_cli(cmd, prompt, self.timeout, "Claude", env=env)
        content = _parse_claude_cli_output(stdout)
        return {"message": {"role": "assistant", "content": content}}


class GeminiCLIProvider:
    """Gemini CLI provider (invokes the local `gemini` binary).

    By default it authenticates with your ``gemini`` login and ignores any
    ``GEMINI_API_KEY`` in the environment (set ``use_cli_auth=False`` to let the
    CLI pick up the API key instead).
    """

    def __init__(
        self,
        command: str = "gemini",
        timeout: int = CLI_TIMEOUT,
        use_cli_auth: bool = True,
    ):
        self._argv = _resolve_cli_command(command)
        self.timeout = timeout
        self.use_cli_auth = use_cli_auth

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a chat request through the Gemini CLI in non-interactive mode."""
        system_text, user_text = _split_system_and_user(messages)
        user_text = _augment_prompt_with_schema(user_text, kwargs.get("format"))
        # The Gemini CLI has no dedicated system-prompt flag, so prepend it.
        prompt = f"{system_text}\n\n{user_text}" if system_text else user_text

        cmd = list(self._argv)
        if model:
            cmd += ["-m", model]

        env = _cli_subprocess_env(
            _GEMINI_CLI_AUTH_ENV_VARS if self.use_cli_auth else None
        )
        stdout = _run_cli(cmd, prompt, self.timeout, "Gemini", env=env)
        return {"message": {"role": "assistant", "content": stdout.strip()}}
