import os
from src.hidden_network.loads import get_equipment_model

class ATPCaseBuilder:
    def __init__(self, template_path: str = None):
        self.template_path = template_path

    def build(self, realization, operating_point, event, output_path: str) -> str:
        """
        Generates a valid ATP-EMTP card file for single equipment switching,
        explicit line faults (LG, LL, LLG, LLL), and co-events in ATP-EMTP syntax.
        """
        scenario_id = getattr(realization, "scenario_id", "scenario_0")

        # Unwrap co-events or single events
        events_to_process = []
        if hasattr(event, "event_1") and hasattr(event, "event_2"):
            events_to_process = [event.event_1, event.event_2]
        else:
            events_to_process = [event]

        # Base physical parameters
        line_mult = realization.line_parameters.get("mult", 1.0) if hasattr(realization, "line_parameters") else 1.0
        R_base = 0.45 * line_mult
        L_base = 0.15 * line_mult

        v_pu = getattr(operating_point, "voltage_pu", {}).get("transformer1", 1.0) if hasattr(operating_point, "voltage_pu") else 1.0
        amp = v_pu * 311.13

        amp_str = f"{amp:.2f}".rjust(10)
        freq_str = f"50.00".rjust(10)
        a1_str = " ".rjust(10)
        t1_str = " ".rjust(10)
        tstart_str = f"-1.00".rjust(10)
        tstop_str = f"100.00".rjust(10)

        src_a = "14SRCA  -1" + amp_str + freq_str + f"0.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str
        src_b = "14SRCB  -1" + amp_str + freq_str + f"-120.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str
        src_c = "14SRCC  -1" + amp_str + freq_str + f"-240.00".rjust(10) + a1_str + t1_str + tstart_str + tstop_str

        branch_cards = []
        switch_cards = []

        # Default high-resistance paths to ground
        branch_cards.extend([
            "  SRCA                      1.E8                                               0",
            "  SRCB                      1.E8                                               0",
            "  SRCC                      1.E8                                               0",
        ])

        for idx, ev in enumerate(events_to_process):
            start_s = getattr(ev, "start_time_s", 0.02)
            start_str = f"{start_s:.4f}".rjust(10)
            ev_class = getattr(ev, "event_class", "equipment_switch")

            if ev_class == "equipment_switch":
                eq_type = getattr(ev, "equipment_type", "ac_motor")
                try:
                    eq_model = get_equipment_model(eq_type)
                    r_eq = eq_model.atp_params.get("r_stator", 0.1)
                    x_eq = eq_model.atp_params.get("x_stator", 0.2)
                except Exception:
                    r_eq, x_eq = 0.2, 0.4

                r_str = f"{r_eq:.4f}".rjust(10)
                l_str = f"{x_eq * 1000.0 / (2*3.14159*50.0):.4f}".rjust(10)
                c_str = f"0.8000".rjust(10)

                node_prefix = f"E{idx}"
                for ph_char in ["A", "B", "C"]:
                    src_node = f"SRC{ph_char}"
                    load_node = f"{node_prefix}{ph_char}"
                    branch_cards.append(f"  {load_node}                       {r_str}{l_str}{c_str}                                     0")
                    switch_cards.append(f"  {src_node}  {load_node}       {start_str}      1.E3                                             0")

            elif ev_class == "line_fault":
                f_type = getattr(ev, "fault_type", "LG")
                f_res = getattr(ev, "fault_resistance", 0.05)
                f_phases = getattr(ev, "faulted_phases", (0,))

                f_res_str = f"{f_res:.4f}".rjust(10)
                zero_str = f"0.0000".rjust(10)

                node_prefix = f"F{idx}"
                phase_map = {0: "A", 1: "B", 2: "C"}

                for ph_idx in f_phases:
                    ph_char = phase_map.get(ph_idx, "A")
                    src_node = f"SRC{ph_char}"
                    fault_node = f"{node_prefix}{ph_char}"
                    branch_cards.append(f"  {fault_node}                       {f_res_str}{zero_str}{zero_str}                                     0")
                    switch_cards.append(f"  {src_node}  {fault_node}       {start_str}      1.E3                                             0")

        if not switch_cards:
            start_str = f"0.0200".rjust(10)
            branch_cards.extend([
                f"  S0A                       0.5000   10.0000    0.8000                                     0",
                f"  S0B                       0.5000   10.0000    0.8000                                     0",
                f"  S0C                       0.5000   10.0000    0.8000                                     0",
            ])
            switch_cards.extend([
                f"  SRCA  S0A       {start_str}      1.E3                                             0",
                f"  SRCB  S0B       {start_str}      1.E3                                             0",
                f"  SRCC  S0C       {start_str}      1.E3                                             0",
            ])

        atp_lines = [
            "BEGIN NEW DATA CASE",
            f"C  ATP Case File for {scenario_id}",
            "POWER FREQUENCY                      50.",
            "$DUMMY, XYZ000",
            "C  dT  >< Tmax >< Xopt >< Copt ><Epsiln>",
            "   1.E-4    0.1     50.     50.",
            "    1000       1       1       1       1       0       0       1       0",
            "/BRANCH",
            "C < n1 >< n2 ><ref1><ref2>< R  >< L  >< C  >",
        ] + branch_cards + [
            "/SWITCH",
            "C < n 1>< n 2>< Tclose ><Top/Tde ><   Ie   ><Vf/CLOP ><  type  >",
        ] + switch_cards + [
            "/SOURCE",
            "C < n 1><>< Ampl.  >< Freq.  ><Phase/T0><   A1   ><   T1   >< TSTART >< TSTOP  >",
            src_a,
            src_b,
            src_c,
            "/OUTPUT",
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
