EXPERIENCE_LEVELS = {
    "intern": "Software Intern",
    "entry": "Entry Level",
    "junior": "Junior (0-2 years)",
    "mid": "Mid-level (2-5 years)",
    "senior": "Senior (5+ years)",
    "staff": "Staff Engineer",
    "principal": "Principal Engineer",
}

ROLE_PRIORITIES = {
    "intern": [
        "Projects",
        "Learning",
        "Open Source",
        "Hackathons",
        "Research",
        "Internships",
    ],
    "entry": ["Internships", "Projects", "Open Source", "Learning"],
    "junior": [
        "Internships",
        "Projects",
        "Production Work",
        "Open Source",
        "Ownership",
    ],
    "mid": [
        "Production Impact",
        "Architecture",
        "Ownership",
        "Mentoring",
        "Cross-team Collaboration",
    ],
    "senior": [
        "Technical Leadership",
        "System Design",
        "Business Impact",
        "Scalability",
        "Mentoring",
        "Architecture Decisions",
    ],
    "staff": [
        "Cross-organization Impact",
        "Strategic Technical Direction",
        "System Architecture",
        "Leadership",
        "Mentoring",
    ],
    "principal": [
        "Company-wide Impact",
        "Industry Leadership",
        "Strategic Vision",
        "Core Architecture",
    ],
}

ROLE_MAX_SCORES = {
    "intern": {
        "open_source": 30,
        "self_projects": 45,
        "production": 10,
        "technical_skills": 15,
    },
    "entry": {
        "open_source": 25,
        "self_projects": 35,
        "production": 20,
        "technical_skills": 20,
    },
    "junior": {
        "open_source": 20,
        "self_projects": 25,
        "production": 35,
        "technical_skills": 20,
    },
    "mid": {
        "open_source": 15,
        "self_projects": 20,
        "production": 45,
        "technical_skills": 20,
    },
    "senior": {
        "open_source": 15,
        "self_projects": 15,
        "production": 45,
        "technical_skills": 25,
    },
    "staff": {
        "open_source": 15,
        "self_projects": 15,
        "production": 45,
        "technical_skills": 25,
    },
    "principal": {
        "open_source": 15,
        "self_projects": 15,
        "production": 45,
        "technical_skills": 25,
    },
}
