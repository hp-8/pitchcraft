# Security Policy

## Supported versions

The project is under active development. Security fixes target the `main` branch.

## Reporting a vulnerability

If you discover a security issue, please email `security@harshpatadia.space` with:

- A clear description of the issue.
- Steps to reproduce.
- The potential impact (data exposure, privilege escalation, etc.).

Please do not open a public issue or pull request for security related findings until the maintainer has had a chance to triage.

## What counts as a security issue

- Anything that could leak lead data, generated outputs, or credentials from a user's environment to a public surface (logs, deployed sites, the repo itself).
- Anything that could let a third party hijack a user's pipeline (token leakage in environment, SSRF in scraping, etc.).
- Anything that affects supply chain integrity (compromised dependencies, malicious config samples).

## Response

You can expect an initial response within 5 working days. We will work with you to validate the issue, ship a fix, and credit you in the release notes if you wish.
