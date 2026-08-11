import numpy as np

def generate_radial_topology(feeder_idx: int, num_buses: int, line_mult: float = 1.0, rng=None) -> dict:
    """
    Generates a radial tree topology represented as a dictionary of buses and lines.
    Uses local seeded RNG for perfect reproducibility.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    root_bus = f"feeder{feeder_idx}_sec"
    buses = [root_bus]
    lines = []

    for i in range(1, num_buses):
        new_bus = f"f{feeder_idx}_node{i}"
        parent_bus = str(rng.choice(buses))

        l_km = float(rng.uniform(0.03, 0.12)) * line_mult
        lines.append({
            "name": f"down_{feeder_idx}_{i}",
            "bus1": parent_bus,
            "bus2": new_bus,
            "length": round(l_km, 4),
            "units": "km"
        })
        buses.append(new_bus)

    return {
        "feeder_idx": feeder_idx,
        "buses": buses,
        "lines": lines
    }

def identify_candidate_pccs(topology: dict) -> list[dict]:
    """
    Identifies all candidate PCC smart-meter points from the topology dictionary.
    Includes both the branch endpoints (for standard lines) and the LV transformer secondaries.
    """
    candidate_pccs = []

    # 1. Standard branch lines in the topology
    for ln in topology.get("lines", []):
        parent = ln["bus1"]
        child = ln["bus2"]
        line_name = ln["name"]

        b_type = "ring" if line_name.startswith("tie_") else "radial"

        candidate_pccs.append({
            "pcc_id": f"pcc_{line_name}",
            "bus": child,
            "parent_bus": parent,
            "branch_id": line_name,
            "branch_type": b_type,
            "meter_eligible": True
        })

    # 2. LV secondary terminals of the distribution transformers
    for idx in [1, 2, 3]:
        candidate_pccs.append({
            "pcc_id": f"trans{idx}_lv_pcc",
            "bus": f"feeder{idx}_sec",
            "parent_bus": f"feeder{idx}_head",
            "branch_id": f"transformer.trans{idx}",
            "branch_type": "transformer",
            "meter_eligible": True
        })

    return candidate_pccs

def select_metered_pccs(candidate_pccs: list[dict], fraction: float, seed: int) -> list[dict]:
    """
    Selects all transformer secondary PCCs, and a configured fraction of branch PCCs
    using a seeded RNG, ensuring perfect alignment with the methodology.
    """
    if not (0.0 < fraction <= 1.0):
        raise ValueError(f"meter_fraction must be in (0.0, 1.0], got {fraction}")

    transformer_pccs = [p for p in candidate_pccs if p.get("branch_type") == "transformer"]
    branch_pccs = [p for p in candidate_pccs if p.get("branch_type") != "transformer"]

    n_branch_meters = max(1, int(np.ceil(fraction * len(branch_pccs)))) if branch_pccs else 0

    rng = np.random.default_rng(seed)

    if branch_pccs:
        selected_indices = rng.choice(len(branch_pccs), size=n_branch_meters, replace=False)
        selected_branch_pccs = [branch_pccs[i] for i in selected_indices]
    else:
        selected_branch_pccs = []

    return transformer_pccs + selected_branch_pccs
