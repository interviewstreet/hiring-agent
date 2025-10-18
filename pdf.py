import os
import sys
import json
import time
import logging
import pymupdf
import re

from models import (
    JSONResume,
    Basics,
    Work,
    Education,
    Skill,
    Project,
    Award,
    BasicsSection,
    WorkSection,
    EducationSection,
    SkillsSection,
    ProjectsSection,
    AwardsSection,
)
from llm_utils import initialize_llm_provider, extract_json_from_response
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
from config import DEVELOPMENT_MODE

logger = logging.getLogger(__name__)


class PDFHandler:

    def __init__(self):
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(DEFAULT_MODEL)

    def _split_text_into_sections(self, text: str) -> Dict[str, str]:
        """Split resume markdown text into sections using heuristic header matching.

        Returns a dictionary mapping section names to their text content.
        """
        section_patterns = {
            "basics": r"(?i)^#{0,3}\s*(contact|personal\s+information|about)\s*$",
            "work": r"(?i)^#{0,3}\s*(work\s+experience|experience|professional\s+experience|employment|career)\s*$",
            "education": r"(?i)^#{0,3}\s*(education|academic|qualifications?)\s*$",
            "skills": r"(?i)^#{0,3}\s*(skills?|technical\s+skills?|competenc(?:y|ies)|technologies|skills?\s+summary)\s*$",
            "projects": r"(?i)^#{0,3}\s*(projects?|portfolio)\s*$",
            "awards": r"(?i)^#{0,3}\s*(awards?|honors?|achievements?|recognition)\s*$",
        }

        sections = {}
        lines = text.split("\n")
        current_section = None
        current_content = []

        # First pass: collect everything before any section header as "basics"
        pre_section_lines = []
        first_header_found = False

        for line in lines:
            matched_section = None
            for section_name, pattern in section_patterns.items():
                if re.match(pattern, line.strip()):
                    matched_section = section_name
                    break

            if matched_section:
                first_header_found = True
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                elif pre_section_lines:
                    # Save pre-section content as basics if basics hasn't been set
                    if "basics" not in sections:
                        sections["basics"] = "\n".join(pre_section_lines).strip()

                current_section = matched_section
                current_content = [line]
            else:
                if not first_header_found:
                    pre_section_lines.append(line)
                elif current_section:
                    current_content.append(line)

        # Save the last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content).strip()
        elif pre_section_lines and "basics" not in sections:
            sections["basics"] = "\n".join(pre_section_lines).strip()

        # Fallback: if no sections were found, treat entire text as unstructured
        if not sections:
            logger.warning(
                "⚠️ No section headers found. Using full text for all sections."
            )
            sections["_full_text"] = text

        return sections

    def _build_context_snippet(self, sections: Dict[str, str]) -> str:
        """Build a context snippet from basics and education sections.

        This provides background information for better section extraction.
        """
        context_parts = []

        if sections.get("basics"):
            context_parts.append("--- CANDIDATE INFORMATION ---")
            context_parts.append(sections["basics"])
            context_parts.append("")

        if sections.get("education"):
            context_parts.append("--- EDUCATION BACKGROUND ---")
            context_parts.append(sections["education"])
            context_parts.append("")

        if not context_parts:
            return ""

        return "\n".join(context_parts)

    def _save_debug_sections(self, sections: Dict[str, str], pdf_filename: str) -> None:
        """Save split sections to debug files when in development mode."""
        if not DEVELOPMENT_MODE:
            return

        try:
            # Create debug output directory
            debug_dir = os.path.join("debug_sections")
            os.makedirs(debug_dir, exist_ok=True)

            # Create a subdirectory for this specific PDF
            base_name = os.path.splitext(os.path.basename(pdf_filename))[0]
            pdf_debug_dir = os.path.join(debug_dir, base_name)
            os.makedirs(pdf_debug_dir, exist_ok=True)

            # Save each section to a separate file
            for section_name, section_content in sections.items():
                if section_content:
                    output_file = os.path.join(
                        pdf_debug_dir, f"{section_name}_section.txt"
                    )
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(f"=== {section_name.upper()} SECTION ===\n\n")
                        f.write(section_content)
                        f.write(f"\n\n=== END {section_name.upper()} SECTION ===")

            # Save a summary file
            summary_file = os.path.join(pdf_debug_dir, "_sections_summary.txt")
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("=== SECTIONS EXTRACTION SUMMARY ===\n\n")
                f.write(f"PDF: {pdf_filename}\n")
                f.write(f"Total sections found: {len(sections)}\n\n")
                for section_name, section_content in sections.items():
                    char_count = len(section_content) if section_content else 0
                    f.write(f"- {section_name}: {char_count} characters\n")

            logger.info(f"🐛 Debug sections saved to: {pdf_debug_dir}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to save debug sections: {e}")

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

            # Use the appropriate provider to make the API call
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = response["message"]["content"]

            try:
                response_text = extract_json_from_response(response_text)
                json_start = response_text.find("{")
                json_end = response_text.rfind("}")
                if json_start != -1 and json_end != -1:
                    response_text = response_text[json_start : json_end + 1]
                parsed_data = json.loads(response_text)
                logger.debug(f"✅ Successfully extracted {section_name} section")

                transformed_data = transform_parsed_data(parsed_data)
                end_time = time.time()
                total_time = end_time - start_time
                logger.debug(
                    f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
                )

                return transformed_data
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error parsing JSON for {section_name} section: {e}")
                logger.error(f"Raw response: {response_text}")
                return None

        except Exception as e:
            logger.error(f"❌ Error calling LLM for {section_name} section: {e}")
            return None

    def extract_basics_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "basics",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render basics template")
            return None
        return self._call_llm_for_section(
            "basics", target_section_text, prompt, BasicsSection
        )

    def extract_work_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "work",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render work template")
            return None
        return self._call_llm_for_section(
            "work", target_section_text, prompt, WorkSection
        )

    def extract_education_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "education",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render education template")
            return None
        return self._call_llm_for_section(
            "education", target_section_text, prompt, EducationSection
        )

    def extract_skills_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "skills",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render skills template")
            return None
        return self._call_llm_for_section(
            "skills", target_section_text, prompt, SkillsSection
        )

    def extract_projects_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "projects",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render projects template")
            return None
        return self._call_llm_for_section(
            "projects", target_section_text, prompt, ProjectsSection
        )

    def extract_awards_section(
        self, target_section_text: str, context_snippet: str = ""
    ) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "awards",
            target_section_text=target_section_text,
            context_snippet=context_snippet,
        )
        if not prompt:
            logger.error("❌ Failed to render awards template")
            return None
        return self._call_llm_for_section(
            "awards", target_section_text, prompt, AwardsSection
        )

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
            return self._extract_all_sections_separately(text_content, pdf_path)

        except Exception as e:
            logger.error(f"❌ Error during PDF to JSON extraction: {e}")
            return None

    def _extract_section_data(
        self,
        target_section_text: str,
        section_name: str,
        context_snippet: str = "",
        return_model=None,
    ) -> Optional[Dict]:
        section_extractors = {
            "basics": self.extract_basics_section,
            "work": self.extract_work_section,
            "education": self.extract_education_section,
            "skills": self.extract_skills_section,
            "projects": self.extract_projects_section,
            "awards": self.extract_awards_section,
        }

        if section_name not in section_extractors:
            logger.error(f"❌ Invalid section name: {section_name}")
            logger.error(f"Valid sections: {list(section_extractors.keys())}")
            return None

        return section_extractors[section_name](target_section_text, context_snippet)

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
        self, text_content: str, pdf_path: str = None
    ) -> Optional[JSONResume]:
        start_time = time.time()

        # Step 1: Split the text into sections
        logger.debug("🔍 Splitting resume text into sections...")
        split_sections = self._split_text_into_sections(text_content)
        logger.debug(f"✅ Found sections: {list(split_sections.keys())}")

        # Save debug sections if in development mode
        if pdf_path:
            self._save_debug_sections(split_sections, pdf_path)

        # Step 2: Extract basics and education first to build context
        sections_order = ["basics", "education", "work", "skills", "projects", "awards"]

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

        # Extract basics and education first (no context needed for these)
        for section_name in ["basics", "education"]:
            # Use full text if section splitting failed
            target_text = split_sections.get(
                section_name, split_sections.get("_full_text", text_content)
            )
            section_data = self._extract_section_data(target_text, section_name, "")

            if section_data:
                complete_resume.update(section_data)
                logger.debug(f"✅ Successfully extracted {section_name} section")
            else:
                logger.error(f"⚠️ Failed to extract {section_name} section")

        # Step 3: Build context snippet from basics and education
        context_snippet = self._build_context_snippet(split_sections)
        if context_snippet:
            logger.debug(f"📝 Built context snippet ({len(context_snippet)} chars)")
        else:
            logger.warning("⚠️ No context snippet available, using empty context")

        # Step 4: Extract remaining sections with context
        for section_name in ["work", "skills", "projects", "awards"]:
            # Use full text if section splitting failed
            target_text = split_sections.get(
                section_name, split_sections.get("_full_text", text_content)
            )
            section_data = self._extract_section_data(
                target_text, section_name, context_snippet
            )

            if section_data:
                complete_resume.update(section_data)
                logger.debug(f"✅ Successfully extracted {section_name} section")
            else:
                logger.error(f"⚠️ Failed to extract {section_name} section")

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

            end_time = time.time()
            total_time = end_time - start_time
            logger.info(
                f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
            )

            return json_resume

        except Exception as e:
            logger.error(f"❌ Error creating JSONResume object: {e}")
            return None
