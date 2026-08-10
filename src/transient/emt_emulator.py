from src.transient.atp_runner import ATPRunner
from src.transient.atp_parser import ATPOutputReader, EMTWaveforms

def run_atp_case(atp_case_path: str, metered_pccs: list[dict], event) -> EMTWaveforms:
    """
    Executes the ATP-EMTP simulation using the generated ATP case card and returns clean EMTWaveforms.
    This acts as a clean adapter to decouple the simulator execution from downstream waveform processing.
    """
    atp_result = ATPRunner().run(atp_case_path)
    return ATPOutputReader().read(atp_result, metered_pccs, event)
