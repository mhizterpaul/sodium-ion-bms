from dataclasses import dataclass, field
import numpy as np

@dataclass
class ConsumerUnitNode:
    node_id: str
    bus_id: str
    is_metered: bool
    nominal_kw: float
    measured_kw: float = 0.0
    load_group: str = "residential_light"
    phase_config: str = "3-phase"

@dataclass
class NetworkGraphBranch:
    branch_id: str
    from_bus: str
    to_bus: str
    length_km: float
    r1_ohm_per_km: float = 0.21
    x1_ohm_per_km: float = 0.08

class LVNetworkGraph:
    """
    Graph representation G = (V, E) for an LV distribution network
    containing metered and unmetered consumer unit nodes and network branches.
    """
    def __init__(self, network_id: str):
        self.network_id = network_id
        self.nodes: dict[str, ConsumerUnitNode] = {}
        self.branches: list[NetworkGraphBranch] = []
        self.buses: set[str] = set()

    def add_bus(self, bus_id: str):
        self.buses.add(bus_id)

    def add_node(self, node: ConsumerUnitNode):
        self.nodes[node.node_id] = node
        self.buses.add(node.bus_id)

    def add_branch(self, branch: NetworkGraphBranch):
        self.branches.append(branch)
        self.buses.add(branch.from_bus)
        self.buses.add(branch.to_bus)

    def get_metered_nodes(self) -> list[ConsumerUnitNode]:
        return [n for n in self.nodes.values() if n.is_metered]

    def get_unmetered_nodes(self) -> list[ConsumerUnitNode]:
        return [n for n in self.nodes.values() if not n.is_metered]

    def total_metered_power_kw(self) -> float:
        return float(sum(n.measured_kw for n in self.nodes.values() if n.is_metered))

    def compute_equivalent_impedance(self) -> tuple[float, float, float]:
        if not self.branches:
            return 0.1, 0.05, float(np.sqrt(0.1**2 + 0.05**2))

        total_r = sum(b.r1_ohm_per_km * b.length_km for b in self.branches)
        total_x = sum(b.x1_ohm_per_km * b.length_km for b in self.branches)

        r_eq = float(total_r / max(1, len(self.branches)**0.5))
        x_eq = float(total_x / max(1, len(self.branches)**0.5))
        z_mag = float(np.sqrt(r_eq**2 + x_eq**2))

        return round(r_eq, 4), round(x_eq, 4), round(z_mag, 4)
