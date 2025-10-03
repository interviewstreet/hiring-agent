"""
Template Manager for Section Extraction

This module provides functionality to load and render Jinja templates for
section-specific resume extraction prompts.
"""

import os
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template


class TemplateManager:
    """
    Manages Jinja templates for section-specific resume extraction.

    This class provides functionality to load and render templates for
    different resume sections (basics, work, education, skills, projects, awards).
    """

    def __init__(self, template_dir: str = "prompts/templates"):
        """
        Initialize the template manager.

        Args:
            template_dir (str): Directory containing Jinja templates
        """
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )
        self._templates: Dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self):
        """Load all available templates."""
        template_files = {
            "basics": "basics.jinja",
            "work": "work.jinja",
            "education": "education.jinja",
            "skills": "skills.jinja",
            "projects": "projects.jinja",
            "awards": "awards.jinja",
            "system_message": "system_message.jinja",
            "github_project_selection": "github_project_selection.jinja",
            "resume_evaluation_criteria": "resume_evaluation_criteria.jinja",
            "resume_evaluation_system_message": "resume_evaluation_system_message.jinja",
            "prioritized_skills": "prioritized_skills.jinja",
        }

        for section_name, filename in template_files.items():
            try:
                template_path = os.path.join(self.template_dir, filename)
                if os.path.exists(template_path):
                    self._templates[section_name] = self.env.get_template(filename)
                else:
                    print(f"⚠️ Template file not found: {template_path}")
            except Exception as e:
                print(f"❌ Error loading template {filename}: {e}")

    def get_available_sections(self) -> list:
        """
        Get list of available section names.

        Returns:
            list: List of available section names
        """
        return list(self._templates.keys())

    def render_template(self, section_name: str, **kwargs) -> Optional[str]:
        """
        Render a template for a specific section.

        Args:
            section_name (str): Name of the section (basics, work, education, etc.)
            **kwargs: Template variables (e.g., text_content)

        Returns:
            Optional[str]: Rendered template string, or None if template not found
        """
        if section_name not in self._templates:
            print(f"❌ Template not found for section: {section_name}")
            print(f"Available sections: {self.get_available_sections()}")
            return None

        try:
            template = self._templates[section_name]
            return template.render(**kwargs)
        except Exception as e:
            print(f"❌ Error rendering template for {section_name}: {e}")
            return None
