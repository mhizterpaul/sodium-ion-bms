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
    meter_fraction: float = 0.5
    seed: int = 42

    def __post_init__(self):
        if not (0.0 < self.meter_fraction <= 1.0):
            raise ValueError(f"meter_fraction must be in (0.0, 1.0], got {self.meter_fraction}")
