from dataclasses import dataclass
import numpy as np
from src.realization.impedance_solver import LatentLineImpedanceSolver
from src.realization.network_size_solver import LatentLineParameterSolver

@dataclass
class LatentLineEstimate:
    known_num_buses: int
    known_num_branches: int
    r_eq_ohm: float
    x_eq_ohm: float
    z_eq_ohm: float
    g_eq_siemens: float
    b_eq_siemens: float
    estimated_load_kw: float
    objective_loss: float

# Alias for backward compatibility if needed
RealizationEstimate = LatentLineEstimate

class LatentLineRealizationSolver:
    """
    Inverse solver for estimating latent LV line electrical parameters and associated loads:
    1. Level A: Model-based parameter search over candidate latent line parameters (R_L, X_L) given known LV topology K.
    2. Level B: Continuous impedance & admittance parameter estimation (R_L_hat, X_L_hat, G_L_hat, B_L_hat)
       via complex least squares over positive-sequence phasors from multi-operating-point observations.
    """

    def __init__(self, param_solver: LatentLineParameterSolver = None, impedance_solver: LatentLineImpedanceSolver = None):
        self.param_solver = param_solver or LatentLineParameterSolver()
        self.impedance_solver = impedance_solver or LatentLineImpedanceSolver()

    def estimate(
        self,
        multi_op_measurements: list[dict],
        known_num_buses: int = 20,
        known_num_branches: int = 19
    ) -> LatentLineEstimate:
        """
        Args:
            multi_op_measurements: list of operating point dictionaries containing 'v_mags', 'i_mags', 'p_kw', etc.
            known_num_buses: number of buses in the known LV network topology.
            known_num_branches: number of branches in the known LV network topology.

        Returns:
            LatentLineEstimate
        """
        if not multi_op_measurements:
            return LatentLineEstimate(
                known_num_buses=known_num_buses,
                known_num_branches=known_num_branches,
                r_eq_ohm=0.1,
                x_eq_ohm=0.05,
                z_eq_ohm=float(np.sqrt(0.1**2 + 0.05**2)),
                g_eq_siemens=1e-3,
                b_eq_siemens=1e-3,
                estimated_load_kw=10.0,
                objective_loss=0.0
            )

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

        # Level A: Search over latent line parameters for known topology
        r_search, x_search, g_search, b_search, loss = self.param_solver.solve(
            observed_ops,
            known_num_buses=known_num_buses,
            known_num_branches=known_num_branches
        )

        # Level B: Continuous impedance estimation from phasors
        r_ls, x_ls, z_ls, g_ls, b_ls = self.impedance_solver.estimate(v_phasors, i_phasors)

        # Combine least-squares and model search estimates
        r_final = (r_search + r_ls) / 2.0
        x_final = (x_search + x_ls) / 2.0
        z_final = float(np.sqrt(r_final**2 + x_final**2))
        g_final = (g_search + g_ls) / 2.0
        b_final = (b_search + b_ls) / 2.0
        avg_load_kw = float(np.mean([op["p_kw"] for op in observed_ops]))

        return LatentLineEstimate(
            known_num_buses=known_num_buses,
            known_num_branches=known_num_branches,
            r_eq_ohm=round(r_final, 4),
            x_eq_ohm=round(x_final, 4),
            z_eq_ohm=round(z_final, 4),
            g_eq_siemens=round(g_final, 6),
            b_eq_siemens=round(b_final, 6),
            estimated_load_kw=round(avg_load_kw, 2),
            objective_loss=round(loss, 6)
        )


# Alias for backward compatibility if needed
LatentNetworkRealizationSolver = LatentLineRealizationSolver
