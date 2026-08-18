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
from src.hidden_network.loads import get_equipment_model, EQUIPMENT_REGISTRY
from src.hidden_network.perturbations import apply_topology_reconfiguration
from src.transient.events import (
    SingleEquipmentSwitchEvent,
    SingleLineFaultEvent,
    EquipmentEquipmentCoEvent,
    EquipmentLineFaultCoEvent
)
from src.simulation.kron_reduction import compute_kron_reduced_impedance
from src.realization.inverse_solver import LatentNetworkRealizationSolver

# Transformer Specifications Matrix for Experimentation (Question 4)
TRANSFORMER_SPECS = {
    "trans1": {
        "spec_id": "tx_spec_std_1500kva",
        "kva": 1500.0,
        "kv_pri": 11.0,
        "kv_sec": 0.415,
        "pct_r": 0.6,
        "pct_x": 4.5
    },
    "trans2": {
        "spec_id": "tx_spec_high_z_1200kva",
        "kva": 1200.0,
        "kv_pri": 11.0,
        "kv_sec": 0.415,
        "pct_r": 0.8,
        "pct_x": 6.0
    },
    "trans3": {
        "spec_id": "tx_spec_low_loss_2000kva",
        "kva": 2000.0,
        "kv_pri": 11.0,
        "kv_sec": 0.415,
        "pct_r": 0.4,
        "pct_x": 3.5
    }
}

def validate_dataset_1(df_1: pd.DataFrame):
    required_cols = [
        "gt_scenario_id", "gt_feeder_id", "gt_topology_type",
        "gt_number_of_buses", "gt_number_of_branches",
        "gt_r_eq_ohm", "gt_x_eq_ohm", "gt_z_eq_ohm",
        "est_number_of_buses", "est_number_of_branches",
        "est_r_eq_ohm", "est_x_eq_ohm", "est_z_eq_ohm",
        "obs_steady_state_time", "obs_steady_state_voltage_abc", "obs_steady_state_current_abc"
    ]
    for col in required_cols:
        if col not in df_1.columns:
            raise ValueError(f"Dataset 1 validation error: missing required column '{col}'")

    if "gt_line_parameter_multiplier" in df_1.columns:
        raise ValueError("Dataset 1 validation error: 'line_parameter_multiplier' must be removed from Dataset 1!")

    for idx, row in df_1.iterrows():
        if row["gt_number_of_buses"] <= 0 or row["est_number_of_buses"] <= 0:
            raise ValueError(f"Dataset 1 row {idx}: number_of_buses must be > 0")

    print("INFO: Dataset 1 validation passed successfully.")

def validate_dataset_2(df_2: pd.DataFrame):
    required_cols = [
        "gt_scenario_id", "gt_transformer_id", "gt_transformer_spec_id", "gt_feeder_id", "gt_pcc_id",
        "gt_event_class", "gt_event_type", "gt_event_start_timestamp_s", "gt_event_end_timestamp_s",
        "obs_raw_transient_time", "obs_raw_transient_v", "obs_raw_transient_i",
        "obs_norm_transient_time", "obs_norm_transient_v", "obs_norm_transient_i",
        "single_event_voltage_signature", "single_event_current_signature"
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

    print("INFO: Dataset 2 validation passed successfully.")

def validate_dataset_3(df_3: pd.DataFrame):
    required_cols = [
        "gt_scenario_id", "gt_transformer_id", "gt_transformer_spec_id", "gt_feeder_id", "gt_pcc_id",
        "gt_coevent_class",
        "gt_event_1_class", "gt_event_1_type", "gt_event_1_start_timestamp_s",
        "gt_event_2_class", "gt_event_2_type", "gt_event_2_start_timestamp_s",
        "gt_time_offset_s",
        "obs_coevent_time", "obs_coevent_v", "obs_coevent_i",
        "obs_composed_single_event_v", "obs_composed_single_event_i",
        "obs_residual_v", "obs_residual_i",
        "residual_voltage_magnitude", "residual_current_magnitude"
    ]
    for col in required_cols:
        if col not in df_3.columns:
            raise ValueError(f"Dataset 3 validation error: missing required column '{col}'")

    for idx, row in df_3.iterrows():
        v_res = json.loads(row["obs_residual_v"])
        i_res = json.loads(row["obs_residual_i"])
        if len(v_res) != 3 or len(i_res) != 3:
            raise ValueError(f"Dataset 3 row {idx}: residual waveform must have 3 phases")
        if not np.isfinite(row["residual_voltage_magnitude"]) or not np.isfinite(row["residual_current_magnitude"]):
            raise ValueError(f"Dataset 3 row {idx}: non-finite residual magnitude")

    print("INFO: Dataset 3 validation passed successfully.")


def generate_experiments_dataset(n_scenarios: int = 15, write_to_disk: bool = True):
    """
    Orchestrates dataset generation for Dataset 1, Dataset 2, and Dataset 3.
    """
    print("INFO: Sweeping scenarios and generating Dataset 1, Dataset 2, and Dataset 3...")
    runner = CoSimulationRunner()
    realization_solver = LatentNetworkRealizationSolver()

    rows_1 = []
    rows_2 = []
    rows_3 = []

    # Signature lookup dictionary for Dataset 3 composition
    # Key: (transformer_spec_id, event_class, event_type, feeder_id) -> dict with 'v_sig', 'i_norm', 'time'
    signature_catalog = {}

    scenario_configs = [
        {"topology": "radial", "buses": 30, "line_mult": 0.95, "load_comp": "linear"},
        {"topology": "radial", "buses": 45, "line_mult": 1.05, "load_comp": "non_linear"},
        {"topology": "ring",   "buses": 60, "line_mult": 1.15, "load_comp": "heavy_duty"},
        {"topology": "radial", "buses": 25, "line_mult": 0.90, "load_comp": "linear"},
        {"topology": "ring",   "buses": 35, "line_mult": 1.00, "load_comp": "non_linear"},
        {"topology": "radial", "buses": 50, "line_mult": 1.10, "load_comp": "heavy_duty"},
        {"topology": "ring",   "buses": 55, "line_mult": 1.20, "load_comp": "linear"},
        {"topology": "radial", "buses": 40, "line_mult": 0.98, "load_comp": "non_linear"},
        {"topology": "ring",   "buses": 30, "line_mult": 1.02, "load_comp": "heavy_duty"},
        {"topology": "radial", "buses": 65, "line_mult": 1.08, "load_comp": "linear"},
        {"topology": "ring",   "buses": 70, "line_mult": 1.12, "load_comp": "non_linear"},
        {"topology": "radial", "buses": 38, "line_mult": 0.92, "load_comp": "heavy_duty"},
        {"topology": "ring",   "buses": 48, "line_mult": 1.04, "load_comp": "linear"},
        {"topology": "radial", "buses": 58, "line_mult": 1.16, "load_comp": "non_linear"},
        {"topology": "ring",   "buses": 28, "line_mult": 0.88, "load_comp": "heavy_duty"}
    ]

    equipment_types = list(EQUIPMENT_REGISTRY.keys())
    fault_types = ["LG", "LL", "LLG", "LLL"]
    fault_phase_map = {
        "LG": (0,),
        "LL": (0, 1),
        "LLG": (0, 1),
        "LLL": (0, 1, 2)
    }

    for idx in range(min(n_scenarios, len(scenario_configs))):
        scenario_id = f"scenario_{idx}"
        config = scenario_configs[idx]
        rng = np.random.default_rng(idx + 1000)

        feeder_idx = (idx % 3) + 1
        has_ring = (config["topology"] == "ring")
        line_mult = float(config["line_mult"])

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

        # --- A. DATASET 1 GENERATION ---
        multi_op_measurements = {1: [], 2: [], 3: []}
        latest_sim_result = None

        for op_idx in range(5):
            trans_load_val = float(30.0 + 10.0 * op_idx)
            h_net_scen = HiddenNetworkScenario(
                scenario_id=f"{scenario_id}_op_{op_idx}",
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

            dummy_ev = SingleEquipmentSwitchEvent(
                equipment_type="ac_motor",
                start_time_s=0.02,
                duration_s=0.04,
                target=f"trans{feeder_idx}",
                parameters={}
            )

            sim_scen = SimulationScenario(
                hidden_network=h_net_scen,
                generator_p_kw=1500.0,
                generator_q_kvar=0.0,
                events=[dummy_ev],
                meter_fraction=0.5,
                seed=42 + idx + op_idx * 100
            )

            sim_result = runner.run_scenario(sim_scen)
            latest_sim_result = sim_result

            for f_id in [1, 2, 3]:
                pcc_id = f"trans{f_id}_lv_pcc"
                if pcc_id in sim_result.steady_state_measurements:
                    multi_op_measurements[f_id].append(sim_result.steady_state_measurements[pcc_id])

        time_s = latest_sim_result.time_s

        for f_id in [1, 2, 3]:
            pcc_id = f"trans{f_id}_lv_pcc"
            pcc_res = latest_sim_result.processed_pccs.get(pcc_id)

            gt_r, gt_x, gt_z = compute_kron_reduced_impedance(topologies[f_id])
            op_meas = multi_op_measurements[f_id]
            est_res = realization_solver.estimate(op_meas)

            v_raw_ss = pcc_res.raw_voltage if pcc_res is not None else np.zeros((len(time_s), 3))
            i_raw_ss = pcc_res.raw_current if pcc_res is not None else np.zeros((len(time_s), 3))

            v_ss_abc = [v_raw_ss[:, 0].tolist(), v_raw_ss[:, 1].tolist(), v_raw_ss[:, 2].tolist()]
            i_ss_abc = [i_raw_ss[:, 0].tolist(), i_raw_ss[:, 1].tolist(), i_raw_ss[:, 2].tolist()]

            row_1 = {
                "gt_scenario_id": f"{scenario_id}_feeder_{f_id}",
                "gt_feeder_id": f"feeder_{f_id}",
                "gt_topology_type": "ring" if topologies[f_id].get("is_ring") else "radial",
                "gt_number_of_buses": len(topologies[f_id]["buses"]),
                "gt_number_of_branches": len(topologies[f_id]["lines"]),
                "gt_r_eq_ohm": gt_r,
                "gt_x_eq_ohm": gt_x,
                "gt_z_eq_ohm": gt_z,
                "est_number_of_buses": est_res.number_of_buses,
                "est_number_of_branches": est_res.number_of_branches,
                "est_r_eq_ohm": est_res.r_eq_ohm,
                "est_x_eq_ohm": est_res.x_eq_ohm,
                "est_z_eq_ohm": est_res.z_eq_ohm,
                "obs_steady_state_time": json.dumps(time_s.tolist()),
                "obs_steady_state_voltage_abc": json.dumps(v_ss_abc),
                "obs_steady_state_current_abc": json.dumps(i_ss_abc),
                f"obs_{pcc_id}_voltage_mag_avg": float(np.mean(pcc_res.raw_voltage)) if pcc_res else 0.0,
                f"obs_{pcc_id}_current_mag_avg": float(np.mean(pcc_res.raw_current)) if pcc_res else 0.0,
                f"obs_{pcc_id}_p_kw": float(latest_sim_result.steady_state_measurements[pcc_id]["p_kw"]) if pcc_id in latest_sim_result.steady_state_measurements else 0.0,
                f"obs_{pcc_id}_q_kvar": float(latest_sim_result.steady_state_measurements[pcc_id]["q_kvar"]) if pcc_id in latest_sim_result.steady_state_measurements else 0.0
            }
            rows_1.append(row_1)

        # --- B. DATASET 2 GENERATION (Single Events + LV Transformer Spec Experiment) ---
        # Generate single events for 8 equipment types and 4 line fault types
        single_events = []
        for eq in equipment_types:
            single_events.append(SingleEquipmentSwitchEvent(
                equipment_type=eq,
                start_time_s=0.02,
                duration_s=0.04,
                target=f"trans{feeder_idx}",
                parameters={}
            ))
        for ft in fault_types:
            single_events.append(SingleLineFaultEvent(
                fault_type=ft,
                start_time_s=0.02,
                duration_s=0.04,
                target=f"trans{feeder_idx}",
                faulted_phases=fault_phase_map[ft],
                fault_resistance=0.05,
                parameters={}
            ))

        for s_ev in single_events:
            ev_class = s_ev.event_class
            ev_type = s_ev.event_type
            eq_type = getattr(s_ev, "equipment_type", None)
            flt_type = getattr(s_ev, "fault_type", None)

            h_net_d2 = HiddenNetworkScenario(
                scenario_id=f"{scenario_id}_{ev_type}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"mult": line_mult},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )

            sim_scen_d2 = SimulationScenario(
                hidden_network=h_net_d2,
                generator_p_kw=1500.0,
                generator_q_kvar=0.0,
                events=[s_ev],
                meter_fraction=0.5,
                seed=42 + idx
            )

            sim_res_d2 = runner.run_scenario(sim_scen_d2)
            t_s = sim_res_d2.time_s

            for f_id in [1, 2, 3]:
                tx_id = f"trans{f_id}"
                pcc_id = f"trans{f_id}_lv_pcc"
                pcc_res = sim_res_d2.processed_pccs.get(pcc_id)
                tx_spec = TRANSFORMER_SPECS[tx_id]

                if pcc_res is not None:
                    v_raw = pcc_res.raw_voltage
                    i_raw = pcc_res.raw_current
                    v_norm = pcc_res.normalized_voltage
                    i_norm = pcc_res.normalized_current

                    v_raw_abc = [v_raw[:, 0].tolist(), v_raw[:, 1].tolist(), v_raw[:, 2].tolist()]
                    i_raw_abc = [i_raw[:, 0].tolist(), i_raw[:, 1].tolist(), i_raw[:, 2].tolist()]
                    v_norm_abc = [v_norm[:, 0].tolist(), v_norm[:, 1].tolist(), v_norm[:, 2].tolist()]
                    i_norm_abc = [i_norm[:, 0].tolist(), i_norm[:, 1].tolist(), i_norm[:, 2].tolist()]

                    # Single event signatures
                    v_sig = v_norm_abc
                    i_sig = i_norm_abc

                    # Catalog signature for Dataset 3 composition
                    cat_key = (tx_spec["spec_id"], ev_class, ev_type, f"feeder_{f_id}")
                    signature_catalog[cat_key] = {
                        "v_sig": np.asarray(v_norm),
                        "i_sig": np.asarray(i_norm),
                        "time": t_s
                    }

                    row_2 = {
                        "gt_scenario_id": f"{scenario_id}_{ev_type}",
                        "gt_transformer_id": tx_id,
                        "gt_transformer_spec_id": tx_spec["spec_id"],
                        "gt_transformer_kva": tx_spec["kva"],
                        "gt_transformer_pct_r": tx_spec["pct_r"],
                        "gt_transformer_pct_x": tx_spec["pct_x"],
                        "gt_feeder_id": f"feeder_{f_id}",
                        "gt_pcc_id": pcc_id,
                        "gt_event_class": ev_class,
                        "gt_event_type": ev_type,
                        "gt_equipment_type": eq_type if eq_type else "",
                        "gt_fault_type": flt_type if flt_type else "",
                        "gt_event_start_timestamp_s": float(s_ev.start_time_s),
                        "gt_event_end_timestamp_s": float(s_ev.start_time_s + s_ev.duration_s),
                        "gt_event_target": s_ev.target,
                        "obs_steady_state_time": json.dumps(t_s.tolist()),
                        "obs_steady_state_v_ref": json.dumps(list(sim_res_d2.steady_state_measurements[pcc_id]["v_mags"])),
                        "obs_steady_state_i_ref": json.dumps(list(sim_res_d2.steady_state_measurements[pcc_id]["i_mags"])),
                        "obs_raw_transient_time": json.dumps(t_s.tolist()),
                        "obs_raw_transient_v": json.dumps(v_raw_abc),
                        "obs_raw_transient_i": json.dumps(i_raw_abc),
                        "obs_norm_transient_time": json.dumps(t_s.tolist()),
                        "obs_norm_transient_v": json.dumps(v_norm_abc),
                        "obs_norm_transient_i": json.dumps(i_norm_abc),
                        "single_event_voltage_signature": json.dumps(v_sig),
                        "single_event_current_signature": json.dumps(i_sig)
                    }
                    rows_2.append(row_2)

        # --- C. DATASET 3 GENERATION (Co-Events & Composed Single-Event Residuals) ---
        # Generate co-events: Equipment-Equipment (simultaneous & time-shifted) and Equipment-Fault (simultaneous & time-shifted)
        eq1 = SingleEquipmentSwitchEvent("ac_motor", 0.02, 0.04, f"trans{feeder_idx}", {})
        eq2 = SingleEquipmentSwitchEvent("dc_motor_inverter", 0.02, 0.04, f"trans{feeder_idx}", {})
        eq2_shifted = SingleEquipmentSwitchEvent("dc_motor_inverter", 0.03, 0.04, f"trans{feeder_idx}", {})

        flt_lg = SingleLineFaultEvent("LG", 0.02, 0.04, f"trans{feeder_idx}", (0,), 0.05, {})
        flt_lg_shifted = SingleLineFaultEvent("LG", 0.03, 0.04, f"trans{feeder_idx}", (0,), 0.05, {})

        co_events = [
            EquipmentEquipmentCoEvent(eq1, eq2),
            EquipmentEquipmentCoEvent(eq1, eq2_shifted),
            EquipmentLineFaultCoEvent(eq1, flt_lg),
            EquipmentLineFaultCoEvent(eq1, flt_lg_shifted)
        ]

        for co_ev in co_events:
            ev1 = co_ev.event_1
            ev2 = co_ev.event_2
            time_offset = co_ev.time_offset_s

            h_net_d3 = HiddenNetworkScenario(
                scenario_id=f"{scenario_id}_co_{ev1.event_type}_{ev2.event_type}",
                num_buses=len(modified_topo["buses"]),
                num_lines=len(modified_topo["lines"]),
                topology=modified_topo,
                line_parameters={"mult": line_mult},
                loads=loads_dist,
                load_composition=load_comp,
                motor_penetration=0.08,
                capacitor_configuration={},
                transformer_loading={"trans1": 50.0, "trans2": 50.0, "trans3": 50.0},
                switching_events=[]
            )

            sim_scen_d3 = SimulationScenario(
                hidden_network=h_net_d3,
                generator_p_kw=1500.0,
                generator_q_kvar=0.0,
                events=[co_ev],
                meter_fraction=0.5,
                seed=42 + idx
            )

            sim_res_d3 = runner.run_scenario(sim_scen_d3)
            t_s = sim_res_d3.time_s

            for f_id in [1, 2, 3]:
                tx_id = f"trans{f_id}"
                pcc_id = f"trans{f_id}_lv_pcc"
                pcc_res = sim_res_d3.processed_pccs.get(pcc_id)
                tx_spec = TRANSFORMER_SPECS[tx_id]

                if pcc_res is not None:
                    v_co = pcc_res.normalized_voltage  # shape (N, 3)
                    i_co = pcc_res.normalized_current  # shape (N, 3)

                    # Retrieve single event signatures from catalog
                    k1 = (tx_spec["spec_id"], ev1.event_class, ev1.event_type, f"feeder_{f_id}")
                    k2 = (tx_spec["spec_id"], ev2.event_class, ev2.event_type, f"feeder_{f_id}")

                    sig1 = signature_catalog.get(k1)
                    sig2 = signature_catalog.get(k2)

                    if sig1 is not None and sig2 is not None:
                        v_comp = sig1["v_sig"] + sig2["v_sig"]
                        i_comp = sig1["i_sig"] + sig2["i_sig"]
                    else:
                        v_comp = v_co
                        i_comp = i_co

                    # Calculate residual waveforms
                    res_v = v_co - v_comp
                    res_i = i_co - i_comp

                    # Calculate scalar residual magnitudes
                    res_v_mag = float(np.sqrt(np.mean(res_v**2)))
                    res_i_mag = float(np.sqrt(np.mean(res_i**2)))

                    row_3 = {
                        "gt_scenario_id": f"{scenario_id}_co_{ev1.event_type}_{ev2.event_type}",
                        "gt_transformer_id": tx_id,
                        "gt_transformer_spec_id": tx_spec["spec_id"],
                        "gt_feeder_id": f"feeder_{f_id}",
                        "gt_pcc_id": pcc_id,
                        "gt_coevent_class": co_ev.event_class,
                        "gt_event_1_class": ev1.event_class,
                        "gt_event_1_type": ev1.event_type,
                        "gt_event_1_equipment_type": getattr(ev1, "equipment_type", ""),
                        "gt_event_1_fault_type": getattr(ev1, "fault_type", ""),
                        "gt_event_1_start_timestamp_s": float(ev1.start_time_s),
                        "gt_event_2_class": ev2.event_class,
                        "gt_event_2_type": ev2.event_type,
                        "gt_event_2_equipment_type": getattr(ev2, "equipment_type", ""),
                        "gt_event_2_fault_type": getattr(ev2, "fault_type", ""),
                        "gt_event_2_start_timestamp_s": float(ev2.start_time_s),
                        "gt_time_offset_s": float(time_offset),
                        "obs_coevent_time": json.dumps(t_s.tolist()),
                        "obs_coevent_v": json.dumps([v_co[:, 0].tolist(), v_co[:, 1].tolist(), v_co[:, 2].tolist()]),
                        "obs_coevent_i": json.dumps([i_co[:, 0].tolist(), i_co[:, 1].tolist(), i_co[:, 2].tolist()]),
                        "obs_composed_single_event_v": json.dumps([v_comp[:, 0].tolist(), v_comp[:, 1].tolist(), v_comp[:, 2].tolist()]),
                        "obs_composed_single_event_i": json.dumps([i_comp[:, 0].tolist(), i_comp[:, 1].tolist(), i_comp[:, 2].tolist()]),
                        "obs_residual_v": json.dumps([res_v[:, 0].tolist(), res_v[:, 1].tolist(), res_v[:, 2].tolist()]),
                        "obs_residual_i": json.dumps([res_i[:, 0].tolist(), res_i[:, 1].tolist(), res_i[:, 2].tolist()]),
                        "residual_voltage_magnitude": round(res_v_mag, 6),
                        "residual_current_magnitude": round(res_i_mag, 6)
                    }
                    rows_3.append(row_3)

    df_1 = pd.DataFrame(rows_1)
    df_2 = pd.DataFrame(rows_2)
    df_3 = pd.DataFrame(rows_3)

    validate_dataset_1(df_1)
    validate_dataset_2(df_2)
    validate_dataset_3(df_3)

    if write_to_disk:
        dir_path = Path("src/simulation")
        dir_path.mkdir(parents=True, exist_ok=True)
        df_1.to_csv(dir_path / "dataset_1.csv", index=False)
        df_2.to_csv(dir_path / "dataset_2.csv", index=False)
        df_3.to_csv(dir_path / "dataset_3.csv", index=False)
        print(f"INFO: Successfully written validated datasets to {dir_path / 'dataset_1.csv'}, {dir_path / 'dataset_2.csv'}, and {dir_path / 'dataset_3.csv'}")

    return df_1, df_2, df_3

if __name__ == "__main__":
    generate_experiments_dataset(n_scenarios=15, write_to_disk=True)
