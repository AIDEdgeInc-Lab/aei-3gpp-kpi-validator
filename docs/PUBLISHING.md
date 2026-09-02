# Publishing process

**This repository exists (`AIDEdgeInc-Lab/aei-3gpp-kpi-validator`) but is
private, and nothing has been published to PyPI.** This document describes
the intended process, mirrored from `aei-geo-features`' publishing setup,
for when going public and a PyPI release are separately approved.

## How a release would be published

- **Normal path**: a maintainer publishes a GitHub Release. This fires
  the workflow's `release: published` trigger, which builds the wheel/
  sdist and publishes them to production PyPI (`environment: pypi`).
- **Manual path**: the workflow can also be run manually via
  `workflow_dispatch` with a `target` input of `testpypi` (default) or
  `pypi`. A manual run always requires `target` to be chosen explicitly;
  `pypi` is never the default.

Both paths run through the same `build` job first, and both publish
jobs are mutually exclusive - only one of `publish-testpypi` /
`publish-pypi` ever runs for a given trigger.

## Why Trusted Publishing instead of a token

PyPI Trusted Publishing lets a specific GitHub Actions workflow
(identified by repo, workflow filename, and environment) request a
short-lived upload credential directly from PyPI via OpenID Connect (OIDC)
at publish time. There is no long-lived `PYPI_API_TOKEN` secret to create,
rotate, store in GitHub Secrets, or accidentally leak in a log.

## Trusted Publisher registration (not yet done)

Needs to be registered as a Trusted Publisher on both pypi.org and
test.pypi.org, tied to this repository, the `publish.yml` workflow
filename, and the `pypi`/`testpypi` environments respectively. That
registration happens on PyPI's own site (Account Settings -> Publishing),
not in this repository. **Not done yet.** Do not treat this as done, and
do not update this section to say it's done, until someone has actually
completed that registration on pypi.org/test.pypi.org and verified it -
this file should never silently mark it complete.

## Current state

- **The GitHub repository exists** (`AIDEdgeInc-Lab/aei-3gpp-kpi-validator`)
  but is **private**, not public.
- No PyPI project exists yet.
- No Trusted Publisher relationship is configured.
- `.github/workflows/publish.yml` is present in this repository but has
  never run - it has no `push`/`pull_request` trigger, so it cannot fire
  by accident.
- `ci.yml` and `codeql.yml` run on push/PR against this repository and
  validate the wheel/sdist build; neither publishes anywhere.
