# NFPP Sodium-Ion Energy Storage Evaluation for Distribution Networks

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mhizterpaul/sodium-ion-ess/blob/main/src/report.ipynb)

## Research Summary & Scope

### 1. DFN-Based NFPP Cell Optimization
A hierarchical multi-stage framework for cell design enhancement:

*   **Layered Material Mapping**: Decoupled architecture for eco-friendly salts (NaTCP, NaBOB), cathode dopants (Cr, Mn, Ni), and MTMS functionalization.

*   **Parameter Optimization**: Hierarchical search for structural ($\theta_s$) and material ($\theta_m$) parameters using sensitivity-based Jacobian screening and a Sensitivity-Guided Cross-Entropy Method (SG-CEM).

Repository Status

The research was initiated to optimize a literature-derived NFPP cell by replacing expensive salt systems and improving its electrochemical properties for grid-scale battery energy storage applications. NFPP chemistry is comparatively safe, practical to work with, and well suited to BESS applications; however, its economic viability remains constrained by supply-chain limitations and the lack of economies of scale.

Development Status: Discontinued / Frozen

The research is currently discontinued until further notice and the repository is frozen at its present stage. The primary constraint is the available development time, combined with the insufficiency of the selected continuum-mechanics solver (FEniCSx) for the required coupled multiphysics formulation.

The intended optimization must satisfy both mechanical and operational stability constraints, including:

* intercalation-induced strain
* thermal strain
* cell-formation and first-cycle strain
* interfacial-layer stability associated with functionalization
* dopant-induced structural strain

In addition, the effects of the selected dopants on the underlying cell physics must be derived and coupled consistently to the electrochemical model. This coupling is necessary to preserve the physical validity of the resulting BESS performance evaluation

The stoichiometric-loss model also requires further mathematical formulation and integration into the coupled electrochemical-mechanical framework. Completing these components requires substantial constitutive development, multiphysics formulation, parameter identification, and experimental validation. Consequently, the complete optimization problem is not attainable within the current time constraints.

The work is therefore frozen at its present stage, with the existing implementation retained as a research baseline for potential future continuation.

## Repository Structure

- `src/cell_optimization/`: Material selection using the materials dataset, chemical regularization, and parameter optimization scripts.
- `nfpp_sodium_ion/`: parameter set for NFPP/Hard-Carbon chemistry.
- `src/report.ipynb`: Orchestration notebook for the complete research pipeline.

### Execution

Run the complete research pipeline via the Jupyter notebook:
```bash
jupyter notebook src/report.ipynb
```

## References
- **Keywords**: Sodium Iron Pyrophosphate (NFPP), Sodium-Ion Battery, Energy Storage System
- **Modeling Framework**: PyBaMM (Electrochemical) 
