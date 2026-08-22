from dataclasses import dataclass
import numpy as np
from src.estimator.load_group import ConsumerLoadPremises, ConsumerLoadClassModel

@dataclass
class ClusterLoadAllocationEstimate:
    feeder_supply_energy_kwh: float
    metered_customer_energy_kwh: float
    estimated_technical_loss_kwh: float
    unmetered_energy_pool_kwh: float
    estimated_unmetered_energy_kwh: float
    allocated_unmetered_customer_energy: dict[str, float]

class ClusterLoadAllocationEstimator:
    """
    Baseline Cluster Load Allocation (CLA) Estimator:
    Formulates E_U = E_F - E_M - E_L and allocates unmetered customer energy:
        E_i_hat = E_U * (w_i / sum(w_j))
    """

    def estimate(
        self,
        feeder_supply_energy_kwh: float,
        metered_customer_energy_kwh: float,
        estimated_technical_loss_kwh: float,
        unmetered_premises: list[ConsumerLoadPremises]
    ) -> ClusterLoadAllocationEstimate:
        """
        Estimates unmetered customer energy allocations using baseline CLA.
        """
        e_u = max(0.0, float(feeder_supply_energy_kwh - metered_customer_energy_kwh - estimated_technical_loss_kwh))

        if not unmetered_premises:
            return ClusterLoadAllocationEstimate(
                feeder_supply_energy_kwh=feeder_supply_energy_kwh,
                metered_customer_energy_kwh=metered_customer_energy_kwh,
                estimated_technical_loss_kwh=estimated_technical_loss_kwh,
                unmetered_energy_pool_kwh=e_u,
                estimated_unmetered_energy_kwh=0.0,
                allocated_unmetered_customer_energy={}
            )

        weights = {}
        for p in unmetered_premises:
            w_i = ConsumerLoadClassModel.compute_expected_weight(p)
            weights[p.consumer_id] = w_i

        sum_w = sum(weights.values())
        if sum_w <= 0:
            sum_w = float(len(unmetered_premises))
            weights = {p.consumer_id: 1.0 for p in unmetered_premises}

        allocations = {}
        for cid, w_i in weights.items():
            e_hat_i = e_u * (w_i / sum_w)
            allocations[cid] = round(float(e_hat_i), 4)

        total_allocated = float(sum(allocations.values()))

        return ClusterLoadAllocationEstimate(
            feeder_supply_energy_kwh=round(float(feeder_supply_energy_kwh), 4),
            metered_customer_energy_kwh=round(float(metered_customer_energy_kwh), 4),
            estimated_technical_loss_kwh=round(float(estimated_technical_loss_kwh), 4),
            unmetered_energy_pool_kwh=round(e_u, 4),
            estimated_unmetered_energy_kwh=round(total_allocated, 4),
            allocated_unmetered_customer_energy=allocations
        )
