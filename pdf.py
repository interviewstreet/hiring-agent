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
        self.provider = initialize_llm_provider(DEFAULT_MODEL)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            doc = pymupdf.open(pdf_path)
            pages = range(doc.page_count)
            resume_text = to_markdown(doc, pages=pages)
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

    
    def extract_certificates_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "certificates", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render certificates template")
            return None
        
        return self._call_llm_for_section("certificates", resume_text, prompt)

    
    def extract_volunteer_experience_section(self, resume_text: str) -> Optional[Dict]:
        prompt = self.template_manager.render_template(
            "volunteer_experience", text_content=resume_text
        )
        if not prompt:
            logger.error("❌ Failed to render volunteer_experience template")
            return None
        
        return self._call_llm_for_section("volunteer_experience", resume_text, prompt)

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
            "certificates": self.extract_certificates_section,
            "volunteer_experience": self.extract_volunteer_experience_section,
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

       
        sections = [
            "basics",
            "work",
            "education",
            "skills",
            "projects",
            "awards",
            "certificates",
            "volunteer_experience",
        ]

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

        for section_name in sections:
            section_data = self._extract_section_data(text_content, section_name)

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
