import numpy as np

def compute_latent_target(hidden_network: dict) -> dict:
    """
    Computes target ground truth latent states X_R* representing network characteristics.
    """
    lines = hidden_network.get("topology", {}).get("lines", [])
    buses = hidden_network.get("topology", {}).get("buses", [])
    loads = hidden_network.get("loads", {}).get("loads", [])

    num_buses = len(buses)
    num_edges = len(lines)
    total_load_kw = sum(ld["kw"] for ld in loads)

    avg_degree = (2.0 * num_edges) / num_buses if num_buses > 0 else 0.0
    entropy = float(avg_degree * np.log2(avg_degree + 1e-3)) if avg_degree > 0 else 0.0

    return {
        "latent_total_buses": num_buses,
        "latent_total_edges": num_edges,
        "latent_total_load_kw": round(total_load_kw, 2),
        "latent_topology_entropy": round(entropy, 3)
    }
