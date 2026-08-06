import numpy as np
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
ProcessPoolExecutor = ThreadPoolExecutor

class CrossEntropyOptimizer:
    def __init__(
        self,
        population_size=64,
        elite_fraction=0.15,
        iterations=15,
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

    def _reflect_sample(self, mu, cov, size):
        """
        Draw samples in z-space and fold them back into [0, 1] using reflection.
        """
        d = len(mu)
        try:
            raw_samples = np.random.multivariate_normal(mu, cov, size=size)
        except np.linalg.LinAlgError:
            stds = np.sqrt(np.maximum(np.diag(cov), 1e-12))
            raw_samples = np.random.normal(mu, stds, size=(size, d))

        # Reflection sampling
        for i in range(size):
            for j in range(d):
                val = raw_samples[i, j]
                while val < 0.0 or val > 1.0:
                    if val < 0.0:
                        val = -val
                    elif val > 1.0:
                        val = 2.0 - val
                raw_samples[i, j] = val
        return raw_samples

    def _evaluate_one(self, sample_z, evaluator_func, x0, active_indices, xl, xu, rounding_func=None):
        """
        Private helper method to evaluate a single candidate sample.
        """
        x_active = self._to_x(sample_z, xl, xu)
        x_full = x0.copy()
        x_full[active_indices] = x_active

        # Apply domain-specific rounding if provided
        if rounding_func is not None:
            x_full = rounding_func(x_full)

        res_eval = evaluator_func(x_full)
        if isinstance(res_eval, tuple):
            if len(res_eval) == 3:
                obj_val, g_list, feasible = res_eval
            else:
                obj_val, feasible = res_eval
                g_list = [0.0] if feasible else [1.0]
        else:
            obj_val = res_eval
            feasible = True
            g_list = [0.0]

        # Penalize infeasible samples: f_penalized = f + lambda * sum(max(0, g)^2)
        penalty = 0.0
        if g_list:
            violations = [max(0.0, g) for g in g_list]
            penalty = self.lambda_penalty * sum(v**2 for v in violations)
            if not feasible:
                assert sum(violations) > 0.0 or any(g > 0.0 for g in g_list), "Inconsistent feasibility and constraint violation list."
                if penalty == 0.0:
                    penalty = 1e5

        score = obj_val + penalty
        return score, feasible, x_full

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

        for it in range(self.iterations):
            # 2. Adaptive Population Size via smooth continuous schedule
            max_std_ratio = np.max(np.sqrt(np.diag(cov_z)) / (initial_std_z + 1e-12))
            if max_std_ratio >= 0.5:
                pop_size = self.population_size
            elif max_std_ratio <= 0.05:
                pop_size = 8
            else:
                fraction = (max_std_ratio - 0.05) / 0.45
                pop_size = int(8 + fraction * (self.population_size - 8))

            # 3. Covariance Regularization
            eigvals, eigvecs = np.linalg.eigh(cov_z)
            eigvals = np.maximum(eigvals, self.min_std**2)
            cov_z_reg = eigvecs @ np.diag(eigvals) @ eigvecs.T

            # 4. Draw samples in z-space
            samples_z = self._reflect_sample(mu_z, cov_z_reg, pop_size)

            # 5. Round samples in x-space immediately (using rounding_func if provided) and project them back to z-space
            # Rounding occurs BEFORE evaluation and BEFORE elite updates
            rounded_samples_z = []
            for sample_z in samples_z:
                x_active = self._to_x(sample_z, xl, xu)
                x_full = x0.copy()
                x_full[active_indices] = x_active

                if rounding_func is not None:
                    x_full = rounding_func(x_full)

                rounded_active = x_full[active_indices]
                rounded_sample_z = self._to_z(rounded_active, xl, xu)
                rounded_samples_z.append(rounded_sample_z)

            samples_z = np.array(rounded_samples_z)

            # 6. Run parallel evaluations using ProcessPoolExecutor as requested
            with ProcessPoolExecutor() as executor:
                jobs = [(sz, evaluator_func, x0, active_indices, xl, xu, rounding_func) for sz in samples_z]
                results = list(executor.map(lambda job: self._evaluate_one(*job), jobs))

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

                # Stronger selection pressure weighting: exp(-5.0 * norm_scores)
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
