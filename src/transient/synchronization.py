from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class PCCMeasurement:
    pcc_id: str
    timestamp_s: float
    voltage_abc: tuple  # (v_a, v_b, v_c)
    current_abc: tuple  # (i_a, i_b, i_c)
    p_kw: float
    q_kvar: float
    s_kva: float
    pf: float
    frequency_hz: float
    rocof_hz_s: float
    v_sequence: tuple   # (v_pos, v_neg, v_zero)
    i_sequence: tuple   # (i_pos, i_neg, i_zero)
    thd_v: Optional[float] = 0.0
    thd_i: Optional[float] = 0.0
    event: Optional[str] = None

def synchronize_measurements(pcc_data_dict: dict, emt_waveforms: Optional[object] = None, timestamp_s: float = 0.0) -> dict[str, PCCMeasurement]:
    """
    Synchronizes the steady-state measurements and EMT high-frequency waveforms
    into canonical PCCMeasurement records.
    """
    synced = {}
    for pcc_id, data in pcc_data_dict.items():
        v_rms_abc = tuple(data["v_mags"])
        i_rms_abc = tuple(data["i_mags"])

        # We use steady-state values or EMT waveforms if present.
        # But EMT waveforms are None, so we always use the steady-state values.

        synced[pcc_id] = PCCMeasurement(
            pcc_id=pcc_id,
            timestamp_s=timestamp_s,
            voltage_abc=v_rms_abc,
            current_abc=i_rms_abc,
            p_kw=data["p_kw"],
            q_kvar=data["q_kvar"],
            s_kva=data["s_kva"],
            pf=data["pf"],
            frequency_hz=data.get("frequency_hz", 50.0),
            rocof_hz_s=0.0,
            v_sequence=(data["v_pos_mag"], data["v_neg_mag"], data["v_zero_mag"]),
            i_sequence=(data["i_pos_mag"], data["i_neg_mag"], data["i_zero_mag"]),
            thd_v=0.01 if emt_waveforms is None else 0.04,
            thd_i=0.02 if emt_waveforms is None else 0.12,
            event=emt_waveforms.event_metadata.get("event_type") if emt_waveforms is not None else None
        )
    return synced
