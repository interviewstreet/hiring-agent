"""
Test utilities and helpers for the Hiring Agent test suite.

Provides common test fixtures, mock data, and utility functions.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from models import (
    JSONResume, Basics, Work, Education, Skill, Project, Award,
    GitHubProfile, EvaluationData, Location, Profile
)


@pytest.fixture
def sample_resume_data():
    """Provide sample resume data for testing."""
    return {
        "basics": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "website": "https://johndoe.com",
            "summary": "Experienced software engineer with 5+ years of experience",
            "location": {
                "city": "San Francisco",
                "countryCode": "US",
                "region": "CA"
            },
            "profiles": [
                {
                    "network": "GitHub",
                    "username": "johndoe",
                    "url": "https://github.com/johndoe"
                },
                {
                    "network": "LinkedIn",
                    "username": "johndoe",
                    "url": "https://linkedin.com/in/johndoe"
                }
            ]
        },
        "work": [
            {
                "company": "Tech Corp",
                "position": "Senior Software Engineer",
                "website": "https://techcorp.com",
                "startDate": "2021-01",
                "endDate": "present",
                "summary": "Led development of scalable web applications",
                "highlights": [
                    "Built microservices architecture serving 1M+ users",
                    "Led team of 5 developers",
                    "Improved system performance by 40%"
                ]
            },
            {
                "company": "StartupXYZ",
                "position": "Software Engineer",
                "startDate": "2019-06",
                "endDate": "2020-12",
                "summary": "Developed full-stack applications",
                "highlights": [
                    "Created REST APIs using Python/Django",
                    "Implemented CI/CD pipelines",
                    "Mentored junior developers"
                ]
            }
        ],
        "education": [
            {
                "institution": "University of Technology",
                "area": "Computer Science",
                "studyType": "Bachelor",
                "startDate": "2015-09",
                "endDate": "2019-05",
                "gpa": "3.8",
                "courses": [
                    "Data Structures and Algorithms",
                    "Machine Learning",
                    "Database Systems",
                    "Software Engineering"
                ]
            }
        ],
        "skills": [
            {
                "name": "Python",
                "level": "Expert",
                "keywords": ["Django", "Flask", "FastAPI", "Pandas", "NumPy"]
            },
            {
                "name": "JavaScript",
                "level": "Advanced",
                "keywords": ["React", "Node.js", "TypeScript", "Express"]
            },
            {
                "name": "Cloud Platforms",
                "level": "Intermediate",
                "keywords": ["AWS", "Docker", "Kubernetes", "Terraform"]
            }
        ],
        "projects": [
            {
                "name": "E-commerce Platform",
                "description": "Full-stack e-commerce platform with payment integration",
                "highlights": [
                    "Built with React and Django",
                    "Integrated Stripe payment processing",
                    "Deployed on AWS with auto-scaling"
                ],
                "keywords": ["Python", "React", "AWS", "Stripe"],
                "startDate": "2022-01",
                "endDate": "2022-06",
                "url": "https://github.com/johndoe/ecommerce-platform"
            }
        ],
        "awards": [
            {
                "title": "Employee of the Year",
                "date": "2023-01",
                "awarder": "Tech Corp",
                "summary": "Recognized for outstanding performance and leadership"
            }
        ]
    }


@pytest.fixture
def sample_github_profile():
    """Provide sample GitHub profile data for testing."""
    return {
        "login": "johndoe",
        "id": 12345,
        "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
        "html_url": "https://github.com/johndoe",
        "name": "John Doe",
        "company": "Tech Corp",
        "blog": "https://johndoe.com",
        "location": "San Francisco, CA",
        "email": "john.doe@example.com",
        "bio": "Software engineer passionate about building scalable applications",
        "public_repos": 25,
        "public_gists": 10,
        "followers": 150,
        "following": 75,
        "created_at": "2019-01-15T10:30:00Z",
        "updated_at": "2023-12-01T15:45:00Z"
    }


@pytest.fixture
def sample_github_repos():
    """Provide sample GitHub repositories data for testing."""
    return [
        {
            "id": 1001,
            "name": "awesome-web-app",
            "full_name": "johndoe/awesome-web-app",
            "html_url": "https://github.com/johndoe/awesome-web-app",
            "description": "A modern web application built with React and Django",
            "language": "Python",
            "stargazers_count": 150,
            "forks_count": 25,
            "open_issues_count": 3,
            "created_at": "2022-01-15T10:30:00Z",
            "updated_at": "2023-11-30T14:20:00Z",
            "pushed_at": "2023-11-30T14:20:00Z",
            "size": 5000,
            "archived": False,
            "disabled": False,
            "fork": False,
            "private": False,
            "topics": ["python", "django", "react", "web-app"]
        },
        {
            "id": 1002,
            "name": "machine-learning-toolkit",
            "full_name": "johndoe/machine-learning-toolkit",
            "html_url": "https://github.com/johndoe/machine-learning-toolkit",
            "description": "A comprehensive toolkit for machine learning projects",
            "language": "Python",
            "stargazers_count": 75,
            "forks_count": 15,
            "open_issues_count": 1,
            "created_at": "2021-06-10T09:15:00Z",
            "updated_at": "2023-10-15T11:30:00Z",
            "pushed_at": "2023-10-15T11:30:00Z",
            "size": 3000,
            "archived": False,
            "disabled": False,
            "fork": False,
            "private": False,
            "topics": ["machine-learning", "python", "data-science", "scikit-learn"]
        },
        {
            "id": 1003,
            "name": "api-gateway",
            "full_name": "johndoe/api-gateway",
            "html_url": "https://github.com/johndoe/api-gateway",
            "description": "Microservices API gateway with authentication and rate limiting",
            "language": "Go",
            "stargazers_count": 200,
            "forks_count": 40,
            "open_issues_count": 5,
            "created_at": "2020-03-20T16:45:00Z",
            "updated_at": "2023-12-01T09:10:00Z",
            "pushed_at": "2023-12-01T09:10:00Z",
            "size": 2000,
            "archived": False,
            "disabled": False,
            "fork": False,
            "private": False,
            "topics": ["go", "microservices", "api", "gateway"]
        }
    ]


@pytest.fixture
def sample_evaluation_data():
    """Provide sample evaluation data for testing."""
    return {
        "overall_score": 87.5,
        "max_possible_score": 100.0,
        "evaluation_summary": "Strong candidate with excellent technical skills and relevant experience",
        "strengths": [
            "Strong Python and JavaScript skills",
            "Experience with modern frameworks (React, Django)",
            "Good understanding of cloud platforms",
            "Active GitHub contributor with quality projects",
            "Leadership experience and team mentoring"
        ],
        "areas_for_improvement": [
            "Could benefit from more experience with containerization",
            "Limited experience with machine learning in production",
            "Could improve technical documentation skills"
        ],
        "bonus_points": 8,
        "deductions": 0,
        "github_analysis": "Active contributor with 25 public repositories. Shows consistent development activity with quality projects spanning web development, machine learning, and microservices. Good mix of languages and technologies.",
        "final_recommendation": "Hire"
    }


@pytest.fixture
def temp_pdf_file():
    """Create a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        # Write minimal PDF content
        temp_file.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF')
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Cleanup
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def mock_llm_response():
    """Provide mock LLM response data."""
    return {
        'message': {
            'content': '{"overall_score": 85.0, "evaluation_summary": "Strong candidate", "strengths": ["Good technical skills"], "areas_for_improvement": ["Could improve documentation"], "bonus_points": 5, "deductions": 0, "github_analysis": "Active contributor", "final_recommendation": "Hire"}'
        },
        'done': True
    }


class TestDataFactory:
    """Factory class for creating test data objects."""
    
    @staticmethod
    def create_json_resume(data: Dict[str, Any] = None) -> JSONResume:
        """Create a JSONResume object from test data."""
        if data is None:
            data = {}
        
        defaults = {
            "basics": {
                "name": "Test User",
                "email": "test@example.com"
            },
            "work": [],
            "education": [],
            "skills": [],
            "projects": [],
            "awards": [],
            "publications": [],
            "languages": [],
            "interests": [],
            "references": []
        }
        
        # Merge defaults with provided data
        merged_data = {**defaults, **data}
        
        return JSONResume(**merged_data)
    
    @staticmethod
    def create_github_profile(data: Dict[str, Any] = None) -> GitHubProfile:
        """Create a GitHubProfile object from test data."""
        if data is None:
            data = {}
        
        defaults = {
            "login": "testuser",
            "id": 12345,
            "avatar_url": "https://github.com/testuser.png",
            "html_url": "https://github.com/testuser",
            "name": "Test User",
            "public_repos": 10,
            "followers": 50,
            "following": 25,
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"
        }
        
        merged_data = {**defaults, **data}
        return GitHubProfile(**merged_data)
    
    @staticmethod
    def create_evaluation_data(data: Dict[str, Any] = None) -> EvaluationData:
        """Create an EvaluationData object from test data."""
        if data is None:
            data = {}
        
        defaults = {
            "overall_score": 75.0,
            "max_possible_score": 100.0,
            "evaluation_summary": "Good candidate",
            "strengths": ["Technical skills"],
            "areas_for_improvement": ["Could improve"],
            "bonus_points": 0,
            "deductions": 0,
            "github_analysis": "Active contributor",
            "final_recommendation": "Consider"
        }
        
        merged_data = {**defaults, **data}
        return EvaluationData(**merged_data)


def assert_valid_json_resume(resume: JSONResume):
    """Assert that a JSONResume object is valid."""
    assert resume is not None
    assert resume.basics is not None
    assert resume.basics.name is not None
    assert resume.basics.email is not None
    assert isinstance(resume.work, list)
    assert isinstance(resume.education, list)
    assert isinstance(resume.skills, list)


def assert_valid_evaluation_data(evaluation: EvaluationData):
    """Assert that an EvaluationData object is valid."""
    assert evaluation is not None
    assert evaluation.overall_score is not None
    assert evaluation.max_possible_score is not None
    assert evaluation.evaluation_summary is not None
    assert isinstance(evaluation.strengths, list)
    assert isinstance(evaluation.areas_for_improvement, list)
    assert evaluation.bonus_points is not None
    assert evaluation.deductions is not None
    assert evaluation.final_recommendation is not None


def create_mock_pdf_handler():
    """Create a mock PDFHandler for testing."""
    mock_handler = Mock()
    mock_handler.extract_text.return_value = """
    John Doe
    Software Engineer
    john@example.com
    
    Experience:
    - Tech Corp: Software Engineer (2020-2023)
    - Developed web applications using Python
    
    Education:
    - University of Technology: Computer Science (2016-2020)
    
    Skills:
    - Python, JavaScript, React
    """
    return mock_handler


def create_mock_github_data():
    """Create mock GitHub data for testing."""
    return {
        'profile': {
            'login': 'johndoe',
            'public_repos': 25,
            'followers': 50,
            'name': 'John Doe'
        },
        'repos': [
            {
                'name': 'awesome-project',
                'stargazers_count': 100,
                'language': 'Python',
                'description': 'An awesome project'
            }
        ]
    }
