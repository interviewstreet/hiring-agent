"""
Configuration settings for the hiring agent application.
"""

# Global development mode flag
DEVELOPMENT_MODE = True

# When True, strip bias-inducing PII (name, contact details, location, school
# name, GPA) from the resume and GitHub data before they reach the evaluation
# LLM. The original data is preserved for CSV export and recruiter-facing
# output; only the text sent to the scorer is redacted.
REDACT_PII_FOR_EVALUATION = True
