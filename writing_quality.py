"""Spelling and optional LLM writing-quality review."""

from __future__ import annotations

import json
import logging
import re
from typing import List, Set

from llm_utils import extract_json_from_response, initialize_llm_provider
from models import JSONResume, SpellingIssue, WritingQualityLLMResponse, WritingQualityReport
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from prompts.template_manager import TemplateManager

logger = logging.getLogger(__name__)

STATIC_ALLOWLIST = {
    "langgraph",
    "grpc",
    "kubernetes",
    "fastapi",
    "opentelemetry",
    "hackerrank",
    "github",
    "gitlab",
    "devops",
    "nodejs",
    "postgresql",
    "mongodb",
    "redis",
    "tensorflow",
    "pytorch",
    "javascript",
    "typescript",
    "golang",
    "graphql",
    "websocket",
    "microservices",
    "api",
    "apis",
    "sdk",
    "ci",
    "cd",
    "nlp",
    "ml",
    "ai",
    "llm",
    "llms",
    "json",
    "yaml",
    "csv",
    "sql",
    "nosql",
    "aws",
    "gcp",
    "azure",
    "docker",
    "kafka",
    "nginx",
    "oauth",
    "jwt",
    "restful",
    "backend",
    "frontend",
    "fullstack",
    "devto",
    "hashnode",
    "substack",
}

MAX_SPELLING_ISSUES = 20
MAX_LLM_INPUT_CHARS = 12000


def _build_allowlist(resume_data: JSONResume) -> Set[str]:
    allowlist = set(STATIC_ALLOWLIST)

    if resume_data.skills:
        for skill_group in resume_data.skills:
            if skill_group.keywords:
                allowlist.update(word.lower() for word in skill_group.keywords)

    if resume_data.work:
        for job in resume_data.work:
            if job.name:
                allowlist.update(re.findall(r"[a-zA-Z]{3,}", job.name.lower()))
            if job.position:
                allowlist.update(re.findall(r"[a-zA-Z]{3,}", job.position.lower()))

    if resume_data.projects:
        for project in resume_data.projects:
            if project.name:
                allowlist.update(re.findall(r"[a-zA-Z]{3,}", project.name.lower()))

    if resume_data.basics and resume_data.basics.name:
        for part in resume_data.basics.name.split():
            allowlist.add(part.lower())

    return allowlist


def _tokenize_lines(text: str) -> List[str]:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", line)
        cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", cleaned)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"[\*`#>|]", " ", cleaned)
        cleaned = cleaned.strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def check_spelling(text: str, resume_data: JSONResume) -> List[SpellingIssue]:
    try:
        from spellchecker import SpellChecker
    except ImportError:
        logger.warning("pyspellchecker not installed; skipping spell check")
        return []

    allowlist = _build_allowlist(resume_data)
    spell = SpellChecker()
    issues: List[SpellingIssue] = []

    for line in _tokenize_lines(text):
        words = re.findall(r"[A-Za-z]{3,}", line)
        for word in words:
            lower = word.lower()
            if lower in allowlist or word.isupper():
                continue
            if lower in spell:
                continue
            correction = spell.correction(lower)
            if correction and correction != lower:
                issues.append(
                    SpellingIssue(
                        word=word,
                        suggestion=correction,
                        context=line[:120],
                    )
                )
            if len(issues) >= MAX_SPELLING_ISSUES:
                return issues

    return issues


def _llm_writing_review(text: str) -> WritingQualityLLMResponse:
    template_manager = TemplateManager()
    prompt = template_manager.render_template(
        "writing_quality", text_content=text[:MAX_LLM_INPUT_CHARS]
    )
    if not prompt:
        return WritingQualityLLMResponse()

    provider = initialize_llm_provider(DEFAULT_MODEL)
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9})
    response = provider.chat(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "stream": False,
            "temperature": model_params.get("temperature", 0.1),
            "top_p": model_params.get("top_p", 0.9),
        },
        format=WritingQualityLLMResponse.model_json_schema(),
    )
    content = extract_json_from_response(response["message"]["content"])
    return WritingQualityLLMResponse(**json.loads(content))


def analyze_writing_quality(
    text: str, resume_data: JSONResume, use_llm: bool = False
) -> WritingQualityReport:
    spelling_issues = check_spelling(text, resume_data)
    grammar_issues: List[str] = []
    clarity_suggestions: List[str] = []

    if use_llm and text.strip():
        try:
            llm_result = _llm_writing_review(text)
            grammar_issues = llm_result.grammar_issues
            clarity_suggestions = llm_result.clarity_suggestions
        except Exception as exc:
            logger.warning("Writing quality LLM review failed: %s", exc)

    return WritingQualityReport(
        spelling_issues=spelling_issues,
        grammar_issues=grammar_issues,
        clarity_suggestions=clarity_suggestions,
    )
