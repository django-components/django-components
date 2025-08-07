# Django Components Repository

Django Components is a Python package that provides a modular and extensible UI framework for Django. It combines Django's templating system with component-based modularity similar to modern frontend frameworks like Vue or React.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Initial Setup
- Install development dependencies:
  - `pip install -r requirements-dev.txt` -- installs all dev dependencies including pytest, black, flake8, etc.
  - `pip install -e .` -- install the package in development mode
- Install Playwright for browser testing (optional, may timeout):
  - `playwright install chromium --with-deps` -- NEVER CANCEL: Can take 10+ minutes due to large download. Set timeout to 15+ minutes.

### Building and Testing
- **NEVER CANCEL BUILDS OR TESTS** -- All timeouts below are validated minimums
- Run the full test suite:
  - `python -m pytest` -- runs all tests. NEVER CANCEL: Takes 2-5 minutes for full suite. Set timeout to 10+ minutes.
  - `python -m pytest tests/test_component.py` -- runs specific test file (~5 seconds)
  - `python -m pytest tests/test_templatetags*.py` -- runs template tag tests (~10 seconds, 349 tests)
- Run linting and code quality checks:
  - `black --check src/django_components` -- check code formatting (~1 second)
  - `black src/django_components` -- format code
  - `isort --check-only --diff src/django_components` -- check import sorting (~1 second)
  - `flake8 .` -- run linting (~2 seconds)
  - `mypy .` -- run type checking (~10 seconds, may show some errors in tests)
- Use tox for comprehensive testing (requires network access):
  - `tox -e black` -- run black in isolated environment
  - `tox -e flake8` -- run flake8 in isolated environment  
  - `tox` -- run full test matrix (multiple Python/Django versions). NEVER CANCEL: Takes 10-30 minutes.

### Sample Project Testing
- Test the sample project to validate functionality:
  - `cd sampleproject`
  - `pip install -r requirements.txt` -- install sample project dependencies
  - `python manage.py check` -- check Django project for errors
  - `python manage.py migrate --noinput` -- run database migrations
  - `python manage.py runserver` -- start development server on port 8000
  - Test with: `curl http://127.0.0.1:8000/` -- should return HTML with calendar component

### Package Building
- Build the package:
  - `python -m build` -- build wheel and sdist. NEVER CANCEL: Takes 2-5 minutes, may timeout on network issues.

### Django Components Commands
The package provides custom Django management commands:
- `python manage.py components list` -- list all components in the project
- `python manage.py components create <name>` -- create a new component
- `python manage.py startcomponent <name>` -- create a new component (alias)
- `python manage.py upgradecomponent` -- upgrade component syntax from old to new format

## Validation

- Always run linting before committing: `black src/django_components && isort src/django_components && flake8 .`
- Always run at least basic tests: `python -m pytest tests/test_component.py`
- Test sample project functionality: Start the sample project and make a request to verify components render correctly
- Check that imports work: `python -c "import django_components; print('OK')"`

## Common Tasks

### Repository Structure
- `src/django_components/` -- main package source code
- `tests/` -- comprehensive test suite with 1000+ tests
- `sampleproject/` -- working Django project demonstrating component usage
- `docs/` -- documentation source (uses mkdocs)
- `requirements-dev.txt` -- development dependencies (validated to work)
- `requirements-docs.txt` -- documentation building dependencies
- `pyproject.toml` -- package configuration and dependencies
- `tox.ini` -- test environment configuration for multiple Python/Django versions

### Key Files to Check When Making Changes
- Always check the sample project works after making changes to core functionality
- Test component discovery by running `python manage.py components list` in the sample project
- Verify component rendering by starting the sample project server and making requests
- Check that import paths in `src/django_components/__init__.py` work correctly

### CI/CD Information  
- GitHub Actions workflow: `.github/workflows/tests.yml`
- Tests run on Python 3.8-3.13 with Django 4.2-5.2
- Includes Playwright browser testing (requires `playwright install chromium --with-deps`)
- Documentation building uses mkdocs
- Pre-commit hooks run black, isort, and flake8

### Time Expectations
- Installing dependencies: 1-2 minutes
- Running basic component tests: 5 seconds
- Running template tag tests (349 tests): 10 seconds  
- Running full test suite: 2-5 minutes. NEVER CANCEL: Set timeout to 10+ minutes
- Playwright browser install: 10+ minutes. NEVER CANCEL: Set timeout to 15+ minutes
- Tox full test matrix: 10-30 minutes. NEVER CANCEL: Set timeout to 45+ minutes
- Package building: 2-5 minutes, may timeout on network issues

### Network Dependencies
- pip installations may timeout due to network issues (this is environment-specific)
- Playwright browser downloads may fail due to large file sizes
- All core functionality works without additional network access once dependencies are installed

### Development Workflow
1. Install dependencies: `pip install -r requirements-dev.txt && pip install -e .`
2. Make changes to source code in `src/django_components/`
3. Run tests: `python -m pytest tests/test_component.py` (or specific test files)
4. Run linting: `black src/django_components && isort src/django_components && flake8 .`
5. Test sample project: `cd sampleproject && python manage.py runserver`
6. Validate with curl: `curl http://127.0.0.1:8000/`
7. Run broader tests before final commit: `python -m pytest tests/test_templatetags*.py`