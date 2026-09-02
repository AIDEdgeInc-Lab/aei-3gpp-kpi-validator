"""
Thin, explicit KPI-metrics adapter. This is the ONLY module in this package
that imports prometheus_client - validator.py has no observability
dependency at all.

Not imported by __init__.py by default: `from aei_3gpp_kpi_validator import
KPIValidator` never pulls in prometheus_client. Callers who want metrics
opt in explicitly with `from aei_3gpp_kpi_validator.metrics import
KPIMetricsAdapter`.

This adapter takes an already-constructed Prometheus registry via
dependency injection rather than assuming any particular observability
stack - bring your own registry.

Design note: this is an explicit adapter, not a decorator. It calls
KPIValidator.validate_column() itself and records the returned
ValidationOutcome - it does not wrap/decorate validate_column's definition.

Registration is idempotent per registry: constructing a second
KPIMetricsAdapter against the *same* registry instance reuses the existing
Counter/Histogram objects instead of raising prometheus_client's "Duplicated
timeseries" error - see
tests/test_metrics_adapter.py::test_two_adapters_share_the_same_registry_without_duplicate_registration_error.
This is scoped to whatever registry is passed in, never a hardcoded global.
"""
from typing import Optional

from prometheus_client import CollectorRegistry, Counter, Histogram

from aei_3gpp_kpi_validator.validator import KPIValidator, ValidationOutcome

_METRIC_PREFIX = "aei_kpi_"


def _get_or_create_collector(registry: CollectorRegistry, factory, name: str, *args, **kwargs):
    """Return the already-registered collector for `name` in `registry` if one
    exists, otherwise create it. Keeps metric registration idempotent per
    registry instance without any global state."""
    try:
        existing = registry._names_to_collectors.get(name)
        if existing is not None:
            return existing
    except AttributeError:
        for collector in registry.collect():
            if collector.name == name:
                return collector
    return factory(name, *args, registry=registry, **kwargs)


class KPIMetricsAdapter:
    """Explicit wrapper: calls a KPIValidator and records the outcome
    through an injected Prometheus registry."""

    def __init__(self, validator: KPIValidator, registry: Optional[CollectorRegistry] = None):
        self.validator = validator
        registry = registry if registry is not None else CollectorRegistry()
        self.registry = registry

        self.success_counter = _get_or_create_collector(
            registry, Counter,
            f"{_METRIC_PREFIX}validation_success_total",
            "Total successful KPI validations",
            ["kpi_name", "gpp3_version"],
        )
        self.failure_counter = _get_or_create_collector(
            registry, Counter,
            f"{_METRIC_PREFIX}validation_failure_total",
            "Total failed KPI validations",
            ["kpi_name", "error_type"],
        )
        self.latency_histogram = _get_or_create_collector(
            registry, Histogram,
            f"{_METRIC_PREFIX}validation_latency_seconds",
            "End-to-end validation latency",
            ["kpi_name", "data_source"],
        )

    def validate_and_record(self, df, kpi_name: str, data_source: str = "unknown") -> ValidationOutcome:
        outcome = self.validator.validate_column(df, kpi_name, data_source)

        if outcome.out_of_range_count > 0:
            self.failure_counter.labels(kpi_name=kpi_name, error_type="validation_error").inc(
                outcome.out_of_range_count
            )
        else:
            self.success_counter.labels(kpi_name=kpi_name, gpp3_version=outcome.gpp3_version).inc()

        self.latency_histogram.labels(kpi_name=kpi_name, data_source=data_source).observe(
            outcome.latency_seconds
        )
        return outcome
