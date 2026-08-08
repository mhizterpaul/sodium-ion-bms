import numpy as np
from src.power_plant.signature import calculate_response_jacobian, analyze_observability_svd

def validate_observability(feeder_idx: int, topology: dict, trans_name: str) -> dict:
    """
    Validates boundary observability of the hidden network topology using SVD of the response Jacobian.
    """
    J = calculate_response_jacobian(feeder_idx, topology, trans_name)
    sigmas, kappa = analyze_observability_svd(J)

    return {
        "singular_values": sigmas,
        "condition_number": kappa,
        "is_observable": bool(kappa < 1e5)
    }
