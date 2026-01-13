# ARGUS Suite Test Suite

This directory contains the comprehensive test suite for the ARGUS Suite forensic analysis toolkit.

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and test utilities
├── test_config_loader.py                # Configuration loading tests
├── utils/
│   └── test_stat_tools.py              # Statistical utility function tests
├── models/
│   └── analysis/
│       └── test_statistical_test.py    # Pydantic model validation tests
├── preprocessing/
│   └── test_cleaning.py                # Data cleaning pipeline tests
└── integration/
    └── test_basic_pipeline.py          # End-to-end integration tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=argus --cov-report=html
```

The coverage report will be generated in `htmlcov/index.html`.

### Run Specific Test Files
```bash
# Test statistical tools only
pytest tests/utils/test_stat_tools.py

# Test configuration loading only
pytest tests/test_config_loader.py

# Test data cleaning only
pytest tests/preprocessing/test_cleaning.py
```

### Run Specific Test Classes or Functions
```bash
# Run a specific test class
pytest tests/utils/test_stat_tools.py::TestWilsonCI

# Run a specific test function
pytest tests/utils/test_stat_tools.py::TestWilsonCI::test_known_values
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests in Parallel (faster)
```bash
pytest -n auto
```

### Run Tests and Stop at First Failure
```bash
pytest -x
```

### Run Only Failed Tests from Last Run
```bash
pytest --lf
```

## Test Categories

### Unit Tests

**Utils Tests** (`tests/utils/`)
- `test_stat_tools.py`: Tests for core statistical functions
  - Wilson confidence intervals
  - Benjamini-Hochberg FDR correction
  - Risk ratios and odds ratios
  - Effect sizes (Cliff's Delta, Cohen's d)
  - Hypothesis tests (z-tests, chi-square, Fisher's exact)

**Model Tests** (`tests/models/`)
- `test_statistical_test.py`: Tests for Pydantic model validators
  - Rate bounds validation (0-1)
  - Count consistency validation
  - P-value bounds validation

**Preprocessing Tests** (`tests/preprocessing/`)
- `test_cleaning.py`: Tests for data cleaning pipeline
  - Duplicate removal
  - Timestamp parsing
  - Incomplete month filtering
  - Type enforcement
  - Schema validation

**Configuration Tests** (`tests/test_config_loader.py`)
- YAML configuration loading
- Validation error handling
- Default value application
- Custom value preservation

### Integration Tests

**Basic Pipeline Tests** (`tests/integration/`)
- End-to-end workflow from raw data to statistical results
- Component interaction verification
- Model integration with analysis functions

## Test Fixtures

Located in `conftest.py`, these fixtures are available to all tests:

### Data Fixtures
- `sample_fuel_data`: 100-row fuel transaction dataset
- `sample_eld_data`: Matching ELD telemetry data
- `sample_2x2_table`: Statistical test 2x2 contingency table
- `sample_distributions`: Various statistical distributions for testing

### Configuration Fixtures
- `temp_config_dir`: Temporary directory with valid config files

### Utility Functions
- `assert_valid_confidence_interval()`: Validate CI bounds
- `assert_valid_pvalue()`: Validate p-value is in [0, 1]

## Writing New Tests

### Test Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure
```python
import pytest
from argus.utils.stat_tools import wilson_ci

class TestWilsonCI:
    """Tests for Wilson confidence interval calculation."""

    def test_known_values(self) -> None:
        """Test against known statistical values."""
        lower, upper = wilson_ci(5, 10)
        assert 0 <= lower <= upper <= 1

    @pytest.mark.parametrize("k,n", [(0, 10), (5, 10), (10, 10)])
    def test_boundary_cases(self, k: int, n: int) -> None:
        """Test boundary conditions."""
        lower, upper = wilson_ci(k, n)
        assert lower <= upper
```

### Using Fixtures
```python
def test_with_sample_data(sample_fuel_data):
    """Test using the sample fuel data fixture."""
    assert len(sample_fuel_data) == 100
    assert 'vehicle_id' in sample_fuel_data.columns
```

### Parameterized Tests
```python
@pytest.mark.parametrize("input,expected", [
    (0, 0.0),
    (5, 0.5),
    (10, 1.0),
])
def test_parameterized(input: int, expected: float) -> None:
    """Test with multiple input/output pairs."""
    result = my_function(input)
    assert result == expected
```

## Test Markers

### Slow Tests
Mark tests that take significant time:
```python
@pytest.mark.slow
def test_large_dataset():
    """This test processes 1M rows."""
    ...
```

Run all tests except slow ones:
```bash
pytest -m "not slow"
```

## Coverage Goals

### Current Coverage
Run `pytest --cov=argus --cov-report=term-missing` to see current coverage.

### Target Coverage by Module
- **stat_tools.py**: 90%+ (critical statistical functions)
- **cleaning.py**: 80%+ (data pipeline foundation)
- **Statistical models**: 100% (validators are critical)
- **Config loading**: 90%+ (error handling paths)
- **Overall**: 80%+

## Continuous Integration

Tests should:
- Run on every commit (GitHub Actions)
- Block PRs if tests fail
- Generate coverage reports
- Run type checking (mypy) alongside tests

## Troubleshooting

### Import Errors
Make sure you've installed the package in development mode:
```bash
pip install -e ".[dev]"
```

### Fixture Not Found
Fixtures must be in `conftest.py` or imported explicitly.

### Test Discovery Issues
Ensure:
- Test files are named `test_*.py`
- Test classes are named `Test*`
- Test functions are named `test_*`
- `__init__.py` exists in test directories

## Adding More Tests

### Priority Areas (Not Yet Covered)
1. **Temporal Analysis** (`utils/temporal_tools.py`)
   - Mann-Kendall trend test
   - CUSUM change detection
   - Month-over-month analysis

2. **Risk Scoring** (`utils/risk_scoring.py`)
   - Risk profile calculation
   - Composite score weighting
   - Percentile-based categorization

3. **Feature Engineering** (`preprocessing/feature_engineering.py`)
   - Business hours calculation
   - Cost per gallon
   - MPG calculation

4. **Pattern Detection** (`suspicious_patterns.py`)
   - Multi-fillup detection
   - Red flag scoring
   - Geographic anomalies

5. **Main Pipeline** (`pipeline.py`)
   - End-to-end pipeline execution
   - Error handling
   - Report generation

## Best Practices

1. **Test one thing at a time**: Each test should verify a single behavior
2. **Use descriptive names**: Test names should clearly state what they test
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Test edge cases**: Zero, negative, NaN, infinity, empty inputs
5. **Use fixtures**: Reuse common test data and setup
6. **Avoid test interdependence**: Tests should run independently
7. **Mock external dependencies**: Don't rely on files, networks, databases
8. **Test both success and failure paths**: Verify error handling
9. **Keep tests fast**: Use small datasets, mock slow operations
10. **Document complex tests**: Explain why, not just what

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pydantic Testing Guide](https://docs.pydantic.dev/latest/concepts/validation/)

---

**Contributing**: When adding new features to ARGUS Suite, please add corresponding tests. Aim for at least 80% code coverage for new modules.
