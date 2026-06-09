import os
import sys
import json
import time
import logging
import re
import pymupdf

from models import (
    JSONResume,
    Basics,
    Work,
    Education,
    Skill,
    Project,
    Award,
    Language,
    BasicsSection,
    WorkSection,
    EducationSection,
    SkillsSection,
    ProjectsSection,
    AwardsSection,
    LanguagesSection,
)
from llm_utils import (
    initialize_llm_provider,
    extract_json_from_response,
    ensure_valid_json,
)
from pymupdf_rag import to_markdown
from typing import List, Optional, Dict, Any
from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)
from prompts.template_manager import TemplateManager
from transform import transform_parsed_data

logger = logging.getLogger(__name__)


class PDFHandler:

    def __init__(self, max_workers: int = 3):
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()
        # Limit the concurrency for section extraction to reduce rate limits
        try:
            self.max_workers = int(max_workers) if max_workers and max_workers > 0 else 3
        except Exception:
            self.max_workers = 3

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(DEFAULT_MODEL)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            with pymupdf.open(pdf_path) as doc:
                pages = range(doc.page_count)
                resume_text = to_markdown(
                    doc,
                    pages=pages,
                )
                logger.debug(
                    f"Extracted text from PDF: {len(resume_text) if resume_text else 0} characters"
                )
                return resume_text
        except Exception as e:
            logger.error(f"An error occurred while reading the PDF: {e}")
            return None

    def _call_llm_for_section(
        self, section_name: str, text_content: str, prompt: str, return_model=None
    ) -> Optional[Dict]:
        try:
            start_time = time.time()
            logger.debug(
                f"🔄 Extracting {section_name} section using {DEFAULT_MODEL}..."
            )

            model_params = MODEL_PARAMETERS.get(
                DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9}
            )

            section_system_message = self.template_manager.render_template(
                "system_message", section_name_param=section_name
            )
            if not section_system_message:
                logger.error(
                    f"❌ Failed to render system message template for {section_name}"
                )
                return None

            chat_params = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": section_system_message},
                    {"role": "user", "content": prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": model_params["temperature"],
                    "top_p": model_params["top_p"],
                },
            }

            kwargs = {}
            if return_model:
                kwargs["format"] = return_model.model_json_schema()

            # Retry logic for rate limits / transient failures
            max_attempts = 3
            attempt = 0
            response_text = None
            while attempt < max_attempts and response_text is None:
                attempt += 1
                try:
                    response = self.provider.chat(**chat_params, **kwargs)
                    response_text = response["message"]["content"]
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "quota" in err_msg.lower():
                        # Parse suggested retry delay if present
                        retry_delay = 8
                        m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", err_msg)
                        if m:
                            try:
                                retry_delay = min(float(m.group(1)) + 1, 30)
                            except Exception:
                                pass
                        logger.warning(
                            f"⚠️ Rate limit for {section_name} (attempt {attempt}/{max_attempts}). Sleeping {retry_delay:.1f}s before retry."
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            f"❌ Non-retryable error extracting {section_name}: {e}"
                        )
                        return None

            if response_text is None:
                logger.error(
                    f"❌ Exhausted retries for {section_name} due to rate limits."
                )
                return None

            cleaned = extract_json_from_response(response_text)
            repaired = ensure_valid_json(
                cleaned,
                provider=self.provider,
                model=DEFAULT_MODEL,
                original_prompt=prompt,
            )

            try:
                parsed_data = json.loads(repaired)
                logger.debug(f"✅ Successfully extracted {section_name} section")
            except json.JSONDecodeError as e:
                logger.error(
                    f"❌ Error parsing JSON for {section_name} section after repair attempts: {e}"
                )
                logger.error(f"Raw repaired text: {repaired}")
                return None

            transformed_data = transform_parsed_data(parsed_data)
            end_time = time.time()
            total_time = end_time - start_time
            logger.debug(
                f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
            )

            return transformed_data

        except Exception as e:
            logger.error(f"❌ Error calling LLM for {section_name} section: {e}")
            return None

    def extract_basics_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "basics", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render basics template")
            return None
        return self._call_llm_for_section("basics", resume_text, prompt, BasicsSection)

    def extract_work_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template("work", text_content=resume_text)
        if not prompt:
            logger.error("❌ Failed to render work template")
            return None
        return self._call_llm_for_section("work", resume_text, prompt, WorkSection)

    def extract_education_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "education", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render education template")
            return None
        return self._call_llm_for_section(
            "education", resume_text, prompt, EducationSection
        )

    def extract_skills_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "skills", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render skills template")
            return None
        return self._call_llm_for_section("skills", resume_text, prompt, SkillsSection)

    def extract_projects_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "projects", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render projects template")
            return None
        return self._call_llm_for_section(
            "projects", resume_text, prompt, ProjectsSection
        )

    def extract_awards_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "awards", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render awards template")
            return None
        return self._call_llm_for_section("awards", resume_text, prompt, AwardsSection)

    def extract_languages_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "languages", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render languages template")
            return None
        return self._call_llm_for_section("languages", resume_text, prompt, LanguagesSection)

    def extract_json_from_text(self, resume_text: str) -> Optional[JSONResume]:
        try:
            return self._extract_all_sections_separately(resume_text)
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None

    def extract_json_from_pdf(self, pdf_path: str) -> Optional[JSONResume]:
        try:
            logger.debug(f"📄 Extracting text from PDF: {pdf_path}")
            text_content = self.extract_text_from_pdf(pdf_path)

            if not text_content:
                logger.error("❌ Failed to extract text from PDF")
                return None

            logger.debug(
                f"✅ Successfully extracted {len(text_content)} characters from PDF"
            )

            logger.debug("🔄 Extracting all sections separately...")
            return self._extract_all_sections_separately(text_content)

        except Exception as e:
            logger.error(f"❌ Error during PDF to JSON extraction: {e}")
            return None

    def _extract_section_data(
        self, text_content: str, section_name: str, return_model=None
    ) -> Optional[Dict]:
        section_extractors = {
            "basics": self.extract_basics_section,
            "work": self.extract_work_section,
            "education": self.extract_education_section,
            "skills": self.extract_skills_section,
            "projects": self.extract_projects_section,
            "awards": self.extract_awards_section,
            "languages": self.extract_languages_section,
        }

        if section_name not in section_extractors:
            logger.error(f"❌ Invalid section name: {section_name}")
            logger.error(f"Valid sections: {list(section_extractors.keys())}")
            return None

        return section_extractors[section_name](text_content)

    def _extract_single_section(
        self, text_content: str, section_name: str, return_model=None
    ) -> Optional[Dict]:
        section_data = self._extract_section_data(
            text_content, section_name, return_model
        )
        if section_data:
            complete_resume = {
                "basics": None,
                "work": None,
                "volunteer": None,
                "education": None,
                "awards": None,
                "certificates": None,
                "publications": None,
                "skills": None,
                "languages": None,
                "interests": None,
                "references": None,
                "projects": None,
                "meta": None,
            }

            complete_resume.update(section_data)
            return complete_resume

        return None

    def _extract_all_sections_separately(
        self, text_content: str
    ) -> Optional[JSONResume]:
        start_time = time.time()

        sections = ["basics", "work", "education", "skills", "projects", "awards", "languages"]

        complete_resume = {
            "basics": None,
            "work": None,
            "volunteer": None,
            "education": None,
            "awards": None,
            "certificates": None,
            "publications": None,
            "skills": None,
            "languages": None,
            "interests": None,
            "references": None,
            "projects": None,
            "meta": None,
        }

        # Parallel extraction using threads (I/O bound network calls)
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}
        # Constrain parallelism to reduce rate limit pressure
        parallel_workers = self.max_workers
        with ThreadPoolExecutor(max_workers=min(len(sections), parallel_workers)) as executor:
            future_map = {
                executor.submit(self._extract_section_data, text_content, section_name): section_name
                for section_name in sections
            }
            for future in as_completed(future_map):
                sec = future_map[future]
                try:
                    section_data = future.result()
                    if section_data:
                        results[sec] = section_data
                        complete_resume.update(section_data)
                        logger.debug(f"✅ Successfully extracted {sec} section (parallel)")
                    else:
                        logger.error(f"⚠️ Failed to extract {sec} section")
                except Exception as e:
                    logger.error(f"❌ Exception extracting {sec} section: {e}")

        # Fallback: if all sections failed in parallel, retry sequentially with small delay
        if not results:
            logger.warning("⚠️ Parallel extraction returned no sections. Retrying sequentially to mitigate rate limits.")
            for sec in sections:
                try:
                    section_data = self._extract_section_data(text_content, sec, None)
                    if section_data:
                        complete_resume.update(section_data)
                        results[sec] = section_data
                        logger.debug(f"✅ Sequentially extracted {sec} section")
                    else:
                        logger.error(f"⚠️ Sequential retry failed for {sec} section")
                    time.sleep(2)  # gentle pacing to avoid hitting per-minute limits
                except Exception as e:
                    logger.error(f"❌ Exception in sequential retry for {sec}: {e}")
        else:
            # Targeted retries for only the missing sections (avoid flooding API)
            missing = [s for s in sections if complete_resume.get(s) is None]
            if missing:
                logger.warning(f"⚠️ Missing sections after parallel run: {missing}. Retrying them sequentially with pacing.")
                for sec in missing:
                    try:
                        section_data = self._extract_section_data(text_content, sec, None)
                        if section_data:
                            complete_resume.update(section_data)
                            results[sec] = section_data
                            logger.debug(f"✅ Filled missing {sec} section via sequential retry")
                        else:
                            logger.error(f"⚠️ Sequential retry could not extract {sec} section")
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"❌ Exception retrying missing {sec} section: {e}")

        # Fallback heuristics for skills & projects if still None
        def _simple_skill_extraction(text: str):
            tech_keywords = [
                "python",
                "java",
                "javascript",
                "typescript",
                "react",
                "node",
                "django",
                "flask",
                "aws",
                "docker",
                "kubernetes",
                "postgres",
                "mysql",
                "mongodb",
                "git",
                "linux",
                "tensorflow",
                "pytorch",
                "llm",
            ]
            found = set()
            lower = text.lower()
            for kw in tech_keywords:
                if kw in lower:
                    found.add(kw)
            if not found:
                return None
            return {
                "skills": [
                    {"name": "Technologies", "level": None, "keywords": sorted(list(found))}
                ]
            }

        def _simple_projects_extraction(text: str):
            # Use work highlights as proxy if present
            projects = []
            if complete_resume.get("work") and isinstance(complete_resume["work"], list):
                for w in complete_resume["work"]:
                    highlights = w.get("highlights") if isinstance(w, dict) else None
                    if highlights:
                        for h in highlights:
                            if any(word in h.lower() for word in ["developed", "built", "engineered", "implemented", "created"]):
                                projects.append({
                                    "name": h[:60] + ("..." if len(h) > 60 else ""),
                                    "description": h,
                                    "highlights": [h],
                                })
            if not projects:
                return None
            return {"projects": projects}

        if complete_resume.get("skills") is None:
            fallback_skills = _simple_skill_extraction(text_content)
            if fallback_skills:
                complete_resume.update(fallback_skills)
                logger.warning("⚠️ Applied heuristic fallback for skills section.")
        if complete_resume.get("projects") is None:
            fallback_projects = _simple_projects_extraction(text_content)
            if fallback_projects:
                complete_resume.update(fallback_projects)
                logger.warning("⚠️ Applied heuristic fallback for projects section from work highlights.")

        # Heuristic fallback for spoken languages if missing
        def _simple_languages_extraction(text: str):
            try:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                langs = []
                for line in lines:
                    if line.lower().startswith("languages:") or line.lower().startswith("language:"):
                        content = line.split(":", 1)[1].strip()
                        parts = [p.strip() for p in re.split(r",|;", content) if p.strip()]
                        for p in parts:
                            # Match formats like "English (Professional)" or just "English"
                            m = re.match(r"^(.*?)\s*\((.*?)\)$", p)
                            if m:
                                langs.append({"language": m.group(1).strip(), "fluency": m.group(2).strip()})
                            else:
                                langs.append({"language": p, "fluency": None})
                        break
                if langs:
                    return {"languages": langs}
            except Exception:
                return None
            return None

        if complete_resume.get("languages") in (None, []):
            fallback_langs = _simple_languages_extraction(text_content)
            if fallback_langs:
                complete_resume.update(fallback_langs)
                logger.warning("⚠️ Applied heuristic fallback for languages section.")

        try:
            if complete_resume.get("basics") and isinstance(
                complete_resume["basics"], dict
            ):
                try:
                    complete_resume["basics"] = Basics(**complete_resume["basics"])
                except Exception as e:
                    logger.error(f"❌ Error creating Basics object: {e}")
                    complete_resume["basics"] = None

            json_resume = JSONResume(**complete_resume)

            # If still completely empty, log explicit warning
            all_empty = all(
                getattr(json_resume, s, None) in (None, [], {})
                for s in ["basics", "work", "education", "skills", "projects", "awards"]
            )
            if all_empty:
                logger.warning("⚠️ Extraction produced an empty resume (all key sections None).")

            end_time = time.time()
            total_time = end_time - start_time
            logger.info(
                f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
            )

            return json_resume

        except Exception as e:
            logger.error(f"❌ Error creating JSONResume object: {e}")
            return None
