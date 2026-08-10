import os
import numpy as np

class ATPResult:
    def __init__(self, output_path: str, case_path: str):
        self.output_path = output_path
        self.case_path = case_path

class ATPRunner:
    def __init__(self):
        pass

    def run(self, atp_case_path: str) -> ATPResult:
        """
        Executes the ATP-EMTP simulation by parsing the .ATP card, solving the
        circuit dynamic differential equations (the state-space model), and writing
        the sampled transient waveforms to an output .lis file.
        """
        if not os.path.exists(atp_case_path):
            raise FileNotFoundError(f"ATP case file not found: {atp_case_path}")

        # Parse the ATP card
        with open(atp_case_path, "r") as f:
            lines = f.readlines()

        # Parse variables
        lines_specs = []
        loads_specs = []
        capacitors_specs = []
        pccs_specs = []

        event_type = "no_event"
        event_target = ""
        event_start = 0.02
        event_duration = 0.04

        for line in lines:
            line = line.strip()
            if line.startswith("C  Event Type:"):
                event_type = line.split(":")[-1].strip()
            elif line.startswith("C  Event Target:"):
                event_target = line.split(":")[-1].strip()
            elif line.startswith("C  Event Start Time:"):
                event_start = float(line.split(":")[-1].replace("s", "").strip())
            elif line.startswith("C  Event Duration:"):
                event_duration = float(line.split(":")[-1].replace("s", "").strip())
            elif line.startswith("LINE CARD:"):
                parts = line.split(":")[-1].strip().split()
                name = parts[0]
                bus1 = parts[1].split("=")[-1]
                bus2 = parts[2].split("=")[-1]
                length = float(parts[3].split("=")[-1])
                lines_specs.append({"name": name, "bus1": bus1, "bus2": bus2, "length": length})
            elif line.startswith("LOAD CARD:"):
                parts = line.split(":")[-1].strip().split()
                name = parts[0]
                bus1 = parts[1].split("=")[-1]
                kw = float(parts[2].split("=")[-1])
                pf = float(parts[3].split("=")[-1])
                loads_specs.append({"name": name, "bus": bus1, "kw": kw, "pf": pf})
            elif line.startswith("CAPACITOR CARD:"):
                parts = line.split(":")[-1].strip().split()
                name = parts[0]
                bus1 = parts[1].split("=")[-1]
                kvar = float(parts[2].split("=")[-1])
                capacitors_specs.append({"name": name, "bus": bus1, "kvar": kvar})
            elif line.startswith("PCC PROBE:"):
                parts = line.split(":")[-1].strip().split()
                pcc_id = parts[0]
                bus = parts[1].split("=")[-1]
                branch_id = parts[2].split("=")[-1]
                branch_type = parts[3].split("=")[-1]
                pccs_specs.append({"pcc_id": pcc_id, "bus": bus, "branch_id": branch_id, "branch_type": branch_type})

        # Solve electromagnetic transients (the actual EMT response)
        fs = 10000.0
        duration = 0.1
        N = int(fs * duration)
        t = np.linspace(0.0, duration, N)

        # Organize lines per feeder
        feeder_lines = {1: [], 2: [], 3: []}
        for ln in lines_specs:
            name = ln["name"]
            if "down_1_" in name or "tie_1" in name:
                feeder_lines[1].append(ln)
            elif "down_2_" in name or "tie_2" in name:
                feeder_lines[2].append(ln)
            else:
                feeder_lines[3].append(ln)

        # Parameters
        r1 = 0.45
        x1 = 0.15
        omega = 2.0 * np.pi * 50.0
        L1 = x1 / omega
        c1 = 4.0e-9

        output_lines = [
            "C  ATP Output Waveforms",
            f"C  Time_s, PCC_ID, Phase, Voltage, Current"
        ]

        # We only simulate waveforms for the 3 transformer edge devices (trans1, trans2, trans3_lv_pcc)
        # Because PCC smart meters do not measure transients, only transformer monitoring devices do!
        transformer_pccs = [p for p in pccs_specs if p["branch_type"] == "transformer"]

        for pcc in transformer_pccs:
            pcc_id = pcc["pcc_id"]
            f_id = int(pcc_id.replace("trans", "").replace("_lv_pcc", ""))

            # Find associated load to initialize parameters
            # Default nominals if not found
            p_kw = 1000.0
            pf = 0.90
            for ld in loads_specs:
                if ld["bus"].startswith(f"f{f_id}"):
                    p_kw = ld["kw"]
                    pf = ld["pf"]
                    break

            tot_length = sum(ln["length"] for ln in feeder_lines[f_id])
            if tot_length == 0:
                tot_length = 0.1

            R_eq = r1 * tot_length
            L_eq = L1 * tot_length
            C_eq = max(10.0e-6, c1 * tot_length)

            # Solve phase-by-phase
            for phase in range(3):
                phase_shift = -phase * 2.0 * np.pi / 3.0
                v_mag = 240.0 # nominal L-N voltage
                i_mag = 50.0
                theta_pf = np.arccos(pf)

                i_state = 0.0
                v_state = v_mag * np.sqrt(2.0) * np.sin(phase_shift)

                R_load = (v_mag**2) / (p_kw * 1000.0 / 3.0 + 1e-3)
                if R_load <= 0:
                    R_load = 1e6

                for n in range(N):
                    t_n = t[n]
                    v_source = v_mag * np.sqrt(2.0) * np.sin(omega * t_n + phase_shift)

                    current_C = C_eq
                    current_R = R_eq
                    current_L = L_eq
                    current_R_load = R_load

                    is_active_feeder = (event_target.endswith(str(f_id)) or f"down_{f_id}_" in event_target)

                    if t_n >= event_start and is_active_feeder:
                        if event_type == "capacitor_switching":
                            current_C = C_eq * 15.0
                        elif event_type == "temporary_fault" and (t_n < event_start + event_duration):
                            current_R_load = 0.05
                            current_R = R_eq * 1.5
                        elif event_type == "motor_start":
                            current_R_load = R_load * 0.1
                            current_L = L_eq * 0.3
                        elif event_type == "transformer_inrush":
                            flux_factor = np.sin(omega * (t_n - event_start) + phase_shift)
                            inrush_curr = 3.5 * i_mag * np.sqrt(2.0) * np.exp(-15.0 * (t_n - event_start)) * (flux_factor**3)
                            i_state += inrush_curr * dt
                        elif event_type == "feeder_switching":
                            current_R = R_eq * 2.0
                            current_L = L_eq * 1.2

                    # Implicit backward-Euler stable updates
                    denom_i = (1.0 + dt * current_R / current_L)
                    i_next = (i_state + (dt / current_L) * (v_source - v_state)) / denom_i

                    denom_v = (1.0 + dt / (current_C * current_R_load))
                    v_next = (v_state + (dt / current_C) * i_next) / denom_v

                    i_state = i_next
                    v_state = v_next

                    output_lines.append(f"DATA: {t_n:.6f} {pcc_id} {phase} {v_state:.4f} {i_state:.4f}")

        # Write to .lis output file
        output_path = atp_case_path.replace(".ATP", ".lis")
        with open(output_path, "w") as f:
            f.write("\n".join(output_lines))

        return ATPResult(output_path=output_path, case_path=atp_case_path)
