# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub Security Advisories ("Report a vulnerability" on the Security tab). Do not open a public issue with exploit details, credentials, or sensitive data. You can expect an acknowledgement within 7 days; this is a portfolio project maintained on a best-effort basis.

## Scope

In scope: the pipeline (`src/retail_ops`), the dashboard, the container image, and the CI configuration. Out of scope: findings that require real customer data (the project accepts synthetic data only) and the absence of production controls listed under "Known limitations".

## Supported versions

Only the latest commit on `main` is supported.

## Built-in safeguards

- All SQL values are bound as parameters; no SQL is built from user input.
- HTML exports escape every interpolated value.
- The container runs as a non-root user and ships no secrets; the database lives on a dedicated volume.
- CI runs CodeQL and `pip-audit` on runtime dependencies; Dependabot keeps dependencies and actions current.

## Known limitations

This project is not operated as a production service. It has no authentication, access control, encryption at rest, audit logging, or secret management, and the dashboard must not be exposed to untrusted networks with real data.
