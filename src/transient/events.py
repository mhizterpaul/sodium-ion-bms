from dataclasses import dataclass
from typing import Literal

@dataclass
class TransientEvent:
    event_type: Literal[
        "transformer_inrush",
        "capacitor_switching",
        "motor_start",
        "feeder_switching",
        "temporary_fault",
    ]
    start_time_s: float
    duration_s: float
    target: str
    parameters: dict
