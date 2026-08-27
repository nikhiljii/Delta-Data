# Security Policy

## Reporting a vulnerability

If you find a security issue in the DeltaData CLI, the documented GitHub
Action, or the public API contract described in this repository, please
report it privately rather than opening a public issue.

- Use GitHub's [private vulnerability reporting](../../security/advisories/new)
  for this repository, or
- Contact the maintainer directly through the channel listed on the
  [hosted demo](https://delta-data.replit.app/).

Please include:
- A description of the issue and its potential impact
- Steps to reproduce (a minimal `before.sql`/`after.sql`/CSV repro is ideal)
- The CLI version or commit you tested against

We aim to acknowledge reports within a few business days. Please give us a
reasonable window to address the issue before any public disclosure.

## Please do not

- **Do not post API keys, tokens, credentials, or real customer/company data
  in issues, pull requests, or discussions** — even when reporting a bug.
  Redact request/response payloads before sharing them.
- Do not attempt to load-test or brute-force the hosted demo API; if you
  need to test rate limits or abuse handling, ask first.

## Scope

This repository publishes the DeltaData **CLI**, **examples**, and
**documentation** for the public API contract. The analysis engine and web
application run as a separately operated, closed-source service — if your
report concerns the hosted service's infrastructure rather than the CLI or
documented API contract, please still report it privately using the channels
above; we'll route it internally.
