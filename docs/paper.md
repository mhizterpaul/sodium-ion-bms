# NFPP Sodium-Ion BESS Performance Benchmarking and Latent Distribution Network State Estimation Using Network Realization Signatures

## Methodology

Base Cell Model (Literature-Aligned NFPP Sodium-Ion Twin System)
1. Electrochemical Core (DFN-Compatible Reaction)
The sodium iron pyrophosphate (NFPP) cathode operates via reversible sodium intercalation:
Na₂FePO₄P₂O₇ ⇌ NaₓFePO₄P₂O₇ + (2 − x)Na⁺ + (2 − x)e⁻
Theoretical specific capacity: ~95–100 mAh g⁻¹, consistent with reported polyanionic NFPP sodium-ion cathode systems used in pouch-scale prototypes.
2. Cathode Electrode Architecture (Composite Design)
NFPP cathodes in practical sodium-ion full cells follow a carbon–binder–domain composite structure processed using N-methyl-2-pyrrolidone (NMP)-based slurry casting.
Fixed composition:
	Sodium iron pyrophosphate (NFPP) active material: 85 wt% 
	Conductive carbon additive (carbon black / acetylene black): 8 wt% 
	Binder: polyvinylidene fluoride (PVDF): 7 wt% 
This structure reflects standard aluminum current collector-based cathodes used in sodium-ion pouch cells with high-density electrode compaction.
3. Anode Design (Hard Carbon System)
Hard carbon anodes are implemented as disordered carbon networks with nanopore and turbostratic domains enabling sodium storage through adsorption, intercalation, and pore filling mechanisms.
Fixed formulation:
	Hard carbon active material: 88 wt% 
	Conductive carbon additive: 6 wt% 
	Binder: polyvinylidene fluoride (PVDF): 6 wt% 
Practical specific capacity: 250–300 mAh g⁻¹, consistent with full-cell hard carbon sodium storage behavior.
4. Electrolyte System (Carbonate-Based Sodium Salt System)
The electrolyte follows a standard sodium-ion full-cell carbonate formulation:
	Sodium hexafluorophosphate (NaPF₆): 1.0 molar concentration 
	Sodium difluoro(oxalato)borate (NaDFOB): 0.2 molar concentration 
	Solvent system: ethylene carbonate and propylene carbonate in 1:1 volumetric ratio 
	Ionic conductivity: ~10 mS cm⁻¹ at 25°C 
5. Electrolyte Additive System (Interphase Engineering)
Interfacial stability is controlled using electrolyte additives that regulate both solid electrolyte interphase and cathode electrolyte interphase formation:
	Fluoroethylene carbonate (FEC): 3 wt%
→ promotes stable solid electrolyte interphase (SEI) formation on the hard carbon anode 
	Vinylene carbonate (VC): 2 wt%
→ enhances SEI uniformity and suppresses continuous electrolyte decomposition 
	Sodium difluoro(oxalato)borate (NaDFOB): functions as both co-salt and cathode electrolyte interphase (CEI) stabilizer 
The SEI is a passivation layer formed on the anode that regulates sodium-ion transport and prevents continuous electrolyte decomposition, while the CEI stabilizes cathode surface reactions and mitigates structural degradation.
6. Pouch Cell Mechanical Architecture (Stacked Design)
The full cell follows a stacked pouch configuration consistent with sodium-ion prototype manufacturing systems:
	Form factor: stacked Z-fold pouch cell architecture 
	Nominal voltage: 3.0–3.2 volts 
	Target capacity class: 10 ampere-hour design point 
Layer stack:
	Cathode current collector: aluminum foil (~15 micrometers) 
	Anode current collector: copper foil (~10 micrometers) 
	Separator: polyolefin trilayer membrane (~20 micrometers) 
	External casing: poly-based moisture barrier (no aluminum laminate)
	Inner sealant: polypropylene-based sealing layer 

#### **Design Space:**
   
*   **Structural Parameters ($\theta_s$):** Electrode thickness ($L_c, L_a$), porosity ($\epsilon_c, \epsilon_a, \epsilon_{sep}$), tortuosity ($\tau$), active material loading and particle size ($r_p$).
*   **Material Parameters ($\theta_m$):** NFPP fraction, conductive carbon fraction, and electrolyte composition (concentration/salts)

#### **Layered Material Mapping**

This phase resolves performance properties for chemistry modifications using a decoupled architecture: a **Material Mapping Engine** for data resolution and a **Physics Layer** for property-to-parameter transformation.

*   **Decoupled Mapping Engine:** The framework implements a prioritized resolution flow (OQMD Exact $\rightarrow$ MP Exact $\rightarrow$ Class Baselines) for a fixed candidate space (Mn/Cr/Ni dopants, NaBOB/NaTCP salts, MTMS functionalization). Strict stability-sorting ensures ground-state accuracy.
*   **Physics Channel Models:** Performance deltas are derived through channel-specific physics models: Nernstian proxies for voltage shifts ($ΔV \propto -ΔE_f$), exponential thermal activation mapping for conductivity ($\sigma \propto \exp(-E_g/2kT)$), and interphase kinetic models for SEI growth, all scaled by a bounded stability realization factor.
*   **Electrolyte & Fluorine Reduction:** Selection of non-fluorinated salts to reduce environmental burden and cost. Primary candidates include **NaBOB** (Sodium bis(oxalato)borate) for stability and **NaTCP** (Sodium tricyanomethanide) for high performance.
*   **Electrode Doping:** Fe-site doping for cathodes using **Cr** (Cr³⁺ stabilizer), **Mn** (voltage booster), and **Ni** is evaluated via sensitivity-based optimization.
*   **Alkyl Silane Functionalization:** Implementation of hard carbon electrode functionalization using **methyltrimethoxysilane (MTMS)**. This process replaces surface –OH groups with –Si–O–R groups on the hard carbon electrode, increasing hydrophobicity and promoting a more uniform SEI layer. The model accounts for reduced SEI kinetics (slower growth and lower irreversible capacity fade), slower interfacial resistance growth over cycles, and optimized exchange current density resulting from improved surface wetting and local ion accessibility.
*   Sensitivity-Driven Cell Parameter Optimization 
The projected design space ($\theta = [\theta_s, \theta_m]$) is explored with a hierarchical workflow that combines sensitivity screening, objective-specific SG-CEM refinement, and expensive stability filtering. In the implementation, the design vector is first perturbed around a nominal point to estimate the Jacobian of the energy, power, and stability responses; only the most influential variables for each objective are retained for optimization instead of searching the full design space at once.

#### BESS Robustness Evaluation Framework


1. Electrochemical–Thermal Driver Model



The BESS is evaluated using the DFN electrochemical model coupled with the lumped thermal model. The model provides the measurable simulation outputs required for performance evaluation:

Terminal voltage, \(V(t)\)

Terminal current, \(I(t)\)

Temperature, \(T(t)\)

State of charge, \(SoC(t)\)

Available capacity, \(Q(t)\)

Energy throughput


The BESS is evaluated under simulated grid-outage, PV-firming, and variable C-rate dispatch profiles.

2. Performance Measurements



Each performance metric is calculated directly from the simulated measurements.

Round-Trip Energy Efficiency (RTE)

Measures the fraction of charging energy recovered during discharge:

\[
\eta_{RTE}
=
\frac{E_{\mathrm{dis}}}{E_{\mathrm{chg}}}
\]

where

\[
E_{\mathrm{dis}}
=
\int_{\mathrm{discharge}} V(t)I(t)\,dt
\]

and

\[
E_{\mathrm{chg}}
=
\int_{\mathrm{charge}} |V(t)I(t)|\,dt.
\]

Coulombic Efficiency

Measures the fraction of charge recovered in terms of electrical charge:

\[
\eta_C
=
\frac{Q_{\mathrm{dis}}}{Q_{\mathrm{chg}}}
\]

with

\[
Q_{\mathrm{dis}}
=
\int_{\mathrm{discharge}} |I(t)|\,dt,
\qquad
Q_{\mathrm{chg}}
=
\int_{\mathrm{charge}} |I(t)|\,dt.
\]

Voltage Efficiency

Represents the voltage-related loss independently of charge throughput:

\[
\eta_V
=
\frac{\eta_{RTE}}{\eta_C}.
\]

Usable Energy Capacity

Measures the energy delivered over the defined operating SOC window:

\[
E_{\mathrm{usable}}
=
\int_{t_0}^{t_1}|V(t)I(t)|\,dt
\]

where \(t_0\) and \(t_1\) correspond to the specified upper and lower SOC limits.

Power Capability

Measures the maximum deliverable electrical power during the simulated operating window:

\[
P_{\max}
=
\max_t |V(t)I(t)|.
\]

Thermal Response

Measures the temperature excursion produced during operation:

\[
\Delta T
=
T_{\max}-T_{\min}
\]

and the maximum operating temperature is

\[
T_{\max}=\max_t T(t).
\]

State of Charge

The instantaneous stored-energy state is represented as:

\[
SoC(t)
=
\frac{Q(t)}{Q_{\max}}\times100\%.
\]

State of Health

Capacity-based degradation is represented as:

\[
SoH(t)
=
\frac{Q_{\max}(t)}
{Q_{\max}(0)}
\times100\%.
\]

Depth of Discharge

For each simulated cycle:

\[
DoD
=
SoC_{\max}-SoC_{\min}.
\]

Equivalent Full Cycles

Accumulated energy throughput is converted into equivalent full cycles:

\[
EFC
=
\frac{\displaystyle\int |P(t)|\,dt}
{2E_{\mathrm{rated}}}.
\]

The factor of \(2\) accounts for one complete charge and discharge throughput.

Capacity Fade

The loss of usable capacity relative to the initial condition is:

\[
F_Q(t)
=
1-
\frac{Q_{\max}(t)}
{Q_{\max}(0)}.
\]

Cycle Life

Cycle life is estimated from the simulated degradation trajectory as the point at which the battery reaches the prescribed minimum \(SoH\):

\[
N_{\mathrm{life}}
=
\min
\left\{
N:
SoH(N)\le SoH_{\mathrm{limit}}
\right\}.
\]

Calendar Life

Where calendar-aging simulations are performed, the corresponding lifetime is:

\[
t_{\mathrm{life}}
=
\min
\left\{
t:
SoH(t)\le SoH_{\mathrm{limit}}
\right\}.
\]

Levelized Cost of Storage

For the economic assessment:

\[
LCOS
=
\frac{C_{\mathrm{capital}}+
C_{\mathrm{replacement}}+
C_{\mathrm{operation}}}
{E_{\mathrm{lifetime,dis}}}
\]

where \(E_{\mathrm{lifetime,dis}}\) is the cumulative simulated energy delivered by the BESS.

---

*   **Limitations**:  While this work focuses on a foundational design space, the cell architecture remains amenable to further performance enhancement via composite electrode structuring, advanced pore network engineering, perturbing other dopant sites (beyond the Fe-site), and exploring a broader range of electrolyte systems (solvents and additives) to further enhance cycle life and energy density. The current optimization scope is intentionally streamlined to accommodate the computational constraints of the DFN solver.
  

---
### Distributed Dynamic State Estimation Using Lantent Network Realization Signatures (core contribution)

Unlike conventional Distribution System State Estimation (DSSE), where the complete network topology and bus model are assumed known, this research considers a partially observable network in which only the upstream distribution station is known while the downstream network remains hidden.

The realization problem is formulated as

[
X_R=\Phi(M)
]

where

* (M) denotes synchronized measurements acquired at feeders and distribution transformers,
* (X_R) is a latent realization state describing the hidden network,
* The aim is to derive (\Phi(\cdot)) realization operator, empirically from simulated operating scenarios.

The emphasis is therefore on discovering which hidden network properties are electrically observable at the distribution station interface and how these observables evolve under changing operating conditions.

---

#### 2. System Model

## Known Plant for Latent Network Realization

The upstream distribution station is completely known and serves as the boundary for observing downstream states.

It consists of:

```text
        Utility Source (Swing Bus)

                  │

      Distribution Substation Transformer

                  │

        Main Distribution Bus ── Generator

                  │
      ┌───────────┼───────────┐
      │           │           │

   Feeder 1    Feeder 2    Feeder 3
      │           │           │

Distribution  Distribution  Distribution
Transformer   Transformer   Transformer
      │           │           │

 Unknown LV   Unknown LV   Unknown LV
 Distribution Distribution Distribution
  Networks     Networks     Networks
```

The plant model contains strictly distribution network elements and local sources to facilitate Latent Network Realization:

* **Utility Source (Swing Bus)**: Represents the steady connection to the transmission grid.

* **Distribution Substation Transformer**: Substation transformer supplying the medium-voltage bus.

* **Three Outgoing Feeders**: Radial lines extending from the substation, each characterized by known feeder lengths and impedances.

* **Fixed Set of Transformers**: Step-down distribution transformers whose primary-side terminals serve as the boundary measurement interfaces.

* **Measurement and Monitoring Devices**: Electrical sensors capturing voltage, current, active/reactive power, and sequence components at each feeder head and transformer primary terminal.

---

#### 3. Measurement Architecture

Measurements are obtained from two sensing layers: feeder monitoring and transformer edge monitoring.

**A. Feeder Measurements**

Each outgoing feeder is instrumented to acquire

##### Electrical Quantities

* Three-phase voltage magnitude and phase angle
* Three-phase current magnitude and phase angle
* Active power ((P))
* Reactive power ((Q))
* Apparent power ((S))
* Power factor

##### Network Quality Metrics

* Frequency
* Rate of Change of Frequency (ROCOF)
* Voltage unbalance
* Current unbalance
* Positive-, negative-, and zero-sequence components

##### Dynamic Measurements

Where transient simulation is available

* Harmonic distortion (THD)
* Voltage waveform samples
* Current waveform samples
* Switching event timestamps

---

**B. Transformer Measurements**

Each distribution transformer serves as an edge measurement node representing the interface to an unknown downstream network.

Measurements include

##### Primary Electrical Measurements

* High-voltage terminal voltage magnitude and phase angle
* High-voltage terminal current magnitude and phase angle
* Active power
* Reactive power
* Apparent power
* Power factor

##### Dynamic Quantities

Where supported

* Loading rate
* Overload duration
* Load recovery characteristics
* Transformer temperature 
* Transient voltage and current waveforms

---

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

**4. Distribution Network Simulation And Station Modeling**

The simulation framework systematically perturbs the unknown downstream network while maintaining a fixed upstream distribution station.

OpenDSS is used to model the distribution station and downstream distribution network.

It provides

* Three-phase power flow
* Quasi-static time-series simulation
* Distribution feeder modelling
* Distribution transformer modelling
* Voltage regulator operation
* Capacitor bank switching
* Load switching
* Protection device modelling
* Python integration for automated simulation studies

---

A transient simulator, was used to reproduce waveform responses associated with

* Transformer energization
* Capacitor switching
* Motor starting
* Feeder switching
* Temporary faults

These simulations complement the steady-state information obtained from OpenDSS.

The perturbation process modifies hidden network characteristics including

* Number of downstream buses
* Network connectivity
* Distribution line parameters
* Load allocation
* Load composition
* Load switching sequences
* Motor penetration
* Capacitor placement
* Transformer loading


Each perturbed network is simulated under a range of operating conditions to generate synchronized feeder and transformer measurements.

The simulation produces a comprehensive dataset relating hidden network perturbations to observable boundary measurements for subsequent realization and distributed dynamic state estimation.

---

The synchronized measurements are transformed into physics-informed features that are expected to generalize across operating conditions

---

**6. Validation**

Validation focuses on answering the following research questions.

1. **Hidden Network Observability**

   Which structural and operational characteristics of the hidden downstream network are observable from synchronized feeder and transformer measurements?

2. **Network Complexity**

   As the hidden network size increases (e.g., increasing numbers of downstream buses), how does the observability and estimation accuracy of the realization algorithm change?

3. **Measurement Sufficiency**

   What combination of feeder and transformer measurements provides sufficient information for accurate distributed dynamic state estimation?

4. **Sensitivity to Hidden Network Perturbations**

   Which classes of downstream perturbations—including topology changes, load redistribution, switching events, transformer loading, and line parameter variations—produce measurable changes at the distribution station boundary?

The validation establishes the practical limits of boundary-based realization and identifies the sensing architecture required for distributed dynamic state estimation in partially observable distribution networks.
