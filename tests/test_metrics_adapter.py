import pathlib

import pandas as pd
import pytest
from prometheus_client import CollectorRegistry

from aei_3gpp_kpi_validator.metrics import KPIMetricsAdapter
from aei_3gpp_kpi_validator.validator import KPIValidator

CONFIG_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "aei_3gpp_kpi_validator" / "config"


@pytest.fixture
def validator():
    return KPIValidator(config_path=str(CONFIG_DIR))


@pytest.fixture
def sample_pandas_data():
    df = pd.DataFrame({
        "rsrp": [-100.0, -50.0],
        "rsrq": [-10.0, -5.0],
        "cell_id": ["A1", "A2"],
    })
    df["rsrp"] = df["rsrp"].astype("float32")
    df["rsrq"] = df["rsrq"].astype("float32")
    df["cell_id"] = df["cell_id"].astype("category")
    return df


def test_adapter_uses_injected_registry_not_a_global_one(validator):
    """The adapter must not touch prometheus_client's default global REGISTRY -
    it only registers against whatever registry is passed in."""
    registry = CollectorRegistry()
    adapter = KPIMetricsAdapter(validator, registry=registry)
    # prometheus_client's Counter metric families are registered without the
    # trailing "_total" (that suffix is added only to the sample name).
    registered_names = {m.name for m in registry.collect()}
    assert "aei_kpi_validation_success" in registered_names


def test_adapter_defaults_to_a_fresh_registry_when_none_injected(validator):
    adapter = KPIMetricsAdapter(validator)
    assert adapter.success_counter is not None


def test_validate_and_record_increments_success_counter(validator, sample_pandas_data):
    registry = CollectorRegistry()
    adapter = KPIMetricsAdapter(validator, registry=registry)

    before = registry.get_sample_value(
        "aei_kpi_validation_success_total", {"kpi_name": "rsrp", "gpp3_version": "15.05.00"}
    ) or 0
    adapter.validate_and_record(sample_pandas_data, "rsrp")
    after = registry.get_sample_value(
        "aei_kpi_validation_success_total", {"kpi_name": "rsrp", "gpp3_version": "15.05.00"}
    )
    assert after == before + 1


def test_validate_and_record_increments_failure_counter_on_out_of_range(validator, sample_pandas_data):
    registry = CollectorRegistry()
    adapter = KPIMetricsAdapter(validator, registry=registry)

    invalid_data = sample_pandas_data.copy()
    invalid_data["rsrp"] = pd.array([-300.0, -400.0], dtype="float32")

    adapter.validate_and_record(invalid_data, "rsrp")
    after_failure = registry.get_sample_value(
        "aei_kpi_validation_failure_total", {"kpi_name": "rsrp", "error_type": "validation_error"}
    )
    assert after_failure == 2


def test_validate_and_record_observes_latency(validator, sample_pandas_data):
    registry = CollectorRegistry()
    adapter = KPIMetricsAdapter(validator, registry=registry)

    adapter.validate_and_record(sample_pandas_data, "rsrp", data_source="unit_test")
    count = registry.get_sample_value(
        "aei_kpi_validation_latency_seconds_count", {"kpi_name": "rsrp", "data_source": "unit_test"}
    )
    assert count == 1


def test_validate_and_record_returns_the_validation_outcome(validator, sample_pandas_data):
    adapter = KPIMetricsAdapter(validator, registry=CollectorRegistry())
    outcome = adapter.validate_and_record(sample_pandas_data, "rsrp")
    assert outcome.kpi_name == "rsrp"
    assert outcome.out_of_range_count == 0


def test_two_adapters_share_the_same_registry_without_duplicate_registration_error(validator):
    """Two independently-constructed KPIMetricsAdapter instances against the
    same registry must not raise prometheus_client's "Duplicated timeseries"
    ValueError, and must both observe each other's recordings."""
    registry = CollectorRegistry()

    adapter_one = KPIMetricsAdapter(validator, registry=registry)
    adapter_two = KPIMetricsAdapter(validator, registry=registry)  # must not raise

    assert adapter_one.success_counter is adapter_two.success_counter
    assert adapter_one.failure_counter is adapter_two.failure_counter
    assert adapter_one.latency_histogram is adapter_two.latency_histogram

    df = pd.DataFrame({
        "rsrp": [-100.0],
        "rsrq": [-10.0],
        "cell_id": ["A1"],
    })
    df["rsrp"] = df["rsrp"].astype("float32")
    df["rsrq"] = df["rsrq"].astype("float32")
    df["cell_id"] = df["cell_id"].astype("category")

    adapter_one.validate_and_record(df, "rsrp")
    after_first = registry.get_sample_value(
        "aei_kpi_validation_success_total", {"kpi_name": "rsrp", "gpp3_version": "15.05.00"}
    )
    adapter_two.validate_and_record(df, "rsrp")
    after_second = registry.get_sample_value(
        "aei_kpi_validation_success_total", {"kpi_name": "rsrp", "gpp3_version": "15.05.00"}
    )
    assert after_second == after_first + 1, (
        "adapter_two's recording did not land on the same counter as adapter_one - "
        "registration is not actually idempotent per registry"
    )


def test_adapters_with_different_registries_do_not_share_state(validator, sample_pandas_data):
    """Sanity check for the other direction: two adapters against two
    different registries must NOT share collectors or observed values."""
    registry_a = CollectorRegistry()
    registry_b = CollectorRegistry()

    adapter_a = KPIMetricsAdapter(validator, registry=registry_a)
    adapter_b = KPIMetricsAdapter(validator, registry=registry_b)

    assert adapter_a.success_counter is not adapter_b.success_counter

    adapter_a.validate_and_record(sample_pandas_data, "rsrp")
    value_in_b = registry_b.get_sample_value(
        "aei_kpi_validation_success_total", {"kpi_name": "rsrp", "gpp3_version": "15.05.00"}
    )
    assert value_in_b is None, "recording against registry_a leaked into registry_b"
