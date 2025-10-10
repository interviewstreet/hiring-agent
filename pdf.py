import os
import sys
import json
import time
import logging
import pymupdf

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

logger = logging.getLogger(__name__)


class PDFHandler:

    def __init__(self):
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        """Initialize the appropriate LLM provider based on the model."""
        self.provider = initialize_llm_provider(DEFAULT_MODEL)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = pymupdf.open(pdf_path)
            pages = range(doc.page_count)
            # We are calling the enhanced pymupdf_rag script here
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
        # This function remains unchanged, as it correctly calls the LLM for a given piece of text.
        # The change is that we will now pass it SMALLER, pre-separated chunks of text.
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

    # --- All the extract_*_section methods below remain unchanged ---
    def extract_basics_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "basics", text_content=resume_text
        )
        return self._call_llm_for_section("basics", resume_text, prompt, BasicsSection)

    def extract_work_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template("work", text_content=resume_text)
        return self._call_llm_for_section("work", resume_text, prompt, WorkSection)

    def extract_education_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "education", text_content=resume_text
        )
        return self._call_llm_for_section(
            "education", resume_text, prompt, EducationSection
        )

    def extract_skills_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "skills", text_content=resume_text
        )
        return self._call_llm_for_section("skills", resume_text, prompt, SkillsSection)

    def extract_projects_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "projects", text_content=resume_text
        )
        return self._call_llm_for_section(
            "projects", resume_text, prompt, ProjectsSection
        )

    def extract_awards_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "awards", text_content=resume_text
        )
        return self._call_llm_for_section("awards", resume_text, prompt, AwardsSection)

    # --- All other top-level methods remain unchanged ---
    def extract_json_from_text(self, resume_text: str) -> Optional[JSONResume]:
        return self._extract_all_sections_separately(resume_text)

    def extract_json_from_pdf(self, pdf_path: str) -> Optional[JSONResume]:
        text_content = self.extract_text_from_pdf(pdf_path)
        if not text_content:
            return None
        return self._extract_all_sections_separately(text_content)

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
        }
        if section_name in section_extractors:
            return section_extractors[section_name](text_content)
        return None

    # --- UPGRADE #1: ADD THE NEW HELPER FUNCTION ---
    # This is now properly indented to be a method of the PDFHandler class.
    def _split_markdown_by_headers(self, markdown_text: str) -> dict:
        """
        Splits a markdown string into a dictionary based on H2 headers.
        This is a robust, deterministic way to parse the resume structure.
        """
        sections = {}
        lines = markdown_text.strip().split("\n")

        current_header_key = "basics"
        current_content = []

        known_headers = {
            "academic details": "education",
            "work experience": "work",
            "projects": "projects",
            "technical skills": "skills",
            "relevant courses": "skills",  # Group courses with skills
            "achievements": "awards",
        }

        for line in lines:
            if line.strip().startswith("##"):
                cleaned_line = line.strip().replace("##", "").strip().lower()

                if cleaned_line in known_headers:
                    # Save the content of the previous section
                    if current_header_key and current_content:
                        sections[current_header_key] = "\n".join(
                            current_content
                        ).strip()

                    # Start the new section
                    current_header_key = known_headers[cleaned_line]
                    current_content = []
                else:
                    # If it's a header we don't recognize, treat it as content
                    current_content.append(line)
            else:
                current_content.append(line)

        # Save the very last section
        if current_header_key and current_content:
            sections[current_header_key] = "\n".join(current_content).strip()

        return sections

    # --- UPGRADE #2: REPLACE THE OLD, INEFFICIENT FUNCTION ---
    def _extract_all_sections_separately(
        self, text_content: str
    ) -> Optional[JSONResume]:
        start_time = time.time()

        # Step 1: Reliably split the document into sections using our new helper function.
        sectioned_text = self._split_markdown_by_headers(text_content)

        complete_resume = {
            "basics": None,
            "work": None,
            "education": None,
            "awards": None,
            "skills": None,
            "projects": None,
        }

        # Step 2: Loop through the pre-separated sections and send them to the LLM for analysis.
        for section_name, section_content in sectioned_text.items():
            if section_name in complete_resume and section_content:
                # Pass the specific section_content, not the whole resume text.
                section_data = self._extract_section_data(section_content, section_name)

                if section_data:
                    # If a section already has data (e.g. skills + courses), merge them
                    if complete_resume.get(section_name):
                        # This is a simplified merge, more complex logic can be added if needed
                        if isinstance(complete_resume[section_name], list):
                            complete_resume[section_name].extend(
                                section_data.get(section_name, [])
                            )
                    else:
                        complete_resume.update(section_data)
                    logger.debug(f"✅ Successfully extracted {section_name} section")
                else:
                    logger.error(
                        f"⚠️ Failed to extract {section_name} section using LLM"
                    )

        try:
            if complete_resume.get("basics") and isinstance(
                complete_resume["basics"], dict
            ):
                complete_resume["basics"] = Basics(**complete_resume["basics"])

            # Filter out keys not expected by JSONResume before creating the object
            valid_keys = JSONResume.model_fields.keys()
            filtered_resume_data = {
                k: v for k, v in complete_resume.items() if k in valid_keys
            }

            json_resume = JSONResume(**filtered_resume_data)

            end_time = time.time()
            total_time = end_time - start_time
            logger.info(
                f"⏱️ Total time for separate section extraction: {total_time:.2f} seconds"
            )

            return json_resume

        except Exception as e:
            logger.error(f"❌ Error creating JSONResume object: {e}")
            return None
