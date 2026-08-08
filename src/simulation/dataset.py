import os
import csv
import random
import numpy as np
from src.simulation.scenario import HiddenNetworkScenario, SimulationScenario
from src.simulation.runner import CoSimulationRunner
from src.hidden_network.topology import generate_radial_topology
from src.hidden_network.loads import distribute_loads
from src.hidden_network.perturbations import apply_topology_reconfiguration
from src.transient.events import TransientEvent

def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = False):
    """
    Orchestrates the program experiments dataset generation by sweeping through QSTS scenarios,
    coupling OpenDSS operating conditions with transient events, and exporting the synchronized features.
    If write_to_disk is True, it will export to scenario_results.csv. By default, it generates in-memory.
    """
    print(f"INFO: Sweeping and generating {n_scenarios} electromagnetic-transient scenarios (In-Memory)...")
    runner = CoSimulationRunner()
    results = []

    events_pool = [
        "transformer_inrush",
        "capacitor_switching",
        "motor_start",
        "feeder_switching",
        "temporary_fault"
    ]

    for idx in range(n_scenarios):
        scenario_id = f"scenario_{idx}"

        feeder_idx = (idx % 3) + 1
        num_buses = random.randint(20, 80)
        has_ring = (idx in [3, 7, 11])
        line_mult = 1.0 + 0.1 * np.sin(idx)

        base_topo = generate_radial_topology(feeder_idx, num_buses)
        modified_topo = apply_topology_reconfiguration(base_topo, has_ring, line_mult)

        loads_dist = distribute_loads(modified_topo["buses"])

        # Perturb load compositions: linear, non-linear, heavy-duty
        # Scenario indices dictate different predominant load categories
        if idx % 3 == 0:
            load_comp = {"linear": 0.7, "non_linear": 0.15, "heavy_duty": 0.15}
        elif idx % 3 == 1:
            load_comp = {"linear": 0.15, "non_linear": 0.7, "heavy_duty": 0.15}
        else:
            load_comp = {"linear": 0.15, "non_linear": 0.15, "heavy_duty": 0.7}

        # Perturb transformer loading dynamically across scenarios
        trans_load_val = 30.0 + 5.0 * (idx % 10) # range: 30% to 75%

        h_net_scen = HiddenNetworkScenario(
            scenario_id=scenario_id,
            num_buses=len(modified_topo["buses"]),
            num_lines=len(modified_topo["lines"]),
            topology=modified_topo,
            line_parameters={"mult": line_mult},
            loads=loads_dist,
            load_composition=load_comp,
            motor_penetration=0.08,
            capacitor_configuration={},
            transformer_loading={"trans1": trans_load_val, "trans2": trans_load_val, "trans3": trans_load_val},
            switching_events=[]
        )

        event_type = events_pool[idx % len(events_pool)]
        if event_type == "temporary_fault" and len(modified_topo["lines"]) > 0:
            fault_target = random.choice(modified_topo["lines"])["name"]
        else:
            fault_target = f"transformer{feeder_idx}"

        t_event = TransientEvent(
            event_type=event_type,
            start_time_s=20.0,
            duration_s=0.1,
            target=fault_target,
            parameters={"energization_angle_deg": 0.0, "fault_resistance_ohm": 0.05}
        )

        sim_scen = SimulationScenario(
            hidden_network=h_net_scen,
            generator_p_kw=1500.0,
            generator_q_kvar=0.0,
            events=[t_event]
        )

        features = runner.run_scenario(sim_scen)

        record = {
            "scenario_index": idx,
            "topology_type": "ring" if has_ring else "radial",
            "simulated_event": event_type,
            "active_feeder": feeder_idx,
            "switching_timestamp_s": float(t_event.start_time_s),
            "downstream_topology_buses": str(modified_topo["buses"]),
            "downstream_topology_lines": str([(ln["name"], ln["bus1"], ln["bus2"], ln["length"]) for ln in modified_topo["lines"]]),
            "hidden_total_buses": len(modified_topo["buses"]),
            "hidden_total_edges": len(modified_topo["lines"]),
            "hidden_motor_count": len(loads_dist["motors"]),
            "hidden_capacitor_count": len(loads_dist["capacitors"])
        }
        record.update(features)
        results.append(record)

    if write_to_disk:
        csv_dir = "src/simulation"
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, "scenario_results.csv")

        headers = list(results[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)
        print(f"INFO: Successfully exported synchronized boundary dataset of {n_scenarios} scenarios to {csv_path}")
    else:
        print(f"INFO: Generated dataset of {n_scenarios} scenarios in-memory successfully.")
    return results

if __name__ == "__main__":
    generate_experiments_dataset()
