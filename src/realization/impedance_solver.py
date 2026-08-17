import numpy as np

class EquivalentImpedanceSolver:
    """
    Estimates positive-sequence complex equivalent impedance Z_eq = R_eq + j*X_eq
    from multiple operating point phasor observations using complex least squares:

        Z_eq = sum(V_k * conj(I_k)) / sum(|I_k|^2)
    """

    @staticmethod
    def compute_positive_sequence_phasor(v_abc_rms: tuple, i_abc_rms: tuple) -> tuple[complex, complex]:
        """
        Computes positive-sequence complex voltage V1 and current I1 from 3-phase RMS values.
        Phase angles are assumed balanced (0, -120, -240 deg) with potential operating unbalance.
        """
        a = np.exp(1j * 2 * np.pi / 3)
        v_a = v_abc_rms[0]
        v_b = v_abc_rms[1] * np.exp(-1j * 2 * np.pi / 3)
        v_c = v_abc_rms[2] * np.exp(1j * 2 * np.pi / 3)

        i_a = i_abc_rms[0]
        i_b = i_abc_rms[1] * np.exp(-1j * 2 * np.pi / 3)
        i_c = i_abc_rms[2] * np.exp(1j * 2 * np.pi / 3)

        v1 = (v_a + a * v_b + (a**2) * v_c) / 3.0
        i1 = (i_a + a * i_b + (a**2) * i_c) / 3.0

        return v1, i1

    @classmethod
    def estimate(cls, v_phasors: list[complex], i_phasors: list[complex]) -> tuple[float, float, float]:
        """
        Estimates (r_eq, x_eq, z_mag) from multi-operating-point complex phasors via complex least squares.
        """
        v = np.asarray(v_phasors, dtype=complex)
        i = np.asarray(i_phasors, dtype=complex)

        denom = np.sum(np.abs(i)**2)
        if denom <= 0 or not np.isfinite(denom):
            return 0.1, 0.05, float(np.sqrt(0.1**2 + 0.05**2))

        z_eq = np.sum(v * np.conj(i)) / denom

        r_eq = float(np.abs(z_eq.real))
        x_eq = float(np.abs(z_eq.imag))
        z_mag = float(np.sqrt(r_eq**2 + x_eq**2))

        return r_eq, x_eq, z_mag
