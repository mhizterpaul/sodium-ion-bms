#### Primary Distribution Transformer Specification (ATP-EMTP Model)

##### General Characteristics

| Parameter         | Value                    | Notes                                          |
| ----------------- | ------------------------ | ---------------------------------------------- |
| Transformer Type  | Three-phase, Two-winding | Injection Substation Transformer               |
| Rated Power       | **7.5 MVA**              | Typical Nigerian urban distribution substation |
| Rated Frequency   | **50 Hz**                | Nigerian grid frequency                        |
| Primary Voltage   | **33 kV (L-L)**          | HV winding                                     |
| Secondary Voltage | **11 kV (L-L)**          | LV feeder bus                                  |
| Number of Phases  | 3                        | Balanced three-phase                           |
| Cooling           | ONAN                     | Oil Natural Air Natural                        |
| Vector Group      | Dyn11                    | Δ/Yg configuration                             |
| Neutral Grounding | Solidly grounded (LV)    | Earth fault protection                         |
| Core Type         | Three-limb CRGO          | Cold Rolled Grain Oriented Steel               |
| Standard          | IEC 60076                | Nigerian utility practice                      |

---

##### Rated Electrical Quantities

| Parameter               | Value        |
| ----------------------- | ------------ |
| Rated Apparent Power    | 7.5 MVA      |
| Rated Power Factor      | 0.95 lagging |
| Rated Primary Current   | **131.2 A**  |
| Rated Secondary Current | **393.6 A**  |
| Frequency               | 50 Hz        |


---

##### Operating Loading

| Quantity         | Value    |
| ---------------- | -------- |
| Peak Active Load | 5.6 MW   |
| Reactive Load    | 2.1 MVAr |
| Apparent Load    | 6.0 MVA  |
| Loading          | 80%      |

---

##### Voltage Regulation

| Parameter         | Value    |
| ----------------- | -------- |
| No-load Voltage   | 11.15 kV |
| Full-load Voltage | 11.00 kV |
| Regulation        | 1.36 %   |

---

##### Tap Changer

| Parameter           | Value  |
| ------------------- | ------ |
| Type                | OLTC   |
| Range               | ±7.5 % |
| Step Size           | 2.5 %  |
| Number of Positions | 7      |
| Nominal Position    | 0      |

---

##### Winding Parameters

| Parameter          | HV       | LV                       |
| ------------------ | -------- | ------------------------ |
| Connection         | Delta    | Grounded Wye             |
| Rated Voltage      | 33 kV    | 11 kV                    |
| Turns Ratio        | 3 : 1    | —                        |
| Winding Resistance | 0.006 pu | Included in equivalent R |

---

##### Losses

###### Copper Loss

| Parameter                | Value |
| ------------------------ | ----- |
| Full-load Copper Loss    | 50 kW |
| Copper Loss @80% Loading | 32 kW |

###### Core Loss

| Parameter    | Value  |
| ------------ | ------ |
| No-load Loss | 7.5 kW |

###### Total Loss

| Parameter               | Value   |
| ----------------------- | ------- |
| Total Loss @80% Loading | 39.5 kW |
| Efficiency              | 99.35 % |

---

##### Leakage Impedance

| Parameter            | Value  |
| -------------------- | ------ |
| Percentage Impedance | 8.35 % |
| Resistance           | 0.60 % |
| Leakage Reactance    | 8.33 % |
| X/R Ratio            | 13.9   |


##### Sequence Impedances (per-unit)

| Sequence | Resistance | Reactance |
| -------- | ---------- | --------- |
| Positive | 0.0060     | 0.0833    |
| Negative | 0.0060     | 0.0833    |
| Zero     | 0.0120     | 0.0450    |

---

##### Magnetizing Branch

| Parameter             | Value  |
| --------------------- | ------ |
| Excitation Current    | 0.8 %  |
| Magnetizing Reactance | 250 pu |
| Core-loss Resistance  | 800 pu |

---

##### Short-Circuit Characteristics

| Parameter                   | Value                    |
| --------------------------- | ------------------------ |
| Short-circuit Voltage       | 8.35 %                   |
| Rated Short-circuit Current | 12 × Rated Current (1 s) |
| Thermal Limit               | IEC 60076                |

---

##### Saturation Characteristics (Required for ATP-EMTP Saturable Transformer)

| Flux (pu) | Magnetizing Current (pu) |
| --------- | ------------------------ |
| 0.0       | 0.000                    |
| 0.8       | 0.002                    |
| 1.0       | 0.008                    |
| 1.1       | 0.015                    |
| 1.2       | 0.050                    |
| 1.3       | 0.180                    |
| 1.4       | 0.420                    |
| 1.5       | 0.900                    |

This nonlinear magnetization curve enables ATP-EMTP to simulate inrush currents, ferroresonance, and saturation effects more accurately than a linear magnetizing branch.

---

##### BCTRAN Equivalent Parameters

| Quantity                    | Value              |
| --------------------------- | ------------------ |
| Base Power                  | 7.5 MVA            |
| Base Frequency              | 50 Hz              |
| Positive Sequence Impedance | 0.006 + j0.0833 pu |
| Zero Sequence Impedance     | 0.012 + j0.045 pu  |
| Magnetizing Reactance       | 250 pu             |
| Core-loss Resistance        | 800 pu             |
| Winding Connections         | Δ/Yg               |
| Tap Position                | 0                  |

---
