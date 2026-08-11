def get_distribution_transformer_spec(feeder_idx: int) -> dict:
    """
    Returns the physical specifications of the 11/0.415 kV distribution step-down transformer.
    Each distribution transformer rated power is 1.5 MVA (1500 kVA).
    """
    return {
        "name": f"trans{feeder_idx}",
        "phases": 3,
        "windings": 2,
        "buses": [f"feeder{feeder_idx}_head", f"feeder{feeder_idx}_sec"],
        "conns": ["delta", "wye"],
        "kvs": [11.0, 0.415],
        "kvas": [1500.0, 1500.0],
        "r_pct": 0.8,
        "xhl_pct": 5.0
    }
