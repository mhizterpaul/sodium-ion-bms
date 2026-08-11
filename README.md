# Distribution System State Estimation Using Wavelet Decomposition with NFPP Sodium-Ion BESS Performance Evaluation

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mhizterpaul/sodium-ion-ess/blob/main/src/report.ipynb)

## Research Summary & Scope

### 1. DFN-Based NFPP Cell Optimization
A hierarchical multi-stage framework for cell design enhancement:

*   **Layered Material Mapping**: Decoupled architecture for eco-friendly salts (NaTCP, NaBOB), cathode dopants (Cr, Mn, Ni), and MTMS functionalization.

*   **Parameter Optimization**: Hierarchical search for structural ($\theta_s$) and material ($\theta_m$) parameters using sensitivity-based Jacobian screening and a Sensitivity-Guided Cross-Entropy Method (SG-CEM).

This repository implements an  plant condition–integrated, high-fidelity performance benchmarking of Sodium Iron Pyrophosphate (NFPP) battery energy storage systems (BESS). 

### 2. Distribution Network State Estimation & Feature Extraction (Core Contribution)

The primary research focus is the realization of latent network states in a multi-feeder distribution network using boundary measurements and sub-cycle transient realization signatures:

*   **Fixed Upstream Plant**: OpenDSS model incorporating utility swing bus, substation step-down transformer and 3 feeders with a fixed set of distribution transformers acting as measurement boundaries.

*   **Scenario Generator**: Systematic perturbation of the unknown downstream networks connected to the feeders, featuring linear and non-linear loads, varying live loads, changing line lengths (electrical distance), switching events, and topology reconfigurations (radial vs ring/loop).

*   **ATP-EMTP Transient Coupling**: Coupling of sub-cycle transients (such as transformer inrush, capacitor switching, motor starting, temporary faults, and non-linear switching  to extract high-frequency spectral and waveform features).

*   **Boundary Measurements**: line and phase angle extraction from OpenDSS.

*   **Feature Tabulation & Rendering**: Export of all steady-state and dynamic parameters directly to CSV, rendering tabulations of transformer parameters and meter parameters in `report.ipynb`.

## Repository Structure

- `src/cell_optimization/`: Material selection using the materials dataset, chemical regularization, and parameter optimization scripts.
- `src/power_plant/`: OpenDSS fixed plant model, measurement extraction, and ATP-EMTP dynamic transient extraction.
- `src/simulation/`: Scenario generator, perturbed downstream line, load, and switching event.
- `nfpp_sodium_ion/`: Ready-to-be-published PyBaMM parameter set for NFPP/Hard-Carbon chemistry.
- `src/report.ipynb`: Orchestration notebook for the complete research pipeline.

## Getting Started

### Installation
```bash
# Install core dependencies
pip install -r requirements.txt

# Install PyBaMM parameter package in editable mode
pip install -e nfpp_sodium_ion/
```

### Execution
Run the complete research pipeline via the Jupyter notebook:
```bash
jupyter notebook src/report.ipynb
```

## References

- **Keywords**: Sodium Iron Pyrophosphate (NFPP), Sodium-Ion Battery, Energy Storage System, Distribution System State Estimation (DSSE), Network Realization, Wavelet Decomposition, Multiresolution Analysis, Distribution Network Observability, Transient Analysis, Statistical Analysis, Microgrid.
- **Modeling Framework**: PyBaMM (Electrochemical), FEniCSx (Mechanical), OpenDSS (Distribution Power Flow), ATP-EMTP(transformer transients)
