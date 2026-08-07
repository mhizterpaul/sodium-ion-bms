import os
import csv
import random
import numpy as np
from opendssdirect import dss

from src.power_plant.plant import initialize_known_plant
from src.power_plant.downstream import generate_topology, build_downstream_network, perturb_network
from src.power_plant.sources import apply_generator_profile
from src.power_plant.measurements import get_boundary_measurements, extract_transformer_terminal_data
from src.power_plant.sensitivity import calculate_voltage_sensitivities
from src.power_plant.signature import calculate_response_jacobian, analyze_observability_svd

def run_event_and_qsts(scenario_idx: int, event_type: str, downstream_data: dict, active_feeder: int):
    """
    Executes a QSTS loop over simulated times for the given event type.
    Applies real physical changes in OpenDSS rather than wave formulas.
    Returns the boundary measurements at the peak/active event step.
    """
    times = list(range(0, 35, 5))  # t = 0, 5, 10, 15, 20, 25, 30
    measurements_history = []
    t_event = 20
    fault_name = f"f_active_{scenario_idx}"

    for t in times:
        # 1. Vary Generator operating point based on time
        p_gen = 1000.0 + 200.0 * np.sin(t / 10.0)
        q_gen = 100.0 + 50.0 * np.cos(t / 10.0)
        apply_generator_profile(p_gen, q_gen)

        # 2. Apply QSTS network profile
        load_scale = 1.0 + 0.15 * np.sin(t / 5.0)

        for f in range(1, 4):
            perturb_network(f, downstream_data[f], load_scale=load_scale, cap_state=True)

        # 3. Apply active event changes at t = t_event
        if t == t_event:
            print(f"  [QSTS t={t}s] Applying event: {event_type} on feeder {active_feeder}")
            if event_type == 'temporary_fault':
                nodes = downstream_data[active_feeder]["buses"]
                fault_bus = nodes[min(3, len(nodes)-1)]
                dss.run_command(f"new fault.{fault_name} bus1={fault_bus} phases=1 r=0.1")
            elif event_type == 'motor_starting':
                perturb_network(active_feeder, downstream_data[active_feeder], load_scale=load_scale * 5.0, cap_state=True)
            elif event_type == 'capacitor_switching':
                perturb_network(active_feeder, downstream_data[active_feeder], load_scale=load_scale, cap_state=False)
            elif event_type == 'transformer_energization':
                perturb_network(active_feeder, downstream_data[active_feeder], load_scale=load_scale * 3.0, cap_state=True)
            elif event_type == 'nonlinear_load':
                perturb_network(active_feeder, downstream_data[active_feeder], load_scale=load_scale * 1.5, cap_state=True)

        # 4. Solve Power Flow
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            dss.run_command("Solve mode=direct")

        m = get_boundary_measurements()
        measurements_history.append((t, m))

        # 5. Clean up temporary event changes after t_event step
        if t == t_event:
            if event_type == 'temporary_fault':
                dss.run_command(f"edit fault.{fault_name} enabled=no")

    event_m = [m for t, m in measurements_history if t == t_event][0]
    return event_m

def generate_realization_dataset(n_scenarios: int = 15):
    """
    Runs physical QSTS simulations across perturbed scenarios, extracts boundaries,
    and exports a comprehensive network realization dataset to CSV.
    """
    print(f"INFO: Running {n_scenarios} Scientifically Consistent QSTS scenarios...")

    events = [
        'steady_state', 'transformer_energization', 'capacitor_switching',
        'motor_starting', 'temporary_fault', 'nonlinear_load'
    ]

    results = []

    for idx in range(n_scenarios):
        # 1. Reset plant to fixed upstream substation & feeders
        initialize_known_plant()

        # 2. Determine scenario configurations
        event = events[idx % len(events)]
        ring_feeder_idx = (idx % 3) + 1 if idx in [7, 12, 14] else 0
        line_mult = 1.0 + 0.15 * np.sin(idx)

        # 3. Generate structured downstream topologies and build them in OpenDSS
        downstream_data = {}
        for f in range(1, 4):
            num_buses = random.randint(20, 80)
            has_ring = (f == ring_feeder_idx)
            topo = generate_topology(f, num_buses, has_ring, line_mult)
            downstream_data[f] = topo
            build_downstream_network(f, topo)

        # 4. Run QSTS simulation with explicit events
        active_feeder = (idx % 3) + 1
        m = run_event_and_qsts(idx, event, downstream_data, active_feeder)

        # 5. Calculate real load perturbation sensitivities: dV/dP and dV/dQ
        dv_dp, dv_dq = calculate_voltage_sensitivities(active_feeder, downstream_data[active_feeder], f"trans{active_feeder}")

        # 6. Calculate Response Jacobian and singular value observability indicator
        J_M = calculate_response_jacobian(active_feeder, downstream_data[active_feeder], f"trans{active_feeder}")
        sigmas, kappa = analyze_observability_svd(J_M)

        # Compile dataset record
        record = {
            "scenario_index": idx,
            "topology_type": "ring" if ring_feeder_idx > 0 else "radial",
            "simulated_event": event,
            "active_feeder": active_feeder,

            # --- Hidden Parameters (ground truth for realizing State Estimation) ---
            "hidden_total_buses": sum(downstream_data[f]["num_buses"] for f in range(1, 4)),
            "hidden_total_edges": sum(downstream_data[f]["num_edges"] for f in range(1, 4)),
            "hidden_f1_r_ohm": downstream_data[1]["total_r_ohm"],
            "hidden_f2_r_ohm": downstream_data[2]["total_r_ohm"],
            "hidden_f3_r_ohm": downstream_data[3]["total_r_ohm"],
            "hidden_motor_count": sum(len(downstream_data[f]["motors"]) for f in range(1, 4)),
            "hidden_capacitor_count": sum(len(downstream_data[f]["capacitors"]) for f in range(1, 4)),

            # --- Boundary Measurements ---
            # Transformer 1 HV side measurements
            "transformer1_hv_voltage_v": round(m["transformer1_hv_voltage"], 1),
            "transformer1_hv_current_amp": round(m["transformer1_hv_current"], 2),
            "transformer1_loading_pct": round(m["transformer1_loading_pct"], 2),
            "transformer1_copper_loss_kw": round((m["transformer1_loading_pct"] / 100.0)**2 * 32.0, 3),
            "transformer1_core_loss_kw": round(7.5, 3),
            "transformer1_voltage_regulation_pct": round(m["transformer1_voltage_regulation_pct"], 3),
            "transformer1_eq_impedance_ohm": round(m["transformer1_z_hv_mag_ohm"], 3),
            "transformer1_tap_position": m["transformer1_tap_position"],

            # Transformer 2
            "transformer2_loading_pct": round(m["transformer2_loading_pct"], 2),
            "transformer2_copper_loss_kw": round((m["transformer2_loading_pct"] / 100.0)**2 * 32.0, 3),
            "transformer2_core_loss_kw": round(7.5, 3),
            "transformer2_voltage_regulation_pct": round(m["transformer2_voltage_regulation_pct"], 3),
            "transformer2_eq_impedance_ohm": round(m["transformer2_z_hv_mag_ohm"], 3),
            "transformer2_tap_position": m["transformer2_tap_position"],

            # Transformer 3
            "transformer3_loading_pct": round(m["transformer3_loading_pct"], 2),
            "transformer3_copper_loss_kw": round((m["transformer3_loading_pct"] / 100.0)**2 * 32.0, 3),
            "transformer3_core_loss_kw": round(7.5, 3),
            "transformer3_voltage_regulation_pct": round(m["transformer3_voltage_regulation_pct"], 3),
            "transformer3_eq_impedance_ohm": round(m["transformer3_z_hv_mag_ohm"], 3),
            "transformer3_tap_position": m["transformer3_tap_position"],

            # Feeder Head 1 Symmetrical components
            "feeder1_voltage_mag_kv": round(m["transformer1_hv_voltage"] / 1000.0, 4),
            "feeder1_voltage_pos_mag_kv": round(m["transformer1_hv_voltage_pos_mag"] / 1000.0, 4),
            "feeder1_voltage_neg_mag_kv": round(m["transformer1_hv_voltage_pos_mag"] * m["transformer1_hv_voltage_unbalance_pct"] / 100000.0, 4),
            "feeder1_voltage_zero_mag_kv": round(0.01 * m["transformer1_hv_voltage_pos_mag"] / 1000.0, 4),
            "feeder1_voltage_unbalance_pct": round(m["transformer1_hv_voltage_unbalance_pct"], 3),

            "feeder1_current_mag_amp": round(m["transformer1_hv_current"], 2),
            "feeder1_current_pos_mag_amp": round(m["transformer1_hv_current_pos_mag"], 2),
            "feeder1_current_unbalance_pct": round(m["transformer1_hv_current_unbalance_pct"], 3),

            "feeder1_p_kw": round(m["transformer1_p_kw"], 2),
            "feeder1_q_kvar": round(m["transformer1_q_kvar"], 2),
            "feeder1_s_kva": round(m["transformer1_s_kva"], 2),
            "feeder1_pf": round(m["transformer1_pf"], 3),

            # Feeder Head 2 Symmetrical components
            "feeder2_voltage_mag_kv": round(m["transformer2_hv_voltage"] / 1000.0, 4),
            "feeder2_voltage_unbalance_pct": round(m["transformer2_hv_voltage_unbalance_pct"], 3),
            "feeder2_current_mag_amp": round(m["transformer2_hv_current"], 2),
            "feeder2_current_unbalance_pct": round(m["transformer2_hv_current_unbalance_pct"], 3),
            "feeder2_p_kw": round(m["transformer2_p_kw"], 2),
            "feeder2_q_kvar": round(m["transformer2_q_kvar"], 2),
            "feeder2_pf": round(m["transformer2_pf"], 3),

            # Feeder Head 3 Symmetrical components
            "feeder3_voltage_mag_kv": round(m["transformer3_hv_voltage"] / 1000.0, 4),
            "feeder3_voltage_unbalance_pct": round(m["transformer3_hv_voltage_unbalance_pct"], 3),
            "feeder3_current_mag_amp": round(m["transformer3_hv_current"], 2),
            "feeder3_current_unbalance_pct": round(m["transformer3_hv_current_unbalance_pct"], 3),
            "feeder3_p_kw": round(m["transformer3_p_kw"], 2),
            "feeder3_q_kvar": round(m["transformer3_q_kvar"], 2),
            "feeder3_pf": round(m["transformer3_pf"], 3),

            # --- Extracted Sensitivity-Driven Real Features ---
            "feeder1_eq_impedance_ohm": round(m["transformer1_z_hv_mag_ohm"], 3),
            "feeder2_eq_impedance_ohm": round(m["transformer2_z_hv_mag_ohm"], 3),
            "feeder3_eq_impedance_ohm": round(m["transformer3_z_hv_mag_ohm"], 3),

            "feeder1_phase_angle_diff_deg": round(m["transformer1_hv_voltage_pos_ang"], 3),
            "feeder2_phase_angle_diff_deg": round(m["transformer2_hv_voltage_pos_ang"], 3),
            "feeder3_phase_angle_diff_deg": round(m["transformer3_hv_voltage_pos_ang"], 3),

            "feeder1_stiffness_kva": round(m["transformer1_hv_voltage_pos_mag"]**2 / (m["transformer1_z_hv_mag_ohm"] + 1e-6) / 1000.0, 2),
            "feeder2_stiffness_kva": round(m["transformer2_hv_voltage_pos_mag"]**2 / (m["transformer2_z_hv_mag_ohm"] + 1e-6) / 1000.0, 2),
            "feeder3_stiffness_kva": round(m["transformer3_hv_voltage_pos_mag"]**2 / (m["transformer3_z_hv_mag_ohm"] + 1e-6) / 1000.0, 2),

            "feeder1_dv_dp": round(dv_dp if active_feeder == 1 else 0.0, 6),
            "feeder1_dv_dq": round(dv_dq if active_feeder == 1 else 0.0, 6),
            "feeder2_dv_dp": round(dv_dp if active_feeder == 2 else 0.0, 6),
            "feeder2_dv_dq": round(dv_dq if active_feeder == 2 else 0.0, 6),
            "feeder3_dv_dp": round(dv_dp if active_feeder == 3 else 0.0, 6),
            "feeder3_dv_dq": round(dv_dq if active_feeder == 3 else 0.0, 6),

            "jacobian_sigma_1": round(sigmas[0], 6),
            "jacobian_sigma_2": round(sigmas[1], 6),
            "jacobian_sigma_3": round(sigmas[2], 6),
            "jacobian_sigma_4": round(sigmas[3], 6),
            "observability_condition_kappa": round(kappa, 3),

            # --- Latent State Mapping ---
            "latent_total_load_demand_kw": round(sum(downstream_data[f]["load_kw_total"] for f in range(1, 4)), 2),
            "latent_topology_entropy": round(sum(downstream_data[f]["topology_entropy"] for f in range(1, 4)), 3),
            "latent_avg_f1_electrical_distance_km": round(0.075 * line_mult * downstream_data[1]["num_buses"], 3)
        }
        results.append(record)

    csv_dir = "src/simulation"
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, "scenario_results.csv")

    headers = list(results[0].keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)

    print(f"INFO: Successfully exported {n_scenarios} QSTS scenario records to {csv_path}")
    return results

if __name__ == "__main__":
    generate_realization_dataset()
