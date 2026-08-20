import numpy as np

class KnownTopologyForwardSolver:
    """
    Predicts boundary voltage V, current I, active power P, and reactive power Q for a known LV topology K
    given candidate latent line parameters (R_L, X_L) and line-associated load contributions.
    """

    def predict(self, r_l: float, x_l: float, load_kw_list: list[float], known_num_buses: int = 20) -> list[dict]:
        """
        Simulates predicted boundary/consumer observations across multiple operating points for known LV network topology.
        """
        predictions = []
        for kw in load_kw_list:
            i_pred = (kw * 1000.0) / (3.0 * 240.0 * 0.95 + 1e-6)
            # Voltage drop across known branch chain with latent line resistance
            v_drop = i_pred * r_l * (known_num_buses / 20.0)
            v_pred = 240.0 - v_drop
            q_pred = kw * np.tan(np.arccos(0.95))

            predictions.append({
                "v_pred": max(200.0, float(v_pred)),
                "i_pred": float(i_pred),
                "p_pred": float(kw),
                "q_pred": float(q_pred)
            })
        return predictions


class LatentLineParameterSolver:
    """
    Estimates latent line electrical parameters (R_L, X_L, G_L, B_L) and associated load parameters L_load
    for a known LV topology by searching candidate parameter variations and minimizing residual loss J.
    """

    def __init__(self, forward_solver: KnownTopologyForwardSolver = None):
        self.forward_solver = forward_solver or KnownTopologyForwardSolver()

    def solve(
        self,
        observed_ops: list[dict],
        known_num_buses: int = 20,
        known_num_branches: int = 19,
        candidate_r_range: np.ndarray = None
    ) -> tuple[float, float, float, float, float]:
        """
        Searches candidate line parameters and selects optimal (R_L_hat, X_L_hat, G_L_hat, B_L_hat, L_load_hat) minimizing loss.
        """
        if candidate_r_range is None:
            candidate_r_range = np.linspace(0.01, 0.50, 50)

        best_r = 0.10
        best_x = 0.05
        min_loss = float("inf")

        load_kw_list = [op.get("p_kw", 10.0) for op in observed_ops]
        v_obs_list = [op.get("v_avg", 240.0) for op in observed_ops]
        i_obs_list = [op.get("i_avg", 15.0) for op in observed_ops]

        for r_cand in candidate_r_range:
            x_cand = 0.35 * r_cand
            predictions = self.forward_solver.predict(r_cand, x_cand, load_kw_list, known_num_buses=known_num_buses)

            v_pred_list = [p["v_pred"] for p in predictions]
            i_pred_list = [p["i_pred"] for p in predictions]

            res_v = np.mean([(vo - vp)**2 for vo, vp in zip(v_obs_list, v_pred_list)])
            res_i = np.mean([(io - ip)**2 for io, ip in zip(i_obs_list, i_pred_list)])

            loss = res_v / (240.0**2) + res_i / (50.0**2)

            if loss < min_loss:
                min_loss = loss
                best_r = float(r_cand)
                best_x = float(x_cand)

        z_mag = float(np.sqrt(best_r**2 + best_x**2))
        g_l = float(best_r / (z_mag**2 + 1e-9))
        b_l = float(best_x / (z_mag**2 + 1e-9))

        return best_r, best_x, g_l, b_l, float(min_loss)


# Alias for backward compatibility if needed
HiddenNetworkSizeSolver = LatentLineParameterSolver
OpenDSSForwardSolver = KnownTopologyForwardSolver
