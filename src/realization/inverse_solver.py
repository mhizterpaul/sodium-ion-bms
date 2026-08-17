from dataclasses import dataclass
import numpy as np
from src.realization.impedance_solver import EquivalentImpedanceSolver
from src.realization.network_size_solver import HiddenNetworkSizeSolver

@dataclass
class RealizationEstimate:
    number_of_buses: int
    number_of_branches: int
    r_eq_ohm: float
    x_eq_ohm: float
    z_eq_ohm: float
    objective_loss: float

class LatentNetworkRealizationSolver:
    """
    Mixed discrete/continuous inverse solver:
    1. Level A: Structural search over candidate bus/branch counts (N_b_hat, N_l_hat).
    2. Level B: Continuous electrical parameter estimation (R_eq_hat, X_eq_hat, Z_eq_hat)
       via complex least squares over positive-sequence phasors from multi-operating-point observations.
    """

    def __init__(self, size_solver: HiddenNetworkSizeSolver = None, impedance_solver: EquivalentImpedanceSolver = None):
        self.size_solver = size_solver or HiddenNetworkSizeSolver()
        self.impedance_solver = impedance_solver or EquivalentImpedanceSolver()

    def estimate(self, multi_op_measurements: list[dict]) -> RealizationEstimate:
        """
        Args:
            multi_op_measurements: list of operating point dictionaries containing 'v_mags', 'i_mags', 'p_kw', etc.

        Returns:
            RealizationEstimate
        """
        if not multi_op_measurements:
            return RealizationEstimate(20, 19, 0.1, 0.05, float(np.sqrt(0.1**2 + 0.05**2)), 0.0)

        v_phasors = []
        i_phasors = []
        observed_ops = []

        for op in multi_op_measurements:
            v_rms = tuple(op.get("v_mags", (240.0, 240.0, 240.0)))
            i_rms = tuple(op.get("i_mags", (10.0, 10.0, 10.0)))

            v1, i1 = self.impedance_solver.compute_positive_sequence_phasor(v_rms, i_rms)
            v_phasors.append(v1)
            i_phasors.append(i1)

            observed_ops.append({
                "v_avg": float(np.mean(v_rms)),
                "i_avg": float(np.mean(i_rms)),
                "p_kw": float(op.get("p_kw", 10.0))
            })

        # Level A: Discrete structural estimation
        n_b_hat, n_l_hat, loss = self.size_solver.solve(observed_ops)

        # Level B: Continuous impedance estimation
        r_eq_hat, x_eq_hat, z_eq_hat = self.impedance_solver.estimate(v_phasors, i_phasors)

        return RealizationEstimate(
            number_of_buses=int(n_b_hat),
            number_of_branches=int(n_l_hat),
            r_eq_ohm=round(r_eq_hat, 4),
            x_eq_ohm=round(x_eq_hat, 4),
            z_eq_ohm=round(z_eq_hat, 4),
            objective_loss=round(loss, 6)
        )
