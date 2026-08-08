import numpy as np

def apply_topology_reconfiguration(topology: dict, has_ring: bool, line_mult: float = 1.0) -> dict:
    """
    Applies structural perturbations such as line parameter changes and loop/ring closures.
    """
    modified_topology = {
        "feeder_idx": topology["feeder_idx"],
        "buses": list(topology["buses"]),
        "lines": [dict(ln) for ln in topology["lines"]],
        "is_ring": False
    }

    for ln in modified_topology["lines"]:
        ln["length"] = round(ln["length"] * line_mult, 4)

    if has_ring and len(modified_topology["buses"]) > 5:
        bus_a = modified_topology["buses"][3]
        bus_b = modified_topology["buses"][-1]
        modified_topology["lines"].append({
            "name": f"tie_{modified_topology['feeder_idx']}",
            "bus1": bus_a,
            "bus2": bus_b,
            "length": round(0.15 * line_mult, 4),
            "units": "km"
        })
        modified_topology["is_ring"] = True

    return modified_topology
