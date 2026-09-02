import pathlib

import pandas as pd
import pytest

from aei_3gpp_kpi_validator.validator import ConfigurationError, KPIValidator, ValidationOutcome

CONFIG_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "aei_3gpp_kpi_validator" / "config"


@pytest.fixture
def validator():
    return KPIValidator(config_path=str(CONFIG_DIR))


@pytest.fixture
def sample_pandas_data():
    df = pd.DataFrame({
        "rsrp": [-145.0, -100.0, -50.0, -40.0],
        "rsrq": [-22.0, -10.0, -5.0, -2.0],
        "cell_id": ["A1", "A2", "B1", "B2"],
    })
    df["rsrp"] = df["rsrp"].astype("float32")
    df["rsrq"] = df["rsrq"].astype("float32")
    df["cell_id"] = df["cell_id"].astype("category")
    return df


# --- Config loading ---

def test_load_kpi_config_success(validator):
    validator.load_kpi_config("rsrp")
    assert "rsrp" in validator.rules
    assert validator.rules["rsrp"]["standard"]["name"] == "TS 36.214"
    assert validator.rules["rsrp"]["valid_range"]["min"] == -140


def test_load_kpi_config_not_found(validator):
    with pytest.raises(FileNotFoundError):
        validator.load_kpi_config("nonexistent_kpi")


def test_corrupted_config_file(tmp_path):
    bad_file = tmp_path / "bad.yml"
    bad_file.write_text("bad::yaml::config:")
    v = KPIValidator(config_path=str(tmp_path))
    with pytest.raises(ConfigurationError):
        v.load_kpi_config("bad")


# --- validate_column (range/clip) ---

def test_validate_column_pandas(validator, sample_pandas_data):
    outcome = validator.validate_column(sample_pandas_data, "rsrp")
    assert isinstance(outcome, ValidationOutcome)
    assert outcome.validated.min() >= -140
    assert outcome.validated.max() <= -44
    # -145.0 is below -140 (min) and -40.0 is above -44 (max): 2 out-of-range records
    assert outcome.out_of_range_count == 2
    assert outcome.gpp3_version == "15.05.00"


def test_validate_column_dask(validator, sample_pandas_data):
    dask = pytest.importorskip("dask")
    import dask.dataframe as dd

    ddf = dd.from_pandas(sample_pandas_data, npartitions=2)
    outcome = validator.validate_column(ddf, "rsrp")
    validated = outcome.validated.compute()
    assert validated.min() >= -140
    assert validated.max() <= -44
    assert outcome.out_of_range_count == 2


# --- validate_handover ---

def test_validate_handover_pandas(validator):
    df = pd.DataFrame({
        "ho_preparation_time": [10, 60, 45, 49],
        "ho_execution_time": [5, 25, 19, 19],
    })
    result = validator.validate_handover(df)
    # rows 0 (10,5) and 2 (45,19) and 3 (49,19) pass; row 1 (60,25) fails both
    assert len(result) == 3
    assert (result["ho_preparation_time"] < 50).all()
    assert (result["ho_execution_time"] < 20).all()


def test_validate_handover_missing_columns(validator):
    df = pd.DataFrame({"unrelated_column": [1, 2, 3]})
    result = validator.validate_handover(df)
    # missing required columns -> validator returns df unchanged, does not raise
    assert result is df


def test_validate_handover_pandas_dask_parity(validator):
    """Same input dataset, both backends, identical validation decisions."""
    dask = pytest.importorskip("dask")
    import dask.dataframe as dd

    df = pd.DataFrame({
        "ho_preparation_time": [10, 60, 45, 49, 50, 0],
        "ho_execution_time": [5, 25, 19, 19, 20, 19],
    })
    pandas_result = validator.validate_handover(df).reset_index(drop=True)

    ddf = dd.from_pandas(df, npartitions=2)
    dask_result = validator.validate_handover(ddf).compute().reset_index(drop=True)

    assert len(pandas_result) == len(dask_result), "summary counts diverge between backends"
    pd.testing.assert_frame_equal(pandas_result, dask_result)


# --- validate_nbiot_power_profile ---

def test_validate_nbiot_power_profile_pandas(validator):
    df = pd.DataFrame({
        "paging_cycle": [100, 300, 256, 257],
        "edrx_cycle": [200000, 100000, 262144, 262145],
    })
    result = validator.validate_nbiot_power_profile(df)
    # row 0 (100, 200000) passes; row 1 fails paging_cycle; row 2 (256, 262144) passes (inclusive);
    # row 3 fails both (257 > 256, 262145 > 262144)
    assert len(result) == 2
    assert (result["paging_cycle"] <= 256).all()
    assert (result["edrx_cycle"] <= 262144).all()


def test_validate_nbiot_power_profile_pandas_dask_parity(validator):
    """Same input dataset, both backends, identical validation decisions,
    including the inclusive-boundary cases (256/262144 must pass, 257/262145 must not)."""
    dask = pytest.importorskip("dask")
    import dask.dataframe as dd

    df = pd.DataFrame({
        "paging_cycle": [100, 300, 256, 257, 0, 256],
        "edrx_cycle": [200000, 100000, 262144, 262145, 0, 262145],
    })
    pandas_result = validator.validate_nbiot_power_profile(df).reset_index(drop=True)

    ddf = dd.from_pandas(df, npartitions=2)
    dask_result = validator.validate_nbiot_power_profile(ddf).compute().reset_index(drop=True)

    assert len(pandas_result) == len(dask_result), "summary counts diverge between backends"
    pd.testing.assert_frame_equal(pandas_result, dask_result)


# --- schema validation ---

def test_validate_column_missing_target_column_raises(validator):
    """The KPI's own column is genuinely required."""
    df = pd.DataFrame({"unrelated_column": [1, 2, 3]})
    with pytest.raises(ValueError):
        validator.validate_column(df, "rsrp")


def test_validate_column_does_not_require_unrelated_kpi_columns(validator):
    """Validating one KPI must not require another KPI's columns. Validating
    'sinr' must succeed with only a 'sinr' column present."""
    df = pd.DataFrame({"sinr": [10.0, 20.0]})
    outcome = validator.validate_column(df, "sinr")
    assert outcome.kpi_name == "sinr"
    assert "rsrp" not in df.columns
    assert "cell_id" not in df.columns


@pytest.mark.parametrize("kpi_name,values,expected_min,expected_max", [
    ("rsrp", [-145.0, -100.0, -40.0], -140, -44),
    ("rsrq", [-25.0, -10.0, 0.0], -20, -3),
    ("sinr", [-25.0, 0.0, 35.0], -20, 30),
])
def test_validate_column_minimum_schema_per_kpi(validator, kpi_name, values, expected_min, expected_max):
    """Independent proof that rsrp, rsrq, and sinr each validate correctly
    using the minimum valid input schema for that KPI alone - a single-column
    DataFrame containing only that KPI's own data, nothing else."""
    df = pd.DataFrame({kpi_name: values})
    outcome = validator.validate_column(df, kpi_name)
    assert outcome.validated.min() >= expected_min
    assert outcome.validated.max() <= expected_max
    assert outcome.kpi_name == kpi_name
