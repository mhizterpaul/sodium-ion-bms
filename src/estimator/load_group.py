from dataclasses import dataclass
import numpy as np

@dataclass
class ConsumerLoadPremises:
    consumer_id: str
    class_id: str  # e.g., 'residential_light', 'commercial', 'industrial_motor'
    is_metered: bool
    connected_load_kw: float
    historical_billing_kwh: float = 100.0
    supply_availability: float = 1.0

class ConsumerLoadClassModel:
    """
    Consumer Premises and Load Class Representation for CLA:
    Defines consumer classes c and metered class energy profiles mu_c(t).
    """
    CLASSES = ["residential_light", "commercial", "industrial_motor"]

    CLASS_WEIGHTS = {
        "residential_light": 1.0,
        "commercial": 2.2,
        "industrial_motor": 3.5
    }

    @classmethod
    def compute_expected_weight(cls, premises: ConsumerLoadPremises) -> float:
        """
        Computes expected consumption weight w_i = E[E_i | C_i, X_i] based on premises characteristics.
        """
        base_w = cls.CLASS_WEIGHTS.get(premises.class_id, 1.0)
        return float(base_w * (premises.connected_load_kw / 10.0) * premises.supply_availability)

    @classmethod
    def get_metered_class_profile(cls, class_id: str, t_points: np.ndarray) -> np.ndarray:
        """
        Returns normalized metered class profile mu_c(t).
        """
        t = np.asarray(t_points, dtype=float)
        if class_id == "residential_light":
            profile = 0.5 + 0.5 * np.sin(2 * np.pi * t / 24.0)
        elif class_id == "commercial":
            profile = 0.2 + 0.8 * (1.0 / (1.0 + np.exp(-0.5 * (t - 12.0))))
        else: # industrial_motor
            profile = 0.8 + 0.2 * np.cos(2 * np.pi * t / 12.0)
        return np.maximum(0.05, profile)
