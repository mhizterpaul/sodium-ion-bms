# Upstream Distribution Station Specification

## 1. Upstream Utility Swing Source
- **Bus Type**: Swing / Slack / Infinite Bus
- **Nominal Voltage ($V_{\mathrm{src}}$)**: 33.0 kV (Line-to-Line RMS)
- **Phase Sequence**: ABC
- **Nominal Frequency ($f_0$)**: 50 Hz
- **Voltage Angle Reference ($\theta_{\mathrm{src}}$)**: 0.0°
- **Source Impedance ($Z_{\mathrm{src}}$)**: $0 + j0\ \Omega$ (Ideal infinite bus)
- **Sequence Impedances**: $Z_1 = 0\ \Omega$, $Z_2 = 0\ \Omega$, $Z_0 = 0\ \Omega$

## 2. Main Medium-Voltage Distribution Feeder Head
- **Nominal MV Voltage**: 11.0 kV (Line-to-Line RMS)
- **Feeder Count**: 3 Feeders (`feeder1`, `feeder2`, `feeder3`)
- **Feeder Conductor Type**: Overhead / Underground 3-phase conductor
- **Feeder Impedance Specification**:
  - $Z_1 = 0.25 + j0.35\ \Omega/\mathrm{km}$
  - $Z_0 = 0.75 + j1.12\ \Omega/\mathrm{km}$
  - Feeder 1 Length: 4.5 km
  - Feeder 2 Length: 6.2 km
  - Feeder 3 Length: 8.5 km
