# LV Network Specification - LV Feeder 2 Topology

## Network Topology & Bus Structure
- **Network ID**: `LV2`
- **Topology Type**: Known Radial Tree
- **Nominal LV Voltage**: 415 V (Line-to-Line RMS) / 240 V (Line-to-Neutral)
- **Base Frequency**: 50 Hz
- **Phase Configuration**: 3-Phase 4-Wire (ABC-N)
- **Number of Buses ($N_b$)**: 25 (Fixed & Known)
- **Number of Branches ($N_l$)**: 24 (Fixed & Known)
- **Transformer Secondary Interface Bus**: `feeder2_sec`
- **Buses ($\mathcal{B}$)**: [`feeder2_sec`, `f2_node1` ... `f2_node24`]
- **Conductor & Line Capability**:
  - **Conductor Specification**: 150 mm² All-Aluminum Conductor (AAC) / 3-phase 4-wire overhead line
  - **Thermal Rating / Ampacity**: 350 A per phase (capable of supporting peak total consumer demand > 300 kW)
  - **Series Resistance ($r$)**: 0.21 $\Omega$/km
  - **Series Reactance ($x$)**: 0.08 $\Omega$/km
  - **Positive-Sequence Impedance ($Z_1$)**: $0.21 + j0.08\ \Omega$/km
  - **Zero-Sequence Impedance ($Z_0$)**: $0.63 + j0.24\ \Omega$/km
- **Consumer Load Placements ($\mathcal{C}$)**: Fixed known locations across buses with specified nominal equipment models (`dc_motor_inverter`, `audio_amplifier`, `industrial_fan`, `compressor`).
