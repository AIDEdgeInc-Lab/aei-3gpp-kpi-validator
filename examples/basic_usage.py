"""Minimal, self-contained usage example for aei_3gpp_kpi_validator.

Run with: python examples/basic_usage.py
"""
import pandas as pd

from aei_3gpp_kpi_validator import KPIValidator


def main() -> None:
    validator = KPIValidator()

    # Range validation against a real 3GPP-standard KPI (TS 36.214 §5.1).
    rsrp_df = pd.DataFrame({"rsrp": [-145.0, -100.0, -50.0, -40.0]})
    outcome = validator.validate_column(rsrp_df, "rsrp")
    print(f"RSRP out-of-range count: {outcome.out_of_range_count}")
    print(f"RSRP clipped values: {outcome.validated.tolist()}")

    # Handover-quality gate (TS 36.331 §5.5).
    handover_df = pd.DataFrame({
        "ho_preparation_time": [10, 60, 45, 49],
        "ho_execution_time": [5, 25, 19, 19],
    })
    passing_handovers = validator.validate_handover(handover_df)
    print(f"Handovers passing the quality gate: {len(passing_handovers)} / {len(handover_df)}")

    # NB-IoT power-saving gate (TS 36.213 §15.2).
    nbiot_df = pd.DataFrame({
        "paging_cycle": [100, 300, 256, 257],
        "edrx_cycle": [200000, 100000, 262144, 262145],
    })
    passing_nbiot = validator.validate_nbiot_power_profile(nbiot_df)
    print(f"NB-IoT profiles passing the power gate: {len(passing_nbiot)} / {len(nbiot_df)}")


if __name__ == "__main__":
    main()
