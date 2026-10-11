import json
import logging
from pathlib import Path
from typing import List, Optional, Type

import pymupdf
from pydantic import BaseModel, Field, create_model

from config import DEFAULT_MODEL, MODEL_PARAMETERS
from llm_utils import initialize_llm_provider, extract_json_from_response
from models import CategoryScore, Deductions
from prompts.template_manager import TemplateManager
from roles import Category, Role, ROLES_DIR

logger = logging.getLogger(__name__)

# the cover letter rubric is the same across roles, unlike the resume categories
# which each role defines for itself. two of these lean on the job description,
# two judge the letter on its own.
COVER_LETTER_CATEGORIES = [
    Category(key="job_alignment", label="Job Alignment", max=40, icon="🎯"),
    Category(key="motivation_fit", label="Motivation & Fit", max=20, icon="🔥"),
    Category(key="communication", label="Communication & Writing", max=20, icon="✍️"),
    Category(key="specificity", label="Specificity", max=20, icon="🔍"),
]
COVER_LETTER_BONUS_MAX = 10

# roles can drop these same-named files in their folder to override the shared
# defaults, same idea as criteria.jinja / system_message.jinja for the resume side.
_CRITERIA_FILE = "cover_letter_criteria.jinja"
_SYSTEM_FILE = "cover_letter_system_message.jinja"


def _load_source(role: Role, filename: str) -> str:
    path = ROLES_DIR / role.name / filename
    if not path.is_file():
        raise ValueError(
            f"Role '{role.name}' is missing {filename}. Cover letter scoring needs "
            f"it in roles/{role.name}/ — see the software_engineering_intern role "
            "for an example."
        )
    return path.read_text(encoding="utf-8")


def build_cover_letter_model() -> Type[BaseModel]:
    # mirrors build_evaluation_model in models.py but with the fixed cover
    # letter rubric, so printing and csv export can reuse the same shape.
    fields = {c.key: (CategoryScore, ...) for c in COVER_LETTER_CATEGORIES}
    scores_model = create_model("CoverLetterScores", **fields)

    bonus_model = create_model(
        "BonusPoints",
        total=(float, Field(ge=0, le=COVER_LETTER_BONUS_MAX)),
        breakdown=(str, Field(description="Breakdown of bonus points")),
    )

    return create_model(
        "CoverLetterEvaluation",
        scores=(scores_model, ...),
        bonus_points=(bonus_model, ...),
        deductions=(Deductions, ...),
        key_strengths=(List[str], Field(min_items=1, max_items=5)),
        areas_for_improvement=(List[str], Field(min_items=1, max_items=5)),
    )


def job_description_path_for(role: Role) -> Optional[Path]:
    # the description lives next to the role definition as plain text. optional on purpose.
    path = ROLES_DIR / role.name / "job_description.txt"
    return path if path.is_file() else None


class CoverLetterEvaluator:
    def __init__(self, role: Role, model_name: str = DEFAULT_MODEL, model_params=None):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.role = role
        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.evaluation_model = build_cover_letter_model()
        self.template_manager = TemplateManager()
        self.provider = initialize_llm_provider(model_name)

        self.criteria_source = _load_source(role, _CRITERIA_FILE)
        self.system_source = _load_source(role, _SYSTEM_FILE)

    def evaluate(
        self, cover_letter_text: str, job_description_text: Optional[str] = None
    ) -> BaseModel:
        system_message = self.template_manager.render_string(
            self.system_source, position_title=self.role.position_title
        )
        prompt = self.template_manager.render_string(
            self.criteria_source,
            position_title=self.role.position_title,
            job_description=job_description_text,
            cover_letter=cover_letter_text,
            bonus_max=COVER_LETTER_BONUS_MAX,
        )

        chat_params = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "options": {
                "stream": False,
                "temperature": self.model_params.get("temperature", 0.5),
                "top_p": self.model_params.get("top_p", 0.9),
            },
        }
        kwargs = {"format": self.evaluation_model.model_json_schema()}

        try:
            response = self.provider.chat(**chat_params, **kwargs)
            response_text = extract_json_from_response(response["message"]["content"])
            evaluation_dict = json.loads(response_text)
            return self.evaluation_model(**evaluation_dict)
        except Exception as e:
            logger.error(f"Error evaluating cover letter: {e}")
            raise


def _pdf_to_text(pdf_path: str) -> str:
    # extract text from cover letter pdf
    try:
        with pymupdf.open(pdf_path) as doc:
            return "\n".join(page.get_text() for page in doc).strip()
    except Exception as e:
        logger.error(f"Failed to read {pdf_path}: {e}")
        return ""


def evaluate_cover_letter(cover_letter_pdf: str, role: Role) -> Optional[BaseModel]:
    cover_letter_text = _pdf_to_text(cover_letter_pdf)
    if not cover_letter_text:
        logger.error(
            f"Could not extract any text from {cover_letter_pdf} — "
            "is it a scanned/image-only PDF?"
        )
        return None

    jd_path = job_description_path_for(role)
    job_description_text = None
    if jd_path:
        job_description_text = jd_path.read_text(encoding="utf-8").strip()
        if not job_description_text:
            logger.warning(f"Found {jd_path} but it's empty.")
            job_description_text = None
    else:
        logger.info(
            f"No job_description.txt in roles/{role.name}/ — "
            "scoring the letter on its own."
        )

    evaluator = CoverLetterEvaluator(role)
    return evaluator.evaluate(cover_letter_text, job_description_text)


def print_cover_letter_results(evaluation, candidate_name: str = "Candidate"):
    print("\n" + "=" * 80)
    print(f"✉️  COVER LETTER EVALUATION FOR: {candidate_name}")
    print("=" * 80)

    if not evaluation:
        print("❌ No evaluation data available")
        return

    total_score = 0
    max_score = 0
    for category in COVER_LETTER_CATEGORIES:
        cat = getattr(evaluation.scores, category.key, None)
        if not cat:
            continue
        capped = min(cat.score, category.max)
        total_score += capped
        max_score += category.max

    if evaluation.bonus_points:
        total_score += evaluation.bonus_points.total
    if evaluation.deductions:
        total_score -= evaluation.deductions.total

    print(f"\n🎯 OVERALL SCORE: {total_score:.1f}/{max_score}")

    print("\n📈 DETAILED SCORES:")
    print("-" * 60)
    for category in COVER_LETTER_CATEGORIES:
        cat = getattr(evaluation.scores, category.key, None)
        if not cat:
            continue
        capped = min(cat.score, category.max)
        print(f"{category.icon} {category.label}: {capped}/{cat.max}")
        print(f"   Evidence: {cat.evidence}")
        print()

    if evaluation.bonus_points:
        print(f"\n⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    if evaluation.deductions and evaluation.deductions.total > 0:
        print(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        print(f"   {evaluation.deductions.reasons}")

    if evaluation.key_strengths:
        print("\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, s in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {s}")

    if evaluation.areas_for_improvement:
        print("\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, a in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {a}")

    print("\n" + "=" * 80)