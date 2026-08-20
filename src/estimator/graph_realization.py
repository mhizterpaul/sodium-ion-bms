from dataclasses import dataclass
import numpy as np
from src.estimator.graph_model import LVNetworkGraph, ConsumerUnitNode, NetworkGraphBranch

@dataclass
class GraphRealizationEstimate:
    known_number_of_buses: int
    known_number_of_branches: int
    estimated_total_consumer_units: int
    estimated_metered_consumer_units: int
    estimated_unmetered_consumer_units: int
    estimated_unmetered_power_kw: float
    r_eq_ohm: float
    x_eq_ohm: float
    z_eq_ohm: float
    objective_loss: float

class GraphBasedConsumerEstimator:
    """
    Graph-Based Realization Algorithm:
    1. Represents the known network as a graph G = (V, E) with 36% metered consumer units.
    2. Extends the graph network by exploring existing branches and replicating these branches into
       random nodes of the network, using non-resampling sequence memory (branches not resampled in each cycle)
       until matching feeder reading.
    3. Estimates the number of unknown (unmetered) consumer units and load profiles.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def estimate(
        self,
        metered_consumer_measurements: list[dict],
        feeder_measurements: dict,
        known_num_buses: int = 20,
        known_num_branches: int = 19
    ) -> GraphRealizationEstimate:
        """
        Args:
            metered_consumer_measurements: 36% metered consumer observations.
            feeder_measurements: feeder head / boundary transformer secondary measurement dict.
            known_num_buses: known count of network buses.
            known_num_branches: known count of network branches.

        Returns:
            GraphRealizationEstimate
        """
        rng = np.random.default_rng(self.seed)

        # 1. Initialize Known Graph G
        graph = LVNetworkGraph(network_id="known_lv_graph")

        # Add known branches
        for i in range(1, known_num_branches + 1):
            l_km = round(float(0.05 + 0.01 * (i % 5)), 4)
            graph.add_branch(NetworkGraphBranch(
                branch_id=f"branch_{i}",
                from_bus=f"bus_{i-1}",
                to_bus=f"bus_{i}",
                length_km=l_km
            ))

        # Add 36% metered consumer units
        metered_power_sum = 0.0
        n_metered = max(1, len(metered_consumer_measurements))

        for idx, m_meas in enumerate(metered_consumer_measurements):
            p_kw = float(m_meas.get("p_kw", 12.0))
            metered_power_sum += p_kw
            graph.add_node(ConsumerUnitNode(
                node_id=f"metered_consumer_{idx}",
                bus_id=f"bus_{(idx % known_num_buses) + 1}",
                is_metered=True,
                nominal_kw=p_kw,
                measured_kw=p_kw
            ))

        # Get total power reading from feeder head / boundary transformer
        p_feeder = float(feeder_measurements.get("p_kw", metered_power_sum / 0.36 if metered_power_sum > 0 else 100.0))
        power_residual = max(0.0, p_feeder - metered_power_sum)

        # 2. Graph Extension Algorithm with Non-Resampling Branch Sequence Memory
        available_branch_indices = list(range(len(graph.branches)))
        rng.shuffle(available_branch_indices)

        n_unmetered = 0
        p_unmetered_added = 0.0
        avg_consumer_unit_kw = float(np.mean([m.get("p_kw", 12.0) for m in metered_consumer_measurements])) if metered_consumer_measurements else 12.0
        avg_consumer_unit_kw = max(3.0, avg_consumer_unit_kw)

        while p_unmetered_added < power_residual:
            if not available_branch_indices:
                # Refresh non-resampling sequence memory for new expansion cycle
                available_branch_indices = list(range(len(graph.branches)))
                rng.shuffle(available_branch_indices)

            # Pop branch from sequence memory without replacement
            branch_idx = available_branch_indices.pop()
            base_branch = graph.branches[branch_idx]

            # Replicate branch to a random node
            target_node_bus = str(rng.choice(list(graph.buses)))
            new_unmetered_bus = f"bus_unmetered_{n_unmetered + 1}"

            replicated_branch = NetworkGraphBranch(
                branch_id=f"repl_{base_branch.branch_id}_{n_unmetered + 1}",
                from_bus=target_node_bus,
                to_bus=new_unmetered_bus,
                length_km=base_branch.length_km
            )
            graph.add_branch(replicated_branch)

            unmetered_kw = round(float(rng.uniform(0.8, 1.2) * avg_consumer_unit_kw), 2)
            graph.add_node(ConsumerUnitNode(
                node_id=f"unmetered_consumer_{n_unmetered + 1}",
                bus_id=new_unmetered_bus,
                is_metered=False,
                nominal_kw=unmetered_kw,
                measured_kw=0.0
            ))

            n_unmetered += 1
            p_unmetered_added += unmetered_kw

        n_total = n_metered + n_unmetered
        r_eq, x_eq, z_eq = graph.compute_equivalent_impedance()
        objective_loss = round(float(abs(p_feeder - (metered_power_sum + p_unmetered_added)) / (p_feeder + 1e-6)), 6)

        return GraphRealizationEstimate(
            known_number_of_buses=known_num_buses,
            known_number_of_branches=known_num_branches,
            estimated_total_consumer_units=n_total,
            estimated_metered_consumer_units=n_metered,
            estimated_unmetered_consumer_units=n_unmetered,
            estimated_unmetered_power_kw=round(p_unmetered_added, 2),
            r_eq_ohm=r_eq,
            x_eq_ohm=x_eq,
            z_eq_ohm=z_eq,
            objective_loss=objective_loss
        )
