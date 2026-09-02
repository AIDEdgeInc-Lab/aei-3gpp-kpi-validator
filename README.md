# aei-3gpp-kpi-validator

[![PyPI version](https://img.shields.io/pypi/v/aei-3gpp-kpi-validator.svg)](https://pypi.org/project/aei-3gpp-kpi-validator/)
[![Python versions](https://img.shields.io/pypi/pyversions/aei-3gpp-kpi-validator.svg)](https://pypi.org/project/aei-3gpp-kpi-validator/)
[![License](https://img.shields.io/pypi/l/aei-3gpp-kpi-validator.svg)](https://github.com/AIDEdgeInc-Lab/aei-3gpp-kpi-validator/blob/main/LICENSE)
[![CI](https://github.com/AIDEdgeInc-Lab/aei-3gpp-kpi-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/AIDEdgeInc-Lab/aei-3gpp-kpi-validator/actions/workflows/ci.yml)

A dependency-light Python validator for real 3GPP-standard telecom KPIs.
Range-checks RSRP, RSRQ, and SINR against their standards-derived valid
ranges, plus two KPI-specific predicate gates (handover quality, NB-IoT
power profile) - each citing the actual 3GPP TS number and section it comes
from. Built on pandas + pydantic + PyYAML; Dask is an optional accelerated
path, not a requirement.

**Status: private, pre-release.** This repository exists at
`AIDEdgeInc-Lab/aei-3gpp-kpi-validator` but is not yet public and not yet
published to PyPI - PyPI Trusted Publishing has not been configured. This
README describes the package as it is intended to work; see
`docs/PUBLISHING.md` for exactly what publishing step remains and its
current (not-yet-done) status.

## Why this exists

Most public "telecom KPI" tooling either doesn't cite a standard at all, or
implies far more standards coverage than it actually implements. This
project does the opposite on purpose: everything it validates is tied to a
real 3GPP TS number and section (see the table below), and everything it
does *not* implement is listed explicitly in "What this deliberately does
not do," rather than silently absent.

This project is separate from, and does not include, any part of AID Edge
Inc.'s proprietary Velorona telecom and decision-intelligence capabilities.
It contains only standards-derived range validation - no degradation
scoring, no detection logic, no customer- or deployment-specific
thresholds of any kind.

## Who this is for

Telecom data engineers, RF/network engineers, and data scientists working
with LTE/5G KPI data who need a lightweight, standards-cited sanity check
before analytics or model training - not a full network-management-system
replacement.

Useful for:

- Range-validating RSRP/RSRQ/SINR columns in a pandas (or optionally Dask)
  DataFrame before feeding them into a pipeline.
- Gating rows on TS 36.331-derived handover-quality timing and TS
  36.213-derived NB-IoT power-saving parameters.
- A starting point for teams who want KPI validation logic they can read,
  audit, and extend themselves, rather than a black-box service.

## Example use cases

- Pre-training data-quality gate for an ML pipeline consuming LTE/5G KPI
  exports.
- Catching malformed or out-of-spec RSRP/RSRQ/SINR values in an ETL job
  before they reach a dashboard.
- Filtering handover or NB-IoT power-saving event logs to standards-valid
  rows for further analysis.
- A citeable, inspectable reference for what "RSRP is out of range" or
  "handover passed the quality gate" actually means, per spec.

## Install

```bash
pip install aei-3gpp-kpi-validator
```

Optional extras:

```bash
pip install "aei-3gpp-kpi-validator[dask]"      # Dask-accelerated validation path
pip install "aei-3gpp-kpi-validator[metrics]"   # Prometheus metrics adapter
```

## Quick start

```python
import pandas as pd
from aei_3gpp_kpi_validator import KPIValidator

validator = KPIValidator()

df = pd.DataFrame({"rsrp": [-145.0, -100.0, -50.0, -40.0]})
outcome = validator.validate_column(df, "rsrp")

print(outcome.out_of_range_count)
# 2  (-145.0 is below -140 dBm min; -40.0 is above -44 dBm max)
print(outcome.validated.tolist())
# [-140.0, -100.0, -50.0, -44.0]  (clipped to the TS 36.214 valid range)
```

See `examples/basic_usage.py` for a complete, runnable example including
the handover and NB-IoT gates.

## What is implemented

| KPI | 3GPP reference | Range | Units |
|---|---|---|---|
| RSRP | TS 36.214, Section 5.1 | -140 to -44 | dBm |
| RSRQ | TS 36.214, Section 5.1 | -20 to -3 | dB |
| SINR | TS 38.214, Section 5.1 | -20 to 30 | dB |
| Handover Quality | TS 36.331, Section 5.5 | 0 to 100 | percentage |
| NB-IoT Power | TS 36.213, Section 15.2 | 0 to 262144 | cycle |

`validate_handover(df)` enforces `ho_preparation_time < 50 & ho_execution_time < 20`
(TS 36.331-derived thresholds). `validate_nbiot_power_profile(df)` enforces
`paging_cycle <= 256 & edrx_cycle <= 262144` (TS 36.213 §15.2 eDRX
cycle-length ceiling, 262144 = 2^18 radio frames). Both run on plain
pandas by default; Dask is an optional accelerated path using the
identical predicate string for both backends - see `tests/test_validator.py`'s
`*_pandas_dask_parity` tests, which assert the two backends produce
identical validation decisions on the same input.

## What this deliberately does not do

**CQI mapping, RedCap, Ambient IoT, Outage/Latency, IoT Security/SUCI, and
PTCRB/GCF certification alignment are not implemented, claimed, or
referenced anywhere in this library.** These were considered during
development and explicitly excluded rather than half-built:

- **CQI mapping** (TS 38.214 §7.1.7.1) - not implemented here. If you need
  a CQI-shaped value, be aware that many "CQI calculator" implementations
  in the wild (including an earlier internal prototype this project's
  authors are aware of) borrow the CQI name and a 1-15 numeric range
  without implementing the actual 3GPP CQI table (modulation scheme, code
  rate, spectral efficiency per index). This library makes no CQI claim of
  any kind rather than risk that same mistake.
- **RedCap** - a genuine 3GPP RedCap reference exists (TR 38.875, "Study
  on support of reduced capability NR devices," Release 17), but it is not
  implemented in this library. If you rely on TR 38.888 from some other
  source for RedCap, note that TR 38.888 is actually titled "Adding wider
  channel bandwidth in NR band n28" - unrelated to RedCap - so double-check
  any RedCap reference against the [official 3GPP specification portal](https://portal.3gpp.org)
  before relying on it.
- **Ambient IoT** (TR 22.840 / TR 38.848) - not implemented.
- **Outage/Latency KPIs** (TS 28.552 / TS 23.503) - not implemented.
- **IoT Security/SUCI** (TS 33.501 / ETSI TS 103 457) - not implemented.
- **PTCRB/GCF certification alignment** - not implemented. This library
  makes no certification or compliance claim of any kind.

This library also does not include, and never has: Kafka/DLQ messaging,
Vault or other encrypted-config loading, circuit-breaker/retry logic,
FastAPI serving endpoints, or STL-based anomaly detection. These are
generic infrastructure or statistics concerns, not 3GPP standards logic,
and are out of scope for what this library is for.

No "production-ready," "enterprise-grade," "FIPS," "SOC 2," or
"GDPR-compliant" claim is made anywhere in this project. If you need any
of those properties, they must come from your own deployment, not from
this library.

## Public API

| Function / value | Purpose |
|---|---|
| `KPIValidator(config_path=...)` | Loads YAML KPI configs and validates DataFrame columns against them. |
| `KPIValidator.validate_column(df, kpi_name, data_source="unknown")` | Range-clip validation against the KPI's configured min/max. Returns a `ValidationOutcome`. |
| `KPIValidator.validate_handover(df)` | TS 36.331 handover-quality gate. Pandas by default, Dask-accelerated if given a Dask DataFrame. |
| `KPIValidator.validate_nbiot_power_profile(df)` | TS 36.213 §15.2 NB-IoT power-saving gate. Pandas by default, Dask-accelerated if given a Dask DataFrame. |
| `ValidationOutcome` | Dataclass: `kpi_name`, `data_source`, `gpp3_version`, `validated`, `out_of_range_count`, `latency_seconds`. |
| `KPIStandard`, `Standard`, `ValidRange` | Pydantic schema for a KPI's standards metadata and valid range - the shape every shipped YAML config follows. |
| `ConfigurationError` | Raised for KPI configuration load/schema errors. |
| `aei_3gpp_kpi_validator.metrics.KPIMetricsAdapter` | Optional, explicit Prometheus adapter - not imported by the package `__init__`, so importing the package never pulls in `prometheus_client`. Takes an injected `CollectorRegistry`; registration is idempotent per registry. |

## Dependencies

Runtime (hard): `pandas`, `pydantic`, `pyyaml`. Optional: `dask[dataframe]`
(accelerates `validate_handover`/`validate_nbiot_power_profile` and
`validate_column`'s clip step on large datasets - imported in a
`try/except ImportError` guard and falls back to pandas-only behavior when
absent); `prometheus-client` (only if you import
`aei_3gpp_kpi_validator.metrics` explicitly). See `CHANGELOG.md` for the
full dependency and license audit.

This library makes no network calls and reads no environment variables -
see `tests/test_package_hygiene.py`.

## Security

See `SECURITY.md` for supported versions and how to report a vulnerability
privately. See `docs/PUBLISHING.md` for the release process this project
is designed to use once published: PyPI Trusted Publishing with OIDC and
no stored API token. **That registration has not been done yet** - there
is no PyPI project for this package today.

## Contributing

See `CONTRIBUTING.md`.

## License

Apache License 2.0 - see `LICENSE`.

Copyright 2026 AID Edge Inc.
