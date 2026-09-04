# Changelog

All notable changes to this project are recorded here. This project is
published on PyPI: https://pypi.org/project/aei-3gpp-kpi-validator/.

## [0.1.1] - 2026-09-04

### Fixed

- Fix stale pre-publish status text in PyPI long_description (no
  functional change).

## [0.1.0] - 2026-09-02

### Added

- `KPIValidator` - loads YAML KPI configs and validates DataFrame columns
  against 3GPP standards-derived ranges (`validate_column`).
- `KPIValidator.validate_handover(df)` - TS 36.331 handover-quality gate.
- `KPIValidator.validate_nbiot_power_profile(df)` - TS 36.213 §15.2 NB-IoT
  power-saving gate.
- Five shipped KPI configs: RSRP (TS 36.214 §5.1), RSRQ (TS 36.214 §5.1),
  SINR (TS 38.214 §5.1), Handover Quality (TS 36.331 §5.5), NB-IoT Power
  (TS 36.213 §15.2).
- `ValidationOutcome`, `KPIStandard`/`Standard`/`ValidRange`,
  `ConfigurationError`.
- Optional `aei_3gpp_kpi_validator.metrics.KPIMetricsAdapter` - explicit,
  dependency-injected Prometheus adapter, not imported by default.
- Optional Dask-accelerated path for `validate_column`, `validate_handover`,
  and `validate_nbiot_power_profile` - both backends verified to produce
  identical validation decisions via parity tests.

### Provenance

Generalized from an internal, already-audited 3GPP standards-validation
module. The internal source module also contained substantial generic
infrastructure (Kafka DLQ, circuit-breaker/retry, FastAPI serving,
simulated Vault/encrypted-config loading, STL-based anomaly detection) that
was already excluded from the internal module before this package was
generalized from it - none of that infrastructure is standards logic, and
none of it is present here. See "Deliberately excluded from this package"
below for the full list and reasoning, ported directly from the internal
module's own deferred-capabilities record.

### Deliberately excluded from this package

- **CQI mapping** (TS 38.214 §7.1.7.1) - never implemented in the source
  material this package was generalized from. Not manufactured here.
- **RedCap, Ambient IoT, Outage/Latency, IoT Security/SUCI, PTCRB/GCF
  certification alignment** - documented as aspirational scope in the
  source material's own notes, but no corresponding code ever existed for
  any of them. None are implemented, claimed, or referenced here.
- **Kafka DLQ, circuit breaker/retry, FastAPI serving, simulated
  Vault/encrypted-config loading, STL-based anomaly detection** - generic
  infrastructure or statistics concerns, not 3GPP standards logic. Out of
  scope for this library by design, not by omission.
- **A multi-KPI convenience wrapper** (looping `validate_column` over a
  list of KPI names) - the source material's version claimed concurrency
  (imported `ThreadPoolExecutor`) but was actually a plain sequential loop.
  Not carried forward; every KPI it would have called is already available
  individually via `validate_column`, so no logic is lost, and a real
  multi-KPI entrypoint can be built trivially by callers if needed.

### Corrected during generalization

- The source material's KPI config YAML files used a **flat** schema
  (`name`/`version`/`table` at the top level) that did not actually match
  what `KPIStandard` requires (a nested `standard: {name, version, table}`
  block) - only the source's own test fixtures used the correct nested
  shape. The five configs shipped here use the nested schema, matching the
  model. `tests/test_models.py` proves every shipped config parses and
  that the old flat shape is correctly rejected.

## Dependency and license audit

| Package | Version range | Purpose | License | Mandatory? | Redistribution/patent concern | Lighter alternative? |
|---|---|---|---|---|---|---|
| `pandas` | `>=1.5,<3` | DataFrame input/output for all validation methods | BSD-3-Clause | Yes | None - permissive, widely redistributed | Rejected: DataFrame-oriented validation is this library's core value proposition |
| `pydantic` | `>=2.0,<3` | `KPIStandard`/`Standard`/`ValidRange` schema validation for KPI configs | MIT | Yes | None | A hand-rolled validator was considered; pydantic's clear error messages and existing test coverage were preferred |
| `pyyaml` | `>=6.0,<7` | Loading the shipped KPI config files | MIT | Yes | None | None needed; de facto standard for YAML in Python |
| `dask[dataframe]` | `>=2023.1,<2026` | Optional accelerated path for large datasets | BSD-3-Clause | No (optional extra) | None | Already optional; imported behind `try/except ImportError` in `validator.py` |
| `prometheus-client` | `>=0.16,<1` | Optional metrics adapter (`metrics.py`) | Apache-2.0 | No (optional extra) | None | Already optional; not imported by the package `__init__` |
| `pytest` | `>=7.4,<10` | Test runner | MIT | Dev-only | None | None needed; de facto standard |
| `build` | `>=1.0,<2` | PEP 517 build frontend, used in CI to build wheel/sdist | MIT | Dev-only | None | None needed |
| `twine` | `>=5.0,<8` | Package-metadata/README validation (`twine check`) in CI | Apache-2.0 | Dev-only | None | None needed |

No dependency copies third-party source code into this project. No
dependency was flagged with unclear or incompatible licensing. All five
runtime/optional dependencies use permissive licenses (BSD-3-Clause, MIT,
Apache-2.0), fully compatible with Apache 2.0 redistribution. Dev-only
tools never ship inside the built wheel/sdist - verified directly against
the built artifacts, not just declared in `pyproject.toml`.
