# Contributing to FarmerVerify AI

Thank you for your interest in contributing! This document outlines how to get
started and the standards we expect.

## Getting Started

1. **Fork** the repository and **clone** your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy the example environment file and fill in your **own** credentials:
   ```bash
   cp .env.example .env
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Data Privacy

- **Never commit real personal data.** All sample data must be synthetic.
- **Never commit secrets, API keys, tokens, or credentials.** Use `.env`
  (which is git-ignored) for all sensitive configuration.
- Do not include real names, phone numbers, Aadhaar numbers, bank details, or
  any personally identifiable information in code, tests, or documentation.
- If you find any real PII or credentials in the repository, report it via the
  process described in [SECURITY.md](SECURITY.md).

## Code Standards

- Follow **PEP 8** for Python code.
- Write clear, self-documenting code; add comments only where intent is not
  obvious.
- Keep functions focused and avoid unnecessary abstractions.
- Match the existing style and structure of the surrounding code.
- Add or update tests for any behavior you change.

## Pull Request Requirements

Before opening a PR, please ensure:

- [ ] Your branch is up to date with `main`.
- [ ] All tests pass locally.
- [ ] No secrets, credentials, or real PII are included.
- [ ] New code includes appropriate tests.
- [ ] The PR description clearly explains **what** changed and **why**.
- [ ] Linting passes and there are no obvious style violations.

## Reporting Issues

- Use **GitHub Issues** for bugs and feature requests.
- Use the process in [SECURITY.md](SECURITY.md) for security vulnerabilities —
  do **not** file those as public issues.

Thank you for helping improve this project!
