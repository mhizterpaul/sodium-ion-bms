# Distribution System State Estimation Using Wavelet Decomposition with NFPP Sodium-Ion BESS Performance Evaluation

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
*   **Sensitivity-Driven Cell Parameter Optimization:** The projected design space ($\theta = [\theta_s, \theta_m]$) is explored with a hierarchical workflow that combines sensitivity screening, objective-specific SG-CEM refinement, and expensive stability filtering. In the implementation, the design vector is first perturbed around a nominal point to estimate the Jacobian of the energy, power, and stability responses; only the most influential variables for each objective are retained for optimization instead of searching the full design space at once.

#### BESS Robustness Evaluation Framework

The BESS is evaluated using the DFN electrochemical model coupled with the thermal model. The model provides the measurable simulation outputs required for performance evaluation including:
  Terminal voltage, \(V(t)\)
  Terminal current, \(I(t)\)
  Temperature, \(T(t)\)
  State of charge, \(SoC(t)\)
  Available capacity, \(Q(t)\)
  Energy throughput
The BESS is evaluated under simulated grid-outage, PV-firming, and variable C-rate dispatch profiles.

**Performance Measurements**
Each performance metric is calculated directly from the simulated measurements.

 * **Round-Trip Energy Efficiency (RTE)**: Measures the fraction of charging energy recovered during discharge
[\eta_{\mathrm{RTE}}=\frac{E_{\mathrm{dis}}}{E_{\mathrm{chg}}}] where
[E_{\mathrm{dis}}=\int_{\mathrm{discharge}} V(t)I(t)\,dt]
and [E_{\mathrm{chg}}=\int_{\mathrm{charge}} |V(t)I(t)|\,dt.]

 * **Coulombic Efficiency**: Measures the fraction of charge recovered in terms of electrical charge [\eta_C=\frac{Q_{\mathrm{dis}}}{Q_{\mathrm{chg}}}] with [Q_{\mathrm{dis}}=\int_{\mathrm{discharge}} |I(t)|\,dt,\qquad Q_{\mathrm{chg}}=\int_{\mathrm{charge}} |I(t)|\,dt.]

 * **Voltage Efficiency**: Represents the voltage-related loss independently of charge throughput [\eta_V=\frac{\eta_{\mathrm{RTE}}}{\eta_C}.]

 * **Usable Energy Capacity**: Measures the energy delivered over the defined operating SOC window [E_{\mathrm{usable}}=\int_{t_0}^{t_1}|V(t)I(t)|\,dt] where \(t_0\) and \(t_1\) correspond to the specified upper and lower SOC limits.

 * **Power Capability**: Measures the maximum deliverable electrical power during the simulated operating window [P_{\max}=\max_t |V(t)I(t)|.]

 * **Thermal Response**: Measures the temperature excursion produced during operation [\Delta T=T_{\max}-T_{\min}] and the maximum operating temperature is [T_{\max}=\max_t T(t).]

 * **Depth of Discharge**: For each simulated cycle [DoD=SoC_{\max}-SoC_{\min}.]

 * **Equivalent Full Cycles**: Accumulated energy throughput is converted into equivalent full cycles [EFC=\frac{\displaystyle\int |P(t)|\,dt}{2E_{\mathrm{rated}}}.]. The factor of \(2\) accounts for one complete charge and discharge throughput.

 * **Capacity Fade**: The loss of usable capacity relative to the initial condition is [F_Q(t)=1-\frac{Q_{\max}(t)}{Q_{\max}(0)}.]

 * **Cycle Life**: Cell life cycle is estimated from the simulated degradation trajectory as the point at which the battery reaches the prescribed minimum \(SoH\), [N_{\mathrm{life}}=\min\left\{N:SoH(N)\le SoH_{\mathrm{limit}}\right\}.]

 * **Calendar Life**: Where calendar-aging simulations are performed, the corresponding lifetime is:
[t_{\mathrm{life}}=\min\left\{t:SoH(t)\le SoH_{\mathrm{limit}}\right\}.]

 * **Levelized Cost of Storage**: For the economic assessment [LCOS=\frac{C_{\mathrm{capital}}+C_{\mathrm{replacement}}+C_{\mathrm{operation}}}{E_{\mathrm{lifetime,dis}}}]
where \(E_{\mathrm{lifetime,dis}}\) is the cumulative simulated energy delivered by the BESS.

**Limitations:**  While this work focuses on a foundational design space, the cell architecture remains amenable to further performance enhancement via composite electrode structuring, advanced pore network engineering, perturbing other dopant sites (beyond the Fe-site), and exploring a broader range of electrolyte systems (solvents and additives) to further enhance cycle life and energy density. The current optimization scope is intentionally streamlined to accommodate the computational constraints of the DFN solver.

---

## Distribution System State Estimation Using Wavelet Decomposition with Known LV Network Topology and Latent Line Parameter Estimation

In this research, the low-voltage (LV) distribution network topology and network structure are known. The research does not estimate or discover a hidden LV network topology. Instead, selected electrical parameters of known LV lines are latent, and the research estimates those latent line parameters from boundary and consumer measurements. Consumer loads are not latent as entities: their existence, type, and placement are known, but loads connected to latent line sections are electrically coupled to the latent line parameters and their load contribution is part of the estimation problem.

The latent line parameter estimation problem is formulated as:

[ X_L = \Phi(M; \mathcal{K}) ]

where:
- $M$ denotes synchronized measurements acquired at distribution transformer boundary meters and consumer meters;
- $\mathcal{K}$ represents the known network model containing:
  [ \mathcal{K} = \left[ \mathcal{T}_{LV}, \mathcal{B}, \mathcal{L}, \mathcal{C}, \mathcal{T}_{TX}, \mathcal{F}_{MV} \right] ]
  in which:
  - $\mathcal{T}_{LV}$: known LV network topology;
  - $\mathcal{B}$: known buses;
  - $\mathcal{L}$: known line set;
  - $\mathcal{C}$: known consumer-load definitions and locations;
  - $\mathcal{T}_{TX}$: known distribution transformer specifications;
  - $\mathcal{F}_{MV}$: known upstream medium-voltage feeder.
- $X_L$ is the latent line parameter vector:
  [ X_L = \left[ \mathbf{R}_L, \mathbf{X}_L, \mathbf{G}_L, \mathbf{B}_L, \mathbf{L}_{\mathrm{load}} \right] ]
  representing series resistance $\mathbf{R}_L$, series reactance $\mathbf{X}_L$, shunt conductance $\mathbf{G}_L$, shunt susceptance $\mathbf{B}_L$, and latent line-associated load electrical contributions $\mathbf{L}_{\mathrm{load}}$.
- $\Phi(\cdot)$ is the empirical estimation operator.

Detailed physical parameters for the upstream station, substation transformer, and LV networks are documented in `docs/specs/upstream_distribution_station.md`, `docs/specs/upstream_transformer.md`, and `docs/specs/lv1/*`, `docs/specs/lv2/*`, `docs/specs/lv3/*`.

### System Model

#### 1. Known Plant Model

The upstream distribution station and MV feeders are completely known and serve as the boundary for observing downstream LV network states.
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
 Known LV     Known LV     Known LV
 Distribution Distribution Distribution
  Network      Network      Network
```

The plant model contains strictly distribution network elements and local sources:

* **Utility Source (Swing Bus)**: Ideal infinite bus connection to the transmission grid (33 kV LL RMS, $Z_{\mathrm{src}} = 0$).
* **Distribution Substation Transformer**: Substation transformer supplying the 11 kV medium-voltage bus (7.5 MVA, 33/11 kV, Dyn11).
* **Main Feeders**: Radial 11 kV feeders extending from the substation, characterized by known lengths and sequence impedances ($Z_1 = 0.25 + j0.35\ \Omega/\mathrm{km}$).
* **Fixed Set of Transformers**: Step-down 11/0.415 kV distribution transformers (`trans1`, `trans2`, `trans3`).
* **Consumer Load Circuits**: Consumer equipment circuits implemented across OpenDSS and ATP-EMTP (`ac_motor`, `dc_motor_inverter`, `microwave`, `induction_plate`, `compressor`, `audio_amplifier`, `ups`, `industrial_fan`).

#### 2. Measurement Architecture

Measurements are obtained from two sensing layers: transformer edge boundary monitoring and consumer smart meters.

1. Consumer Smart-Meter Measurements

Selected candidate consumer nodes are instrumented with smart meters to acquire:
  Three-phase voltage magnitude and phase angle
  Three-phase current magnitude and phase angle
  Active power (P), Reactive power (Q), Apparent power (S), Power factor (PF)
  Positive-, negative-, and zero-sequence components

2. Transformer Boundary Measurements

Each distribution transformer secondary serves as an edge measurement node. Measurements include:
  Voltage and current magnitude and phase angle
  Active, reactive, and apparent power
  Transient voltage and current waveforms ($V_{abc}(t), I_{abc}(t)$)

#### 3. Simulation Framework

The LV network topology, bus connectivity, branch count, transformer location, and consumer-load placement are fixed and known. Experimental variability is introduced through the electrical parameters of designated latent LV line sections and through operating/event conditions. Events in Dataset 2, 3, and 4 originate from known LV lines.

The simulation framework generates four distinct, decoupled datasets:

1. **Dataset 1 (Latent Line Parameter Estimation Dataset)**: Focuses on steady-state latent line parameter estimation.
   - **Ground-Truth Target Variables ($X_L$):** `gt_scenario_id`, `gt_feeder_id`, `gt_topology_type`, `known_number_of_buses`, `known_number_of_branches`, `gt_r_eq_ohm`, `gt_x_eq_ohm`, `gt_z_eq_ohm`, `gt_g_eq_siemens`, `gt_b_eq_siemens`.
   - **Inverse Realization Estimates ($\hat{X}_L$):** `est_r_eq_ohm`, `est_x_eq_ohm`, `est_z_eq_ohm`, `est_g_eq_siemens`, `est_b_eq_siemens` derived by `LatentLineRealizationSolver`.
   - **Observation Features ($M$):** Three-phase steady-state time vector (`obs_steady_state_time`), voltage waveforms (`obs_steady_state_voltage_abc`), current waveforms (`obs_steady_state_current_abc`), along with boundary meter summary metrics.

2. **Dataset 2 (Question 1 Event Pair Observability Dataset)**: Evaluates event pair observability on known LV lines across (i) load switch pairs (`load_load`), (ii) line fault pairs (`fault_fault`), and (iii) mixed load switch and fault pairs (`load_fault`). Uses fixed baseline transformer specifications and zero time shift ($t_{\mathrm{offset}} = 0.0\ \mathrm{s}$).

3. **Dataset 3 (Question 2 Time Shift Operation Dataset)**: Evaluates residual magnitude variation under time shift operations ($t_{\mathrm{offset}} = 0.0\ \mathrm{s}$ vs $t_{\mathrm{offset}} > 0.0\ \mathrm{s}$) across event pairs on known LV lines.

4. **Dataset 4 (Question 3 Transformer Specification Dataset)**: Evaluates how transformer specification variations affect event pair observability across load switch pairs, line fault pairs, and mixed pairs on known LV lines.

#### 4. Statistical Testing

##### Dataset 1 Latent Parameter Estimation Accuracy Testing

Dataset 1 statistical analysis (`src/statistics/correlation.py`) evaluates the accuracy of `LatentLineRealizationSolver` in recovering latent line electrical parameters ($R_L, X_L, Z_L, G_L, B_L$) from boundary and consumer measurements across 3 feeder subgroups (`feeder_1`, `feeder_2`, `feeder_3`). Metrics evaluated include:
1. **Root Mean Squared Error (RMSE)** for continuous equivalent impedance estimation ($\hat{R}_{\mathrm{eq}}$, $\hat{X}_{\mathrm{eq}}$, $\hat{Z}_{\mathrm{eq}}$):
  \[\mathrm{RMSE}_{Z} = \sqrt{\frac{1}{N}\sum_{i=1}^N (\hat{Z}_{\mathrm{eq},i} - Z_{\mathrm{eq},i})^2}\]
2. **RMSE** for equivalent admittance estimation ($\hat{G}_{\mathrm{eq}}$, $\hat{B}_{\mathrm{eq}}$).

##### Dataset 2 Event Pair Observability Testing 

Factorial ANOVA analysis (`src/statistics/q1_event_pair_analysis.py`) evaluates event pair observability across pair categories (`load_load`, `fault_fault`, `load_fault`) using Dataset 2 under fixed baseline transformer specs and zero time shift.

##### Dataset 3 Time Shift Operation Variation Testing

Levene / Brown-Forsythe variance analysis (`src/statistics/q2_time_shift_analysis.py`) evaluates residual magnitude variation under time shift operations ($t_{\mathrm{offset}} = 0$ vs $t_{\mathrm{offset}} > 0$) using Dataset 3.

##### Dataset 4 Transformer Specification Effect Testing

One-Way ANOVA testing (`src/statistics/q3_transformer_spec_analysis.py`) evaluates how transformer specification variations affect observability across pair categories using Dataset 4.
