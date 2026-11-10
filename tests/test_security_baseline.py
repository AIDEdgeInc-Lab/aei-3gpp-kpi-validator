"""Security baseline (Phase 4): a KPI name can only select a file inside the configuration folder, and a configured range must be
finite and ordered. Both would have been accepted by 0.1.2."""
import math
import os

import pandas as pd
import pytest

from aei_3gpp_kpi_validator.models import KPIStandard
from aei_3gpp_kpi_validator.validator import DEFAULT_CONFIG_PATH, ConfigurationError, KPIValidator

VALID_YAML = """standard:
  name: "3GPP TS 36.133"
  version: "17.0.0"
description: "test"
valid_range:
  min: {lo}
  max: {hi}
measurement_units: "dB"
"""


@pytest.fixture
def outside_config(tmp_path):
    """A schema-valid KPI file OUTSIDE the configuration folder, the kind of file a traversal would reach."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (tmp_path / "secret.yml").write_text(VALID_YAML.format(lo=0, hi=1))
    return cfg


@pytest.mark.parametrize("name", ["../secret", "..%2Fsecret", "sub/../../secret", "/etc/passwd", "rsrp.yml", ".", "", "a b",
                                  "x" * 65, None, 5])
def test_kpi_name_cannot_leave_the_configuration_folder(outside_config, name):
    v = KPIValidator(config_path=str(outside_config))
    with pytest.raises(ConfigurationError, match="Invalid KPI name"):
        v.load_kpi_config(name)
    assert v.rules == {}


def test_absolute_path_name_used_to_bypass_config_path(tmp_path):
    # os.path.join discards config_path when the second part is absolute: 0.1.2 would have loaded <tmp>/secret.yml.
    (tmp_path / "secret.yml").write_text(VALID_YAML.format(lo=0, hi=1))
    v = KPIValidator(config_path=DEFAULT_CONFIG_PATH)
    with pytest.raises(ConfigurationError):
        v.load_kpi_config(str(tmp_path / "secret"))


def test_symlink_inside_config_pointing_outside_is_refused(outside_config):
    os.symlink(outside_config.parent / "secret.yml", outside_config / "leak.yml")
    v = KPIValidator(config_path=str(outside_config))
    with pytest.raises(ConfigurationError, match="outside the configuration folder"):
        v.load_kpi_config("leak")


def test_shipped_kpis_still_load_case_insensitively():
    v = KPIValidator()
    for name in ("rsrp", "RSRQ", "sinr", "handover_quality", "nbiot_power"):
        v.load_kpi_config(name)
    assert set(v.rules) == {"rsrp", "RSRQ", "sinr", "handover_quality", "nbiot_power"}


def test_unknown_but_well_formed_name_is_still_file_not_found():
    with pytest.raises(FileNotFoundError):
        KPIValidator().load_kpi_config("nonexistent_kpi")


@pytest.mark.parametrize("lo,hi", [(".nan", 10), (0, ".nan"), ("-.inf", 0), (0, ".inf"), (10, 0)])
def test_unusable_range_in_yaml_is_refused(tmp_path, lo, hi):
    (tmp_path / "bad.yml").write_text(VALID_YAML.format(lo=lo, hi=hi))
    with pytest.raises(ConfigurationError):
        KPIValidator(config_path=str(tmp_path)).load_kpi_config("bad")


def test_nan_bound_would_have_been_a_silent_pass():
    """Why the range check matters: with a NaN bound nothing is ever out of range."""
    s = pd.Series([-500.0, 0.0, 500.0])
    assert int(((s < math.nan) | (s > math.nan)).sum()) == 0


@pytest.mark.parametrize("lo,hi", [(-140, -44), (0, 0), (-3.5, 3.5)])
def test_valid_ranges_accepted(lo, hi):
    KPIStandard(standard={"name": "x", "version": "1"}, description="d", valid_range={"min": lo, "max": hi}, measurement_units="u")
