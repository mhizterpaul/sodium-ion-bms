# Known LV Line Parameters Specification - LV Network 1

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
| Line ID | From Bus | To Bus | Length ($L_l$) | $R_l = r_1 L_l$ ($\Omega$) | $X_l = x_1 L_l$ ($\Omega$) | Thermal Rating |
|---|---|---|---|---|---|---|
| `down_1_1` | `feeder1_sec` | `f1_node1` | 0.05 km | 0.0105 $\Omega$ | 0.0040 $\Omega$ | 350 A |
| `down_1_2` | `feeder1_sec` | `f1_node2` | 0.06 km | 0.0126 $\Omega$ | 0.0048 $\Omega$ | 350 A |
| `down_1_3` | `f1_node1` | `f1_node3` | 0.07 km | 0.0147 $\Omega$ | 0.0056 $\Omega$ | 350 A |
| `down_1_4` | `f1_node1` | `f1_node4` | 0.08 km | 0.0168 $\Omega$ | 0.0064 $\Omega$ | 350 A |
| `down_1_5` | `f1_node2` | `f1_node5` | 0.05 km | 0.0105 $\Omega$ | 0.0040 $\Omega$ | 350 A |
| `down_1_6` | `f1_node2` | `f1_node6` | 0.06 km | 0.0126 $\Omega$ | 0.0048 $\Omega$ | 350 A |
| `down_1_7` | `f1_node3` | `f1_node7` | 0.07 km | 0.0147 $\Omega$ | 0.0056 $\Omega$ | 350 A |
| `down_1_8` | `f1_node3` | `f1_node8` | 0.08 km | 0.0168 $\Omega$ | 0.0064 $\Omega$ | 350 A |
| `down_1_9` | `f1_node4` | `f1_node9` | 0.05 km | 0.0105 $\Omega$ | 0.0040 $\Omega$ | 350 A |
| `down_1_10` | `f1_node4` | `f1_node10` | 0.06 km | 0.0126 $\Omega$ | 0.0048 $\Omega$ | 350 A |
| `down_1_11` | `f1_node5` | `f1_node11` | 0.07 km | 0.0147 $\Omega$ | 0.0056 $\Omega$ | 350 A |
| `down_1_12` | `f1_node5` | `f1_node12` | 0.08 km | 0.0168 $\Omega$ | 0.0064 $\Omega$ | 350 A |
| `down_1_13` | `f1_node6` | `f1_node13` | 0.05 km | 0.0105 $\Omega$ | 0.0040 $\Omega$ | 350 A |
| `down_1_14` | `f1_node6` | `f1_node14` | 0.06 km | 0.0126 $\Omega$ | 0.0048 $\Omega$ | 350 A |
| `down_1_15` | `f1_node7` | `f1_node15` | 0.07 km | 0.0147 $\Omega$ | 0.0056 $\Omega$ | 350 A |
| `down_1_16` | `f1_node7` | `f1_node16` | 0.08 km | 0.0168 $\Omega$ | 0.0064 $\Omega$ | 350 A |
| `down_1_17` | `f1_node8` | `f1_node17` | 0.05 km | 0.0105 $\Omega$ | 0.0040 $\Omega$ | 350 A |
| `down_1_18` | `f1_node8` | `f1_node18` | 0.06 km | 0.0126 $\Omega$ | 0.0048 $\Omega$ | 350 A |
| `down_1_19` | `f1_node9` | `f1_node19` | 0.07 km | 0.0147 $\Omega$ | 0.0056 $\Omega$ | 350 A |
