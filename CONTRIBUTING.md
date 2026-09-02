# Contributing

Thanks for considering a contribution. This project is intentionally
narrow in scope - see README.md's "What is implemented" and "What this
deliberately does not do" sections before proposing a new feature.
Anything not tied to a real, cited 3GPP standard is likely out of scope
for this repository.

## Development setup

```bash
git clone <repository-url>
cd aei-3gpp-kpi-validator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Before opening a pull request

- Add or update tests for any behavior change, including a Dask parity
  test if the change touches `validate_handover`, `validate_nbiot_power_profile`,
  or `validate_column`'s Dask path.
- Any new KPI must cite a real 3GPP TS/TR number and section - no
  aspirational or unverified standards claims. If you're not certain a
  citation is correct, say so explicitly in the PR rather than asserting
  it.
- Do not add a new hard runtime dependency without discussion first - open
  an issue describing the use case. Dask and Prometheus support must stay
  optional.
- Run `pytest` locally; CI will also run it against all supported Python
  versions.

## Reporting bugs vs. reporting vulnerabilities

Functional bugs: open a GitHub issue.
Security vulnerabilities: see `SECURITY.md` - do not open a public issue.

## Code of conduct

Be respectful and constructive. Maintainers may close issues or PRs that
are off-topic, abusive, or outside this project's stated scope.
