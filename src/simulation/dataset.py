import os
import csv
import json
import numpy as np
import pandas as pd
from pathlib import Path

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
from src.hidden_network.pcc_meters import get_pcc_measurements

def validate_dataset_1(df_1: pd.DataFrame):
    """
    Validates Dataset 1 schema, numerical integrity, and waveform dimensions.
    """
    required_cols = [
        "gt_scenario_id", "gt_feeder_id", "gt_topology_type",
        "gt_estimated_number_of_buses", "gt_estimated_number_of_branches",
        "gt_estimated_z_eq_ohm", "gt_estimated_r_eq_ohm", "gt_estimated_x_eq_ohm",
        "obs_steady_state_time", "obs_steady_state_voltage_abc", "obs_steady_state_current_abc"
    ]
    for col in required_cols:
        if col not in df_1.columns:
            raise ValueError(f"Dataset 1 validation error: missing required column '{col}'")

    if "gt_line_parameter_multiplier" in df_1.columns:
        raise ValueError("Dataset 1 validation error: 'line_parameter_multiplier' must be removed from Dataset 1!")

    for idx, row in df_1.iterrows():
        if row["gt_estimated_number_of_buses"] <= 0:
            raise ValueError(f"Dataset 1 row {idx}: estimated_number_of_buses must be > 0")
        if row["gt_estimated_number_of_branches"] <= 0:
            raise ValueError(f"Dataset 1 row {idx}: estimated_number_of_branches must be > 0")
        for z_col in ["gt_estimated_z_eq_ohm", "gt_estimated_r_eq_ohm", "gt_estimated_x_eq_ohm"]:
            if not np.isfinite(row[z_col]):
                raise ValueError(f"Dataset 1 row {idx}: non-finite impedance in {z_col}")

        t = json.loads(row["obs_steady_state_time"])
        v_abc = json.loads(row["obs_steady_state_voltage_abc"])
        i_abc = json.loads(row["obs_steady_state_current_abc"])

        if len(t) == 0:
            raise ValueError(f"Dataset 1 row {idx}: steady_state_time is empty")
        if len(v_abc) != 3 or len(i_abc) != 3:
            raise ValueError(f"Dataset 1 row {idx}: steady-state voltage/current must have 3 phases")
        if any(len(p) != len(t) for p in v_abc) or any(len(p) != len(t) for p in i_abc):
            raise ValueError(f"Dataset 1 row {idx}: phase length does not match time length")

    print("INFO: Dataset 1 validation passed successfully.")

def validate_dataset_2(df_2: pd.DataFrame):
    """
    Validates Dataset 2 schema, numerical integrity, and transient waveform dimensions.
    """
    required_cols = [
        "gt_scenario_id", "gt_feeder_id", "gt_pcc_id", "gt_event_type",
        "gt_effective_load_kw", "gt_load_type", "gt_start_timestamp_s", "gt_end_timestamp_s",
        "obs_raw_transient_time", "obs_raw_transient_v", "obs_raw_transient_i",
        "obs_norm_transient_time", "obs_norm_transient_v", "obs_norm_transient_i"
    ]
    for col in required_cols:
        if col not in df_2.columns:
            raise ValueError(f"Dataset 2 validation error: missing required column '{col}'")

    for idx, row in df_2.iterrows():
        t = json.loads(row["obs_raw_transient_time"])
        v_raw = json.loads(row["obs_raw_transient_v"])
        i_raw = json.loads(row["obs_raw_transient_i"])
        v_norm = json.loads(row["obs_norm_transient_v"])
        i_norm = json.loads(row["obs_norm_transient_i"])

        if len(t) == 0:
            raise ValueError(f"Dataset 2 row {idx}: transient time vector is empty")
        if len(v_raw) != 3 or len(i_raw) != 3:
            raise ValueError(f"Dataset 2 row {idx}: raw waveform must have 3 phases")
        if len(v_norm) != 3 or len(i_norm) != 3:
            raise ValueError(f"Dataset 2 row {idx}: normalized waveform must have 3 phases")
        if any(len(p) != len(t) for p in v_raw) or any(len(p) != len(t) for p in i_raw):
            raise ValueError(f"Dataset 2 row {idx}: raw phase length mismatch")
        if any(len(p) != len(t) for p in v_norm) or any(len(p) != len(t) for p in i_norm):
            raise ValueError(f"Dataset 2 row {idx}: normalized phase length mismatch")

    print("INFO: Dataset 2 validation passed successfully.")


def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = True):
    """
    Orchestrates experiment dataset generation:
    1. Sweeps through OpenDSS/QSTS operating point scenarios using CoSimulationRunner.
    2. Runs EMT transient simulations via ATPRunner to acquire 3-phase waveforms.
    3. Extracts steady-state waveforms directly from pre-event solved simulation measurements.
    4. Normalizes transient waveforms using steady-state transformer references.
    5. Serializes two decoupled CSV datasets (Dataset 1 and Dataset 2).
    """
    print(f"INFO: Sweeping and generating {n_scenarios} OpenDSS QSTS/operating point scenarios...")
    runner = CoSimulationRunner()

    rows_1 = []
    rows_2 = []

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

        rng = np.random.default_rng(idx + 1000)

        feeder_idx = (idx % 3) + 1
        has_ring = (config["topology"] == "ring")
        line_mult = float(config["line_mult"])

        # 1. Generate active, independent LV networks
        topologies = {}
        all_buses = []
        all_lines = []
        is_ring = False

        for f_idx in [1, 2, 3]:
            num_buses_f = int(rng.integers(20, 35))
            base_f = generate_radial_topology(f_idx, num_buses_f, rng=rng)

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

        # 2. Distribute loads
        loads1 = distribute_loads(topologies[1]["buses"], rng=rng)
        loads2 = distribute_loads(topologies[2]["buses"], rng=rng)
        loads3 = distribute_loads(topologies[3]["buses"], rng=rng)

        loads_dist = {
            "loads": loads1["loads"] + loads2["loads"] + loads3["loads"],
            "capacitors": loads1["capacitors"] + loads2["capacitors"] + loads3["capacitors"],
            "motors": loads1["motors"] + loads2["motors"] + loads3["motors"],
            "ders": loads1["ders"] + loads2["ders"] + loads3["ders"]
        }

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

        # Execute simulation
        sim_result = runner.run_scenario(sim_scen)
        time_s = sim_result.time_s
        pre_event_mask = time_s < t_event.start_time_s

        # 3. BUILD DATASET 1 RECORDS
        for f_id in [1, 2, 3]:
            pcc_id = f"trans{f_id}_lv_pcc"
            pcc_res = sim_result.processed_pccs.get(pcc_id)

            z_est = 0.0
            r_est = 0.0
            x_est = 0.0
            if pcc_res:
                v_lv_avg = float(np.mean(pcc_res.raw_voltage))
                i_lv_avg = float(np.mean(pcc_res.raw_current))
                p_val = float(sim_result.steady_state_measurements[pcc_id]["p_kw"]) * 1000.0
                q_val = float(sim_result.steady_state_measurements[pcc_id]["q_kvar"]) * 1000.0

                z_est = v_lv_avg / (i_lv_avg + 1e-6)
                r_est = p_val / (3.0 * i_lv_avg**2 + 1e-6)
                x_est = q_val / (3.0 * i_lv_avg**2 + 1e-6)

            # Extract 3-phase steady-state waveforms directly from solved pre-event simulation data
            if pcc_res is not None and pcc_res.raw_voltage is not None and pcc_res.raw_voltage.shape[0] == len(time_s):
                # Extract pre-event window or actual raw solved waveforms
                v_raw_ss = pcc_res.raw_voltage
                i_raw_ss = pcc_res.raw_current
                v_ss_abc = [v_raw_ss[:, 0].tolist(), v_raw_ss[:, 1].tolist(), v_raw_ss[:, 2].tolist()]
                i_ss_abc = [i_raw_ss[:, 0].tolist(), i_raw_ss[:, 1].tolist(), i_raw_ss[:, 2].tolist()]
            else:
                v_ss_abc = [[0.0]*len(time_s), [0.0]*len(time_s), [0.0]*len(time_s)]
                i_ss_abc = [[0.0]*len(time_s), [0.0]*len(time_s), [0.0]*len(time_s)]

            row_1 = {
                "gt_scenario_id": f"{scenario_id}_feeder_{f_id}",
                "gt_feeder_id": f"feeder_{f_id}",
                "gt_topology_type": "ring" if topologies[f_id].get("is_ring") else "radial",
                "gt_estimated_number_of_buses": len(topologies[f_id]["buses"]),
                "gt_estimated_number_of_branches": len(topologies[f_id]["lines"]),
                "gt_estimated_z_eq_ohm": round(float(z_est), 4),
                "gt_estimated_r_eq_ohm": round(float(r_est), 4),
                "gt_estimated_x_eq_ohm": round(float(x_est), 4),
                "obs_steady_state_time": json.dumps(time_s.tolist()),
                "obs_steady_state_voltage_abc": json.dumps(v_ss_abc),
                "obs_steady_state_current_abc": json.dumps(i_ss_abc)
            }

            if pcc_res:
                row_1[f"obs_{pcc_id}_voltage_mag_avg"] = float(np.mean(pcc_res.raw_voltage))
                row_1[f"obs_{pcc_id}_current_mag_avg"] = float(np.mean(pcc_res.raw_current))
                row_1[f"obs_{pcc_id}_p_kw"] = float(sim_result.steady_state_measurements[pcc_id]["p_kw"])
                row_1[f"obs_{pcc_id}_q_kvar"] = float(sim_result.steady_state_measurements[pcc_id]["q_kvar"])
                row_1[f"obs_{pcc_id}_s_kva"] = float(sim_result.steady_state_measurements[pcc_id]["s_kva"])
                row_1[f"obs_{pcc_id}_pf"] = float(sim_result.steady_state_measurements[pcc_id]["pf"])

            rows_1.append(row_1)

        # 4. BUILD DATASET 2 RECORDS
        for pcc in sim_result.metered_pccs:
            pcc_id = pcc["pcc_id"]
            if "trans1" in pcc_id or "down_1_" in pcc_id:
                f_id = 1
            elif "trans2" in pcc_id or "down_2_" in pcc_id:
                f_id = 2
            else:
                f_id = 3

            parent_trans_pcc_id = f"trans{f_id}_lv_pcc"
            pcc_res = sim_result.processed_pccs.get(parent_trans_pcc_id)

            if pcc_res is None:
                raise RuntimeError(f"Missing required EMT waveform for transformer {parent_trans_pcc_id}")

            v_raw = pcc_res.raw_voltage  # shape (N, 3)
            i_raw = pcc_res.raw_current  # shape (N, 3)

            v_raw_abc = [v_raw[:, 0].tolist(), v_raw[:, 1].tolist(), v_raw[:, 2].tolist()]
            i_raw_abc = [i_raw[:, 0].tolist(), i_raw[:, 1].tolist(), i_raw[:, 2].tolist()]

            v_norm = pcc_res.normalized_voltage  # shape (N, 3)
            i_norm = pcc_res.normalized_current  # shape (N, 3)

            v_norm_abc = [v_norm[:, 0].tolist(), v_norm[:, 1].tolist(), v_norm[:, 2].tolist()]
            i_norm_abc = [i_norm[:, 0].tolist(), i_norm[:, 1].tolist(), i_norm[:, 2].tolist()]

            row_2 = {
                "gt_scenario_id": scenario_id,
                "gt_feeder_id": f"feeder_{f_id}",
                "gt_pcc_id": pcc_id,
                "gt_event_type": event_type,
                "gt_simulated_event": event_type,
                "gt_effective_load_kw": float(sim_result.steady_state_measurements[pcc_id]["p_kw"]) if pcc_id in sim_result.steady_state_measurements else 0.0,
                "gt_load_type": config["load_comp"],
                "gt_start_timestamp_s": float(t_event.start_time_s),
                "gt_end_timestamp_s": float(t_event.start_time_s + t_event.duration_s),
                "obs_scenario_id": scenario_id,
                "obs_feeder_id": f"feeder_{f_id}",
                "obs_pcc_id": pcc_id,
                "obs_steady_state_v_ref": json.dumps(list(sim_result.steady_state_measurements[parent_trans_pcc_id]["v_mags"])),
                "obs_steady_state_i_ref": json.dumps(list(sim_result.steady_state_measurements[parent_trans_pcc_id]["i_mags"])),
                "obs_raw_transient_time": json.dumps(time_s.tolist()),
                "obs_raw_transient_v": json.dumps(v_raw_abc),
                "obs_raw_transient_i": json.dumps(i_raw_abc),
                "obs_norm_transient_time": json.dumps(time_s.tolist()),
                "obs_norm_transient_v": json.dumps(v_norm_abc),
                "obs_norm_transient_i": json.dumps(i_norm_abc)
            }
            rows_2.append(row_2)

    df_1 = pd.DataFrame(rows_1)
    df_2 = pd.DataFrame(rows_2)

    # Validate generated datasets before persistence
    validate_dataset_1(df_1)
    validate_dataset_2(df_2)

    if write_to_disk:
        dir_path = Path("src/simulation")
        dir_path.mkdir(parents=True, exist_ok=True)
        df_1.to_csv(dir_path / "dataset_1.csv", index=False)
        df_2.to_csv(dir_path / "dataset_2.csv", index=False)
        print(f"INFO: Successfully written validated datasets to {dir_path / 'dataset_1.csv'} and {dir_path / 'dataset_2.csv'}")

    return df_1, df_2

if __name__ == "__main__":
    generate_experiments_dataset(n_scenarios=15, write_to_disk=True)
