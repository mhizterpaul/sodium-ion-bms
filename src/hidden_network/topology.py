import random
import numpy as np

def generate_radial_topology(feeder_idx: int, num_buses: int, line_mult: float = 1.0) -> dict:
    """
    Generates a radial tree topology represented as a dictionary of buses and lines.
    This fulfills the requirement: Make the downstream topology a parameter.
    """
    root_bus = f"feeder{feeder_idx}_sec"
    buses = [root_bus]
    lines = []

    for i in range(1, num_buses):
        new_bus = f"f{feeder_idx}_node{i}"
        parent_bus = random.choice(buses)

        l_km = random.uniform(0.03, 0.12) * line_mult
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
