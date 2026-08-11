from dataclasses import dataclass
from typing import Optional
from src.transient.events import TransientEvent

@dataclass
class EMTEvent:
    event_id: str
    event_type: str
    start_time_s: float
    duration_s: Optional[float]
    target_element: Optional[str]
    target_bus: Optional[str]
    phase_mask: Optional[tuple[bool, bool, bool]]
    parameters: dict

@dataclass
class NetworkRealization:
    realization_id: str
    buses: list[str]
    lines: list[dict]
    transformers: list[dict]
    loads: list[dict]
    capacitors: list[dict]
    motors: list[dict]
    ders: list[dict]
    source: dict
    metered_pccs: list[dict]
    hidden_state: dict
    channel_map: dict

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
    events: list[EMTEvent]
    meter_fraction: float = 0.5
    seed: int = 42

    def __post_init__(self):
        if not (0.0 < self.meter_fraction <= 1.0):
            raise ValueError(f"meter_fraction must be in (0.0, 1.0], got {self.meter_fraction}")
