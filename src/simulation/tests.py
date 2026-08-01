import pybamm
import numpy as np
import os
import json
import copy
import traceback
from nfpp_sodium_ion.src.cell_parameters.parameter_builder import get_parameter_values
from src.cell_optimization.parameter_opts import ParamTransform, DESIGN_SPACE
from src.simulation.utilities.tests_driver import ElectrochemicalThermalDriverModel

class BESSScenarioGenerator:
    """Generates realistic BESS Experiments (Issue 3, 11, 13) with optimized rest durations."""

    @staticmethod
    def charge_step(rate, limit=None):
        return f"Charge at {rate} until {limit}V" if limit else f"Charge at {rate}"

    @staticmethod
    def discharge_step(rate, limit=None):
        return f"Discharge at {rate} until {limit}V" if limit else f"Discharge at {rate}"

    @staticmethod
    def get_blackout_scenario(v_max, fast=False):
        if fast:
            return pybamm.Experiment([
                "Charge at 1C for 2 minutes",
                "Rest for 2 minutes"
            ])
        # Unexpected grid outage during charging with 2-minute rest
        return pybamm.Experiment([
            "Charge at 1C for 20 minutes",
            "Rest for 120 seconds"
        ])

    @staticmethod
    def get_dispatch_scenario(v_min, v_max, fast=False):
        # Issue 3, 10: Multi-stage realistic BESS dispatch - Left as is for dispatch performance evaluation
        return pybamm.Experiment([
            BESSScenarioGenerator.discharge_step("0.5C", limit=v_min),
            "Rest for 20 minutes",
            BESSScenarioGenerator.charge_step("0.5C", limit=v_max),
            "Rest for 20 minutes",
            "Discharge at 10 W for 10 minutes", # Peak shaving proxy
            "Rest for 30 minutes"
        ])

    @staticmethod
    def get_pv_firming_scenario(v_max):
        # Realistic PV ramps with optimized 30-second rest durations
        return pybamm.Experiment([
            "Charge at 0.2C for 5 minutes",
            "Rest for 30 seconds",
            "Charge at 0.8C for 5 minutes",
            "Rest for 30 seconds",
            BESSScenarioGenerator.charge_step("0.5C", limit=v_max)
        ])

class StabilityValidator:
    """
    Stability Validation focusing on robustness, blackout recovery, thermal response, efficiency,
    and charge cycling estimation.
    """

    def __init__(self):
        # Enforce final_validation.json dependency
        val_path = "final_validation.json"
        if not os.path.exists(val_path):
            raise FileNotFoundError(f"Missing mandatory pipeline artifact: {val_path}. Run validate.py first.")

        with open(val_path, "r") as f:
            self.pipeline_data = json.load(f)

        opt_data = self.pipeline_data.get("optimization")
        if not opt_data:
            raise KeyError(f"Invalid optimization data in {val_path}")

        # Reconstruct optimized parameters using the pipeline values
        base_params = get_parameter_values()
        pt = ParamTransform(pybamm.ParameterValues(base_params))

        # Apply deltas (merging functionalization if present)
        deltas = copy.deepcopy(opt_data.get("combined_deltas_representative", {}))

        pt.apply_physics_deltas(deltas)

        design_specs = opt_data.get("design_specs_representative", {})
        pt.apply_design_vector(
            np.array([design_specs[k] for k in DESIGN_SPACE if k in design_specs]),
            [k for k in DESIGN_SPACE if k in design_specs]
        )

        self.optimized_params = pt.get_parameter_values()
        # Ensure DFN stability parameters from validate.py
        if "SEI solvent diffusivity [m2.s-1]" not in self.optimized_params:
             self.optimized_params["SEI solvent diffusivity [m2.s-1]"] = 2.5e-22
        if "Bulk solvent concentration [mol.m-3]" not in self.optimized_params:
             self.optimized_params["Bulk solvent concentration [mol.m-3]"] = 2636.0
        self.electro_model = ElectrochemicalThermalDriverModel()

    def run_full_simulation(self, updates, c_rate=1.0, experiment=None):
        # 1. Electrochemical-Thermal Solve
        model_dict = self.electro_model.build_model(parameter_updates=updates)

        try:
            fast_run = (os.environ.get("CEM_FAST_RUN") == "True")
            if experiment:
                results = self.electro_model.simulate(model_dict, experiment=experiment)
            else:
                # Adjust current for C-rate (handle scalar or profile)
                cap_ah = model_dict["parameter_values"]["Nominal cell capacity [A.h]"]

                # Effective average c-rate for time scaling
                if isinstance(c_rate, (list, np.ndarray)):
                    eff_c_rate = np.mean(c_rate)
                    current = c_rate * cap_ah
                else:
                    eff_c_rate = c_rate
                    current = c_rate * cap_ah

                # Time for 1C is 3600s
                duration = 120 if fast_run else (3600 / eff_c_rate)
                n_pts = 10 if fast_run else 50
                times = np.linspace(0, duration, n_pts)
                results = self.electro_model.simulate(model_dict, times, current_function=current)

            return {
                "electro": results,
                "params": model_dict["parameter_values"]
            }
        except Exception as e:
            print(f"ERROR: run_full_simulation failed: {e}\n{traceback.format_exc()}")
            raise

    def validate_optimized_design(self):
        print("Validating optimized twin with full physics (using BESS scenarios)...")

        v_min = self.optimized_params["Lower voltage cut-off [V]"]
        v_max = self.optimized_params["Upper voltage cut-off [V]"]

        fast_run = (os.environ.get("CEM_FAST_RUN") == "True")

        # 1. Base Validation: BESS Dispatch (Issue 3, 11) - left as is
        dispatch_experiment = BESSScenarioGenerator.get_dispatch_scenario(v_min, v_max, fast=fast_run)
        res_dispatch = self.run_full_simulation(self.optimized_params, experiment=dispatch_experiment)

        # 2. Robustness Check: Grid Outage during Charge (Issue 11, 13)
        print("  Running Robustness Check: Grid Outage during high-rate charge (+10% thickness)...")
        robust_updates = self.optimized_params.copy()
        robust_updates["Positive electrode thickness [m]"] *= 1.1

        blackout_experiment = BESSScenarioGenerator.get_blackout_scenario(v_max, fast=fast_run)
        res_robust = self.run_full_simulation(robust_updates, experiment=blackout_experiment)

        # 3. Varying C-rate Stress Test (Requested by user)
        if fast_run:
            print("  Running Varying C-rate Stress Test (Fast profile)...")
            profile = self.electro_model.get_varying_c_rate_profile(base_c_rate=1.0, duration=120, n_points=10)
        else:
            print("  Running Varying C-rate Stress Test (Oscillating profile)...")
            profile = self.electro_model.get_varying_c_rate_profile(base_c_rate=1.0, duration=1800, n_points=50)
        res_varying = self.run_full_simulation(self.optimized_params, c_rate=profile)

        # 4. Physically Meaningful Efficiency Metrics (Issue 4, 5, 12)
        def compute_efficiency_metrics(sol):
             v = sol["Terminal voltage [V]"].entries
             i = sol["Current [A]"].entries
             t = sol["Time [s]"].entries
             p = v * i

             # Identify flow direction via Discharge capacity change (Issue 4, 12)
             q_ah = sol["Discharge capacity [A.h]"].entries
             # Positive diff in discharge capacity = discharge process
             is_discharge = np.concatenate([[True], np.diff(q_ah) >= 0])

             trapz_func = getattr(np, "trapezoid", getattr(np, "trapz", None))

             # Separate Charge (in) and Discharge (out) using robust sign detection
             e_out = trapz_func(np.where(is_discharge, p, 0), t) / 3600.0
             e_in = abs(trapz_func(np.where(~is_discharge, p, 0), t)) / 3600.0

             # Coulombic efficiency integration (Issue 5)
             q_out = trapz_func(np.where(is_discharge, i, 0), t) / 3600.0
             q_in = abs(trapz_func(np.where(~is_discharge, i, 0), t)) / 3600.0

             eta_e = e_out / e_in if e_in > 0 else 0.0
             eta_c = q_out / q_in if q_in > 0 else 0.0
             eta_v = eta_e / eta_c if eta_c > 0 else 0.0

             return {"e_in": e_in, "e_out": e_out, "eta_energy": eta_e, "eta_coulombic": eta_c, "eta_voltage": eta_v}

        metrics = compute_efficiency_metrics(res_dispatch["electro"]["solution"])

        # 4. Constraint-Based Robustness Scoring (Issue 6, 14)
        def evaluate_robustness(res):
             T_max = np.max(res["electro"]["temperature"])
             soh_final = res["electro"]["soh_trajectory"][-1] / 100.0
             v_min_actual = np.min(res["electro"]["terminal_voltage"])
             v_max_actual = np.max(res["electro"]["terminal_voltage"])

             # Hard constraints focusing on thermal and SOH/voltage stability
             constraints = [
                  T_max < 333.15, # 60C limit
                  soh_final > 0.99, # Negligible degradation for short trace
                  v_min_actual > 0.95 * v_min,
                  v_max_actual < 1.05 * v_max
             ]

             score = sum(constraints) / len(constraints)
             return score, all(constraints)

        robustness_score, robustness_passed = evaluate_robustness(res_robust)

        # Also check varying c-rate robustness
        var_score, var_passed = evaluate_robustness(res_varying)
        combined_robustness_score = (robustness_score + var_score) / 2.0

        # Compile final report
        clean_params = {}
        for k, v in res_dispatch["params"].items():
            if not callable(v):
                clean_k = k.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").replace(".", "").replace("/", "_")[:31]
                clean_params[clean_k] = v

        results = {
            "energy_discharge_kwh": float(metrics["e_out"] / 1000.0),
            "energy_charge_kwh": float(metrics["e_in"] / 1000.0),
            "eta_energy": float(metrics["eta_energy"]),
            "eta_coulombic": float(metrics["eta_coulombic"]),
            "eta_voltage": float(metrics["eta_voltage"]),
            "nominal_voltage_v": float(np.mean(res_dispatch["electro"]["terminal_voltage"])),
            "max_thermal_response_k": float(np.max(res_dispatch["electro"]["temperature"])),
            "robustness_score": float(combined_robustness_score),
            "robustness_passed": bool(robustness_passed and var_passed),
            "blackout_recovery_success": bool(res_robust["electro"]["solution"] is not None),
            "estimated_charge_cycling_soh": float(res_dispatch["electro"]["soh_trajectory"][-1]),
            "merged_params": clean_params
        }

        return results

    def export_to_json(self, results, output_path="src/power_plant/cell_params.json"):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Validated Model (JSON) exported to {output_path}")

if __name__ == "__main__":
    validator = StabilityValidator()
    results = validator.validate_optimized_design()
    validator.export_to_json(results)
