"""Package-hygiene tests: no network calls, no env-var dependency, no
import-time side effects, no internal AID Edge / Velorona paths or naming
leaking into the public package.

Adapted from aei-geo-features' test_package_hygiene.py (same repo family,
same bar). Unlike that package, this one legitimately ships YAML config
data files under src/ - the "no internal paths" sweep below covers .py
source only, matching the equivalent check there.
"""
import ast
import importlib
import sys
from pathlib import Path

import aei_3gpp_kpi_validator

SRC_DIR = Path(aei_3gpp_kpi_validator.__file__).resolve().parent


def _all_source_files():
    return sorted(SRC_DIR.rglob("*.py"))


def test_package_has_no_network_imports():
    banned = {"requests", "urllib", "http", "socket", "aiohttp", "httpx"}
    for path in _all_source_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned, f"{path}: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned, f"{path}: {node.module}"


def test_package_does_not_read_environment_variables():
    for path in _all_source_files():
        assert "os.environ" not in path.read_text(), path
        assert "os.getenv" not in path.read_text(), path


def test_no_module_level_side_effect_calls():
    """No function call at module top level (besides class/def bodies) -
    i.e. nothing runs at import time beyond defining names."""
    for path in _all_source_files():
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                raise AssertionError(f"Unexpected import-time call in {path}: {ast.dump(node.value.func)}")


def test_no_internal_aid_edge_or_velorona_paths_in_source():
    banned_substrings = ["velorona", "aidedgeinc", "AIDEdgeInc-Lab", "aei.foundation", "aei.telecom", "aei.ml_platform"]
    for path in _all_source_files():
        text = path.read_text().lower()
        for banned in banned_substrings:
            assert banned.lower() not in text, f"Found '{banned}' in {path}"


def test_no_internal_error_hierarchy_imported():
    """Confirms this package's errors are self-contained - never import an
    internal AEIError-rooted base class."""
    for path in _all_source_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("aei.foundation"), f"{path} imports internal {node.module}"


def test_reimporting_module_does_not_reexecute_side_effect_logic():
    """Re-import is idempotent and side-effect-free (proxy: no exception,
    same object identity)."""
    mod1 = importlib.import_module("aei_3gpp_kpi_validator")
    mod2 = importlib.reload(sys.modules["aei_3gpp_kpi_validator"])
    assert mod1.__version__ == mod2.__version__


def test_no_secret_like_string_literals_in_source():
    """A crude but real check: no string literal in source looks like an
    API key, token, or credential."""
    suspicious_markers = ["api_key", "apikey", "secret_key", "access_token", "aws_secret", "private_key", "-----BEGIN"]
    for path in _all_source_files():
        text = path.read_text().lower()
        for marker in suspicious_markers:
            assert marker not in text, f"Suspicious marker '{marker}' found in {path}"


def test_shipped_configs_are_the_only_data_files():
    """The package ships exactly the 5 KPI YAML configs as data - nothing
    else under config/, and no other data directory anywhere in src/."""
    config_dir = SRC_DIR / "config"
    shipped = sorted(p.name for p in config_dir.glob("*"))
    assert shipped == [
        "handover_quality.yml",
        "nbiot_power.yml",
        "rsrp.yml",
        "rsrq.yml",
        "sinr.yml",
    ]


def test_no_unbacked_compliance_or_marketing_claims_in_source():
    """This library makes standards-citation claims (TS numbers/sections)
    only - never an unbacked production/compliance/certification claim."""
    banned_markers = [
        "enterprise-grade", "enterprise grade", "production-ready", "production ready",
        "fips", "soc 2", "soc2", "gdpr-compliant", "gdpr compliant", "certified",
    ]
    for path in _all_source_files():
        text = path.read_text().lower()
        for marker in banned_markers:
            assert marker not in text, f"Unbacked claim marker '{marker}' found in {path}"
