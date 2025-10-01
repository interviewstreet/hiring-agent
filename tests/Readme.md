Testing Guide
Overview
This directory contains the test suite for the Hiring Agent project. The tests ensure code quality, catch regressions, and document expected behavior.
Running Tests
Run All Tests
bashpytest
Run with Coverage Report
bashpytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser to see detailed coverage
Run Specific Test File
bashpytest tests/test_pdf_handler.py
Run Specific Test
bashpytest tests/test_pdf_handler.py::TestPDFHandler::test_extract_text_from_pdf_success
Run with Verbose Output
bashpytest -v
Test Structure
Unit Tests

test_pdf_handler.py: Tests for PDF extraction and parsing logic
Focus on individual functions and methods
Use mocking to isolate components

Integration Tests

Tests marked with @pytest.mark.integration
Test multiple components working together
May require actual LLM models

Writing New Tests
Test Naming Convention

Test files: test_*.py
Test classes: Test*
Test functions: test_*

Example Test
pythondef test_extract_basics_section_with_valid_data(self, pdf_handler, sample_resume_text):
    """Test extraction of basics section with valid data."""
    with patch.object(pdf_handler, '_call_llm_for_section') as mock_llm:
        mock_llm.return_value = {'basics': {'name': 'John Doe'}}
        result = pdf_handler.extract_basics_section(sample_resume_text)
        assert result is not None
        assert result['basics']['name'] == 'John Doe'
Test Markers

@pytest.mark.slow: For tests that take longer than 1 second
@pytest.mark.integration: For integration tests

Run only fast tests:
bashpytest -m "not slow"
Fixtures
Fixtures are reusable test data or setup code:

pdf_handler: Creates a PDFHandler instance
sample_resume_text: Provides sample resume text

Mocking
We use unittest.mock for mocking:

Mock external dependencies (LLM calls, file I/O)
Keep tests fast and deterministic
Isolate the code under test

Coverage Goals

Aim for 80%+ code coverage
Focus on critical paths and edge cases
Don't sacrifice test quality for coverage numbers

Continuous Integration
Tests run automatically on:

Every pull request
Every commit to main branch
Nightly builds

Troubleshooting
Tests Fail Locally

Ensure all dependencies are installed: pip install -r requirements.txt
Check Python version: python --version (should be 3.11+)
Clear pytest cache: pytest --cache-clear

Import Errors
Make sure you're in the project root directory and virtual environment is activated.
Mocking Issues
Ensure you're mocking the right path. Use from module import function format.
Adding New Test Files

Create file in tests/ directory with test_ prefix
Import necessary modules and fixtures
Follow existing test patterns
Run tests to verify they pass
Update this README if adding new test categories