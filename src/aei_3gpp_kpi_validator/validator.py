"""
3GPP KPI standards validator: range validation against real TS-derived
thresholds, plus two KPI-specific predicate checks (handover, NB-IoT power).

This module never imports prometheus_client - metrics are the job of
metrics.py, which calls into this module's outcomes rather than the other
way around.

Dask is optional. validate_handover and validate_nbiot_power_profile use the
same predicate string for both pandas and Dask input, so the two backends
cannot silently diverge in business semantics - see tests/test_validator.py's
parity tests.
"""
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import pandas as pd
import yaml
from pandas.api.types import is_numeric_dtype
from pydantic import ValidationError as PydanticValidationError

from aei_3gpp_kpi_validator.models import KPIStandard

try:
    import dask.dataframe as dd
    DASK_AVAILABLE = True
except ImportError:
    dd = None
    DASK_AVAILABLE = False

LOG = logging.getLogger("aei_3gpp_kpi_validator.validator")

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config")

_HANDOVER_REQUIRED_COLUMNS = {"ho_preparation_time", "ho_execution_time"}
_HANDOVER_PREDICATE = "ho_preparation_time < 50 & ho_execution_time < 20"

_NBIOT_REQUIRED_COLUMNS = {"paging_cycle", "edrx_cycle"}
_NBIOT_PREDICATE = "paging_cycle <= 256 & edrx_cycle <= 262144"


class ConfigurationError(Exception):
    """Raised for KPI configuration load/schema errors."""


@dataclass
class ValidationOutcome:
    """What validate_column produced, plus the stats a metrics adapter needs.

    Deliberately returned instead of calling Prometheus inline - see
    metrics.py, which is the only module in this package permitted to import
    prometheus_client.
    """
    kpi_name: str
    data_source: str
    gpp3_version: str
    validated: Any  # pd.Series or dask.dataframe.Series
    out_of_range_count: int
    latency_seconds: float


class KPIValidator:
    """Loads YAML KPI configs and validates DataFrame columns against them."""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.rules: Dict[str, Dict] = {}
        self._validate_config_path(config_path)

    def _validate_config_path(self, config_path: str) -> None:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration path not found: {config_path}")

    def load_kpi_config(self, kpi_name: str) -> None:
        filepath = os.path.join(self.config_path, f"{kpi_name.lower()}.yml")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration for {kpi_name} not found.")
        try:
            with open(filepath, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML for {kpi_name}: {e}") from e
        self._validate_kpi_schema(config)
        self.rules[kpi_name] = config
        LOG.info(f"Loaded config for {kpi_name} from {filepath}")

    def _validate_kpi_schema(self, config: dict) -> None:
        try:
            KPIStandard(**config)
        except PydanticValidationError as e:
            LOG.error(f"Invalid KPI schema: {e}")
            raise ConfigurationError(str(e)) from e

    def _clip_column(self, series, min_val: float, max_val: float):
        if DASK_AVAILABLE and isinstance(series, dd.Series):
            return series.map_partitions(lambda s: s.clip(lower=min_val, upper=max_val))
        return series.clip(lower=min_val, upper=max_val)

    def _validate_data_schema(self, df, kpi_name: str) -> None:
        """Validates that the target KPI's own column exists and is numeric.

        Deliberately scoped to just `kpi_name`: nothing in validate_column
        reads any column other than df[kpi_name], so validating e.g. 'sinr'
        must not require rsrp/rsrq/cell_id to be present.
        """
        if kpi_name not in df.columns:
            raise ValueError(f"Missing required column: {kpi_name}")

        actual_dtype = df[kpi_name].dtype
        if DASK_AVAILABLE and isinstance(df, dd.DataFrame):
            if not (pd.api.types.is_float_dtype(actual_dtype) or pd.api.types.is_integer_dtype(actual_dtype)):
                raise TypeError(f"Column '{kpi_name}' must be numeric in Dask, but got {actual_dtype}")
        else:
            if not is_numeric_dtype(df[kpi_name]):
                raise TypeError(f"Column '{kpi_name}' must be numeric, but got {actual_dtype}")

    def validate_column(self, df, kpi_name: str, data_source: str = "unknown") -> ValidationOutcome:
        """Range-clip validation against the KPI's configured min/max."""
        if kpi_name not in self.rules:
            self.load_kpi_config(kpi_name)
        rule = self.rules[kpi_name]

        self._validate_data_schema(df, kpi_name)
        start_time = time.time()

        min_val = rule["valid_range"]["min"]
        max_val = rule["valid_range"]["max"]

        out_of_range = (df[kpi_name] < min_val) | (df[kpi_name] > max_val)
        out_of_range_count = (
            out_of_range.sum().compute() if DASK_AVAILABLE and isinstance(out_of_range, dd.Series)
            else out_of_range.sum()
        )
        if out_of_range_count > 0:
            LOG.warning(f"Validation errors detected for {kpi_name}: {out_of_range_count} out-of-range records")

        validated_series = self._clip_column(df[kpi_name], min_val, max_val)
        latency = time.time() - start_time

        return ValidationOutcome(
            kpi_name=kpi_name,
            data_source=data_source,
            gpp3_version=rule["standard"]["version"],
            validated=validated_series,
            out_of_range_count=int(out_of_range_count),
            latency_seconds=latency,
        )

    def validate_handover(self, df):
        """TS 36.331 handover quality gate: keeps rows where
        ho_preparation_time < 50 ms and ho_execution_time < 20 ms.

        Pandas-default; Dask-accelerated if given a Dask DataFrame. Both
        backends apply the exact same predicate string - see
        tests/test_validator.py::test_validate_handover_pandas_dask_parity.
        """
        missing = _HANDOVER_REQUIRED_COLUMNS - set(df.columns)
        if missing:
            LOG.error(f"Missing column(s) for handover validation: {missing}")
            return df
        try:
            if DASK_AVAILABLE and isinstance(df, dd.DataFrame):
                return df.map_partitions(
                    lambda partition: partition.query(_HANDOVER_PREDICATE, engine="python"),
                    meta=df._meta,
                )
            return df.query(_HANDOVER_PREDICATE, engine="python")
        except Exception as e:
            LOG.error(f"Error during handover validation: {e}")
            return df

    def validate_nbiot_power_profile(self, df):
        """TS 36.213 §15.2 NB-IoT power-saving gate: keeps rows where
        paging_cycle <= 256 and edrx_cycle <= 262144 (2^18) radio frames.

        Pandas-default; Dask-accelerated if given a Dask DataFrame. Both
        backends apply the exact same predicate string - see
        tests/test_validator.py::test_validate_nbiot_power_profile_pandas_dask_parity.
        """
        missing = _NBIOT_REQUIRED_COLUMNS - set(df.columns)
        if missing:
            LOG.error(f"Missing column(s) for NB-IoT power profile validation: {missing}")
            return df
        try:
            if DASK_AVAILABLE and isinstance(df, dd.DataFrame):
                return df.map_partitions(
                    lambda partition: partition.query(_NBIOT_PREDICATE, engine="python"),
                    meta=df._meta,
                )
            return df.query(_NBIOT_PREDICATE, engine="python")
        except Exception as e:
            LOG.error(f"Error during NB-IoT power profile validation: {e}")
            return df
