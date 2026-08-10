import os
import csv
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
from src.transient.emt_emulator import simulate_emt_waveforms
from src.features.wavelet_processor import process_pcc_waveforms

def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = False):
    """
    Orchestrates the program experiments dataset generation by sweeping through scenarios,
    generating 3 independent LV networks under Option A, solving OpenDSS operating points,
    running EMT simulations to acquire three-phase transient waveforms, and outputting
    two distinct, decoupled datasets.
    """
    print(f"INFO: Sweeping and generating {n_scenarios} OpenDSS QSTS/operating point scenarios (In-Memory)...")
    runner = CoSimulationRunner()

    dataset_1 = []
    dataset_2 = []

    # Explicit scenario configuration matrix (perfectly balanced to prevent confounded factors)
    scenario_configs = [
        {"topology": "radial", "buses": 30, "line_mult": 0.95, "load_comp": "linear", "event": "transformer_inrush"},
        {"topology": "radial", "buses": 45, "line_mult": 1.05, "load_comp": "non_linear", "event": "capacitor_switching"},
        {"topology": "ring",   "buses": 60, "line_mult": 1.15, "load_comp": "heavy_duty", "event": "motor_start"},
        {"topology": "radial", "buses": 25, "line_mult": 0.90, "load_comp": "linear", "event": "feeder_switching"},
        {"topology": "ring",   "buses": 35, "line_mult": 1.00, "load_comp": "non_linear", "event": "temporary_fault"},
        {"topology": "radial", "buses": 50, "line_mult": 1.10, "load_comp": "heavy_duty", "event": "transformer_inrush"},
        {"topology": "ring",   "buses": 55, "line_mult": 1.20, "load_comp": "linear", "event": "capacitor_switching"},
        {"topology": "radial", "buses": 40, "line_mult": 0.98, "load_comp": "non_linear", "event": "motor_start"},
        {"topology": "ring",   "buses": 30, "line_mult": 1.02, "load_comp": "heavy_duty", "event": "feeder_switching"},
        {"topology": "radial", "buses": 65, "line_mult": 1.08, "load_comp": "linear", "event": "temporary_fault"},
        {"topology": "ring",   "buses": 70, "line_mult": 1.12, "load_comp": "non_linear", "event": "transformer_inrush"},
        {"topology": "radial", "buses": 38, "line_mult": 0.92, "load_comp": "heavy_duty", "event": "capacitor_switching"},
        {"topology": "ring",   "buses": 48, "line_mult": 1.04, "load_comp": "linear", "event": "motor_start"},
        {"topology": "radial", "buses": 58, "line_mult": 1.16, "load_comp": "non_linear", "event": "feeder_switching"},
        {"topology": "ring",   "buses": 28, "line_mult": 0.88, "load_comp": "heavy_duty", "event": "temporary_fault"}
    ]

    for idx in range(min(n_scenarios, len(scenario_configs))):
        scenario_id = f"scenario_{idx}"
        config = scenario_configs[idx]

        # Local seeded RNG for perfect reproducibility
        rng = np.random.default_rng(idx + 1000)

        feeder_idx = (idx % 3) + 1
        has_ring = (config["topology"] == "ring")
        line_mult = float(config["line_mult"])

        # 1. Generate three active, independent LV networks (Option A)
        topologies = {}
        all_buses = []
        all_lines = []
        is_ring = False

        for f_idx in [1, 2, 3]:
            # Generate radial topology using rng
            num_buses_f = int(rng.integers(20, 35))
            base_f = generate_radial_topology(f_idx, num_buses_f, rng=rng)

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
        loads1 = distribute_loads(topologies[1]["buses"], rng=rng)
        loads2 = distribute_loads(topologies[2]["buses"], rng=rng)
        loads3 = distribute_loads(topologies[3]["buses"], rng=rng)

        loads_dist = {
            "loads": loads1["loads"] + loads2["loads"] + loads3["loads"],
            "capacitors": loads1["capacitors"] + loads2["capacitors"] + loads3["capacitors"],
            "motors": loads1["motors"] + loads2["motors"] + loads3["motors"],
            "ders": loads1["ders"] + loads2["ders"] + loads3["ders"]
        }

        # Load composition perturbations
        if config["load_comp"] == "linear":
            load_comp = {"linear": 0.7, "non_linear": 0.15, "heavy_duty": 0.15}
        elif config["load_comp"] == "non_linear":
            load_comp = {"linear": 0.15, "non_linear": 0.7, "heavy_duty": 0.15}
        else:
            load_comp = {"linear": 0.15, "non_linear": 0.15, "heavy_duty": 0.7}

        trans_load_val = float(30.0 + 5.0 * (idx % 10))

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

        event_type = config["event"]

        # Use actual registered element name for faults
        if event_type == "temporary_fault" and len(modified_topo["lines"]) > 0:
            fault_target = str(rng.choice(modified_topo["lines"])["name"])
        else:
            fault_target = f"trans{feeder_idx}"

        t_event = TransientEvent(
            event_type=event_type,
            start_time_s=0.02,
            duration_s=0.04,
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

        # Run OpenDSS + EMT Simulation via CoSimulationRunner
        sim_result = runner.run_scenario(sim_scen)

        # 3. CONSTRUCT DATASET 1 (Scenario-Based Dataset)
        gt_1 = {
            "scenario_id": scenario_id,
            "network_id": f"feeder_{feeder_idx}",
            "topology_type": "ring" if is_ring else "radial",
            "hidden_total_buses": len(modified_topo["buses"]),
            "hidden_total_edges": len(modified_topo["lines"]),
            "line_parameter_multiplier": line_mult
        }

        # Strictly limited to the LV transformer monitoring device steady-state measurements and transformer edge LV smart-meter measurements.
        obs_1_features = {}
        for pcc_id in ["trans1_lv_pcc", "trans2_lv_pcc", "trans3_lv_pcc"]:
            pcc_res = sim_result.processed_pccs.get(pcc_id)
            if pcc_res:
                obs_1_features[f"{pcc_id}_voltage_mag_avg"] = float(np.mean(pcc_res.raw_voltage))
                obs_1_features[f"{pcc_id}_current_mag_avg"] = float(np.mean(pcc_res.raw_current))
                obs_1_features[f"{pcc_id}_p_kw"] = float(sim_result.steady_state_measurements[pcc_id]["p_kw"])
                obs_1_features[f"{pcc_id}_q_kvar"] = float(sim_result.steady_state_measurements[pcc_id]["q_kvar"])
                obs_1_features[f"{pcc_id}_s_kva"] = float(sim_result.steady_state_measurements[pcc_id]["s_kva"])
                obs_1_features[f"{pcc_id}_pf"] = float(sim_result.steady_state_measurements[pcc_id]["pf"])
                obs_1_features[f"{pcc_id}_voltage_unbalance_pct"] = float(sim_result.steady_state_measurements[pcc_id]["v_unbalance_pct"])
                obs_1_features[f"{pcc_id}_current_unbalance_pct"] = float(sim_result.steady_state_measurements[pcc_id]["i_unbalance_pct"])

        obs_1 = {
            "scenario_id": scenario_id,
            "features": obs_1_features
        }
        dataset_1.append({"ground_truth": gt_1, "observations": obs_1})

        # 4. CONSTRUCT DATASET 2 (Event-Based Dataset)
        for pcc_id, processed in sim_result.processed_pccs.items():
            obs_2 = {
                "scenario_id": scenario_id,
                "network_state_id": f"state_{config['topology']}_{config['buses']}_{config['line_mult']}",
                "event_id": event_type,
                "pcc_id": pcc_id,
                "steady_state_reference": {
                    "v_mags_ss": list(sim_result.steady_state_measurements[pcc_id]["v_mags"]),
                    "i_mags_ss": list(sim_result.steady_state_measurements[pcc_id]["i_mags"])
                },
                "raw_transient_waveform": {
                    "time": list(sim_result.time_s),
                    "voltage_abc": processed.raw_voltage.tolist(),
                    "current_abc": processed.raw_current.tolist()
                },
                "normalized_transient_waveform": {
                    "voltage_abc": processed.normalized_voltage.tolist(),
                    "current_abc": processed.normalized_current.tolist()
                },
                "fft": {
                    "voltage": [fft.tolist() for fft in processed.voltage_fft],
                    "current": [fft.tolist() for fft in processed.current_fft]
                },
                "swt": {
                    "voltage": [[[cA.tolist(), cD.tolist()] for cA, cD in p_swt] for p_swt in processed.voltage_swt],
                    "current": [[[cA.tolist(), cD.tolist()] for cA, cD in p_swt] for p_swt in processed.current_swt]
                },
                "features": processed.features
            }

            gt_2 = {
                "scenario_id": scenario_id,
                "simulated_event": event_type,
                "switching_timestamp_s": float(t_event.start_time_s)
            }
            dataset_2.append({"ground_truth": gt_2, "observations": obs_2})

    print(f"INFO: Generated Dataset 1 and Dataset 2 of {n_scenarios} scenarios in-memory successfully.")
    return dataset_1, dataset_2

if __name__ == "__main__":
    generate_experiments_dataset()
