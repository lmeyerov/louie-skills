# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| `main` | yes |

## Reporting a Vulnerability

Do not include secrets, exploit code, or sensitive details in a public issue. Instead, email `security@graphistry.com` with the impact, affected paths, reproduction steps, and suggested mitigation.

We aim to acknowledge reports within 48 hours and coordinate disclosure with the reporter when practical.

## Repository Safety

- Secret detection runs locally and in CI.
- Pull requests run with read-only repository contents permissions except CodeQL's required security-event upload permission.
- Workflow changes are linted and scanned with actionlint and zizmor.
- Enable GitHub secret scanning, push protection, Dependabot security updates, and code scanning in repository settings.
- Protect `main`: require pull requests and passing checks, and disallow force pushes and deletions.
