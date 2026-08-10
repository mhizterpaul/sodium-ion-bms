from opendssdirect import dss
import numpy as np

from src.power_plant.plant import initialize_known_plant
from src.power_plant.operating_point import solve_operating_point
from src.power_plant.measurements import get_pcc_measurements

from src.hidden_network.topology import (
    generate_radial_topology,
    identify_candidate_pccs,
    select_metered_pccs
)
from src.hidden_network.loads import distribute_loads
from src.hidden_network.transformers import get_distribution_transformer_spec
from src.hidden_network.perturbations import apply_topology_reconfiguration

from src.transient.atp_case_builder import ATPCaseBuilder
from src.transient.synchronization import synchronize_measurements
from src.transient.emt_emulator import simulate_emt_waveforms
from src.features.wavelet_processor import process_pcc_waveforms

class SimulationResult:
    def __init__(self, time_s: np.ndarray, metered_pccs: list[dict], steady_state_measurements: dict, processed_pccs: dict):
        self.time_s = time_s
        self.metered_pccs = metered_pccs
        self.steady_state_measurements = steady_state_measurements
        self.processed_pccs = processed_pccs

class CoSimulationRunner:
    def __init__(self):
        self.atp_builder = ATPCaseBuilder()

    def run_scenario(self, sim_scenario) -> SimulationResult:
        """
        Coordinates full co-simulation run: DSS operating point + EMT transient waveform simulation.
        Returns a structured SimulationResult object.
        """
        initialize_known_plant()

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

        op = solve_operating_point(sim_scenario.generator_p_kw, sim_scenario.generator_q_kvar)

        # 1. Identify candidate PCCs and select metered PCCs
        candidate_pccs = identify_candidate_pccs(topo)
        meter_fraction = getattr(sim_scenario, "meter_fraction", 0.5)
        seed = getattr(sim_scenario, "seed", 42)
        metered_pccs = select_metered_pccs(candidate_pccs, fraction=meter_fraction, seed=seed)

        # 2. Get OpenDSS power flow measurements (meter-informed network representation)
        pcc_measurements = get_pcc_measurements(metered_pccs)

        # 3. Simulate High-Fidelity physical EMT transient waveforms
        event = sim_scenario.events[0] if sim_scenario.events else None
        if event is None:
            raise RuntimeError(f"No transient event specified for scenario {scenario_id}")

        self.atp_builder.build(op, h_net, event, f"src/simulation/atp_cases/{scenario_id}_{event.event_type}.ATP")

        # EMT Simulator producing actual waveforms
        emt_waveforms = simulate_emt_waveforms(metered_pccs, pcc_measurements, event, fs=10000.0, duration=0.1)

        # Waveform Integrity Assertions (complying with Rule 21)
        assert emt_waveforms is not None, f"EMT waveform generation failed for {scenario_id}"
        assert emt_waveforms.time_s.ndim == 1
        assert len(emt_waveforms.time_s) == int(10000.0 * 0.1)

        processed_pccs = {}

        # 4. Steady-state normalization, FFT, and SWT Decomposition (complying with Rule 7, 8, 19, 21)
        for pcc in metered_pccs:
            pcc_id = pcc["pcc_id"]
            v_wave = emt_waveforms.pcc_voltages.get(pcc_id)
            i_wave = emt_waveforms.pcc_currents.get(pcc_id)

            # Run Waveform assertions for each phase/channel
            assert v_wave is not None, f"Missing voltage waveform for PCC {pcc_id} in scenario {scenario_id}"
            assert i_wave is not None, f"Missing current waveform for PCC {pcc_id} in scenario {scenario_id}"
            assert v_wave.ndim >= 2
            assert i_wave.ndim >= 2
            assert len(emt_waveforms.time_s) == v_wave.shape[0]
            assert len(emt_waveforms.time_s) == i_wave.shape[0]
            assert np.all(np.isfinite(v_wave))
            assert np.all(np.isfinite(i_wave))

            # Normalization window precedes event (event start at 0.02s)
            processed_pcc = process_pcc_waveforms(pcc_id, emt_waveforms.time_s, v_wave, i_wave, event_start=0.02)
            processed_pccs[pcc_id] = processed_pcc

        return SimulationResult(
            time_s=emt_waveforms.time_s,
            metered_pccs=metered_pccs,
            steady_state_measurements=pcc_measurements,
            processed_pccs=processed_pccs
        )
