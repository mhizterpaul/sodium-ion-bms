# Advanced State Estimation and NFPP Sodium-Ion Energy Storage Evaluation for Distribution Networks

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
[eta_{RTE}=frac{E_{\mathrm{dis}}}{E_{\mathrm{chg}}}] whereb[E_{\mathrm{dis}}=int_{\mathrm{discharge}} V(t)I(t),dt]
and [E_{\mathrm{chg}}=\int_{\mathrm{charge}} |V(t)I(t)|\,dt.]

 * **Coulombic Efficiency**: Measures the fraction of charge recovered in terms of electrical charge [\eta_C=\frac{Q_{\mathrm{dis}}}{Q_{\mathrm{chg}}}] with [Q_{\mathrm{dis}}= int_{\mathrm{discharge}} |I(t)|\,dt,\qquad Q_{\mathrm{chg}}=\int_{\mathrm{charge}} |I(t)|\,dt.]

 * **Voltage Efficiency**: Represents the voltage-related loss independently of charge throughput [\eta_V=\frac{\eta_{RTE}}{\eta_C}.]

 * **Usable Energy Capacity**: Measures the energy delivered over the defined operating SOC window [E_{\mathrm{usable}}=\int_{t_0}^{t_1}|V(t)I(t)|\,dt] where \(t_0\) and \(t_1\) correspond to the specified upper and lower SOC limits.

 * **Power Capability**: Measures the maximum deliverable electrical power during the simulated operating window [P_{\max}=\max_t |V(t)I(t)|.]

 * **Thermal Response**: Measures the temperature excursion produced during operation [\Delta T=T_{\max}-T_{\min}] and the maximum operating temperature is[T_{\max}=\max_t T(t).]

 * **Depth of Discharge**: For each simulated cycle [DoD=SoC_{\max}-SoC_{\min}.]

 * **Equivalent Full Cycles**: Accumulated energy throughput is converted into equivalent full cycles [EFC=\frac{\displaystyle\int |P(t)|\,dt}{2E_{\mathrm{rated}}}.]. The factor of \(2\) accounts for one complete charge and discharge throughput.

 * **Capacity Fade**: The loss of usable capacity relative to the initial condition is [F_Q(t)=1-\frac{Q_{\max}(t)}{Q_{\max}(0)}.]

 * **Cycle Life**: cell life cycle is estimated from the simulated degradation trajectory as the point at which the battery reaches the prescribed minimum \(SoH\), [N_{\mathrm{life}}=\min\left\{N:SoH(N)\le SoH_{\mathrm{limit}}\right\}.]

 * **Calendar Life**: Where calendar-aging simulations are performed, the corresponding lifetime is:
[t_{\mathrm{life}}=\min\left\{t:SoH(t)\le SoH_{\mathrm{limit}}\right\}.]

 * **Levelized Cost of Storage**: For the economic assessment [LCOS=\frac{C_{\mathrm{capital}}+C_{\mathrm{replacement}}+C_{\mathrm{operation}}}{E_{\mathrm{lifetime,dis}}}\]
where \(E_{\mathrm{lifetime,dis}}\) is the cumulative simulated energy delivered by the BESS.

**Limitations:**  While this work focuses on a foundational design space, the cell architecture remains amenable to further performance enhancement via composite electrode structuring, advanced pore network engineering, perturbing other dopant sites (beyond the Fe-site), and exploring a broader range of electrolyte systems (solvents and additives) to further enhance cycle life and energy density. The current optimization scope is intentionally streamlined to accommodate the computational constraints of the DFN solver.

---

## Time-Adjusted Cluster Load Allocation with Error Correction in Sparsely Metered Distribution Networks (core contribution)

In a sparsely metered distribution system, the utility may know:
feeder/transformer energy supplied;
measurements from a relatively small subset of consumers;
some information about consumer premises;
historical consumption patterns/classes;
but does not know the actual consumption of every customer.
the  formulation is:
\[ E_U = E_T - E_M - E_L \]
where:
\(E_T\) = transformer/feeder energy,
\(E_M\) = measured customer energy,
\(E_L\) = estimated technical losses,
\(E_U\) = energy attributable to unknown/unmetered customers.
You can then estimate an expected consumption for each unmetered customer:
\[ w_i=\mathbb E[E_i\mid C_i,X_i] \]
where \(X_i\) could include:
customer class,
historical billing,
premises characteristics,
connected load,
time of year,
supply availability,
transformer loading,
feeder characteristics.
Then:
\[ \boxed{ \hat E_i = E_U \frac{w_i}{\sum_{j\in U}w_j} } \]
with time-adjusted consumer/load-class information.
Suppose consumer \(i\) belongs to class \(c\), with metered class profile
\[ \mu_c(t). \]
For an unmetered consumer, rather than assigning a static class average, estimate:
\[ \hat E_i = \int_{t_0}^{t_1} \alpha_i(t)\mu_{c_i}(t)\,dt \]
where \(\alpha_i(t)\) is your time adjustment factor for observed metered-class behaviour;
Let the actual feeder energy be
\[ E_F = E_L+E_{NTL}+E_T \]
where:
\(E_L\): legitimate consumer consumption;
\(E_{NTL}\): technical network losses;
\(E_T\): non-technical losses/theft.
Therefore the allocation error is:
\[ E_F-\hat E_L = \hat E_{loss}+\hat E_T. \]
we report the baseline CLA error and time adjusted CLA error, and derive transient-assisted CLA error correction factor

### System Model

#### 1. Known Plant for Latent Network Realization

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
     LV           LV          LV
 Distribution Distribution Distribution
  Networks     Networks     Networks
```

The plant model contains strictly distribution network elements and local sources to facilitate Latent Network Realization:

* **Utility Source (Swing Bus)**: Represents the steady connection to the transmission grid.
* **Distribution Substation Transformer**: Substation transformer supplying the medium-voltage bus.
* **Main Feeder**: with lines extending from the substation, each characterized by known feeder lengths and impedances.
* **Fixed Set of Transformers**: Step-down distribution transformers whose primary-side terminals serve as the boundary measurement interfaces.
* **Measurement and Monitoring Devices**: Electrical sensors capturing voltage, current, active/reactive power, and sequence components at the meters and transformer primary terminal.
* **Consumer Load Circuits**: To accurately represent realistic residential, commercial, and industrial end-user devices, consumer equipment circuits are implemented compatibly across OpenDSS and ATP-EMTP:
  1. **AC Motor (`ac_motor`)**: Three-phase induction motor with stator resistance/inductance, magnetizing branch, rotor resistance/inductance, and mechanical inertia.
  2. **DC Motor + Inverter (`dc_motor_inverter`)**: Rectifier stage, DC-link capacitor, PWM H-bridge inverter, and DC motor armature $R_a, L_a$ with speed-dependent Back-EMF.
  3. **Microwave (`microwave`)**: Input rectifier, PFC stage, DC-link capacitor, high-voltage transformer, diode voltage doubler, and magnetron non-linear load.
  4. **Induction Plate (`induction_plate`)**: Input rectifier, DC-link, high-frequency resonant inverter, resonant capacitor, and induction coil $R_{\mathrm{eq}} + j\omega L_{\mathrm{eq}}$.
  5. **Compressor (`compressor`)**: Single-phase AC induction motor driving reciprocating/scroll compressor load torque.
  6. **Audio Amplifier (`audio_amplifier`)**: AC supply rectifier, DC-link supply capacitor bank, Class-D switching H-bridge, LC output filter, and speaker impedance.
  7. **Uninterruptible Power Supply / UPS (`ups`)**: Battery bank equivalent circuit, DC-link, bidirectional converter, and AC-side filter interface.
  8. **Industrial Fan (`industrial_fan`)**: Three-phase induction motor driving speed-squared aerodynamic fan load torque.

#### 2. Measurement Architecture

Measurements are obtained from two sensing layers:  smart meters measurement at consumer and feeder edge and transformer edge transient analyzer.

1. Smart-Meter Measurements
The metering hierarchy is organized as follows:

```text
               Known MV feeder
                      │
                  Edge Meter
                      │
                ┌─────┴─────┐
                │Transformer│
                └─────┬─────┘
                      │
                      │
             ┌────────┴────────┐
             │                 │
            Smart              |
            Meter              |
             │                 │
           Consumer          Consumer
            Unit A            Unit B
                     
```

Selected candidate units are instrumented with smart meters to acquire:
  Active power (P)
  Reactive power (Q)
  Apparent power (S)
  Power factor (PF)
  Energy consumption (kWh)

2. Transformer Measurements
Each distribution transformer serves as an edge measurement node representing the interface to the downstream network. Measurements include:
Primary Electrical Measurements
  phase voltage magnitude and phase angle
  phase current magnitude and phase angle
  Active power
  Reactive power
  Apparent power
  Power factor

Dynamic Quantities
  Loading rate
  Transformer temperature
  Transient voltage and current waveforms

#### 3. Distribution Network Simulation

The simulation involves first assigning consumer load classes to consumer load circuits, the 3 lv trasnformer models have fixed varied specification, we take energy consumption from the metered consumer load circuits for time dt, we construct dataset 1 which include the assigned classes and the energy consumption of the metered group in the network, we compute baseline cla error and time adjusted cla error, considering non technical losses included in the model. we generated 3 datasets including consumer load circuit switch transient co-events under 3 network conditions, we analyse the observability of these events from which we compute the error correction factor of transformer transients based consumer load prediction on time adjusted cla error. The simulation is performed using OpenDSS and ATP-EMTP.

1. **Dataset 1**: ...

2. **Dataset 2**: Evaluates what type of event pairs are observable across load switch pairs (`load_load`), line fault pairs (`fault_fault`), and mixed load switch and fault pairs (`load_fault`).
   - **Ground-Truth Target Variables ($X_R$):** `gt_scenario_id`, `gt_transformer_id`, `gt_transformer_spec_id`, `gt_feeder_id`, `gt_meter_id`, `gt_pair_category`, `gt_event_1_class`, `gt_event_1_type`, `gt_event_2_class`, `gt_event_2_type`, 
   - **Observation Features ($M_{\mathrm{meter}}$):** Three-phase co-event waveforms (`obs_coevent_v`, `obs_coevent_i`), composed single-event responses (`obs_composed_single_event_v`, `obs_composed_single_event_i`), residual waveforms (`obs_residual_v`, `obs_residual_i`), and scalar residual magnitudes (`residual_voltage_magnitude`, `residual_current_magnitude`) across the 3 phases. Uses a fixed baseline transformer specification and fixed $t_{\mathrm{offset}} = 0.0\,\mathrm{s}$ 

3. **Dataset 3**: Evaluates how residual magnitude in pair varies with time shift operation ($t_{\mathrm{offset}} = 0.0\,\mathrm{s}$ vs $t_{\mathrm{offset}} > 0.0\,\mathrm{s}$) across load switch pairs, line fault pairs, and mixed load-fault pairs.
   - **Ground-Truth Target Variables ($X_R$):** `gt_scenario_id`, `gt_transformer_id`, `gt_transformer_spec_id`, `gt_feeder_id`, `gt_meter_id`, `gt_pair_category`, `gt_event_1_class`, `gt_event_1_type`, `gt_event_2_class`, `gt_event_2_type`,`gt_time_offset_s` 
   - **Observation Features ($M_{\mathrm{meter}}$):** Three-phase co-event waveforms (`obs_coevent_v`, `obs_coevent_i`), composed single-event responses (`obs_composed_single_event_v`, `obs_composed_single_event_i`), residual waveforms (`obs_residual_v`, `obs_residual_i`), and scalar residual magnitudes (`residual_voltage_magnitude`, `residual_current_magnitude`) across the 3 phases. Uses a fixed baseline transformer specification

4. **Dataset 4**: Evaluates how transformer specification affects the observability of line fault pairs, load switch pairs, and mixed load-fault pairs. Featuring varying transformer specifications:
| Parameter     
Regulation  
Full-load Copper Loss    
Copper Loss @80% Loading 
| -------------------- 
| Percentage Impedance 
| Resistance           
| Leakage Reactance    
| X/R Ratio            
| Sequence | Resistance | Reactance |
| -------- | 
| Positive | 
| Negative | 
| Zero     |         
| ---------------------
| Excitation Current   
| Magnetizing Reactance
| Core-loss Resistance 

   - **Ground-Truth Target Variables ($X_R$):** `gt_scenario_id`, `gt_transformer_id`, `gt_transformer_spec_id`, `gt_feeder_id`, `gt_meter_id`, `gt_pair_category`, `gt_event_1_class`, `gt_event_1_type`, `gt_event_2_class`, `gt_event_2_type`, 
   - **Observation Features ($M_{\mathrm{meter}}$):** Three-phase co-event waveforms (`obs_coevent_v`, `obs_coevent_i`), composed single-event responses (`obs_composed_single_event_v`, `obs_composed_single_event_i`), residual waveforms (`obs_residual_v`, `obs_residual_i`), and scalar residual magnitudes (`residual_voltage_magnitude`, `residual_current_magnitude`) across the 3 phases. Uses fixed $t_{\mathrm{offset}} = 0.0\,\mathrm{s}$ 


#### 4. Statistical Tests for lv network observable  using trasnformer transients

##### Dataset 2 Event Pair Observability Testing 

Factorial ANOVA analysis (`src/statistics/q1_event_pair_analysis.py`) evaluates event pair observability across load switch pairs (`load_load`), line fault pairs (`fault_fault`), and mixed load-fault pairs (`load_fault`), Evaluates $F_{\mathrm{voltage}}, p_{\mathrm{voltage}}$ and $F_{\mathrm{current}}, p_{\mathrm{current}}$ to test observability differences across pair categories.

##### Dataset 3 Time Shift Operation Variation Testing

Levene / Brown-Forsythe variance analysis (`src/statistics/q2_time_shift_analysis.py`) evaluates residual magnitude variation under time shift operations ($t_{\mathrm{offset}} = 0$ vs $t_{\mathrm{offset}} > 0$) using Dataset 3 across: Load switch event pairs, Line fault event pairs and load switch and fault pairs

##### Dataset 4 Transformer Specification Effect Testing

One-Way ANOVA testing (`src/statistics/q3_transformer_spec_analysis.py`) evaluates how transformer specification variations affect observability across load switch pairs, line fault pairs, and mixed pairs, Measures $F_{\mathrm{spec}}, p_{\mathrm{spec}}$ across transformer specification.

**Limitations:** The validation establishes the practical limits of boundary-based realization and identifies the sensing architecture required for distributed dynamic state estimation in partially observable distribution networks within the limits of the simulated environment.
