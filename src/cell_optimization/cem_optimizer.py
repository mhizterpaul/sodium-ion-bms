import numpy as np
from concurrent.futures import ProcessPoolExecutor

class CrossEntropyOptimizer:
    def __init__(
        self,
        population_size=32,
        elite_fraction=0.15,
        iterations=5,
        smoothing=0.7,
        min_std=1e-4,
        lambda_penalty=1e5
    ):
        self.population_size = population_size
        self.elite_fraction = elite_fraction
        self.iterations = iterations
        self.smoothing = smoothing
        self.min_std = min_std
        self.lambda_penalty = lambda_penalty

    def _to_z(self, x, xl, xu):
        range_val = np.maximum(xu - xl, 1e-12)
        return (x - xl) / range_val

    def _to_x(self, z, xl, xu):
        return xl + z * (xu - xl)
        


    def optimize(self, evaluator_func, x0, bounds, active_indices, G_vector, rounding_func=None, verbose=True):
        """
        Sensitivity-Guided Cross-Entropy Method (SG-CEM) Optimizer.
        """
        xl_full, xu_full = bounds[:, 0], bounds[:, 1]
        xl = xl_full[active_indices]
        xu = xu_full[active_indices]

        # 1. Sensitivity-Weighted Initialization
        G_active = np.abs(G_vector[active_indices])
        max_g = np.max(G_active) if np.max(G_active) > 0 else 1.0
        w_sens = G_active / max_g

        sigma_max = 0.25
        sigma_min = 0.02
        std_fractions = (1.0 - w_sens) * sigma_max + w_sens * sigma_min

        mu_z = self._to_z(x0[active_indices], xl, xu)
        cov_z = np.diag(std_fractions ** 2)
        initial_std_z = np.sqrt(np.diag(cov_z))

        best_score = 1e12
        best_x = x0[active_indices].copy()
        best_history = []

        try:
                with ProcessPoolExecutor(max_workers=2) as executor:
                    raw_results = list(executor.map(evaluator_func, jobs))
            except Exception:
                # Fallback to sequential execution if parallel pool fails
                raw_results = []
                for job in jobs:
                    res_val = evaluator_func(job)
                    raw_results.append(res_val)
                    # CLEANUP AFTER EACH SEQUENTIAL EVALUATION!
                    import sys
                    import gc
                    import shutil
                    from pathlib import Path

                    shutil.rmtree(Path.home() / ".cache" / "pybamm", ignore_errors=True)
                    for module_name, module in list(sys.modules.items()):
                        if module_name.startswith("pybamm"):
                            for attr_name in dir(module):
                                try:
                                    attr = getattr(module, attr_name)
                                    if hasattr(attr, "cache_clear") and callable(attr.cache_clear):
                                        attr.cache_clear()
                                    elif hasattr(attr, "clear_cache") and callable(attr.clear_cache):
                                        attr.clear_cache()
                                except Exception:
                                    pass
                    gc.collect()
                    
            results = []
            for res_raw in raw_results:
                if isinstance(res_raw, tuple):
                    score_unpenalized = res_raw[0]
                    feasible = res_raw[1] if len(res_raw) == 2 else res_raw[2]
                    g_list = [] if len(res_raw) == 2 else res_raw[1]
                else:
                    score_unpenalized = res_raw
                    feasible = True
                    g_list = []

                # Penalize infeasible samples: f_penalized = f + lambda * sum(max(0, g)^2)
                penalty = 0.0
                if g_list:
                    violations = [max(0.0, g) for g in g_list]
                    penalty = self.lambda_penalty * sum(v**2 for v in violations)
                    if not feasible:
                        assert sum(violations) > 0.0 or any(g > 0.0 for g in g_list), "Inconsistent feasibility and constraint violation list."
                        if penalty == 0.0:
                            penalty = 1e5
                elif not feasible:
                    penalty = 1e5

                score = score_unpenalized + penalty
                results.append((score, feasible))

            scores = np.array([r[0] for r in results])
            feasibles = np.array([r[1] for r in results])

            indices = np.argsort(scores)
            sorted_scores = scores[indices]
            sorted_samples_z = samples_z[indices]

            # 7. Adaptive Elite Fraction
            progress = it / self.iterations
            if progress < 0.3:
                elite_frac = 0.25
            elif progress < 0.7:
                elite_frac = 0.15
            else:
                elite_frac = 0.05

            elite_count = max(2, int(pop_size * elite_frac))
            elites_z = sorted_samples_z[:elite_count]
            elite_scores = sorted_scores[:elite_count]

            if elite_scores[0] < best_score:
                best_score = elite_scores[0]
                best_x = self._to_x(elites_z[0], xl, xu)

            # 8. Elite Diversity Check
            if len(elites_z) >= 2:
                elite_std = np.std(elites_z, axis=0)
                if np.max(elite_std) < 0.005:
                    if verbose:
                        print(f"INFO[CEM]: Elite diversity collapse detected. Boosting covariance.")
                    cov_z += np.diag((0.1 * initial_std_z) ** 2)

            # 9. Update distribution parameters using weighted elites
            if len(elites_z) >= 2:
                min_es = np.min(elite_scores)
                max_es = np.max(elite_scores)
                range_es = max_es - min_es
                if range_es > 1e-12:
                    norm_scores = (elite_scores - min_es) / range_es
                else:
                    norm_scores = np.zeros_like(elite_scores)

                # Selection pressure weighting: exp(-5.0 * norm_scores)
                w = np.exp(-5.0 * norm_scores)
                w /= np.sum(w)

                new_mu_z = np.sum(w[:, None] * elites_z, axis=0)

                diff = elites_z - new_mu_z
                new_cov_z = np.zeros_like(cov_z)
                for j in range(len(elites_z)):
                    new_cov_z += w[j] * np.outer(diff[j], diff[j])

                mu_z = self.smoothing * new_mu_z + (1.0 - self.smoothing) * mu_z
                cov_z = self.smoothing * new_cov_z + (1.0 - self.smoothing) * cov_z

                # Diagonal scaling D * Sigma * D for sensitivity-based contraction
                alpha_jac = 0.1
                d_factors = 1.0 / np.sqrt(1.0 + alpha_jac * w_sens)
                cov_z = (d_factors[:, None] * cov_z) * d_factors[None, :]
            else:
                mu_z = 0.5 * sorted_samples_z[0] + 0.5 * mu_z

            if verbose:
                num_feas = np.sum(feasibles)
                print(f"INFO[CEM]: Iteration {it+1}/{self.iterations} - Best Score: {best_score:.6f} - Feasible: {num_feas}/{pop_size}")

            # 10. Sliding window variance convergence check
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

        return best_x
