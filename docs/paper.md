# NFPP Sodium-Ion Energy Storage Evaluation for Distribution Networks

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
*   **Sensitivity-Guided Cross-Entropy Method (SG-CEM) Cell Parameter Optimization:** The cell design space ($\theta = [\theta_s, \theta_m]$) is optimized through a two-stage hierarchical architecture:
    *   **Stage 1: Electrochemical SG-CEM Optimization:** Optimizes individual scalar objectives ($f(\theta) \to \mathbb{R}$) for energy, power, and thermal stability. At the symbolic baseline anchor $\theta_{\text{symbolic}}$, $1 + 2N$ central finite-difference sweeps compute the local gradient, diagonal Hessian, and dimensionless parameter elasticities $S_j = \left| \frac{\theta_j}{f} \frac{\partial f}{\partial \theta_j} \right|$. A damped Newton step is applied in normalized $z$-space ($z \in [0, 1]$), and an adaptive sensitivity-conditioned trust region $r_j = r_{\min} + \tilde{S}_j(r_{\max} - r_{\min})$ ($0.5\%$ to $3\%$ of domain span) is formed around $\theta_{\text{symbolic}}$. To ensure numerical efficiency and prevent PyBaMM solver memory degradation, Stage 1 CEM executes sequentially in two steps for each objective: Step 1 optimizes material parameters ($\theta_m$: carbon fraction, electrolyte concentration) followed by PyBaMM memory clearing, and Step 2 optimizes structural parameters ($\theta_s$: electrode thicknesses, porosities, particle radii, loading fractions, Bruggeman coefficients). $\theta_{\text{symbolic}}$ is strictly preserved in the candidate population to guarantee non-degrading stochastic search iterations.
    *   **Stage 2: Independent FEM Structural-Stability Optimization:** Elite and best parameter candidate designs composed across objectives from Stage 1 undergo independent thermoelastic strain optimization using a finite element method (FEM) strain solver. Structural variables ($\theta_s$) are iteratively adjusted to satisfy critical thermoelastic strain constraints ($\eta = \epsilon_{\max} / \epsilon_{\text{critical}} \le \eta_{\text{threshold}}$). Candidates meeting stability criteria are filtered via multi-objective utility scoring ($0.4 E_{\text{norm}} + 0.4 P_{\text{norm}} + 0.2 T_{\text{norm}}$) to select the optimal representative design.

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

**Limitations:** 

