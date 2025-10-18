# Hiring Agent Test Suite

This directory contains comprehensive tests for the Hiring Agent application, including unit tests, integration tests, and performance tests.

## 🧪 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and test utilities
├── test_models.py              # Unit tests for Pydantic models
├── test_llm_utils.py           # Unit tests for LLM utilities
├── test_integration.py         # Integration tests for full pipeline
└── test_performance.py         # Performance and optimization tests
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation
```bash
# Install dependencies including test packages
pip install -r requirements.txt

# Or install only test dependencies
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

### Running Tests

#### Run All Tests
```bash
pytest
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/test_models.py tests/test_llm_utils.py

# Integration tests only
pytest tests/test_integration.py

# Performance tests only
pytest tests/test_performance.py
```

#### Run with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

#### Run Tests in Parallel
```bash
pytest -n auto
```

## 📋 Test Categories

### Unit Tests (`test_models.py`, `test_llm_utils.py`)
- **Purpose**: Test individual components in isolation
- **Coverage**: Pydantic models, LLM utilities, data validation
- **Speed**: Fast (< 1 second per test)
- **Dependencies**: Minimal mocking

### Integration Tests (`test_integration.py`)
- **Purpose**: Test complete workflows and component interactions
- **Coverage**: End-to-end pipeline, PDF processing, GitHub integration
- **Speed**: Medium (1-5 seconds per test)
- **Dependencies**: Mocked external services

### Performance Tests (`test_performance.py`)
- **Purpose**: Test performance characteristics and optimization
- **Coverage**: Response times, memory usage, concurrent processing
- **Speed**: Slow (> 5 seconds per test)
- **Dependencies**: Realistic data sizes

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    api: Tests that require API access
```

### Test Markers
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Performance tests
- `@pytest.mark.api`: Tests requiring API access

## 🛠️ Test Utilities

### Fixtures (`conftest.py`)
- `sample_resume_data`: Complete resume data for testing
- `sample_github_profile`: GitHub profile data
- `sample_github_repos`: GitHub repository data
- `sample_evaluation_data`: Evaluation results
- `temp_pdf_file`: Temporary PDF file for testing
- `mock_llm_response`: Mock LLM response data

### Test Data Factory
```python
from tests.conftest import TestDataFactory

# Create test objects
resume = TestDataFactory.create_json_resume()
profile = TestDataFactory.create_github_profile()
evaluation = TestDataFactory.create_evaluation_data()
```

### Utility Functions
```python
# Assert valid data structures
assert_valid_json_resume(resume)
assert_valid_evaluation_data(evaluation)

# Create mock objects
mock_pdf_handler = create_mock_pdf_handler()
mock_github_data = create_mock_github_data()
```

## 📊 Coverage Requirements

- **Minimum Coverage**: 80%
- **Critical Modules**: 90%+ (models, llm_utils, core pipeline)
- **Coverage Reports**: HTML and terminal output

### Coverage Commands
```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pytest --cov=. --cov-report=term-missing

# Coverage with fail threshold
pytest --cov=. --cov-fail-under=80
```

## 🚀 CI/CD Integration

### GitHub Actions
The test suite is integrated with GitHub Actions for continuous integration:

- **Matrix Testing**: Python 3.11 and 3.12
- **Test Categories**: Unit, integration, performance
- **Coverage**: Uploaded to Codecov
- **Security**: Bandit and Safety scans
- **Documentation**: Auto-build on main branch

### Local CI Simulation
```bash
# Run full CI pipeline locally
make ci

# Or step by step
make lint
make test-coverage
make check-all
```

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest -v -s
```

### Specific Test Debugging
```bash
# Run specific test with debug output
pytest tests/test_models.py::TestBasics::test_valid_basics -v -s

# Run tests matching pattern
pytest -k "test_valid" -v
```

### Test Discovery
```bash
# List all tests
pytest --collect-only

# List tests in specific file
pytest tests/test_models.py --collect-only
```

## 📈 Performance Benchmarks

### Expected Performance Targets
- **PDF Extraction**: < 10 seconds for typical resume
- **GitHub API Calls**: < 5 seconds per request
- **JSON Processing**: < 1 second for large responses
- **Memory Usage**: < 50MB increase during processing
- **Concurrent Operations**: 5x speedup with threading

### Performance Test Commands
```bash
# Run performance tests
pytest tests/test_performance.py -v

# Run with timing
pytest tests/test_performance.py -v --durations=10
```

## 🔍 Test Data Management

### Sample Data
- **Resume Data**: Realistic JSON Resume format
- **GitHub Data**: Complete profile and repository information
- **Evaluation Data**: Comprehensive scoring results
- **PDF Files**: Minimal valid PDF structures

### Mock Data
- **External APIs**: GitHub, LLM providers
- **File Operations**: PDF processing, cache operations
- **Network Calls**: HTTP requests and responses

## 🚨 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

#### Missing Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Install only test dependencies
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

#### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Fix file permissions
find . -name "*.py" -exec chmod 644 {} \;
```

### Test Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
pytest --version
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pytest Mock Documentation](https://pytest-mock.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🤝 Contributing to Tests

### Adding New Tests
1. Follow naming convention: `test_*.py`
2. Use descriptive test names: `test_valid_resume_creation`
3. Include docstrings explaining test purpose
4. Use appropriate markers (`@pytest.mark.unit`, etc.)
5. Add fixtures for reusable test data

### Test Quality Guidelines
- **Isolation**: Tests should not depend on each other
- **Deterministic**: Tests should produce consistent results
- **Fast**: Unit tests should run quickly
- **Clear**: Test names and assertions should be self-documenting
- **Comprehensive**: Cover edge cases and error conditions

### Example Test Structure
```python
class TestNewFeature:
    """Test new feature functionality."""
    
    def test_feature_success_case(self):
        """Test feature with valid input."""
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = process_feature(input_data)
        
        # Assert
        assert result is not None
        assert result.status == "success"
    
    def test_feature_error_case(self):
        """Test feature with invalid input."""
        # Arrange
        invalid_data = None
        
        # Act & Assert
        with pytest.raises(ValueError):
            process_feature(invalid_data)
```
