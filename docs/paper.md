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
*   Sensitivity-Driven Cell Parameter Optimization 
The projected design space ($\theta = [\theta_s, \theta_m]$) is explored with a hierarchical workflow that combines sensitivity screening, objective-specific SG-CEM refinement, and expensive stability filtering. In the implementation, the design vector is first perturbed around a nominal point to estimate the Jacobian of the energy, power, and stability responses; only the most influential variables for each objective are retained for optimization instead of searching the full design space at once.

#### BESS Robustness Evaluation Framework


1. Electrochemical–Thermal Driver Model



The BESS is evaluated using the DFN electrochemical model coupled with the thermal model. The model provides the measurable simulation outputs required for performance evaluation:

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

[eta_{RTE}=frac{E_{\mathrm{dis}}}{E_{\mathrm{chg}}}] whereb[E_{\mathrm{dis}}=int_{\mathrm{discharge}} V(t)I(t),dt]
and [E_{\mathrm{chg}}=\int_{\mathrm{charge}} |V(t)I(t)|\,dt.] Coulombic Efficiency

Measures the fraction of charge recovered in terms of electrical charge:

[\eta_C=\frac{Q_{\mathrm{dis}}}{Q_{\mathrm{chg}}}] with [Q_{\mathrm{dis}}= int_{\mathrm{discharge}} |I(t)|\,dt,\qquad Q_{\mathrm{chg}}=\int_{\mathrm{charge}} |I(t)|\,dt.]

Voltage Efficiency

Represents the voltage-related loss independently of charge throughput:

[\eta_V=\frac{\eta_{RTE}}{\eta_C}.]

Usable Energy Capacity

Measures the energy delivered over the defined operating SOC window:

[E_{\mathrm{usable}}=\int_{t_0}^{t_1}|V(t)I(t)|\,dt] where \(t_0\) and \(t_1\) correspond to the specified upper and lower SOC limits.

Power Capability

Measures the maximum deliverable electrical power during the simulated operating window:

[P_{\max}=\max_t |V(t)I(t)|.]

Thermal Response

Measures the temperature excursion produced during operation:

[\Delta T=T_{\max}-T_{\min}] and the maximum operating temperature is[T_{\max}=\max_t T(t).]

Depth of Discharge

For each simulated cycle:

[DoD=SoC_{\max}-SoC_{\min}.]

Equivalent Full Cycles

Accumulated energy throughput is converted into equivalent full cycles:

[EFC=\frac{\displaystyle\int |P(t)|\,dt}{2E_{\mathrm{rated}}}.]

The factor of \(2\) accounts for one complete charge and discharge throughput.

Capacity Fade

The loss of usable capacity relative to the initial condition is:

[F_Q(t)=1-\frac{Q_{\max}(t)}{Q_{\max}(0)}.]

Cycle Life

Cycle life is estimated from the simulated degradation trajectory as the point at which the battery reaches the prescribed minimum \(SoH\):

[N_{\mathrm{life}}=\min\left\{N:SoH(N)\le SoH_{\mathrm{limit}}\right\}.]

Calendar Life

Where calendar-aging simulations are performed, the corresponding lifetime is:
[t_{\mathrm{life}}=\min\left\{t:SoH(t)\le SoH_{\mathrm{limit}}\right\}.]

Levelized Cost of Storage

For the economic assessment:

[LCOS=\frac{C_{\mathrm{capital}}+C_{\mathrm{replacement}}+C_{\mathrm{operation}}}{E_{\mathrm{lifetime,dis}}}\]
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

* (M) denotes synchronized measurements acquired at the meters and distribution transformers,
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

* **Main Feeder**: with lines extending from the substation, each characterized by known feeder lengths and impedances.

* **Fixed Set of Transformers**: Step-down distribution transformers whose primary-side terminals serve as the boundary measurement interfaces.

* **Measurement and Monitoring Devices**: Electrical sensors capturing voltage, current, active/reactive power, and sequence components at the meters and transformer primary terminal.

---

#### 3. Measurement Architecture

Measurements are obtained from two sensing layers: PCC line measurements using smart meters and transformer edge monitoring.

**A. PCC Smart-Meter Measurements**

The metering hierarchy is organized as follows:

```text
             Known MV feeder
                       │
                       │
                 ┌─────┴─────┐
                 │ Transformer│
                 └─────┬─────┘
                       │
                    PCC / Edge
                    Smart Meter
                       │
              ┌────────┴────────┐
              │                 │
            Line A            Line B
              │                 │
             PCC                |
          Smart Meter           |
              │                 │
          ┌───┴───┐       ┌───┴───┐
          │        │       │         │
```

Selected candidate PCCs are instrumented with smart meters to acquire:

##### Electrical Quantities

* Three-phase voltage magnitude and phase angle
* Three-phase current magnitude and phase angle
* Active power (P)
* Reactive power (Q)
* Apparent power (S)
* Power factor (PF)

##### Network Quality Metrics

* Frequency
* Rate of Change of Frequency (ROCOF)
* Voltage unbalance
* Current unbalance
* Positive-, negative-, and zero-sequence components

---

**B. Transformer Measurements**

Each distribution transformer serves as an edge measurement node representing the interface to an unknown downstream network.

Measurements include
Primary Electrical Measurements

    High-voltage terminal voltage magnitude and phase angle
    High-voltage terminal current magnitude and phase angle
    Active power
    Reactive power
    Apparent power
    Power factor

Dynamic Quantities

    Loading rate
    Overload duration
    Load recovery characteristics
    Transformer temperature
    Transient voltage and current waveforms

---

##### 4. Distribution Network Simulation And Station Modeling

The simulation framework systematically perturbs the unknown downstream network while maintaining a fixed upstream distribution station.

OpenDSS is used to simulate the known upstream station together with the hidden downstream distribution network.

A transient simulator is included to support waveform-based event responses, but the current implementation also relies on synchronized steady-state boundary measurements from OpenDSS.

The code generates scenario datasets by:

* building hidden downstream topologies with radial and optional ring configurations
* modifying the number of downstream buses and network connectivity
* perturbing line parameters using a scenario-dependent multiplier
* varying load allocation and load composition across linear, non-linear, and heavy-duty load classes
* assigning transformer loading to each boundary transformer in the range 30–75 %
* instantiating switching events for transformer inrush, capacitor switching, motor starts, feeder switching, and temporary faults
* constructing OpenDSS objects for lines, loads, capacitors, motors, and distributed energy resources

For each scenario, `CoSimulationRunner.run_scenario`:

* solves the OpenDSS operating point for the known upstream plant plus the hidden downstream network
* collects PCC measurements via `get_pcc_measurements()`
* builds an ATP event case with `ATPCaseBuilder`
* currently falls back to synchronized operating-point values when EMT waveform output is unavailable

Measurements captured in each result include:

* transformer three-phase voltages and currents waveforms
* active power (`P`), reactive power (`Q`), and apparent power (`S`) at boundary nodes
* derived steady-state features, sequence features, transient features, and spectral features

The simulation framework generates two distinct, decoupled datasets to evaluate the latent observability problem under different operating conditions. Critically, to align with the decentralized physical architecture, measurements are not synchronized across transformers, and each dataset element strictly references exactly one transformer's measurements to prevent any inter-transformer leakage:

1. **Dataset 1 (Scenario-Based Dataset)**: Focuses on steady-state network realization and structural state estimation.
   - **Ground-Truth Target Variables ($X_R$):** Network line parameter multiplier (`line_parameter_multiplier`), topology class (`topology_type`), and network size (`hidden_total_buses`) of a single specific feeder's hidden LV network.
   - **Observation Features ($M_{\mathrm{PCC}}$):** Strictly limited to the associated single LV transformer monitoring device steady-state measurements and its associated transformer edge LV smart-meter measurements, completely excluding measurements from other transformers.

2. **Dataset 2 (Event-Based Dataset)**: Focuses on transient/switching dynamic state realization.
   - **Ground-Truth Target Variables ($X_R$):** Event type (`simulated_event`) and event occurrence timestamp (`switching_timestamp_s`).
   - **Observation Features ($M_{\mathrm{PCC}}$):** Synchronized readings of a single selected branch smart-meter and its associated single parent edge transformer device. Measurements are strictly localized and synced across the meter-transformer nodes of the same unknown LV network only.

Each perturbed network is simulated to produce these decoupled datasets, linking hidden network states and events to observable PCC-level signatures without any target label leakage or cross-transformer data contamination.

---

##### statistical tests for state estimation

* Test 1 — Distance correlation: does the measurement contain information about hidden state?

Distance correlation was specifically developed to detect dependence between random vectors and has the important property that population distance correlation is zero iff the variables are independent.

Define:
\[ X=\text{hidden network state} \] and \[ Y=\text{measurement vector}. \]
Calculate \[ dCor(X,Y). \]

the hypothesis becomes:
\[ H_0:X\perp Y \] versus \[ H_1:X\not\perp Y. \]
But we do not rely on the asymptotic p-value. we use a permutation test.

* Test 2 — MMD: do two hidden networks generate different measurement distributions?

This is particularly useful because the hidden networks are discrete realizations.

Take two hidden network states: \[ G_a,\;G_b. \]
Their corresponding measurement distributions are: \[ P_a(Y) \]and\[ P_b(Y). \]
The null hypothesis is:
\[ H_0:P_a=P_b. \]

Using the Maximum Mean Discrepancy (MMD) two-sample test. Gretton et al. formulated MMD specifically as a kernel-based statistical test for determining whether two samples originate from different distributions.

Conceptually: \[ MMD^2(P_a,P_b) = \left\| \mu_{P_a}-\mu_{P_b} \right\|_{\mathcal H}^{2}. \]

This is extremely appropriate for the dataset because we don't need to assume that the measurements are Gaussian.

* Test 3 — PERMANOVA: are measurement vectors separated by hidden network state?

Anderson's PERMANOVA provides a non-parametric multivariate analogue of ANOVA based on distances and permutations.

The model can be: \[ D_{ij}=d(Y_i,Y_j) \]
where \(d\) might be: Euclidean distance, standardized Euclidean distance,
Mahalanobis distance,
or another appropriate distance.

Then test: \[ H_0: \text{measurement distributions do not differ by network realization}. \] The resulting pseudo-\(F\) statistic and permutation \(p\)-value tell you whether the groups differ.

More importantly we report:
\[ R^2_{\rm network} = \frac{SS_{\rm network}}{SS_{\rm total}}. \]

PERMANOVA can confound location differences with dispersion differences. Therefore, we pair it with a dispersion test rather than reporting it alone.

Brown–Forsythe: does network state change measurement variability?

For each measurement feature \(Y_j\), test:
\[ H_0: \sigma^2_{G_1} = \sigma^2_{G_2} = \cdots = \sigma^2_{G_K}. \] Brown–Forsythe is specifically designed as a robust test for equality of variances, making it less sensitive to non-normality than the classical variance-ratio approach.

For example:
Network A and B may have similar mean voltage/current responses, but Network B produces substantially greater variability.

That variability itself can carry information about the hidden network.
So we investigate: \[ E[Y|G]. \] and \[ Var(Y|G). \]

* Test 4 — Noise robustness: 
we don't merely add Gaussian noise and report correlation coefficients.
we Construct controlled noise levels.

For example:
\[ Y^{(\sigma)} = Y+\epsilon, \] with \[ \epsilon\sim\mathcal N(0,\sigma^2). \]
Or
\[ Y_j^{(\sigma)} = Y_j+\epsilon_j, \] where
\[ \epsilon_j\sim \mathcal N(0,\sigma_j^2). \]

Then repeat the same statistical tests.
Now you can define an empirical statistical observability threshold.

* Test 5 — TOST for practical equivalence

Suppose two different hidden networks produce almost indistinguishable measurement responses.
formulate an equivalence margin for a measurement feature:

\[ \Delta_L=-\delta,\qquad \Delta_U=+\delta. \]
Then perform the Two One-Sided Tests procedure:
\[ H_{01}:\Delta\leq-\delta \]and\[ H_{02}:\Delta\geq+\delta. \]
Rejecting both means the difference lies within the pre-specified practically negligible interval.


That gives a principled way of identifying observationally indistinguishable network classes
HSIC is another kernel-based independence test.
we test: \[ H_0:X\perp Y. \] HSIC measures dependence through the Hilbert–Schmidt norm of the cross-covariance operator.

* Test 6 — Is hidden network configuration statistically observable?

This is important for your eventual operator design.

For each measurement channel \(Y_j\), test which classes of downstream perturbations—including topology changes, network size, load redistribution, switching events, transformer loading, and line parameter variations—produce measurable changes at the distribution station boundary:

\[ H_0:X\perp Y_j. \]
Tests:
distance correlation
permutation test
HSIC as secondary confirmation

This is directly useful for the question: Which hidden network properties are electrically observable at the station interface?

##### validation architecture

```text
                DATASET
                    │
          ┌─────────┴─────────┐
          │                   │
   Hidden Network State   Measurements
          │                   │
          └─────────┬─────────┘
                    │
              Statistical
                Analysis
                    │
        ┌───────────┼───────────┐
        │           │           │
     Dependence  Distribution  Multivariate
        │        Separation     Separation
        │           │           │
      dCor         MMD       PERMANOVA
      HSIC
        │           │           │
        └───────────┼───────────┘
                    │
             Noise Injection
                    │
          ┌─────────┴─────────┐
          │                   │
       SNR sweep          Sensor noise
          │                   │
          └─────────┬─────────┘
                    │
           Repeat statistical
               validation
                    │
                    ▼
       Statistical Observability
                    │
        ┌───────────┴───────────┐
        │                       │
 Distinguishable states    Equivalent states
        │                       │
       MMD                 TOST/equivalence
        │                       │
        └───────────┬───────────┘
                    ▼
        Operator Design Requirements
```

We decide whether the statistical unit should be the scenario trajectory, the event response, or derived window-level features. That choice determines whether these tests remain statistically valid in the presence of temporal autocorrelation and repeated measurements.

The validation establishes the practical limits of boundary-based realization and identifies the sensing architecture required for distributed dynamic state estimation in partially observable distribution networks within the limits of the simulated environment.
