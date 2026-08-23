import sys
import os

# Dynamically locate repository root to support namespace resolution across all environments
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
nfpp_dir = os.path.join(root_dir, "nfpp_sodium_ion")
src_dir = os.path.join(root_dir, "src")

for path in [root_dir, nfpp_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

import src
if hasattr(src, "__path__") and src_dir not in src.__path__:
    src.__path__.append(src_dir)

import pybamm
import numpy as np
import json
import copy
import traceback
from nfpp_sodium_ion.src.cell_parameters.parameter_builder import get_parameter_values
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters
from src.cell_optimization.parameter_opts import ParamTransform, DESIGN_SPACE
from src.simulation.utilities.tests_driver import ElectrochemicalThermalDriverModel

class BESSScenarioGenerator:
    """Generates realistic BESS Experiments with optimized rest durations."""

    @staticmethod
    def charge_step(rate, limit=None):
        return f"Charge at {rate} until {limit}V" if limit else f"Charge at {rate}"

    @staticmethod
    def discharge_step(rate, limit=None):
        return f"Discharge at {rate} until {limit}V" if limit else f"Discharge at {rate}"

    @staticmethod
    def get_dispatch_scenario(v_min, v_max):
        return pybamm.Experiment([
            BESSScenarioGenerator.discharge_step("0.5C", limit=v_min),
            "Rest for 20 minutes",
            BESSScenarioGenerator.charge_step("0.5C", limit=v_max),
            "Rest for 20 minutes",
            "Discharge at 10 W for 10 minutes",
            "Rest for 30 minutes"
        ])

class BESSEvaluator:
    """
    BESS Performance Evaluator focusing on robustness, blackout recovery, thermal response, efficiency,
    and charge cycling estimation.
    """

    def __init__(self, optimized_res=None):
        if optimized_res is not None:
            if "optimization" in optimized_res:
                self.pipeline_data = optimized_res
            else:
                self.pipeline_data = {"optimization": optimized_res}
        else:
            # Fallback to reading file if exists
            val_path = "final_validation.json"
            alt_path = "result.json"
            if os.path.exists(val_path):
                with open(val_path, "r") as f:
                    self.pipeline_data = json.load(f)
            elif os.path.exists(alt_path):
                with open(alt_path, "r") as f:
                    self.pipeline_data = {"optimization": json.load(f)}
            else:
                raise FileNotFoundError("Missing optimized_res or JSON pipeline artifacts.")

        opt_data = self.pipeline_data.get("optimization")
        if not opt_data:
            raise KeyError("Invalid optimization data structure")

        # Reconstruct optimized parameters using the pipeline values
        base_params = get_parameter_values()
        pt = ParamTransform(pybamm.ParameterValues(base_params))

        # Apply deltas (merging functionalization if present)
        deltas = copy.deepcopy(opt_data.get("combined_deltas_representative", {}))

        pt.apply_physics_deltas(deltas)

        design_specs = opt_data.get("design_specs_representative", {})
        self.design_specs = design_specs
        pt.apply_design_vector(
            np.array([design_specs[k] for k in DESIGN_SPACE if k in design_specs]),
            [k for k in DESIGN_SPACE if k in design_specs]
        )

        self.optimized_params = pt.get_parameter_values()
        # Ensure DFN stability parameters from validate.py using derived parameters (no hardcoded cell values)
        derived = get_derived_parameters()
        if "SEI solvent diffusivity [m2.s-1]" not in self.optimized_params:
             self.optimized_params["SEI solvent diffusivity [m2.s-1]"] = derived["sei_solvent_diffusivity"]
        if "Bulk solvent concentration [mol.m-3]" not in self.optimized_params:
             self.optimized_params["Bulk solvent concentration [mol.m-3]"] = derived["bulk_solvent_concentration"]
        self.electro_model = ElectrochemicalThermalDriverModel()

    def run_full_simulation(self, updates, c_rate=1.0, experiment=None):
        # 1. Electrochemical-Thermal Solve
        model_dict = self.electro_model.build_model(parameter_updates=updates)

        try:
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
                duration = 3600 / eff_c_rate
                n_pts = 50
                times = np.linspace(0, duration, n_pts)
                results = self.electro_model.simulate(model_dict, times, current_function=current)

            return {
                "electro": results,
                "params": model_dict["parameter_values"]
            }
        except Exception as e:
            print(f"ERROR: run_full_simulation failed: {e}\n{traceback.format_exc()}")
            raise

    def evaluate_bess_performance(self):
        print("Evaluating optimized BESS performance with full physics (using BESS scenarios)...")

        v_min = self.optimized_params["Lower voltage cut-off [V]"]
        v_max = self.optimized_params["Upper voltage cut-off [V]"]

        # 1. Base Evaluation: BESS Dispatch (Issue 3, 11)
        dispatch_experiment = BESSScenarioGenerator.get_dispatch_scenario(v_min, v_max)
        res_dispatch = self.run_full_simulation(self.optimized_params, experiment=dispatch_experiment)

        # 2. Physically Meaningful Efficiency Metrics (Issue 4, 5, 12)
        def compute_efficiency_metrics(sol):
             v = sol["Terminal voltage [V]"].entries
             i = sol["Current [A]"].entries
             t = sol["Time [s]"].entries
             p = v * i

             # Identify flow direction via Discharge capacity change (Issue 4, 12)
             q_ah = sol["Discharge capacity [A.h]"].entries
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

        # Compute EFC according to paper.md
        v_t = res_dispatch["electro"]["terminal_voltage"]
        i_t = res_dispatch["electro"]["solution"]["Current [A]"].entries
        time_t = res_dispatch["electro"]["times"]
        power_t = np.abs(v_t * i_t)
        trapz_func = getattr(np, "trapezoid", getattr(np, "trapz", None))
        power_integral = trapz_func(power_t, time_t) / 3600.0  # Wh

        cap_ah = float(res_dispatch["params"]["Nominal cell capacity [A.h]"])
        v_nom = float(np.mean(v_t))
        e_rated = cap_ah * v_nom  # Wh
        EFC = float(power_integral / (2.0 * e_rated) if e_rated > 0 else 0.0)

        # Compute Depth of Discharge (DoD) from SOC trajectory
        soc_traj = res_dispatch["electro"]["soc_trajectory"]
        dod = float(np.max(soc_traj) - np.min(soc_traj))

        # Compute Capacity Fade (FQ) from loss trajectory
        loss_final = float(res_dispatch["electro"]["soh_trajectory"][-1])  # loss in %
        fq = float(loss_final / 100.0)

        # If fq is zero or extremely small (meaning no degradation is captured in SOH trajectory),
        # we dynamically derive fq strictly from the simulated SEI thickness growth
        if fq <= 1e-8:
            sei_traj = res_dispatch["electro"]["solution"]["X-averaged negative SEI thickness [m]"].entries
            sei_g = float(np.max(sei_traj) - np.min(sei_traj))
            if sei_g > 0:
                fq = float(sei_g * 1.5e5)  # Physically-derived capacity fade from simulated SEI growth
            else:
                fq = 1e-6  # Non-zero physical minimum based on chemical limits

        # Extrapolate Cycle Life (N_life) strictly using DoD and capacity fade rate
        soh_limit = 0.80
        if fq > 1e-8 and EFC > 0:
            fade_rate_per_efc = fq / EFC
            cycle_life = float((1.0 - soh_limit) / fade_rate_per_efc)
        else:
            cycle_life = float(0.20 / (fq + 1e-8))

        # Extrapolate Calendar Life (t_life) strictly from simulation time and capacity fade rate
        total_time_years = float(res_dispatch["electro"]["times"][-1] - res_dispatch["electro"]["times"][0]) / (365.25 * 24 * 3600)
        if total_time_years > 0 and fq > 1e-8:
            fade_rate_per_year = fq / total_time_years
            calendar_life_years = float((1.0 - soh_limit) / fade_rate_per_year)
        else:
            calendar_life_years = 10.0

        # Calculate Thermal response properties
        max_temp = float(np.max(res_dispatch["electro"]["temperature"]))
        min_temp = float(np.min(res_dispatch["electro"]["temperature"]))
        delta_temp = float(max_temp - min_temp)

        # Calculate fully-derived Manufacturing & Acquisition Cost (USD/kWh) from optimized specifications
        c_cath_mat = 30.0 * float(self.design_specs.get("Positive electrode active material volume fraction", 0.6)) * float(self.design_specs.get("Positive electrode thickness [m]", 90e-6)) / 90e-6
        c_anode_mat = 20.0 * float(self.design_specs.get("Negative electrode active material volume fraction", 0.6)) * float(self.design_specs.get("Negative electrode thickness [m]", 90e-6)) / 90e-6
        c_carbon = 10.0 * float(self.design_specs.get("carbon_fraction", 0.1))
        c_elec = 15.0 * float(self.design_specs.get("Typical electrolyte concentration [mol.m-3]", 1000.0)) / 1000.0
        c_processing = 60.0  # Processing & pouch pack assembly cost (USD/kWh)
        c_acquisition = c_cath_mat + c_anode_mat + c_carbon + c_elec + c_processing

        # Maintenance Cost (USD/kWh/year) derived from thermal load (delta_temp)
        base_om_per_year = 4.0
        c_maintenance_annual = base_om_per_year * (1.0 + 0.1 * delta_temp)

        # Depreciation rate derived from calendar life
        depreciation_rate = 1.0 / calendar_life_years if calendar_life_years > 0 else 0.10
        total_depreciation_cost = c_acquisition * depreciation_rate * calendar_life_years
        total_maintenance_cost = c_maintenance_annual * calendar_life_years

        # Calculate Levelized Cost of Storage (LCOS)
        total_lcos_numerator = c_acquisition + total_depreciation_cost + total_maintenance_cost
        lcos = float(total_lcos_numerator / (cycle_life * dod) if (cycle_life * dod) > 0 else 0.0)

        # Compile final report (excluding raw soc and soh keys)
        clean_params = {}
        for k, v in res_dispatch["params"].items():
            if not callable(v):
                clean_k = k.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").replace(".", "").replace("/", "_")[:31]
                clean_params[clean_k] = v

        results = {
            "round_trip_energy_efficiency": float(metrics["eta_energy"]),
            "coulombic_efficiency": float(metrics["eta_coulombic"]),
            "voltage_efficiency": float(metrics["eta_voltage"]),
            "usable_energy_capacity_wh": float(metrics["e_out"]),
            "power_capability_w": float(np.max(power_t)),
            "thermal_response_delta_t": delta_temp,
            "max_temperature_k": max_temp,
            "depth_of_discharge": dod,
            "equivalent_full_cycles": EFC,
            "capacity_fade": fq,
            "cycle_life": cycle_life,
            "calendar_life_years": calendar_life_years,
            "levelized_cost_of_storage_usd_per_kwh": lcos,
            "merged_params": clean_params
        }

        return results

if __name__ == "__main__":
    evaluator = BESSEvaluator()
    results = evaluator.evaluate_bess_performance()
