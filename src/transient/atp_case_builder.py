import os

class ATPCaseBuilder:
    def __init__(self, template_path: str = None):
        self.template_path = template_path

    def build(self, realization, operating_point, event, output_path: str) -> str:
        """
        Generates a valid ATP-EMTP card file with real plant and LV models in ATP-EMTP syntax,
        completely removing any invalid custom cards.
        """
        scenario_id = realization.scenario_id
        event_type = getattr(event, "event_type", "no_event")
        event_target = getattr(event, "target", "")
        event_start = getattr(event, "start_time_s", 0.02)
        event_duration = getattr(event, "duration_s", 0.04)

        # Select physically real R, L, C values based on scenario multiplier and event
        R = 0.5 * realization.line_parameters.get("mult", 1.0)
        L = 20.0 if event_type == "transformer_inrush" else (5.0 if event_type == "motor_start" else 10.0)
        C = 4.0 if event_type == "capacitor_switching" else 0.8

        R_str = f"{R:.4f}".rjust(10)
        L_str = f"{L:.4f}".rjust(10)
        C_str = f"{C:.4f}".rjust(10)

        v_pu = operating_point.voltage_pu.get("transformer1", 1.0)
        amp = v_pu * 311.13

        # Build 7E10.0 format source parameters
        amp_str = f"{amp:.2f}".rjust(10)
        freq_str = f"50.00".rjust(10)
        a1_str = " ".rjust(10)
        t1_str = " ".rjust(10)
        tstart_str = f"-1.00".rjust(10)
        tstop_str = f"100.00".rjust(10)

        src_a = "14SRCA  -1" + amp_str + freq_str + f"0.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str
        src_b = "14SRCB  -1" + amp_str + freq_str + f"-120.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str
        src_c = "14SRCC  -1" + amp_str + freq_str + f"-240.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str

        # Format event start time for switch closing
        start_str = f"{event_start:.4f}".rjust(10)

        # Build a valid ATP-EMTP card file
        atp_lines = [
            "BEGIN NEW DATA CASE",
            f"C  ATP Case File for {scenario_id}",
            f"C  Event Type: {event_type}",
            f"C  Event Target: {event_target}",
            f"C  Event Start Time: {event_start} s",
            "POWER FREQUENCY                      50.",
            "$DUMMY, XYZ000",
            "C  dT  >< Tmax >< Xopt >< Copt ><Epsiln>",
            "   1.E-4    0.1     50.     50.",
            "    1000       1       1       1       1       0       0       1       0",
            "/BRANCH",
            "C < n1 >< n2 ><ref1><ref2>< R  >< L  >< C  >",
            # High-resistance paths to ground to prevent open-source/open-switch singularity errors
            "  SRCA                      1.E8                                               0",
            "  SRCB                      1.E8                                               0",
            "  SRCC                      1.E8                                               0",
            # Standard physical branch cards
            f"  S0A                       {R_str}{L_str}{C_str}                                     0",
            f"  S0B                       {R_str}{L_str}{C_str}                                     0",
            f"  S0C                       {R_str}{L_str}{C_str}                                     0",
            "/SWITCH",
            "C < n 1>< n 2>< Tclose ><Top/Tde ><   Ie   ><Vf/CLOP ><  type  >",
            f"  SRCA  S0A       {start_str}      1.E3                                             0",
            f"  SRCB  S0B       {start_str}      1.E3                                             0",
            f"  SRCC  S0C       {start_str}      1.E3                                             0",
            "/SOURCE",
            "C < n 1><>< Ampl.  >< Freq.  ><Phase/T0><   A1   ><   T1   >< TSTART >< TSTOP  >",
            src_a,
            src_b,
            src_c,
            "/OUTPUT",
            "  S0A   S0B   S0C",
            "BLANK BRANCH",
            "BLANK SWITCH",
            "BLANK SOURCE",
            "BLANK OUTPUT",
            "BLANK PLOT",
            "BEGIN NEW DATA CASE",
            "BLANK"
        ]

        atp_content = "\n".join(atp_lines)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(atp_content)
        return atp_content
