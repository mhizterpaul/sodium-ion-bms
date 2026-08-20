# Known LV Line Parameters Specification - LV Network 3

## Known Conductor & Line Physical Specifications
- **Conductor Type**: 150 mm² All-Aluminum Conductor (AAC) / 3-phase 4-wire overhead
- **Current Ampacity / Thermal Limit**: 350 A per phase (capable of supporting peak consumer loads)
- **Positive-Sequence Series Resistance ($r_1$)**: 0.21 $\Omega$/km
- **Positive-Sequence Series Reactance ($x_1$)**: 0.08 $\Omega$/km
- **Shunt Conductance ($g_1$)**: $1.0 \times 10^{-6}$ S/km
- **Shunt Susceptance ($b_1$)**: $1.0 \times 10^{-6}$ S/km
- **Zero-Sequence Series Resistance ($r_0$)**: 0.63 $\Omega$/km
- **Zero-Sequence Series Reactance ($x_0$)**: 0.24 $\Omega$/km
- **Nominal Operating Frequency**: 50 Hz

## Known Network Line Segment Inventory
Lines `down_3_1` through `down_3_29` connect known buses `feeder3_sec`, `f3_node1` ... `f3_node29` with specified lengths (0.05 to 0.10 km) capable of supporting peak consumer loads under 350 A thermal rating per phase.
