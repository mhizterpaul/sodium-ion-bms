from opendssdirect import dss
import numpy as np

from src.power_plant.plant import initialize_known_plant
from src.power_plant.operating_point import solve_operating_point
from src.power_plant.measurements import get_boundary_measurements

from src.hidden_network.topology import generate_radial_topology
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

    def run_scenario(self, sim_scenario) -> dict:
        """
        Coordinates full co-simulation run: DSS operating point + ATP transient.
        """
        initialize_known_plant()

        h_net = sim_scenario.hidden_network
        topo = h_net.topology

        dss.run_command(f"new linecode.down_lv nphases=3 r1=0.45 x1=0.15 r0=1.20 x0=0.35 c1=4.0 c0=2.0 units=km")
        for ln in topo["lines"]:
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
        dss_measurements = get_boundary_measurements()

        synced_measurements = {}
        fft_features = {}

        for event in sim_scenario.events:
            self.atp_builder.build(op, h_net, event, f"src/simulation/atp_cases/{h_net.scenario_id}_{event.event_type}.ATP")
            # Backend process deleted, fallback to synchronized operating-point values
            emt_waveforms = None
            synced_measurements = synchronize_measurements(dss_measurements, emt_waveforms)
            fft_features = extract_spectral_features(emt_waveforms)

        if not sim_scenario.events:
            synced_measurements = synchronize_measurements(dss_measurements, None)
            fft_features = extract_spectral_features(None)

        f_steady = extract_steady_state_features(synced_measurements)
        f_seq = extract_sequence_features(synced_measurements)
        f_trans = extract_transient_features(synced_measurements)

        result = {}
        result.update(f_steady)
        result.update(f_seq)
        result.update(f_trans)
        result.update(fft_features)

        return result
