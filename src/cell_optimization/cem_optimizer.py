from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import gc
import numpy as np


@dataclass
class CEMResult:
    """
    Result of ONE scalar Cross-Entropy Method (CEM) optimization run.
    """
    best_x: np.ndarray
    elite_x: List[np.ndarray]
    best_value: float


class CrossEntropyOptimizer:
    """
    Stage 1: Sensitivity-Guided Cross-Entropy Method (SG-CEM) Optimizer.
    Optimizes exactly ONE scalar objective function f(theta) -> R per run.

    No FEM, no thermoelastic model, and no structural optimization in cem_optimizer.py.
    """

    def __init__(
        self,
        population_size: int = 8,
        iterations: int = 3,
        elite_fraction: float = 0.25,
        smoothing: float = 0.7,
        min_std: float = 0.01,
        random_seed: Optional[int] = None,
    ):
        self.population_size = population_size
        self.iterations = iterations
        self.elite_fraction = elite_fraction
        self.smoothing = smoothing
        self.min_std = min_std
        self.rng = np.random.default_rng(random_seed)

    @staticmethod
    def _to_z(x: np.ndarray, xl: np.ndarray, xu: np.ndarray) -> np.ndarray:
        return (x - xl) / np.maximum(xu - xl, 1e-12)

    @staticmethod
    def _to_x(z: np.ndarray, xl: np.ndarray, xu: np.ndarray) -> np.ndarray:
        return xl + z * (xu - xl)

    def compute_sensitivity(
        self,
        objective_func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: np.ndarray,
        active_indices: Sequence[int],
        relative_step: float = 1e-3,
    ) -> Dict[str, Any]:
        """
        Calculates central finite-difference gradient and dimensionless elasticity for 1 scalar objective function.
        """
        act_idx = np.asarray(active_indices, dtype=int)
        dim = len(act_idx)

        f0 = float(objective_func(x0))

        J_f = np.zeros(dim, dtype=float)
        elasticity = np.zeros(dim, dtype=float)

        for col, j in enumerate(act_idx):
            lower = float(bounds[j, 0])
            upper = float(bounds[j, 1])

            scale = max(abs(x0[j]), abs(upper - lower), 1e-12)
            h = relative_step * scale

            can_minus = (x0[j] - h >= lower)
            can_plus = (x0[j] + h <= upper)

            if can_plus and can_minus:
                x_plus = x0.copy()
                x_minus = x0.copy()
                x_plus[j] += h
                x_minus[j] -= h

                f_plus = float(objective_func(x_plus))
                f_minus = float(objective_func(x_minus))

                J_f[col] = (f_plus - f_minus) / (2.0 * h)
            elif can_plus:
                x_plus = x0.copy()
                x_plus[j] += h
                f_plus = float(objective_func(x_plus))
                J_f[col] = (f_plus - f0) / h
            elif can_minus:
                x_minus = x0.copy()
                x_minus[j] -= h
                f_minus = float(objective_func(x_minus))
                J_f[col] = (f0 - f_minus) / h

            denom = max(abs(f0), 1e-12)
            elasticity[col] = abs(x0[j] / denom * J_f[col])

        return {
            "f0": f0,
            "gradient": J_f,
            "elasticity": elasticity,
        }

    def optimize(
        self,
        objective_func: Callable[[np.ndarray], float],
        x0: np.ndarray,
        bounds: np.ndarray,
        active_indices: Sequence[int],
        rounding_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        verbose: bool = False,
    ) -> CEMResult:
        """
        Solves 1 scalar optimization function f(theta) -> R.
        Computes finite-difference sensitivity, performs local gradient step,
        and samples CEM candidates around that guided point.
        Returns CEMResult(best_x, elite_x, best_value).
        """
        act_idx = np.asarray(active_indices, dtype=int)
        dim = len(act_idx)

        xl = bounds[act_idx, 0]
        xu = bounds[act_idx, 1]

        # 1. PyBaMM baseline sensitivity
        sens = self.compute_sensitivity(
            objective_func=objective_func,
            x0=x0,
            bounds=bounds,
            active_indices=act_idx,
        )

        grad = sens["gradient"]
        elasticity = sens["elasticity"]

        e_max = max(float(np.max(elasticity)), 1e-12)
        w_sens = elasticity / e_max

        # 2. Signed gradient local improvement step
        norm_grad = np.linalg.norm(grad)
        direction = -grad / norm_grad if norm_grad > 1e-12 else np.zeros(dim)

        initial_step = 0.05 * (xu - xl)
        x_guided = np.clip(x0[act_idx] + direction * initial_step, xl, xu)
        mu_z = self._to_z(x_guided, xl, xu)

        # 3. Sensitivity-based initial covariance scaling
        sigma_max = 0.20
        sigma_min = self.min_std
        sigma = np.maximum(sigma_max - (sigma_max - sigma_min) * w_sens, sigma_min)
        cov_z = np.diag(sigma ** 2)

        best_score = float(sens["f0"])
        best_x = x0.copy()
        elite_samples: List[np.ndarray] = [x0.copy()]

        # 4. CEM iterations
        for iteration in range(self.iterations):
            raw_z = self.rng.multivariate_normal(mean=mu_z, cov=cov_z, size=self.population_size)
            samples_z = np.clip(raw_z, 0.0, 1.0)

            evaluated = []
            for z in samples_z:
                x_cand = x0.copy()
                x_cand[act_idx] = self._to_x(z, xl, xu)
                if rounding_func is not None:
                    x_cand = rounding_func(x_cand)

                try:
                    score = float(objective_func(x_cand))
                    evaluated.append((score, x_cand, z))
                except Exception as exc:
                    if verbose:
                        print(f"WARNING[CEM]: Candidate evaluation failed: {exc}")

            if not evaluated:
                raise RuntimeError("CEM produced no valid candidate evaluations.")

            evaluated.sort(key=lambda item: item[0])

            if evaluated[0][0] < best_score:
                best_score = evaluated[0][0]
                best_x = evaluated[0][1].copy()

            elite_count = max(2, min(len(evaluated), int(np.ceil(self.elite_fraction * len(evaluated)))))
            elites = evaluated[:elite_count]

            elite_samples = [item[1].copy() for item in elites]
            elites_z = np.array([item[2] for item in elites])
            scores = np.array([item[0] for item in elites])

            score_shift = scores - np.min(scores)
            weights = np.exp(-5.0 * score_shift / max(np.std(scores), 1e-12))
            weights /= np.sum(weights)

            new_mu_z = np.sum(weights[:, None] * elites_z, axis=0)
            centered = elites_z - new_mu_z
            new_cov_z = centered.T @ (centered * weights[:, None])
            new_cov_z += np.eye(dim) * (self.min_std ** 2)

            mu_z = self.smoothing * new_mu_z + (1.0 - self.smoothing) * mu_z
            cov_z = self.smoothing * new_cov_z + (1.0 - self.smoothing) * cov_z

            diag = np.maximum(np.diag(cov_z), sigma ** 2)
            cov_z = np.diag(diag)

            if verbose:
                print(f"[CEM] Iteration {iteration+1}/{self.iterations} | Best Score: {best_score:.6e}")

            gc.collect()

        return CEMResult(
            best_x=best_x,
            elite_x=elite_samples,
            best_value=best_score,
        )
