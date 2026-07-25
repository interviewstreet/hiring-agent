"""Discover and fetch technical blog metadata for evaluation enrichment."""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests

from llm_utils import extract_json_from_response, initialize_llm_provider
from models import JSONResume
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from prompts.template_manager import TemplateManager

logger = logging.getLogger(__name__)

BLOG_NETWORKS = {
    "medium",
    "dev.to",
    "devto",
    "hashnode",
    "substack",
    "wordpress",
    "blog",
    "personal website",
}
BLOG_DOMAINS = {
    "medium.com",
    "dev.to",
    "hashnode.dev",
    "substack.com",
    "wordpress.com",
    "blogspot.com",
}
REQUEST_TIMEOUT = 8
MAX_BLOGS = 5


def _is_blog_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if any(domain in host for domain in BLOG_DOMAINS):
        return True
    path = (parsed.path or "").lower()
    return "/blog" in path or host.startswith("blog.")


def discover_blog_urls(resume_data: JSONResume, github_data: Optional[dict] = None) -> List[str]:
    urls: Set[str] = set()

    if resume_data.basics:
        if resume_data.basics.url and _is_blog_url(resume_data.basics.url):
            urls.add(resume_data.basics.url)
        for profile in resume_data.basics.profiles or []:
            network = (profile.network or "").lower()
            if network in BLOG_NETWORKS or _is_blog_url(profile.url):
                urls.add(profile.url)

    if github_data:
        profile = github_data.get("profile", {})
        blog_url = profile.get("blog")
        if blog_url and _is_blog_url(blog_url):
            urls.add(blog_url)

    return list(urls)[:MAX_BLOGS]


def _fetch_page_metadata(url: str) -> dict:
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "hiring-agent/1.0"},
        )
        response.raise_for_status()
        html = response.text
    except Exception as exc:
        logger.debug("Blog fetch failed for %s: %s", url, exc)
        return {"url": url, "score": 0.0, "details": f"Fetch failed: {exc}"}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "Unknown"
    word_count = len(re.findall(r"\w+", html))
    details = f"Title: {title[:120]}; approx page words: {word_count}"
    score = min(10.0, 3.0 + (word_count / 1000))

    return {"url": url, "score": round(score, 1), "details": details}


def _llm_score_blogs(blogs: List[dict]) -> List[dict]:
    template_manager = TemplateManager()
    summary = json.dumps(blogs, indent=2)
    prompt = template_manager.render_template("blog_scoring", blog_summary=summary)
    if not prompt:
        return blogs

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
    )
    content = extract_json_from_response(response["message"]["content"])
    payload = json.loads(content)
    scored = payload.get("blogs", blogs)
    return scored[:MAX_BLOGS]


def fetch_blog_metadata(
    urls: List[str], use_llm_scoring: bool = False
) -> dict:
    if not urls:
        return {}

    blogs = [_fetch_page_metadata(url) for url in urls[:MAX_BLOGS]]
    if use_llm_scoring:
        try:
            blogs = _llm_score_blogs(blogs)
        except Exception as exc:
            logger.warning("Blog LLM scoring failed: %s", exc)

    scores = [blog.get("score", 0.0) for blog in blogs if isinstance(blog.get("score"), (int, float))]
    blog_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    return {
        "total_blogs": len(blogs),
        "blog_score": blog_score,
        "blog_details": f"Found {len(blogs)} blog URL(s); average metadata score {blog_score}/10",
        "blogs": blogs,
    }
