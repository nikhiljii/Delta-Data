# Releasing the CLI

The `deltadata` CLI ([PyPI](https://pypi.org/project/deltadata/)) ships
independently from the hosted engine/API — bumping the CLI's version never
requires a change to the private engine repo, and vice versa.

Routine publishing is designed to use
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OpenID
Connect), not a stored API token: pushing a `cli-v*` tag makes GitHub Actions
build the package and PyPI verify the workflow run directly. The initial
`0.1.x` releases were bootstrapped with a temporary token because the
account-side publisher identity did not match; that token must be revoked on
PyPI and deleted from Replit Secrets immediately after use. No PyPI token
belongs in the repository or long-lived workspace configuration.

## One-time setup for automated releases

The first `deltadata` release is live on PyPI. Future releases use a trusted
publisher, which a repo maintainer must register or verify on PyPI with these
exact values:

- Project name: `deltadata`
- Repository owner: `nikhiljii`
- Repository name: `Delta-Data`
- Workflow filename: `publish-cli.yml` (filename only)
- Environment name: `pypi`

The initial automated attempts returned `invalid-publisher`, so this
account-side entry still needs verification before the next tag release.
Check the saved entry under "Pending publishers" on the PyPI account page.
Once verified, the setup only needs attention again if the repository, workflow
filename, or environment changes.

## Cutting a release

1. Update the version in `cli/deltadata_cli/__init__.py`
   (`__version__ = "X.Y.Z"`) — this is the single source of truth;
   `pyproject.toml` reads it dynamically, so there is nowhere else to bump.
2. Add a new section to `cli/CHANGELOG.md` under the new version, moving
   anything from `[Unreleased]`.
3. Run the checks locally:
   ```bash
   cd cli
   pip install -e .
   pytest tests/
   python -m build
   twine check dist/*
   ```
4. Commit (`git commit -am "Release deltadata vX.Y.Z"`), merge to `main`,
   then tag and push:
   ```bash
   git tag cli-vX.Y.Z
   git push origin cli-vX.Y.Z
   ```
5. Pushing the tag triggers `.github/workflows/publish-cli.yml`, which
   builds the sdist/wheel and publishes them to PyPI. Watch the Actions run;
   the job also verifies the tag version matches
   `deltadata_cli.__version__` and fails fast if they've drifted.
6. Once the run succeeds, confirm with `pip install --upgrade deltadata`
   (or check https://pypi.org/project/deltadata/#history) and cut a GitHub
   Release from the tag with the matching CHANGELOG section as notes.

## Versioning policy

The CLI follows [Semantic Versioning](https://semver.org/):

- **Patch** (`0.1.x`) — bug fixes, doc-only changes, no behavior change.
- **Minor** (`0.x.0`) — new flags or output fields, additive and
  backward-compatible.
- **Major** — breaking changes to flags, output shape, or exit codes.
  Pre-1.0, minor bumps may still include small breaking changes; this will
  tighten once the CLI reaches `1.0.0`.

Exit codes (`0`/`1`/`2`/`3`, documented in the root README and
`cli/README.md`) are part of the CLI's public contract — changing their
meaning is always a breaking change.
