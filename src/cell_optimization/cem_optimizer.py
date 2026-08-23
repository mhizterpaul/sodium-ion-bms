from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional, Callable, Union
import numpy as np
import copy
import gc

@dataclass
class EvaluationResult:
    objective: Union[float, np.ndarray]  # Can be scalar or vector of objective values
    constraints: List[float] = field(default_factory=list)  # g_k(theta) <= 0
    feasible: bool = True
    metrics: Dict[str, Any] = field(default_factory=dict)

class PyBaMMSensitivityAnalyzer:
    """
    Computes central finite difference sensitivities (Jacobians) and dimensionless elasticities
    from PyBaMM DFN evaluations.
    """

    def __init__(self, evaluator_func: Callable[[np.ndarray], EvaluationResult]):
        self.evaluator_func = evaluator_func

    def evaluate(self, x: np.ndarray) -> EvaluationResult:
        return self.evaluator_func(x)

    def jacobian(
        self,
        x0: np.ndarray,
        bounds: np.ndarray,
        active_indices: Optional[List[int]] = None,
        eps: float = 1e-3,
        obj_weights: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Calculates central finite-difference Jacobian J_F and J_g around x0 with bound-aware fallback,
        and dimensionless elasticity S_ij = | (theta_j / max(|F_i|, eps_F)) * (dF_i / dtheta_j) |.
        """
        if active_indices is None:
            active_indices = list(range(len(x0)))

        xl_full, xu_full = bounds[:, 0], bounds[:, 1]
        dim = len(active_indices)

        # Baseline evaluation
        res0 = self.evaluate(x0)
        obj0 = res0.objective
        f0 = np.array([float(obj0)]) if (np.isscalar(obj0) or isinstance(obj0, (int, float, np.floating))) else np.array(obj0, dtype=float)
        g0 = np.array(res0.constraints, dtype=float) if res0.constraints else np.array([])

        num_objs = len(f0)
        num_cons = len(g0)

        J_F = np.zeros((num_objs, dim))
        J_g = np.zeros((num_cons, dim)) if num_cons > 0 else np.zeros((0, dim))

        for idx, j in enumerate(active_indices):
            xl_j, xu_j = xl_full[j], xu_full[j]
            delta = eps * max(xu_j - xl_j, 1e-6)

            x_plus = x0.copy()
            x_minus = x0.copy()

            can_plus = (x0[j] + delta) <= xu_j
            can_minus = (x0[j] - delta) >= xl_j

            if can_plus and can_minus:
                x_plus[j] = x0[j] + delta
                x_minus[j] = x0[j] - delta

                res_plus = self.evaluate(x_plus)
                res_minus = self.evaluate(x_minus)

                f_plus = np.array([res_plus.objective]) if np.isscalar(res_plus.objective) else np.array(res_plus.objective, dtype=float)
                f_minus = np.array([res_minus.objective]) if np.isscalar(res_minus.objective) else np.array(res_minus.objective, dtype=float)

                g_plus = np.array(res_plus.constraints, dtype=float) if res_plus.constraints else np.array([])
                g_minus = np.array(res_minus.constraints, dtype=float) if res_minus.constraints else np.array([])

                h = 2.0 * delta
                J_F[:, idx] = (f_plus - f_minus) / h
                if num_cons > 0 and len(g_plus) == num_cons and len(g_minus) == num_cons:
                    J_g[:, idx] = (g_plus - g_minus) / h

            elif can_plus:
                x_plus[j] = x0[j] + delta
                res_plus = self.evaluate(x_plus)
                f_plus = np.array([res_plus.objective]) if np.isscalar(res_plus.objective) else np.array(res_plus.objective, dtype=float)
                g_plus = np.array(res_plus.constraints, dtype=float) if res_plus.constraints else np.array([])

                h = delta
                J_F[:, idx] = (f_plus - f0) / h
                if num_cons > 0 and len(g_plus) == num_cons:
                    J_g[:, idx] = (g_plus - g0) / h

            elif can_minus:
                x_minus[j] = x0[j] - delta
                res_minus = self.evaluate(x_minus)
                f_minus = np.array([res_minus.objective]) if np.isscalar(res_minus.objective) else np.array(res_minus.objective, dtype=float)
                g_minus = np.array(res_minus.constraints, dtype=float) if res_minus.constraints else np.array([])

                h = delta
                J_F[:, idx] = (f0 - f_minus) / h
                if num_cons > 0 and len(g_minus) == num_cons:
                    J_g[:, idx] = (g0 - g_minus) / h

        # Calculate dimensionless elasticity S_ij = | (theta_j / max(|F_i|, 1e-6)) * (dF_i / dtheta_j) |
        S_F = np.zeros((num_objs, dim))
        for i in range(num_objs):
            denom = max(abs(f0[i]), 1e-6)
            for idx, j in enumerate(active_indices):
                S_F[i, idx] = abs((x0[j] / denom) * J_F[i, idx])

        return {
            "objective": J_F,
            "constraints": J_g,
            "elasticity": S_F,
            "f0": f0,
            "g0": g0
        }

class CrossEntropyOptimizer:
    def __init__(
        self,
        population_size: int = 32,
        elite_fraction: float = 0.15,
        iterations: int = 5,
        smoothing: float = 0.7,
        min_std: float = 1e-4,
        lambda_penalty: float = 1e5,
        screening_ratio: float = 0.5,
    ):
        self.population_size = population_size
        self.elite_fraction = elite_fraction
        self.iterations = iterations
        self.smoothing = smoothing
        self.min_std = min_std
        self.lambda_penalty = lambda_penalty
        self.screening_ratio = screening_ratio

    def _to_z(self, x: np.ndarray, xl: np.ndarray, xu: np.ndarray) -> np.ndarray:
        range_val = np.maximum(xu - xl, 1e-12)
        return (x - xl) / range_val

    def _to_x(self, z: np.ndarray, xl: np.ndarray, xu: np.ndarray) -> np.ndarray:
        return xl + z * (xu - xl)

    def optimize(
        self,
        evaluator_func: Callable[[np.ndarray], EvaluationResult],
        x0: np.ndarray,
        bounds: np.ndarray,
        sensitivity: Optional[Dict[str, np.ndarray]] = None,
        active_indices: Optional[List[int]] = None,
        constraints: Optional[Callable[[np.ndarray], List[float]]] = None,
        rounding_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        surrogate_func: Optional[Callable[[np.ndarray], EvaluationResult]] = None,
        obj_weights: Optional[np.ndarray] = None,
        obj_refs: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> np.ndarray:
        """
        Sensitivity-Guided Cross-Entropy Method (SG-CEM) Optimizer.
        """
        if active_indices is None:
            active_indices = list(range(len(x0)))

        xl_full, xu_full = bounds[:, 0], bounds[:, 1]
        xl = xl_full[active_indices]
        xu = xu_full[active_indices]
        x0_act = x0[active_indices]
        dim = len(active_indices)

        # Compute sensitivity via PyBaMMSensitivityAnalyzer if not provided
        if sensitivity is None:
            analyzer = PyBaMMSensitivityAnalyzer(evaluator_func)
            sensitivity = analyzer.jacobian(x0, bounds, active_indices=active_indices)

        J_F = sensitivity.get("objective", np.zeros((1, dim)))
        J_g = sensitivity.get("constraints", np.zeros((0, dim)))
        S_F = sensitivity.get("elasticity", np.zeros((1, dim)))

        num_objs = J_F.shape[0]
        if obj_weights is None:
            weights = np.ones(num_objs) / float(num_objs)
        else:
            weights = np.array(obj_weights, dtype=float)
            weights = weights / np.sum(weights)

        # 1. Normalized Elasticity S_j = sum_i w_i S_ij
        S_j = np.sum(weights[:, None] * S_F, axis=0) if S_F.ndim == 2 else np.zeros(dim)
        s_max = np.max(S_j) if len(S_j) > 0 and np.max(S_j) > 0 else 1.0
        w_sens = S_j / s_max

        # 2. Signed gradient determines search direction: d = - sum_i w_i grad f_i + sum_k max(0, g_k) grad g_k
        grad_f_agg = np.sum(weights[:, None] * J_F, axis=0)
        d_j = -grad_f_agg

        if J_g.shape[0] > 0 and "g0" in sensitivity:
            g0 = sensitivity["g0"]
            for k in range(min(len(g0), J_g.shape[0])):
                if g0[k] > 0:
                    d_j += g0[k] * J_g[k]

        d_norm = np.linalg.norm(d_j)
        if d_norm > 1e-12:
            d_j = d_j / d_norm

        # Direction-guided initial mean
        alpha = 0.1 * (xu - xl)
        x_init = np.clip(x0_act + alpha * d_j, xl, xu)
        mu_z = self._to_z(x_init, xl, xu)

        # 3. Variance scaling based on normalized sensitivity magnitude
        sigma_max = 0.25
        sigma_min = 0.02
        std_fractions = sigma_max - (sigma_max - sigma_min) * w_sens
        std_fractions = np.maximum(std_fractions, sigma_min)

        cov_z = np.diag(std_fractions ** 2)
        initial_std_z = np.sqrt(np.diag(cov_z))

        best_score = 1e12
        best_x = x0_act.copy()
        best_history = []

        pop_size = self.population_size

        for it in range(self.iterations):
            raw_samples_z = np.random.multivariate_normal(mu_z, cov_z, size=pop_size)
            samples_z = np.clip(raw_samples_z, 0.0, 1.0)
            samples_x = np.array([self._to_x(z, xl, xu) for z in samples_z])

            if rounding_func is not None:
                samples_x = np.array([rounding_func(x) for x in samples_x])

            # Cheap screening if surrogate is provided
            if surrogate_func is not None:
                num_screened = max(int(pop_size * self.screening_ratio), 4)
                cheap_results = [surrogate_func(x) for x in samples_x]
                cheap_scores = []
                for res in cheap_results:
                    sc = np.sum(res.objective) if isinstance(res.objective, np.ndarray) else res.objective
                    pen = self.lambda_penalty * sum(max(0.0, g)**2 for g in res.constraints)
                    cheap_scores.append(sc + pen)
                eval_indices = np.argsort(cheap_scores)[:num_screened].tolist()
            else:
                eval_indices = list(range(pop_size))

            # Full evaluation on selected candidates
            eval_results = []
            for idx in eval_indices:
                x_cand = samples_x[idx]
                x_full = x0.copy()
                x_full[active_indices] = x_cand

                try:
                    res = evaluator_func(x_full)
                except Exception as e:
                    res = EvaluationResult(objective=1e9, constraints=[1.0], feasible=False, metrics={"error": str(e)})

                # Normalized objective calculation
                if isinstance(res.objective, np.ndarray):
                    if obj_refs is not None and len(obj_refs) == len(res.objective):
                        norm_obj = res.objective / obj_refs
                    else:
                        norm_obj = res.objective
                    obj_val = np.dot(weights, norm_obj)
                else:
                    obj_val = float(res.objective)

                # Standardized penalty calculation: P(theta) = lambda * sum(max(0, g_k)^2)
                penalty = 0.0
                if res.constraints:
                    violations = [max(0.0, g) for g in res.constraints]
                    penalty = self.lambda_penalty * sum(v**2 for v in violations)
                    if not res.feasible and penalty == 0.0:
                        penalty = 1e5
                elif not res.feasible:
                    penalty = 1e5

                score = obj_val + penalty
                eval_results.append((idx, score, res))

            # CRITICAL FIX: Only evaluated candidates participate in elite selection
            evaluated_indices = np.array([idx for idx, _, _ in eval_results])
            evaluated_scores = np.array([sc for _, sc, _ in eval_results])

            order = np.argsort(evaluated_scores)
            sorted_eval_scores = evaluated_scores[order]
            sorted_eval_indices = evaluated_indices[order]
            sorted_eval_samples_z = samples_z[sorted_eval_indices]

            # Adaptive Elite Fraction
            progress = it / max(1, self.iterations)
            if progress < 0.3:
                elite_frac = 0.25
            elif progress < 0.7:
                elite_frac = 0.15
            else:
                elite_frac = 0.05

            num_evaluated = len(eval_results)
            elite_count = max(2, min(int(pop_size * elite_frac), num_evaluated))

            elites_z = sorted_eval_samples_z[:elite_count]
            elite_scores = sorted_eval_scores[:elite_count]

            if elite_scores[0] < best_score:
                best_score = elite_scores[0]
                best_x = self._to_x(elites_z[0], xl, xu)

            # Elite Diversity Check
            if len(elites_z) >= 2:
                elite_std = np.std(elites_z, axis=0)
                if np.max(elite_std) < 0.005:
                    if verbose:
                        print(f"INFO[CEM]: Elite diversity collapse detected. Boosting covariance.")
                    cov_z += np.diag((0.1 * initial_std_z) ** 2)

            # Update distribution parameters using weighted elites
            if len(elites_z) >= 2:
                min_es = np.min(elite_scores)
                max_es = np.max(elite_scores)
                range_es = max_es - min_es
                norm_scores = (elite_scores - min_es) / range_es if range_es > 1e-12 else np.zeros_like(elite_scores)

                w = np.exp(-5.0 * norm_scores)
                w /= np.sum(w)

                new_mu_z = np.sum(w[:, None] * elites_z, axis=0)
                diff = elites_z - new_mu_z
                new_cov_z = np.zeros_like(cov_z)
                for j in range(len(elites_z)):
                    new_cov_z += w[j] * np.outer(diff[j], diff[j])

                mu_z = self.smoothing * new_mu_z + (1.0 - self.smoothing) * mu_z
                cov_z = self.smoothing * new_cov_z + (1.0 - self.smoothing) * cov_z

                # Sensitivity-based covariance contraction
                alpha_jac = 0.1
                d_factors = 1.0 / np.sqrt(1.0 + alpha_jac * w_sens)
                cov_z = (d_factors[:, None] * cov_z) * d_factors[None, :]
            else:
                mu_z = 0.5 * sorted_eval_samples_z[0] + 0.5 * mu_z

            if verbose:
                num_feas = sum(1 for _, _, r in eval_results if r.feasible)
                print(f"INFO[CEM]: Iteration {it+1}/{self.iterations} - Best Score: {best_score:.6f} - Feasible evaluated: {num_feas}/{num_evaluated}")

            # Convergence checks
            best_history.append(best_score)
            if len(best_history) >= 5:
                window_var = np.var(best_history[-5:])
                if window_var < 1e-8:
                    if verbose:
                        print(f"INFO[CEM]: Converged on stable best objective score variance: {window_var:.3e} < 1e-8")
                    break

            max_std = np.max(np.sqrt(np.diag(cov_z)))
            if max_std < self.min_std:
                if verbose:
                    print(f"INFO[CEM]: Converged on max std of covariance: {max_std:.6e} < {self.min_std}")
                break

            gc.collect()

        x_res = x0.copy()
        x_res[active_indices] = best_x
        return x_res
