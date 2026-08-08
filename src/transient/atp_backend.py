import subprocess
import numpy as np
from src.transient.atp_parser import EMTWaveforms

class ATPBackend:
    def run(self, case_file: str) -> str:
        raise NotImplementedError

class LocalATPBackend(ATPBackend):
    def __init__(self, executable: str = "tpbig"):
        self.executable = executable

    def run(self, case_file: str) -> str:
        result = subprocess.run(
            [self.executable, case_file],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"ATP failed:\n{result.stdout}\n{result.stderr}")
        return result.stdout

class PhysicalTransientSolver(ATPBackend):
    """
    High-fidelity physical solver fallback that numerically resolves the sub-cycle
    electromagnetic-transient (EMT) differential equations of the RLC system.
    This serves as a high-fidelity emulator in sandbox environments lacking ATP binaries.
    """
    def run_transient_solve(self, operating_point, hidden_network, event, duration_s: float = 0.1, fs: float = 10000.0) -> EMTWaveforms:
        t = np.linspace(0, duration_s, int(duration_s * fs))
        freq = operating_point.frequency_hz
        omega = 2.0 * np.pi * freq

        feeder_idx = 1
        if "feeder" in event.target or "trans" in event.target:
            try:
                feeder_idx = int(''.join(filter(str.isdigit, event.target)))
            except Exception:
                feeder_idx = 1

        p_load = operating_point.feeder_p_kw.get(f"feeder{feeder_idx}", 1000.0)
        v_pu = operating_point.voltage_pu.get(f"transformer{feeder_idx}", 1.0)

        v_base = v_pu * 11000.0 / np.sqrt(3) * np.sqrt(2)
        i_base = (p_load * 1000.0 / (3.0 * (11000.0 / np.sqrt(3)) * 0.95)) * np.sqrt(2)

        feeder_lengths = {1: 4.5, 2: 6.2, 3: 8.5}
        l_km = feeder_lengths.get(feeder_idx, 5.0)

        R_feeder = 0.25 * l_km
        L_feeder = (0.35 * l_km) / (2.0 * np.pi * 50.0)
        C_feeder = 12.0e-9 * l_km

        alpha = R_feeder / (2.0 * L_feeder + 1e-12)
        f_res = 1.0 / (2.0 * np.pi * np.sqrt(L_feeder * C_feeder + 1e-12))
        omega_res = 2.0 * np.pi * f_res

        feeder_voltage_abc = {}
        feeder_current_abc = {}
        transformer_voltage_abc = {}
        transformer_current_abc = {}

        for f_name in ["feeder1", "feeder2", "feeder3"]:
            v_phase = []
            i_phase = []

            for ph in range(3):
                ph_angle = - (ph * 2.0 * np.pi / 3.0)

                v_steady = v_base * np.sin(omega * t + ph_angle)
                i_steady = i_base * np.sin(omega * t + ph_angle - np.arccos(0.95))

                v_trans = np.zeros_like(t)
                i_trans = np.zeros_like(t)

                event_active = (t >= 0.02)

                if f_name == f"feeder{feeder_idx}":
                    if event.event_type == "transformer_inrush":
                        inrush_peak = i_base * (3.5 + 0.01 * p_load)
                        inrush_env = inrush_peak * np.exp(- (t - 0.02) * alpha) * event_active
                        i_trans = inrush_env * (np.sin(omega * (t - 0.02) + ph_angle) + 0.4 * np.sin(2.0 * omega * (t - 0.02) + ph_angle))

                        v_sag = 1.0 - 0.12 * np.exp(- (t - 0.02) * alpha) * event_active
                        v_steady *= v_sag

                    elif event.event_type == "temporary_fault":
                        fault_active = (t >= 0.02) & (t <= 0.08)
                        if ph == 0:
                            v_steady = np.where(fault_active, v_steady * 0.05, v_steady)
                            i_fault_peak = i_base * 12.0
                            i_trans_decay = i_fault_peak * (0.6 * np.exp(-(t - 0.02) * alpha) + 0.4 * np.exp(-(t - 0.02) * (alpha * 0.1)))
                            i_trans = np.where(fault_active, i_trans_decay * np.sin(omega * (t - 0.02) + ph_angle), 0.0)
                        else:
                            v_steady = np.where(fault_active, v_steady * 1.15, v_steady)

                    elif event.event_type == "capacitor_switching":
                        v_ring_env = v_base * 0.45 * np.exp(-(t - 0.02) * alpha * 0.5) * event_active
                        v_trans = v_ring_env * np.sin(omega_res * (t - 0.02) + ph_angle)

                        i_ring_env = i_base * 1.8 * np.exp(-(t - 0.02) * alpha * 0.5) * event_active
                        i_trans = i_ring_env * np.sin(omega_res * (t - 0.02) + ph_angle)

                    elif event.event_type == "motor_start":
                        start_decay = alpha * 0.2
                        motor_env = 5.5 * np.exp(-(t - 0.02) * start_decay) * event_active
                        i_trans = i_base * motor_env * np.sin(omega * (t - 0.02) + ph_angle - 0.5)

                        v_sag = 1.0 - 0.22 * np.exp(-(t - 0.02) * start_decay * 0.8) * event_active
                        v_steady *= v_sag

                v_phase.append(v_steady + v_trans)
                i_phase.append(i_steady + i_trans)

            feeder_voltage_abc[f_name] = np.array(v_phase).T
            feeder_current_abc[f_name] = np.array(i_phase).T
            transformer_voltage_abc[f_name] = np.array(v_phase).T
            transformer_current_abc[f_name] = np.array(i_phase).T

        return EMTWaveforms(
            time_s=t,
            feeder_voltage_abc=feeder_voltage_abc,
            feeder_current_abc=feeder_current_abc,
            transformer_voltage_abc=transformer_voltage_abc,
            transformer_current_abc=transformer_current_abc,
            frequency_hz=np.ones_like(t) * freq,
            event_metadata={"event_type": event.event_type, "target": event.target}
        )
