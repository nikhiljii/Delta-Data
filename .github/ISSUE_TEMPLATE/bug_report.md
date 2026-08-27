---
name: Bug report
about: Report a problem with the DeltaData CLI or documented API contract
title: "[Bug] "
labels: bug
---

**Do not include API keys, tokens, credentials, or real customer/company
data below.** Redact request/response payloads before pasting them. See
[SECURITY.md](../../SECURITY.md) for reporting actual security issues
privately.

## Describe the bug

A clear description of what went wrong.

## To reproduce

```bash
deltadata compare \
  --before before.sql \
  --after after.sql \
  --data orders.csv \
  --fail-on high
```

Attach a minimal `before.sql`/`after.sql`/CSV that reproduces the issue, if
possible (synthetic data only).

## Expected behavior

What you expected to happen.

## Actual behavior

What actually happened (exit code, error message, or `--json` output).

## Environment

- DeltaData CLI version / commit:
- OS:
- Python version:
