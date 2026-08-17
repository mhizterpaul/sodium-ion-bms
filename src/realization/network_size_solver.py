import numpy as np

class OpenDSSForwardSolver:
    """
    Predicts boundary voltage V, current I, active power P, and reactive power Q for a candidate hidden network structure.
    """

    def predict(self, n_buses: int, n_branches: int, r_eq: float, x_eq: float, load_kw_list: list[float]) -> list[dict]:
        """
        Simulates predicted boundary observations across multiple operating points.
        """
        predictions = []
        for kw in load_kw_list:
            i_pred = (kw * 1000.0) / (3.0 * 240.0 * 0.95 + 1e-6)
            v_drop = i_pred * r_eq
            v_pred = 240.0 - v_drop
            q_pred = kw * np.tan(np.arccos(0.95))

            predictions.append({
                "v_pred": max(200.0, float(v_pred)),
                "i_pred": float(i_pred),
                "p_pred": float(kw),
                "q_pred": float(q_pred)
            })
        return predictions


class HiddenNetworkSizeSolver:
    """
    Mixed discrete structural search over candidate bus counts N_b in [20..35]
    using regularized residual loss J = Residual + lambda_b * N_b + lambda_l * N_l.
    """

    def __init__(self, forward_solver: OpenDSSForwardSolver = None):
        self.forward_solver = forward_solver or OpenDSSForwardSolver()

    def solve(self, observed_ops: list[dict], candidate_n_buses_range: range = range(20, 36)) -> tuple[int, int, float]:
        """
        Searches candidate network sizes and selects optimal (N_b_hat, N_l_hat) minimizing regularized loss.
        """
        best_n_b = 20
        best_n_l = 19
        min_loss = float("inf")

        load_kw_list = [op.get("p_kw", 10.0) for op in observed_ops]
        v_obs_list = [op.get("v_avg", 240.0) for op in observed_ops]
        i_obs_list = [op.get("i_avg", 15.0) for op in observed_ops]

        for n_b in candidate_n_buses_range:
            n_l = n_b - 1  # Radial tree structure assumption
            r_candidate = 0.45 * (0.1 * (n_b / 20.0))
            x_candidate = 0.15 * (0.1 * (n_b / 20.0))

            predictions = self.forward_solver.predict(n_b, n_l, r_candidate, x_candidate, load_kw_list)

            v_pred_list = [p["v_pred"] for p in predictions]
            i_pred_list = [p["i_pred"] for p in predictions]

            res_v = np.mean([(vo - vp)**2 for vo, vp in zip(v_obs_list, v_pred_list)])
            res_i = np.mean([(io - ip)**2 for io, ip in zip(i_obs_list, i_pred_list)])

            # Regularization penalty to prevent overfitting
            loss = res_v / (240.0**2) + res_i / (50.0**2) + 0.001 * n_b

            if loss < min_loss:
                min_loss = loss
                best_n_b = n_b
                best_n_l = n_l

        return best_n_b, best_n_l, float(min_loss)
