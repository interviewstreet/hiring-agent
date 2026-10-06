"""Rewrites an extracted resume's prose into stronger, rubric-aligned content.

``ResumeRewriter`` consumes the already-parsed and validated ``JSONResume``
(nothing is re-read from the raw PDF) and rewrites only the editable prose
fields: the basics ``summary``, work ``summary``/``highlights`` and project
``description``/``highlights``.

Fact preservation is enforced in Python, not by the prompt: the LLM is given
narrow output schemas that only expose editable fields, and ``_merge`` rebuilds
the resume from the original data, applying only whitelisted edits (keyed by the
id each entry echoes back, so a reordered LLM response can never misattribute
content). Protected fields (name, contact, dates, URLs, education, skills
lists, ...) therefore cannot drift by construction.
"""

import json
import logging

from models import (
    JSONResume,
    RewrittenBasics,
    RewrittenProjectList,
    RewrittenWorkList,
)
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from prompts.template_manager import TemplateManager
from llm_utils import extract_json_from_response, initialize_llm_provider

logger = logging.getLogger(__name__)

# Rewrites are a pure prose task; pin low temperature for determinism regardless
# of the model's default params (pdf.py already uses 0.1 for extraction).
REWRITE_TEMPERATURE = 0.1
REWRITE_TOP_P = 0.9

# Editable fields per section. Everything else in the resume is protected and is
# never overwritten by _merge.
_EDITABLE_FIELDS = {
    "basics": ("summary",),
    "work": ("summary", "highlights"),
    "projects": ("description", "highlights"),
}


class ResumeRewriter:
    """Rewrite editable prose sections of a ``JSONResume`` for a given role."""

    def __init__(
        self,
        role,
        model_name: str = DEFAULT_MODEL,
        model_params: dict = None,
    ):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.role = role
        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(model_name, {})
        self.template_manager = TemplateManager()
        self.provider = initialize_llm_provider(model_name)

    def rewrite(self, resume_data: JSONResume, evaluation=None) -> JSONResume:
        """Return a new ``JSONResume`` with prose sections rewritten in place.

        A failed rewrite of any section falls back to the original content for
        that section; this never produces a partial or corrupt resume. Sections
        that are missing or empty are skipped without an LLM call.
        """
        if not resume_data:
            raise ValueError("No resume data to rewrite")

        rewrites = {}
        basics = resume_data.basics
        if basics is not None and basics.summary:
            rewrites["basics"] = self._rewrite_summary(basics.summary, evaluation)
        if resume_data.work:
            rewrites["work"] = self._rewrite_work(resume_data.work, evaluation)
        if resume_data.projects:
            rewrites["projects"] = self._rewrite_projects(
                resume_data.projects, evaluation
            )

        return self._merge(resume_data, rewrites)

    def _rewrite_summary(self, summary: str, evaluation):
        payload = {"summary": summary}
        prompt = self._render_section_prompt("summary", payload, evaluation)
        result = self._call_llm("summary", RewrittenBasics, prompt)
        if result is None or not result.summary:
            return None
        return result.summary

    def _rewrite_work(self, work, evaluation):
        payload = [
            {
                "id": index,
                "position": entry.position,
                "name": entry.name,
                "summary": entry.summary,
                "highlights": entry.highlights or [],
            }
            for index, entry in enumerate(work)
        ]
        prompt = self._render_section_prompt("work", payload, evaluation)
        result = self._call_llm("work", RewrittenWorkList, prompt)
        if result is None or not result.work:
            return None
        return [(entry.id, entry.summary, entry.highlights) for entry in result.work]

    def _rewrite_projects(self, projects, evaluation):
        payload = [
            {
                "id": index,
                "name": project.name,
                "description": project.description,
                "highlights": project.highlights or [],
                "technologies": project.technologies or [],
            }
            for index, project in enumerate(projects)
        ]
        prompt = self._render_section_prompt("projects", payload, evaluation)
        result = self._call_llm("projects", RewrittenProjectList, prompt)
        if result is None or not result.projects:
            return None
        return [
            (entry.id, entry.description, entry.highlights) for entry in result.projects
        ]

    def _render_section_prompt(self, section_name: str, payload, evaluation) -> str:
        return self.template_manager.render_template_by_name(
            "resume_rewrite",
            section_name=section_name,
            section_data=json.dumps(payload, indent=2, ensure_ascii=False),
            role_title=self.role.position_title,
            rubric_guidance=self._rubric_guidance(),
            evaluation_feedback=self._evaluation_feedback(evaluation),
        )

    def _rubric_guidance(self) -> str:
        if not self.role.categories:
            return "No rubric categories defined."
        return "; ".join(
            f"{category.label} (max {category.max})"
            for category in self.role.categories
        )

    def _evaluation_feedback(self, evaluation) -> str:
        if evaluation is None:
            return "No evaluation feedback provided."
        parts = []
        if getattr(evaluation, "areas_for_improvement", None):
            parts.append(
                "Areas for improvement: " + "; ".join(evaluation.areas_for_improvement)
            )
        if getattr(evaluation, "deductions", None) and getattr(
            evaluation.deductions, "reasons", ""
        ):
            parts.append("Deductions: " + evaluation.deductions.reasons)
        return "\n".join(parts) if parts else "No evaluation feedback provided."

    def _call_llm(self, section_name: str, return_model, prompt: str):
        """Call the LLM with a narrow output schema; return None on any failure."""
        try:
            system_message = self.template_manager.render_template(
                "rewrite_system_message"
            )
            chat_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": REWRITE_TEMPERATURE,
                    "top_p": REWRITE_TOP_P,
                },
            }
            kwargs = {"format": return_model.model_json_schema()}
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = extract_json_from_response(response["message"]["content"])
            json_start = response_text.find("{")
            json_end = response_text.rfind("}")
            if json_start != -1 and json_end != -1:
                response_text = response_text[json_start : json_end + 1]
            return return_model(**json.loads(response_text))
        except Exception as e:
            logger.warning(f"⚠️ Rewrite failed for '{section_name}': {e}")
            return None

    def _merge(self, original: JSONResume, rewrites: dict) -> JSONResume:
        """Rebuild the resume from the original, applying only editable edits.

        The merged dict is seeded from the original, so protected fields are
        preserved by construction even if a rewrite payload contains them.

        Work and project rewrites are keyed by the ``id`` each entry echoed from
        the payload. This guards against the LLM reordering entries: content can
        never be attributed to the wrong company/project. Entries whose id is
        missing, out of range, or duplicated fall back to the original content.
        """
        merged = original.model_dump()

        basics = rewrites.get("basics")
        if basics is not None and merged.get("basics") is not None:
            merged["basics"]["summary"] = basics

        work = rewrites.get("work")
        if work is not None and merged.get("work"):
            applied_ids = set()
            for entry_id, summary, highlights in work:
                if entry_id is None or entry_id in applied_ids:
                    continue
                if not (0 <= entry_id < len(merged["work"])):
                    continue
                target = merged["work"][entry_id]
                if summary:
                    target["summary"] = summary
                if highlights:
                    target["highlights"] = highlights
                applied_ids.add(entry_id)

        projects = rewrites.get("projects")
        if projects is not None and merged.get("projects"):
            applied_ids = set()
            for entry_id, description, highlights in projects:
                if entry_id is None or entry_id in applied_ids:
                    continue
                if not (0 <= entry_id < len(merged["projects"])):
                    continue
                target = merged["projects"][entry_id]
                if description:
                    target["description"] = description
                if highlights:
                    target["highlights"] = highlights
                applied_ids.add(entry_id)

        return JSONResume(**merged)
