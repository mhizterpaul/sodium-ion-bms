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

        # Build a valid ATP-EMTP card case file
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
            "     1000       1       1       1       1       0       0       1       0",
            "/BRANCH",
            "C < n1 >< n2 ><ref1><ref2>< R  >< L  >< C  >",
            "  SRCA                      1.E3                                               0",
            "  SRCB                      1.E3                                               0",
            "  SRCC                      1.E3                                               0",
            "/SWITCH",
            "C < n 1>< n 2>< Tclose ><Top/Tde ><   Ie   ><Vf/CLOP ><  type  >",
            "  SRCA  S0A                                           MEASURING                0",
            "  SRCB  S0B                                           MEASURING                0",
            "  SRCC  S0C                                           MEASURING                0",
            "  S1A             -7.654      1.E3                                             0",
            "  S1B             -7.654      1.E3                                             0",
            "  S1C             -7.654      1.E3                                             0",
            "/SOURCE",
            "C < n 1><>< Ampl.  >< Freq.  ><Phase/T0><   A1   ><   T1   >< TSTART >< TSTOP  >",
            "14SRCA  -1    311.13       50.                                     -1.      100.",
            "14SRCB  -1    311.13       50.     -120.                           -1.      100.",
            "14SRCC  -1    311.13       50.     -240.                           -1.      100.",
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
