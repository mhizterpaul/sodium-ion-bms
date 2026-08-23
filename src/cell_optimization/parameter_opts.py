import numpy as np
import pybamm
import json
import os
import traceback
import inspect
import copy
import gc
from collections import OrderedDict
from typing import Dict, Any, List, Tuple, Optional, Callable
from src.cell_optimization.cem_optimizer import CrossEntropyOptimizer, EvaluationResult, PyBaMMSensitivityAnalyzer
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters
from src.simulation.utilities.mechanical.fenics_model import ThermoelasticStrainModel

# --- DESIGN SPACE (θ) ---
DESIGN_SPACE = [
    "Positive electrode thickness [m]",                           # θs - thickness
    "Negative electrode thickness [m]",                           # θs - thickness
    "Positive electrode porosity",                                 # θs - porosity
    "Negative electrode porosity",                                 # θs - porosity
    "Positive particle radius [m]",                               # θs - particle size
    "Negative particle radius [m]",                               # θs - particle size
    "Separator porosity",                                          # θs - porosity
    "Positive electrode active material volume fraction",          # θs - loading
    "Negative electrode active material volume fraction",          # θs - loading
    "Positive electrode Bruggeman coefficient (electrolyte)",      # θs - tortuosity
    "Negative electrode Bruggeman coefficient (electrolyte)",      # θs - tortuosity
    "carbon_fraction",                                             # θm - conductive carbon fraction
    "Typical electrolyte concentration [mol.m-3]"                  # θm - electrolyte composition
]

DESIGN_BOUNDS = np.array([
    [30e-6, 150e-6], [30e-6, 150e-6],                             # Electrode thickness bounds
    [0.2, 0.5], [0.2, 0.5],                                       # Electrode porosity bounds
    [1e-7, 10e-6], [1e-7, 10e-6],                                 # Particle radius bounds
    [0.3, 0.7],                                                    # Separator porosity bounds
    [0.4, 0.8], [0.4, 0.8],                                       # Active material volume fraction bounds
    [1.1, 2.5], [1.1, 2.5],                                       # Bruggeman coefficient (tortuosity) bounds
    [0.02, 0.15],                                                  # Carbon fraction bounds
    [800.0, 1800.0]                                                # Electrolyte concentration bounds
])

# --- WRAPPER CLASSES FOR CALLABLE PARAMETERS ---
class OCPWrapper:
    def __init__(self, base_ocp: Callable, boost: float):
        self.base_ocp = base_ocp
        self.boost = boost
        self.__signature__ = getattr(base_ocp, "__signature__", None)
    def __call__(self, sto, *args, **kwargs):
        val = self.base_ocp(sto, *args, **kwargs)
        return val + self.boost

class MultiplicativeWrapper:
    def __init__(self, base_func: Callable, factor: float):
        self.base_func = base_func
        self.factor = factor
        self.__signature__ = getattr(base_func, "__signature__", None)
    def __call__(self, *args, **kwargs):
        return self.base_func(*args, **kwargs) * self.factor

class VolumeChangeModel:
    def __init__(self, factor=0.1):
        self.factor = factor
        self.__signature__ = inspect.signature(self.__call__)
    def __call__(self, sto):
        return self.factor * sto

# --- PHYSICS MODELS ---
def carbon_percolation_conductivity(fraction: float, base_cond: float = 100.0) -> float:
    phi_c = 0.03
    return base_cond * (max(fraction - phi_c, 0.0) + 1e-6) ** 1.8

def validate_params(pv: Dict[str, Any], verbose: bool = False) -> bool:
    if "Positive particle diffusivity [m2.s-1]" in pv:
        D_p = pv["Positive particle diffusivity [m2.s-1]"]
        D_val = D_p(0.5, 298.15) if callable(D_p) else D_p
        if D_val > 1e-8:
            if verbose: print(f"DEBUG: validate_params failed: D_p > 1e-8 ({D_val})")
            return False

    for p in ["Positive electrode porosity", "Negative electrode porosity", "Separator porosity"]:
        if p in pv:
            val = pv[p]
            if val <= 0.1 or val >= 0.6:
                if verbose: print(f"DEBUG: validate_params failed: {p} = {val} out of bounds (0.1, 0.6)")
                return False

    for r in ["Positive particle radius [m]", "Negative particle radius [m]"]:
        if r in pv:
            val = pv[r]
            if val <= 1e-8 or val >= 20e-6:
                if verbose: print(f"DEBUG: validate_params failed: {r} = {val} out of bounds")
                return False

    for t in ["Positive electrode thickness [m]", "Negative electrode thickness [m]", "Separator thickness [m]"]:
        if t in pv:
            val = pv[t]
            if val <= 10e-6 or val >= 300e-6:
                if verbose: print(f"DEBUG: validate_params failed: {t} = {val} out of bounds")
                return False

    for am in ["Positive electrode active material volume fraction", "Negative electrode active material volume fraction"]:
        if am in pv:
            val = pv[am]
            if val <= 0.0 or val >= 0.9:
                if verbose: print(f"DEBUG: validate_params failed: {am} = {val} out of bounds")
                return False

    for domain in ["Positive", "Negative"]:
        por_key = f"{domain} electrode porosity"
        am_key = f"{domain} electrode active material volume fraction"
        if por_key in pv and am_key in pv:
            por = pv[por_key]
            am = pv[am_key]
            carb = pv.get("carbon_fraction", 0.05)
            if (por + am + carb) >= 0.98:
                if verbose: print(f"DEBUG: validate_params failed: {domain} total fraction exceeds 1.0 (porosity={por}, AM={am}, carbon={carb})")
                return False

    return True

class ParamTransform:
    def __init__(
        self,
        base_values: Optional[Dict[str, Any]] = None,
        derived: Optional[Dict[str, Any]] = None,
    ):
        self.values_dict = copy.deepcopy(
            dict(base_values) if base_values is not None else dict(get_parameter_values())
        )
        self.derived = derived if derived is not None else get_derived_parameters()
        self.scaling_factors = {}

    def _apply_scaling(self, key: str, factor: float):
        self.scaling_factors[key] = self.scaling_factors.get(key, 1.0) * factor

    def apply_physics_deltas(self, deltas: Dict[str, Any]):
        if "thermodynamic" in deltas:
            d = deltas["thermodynamic"]
            if "voltage_boost" in d:
                ocp = self.values_dict.get("Positive electrode OCP [V]")
                boost = d["voltage_boost"]
                if callable(ocp):
                    self.values_dict["Positive electrode OCP [V]"] = OCPWrapper(ocp, boost)
                else:
                    self.values_dict["Positive electrode OCP [V]"] += boost
                for cut_off in ["Lower voltage cut-off [V]", "Upper voltage cut-off [V]"]:
                    if cut_off in self.values_dict:
                        self.values_dict[cut_off] += boost
            if "initial_sodium_loss_delta" in d:
                self._apply_scaling("Initial concentration in negative electrode [mol.m-3]", (1.0 + d["initial_sodium_loss_delta"]))
            if "stability_shift" in d:
                 self._apply_scaling("SEI reaction exchange current density [A.m-2]", np.exp(-d["stability_shift"]))
                 self._apply_scaling("Positive electrode LAM constant proportional term [s-1]", np.exp(-d["stability_shift"]))

        if "transport" in deltas:
            d = deltas["transport"]
            if "diffusivity_log_delta" in d:
                self._apply_scaling("Positive particle diffusivity [m2.s-1]", np.exp(d["diffusivity_log_delta"]))
            if "conductivity_log_delta" in d:
                self._apply_scaling("Positive electrode conductivity [S.m-1]", np.exp(d["conductivity_log_delta"]))
            if "electrolyte_conductivity_log_delta" in d:
                self._apply_scaling("Electrolyte conductivity [S.m-1]", np.exp(d["electrolyte_conductivity_log_delta"]))
            if "electrolyte_diffusivity_log_delta" in d:
                self._apply_scaling("Electrolyte diffusivity [m2.s-1]", np.exp(d["electrolyte_diffusivity_log_delta"]))

        if "kinetic" in deltas:
            d = deltas["kinetic"]
            if "exchange_current_log_delta" in d:
                self._apply_scaling("Positive electrode exchange-current density [A.m-2]", np.exp(d["exchange_current_log_delta"]))
                self._apply_scaling("Negative electrode exchange-current density [A.m-2]", np.exp(d["exchange_current_log_delta"]))
            if "sei_growth_log_delta" in d:
                self._apply_scaling("SEI reaction exchange current density [A.m-2]", np.exp(d["sei_growth_log_delta"]))
            if "sei_resistivity_log_delta" in d:
                self._apply_scaling("SEI resistivity [Ohm.m]", np.exp(d["sei_resistivity_log_delta"]))

        if "mechanical" in deltas:
             d = deltas["mechanical"]
             if "modulus_degradation_factor" in d:
                  self._apply_scaling("Negative electrode Young's modulus [Pa]", d["modulus_degradation_factor"])

    def apply_design_vector(self, x: np.ndarray, names: List[str]):
        for val, name in zip(x, names):
            if name == "carbon_fraction":
                self.values_dict["Positive electrode conductivity [S.m-1]"] = carbon_percolation_conductivity(val)
            elif name.endswith("porosity"):
                 eps = val
                 tau = eps ** (-0.5)
                 self.values_dict[name] = val
                 if name == "Separator porosity" and "Electrolyte conductivity [S.m-1]" in self.values_dict:
                      self._apply_scaling("Electrolyte conductivity [S.m-1]", (eps / tau) ** 1.5)
            else:
                self.values_dict[name] = val

    def get_parameter_values(self) -> pybamm.ParameterValues:
        derived = self.derived
        c_max_p = self.values_dict.get("Maximum concentration in positive electrode [mol.m-3]", derived["c_max_p"])
        c_max_n = self.values_dict.get("Maximum concentration in negative electrode [mol.m-3]", derived["c_max_n"])
        self.values_dict["Initial concentration in positive electrode [mol.m-3]"] = 0.5 * c_max_p
        self.values_dict["Initial concentration in negative electrode [mol.m-3]"] = 0.5 * c_max_n
        self.values_dict["Lower voltage cut-off [V]"] = 0.5
        self.values_dict["Upper voltage cut-off [V]"] = 4.5

        for key, factor in self.scaling_factors.items():
            original = self.values_dict.get(key)
            if original is None: continue
            if callable(original):
                self.values_dict[key] = MultiplicativeWrapper(original, factor)
            else:
                self.values_dict[key] *= factor

        return pybamm.ParameterValues(self.values_dict)

class SimulationRunner:
    def __init__(self, model, solver_class, solver_kwargs):
        self.model = model
        self.solver_class = solver_class
        self.solver_kwargs = solver_kwargs

    def run_simulation(self, params: pybamm.ParameterValues, c_rate: float = 1.0) -> Dict[str, Any]:
        try:
            sim = pybamm.Simulation(
                self.model,
                parameter_values=params,
                solver=self.solver_class(**self.solver_kwargs)
            )
            sol = sim.solve([0, 3600], inputs={"Current [A]": params["Nominal cell capacity [A.h]"] * c_rate})
            return {"sol": sol, "success": True}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def clear_memory(self):
        import sys
        import shutil
        from pathlib import Path
        shutil.rmtree(Path.home() / ".cache" / "pybamm", ignore_errors=True)
        for module_name, module in list(sys.modules.items()):
            if module_name.startswith("pybamm"):
                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name)
                        if hasattr(attr, "cache_clear") and callable(attr.cache_clear):
                            attr.cache_clear()
                        elif hasattr(attr, "clear_cache") and callable(attr.clear_cache):
                            attr.clear_cache()
                    except Exception:
                        pass
        gc.collect()

def post_process_sol(res: Dict[str, Any], return_sol: bool = False) -> Dict[str, Any]:
    if not res["success"]:
        return res
    try:
        sol = res["sol"]
        v, curr, t = sol["Terminal voltage [V]"].entries, sol["Current [A]"].entries, sol["Time [s]"].entries
        trapz_func = getattr(np, "trapezoid", getattr(np, "trapz", None))
        energy_wh = abs(trapz_func(v * curr, t)) / 3600
        power_vals = np.abs(v * curr)
        energy = float(energy_wh)
        power = np.max(power_vals)
        T_max = np.max(sol["Cell temperature [K]"].entries)
        stresses = []
        for sv in ["Positive particle surface tangential stress [Pa]", "Negative particle surface tangential stress [Pa]"]:
             try: stresses.append(np.max(np.abs(sol[sv].entries)))
             except (KeyError, pybamm.ModelError, AttributeError): pass
        max_stress = np.max(stresses) if stresses else 0.0
        final_res = {"energy": float(energy), "power": float(power), "T_max": float(T_max), "stress": float(max_stress), "stresses": stresses, "success": True}
        if return_sol: final_res["sol"] = sol
        return final_res
    except Exception as e:
        return {"success": False, "reason": f"Post-simulation processing failed: {e}"}

class HierarchicalOptimizer:
    def __init__(self, engine: Optional[Any] = None, base_params: Optional[pybamm.ParameterValues] = None):
        self.engine = engine
        self.base_params = base_params or pybamm.ParameterValues(get_parameter_values())
        self.base_values = dict(self.base_params)
        self.derived = get_derived_parameters()
        options = {"SEI": "solvent-diffusion limited", "loss of active material": "stress-driven", "thermal": "lumped"}
        try:
            self.model = pybamm.sodium_ion.DFN(options)
        except AttributeError:
            self.model = pybamm.lithium_ion.DFN(options)
        self.solver_kwargs = {"rtol": 1e-7, "atol": 1e-9, "options": {"dt_max": 5.0}}
        self.runner = SimulationRunner(self.model, pybamm.IDAKLUSolver, self.solver_kwargs)
        self.mech_model = ThermoelasticStrainModel()

    def simulate(self, params: pybamm.ParameterValues, c_rate: float = 1.0) -> Dict[str, Any]:
        raw_res = self.runner.run_simulation(params, c_rate=c_rate)
        return post_process_sol(raw_res, return_sol=True)

    def evaluate_stability_pde(self, sol: Any, params: pybamm.ParameterValues, c_rate: float = 1.0) -> Tuple[bool, float]:
        try:
            mech_res = self.mech_model.solve_strain(sol, params, c_rate=c_rate)
            max_strain = mech_res["max_strain"]
            mat_key = "NFPP" if "NFPP" in self.mech_model.critical_thresholds else list(self.mech_model.critical_thresholds.keys())[0]
            critical_strain = self.mech_model.critical_thresholds.get(mat_key, 2e-3)
            eta = max_strain / critical_strain
            eta_threshold = float(os.environ.get("CEM_ETA_THRESHOLD", 1.8))
            is_feasible = (eta <= eta_threshold)
            g_mech = (eta / eta_threshold) - 1.0
            return is_feasible, g_mech
        except Exception as e:
            print(f"ERROR: FEM solve failed: {e}\n{traceback.format_exc()}")
            return False, 1e3

    def evaluate_candidate_robustness(self, best_x: np.ndarray, deltas: Dict[str, Any], num_samples: int = 5, delta_rel: float = 0.02) -> Dict[str, float]:
        scores = []
        violations = []

        pt_base = ParamTransform(base_values=self.base_values, derived=self.derived)
        pt_base.apply_physics_deltas(deltas)
        pt_base.apply_design_vector(best_x, DESIGN_SPACE)
        res_nom = self.simulate(pt_base.get_parameter_values())

        if not res_nom["success"]:
            return {"E_energy": 0.0, "Var_energy": 0.0, "P_instability": 1.0}

        scores.append(res_nom["energy"])
        violations.append(0.0)

        for _ in range(num_samples):
            perturbation = np.random.uniform(-delta_rel, delta_rel, size=len(best_x))
            x_pert = best_x * (1.0 + perturbation)
            x_pert = np.clip(x_pert, DESIGN_BOUNDS[:, 0], DESIGN_BOUNDS[:, 1])

            pt = ParamTransform(base_values=self.base_values, derived=self.derived)
            pt.apply_physics_deltas(deltas)
            pt.apply_design_vector(x_pert, DESIGN_SPACE)
            res_pert = self.simulate(pt.get_parameter_values())

            if res_pert["success"]:
                scores.append(res_pert["energy"])
                is_feasible, g_mech = self.evaluate_stability_pde(res_pert["sol"], pt.get_parameter_values())
                violations.append(1.0 if not is_feasible else 0.0)
            else:
                violations.append(1.0)

        return {
            "E_energy": float(np.mean(scores)),
            "Var_energy": float(np.var(scores)),
            "P_instability": float(np.mean(violations))
        }

    def run(self) -> Dict[str, Any]:
        return run_workflow(engine=self.engine)

def geometry_rounding(x: np.ndarray) -> np.ndarray:
    x_rounded = x.copy()
    for idx, val in enumerate(x_rounded):
        if idx in [0, 1]:
            x_rounded[idx] = np.round(val * 1e6) / 1e6
        elif idx in [4, 5]:
            x_rounded[idx] = np.round(val * 1e8) / 1e8
    return x_rounded

def run_workflow(engine: Optional[Any] = None):
    optimizer = None
    final_opt_designs = None
    candidate_metrics = None

    try:
        from src.cell_optimization.material_opt import MaterialMappingEngine, MaterialCategory
        if engine is None: engine = MaterialMappingEngine()
        db, bases = engine.run()
        if not bases:
            print("ERROR: Hierarchical optimization aborted: Base material resolution failed.")
            raise RuntimeError("Base material resolution failed.")
        from src.cell_optimization.chem_regularization import derive_coupled_deltas, regularize_salt_props

        print("\n" + "="*120)
        print(f"{'MATERIAL JUXTAPOSITION & DERIVED CELL PARAMETER DELTAS':^120s}")
        print("="*120)

        # 1. Layer 1: Material Selection Stage (Dopant & Salt selection purely from OQMD / QM props)
        print(f"\nLAYER 1: PARALLEL DOPANT OPTIMIZATION")
        print(f"{'Candidate':25s} | {'QM: Form E':12s} | {'QM: Volume':12s} | {'Derived Delta Key':40s} | {'Value':12s}")
        print("-" * 120)
        best_dopant = None
        best_dopant_score = -1e9
        for cand in db[MaterialCategory.CATHODE_DOPANT]:
            cand.deltas = derive_coupled_deltas(bases["cathode"]["properties"], cand.properties, bases["cathode"]["formula"], cand.composition)
            p, d = cand.properties, cand.deltas
            flat = [(k, v) for gn, gv in d.items() for k, v in gv.items()]
            for i, (k, v) in enumerate(flat):
                if i == 0: print(f"{cand.name:25s} | {p.get('formation_energy', 0.0):12.4f} | {p.get('volume_per_atom', 0.0):12.4f} | {k:40s} | {v:+.4e}")
                else: print(f"{'':25s} | {'':12s} | {'':12s} | {k:40s} | {v:+.4e}")

            # Scoring based strictly on OQMD-derived property deltas
            voltage_boost = d.get("thermodynamic", {}).get("voltage_boost", 0.0)
            diffusivity_log_delta = d.get("transport", {}).get("diffusivity_log_delta", 0.0)
            conductivity_log_delta = d.get("transport", {}).get("conductivity_log_delta", 0.0)
            exchange_current_log_delta = d.get("kinetic", {}).get("exchange_current_log_delta", 0.0)
            stability_shift = d.get("thermodynamic", {}).get("stability_shift", 0.0)

            score = (voltage_boost * 10.0 +
                     diffusivity_log_delta * 2.0 +
                     conductivity_log_delta * 1.0 +
                     exchange_current_log_delta * 2.0 +
                     stability_shift * 5.0)
            cand.score = score
            if score > best_dopant_score:
                best_dopant_score = score
                best_dopant = cand

        print(f"\nLAYER 1: PARALLEL SALT OPTIMIZATION")
        print(f"{'Candidate':25s} | {'QM: Form E':12s} | {'QM: Volume':12s} | {'Derived Delta Key':40s} | {'Value':12s}")
        print("-" * 120)
        best_salt = None
        best_salt_score = -1e9
        for cand in db[MaterialCategory.SALT]:
            cand.deltas = regularize_salt_props(bases["salt"]["formula"], cand.composition, bases["salt"]["properties"], cand.properties)
            p, d = cand.properties, cand.deltas
            flat = [(k, v) for gn, gv in d.items() for k, v in gv.items()]
            for i, (k, v) in enumerate(flat):
                if i == 0: print(f"{cand.name:25s} | {p.get('formation_energy', 0.0):12.4f} | {p.get('volume_per_atom', 0.0):12.4f} | {k:40s} | {v:+.4e}")
                else: print(f"{'':25s} | {'':12s} | {'':12s} | {k:40s} | {v:+.4e}")

            electrolyte_conductivity_log_delta = d.get("transport", {}).get("electrolyte_conductivity_log_delta", 0.0)
            electrolyte_diffusivity_log_delta = d.get("transport", {}).get("electrolyte_diffusivity_log_delta", 0.0)

            score = (electrolyte_conductivity_log_delta * 5.0 +
                     electrolyte_diffusivity_log_delta * 2.0)
            cand.score = score
            if score > best_salt_score:
                best_salt_score = score
                best_salt = cand
        print("="*120 + "\n")

        optimizer = HierarchicalOptimizer(engine=engine)
        deltas = {}
        if best_dopant and best_dopant.deltas:
            for g_name, props in best_dopant.deltas.items():
                deltas.setdefault(g_name, {}).update(props)
        if best_salt and best_salt.deltas:
            for g_name, props in best_salt.deltas.items():
                deltas.setdefault(g_name, {}).update(props)

        print(f"--> SELECTED OPTIMAL DOPANT: {best_dopant.name} (Score: {best_dopant.score:.4f})")
        print(f"--> SELECTED OPTIMAL SALT:   {best_salt.name} (Score: {best_salt.score:.4f})")
        print("CONSTRUCTING OPTIMIZED BASE CELL...")

        x_base = np.array([np.mean(b) for b in DESIGN_BOUNDS])

        print("\nSTAGE 2: PARAMETER CO-OPTIMIZATION (SEQUENTIAL OBJECTIVES)")
        MAT_INDICES = [11, 12]
        STRUCT_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        modes = ["energy", "power", "thermal_stability", "stability"]

        pop_size = int(os.environ.get("CEM_POP_SIZE", "8"))
        iterations = int(os.environ.get("CEM_ITERATIONS", "2"))
        cem = CrossEntropyOptimizer(population_size=pop_size, iterations=iterations)

        final_opt_designs = []

        for mode in modes:
            print(f"\n---> Optimizing objective mode: {mode.upper()}")

            def pybamm_evaluator(x_full: np.ndarray) -> EvaluationResult:
                pt = ParamTransform(base_values=optimizer.base_values, derived=optimizer.derived)
                pt.apply_physics_deltas(deltas)
                pt.apply_design_vector(x_full, DESIGN_SPACE)
                pv = pt.get_parameter_values()

                if not validate_params(dict(pv)):
                    return EvaluationResult(objective=np.array([1e9, 1e9, 1e9, 1e9]), constraints=[1.0], feasible=False)

                res = optimizer.simulate(pv)
                if not res["success"]:
                    return EvaluationResult(objective=np.array([1e9, 1e9, 1e9, 1e9]), constraints=[1.0], feasible=False)

                is_feasible, g_mech = optimizer.evaluate_stability_pde(res["sol"], pv)

                # Return full vector objective F(theta) = [-E, -P, T_max, stress]
                f_vector = np.array([
                    -res["energy"],
                    -res["power"],
                    res["T_max"],
                    res["stress"]
                ])

                return EvaluationResult(objective=f_vector, constraints=[g_mech], feasible=is_feasible, metrics=res)

            # Calculate PyBaMM sensitivity via PyBaMMSensitivityAnalyzer
            sensitivity_analyzer = PyBaMMSensitivityAnalyzer(pybamm_evaluator)

            # --- STEP 1: Material parameters optimization (indices 11, 12) ---
            print(f"  Step 1: Material parameters optimization ({[DESIGN_SPACE[i] for i in MAT_INDICES]})...")
            sens_mat = sensitivity_analyzer.jacobian(x_base, DESIGN_BOUNDS, active_indices=MAT_INDICES)
            x_mat_opt = cem.optimize(
                evaluator_func=pybamm_evaluator,
                x0=x_base.copy(),
                bounds=DESIGN_BOUNDS,
                sensitivity=sens_mat,
                active_indices=MAT_INDICES,
                rounding_func=geometry_rounding,
                verbose=False
            )

            # CLEAR MEMORY BETWEEN STEP 1 AND STEP 2
            print("  [CLEARING MEMORY BETWEEN STEP 1 (MATERIAL OPTS) AND STEP 2 (STRUCTURAL OPTS)...]")
            optimizer.runner.clear_memory()

            # --- STEP 2: Structural parameters optimization (indices 0..10) ---
            print(f"  Step 2: Structural parameters optimization ({len(STRUCT_INDICES)} variables)...")
            sens_struct = sensitivity_analyzer.jacobian(x_mat_opt, DESIGN_BOUNDS, active_indices=STRUCT_INDICES)
            x_struct_opt = cem.optimize(
                evaluator_func=pybamm_evaluator,
                x0=x_mat_opt,
                bounds=DESIGN_BOUNDS,
                sensitivity=sens_struct,
                active_indices=STRUCT_INDICES,
                rounding_func=geometry_rounding,
                verbose=False
            )

            final_opt_designs.append(x_struct_opt)
            optimizer.runner.clear_memory()

        print("\nRUNNING PARETO FRONT FILTERING...")
        candidate_metrics = []
        for x in final_opt_designs:
            pt = ParamTransform(base_values=optimizer.base_values, derived=optimizer.derived)
            pt.apply_physics_deltas(deltas)
            pt.apply_design_vector(x, DESIGN_SPACE)
            res = optimizer.simulate(pt.get_parameter_values())
            if res["success"]:
                candidate_metrics.append((x, res))

        if not candidate_metrics:
            raise RuntimeError("No optimized parameter designs succeeded in DFN simulation.")

        ens = [r["energy"] for _, r in candidate_metrics]
        pws = [r["power"] for _, r in candidate_metrics]
        tms = [r["T_max"] for _, r in candidate_metrics]

        min_en, max_en = min(ens), max(ens)
        min_pw, max_pw = min(pws), max(pws)
        min_tm, max_tm = min(tms), max(tms)

        def utility(res):
            en_norm = (res["energy"] - min_en) / (max_en - min_en + 1e-12)
            pw_norm = (res["power"] - min_pw) / (max_pw - min_pw + 1e-12)
            tm_norm = (max_tm - res["T_max"]) / (max_tm - min_tm + 1e-12)
            return 0.4 * en_norm + 0.4 * pw_norm + 0.2 * tm_norm

        ranked_candidates = sorted(candidate_metrics, key=lambda c: utility(c[1]), reverse=True)
        best_candidate_design, best_metrics = ranked_candidates[0]

        # Post-optimization Candidate Robustness Evaluation in parameter_opts.py
        print("\nEVALUATING FINAL CANDIDATE ROBUSTNESS...")
        robustness = optimizer.evaluate_candidate_robustness(best_candidate_design, deltas)
        print(f"  Robustness Metrics: E[Energy]={robustness['E_energy']:.4f} Wh, Var[Energy]={robustness['Var_energy']:.6e}, P[Instability]={robustness['P_instability']:.2%}")

        groups = {"Energy": [], "Power": [], "Thermal Stability": [], "Stability": [], "Coupled": []}

        output = {
            "materials": {
                "cathode": {"name": best_dopant.name, "formula": best_dopant.composition, "properties": best_dopant.properties},
                "electrolyte": {"salt": best_salt.name, "properties": best_salt.properties}
            },
            "bases": bases,
            "design_specs_representative": dict(zip(DESIGN_SPACE, best_candidate_design.tolist())),
            "opt_designs_per_objective": {
                mode: dict(zip(DESIGN_SPACE, design.tolist()))
                for mode, design in zip(modes, final_opt_designs)
            },
            "combined_deltas_representative": deltas,
            "robustness": robustness,
            "parameter_grouping": groups
        }
        with open("result.json", "w") as f: json.dump(output, f, indent=2)

        print("\n" + "="*80)
        print(f"{'HIERARCHICAL CO-OPTIMIZATION WORKFLOW COMPLETE':^80s}")
        print("="*80)
        print("\nCHEMISTRY SELECTION (LAYER 1 - QM & ANALYTICAL SCORING):")
        print("-" * 80)
        print(f"  Selected Cathode Dopant: {best_dopant.name} ({best_dopant.composition})")
        print(f"    Analytical Score:      {best_dopant.score:.4f}")
        print(f"  Selected Electrolyte Salt: {best_salt.name} ({best_salt.composition})")
        print(f"    Analytical Score:      {best_salt.score:.4f}")

        print("\nDESIGN VARIABLES OPTIMIZATION (STAGE 2):")
        print("-" * 80)
        print("  Structural Parameters (θs) Optimized:")
        for k, v in output['design_specs_representative'].items():
            if k not in ["carbon_fraction", "Typical electrolyte concentration [mol.m-3]"]:
                print(f"    {k:40s}: {v:12.6e}")

        print("  Material Parameters (θm) Optimized:")
        for k, v in output['design_specs_representative'].items():
            if k in ["carbon_fraction", "Typical electrolyte concentration [mol.m-3]"]:
                print(f"    {k:40s}: {v:12.6e}")
        print("="*80 + "\n")
        return output
    finally:
        print("\nCLEANUP: Releasing optimization memory...")
        if optimizer is not None:
            try: optimizer.runner.clear_memory()
            except Exception as e: print(f"WARNING: Runner cleanup failed: {e}")
        del final_opt_designs
        del candidate_metrics
        del optimizer
        gc.collect()
        print("CLEANUP: Memory release completed.")

if __name__ == "__main__":
    optimizer = None
    try:
        optimizer = HierarchicalOptimizer()
        optimizer.run()
    finally:
        if optimizer is not None:
            try: optimizer.runner.clear_memory()
            except Exception: pass
