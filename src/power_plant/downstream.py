import random
import numpy as np
from opendssdirect import dss

def generate_topology(feeder_idx: int, num_buses: int, has_ring: bool, line_mult: float = 1.0) -> dict:
    """
    Generates a structured dictionary representing the hidden network topology.
    """
    root_bus = f"feeder{feeder_idx}_sec"
    buses = [root_bus]
    lines = []
    loads = []
    switches = []
    motors = []
    capacitors = []
    ders = []

    # Iteratively build radial branches
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

    # Optional tie-line loop/ring
    is_ring_formed = False
    if has_ring and len(buses) > 5:
        # Choose two buses far apart
        bus_a = buses[3]
        bus_b = buses[-1]
        lines.append({
            "name": f"tie_{feeder_idx}",
            "bus1": bus_a,
            "bus2": bus_b,
            "length": round(0.15 * line_mult, 4),
            "units": "km"
        })
        is_ring_formed = True

    # Distribute loads
    load_kw_total = 0.0
    for bus in buses[1:]:
        if random.random() < 0.6:
            load_kw = random.uniform(5.0, 25.0)
            l_model = random.choice([1, 2, 3]) # 1: Constant PQ, 2: Constant Z, 3: Constant I
            pf = random.choice([0.85, 0.90, 0.95])
            loads.append({
                "name": f"l_{bus}",
                "bus": bus,
                "kw": round(load_kw, 2),
                "pf": pf,
                "model": l_model
            })
            load_kw_total += load_kw

        # Place capacitors
        if random.random() < 0.12:
            cap_kvar = random.choice([15.0, 30.0, 45.0])
            capacitors.append({
                "name": f"c_{bus}",
                "bus": bus,
                "kvar": cap_kvar
            })

        # Place motors
        if random.random() < 0.08:
            motors.append({
                "name": f"m_{bus}",
                "bus": bus,
                "kw": round(random.uniform(10.0, 30.0), 1),
                "pf": 0.8
            })

        # Place DERs (PV or other distributed energy resources)
        if random.random() < 0.05:
            ders.append({
                "name": f"der_{bus}",
                "bus": bus,
                "kw": round(random.uniform(5.0, 20.0), 1)
            })

    # Topology average degree/entropy calculation
    num_edges = len(lines)
    avg_degree = (2.0 * num_edges) / len(buses) if len(buses) > 0 else 0.0
    topology_entropy = float(avg_degree * np.log2(avg_degree + 1e-3)) if avg_degree > 0 else 0.0

    return {
        "feeder_idx": feeder_idx,
        "buses": buses,
        "num_buses": len(buses),
        "num_edges": num_edges,
        "lines": lines,
        "loads": loads,
        "switches": switches,
        "motors": motors,
        "capacitors": capacitors,
        "ders": ders,
        "is_ring": is_ring_formed,
        "total_r_ohm": round(sum(0.45 * ln["length"] for ln in lines), 4),
        "total_x_ohm": round(sum(0.15 * ln["length"] for ln in lines), 4),
        "load_kw_total": round(load_kw_total, 2),
        "topology_entropy": round(topology_entropy, 3)
    }

def build_downstream_network(feeder_idx: int, topology: dict):
    """
    Attaches the independently generated LV network in OpenDSS based on topology dictionary.
    """
    # Define downstream line code for LV (0.415 kV)
    dss.run_command(f"new linecode.down_lv_{feeder_idx} nphases=3 r1=0.45 x1=0.15 r0=1.20 x0=0.35 c1=4.0 c0=2.0 units=km")

    # Build lines
    for ln in topology["lines"]:
        dss.run_command(
            f"new line.{ln['name']} "
            f"bus1={ln['bus1']} "
            f"bus2={ln['bus2']} "
            f"phases=3 "
            f"linecode=down_lv_{feeder_idx} "
            f"length={ln['length']} "
            f"units={ln['units']}"
        )

    # Build loads
    for ld in topology["loads"]:
        dss.run_command(
            f"new load.{ld['name']} "
            f"bus1={ld['bus']} "
            f"phases=3 "
            f"kv=0.415 "
            f"kw={ld['kw']} "
            f"pf={ld['pf']} "
            f"model={ld['model']} "
            f"status=fixed"
        )

    # Build capacitors
    for cap in topology["capacitors"]:
        dss.run_command(
            f"new capacitor.{cap['name']} "
            f"bus1={cap['bus']} "
            f"phases=3 "
            f"kv=0.415 "
            f"kvar={cap['kvar']} "
            f"conn=wye"
        )

    # Build motors (as actual OpenDSS loads with constant impedance model for starting proxy)
    for m in topology["motors"]:
        dss.run_command(
            f"new load.{m['name']} "
            f"bus1={m['bus']} "
            f"phases=3 "
            f"kv=0.415 "
            f"kw={m['kw']} "
            f"pf={m['pf']} "
            f"model=2 "  # model=2 is constant impedance
            f"status=fixed"
        )

    # Build DERs (as actual OpenDSS generators)
    for der in topology["ders"]:
        dss.run_command(
            f"new generator.{der['name']} "
            f"bus1={der['bus']} "
            f"phases=3 "
            f"kv=0.415 "
            f"kw={der['kw']} "
            f"pf=1.0 "
            f"model=1"
        )

def perturb_network(feeder_idx: int, topology: dict, load_scale: float = 1.0, cap_state: bool = True):
    """
    Modifies operating state of loads and capacitors inside the OpenDSS system.
    """
    for ld in topology["loads"]:
        p_scaled = ld["kw"] * load_scale
        dss.run_command(f"edit load.{ld['name']} kw={round(p_scaled, 2)}")

    for cap in topology["capacitors"]:
        status = "enabled" if cap_state else "disabled"
        dss.run_command(f"edit capacitor.{cap['name']} enabled={'yes' if cap_state else 'no'}")
