from opendssdirect import dss
import numpy as np

from src.power_plant.plant import initialize_known_plant, solve_operating_point
from src.hidden_network.pcc_meters import get_pcc_measurements

from src.hidden_network.topology import (
    generate_radial_topology,
    identify_candidate_pccs,
    select_metered_pccs
)
from src.hidden_network.loads import distribute_loads
from src.power_plant.transformers import get_distribution_transformer_spec
from src.hidden_network.perturbations import apply_topology_reconfiguration

from src.transient.atp_case_builder import ATPCaseBuilder
from src.transient.atp_runner import ATPRunner
from src.transient.atp_parser import ATPOutputReader

class SimulationResult:
    def __init__(self, time_s: np.ndarray, metered_pccs: list[dict], steady_state_measurements: dict, processed_pccs: dict):
        self.time_s = time_s
        self.metered_pccs = metered_pccs
        self.steady_state_measurements = steady_state_measurements
        self.processed_pccs = processed_pccs

class CoSimulationRunner:
    def __init__(self):
        self.atp_builder = ATPCaseBuilder()

    def run_scenario(self, sim_scenario, use_baseline_transformers: bool = False) -> SimulationResult:
        """
        Coordinates full co-simulation run: DSS operating point + ATP transient waveform simulation.
        Returns a structured SimulationResult object.
        """
        initialize_known_plant(use_baseline_transformers=use_baseline_transformers)

        h_net = sim_scenario.hidden_network
        topo = h_net.topology
        scenario_id = h_net.scenario_id

        dss.run_command(f"new linecode.down_lv nphases=3 r1=0.45 x1=0.15 r0=1.20 x0=0.35 c1=4.0 c0=2.0 units=km")

        topologies = topo.get("topologies", {})
        if topologies:
            for feeder_idx, sub_topo in topologies.items():
                hidden_root_bus = sub_topo["buses"][0]
                expected_transformer_secondary = f"feeder{feeder_idx}_sec"
                assert hidden_root_bus == expected_transformer_secondary, f"Hidden network root {hidden_root_bus} does not match expected transformer secondary {expected_transformer_secondary}"

                for ln in sub_topo["lines"]:
                    dss.run_command(
                        f"new line.{ln['name']} bus1={ln['bus1']} bus2={ln['bus2']} phases=3 linecode=down_lv length={ln['length']} units={ln['units']}"
                    )
        else:
            for ln in topo.get("lines", []):
                dss.run_command(
                    f"new line.{ln['name']} bus1={ln['bus1']} bus2={ln['bus2']} phases=3 linecode=down_lv length={ln['length']} units={ln['units']}"
                )

        for ld in h_net.loads["loads"]:
            dss.run_command(
                f"new load.{ld['name']} bus1={ld['bus']} phases=3 kv=0.415 kw={ld['kw']} pf={ld['pf']} model={ld['model']} status=fixed"
            )
        for cap in h_net.loads["capacitors"]:
            dss.run_command(
                f"new capacitor.{cap['name']} bus1={cap['bus']} phases=3 kv=0.415 kvar={cap['kvar']} conn=wye"
            )
        for m in h_net.loads["motors"]:
            dss.run_command(
                f"new load.{m['name']} bus1={m['bus']} phases=3 kv=0.415 kw={m['kw']} pf={m['pf']} model=2 status=fixed"
            )
        for der in h_net.loads["ders"]:
            dss.run_command(
                f"new generator.{der['name']} bus1={der['bus']} phases=3 kv=0.415 kw={der['kw']} pf=1.0 model=1"
            )

        # Apply distribution line faults in OpenDSS prior to solving operating point
        if sim_scenario.events:
            events_to_check = []
            for ev in sim_scenario.events:
                if hasattr(ev, "event_1") and hasattr(ev, "event_2"):
                    events_to_check.extend([ev.event_1, ev.event_2])
                else:
                    events_to_check.append(ev)

            fault_count = 0
            for ev in events_to_check:
                if getattr(ev, "event_class", "") == "line_fault":
                    fault_count += 1
                    f_type = getattr(ev, "fault_type", "LG")
                    target = getattr(ev, "target", "trans1")
                    f_res = getattr(ev, "fault_resistance", 0.05)
                    phases = getattr(ev, "faulted_phases", (0,))

                    if target.startswith("trans"):
                        f_num = target.replace("trans", "")
                        target_bus = f"feeder{f_num}_sec"
                    elif not target.startswith("feeder") and not target.startswith("down_"):
                        target_bus = "feeder1_sec"
                    else:
                        target_bus = target

                    fault_name = f"dist_fault_{fault_count}"

                    if f_type == "LG":
                        ph_num = phases[0] + 1 if phases else 1
                        dss.run_command(f"new Fault.{fault_name} bus1={target_bus}.{ph_num} phases=1 r={f_res}")
                    elif f_type == "LL":
                        ph1 = phases[0] + 1 if len(phases) > 0 else 1
                        ph2 = phases[1] + 1 if len(phases) > 1 else 2
                        dss.run_command(f"new Fault.{fault_name} bus1={target_bus}.{ph1} bus2={target_bus}.{ph2} phases=1 r={f_res}")
                    elif f_type == "LLG":
                        dss.run_command(f"new Fault.{fault_name} bus1={target_bus}.1.2 phases=2 r={f_res}")
                    elif f_type == "LLL":
                        dss.run_command(f"new Fault.{fault_name} bus1={target_bus}.1.2.3 phases=3 r={f_res}")
                    else:
                        dss.run_command(f"new Fault.{fault_name} bus1={target_bus}.1 phases=1 r={f_res}")

        op = solve_operating_point(sim_scenario.generator_p_kw, sim_scenario.generator_q_kvar)

        # 1. Identify candidate PCCs and select metered PCCs
        candidate_pccs = identify_candidate_pccs(topo)
        meter_fraction = getattr(sim_scenario, "meter_fraction", 0.5)
        seed = getattr(sim_scenario, "seed", 42)
        metered_pccs = select_metered_pccs(candidate_pccs, fraction=meter_fraction, seed=seed)

        # 2. Get OpenDSS power flow measurements (meter-informed network representation)
        pcc_measurements = get_pcc_measurements(metered_pccs)

        # 3. Simulate High-Fidelity physical EMT transient waveforms using ATP adapter
        event = sim_scenario.events[0] if sim_scenario.events else None
        if event is None:
            raise RuntimeError(f"No transient event specified for scenario {scenario_id}")

        if hasattr(event, "event_1") and hasattr(event, "event_2"):
            t_off = getattr(event, "time_offset_s", 0.0)
            ev_key = f"{event.event_1.event_type}_{event.event_2.event_type}_coevent_{t_off:.2f}s"
        elif getattr(event, "event_class", "") == "equipment_switch":
            ev_key = f"{event.event_type}_switch"
        else:
            ev_key = "dist_fault_steady"

        atp_case_path = f"src/simulation/atp_cases/case_{ev_key}.ATP"
        self.atp_builder.build(h_net, op, event, atp_case_path)

        # Actual ATP-EMTP execution and waveform extraction directly via ATPRunner/ATPOutputReader
        atp_result = ATPRunner().run(atp_case_path)
        emt_waveforms = ATPOutputReader().read(atp_result, metered_pccs, event)

        # Waveform Integrity Assertions (complying with Rule 21)
        assert emt_waveforms is not None, f"EMT waveform generation failed for {scenario_id}"
        assert emt_waveforms.time_s.ndim == 1
        assert len(emt_waveforms.time_s) == int(10000.0 * 0.1)

        processed_pccs = {}

        # 4. Extract raw physical waveforms on transformer LV secondaries
        for pcc in metered_pccs:
            pcc_id = pcc["pcc_id"]
            if pcc.get("branch_type") == "transformer":
                v_wave = emt_waveforms.pcc_voltages.get(pcc_id)
                i_wave = emt_waveforms.pcc_currents.get(pcc_id)

                assert v_wave is not None, f"Missing voltage waveform for PCC {pcc_id} in scenario {scenario_id}"
                assert i_wave is not None, f"Missing current waveform for PCC {pcc_id} in scenario {scenario_id}"
                assert v_wave.ndim >= 2
                assert i_wave.ndim >= 2
                assert len(emt_waveforms.time_s) == v_wave.shape[0]
                assert len(emt_waveforms.time_s) == i_wave.shape[0]
                assert np.all(np.isfinite(v_wave))
                assert np.all(np.isfinite(i_wave))

                processed_pccs[pcc_id] = {
                    "raw_voltage": v_wave,
                    "raw_current": i_wave
                }

        return SimulationResult(
            time_s=emt_waveforms.time_s,
            metered_pccs=metered_pccs,
            steady_state_measurements=pcc_measurements,
            processed_pccs=processed_pccs
        )
