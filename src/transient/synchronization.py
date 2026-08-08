from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class BoundaryMeasurement:
    timestamp_s: float
    source: str
    node: str
    voltage_abc: tuple
    current_abc: tuple
    p_kw: float
    q_kvar: float
    s_kva: float
    frequency_hz: float
    rocof_hz_s: float
    v_sequence: tuple
    i_sequence: tuple
    thd_v: Optional[float] = None
    thd_i: Optional[float] = None
    event: Optional[str] = None

def synchronize_measurements(dss_m: dict, emt_waveforms: Optional[object] = None, timestamp_s: float = 0.0) -> dict:
    """
    Synchronizes the steady-state measurements and EMT high-frequency waveforms
    into canonical BoundaryMeasurement records.
    """
    synced = {}

    for i in range(1, 4):
        f_name = f"feeder{i}"

        if emt_waveforms is not None and f_name in emt_waveforms.feeder_voltage_abc:
            v_wave = emt_waveforms.feeder_voltage_abc[f_name]
            i_wave = emt_waveforms.feeder_current_abc[f_name]
            v_rms = float(np.sqrt(np.mean(v_wave**2)))
            i_rms = float(np.sqrt(np.mean(i_wave**2)))
        else:
            v_rms = dss_m.get(f"transformer{i}_hv_voltage", 11000.0 / np.sqrt(3))
            i_rms = dss_m.get(f"transformer{i}_hv_current", 50.0)

        synced[f_name] = BoundaryMeasurement(
            timestamp_s=timestamp_s,
            source="Substation",
            node=f"feeder{i}_head",
            voltage_abc=(v_rms, v_rms, v_rms),
            current_abc=(i_rms, i_rms, i_rms),
            p_kw=dss_m.get(f"transformer{i}_p_kw", 1000.0),
            q_kvar=dss_m.get(f"transformer{i}_q_kvar", 100.0),
            s_kva=dss_m.get(f"transformer{i}_s_kva", 1005.0),
            frequency_hz=dss_m.get("frequency_hz", 50.0),
            rocof_hz_s=0.0,
            v_sequence=(dss_m.get(f"transformer{i}_hv_voltage_pos_mag", v_rms), 0.0, 0.0),
            i_sequence=(dss_m.get(f"transformer{i}_hv_current_pos_mag", i_rms), 0.0, 0.0),
            thd_v=0.01 if emt_waveforms is None else 0.04,
            thd_i=0.02 if emt_waveforms is None else 0.12,
            event=emt_waveforms.event_metadata.get("event_type") if emt_waveforms is not None else None
        )

    return synced
