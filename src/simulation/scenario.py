from dataclasses import dataclass
from src.transient.events import TransientEvent

@dataclass
class HiddenNetworkScenario:
    scenario_id: str
    num_buses: int
    num_lines: int
    topology: dict
    line_parameters: dict
    loads: dict
    load_composition: dict
    motor_penetration: float
    capacitor_configuration: dict
    transformer_loading: dict
    switching_events: list

@dataclass
class SimulationScenario:
    hidden_network: HiddenNetworkScenario
    generator_p_kw: float
    generator_q_kvar: float
    events: list[TransientEvent]
