# Python Version Requirement

The ARGUS Suite requires **Python 3.12 or higher** as specified in `pyproject.toml`.

## Running Tests

To run the test suite, ensure you have Python 3.12+ installed:

```bash
# Check your Python version
python --version

# Should show Python 3.12.x or higher
```

## Installation

```bash
# Install the package with development dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# Run with coverage
pytest --cov=argus --cov-report=html
```

## Why Python 3.12+?

The project uses modern Python features and dependencies that require Python 3.12:
- Type hints and type system improvements
- Modern Pydantic 2.11.0+ features
- NumPy 2.3.0+ compatibility
- Updated pandas 2.3.0+ features

## CI/CD

Continuous Integration should use Python 3.12 or 3.13 for testing.

Example GitHub Actions configuration:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest --cov=argus --cov-report=xml
```
