# Contributing to DB Clone Tool

Thank you for your interest in contributing to DB Clone Tool! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/melihcelenk/db-clone-tool.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit your changes: `git commit -m "Add feature: description"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Run with coverage:
```bash
pytest --cov=src.db_clone_tool --cov-report=html
```

4. Format code:
```bash
black src/ tests/
```

5. Lint code:
```bash
flake8 src/ tests/
```

## Coding Standards

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Keep functions small and focused
- Write tests for new features
- Update documentation as needed

## Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Use descriptive test names

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Reference issue numbers if applicable

Example:
```
Add support for PostgreSQL connections
Fix schema size calculation for large databases
Update README with installation instructions
```

## Pull Request Process

1. Update README.md if needed
2. Update CHANGELOG.md with your changes
3. Ensure all tests pass
4. Ensure code follows style guidelines
5. Request review from maintainers

## Reporting Bugs

When reporting bugs, please include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)
- Error messages or logs

## Suggesting Features

When suggesting features, please include:
- Use case description
- Proposed solution
- Alternatives considered
- Additional context

## Questions?

Feel free to open an issue for any questions or concerns.

Thank you for contributing!
