from opendssdirect import dss
from src.power_plant.sources import configure_generator

def initialize_known_plant():
    """
    Initializes the fixed upstream distribution station using OpenDSS.
    The known plant has standard distribution voltage levels:
    - Utility Grid Source (33 kV)
    - Injection Substation Transformer (33 kV to 11 kV, 7.5 MVA)
    - Main Distribution Bus / PCC (11 kV)
    - PCU / Shared Generator (coupled at 11 kV main_bus)
    - Medium-voltage Switchgear
    - Three 11 kV Feeders (Line 1, Line 2, Line 3)
    - Fixed set of three 11/0.415 kV step-down Distribution Transformers (1.5 MVA) acting as edge interfaces
    """
    print("INFO: Initializing OpenDSS Physics-Based Known Plant Model (33/11/0.415 kV)...")

    # 1. Clear previous systems and define main circuit at swing bus (33 kV)
    dss.Basic.ClearAll()
    dss.run_command("new circuit.FixedPlant basekv=33.0 pu=1.0 phases=3")

    # 2. Substation Transformer (33 kV to 11 kV, delta-wye, 7.5 MVA)
    # Rwdg=0.6%, X=8.33% from spec sheet in paper.md
    dss.run_command(
        "new transformer.substation "
        "phases=3 windings=2 "
        "buses=[sourcebus, main_bus] "
        "conns=[delta, wye] "
        "kvs=[33.0, 11.0] "
        "kvas=[7500, 7500] "
        "%r=0.6 xhl=8.33"
    )

    # 3. Configure Controllable Shared Generator (coupled at 11 kV main_bus)
    configure_generator(p_kw=1500.0, q_kvar=0.0)

    # 4. Outgoing radial 11 kV Feeders (Line 1, Line 2, Line 3)
    # Standard 11 kV line parameters
    dss.run_command("new linecode.feeder nphases=3 r1=0.25 x1=0.35 r0=0.75 x0=1.12 c1=12.0 c0=6.0 units=km")

    # Feeders extending from main_bus to the respective 11 kV feeder head buses
    # Feeder lengths: feeder1=4.5km, feeder2=6.2km, feeder3=8.5km
    dss.run_command("new line.feeder1 bus1=main_bus bus2=feeder1_head phases=3 linecode=feeder length=4.5 units=km")
    dss.run_command("new line.feeder2 bus1=main_bus bus2=feeder2_head phases=3 linecode=feeder length=6.2 units=km")
    dss.run_command("new line.feeder3 bus1=main_bus bus2=feeder3_head phases=3 linecode=feeder length=8.5 units=km")

    # 5. Fixed Set of Distribution Transformers (11/0.415 kV, delta-wye, 1.5 MVA)
    # Secondary side is 0.415 kV (LV) which connects to the unknown downstream networks
    dss.run_command("new transformer.trans1 phases=3 windings=2 buses=[feeder1_head, feeder1_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans2 phases=3 windings=2 buses=[feeder2_head, feeder2_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans3 phases=3 windings=2 buses=[feeder3_head, feeder3_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")

    print("INFO: OpenDSS Known Plant Model successfully initialized.")
