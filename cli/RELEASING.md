# Releasing the CLI

The `deltadata` CLI ([PyPI](https://pypi.org/project/deltadata/)) ships
independently from the hosted engine/API — bumping the CLI's version never
requires a change to the private engine repo, and vice versa.

Publishing uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OpenID Connect), not a stored API token: pushing a `cli-v*` tag makes
GitHub Actions build the package and PyPI verifies the workflow run
directly. No PyPI secret exists in this repo.

## One-time setup (already done for this repo)

A repo maintainer registered a trusted publisher on PyPI for the `deltadata`
project, pointing at:

- Repository owner/name: `nikhiljii/Delta-Data`
- Workflow filename: `.github/workflows/publish-cli.yml`
- Environment name: `pypi`

This only needs to be done once (or again if the workflow file is renamed
or moved). See PyPI's "Publishing" settings under the project, or
"Pending publishers" on the account page if the project doesn't exist on
PyPI yet.

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
