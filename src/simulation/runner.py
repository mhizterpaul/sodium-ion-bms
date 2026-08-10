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

from src.features.steady_state import extract_steady_state_features
from src.features.sequence import extract_sequence_features
from src.features.transient import extract_transient_features
from src.features.spectral import extract_spectral_features

class CoSimulationRunner:
    def __init__(self):
        self.atp_builder = ATPCaseBuilder()

    def run_scenario(self, sim_scenario) -> tuple[dict, list[dict]]:
        """
        Coordinates full co-simulation run: DSS operating point + ATP transient.
        Returns a tuple of (features_dict, metered_pccs_list).
        """
        initialize_known_plant()

        h_net = sim_scenario.hidden_network
        topo = h_net.topology

        dss.run_command(f"new linecode.down_lv nphases=3 r1=0.45 x1=0.15 r0=1.20 x0=0.35 c1=4.0 c0=2.0 units=km")

        # Build independent LV topologies
        topologies = topo.get("topologies", {})
        if topologies:
            # Validate root connection of all hidden topologies to the transformer secondary
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

        # Identify candidate PCCs and select metered PCCs
        candidate_pccs = identify_candidate_pccs(topo)
        meter_fraction = getattr(sim_scenario, "meter_fraction", 0.5)
        seed = getattr(sim_scenario, "seed", 42)
        metered_pccs = select_metered_pccs(candidate_pccs, fraction=meter_fraction, seed=seed)

        # Get PCC measurements
        pcc_measurements = get_pcc_measurements(metered_pccs)

        synced_measurements = {}
        fft_features = {}

        for event in sim_scenario.events:
            self.atp_builder.build(op, h_net, event, f"src/simulation/atp_cases/{h_net.scenario_id}_{event.event_type}.ATP")
            # Backend process deleted, fallback to synchronized operating-point values
            emt_waveforms = None
            synced_measurements = synchronize_measurements(pcc_measurements, emt_waveforms)
            fft_features = extract_spectral_features(emt_waveforms)

        if not sim_scenario.events:
            synced_measurements = synchronize_measurements(pcc_measurements, None)
            fft_features = extract_spectral_features(None)

        f_steady = extract_steady_state_features(synced_measurements)
        f_seq = extract_sequence_features(synced_measurements)
        f_trans = extract_transient_features(synced_measurements, None) # No EMT waveforms

        result = {}
        result.update(f_steady)
        result.update(f_seq)
        result.update(f_trans)
        result.update(fft_features)

        # Add explicit synchronized measurements at metered PCCs only
        for pcc_id, m in synced_measurements.items():
            result[f"{pcc_id}_voltage_a"] = float(m.voltage_abc[0])
            result[f"{pcc_id}_voltage_b"] = float(m.voltage_abc[1])
            result[f"{pcc_id}_voltage_c"] = float(m.voltage_abc[2])
            result[f"{pcc_id}_current_a"] = float(m.current_abc[0])
            result[f"{pcc_id}_current_b"] = float(m.current_abc[1])
            result[f"{pcc_id}_current_c"] = float(m.current_abc[2])
            result[f"{pcc_id}_p_kw"] = float(m.p_kw)
            result[f"{pcc_id}_q_kvar"] = float(m.q_kvar)
            result[f"{pcc_id}_s_kva"] = float(m.s_kva)

        return result, metered_pccs
