"""
3GPP KPI standards validation: real TS-derived range checks for RSRP, RSRQ,
SINR, handover quality, and NB-IoT power profile.

metrics.py is intentionally NOT imported here - importing this package never
pulls in prometheus_client. See metrics.py for the optional adapter.
"""
from aei_3gpp_kpi_validator.models import KPIStandard, Standard, ValidRange
from aei_3gpp_kpi_validator.validator import ConfigurationError, KPIValidator, ValidationOutcome

__version__ = "0.1.1"

__all__ = [
    "__version__",
    "Standard",
    "ValidRange",
    "KPIStandard",
    "KPIValidator",
    "ValidationOutcome",
    "ConfigurationError",
]
