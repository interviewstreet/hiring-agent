Hiring Agent Test Suite

This directory contains the test suite for the Hiring Agent project. The tests ensure code quality, catch regressions, and document expected behavior.

Running Tests

Run All Tests

bash
pytest
Run with Coverage Report

bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser to see detailed coverage
Run Specific Test File

bash
pytest tests/test_pdf_handler.py
Run Specific Test

bash
pytest tests/test_pdf_handler.py::TestPDFHandler::test_extract_text_from_pdf_success
Run with Verbose Output

bash
pytest -v
Test Structure
Unit Tests
File: test_pdf_handler.py

Purpose: Tests for PDF extraction and parsing logic.

Focus: Individual functions and methods.

Approach: Use mocking to isolate components.

Integration Tests
Marked with @pytest.mark.integration.

Purpose: Test multiple components working together.

May require actual LLM models.

Writing New Tests
Test Naming Convention
Test files: test_*.py

Test classes: Test*

Test functions: test_*

Example Test

python
def test_extract_basics_section_with_valid_data(self, pdf_handler, sample_resume_text):
    """Test extraction of basics section with valid data."""
    with patch.object(pdf_handler, '_call_llm_for_section') as mock_llm:
        mock_llm.return_value = {'basics': {'name': 'John Doe'}}
        result = pdf_handler.extract_basics_section(sample_resume_text)
        assert result is not None
        assert result['basics']['name'] == 'John Doe'
Test Markers
@pytest.mark.slow: For tests that take longer than 1 second.

@pytest.mark.integration: For integration tests.

Run only fast tests:

bash
pytest -m "not slow"
Fixtures
Fixtures provide reusable test data or setup code:

pdf_handler: Creates a PDFHandler instance.

sample_resume_text: Provides sample resume text.

Mocking
We use unittest.mock for mocking:

Mock external dependencies (LLM calls, file I/O).

Keep tests fast and deterministic.

Isolate the code under test.

Coverage Goals
Aim for 80%+ code coverage.

Focus on critical paths and edge cases.

Do not sacrifice test quality for coverage numbers.

Continuous Integration
Tests run automatically on:

Every pull request.

Every commit to main branch.

Nightly builds.

Troubleshooting
Tests Fail Locally
Ensure all dependencies are installed:

bash
pip install -r requirements.txt
Check Python version (should be 3.11+):

bash
python --version
Clear pytest cache:

bash
pytest --cache-clear
Import Errors
Make sure you're in the project root.

Ensure virtual environment is activated.

Mocking Issues
Mock the correct path.

Use from module import function format.

Adding New Test Files
Create the file in tests/ directory with test_ prefix.

Import necessary modules and fixtures.

Follow existing test patterns.

Run tests to verify they pass.

Update this README if adding new test categories.

