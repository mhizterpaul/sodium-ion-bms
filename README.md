# Advanced State Estimation and NFPP Sodium-Ion Energy Storage Evaluation for Distribution Networks

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mhizterpaul/sodium-ion-ess/blob/main/src/report.ipynb)

## Research Summary & Scope

### 1. DFN-Based NFPP Cell Optimization
A hierarchical multi-stage framework for cell design enhancement:

*   **Layered Material Mapping**: Decoupled architecture for eco-friendly salts (NaTCP, NaBOB), cathode dopants (Cr, Mn, Ni), and MTMS functionalization.

*   **Parameter Optimization**: Hierarchical search for structural ($\theta_s$) and material ($\theta_m$) parameters using sensitivity-based Jacobian screening and a Sensitivity-Guided Cross-Entropy Method (SG-CEM).

This repository implements an plant condition–integrated, high-fidelity performance benchmarking of Sodium Iron Pyrophosphate (NFPP) battery energy storage systems (BESS).

### 2. Time-Adjusted Cluster Load Allocation with Error Correction in Sparsely Metered Distribution Networks (Core Contribution)

The primary research focus is distribution network state estimation using Time-Adjusted Cluster Load Allocation (CLA) and transformer dynamic signal processing in sparsely metered distribution networks:

*   **Known Upstream Plant & LV Networks**: OpenDSS model incorporating utility swing bus, substation step-down transformer, and 3 feeders with known radial LV topologies and transformer edge interfaces.

*   **Time-Adjusted Cluster Load Allocation**: Unmetered customer energy allocation ($E_U = E_F - E_M - E_L$) using class-based profile weights, time-adjustment integrals $\alpha_i(t)$, and technical loss accounting ($E_L = E_{\mathrm{transformer\_loss}} + E_{\mathrm{line\_loss}}$).

*   **ATP-EMTP Transient Coupling**: Coupling of sub-cycle transients (such as equipment switching and explicit line faults) at distribution transformer secondaries to extract high-frequency spectral and waveform residual signatures for transient error correction.

*   **Boundary & Consumer Measurements**: 36% consumer smart meter coverage combined with feeder boundary and transformer secondary monitoring.

*   **Feature Tabulation & Rendering**: Export of all steady-state and dynamic parameters directly to CSV datasets, rendering error metrics and error reduction factor calculations in `report.ipynb`.

## Repository Structure

- `src/cell_optimization/`: Material selection using the materials dataset, chemical regularization, and parameter optimization scripts.
- `src/power_plant/`: OpenDSS fixed plant model, measurement extraction, and ATP-EMTP dynamic transient extraction.
- `src/lv_networks/`: Known radial LV network topologies, consumer equipment models, and meter selection routines.
- `src/estimator/`: Cluster Load Allocation (`cla_estimator.py`) and Time-Adjusted CLA (`time_adjusted_cla_estimator.py`) state estimation engines.
- `src/simulation/`: Scenario definitions, co-simulation runner, and dataset generation routines.
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

- **Keywords**: Sodium Iron Pyrophosphate (NFPP), Sodium-Ion Battery, Energy Storage System, Distribution System State Estimation (DSSE), Cluster Load Allocation, Time-Adjusted CLA, Transient Analysis, Statistical Analysis.
- **Modeling Framework**: PyBaMM (Electrochemical), FEniCSx (Mechanical), OpenDSS (Distribution Power Flow), ATP-EMTP (transformer transients).
