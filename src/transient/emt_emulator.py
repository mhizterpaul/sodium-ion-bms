import numpy as np

class EMTWaveforms:
    def __init__(self, time_s: np.ndarray, pcc_voltages: dict[str, np.ndarray], pcc_currents: dict[str, np.ndarray], event_metadata: dict):
        self.time_s = time_s
        self.pcc_voltages = pcc_voltages   # {pcc_id: (N_samples, 3)}
        self.pcc_currents = pcc_currents   # {pcc_id: (N_samples, 3)}
        self.event_metadata = event_metadata

def simulate_emt_waveforms(metered_pccs: list[dict], pcc_measurements: dict, event, fs: float = 10000.0, duration: float = 0.1) -> EMTWaveforms:
    """
    Simulates high-fidelity three-phase voltage and current waveforms
    for each metered PCC, incorporating physical transient excitation dynamics.
    """
    N = int(fs * duration)
    t = np.linspace(0.0, duration, N)

    pcc_voltages = {}
    pcc_currents = {}

    event_type = getattr(event, "event_type", "no_event")
    event_start = getattr(event, "start_time_s", 0.02)
    event_duration = getattr(event, "duration_s", 0.04)

    # Pre-event and post-event masking
    pre_mask = t < event_start
    post_mask = t >= event_start

    for pcc in metered_pccs:
        pcc_id = pcc["pcc_id"]
        data = pcc_measurements[pcc_id]

        v_rms_list = data["v_mags"]  # 3 elements
        i_rms_list = data["i_mags"]  # 3 elements
        pf = data["pf"]

        v_wave = np.zeros((N, 3))
        i_wave = np.zeros((N, 3))

        for phase in range(3):
            v_rms = v_rms_list[phase] if phase < len(v_rms_list) else 240.0
            i_rms = i_rms_list[phase] if phase < len(i_rms_list) else 10.0

            # Phase shifts (A, B, C)
            phase_shift = -phase * 2.0 * np.pi / 3.0
            theta = np.arccos(pf)

            # Pre-event steady-state wave
            v_pre = v_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t[pre_mask] + phase_shift)
            i_pre = i_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t[pre_mask] + phase_shift - theta)

            v_wave[pre_mask, phase] = v_pre
            i_wave[pre_mask, phase] = i_pre

            # Post-event waveform with transient dynamics
            t_post = t[post_mask] - event_start

            v_trans = np.zeros_like(t_post)
            i_trans = np.zeros_like(t_post)

            if event_type == "capacitor_switching":
                # High-frequency decaying ringing on voltage
                v_trans = 0.4 * v_rms * np.sqrt(2.0) * np.exp(-120.0 * t_post) * np.sin(2.0 * np.pi * 480.0 * t_post + phase_shift)
                i_trans = 0.1 * i_rms * np.sqrt(2.0) * np.exp(-100.0 * t_post) * np.sin(2.0 * np.pi * 480.0 * t_post + phase_shift)

            elif event_type == "transformer_inrush":
                # Second-harmonic rich current inrush
                v_trans = -0.1 * v_rms * np.sqrt(2.0) * np.exp(-40.0 * t_post) * np.sin(2.0 * np.pi * 50.0 * t_post + phase_shift)
                i_trans = 4.0 * i_rms * np.sqrt(2.0) * np.exp(-15.0 * t_post) * np.sin(2.0 * np.pi * 100.0 * t_post + phase_shift)

            elif event_type == "motor_start":
                # High starting current with low power factor
                v_trans = -0.15 * v_rms * np.sqrt(2.0) * np.exp(-10.0 * t_post) * np.sin(2.0 * np.pi * 50.0 * t_post + phase_shift)
                i_trans = 2.5 * i_rms * np.sqrt(2.0) * np.exp(-8.0 * t_post) * np.sin(2.0 * np.pi * 50.0 * t_post + phase_shift - 1.2)

            elif event_type == "temporary_fault":
                # Severe voltage drop and current spike during fault, followed by recovery
                fault_mask = t_post < event_duration
                recovery_mask = t_post >= event_duration

                # During fault
                v_trans[fault_mask] = -0.8 * v_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t_post[fault_mask] + phase_shift)
                i_trans[fault_mask] = 5.0 * i_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t_post[fault_mask] + phase_shift - 0.2)

                # Recovery transient
                t_rec = t_post[recovery_mask] - event_duration
                v_trans[recovery_mask] = -0.2 * v_rms * np.sqrt(2.0) * np.exp(-50.0 * t_rec) * np.sin(2.0 * np.pi * 50.0 * t_rec + phase_shift)
                i_trans[recovery_mask] = 0.5 * i_rms * np.sqrt(2.0) * np.exp(-40.0 * t_rec) * np.sin(2.0 * np.pi * 50.0 * t_rec + phase_shift)

            elif event_type == "feeder_switching":
                # Fast step transient
                v_trans = 0.2 * v_rms * np.sqrt(2.0) * np.exp(-250.0 * t_post) * np.sin(2.0 * np.pi * 600.0 * t_post + phase_shift)
                i_trans = 0.3 * i_rms * np.sqrt(2.0) * np.exp(-200.0 * t_post) * np.sin(2.0 * np.pi * 600.0 * t_post + phase_shift)

            # Combine steady state and transient
            v_wave[post_mask, phase] = v_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t_post + phase_shift) + v_trans
            i_wave[post_mask, phase] = i_rms * np.sqrt(2.0) * np.sin(2.0 * np.pi * 50.0 * t_post + phase_shift - theta) + i_trans

        pcc_voltages[pcc_id] = v_wave
        pcc_currents[pcc_id] = i_wave

    event_metadata = {
        "event_type": event_type,
        "start_time_s": event_start,
        "duration_s": event_duration
    }

    return EMTWaveforms(t, pcc_voltages, pcc_currents, event_metadata)
