import os
import csv
import random
import numpy as np
from src.simulation.scenario import HiddenNetworkScenario, SimulationScenario
from src.simulation.runner import CoSimulationRunner
from src.hidden_network.topology import (
    generate_radial_topology,
    identify_candidate_pccs,
    select_metered_pccs
)
from src.hidden_network.loads import distribute_loads
from src.hidden_network.perturbations import apply_topology_reconfiguration
from src.transient.events import TransientEvent
from src.power_plant.measurements import get_pcc_measurements
from src.transient.synchronization import synchronize_measurements
from src.features.steady_state import extract_steady_state_features
from src.features.sequence import extract_sequence_features

def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = False):
    """
    Orchestrates the program experiments dataset generation by sweeping through scenarios,
    generating 3 independent LV networks under Option A, solving OpenDSS operating points,
    and outputting two strictly decoupled datasets (Dataset 1 and Dataset 2).
    """
    print(f"INFO: Sweeping and generating {n_scenarios} OpenDSS QSTS/operating point scenarios (In-Memory)...")
    runner = CoSimulationRunner()

    dataset_1 = []
    dataset_2 = []

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
        has_ring = (idx in [3, 7, 11])
        line_mult = 1.0 + 0.1 * np.sin(idx)

        # 1. Generate three active, independent LV networks (Option A)
        topologies = {}
        all_buses = []
        all_lines = []
        is_ring = False

        for f_idx in [1, 2, 3]:
            # Generate radial topology
            num_buses_f = random.randint(20, 40)  # slightly reduced to speed up and fit within sandbox
            base_f = generate_radial_topology(f_idx, num_buses_f)

            # Reconfigure topology
            has_ring_f = has_ring and (f_idx == feeder_idx)
            mod_f = apply_topology_reconfiguration(base_f, has_ring_f, line_mult)

            topologies[f_idx] = mod_f
            all_buses.extend(mod_f["buses"])
            all_lines.extend(mod_f["lines"])
            if mod_f.get("is_ring"):
                is_ring = True

        modified_topo = {
            "topologies": topologies,
            "buses": all_buses,
            "lines": all_lines,
            "is_ring": is_ring
        }

        # 2. Distribute loads on all three networks
        loads1 = distribute_loads(topologies[1]["buses"])
        loads2 = distribute_loads(topologies[2]["buses"])
        loads3 = distribute_loads(topologies[3]["buses"])

        loads_dist = {
            "loads": loads1["loads"] + loads2["loads"] + loads3["loads"],
            "capacitors": loads1["capacitors"] + loads2["capacitors"] + loads3["capacitors"],
            "motors": loads1["motors"] + loads2["motors"] + loads3["motors"],
            "ders": loads1["ders"] + loads2["ders"] + loads3["ders"]
        }

        # Load composition perturbations
        if idx % 3 == 0:
            load_comp = {"linear": 0.7, "non_linear": 0.15, "heavy_duty": 0.15}
        elif idx % 3 == 1:
            load_comp = {"linear": 0.15, "non_linear": 0.7, "heavy_duty": 0.15}
        else:
            load_comp = {"linear": 0.15, "non_linear": 0.15, "heavy_duty": 0.7}

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

        # Use actual registered element name for faults
        if event_type == "temporary_fault" and len(modified_topo["lines"]) > 0:
            fault_target = random.choice(modified_topo["lines"])["name"]
        else:
            fault_target = f"trans{feeder_idx}"

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
            events=[t_event],
            meter_fraction=0.5,
            seed=42 + idx
        )

        # Run OpenDSS co-simulation
        features, metered_pccs = runner.run_scenario(sim_scen)

        # 3. CONSTRUCT DATASET 1 (Scenario-based dataset)
        # Ground truth: line parameters (reflective of the network), topology class, and network size
        gt_1 = {
            "scenario_id": scenario_id,
            "line_parameter_multiplier": line_mult,
            "topology_type": "ring" if is_ring else "radial",
            "hidden_total_buses": len(modified_topo["buses"]),
            "hidden_total_edges": len(modified_topo["lines"])
        }

        # Observations: ONLY transformer steady-state readings (trans1_lv_pcc, trans2_lv_pcc, trans3_lv_pcc)
        # Extract them directly to guarantee they are always available and pristine
        trans_pccs = [
            {
                "pcc_id": f"trans{f_id}_lv_pcc",
                "bus": f"feeder{f_id}_sec",
                "parent_bus": f"feeder{f_id}_head",
                "branch_id": f"transformer.trans{f_id}",
                "branch_type": "transformer",
                "meter_eligible": True
            } for f_id in [1, 2, 3]
        ]
        trans_measurements = get_pcc_measurements(trans_pccs)
        synced_trans = synchronize_measurements(trans_measurements, None)
        f_steady_trans = extract_steady_state_features(synced_trans)
        f_seq_trans = extract_sequence_features(synced_trans)

        obs_1_features = {}
        obs_1_features.update(f_steady_trans)
        obs_1_features.update(f_seq_trans)
        for pcc_id, m in synced_trans.items():
            obs_1_features[f"{pcc_id}_voltage_a"] = float(m.voltage_abc[0])
            obs_1_features[f"{pcc_id}_voltage_b"] = float(m.voltage_abc[1])
            obs_1_features[f"{pcc_id}_voltage_c"] = float(m.voltage_abc[2])
            obs_1_features[f"{pcc_id}_current_a"] = float(m.current_abc[0])
            obs_1_features[f"{pcc_id}_current_b"] = float(m.current_abc[1])
            obs_1_features[f"{pcc_id}_current_c"] = float(m.current_abc[2])
            obs_1_features[f"{pcc_id}_p_kw"] = float(m.p_kw)
            obs_1_features[f"{pcc_id}_q_kvar"] = float(m.q_kvar)
            obs_1_features[f"{pcc_id}_s_kva"] = float(m.s_kva)

        obs_1 = {
            "scenario_id": scenario_id,
            "features": obs_1_features
        }
        dataset_1.append({"ground_truth": gt_1, "observations": obs_1})

        # 4. CONSTRUCT DATASET 2 (Event-based dataset)
        # Ground truth: events, event timestamps
        gt_2 = {
            "scenario_id": scenario_id,
            "simulated_event": event_type,
            "switching_timestamp_s": float(t_event.start_time_s)
        }

        # Observations: event timestamps and synchronized readings (PCC observations)
        obs_2 = {
            "scenario_id": scenario_id,
            "metered_pccs": [p["pcc_id"] for p in metered_pccs],
            "features": features
        }
        dataset_2.append({"ground_truth": gt_2, "observations": obs_2})

    print(f"INFO: Generated Dataset 1 and Dataset 2 of {n_scenarios} scenarios in-memory successfully.")
    return dataset_1, dataset_2

if __name__ == "__main__":
    generate_experiments_dataset()
