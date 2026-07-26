# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

Instead, email the maintainer at **[security@example.com]** with:

- A description of the vulnerability
- Steps to reproduce
- The potential impact
- Any suggested remediation

You can expect an acknowledgement within a reasonable timeframe. Please allow
time for a fix to be prepared before any public disclosure.

## Important Notice

This project is a **portfolio / educational demonstration**. It is **not
hardened for production use** out of the box. Before deploying it in any
environment that handles real personal data:

- Supply your **own** credentials and secrets via a local `.env` file — never
  commit secrets to version control.
- Rotate and revoke any credentials that may have been exposed during
  development.
- Ensure compliance with applicable data-protection regulations, including
  India's **Digital Personal Data Protection (DPDP) Act, 2023**.
- Review authentication, authorization, input validation, and rate limiting.
- All sample data included in this repository is **synthetic** and does not
  represent any real individual.

## Scope

| In Scope                                | Out of Scope                          |
|-----------------------------------------|---------------------------------------|
| Code in this repository                 | Third-party services (Twilio, Google) |
| Default configuration and dependencies  | Your own deployment infrastructure    |
| Documented API endpoints                | Issues requiring committed real secrets |

## Supported Versions

This project is provided as-is. Security fixes, if any, are applied to the
`main` branch only.
