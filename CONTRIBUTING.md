# Contributing to 3D Print CAD Assistant

Thank you for your interest in contributing to the 3D Print CAD Assistant project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- Be respectful and considerate in all interactions
- Welcome diverse perspectives and experiences
- Focus on constructive feedback
- Assume good intentions
- Report unacceptable behavior to project maintainers

## Getting Started

### Prerequisites

- Python 3.9+ (3.11 recommended)
- Git for version control
- Basic understanding of 3D printing concepts
- Familiarity with mesh processing and CAD principles

### Finding Ways to Contribute

- **Bug Reports**: Submit detailed bug reports with reproduction steps
- **Feature Requests**: Propose new features with use cases
- **Code Contributions**: Fix bugs, implement features, improve performance
- **Documentation**: Improve guides, add examples, fix typos
- **Testing**: Add test coverage, improve test quality
- **Translations**: Help translate UI and documentation (English ↔ Japanese)

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/3DprintCAD.git
cd 3DprintCAD
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements_dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Create Development Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Contribution Workflow

### 1. Make Changes

- Keep changes focused and atomic
- Follow existing code patterns
- Write clear, self-documenting code
- Add comments for complex logic

### 2. Write Tests

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_mesh_validator.py -v
```

### 3. Ensure Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Security scan
bandit -r src/
```

### 4. Update Documentation

- Update relevant documentation files
- Add docstrings to new functions/classes
- Update API documentation if needed
- Add examples for new features

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

```python
# Line length: 100 characters (configured in pyproject.toml)
# Use Black for formatting
# Use type hints where appropriate

def validate_mesh(
    mesh_path: Path,
    min_wall_thickness: float = 0.4,
    check_manifold: bool = True
) -> ValidationResult:
    """
    Validate 3D mesh for printability.

    Args:
        mesh_path: Path to mesh file
        min_wall_thickness: Minimum wall thickness in mm
        check_manifold: Whether to check manifold properties

    Returns:
        ValidationResult containing validation status and issues

    Raises:
        FileNotFoundError: If mesh file doesn't exist
        ValueError: If mesh format is unsupported
    """
    pass
```

### Key Conventions

- **Naming**:
  - Classes: `PascalCase` (e.g., `MeshValidator`)
  - Functions/variables: `snake_case` (e.g., `validate_mesh`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
  - Private members: prefix with `_` (e.g., `_internal_helper`)

- **Imports**:
  ```python
  # Standard library
  import os
  from pathlib import Path

  # Third-party
  import numpy as np
  import trimesh

  # Local
  from ..core.analysis import mesh_validator
  ```

- **Error Handling**:
  ```python
  # Use specific exceptions
  raise ValueError(f"Invalid mesh format: {format}")

  # Provide context in error messages
  try:
      mesh = load_mesh(path)
  except Exception as e:
      logger.error(f"Failed to load mesh from {path}: {e}")
      raise
  ```

### Security Requirements

- **Never hardcode secrets** - use environment variables
- **Validate all inputs** - sanitize file paths, validate data
- **Use parameterized queries** - prevent SQL injection
- **Sanitize output** - prevent XSS in web interface
- **Check file permissions** - ensure proper access controls
- **Log security events** - track authentication, authorization

## Testing Requirements

### Test Coverage

- Aim for >80% code coverage
- All new features must include tests
- Bug fixes should include regression tests

### Test Types

```python
# Unit tests - test individual functions
def test_calculate_volume():
    mesh = create_test_cube(size=10)
    assert abs(calculate_volume(mesh) - 1000.0) < 0.1

# Integration tests - test component interactions
def test_mesh_validation_pipeline():
    result = validate_mesh("test_model.stl")
    assert result.is_valid
    assert len(result.warnings) == 0

# End-to-end tests - test complete workflows
def test_cli_batch_processing():
    output = run_cli(["--batch", "models/*.stl"])
    assert output.return_code == 0
    assert "processed 5 files" in output.stdout
```

### Running Tests

```bash
# All tests
make test

# With coverage report
make coverage

# Specific test file
pytest tests/test_mesh_validator.py -v

# Specific test function
pytest tests/test_mesh_validator.py::test_manifold_detection -v

# Parallel execution
pytest tests/ -n auto
```

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def optimize_mesh(
    mesh: trimesh.Trimesh,
    target_faces: int = 10000,
    preserve_topology: bool = True
) -> trimesh.Trimesh:
    """
    Optimize mesh by reducing face count while preserving quality.

    This function uses quadric error metrics to intelligently reduce
    the polygon count while maintaining visual fidelity and topology.

    Args:
        mesh: Input mesh to optimize
        target_faces: Target number of faces after optimization
        preserve_topology: If True, maintains original topology

    Returns:
        Optimized mesh with reduced face count

    Raises:
        ValueError: If target_faces is negative or zero

    Example:
        >>> mesh = trimesh.load("model.stl")
        >>> optimized = optimize_mesh(mesh, target_faces=5000)
        >>> print(f"Reduced from {len(mesh.faces)} to {len(optimized.faces)}")
    """
    pass
```

### Documentation Files

Update relevant files when making changes:

- `README.md` - High-level overview and quick start
- `docs/USER_GUIDE.md` - User-facing documentation
- `docs/API.md` - API reference documentation
- `docs/DEVELOPMENT.md` - Development guide
- `CHANGELOG.md` - Document changes in each version

## Submitting Changes

### Commit Guidelines

```bash
# Use conventional commits format
# Type: feat, fix, docs, style, refactor, test, chore

git commit -m "feat: Add support for 3MF file format"
git commit -m "fix: Correct volume calculation for non-manifold meshes"
git commit -m "docs: Update API documentation for mesh validator"
git commit -m "test: Add integration tests for batch processing"
```

### Pull Request Process

1. **Update Your Branch**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Use descriptive title
   - Reference related issues (#123)
   - Provide detailed description
   - Include screenshots for UI changes
   - List breaking changes if any

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No new warnings generated
```

## Review Process

### What Reviewers Look For

- **Correctness**: Does the code work as intended?
- **Quality**: Is the code clean, readable, and maintainable?
- **Testing**: Are there adequate tests with good coverage?
- **Security**: Are there any security vulnerabilities?
- **Performance**: Are there performance implications?
- **Documentation**: Is the change properly documented?

### Addressing Feedback

- Respond to all review comments
- Make requested changes in new commits
- Mark conversations as resolved when addressed
- Ask for clarification if feedback is unclear

### Approval and Merge

- At least one maintainer approval required
- All CI checks must pass
- No unresolved review comments
- Up-to-date with main branch
- Squash and merge for clean history

## Additional Resources

### Documentation

- [User Guide](docs/USER_GUIDE.md)
- [API Reference](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Security Policy](docs/SECURITY_HARDENING.md)

### Communication

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Security**: Report security issues privately to security@example.com

### Recognition

Contributors are recognized in:
- `CHANGELOG.md` for each release
- GitHub contributors list
- Special acknowledgment for significant contributions

Thank you for contributing to making 3D printing more accessible and reliable!
