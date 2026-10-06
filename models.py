from typing import (
    List,
    Optional,
    Dict,
    Tuple,
    Any,
    Type,
    Literal,
    Protocol,
    runtime_checkable,
)
from pydantic import (
    BaseModel,
    Field,
    create_model,
    field_validator,
    ConfigDict,
    computed_field,
    model_validator,
)


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


class RewrittenBasics(BaseModel):
    """Editable fields for the resume summary rewrite.

    The LLM is only allowed to touch ``summary``; all other basics fields
    (name, email, phone, url, location, profiles) are protected and never
    exposed in the output schema.
    """

    summary: Optional[str] = None


class RewrittenWork(BaseModel):
    """Editable fields for one work entry rewrite.

    ``id`` is the position of the entry in the original work list (copied
    unchanged by the LLM). The rewriter uses it to map rewrites back to the
    correct entry, so a reordered LLM response can never misattribute content.
    """

    id: Optional[int] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None


class RewrittenWorkList(BaseModel):
    """Batch of rewritten work entries, position-keyed to the original list.

    Keeping the array ordered and same-length (with ids echoed back) lets the
    rewriter merge edits into the original resume without dropping, reordering,
    or misattributing entries.
    """

    work: Optional[List[RewrittenWork]] = None


class RewrittenProject(BaseModel):
    """Editable fields for one project rewrite.

    ``id`` is the position of the project in the original projects list (copied
    unchanged by the LLM); the rewriter maps rewrites back by id.
    """

    id: Optional[int] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None


class RewrittenProjectList(BaseModel):
    """Batch of rewritten project entries, position-keyed to the original list."""

    projects: Optional[List[RewrittenProject]] = None


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


def _points_for_rank(rank, tiers) -> int:
    """Return the points for a qualifying rank, or zero."""
    for tier in tiers:
        if rank is not None and tier["min_rank"] <= rank <= tier["max_rank"]:
            return tier["points"]
    return 0


class BonusItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: int = Field(ge=0)
    evidence: str = Field(min_length=1)


class RankedBonusItem(BonusItem):
    rank: Optional[int] = Field(..., ge=1)


def _allowed_bonus_points(rule) -> tuple[int, ...]:
    """Return every point value allowed by a bonus rule, including zero."""
    configured = (
        (tier["points"] for tier in rule["tiers"])
        if "tiers" in rule
        else rule["points"]
    )
    return tuple(sorted({0, *configured}))


def _build_bonus_item_model(rule) -> Type[BaseModel]:
    """Build an item whose JSON schema lists the rule's allowed points."""
    allowed_points = _allowed_bonus_points(rule)
    points_type = Literal[allowed_points]
    base = RankedBonusItem if "tiers" in rule else BonusItem
    name = "".join(part.title() for part in rule["key"].split("_"))

    return create_model(
        f"{name}BonusItem",
        __base__=base,
        points=(
            points_type,
            Field(description=f"Allowed values: {', '.join(map(str, allowed_points))}"),
        ),
    )


def _validate_bonus(rule, item) -> None:
    """Validate one item against its configured points or rank tiers."""
    if "tiers" in rule:
        expected = _points_for_rank(item.rank, rule["tiers"])
        if item.points != expected:
            raise ValueError(
                f"{rule['label']}: rank {item.rank} requires {expected} points"
            )
        return

    allowed = set(_allowed_bonus_points(rule))
    if item.points not in allowed:
        raise ValueError(f"{rule['label']}: points must be one of {sorted(allowed)}")


def _format_bonus(rule, item) -> str:
    """Format one item for the human-readable breakdown."""
    details = item.evidence
    if "tiers" in rule:
        rank = "no stated rank" if item.rank is None else f"rank {item.rank}"
        outcome = "awarded once" if item.points else "no qualifying bonus"
        details = f"{rank}; {outcome}; {details}"
    return f"{rule['label']}: +{item.points} points; {details}"


def build_bonus_model(role) -> Type[BaseModel]:
    """Assemble the role's bonus entries and expose their total and breakdown."""
    if not role.bonus_rules:
        return create_model(
            "BonusPoints",
            total=(
                float,
                Field(ge=0, le=role.bonus_max, description="Total bonus points"),
            ),
            breakdown=(str, Field(description="Breakdown of bonus points")),
        )

    fields = {}
    for rule in role.bonus_rules:
        fields[rule["key"]] = (
            _build_bonus_item_model(rule),
            Field(description=rule["description"]),
        )
    BonusItems = create_model(
        "BonusItems", __config__=ConfigDict(extra="forbid"), **fields
    )

    class BonusPoints(BaseModel):
        model_config = ConfigDict(extra="forbid")
        items: BonusItems

        @model_validator(mode="after")
        def validate_items(self):
            for rule in role.bonus_rules:
                _validate_bonus(rule, getattr(self.items, rule["key"]))
            return self

        @computed_field
        @property
        def total(self) -> int:
            subtotal = sum(
                getattr(self.items, rule["key"]).points for rule in role.bonus_rules
            )
            return min(subtotal, role.bonus_max)

        @computed_field
        @property
        def breakdown(self) -> str:
            items = [
                (rule, getattr(self.items, rule["key"])) for rule in role.bonus_rules
            ]
            lines = [_format_bonus(rule, item) for rule, item in items]
            subtotal = sum(item.points for _, item in items)

            total = min(subtotal, role.bonus_max)
            lines.append(
                f"Subtotal: {subtotal}; total after {role.bonus_max}-point cap: {total}."
            )
            return "\n".join(lines)

    return BonusPoints


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

    bonus_model = build_bonus_model(role)

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
        for parameter in ("temperature", "top_p", "reasoning_effort"):
            if parameter in options:
                body[parameter] = options[parameter]

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

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                try:
                    detail = response.json()
                except ValueError:
                    detail = response.text
                raise requests.HTTPError(
                    f"{exc}. Response: {detail}",
                    request=response.request,
                    response=response,
                ) from exc
            data = response.json()
            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise ValueError(f"Unexpected response shape from {url}: {data}")
            return {"message": {"role": "assistant", "content": content}}
