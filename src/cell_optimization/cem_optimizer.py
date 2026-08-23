from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import gc
import numpy as np


@dataclass
class EvaluationResult:
    """
    Result of ONE evaluation.
    """
    objective: float
    constraints: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=float)
    )
    feasible: bool = True
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CEMResult:
    """
    Result of ONE local Sensitivity-Conditioned Cross-Entropy Method (SG-CEM) optimization run.
    """
    best_x: np.ndarray
    elite_x: List[np.ndarray]
    best_value: float
    symbolic_x: np.ndarray
    symbolic_value: float
    improvement: float
    sensitivity: np.ndarray
    search_radius: np.ndarray


class CrossEntropyOptimizer:
    """
    Sensitivity-Conditioned Cross-Entropy Method (SG-CEM) Optimizer.
    Uses x_symbolic as anchor, calculates local sensitivity at x_symbolic,
    constructs a narrow sensitivity-conditioned local trust region around x_symbolic,
    and performs local stochastic verification/refinement.
    """

    def __init__(
        self,
        population_size: int = 4,
        iterations: int = 2,
        elite_fraction: float = 0.25,
        smoothing: float = 0.7,
        min_std: float = 0.005,
        min_radius: float = 0.005,
        max_radius: float = 0.03,
        random_seed: Optional[int] = None,
    ):
        self.population_size = population_size
        self.iterations = iterations
        self.elite_fraction = elite_fraction
        self.smoothing = smoothing
        self.min_std = min_std
        self.min_radius = min_radius
        self.max_radius = max_radius
        self.rng = np.random.default_rng(random_seed)

    def compute_sensitivity(
        self,
        objective_func: Callable[[np.ndarray], float],
        x_symbolic: np.ndarray,
        bounds: np.ndarray,
        active_indices: Sequence[int],
        relative_step: float = 1e-3,
    ) -> Dict[str, Any]:
        """
        Calculates central finite-difference gradient, diagonal Hessian, and dimensionless elasticity at x_symbolic.
        """
        act_idx = np.asarray(active_indices, dtype=int)
        dim = len(act_idx)

        f0 = float(objective_func(x_symbolic))

        grad = np.zeros(dim, dtype=float)
        elasticity = np.zeros(dim, dtype=float)

        for col, j in enumerate(act_idx):
            lower = float(bounds[j, 0])
            upper = float(bounds[j, 1])

            scale = max(abs(x_symbolic[j]), abs(upper - lower), 1e-12)
            h = relative_step * scale

            can_minus = (x_symbolic[j] - h >= lower)
            can_plus = (x_symbolic[j] + h <= upper)

            if can_plus and can_minus:
                x_plus = x_symbolic.copy()
                x_minus = x_symbolic.copy()
                x_plus[j] += h
                x_minus[j] -= h

                f_plus = float(objective_func(x_plus))
                f_minus = float(objective_func(x_minus))

                grad[col] = (f_plus - f_minus) / (2.0 * h)
            elif can_plus:
                x_plus = x_symbolic.copy()
                x_plus[j] += h
                f_plus = float(objective_func(x_plus))
                grad[col] = (f_plus - f0) / h
            elif can_minus:
                x_minus = x_symbolic.copy()
                x_minus[j] -= h
                f_minus = float(objective_func(x_minus))
                grad[col] = (f0 - f_minus) / h

            denom = max(abs(f0), 1e-12)
            elasticity[col] = abs(x_symbolic[j] / denom * grad[col])

        return {
            "f0": f0,
            "gradient": grad,
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
        Performs local SG-CEM refinement around x_symbolic within a narrow sensitivity-conditioned trust region.
        Returns CEMResult containing best_x, elite_x, best_value, symbolic_x, symbolic_value, improvement, sensitivity, search_radius.
        """
        act_idx = np.asarray(active_indices, dtype=int)
        dim = len(act_idx)

        xl = bounds[act_idx, 0]
        xu = bounds[act_idx, 1]
        domain_span = xu - xl

        x_symbolic = x0.copy()
        symbolic_value = float(objective_func(x_symbolic))

        # 1. Compute sensitivity AT x_symbolic
        sens = self.compute_sensitivity(
            objective_func=objective_func,
            x_symbolic=x_symbolic,
            bounds=bounds,
            active_indices=act_idx,
        )

        elasticity = sens["elasticity"]
        e_max = max(float(np.max(elasticity)), 1e-12)
        e_norm = elasticity / e_max

        # 2. Sensitivity-conditioned trust region radius:
        # High sensitivity -> tiny search radius
        # Low sensitivity -> slightly larger search radius
        radius = self.min_radius + (1.0 - e_norm) * (self.max_radius - self.min_radius)
        search_radius_vals = radius * domain_span

        local_xl = np.maximum(xl, x_symbolic[act_idx] - search_radius_vals)
        local_xu = np.minimum(xu, x_symbolic[act_idx] + search_radius_vals)

        # Center at symbolic optimum
        mu = x_symbolic[act_idx].copy()
        sigma = search_radius_vals.copy()

        best_x = x_symbolic.copy()
        best_value = symbolic_value
        elite_samples: List[np.ndarray] = [x_symbolic.copy()]

        # 3. Local CEM refinement loop
        for iteration in range(self.iterations):
            samples = self.rng.normal(
                loc=mu,
                scale=sigma,
                size=(self.population_size, dim),
            )

            samples = np.clip(samples, local_xl, local_xu)

            evaluated = []
            # x_symbolic must always remain in the candidate set
            evaluated.append((symbolic_value, x_symbolic.copy()))

            for candidate_active in samples:
                candidate = x_symbolic.copy()
                candidate[act_idx] = candidate_active

                if rounding_func is not None:
                    candidate = rounding_func(candidate)

                try:
                    val = float(objective_func(candidate))
                    evaluated.append((val, candidate))
                except Exception as exc:
                    if verbose:
                        print(f"WARNING[CEM]: Perturbation candidate evaluation failed: {exc}")

            evaluated.sort(key=lambda item: item[0])

            best_value, best_x = evaluated[0][0], evaluated[0][1].copy()

            elite_count = max(2, int(np.ceil(self.elite_fraction * len(evaluated))))
            elites = evaluated[:elite_count]

            elite_samples = [item[1].copy() for item in elites]
            elite_values = np.array([item[0] for item in elites])
            elite_x = np.array([item[1][act_idx] for item in elites])

            # Weighted local covariance update
            score_shift = elite_values - elite_values.min()
            temperature = max(np.std(elite_values), 1e-12)
            weights = np.exp(-score_shift / temperature)
            weights /= weights.sum()

            mu = np.sum(weights[:, None] * elite_x, axis=0)
            variance = np.sum(weights[:, None] * (elite_x - mu) ** 2, axis=0)

            sigma = np.maximum(np.sqrt(variance), self.min_std * domain_span)
            sigma = np.minimum(sigma, search_radius_vals)
            mu = np.clip(mu, local_xl, local_xu)

            if verbose:
                print(f"[CEM] Iteration {iteration+1}/{self.iterations} | Best Score: {best_value:.6e}")

            gc.collect()

        improvement = max(0.0, symbolic_value - best_value)

        return CEMResult(
            best_x=best_x,
            elite_x=elite_samples,
            best_value=best_value,
            symbolic_x=x_symbolic,
            symbolic_value=symbolic_value,
            improvement=improvement,
            sensitivity=elasticity,
            search_radius=search_radius_vals,
        )
