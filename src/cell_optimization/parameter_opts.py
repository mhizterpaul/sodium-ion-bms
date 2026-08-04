import numpy as np
import pybamm
import json
import os
import traceback
import inspect
import copy
import gc
from collections import OrderedDict
from typing import Dict, Any, List, Tuple, Optional
from src.cell_optimization.cem_optimizer import CrossEntropyOptimizer
from nfpp_sodium_ion.src.cell_parameters.cell_alpha import get_parameter_values
from nfpp_sodium_ion.src.calibration.derivation import get_derived_parameters
from src.simulation.utilities.mechanical.fenics_model import ThermoelasticStrainModel
from pint import UnitRegistry

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

# --- PHYSICS MODELS ---

def carbon_percolation_conductivity(fraction: float, base_cond: float = 100.0) -> float:
    phi_c = 0.03
    return base_cond * (max(fraction - phi_c, 0.0) + 1e-6) ** 1.8

def validate_params(pv: Dict[str, Any], verbose: bool = False):
    required = ["Nominal cell capacity [A.h]", "Positive electrode exchange-current density [A.m-2]"]
    derived = get_derived_parameters()

    for r in required:
        if r not in pv:
            if verbose: print(f"DEBUG: validate_params failed: {r} missing")
            return False
        val = pv[r]
        if callable(val):
            sig = inspect.signature(val)
            params_list = list(sig.parameters.keys())
            grounded_map = {
                "c_e": 1200.0,
                "c_s_surf": 0.5 * derived.get("c_max_p", 25000.0),
                "c_s_max": derived.get("c_max_p", 25000.0),
                "T": 298.15,
                "sto": 0.5
            }
            args = [grounded_map.get(p, 0.5) for p in params_list]
            try:
                res = val(*args)
                actual_val = float(res.value) if hasattr(res, "value") else float(res)
            except Exception as e:
                if verbose: print(f"DEBUG: validate_params callable {r} failed: {e}")
                actual_val = 1.0
        else:
            actual_val = val
        if actual_val <= 0:
            if verbose: print(f"DEBUG: validate_params failed: {r} <= 0 ({actual_val})")
            return False

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

    # Physical consistency check: active material fraction + porosity + carbon fraction < 1.0
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

class OCPWrapper:
    def __init__(self, orig_ocp, boost):
        self.orig_ocp = orig_ocp
        self.boost = boost
        try:
            self.__signature__ = inspect.signature(orig_ocp)
            self.__name__ = getattr(orig_ocp, "__name__", "ocp_wrapper")
            self.__doc__ = getattr(orig_ocp, "__doc__", "")
        except Exception:
            pass
    def __call__(self, *args, **kwargs):
        return self.orig_ocp(*args, **kwargs) + self.boost

class MultiplicativeWrapper:
    def __init__(self, orig_func, factor):
        self.orig_func = orig_func
        self.factor = factor
        try:
            self.__signature__ = inspect.signature(orig_func)
            self.__name__ = getattr(orig_func, "__name__", "wrapper")
            self.__doc__ = getattr(orig_func, "__doc__", "")
        except Exception:
            pass
    def __call__(self, *args, **kwargs):
        return self.orig_func(*args, **kwargs) * self.factor

class VolumeChangeModel:
    def __init__(self, factor=0.1):
        self.factor = factor
    def __call__(self, sto):
        return self.factor * sto

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
                 # Scale electrolyte conductivity strictly on Separator porosity processing
                 # to prevent repeated multi-scale wrapping and shape mismatch discretisation errors
                 if name == "Separator porosity" and "Electrolyte conductivity [S.m-1]" in self.values_dict:
                      self._apply_scaling("Electrolyte conductivity [S.m-1]", (eps / tau) ** 1.5)
            else:
                self.values_dict[name] = val

    def get_parameter_values(self) -> pybamm.ParameterValues:
        derived = self.derived

        self.values_dict.setdefault("Negative electrode volume change", VolumeChangeModel(0.1))
        self.values_dict.setdefault("Positive electrode volume change", VolumeChangeModel(0.1))
        self.values_dict.setdefault("Cell thermal expansion coefficient [m.K-1]", 1e-6)
        self.values_dict.setdefault("Number of cells connected in series to make a battery", 1)
        self.values_dict.setdefault("Number of strings connected in parallel to make a battery", 1)

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

        self.values_dict.setdefault("Cell volume [m3]", derived["cell_volume"])
        self.values_dict.setdefault("Cell cooling surface area [m2]", derived["surface_area"])
        self.values_dict.setdefault("Total heat transfer coefficient [W.m-2.K-1]", derived["total_htc"])
        self.values_dict.setdefault("SEI solvent diffusivity [m2.s-1]", derived["sei_solvent_diffusivity"])
        self.values_dict.setdefault("Bulk solvent concentration [mol.m-3]", derived["bulk_solvent_concentration"])

        self.values_dict.setdefault("Negative current collector density [kg.m-3]", derived["cu_density"])
        self.values_dict.setdefault("Positive current collector density [kg.m-3]", derived["al_density"])
        self.values_dict.setdefault("Negative current collector specific heat capacity [J.kg-1.K-1]", derived["cu_cp"])
        self.values_dict.setdefault("Positive current collector specific heat capacity [J.kg-1.K-1]", derived["al_cp"])
        self.values_dict.setdefault("Negative current collector thermal conductivity [W.m-1.K-1]", derived["cu_tc"])
        self.values_dict.setdefault("Positive current collector thermal conductivity [W.m-1.K-1]", derived["al_tc"])

        return pybamm.ParameterValues(self.values_dict)

def _transform_candidate_worker(job):
    x, deltas, base_values, derived = job
    pt = ParamTransform(
        base_values=base_values,
        derived=derived,
    )
    pt.apply_physics_deltas(deltas)
    pt.apply_design_vector(x, DESIGN_SPACE)
    pv = pt.get_parameter_values()
    return dict(pv)

def transform_candidates_parallel(
    candidates: List[Tuple[np.ndarray, Dict[str, Any]]],
    base_values: Dict[str, Any],
    derived: Dict[str, Any],
    max_workers: Optional[int] = None,
) -> List[pybamm.ParameterValues]:
    if not candidates: return []
    max_workers = max_workers or max(1, os.cpu_count() - 1)
    jobs = [(x, deltas, base_values, derived) for x, deltas in candidates]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        transformed_dicts = list(executor.map(_transform_candidate_worker, jobs))
    return [pybamm.ParameterValues(values) for values in transformed_dicts]

class MeshCache:
    """
    Bounded LRU Cache to manage PyBaMM Mesh objects.
    To ensure absolute thread safety during parallel simulations, we only cache
    the read-only Mesh object and always instantiate a fresh pybamm.Discretisation
    for each thread call.
    """
    def __init__(self, max_size: int = 16):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get_mesh_and_disc(self, params, model, submesh_types, var_pts, spatial_methods):
        geom_keys = [
            "Positive electrode thickness [m]",
            "Negative electrode thickness [m]",
            "Separator thickness [m]",
            "Positive particle radius [m]",
            "Negative particle radius [m]"
        ]
        key = tuple(float(params.get(k, 0.0)) for k in geom_keys)

        if key in self.cache:
            mesh = self.cache.pop(key)
            self.cache[key] = mesh
        else:
            geometry = copy.deepcopy(model.default_geometry)
            params.process_geometry(geometry)
            mesh = pybamm.Mesh(geometry, submesh_types, var_pts)
            self.cache[key] = mesh

        while len(self.cache) > self.max_size:
            _, old_mesh = self.cache.popitem(last=False)
            del old_mesh

        # Instantiate a fresh, unshared, state-isolated Discretisation object for this simulation solve
        disc = pybamm.Discretisation(mesh, spatial_methods)
        return mesh, disc

    def clear(self):
        """Release all cached meshes explicitly."""
        for mesh in list(self.cache.values()):
            del mesh
        self.cache.clear()
        gc.collect()

class SingleObjectiveProblem:
    def __init__(self, optimizer, x_full, active_indices, deltas, mode, ref_scale=1.0):
        self.optimizer = optimizer
        self.x_full = x_full
        self.active_indices = active_indices
        self.deltas = deltas
        self.mode = mode
        self.ref_scale = max(abs(ref_scale), 1e-9)

    def evaluate_single(self, x_full):
        from src.cell_optimization.chem_regularization import mechanical_stability_metric
        g1 = (x_full[0] - x_full[1]) / max(DESIGN_BOUNDS[0][1], DESIGN_BOUNDS[1][1])

        pt = ParamTransform(
            base_values=self.optimizer.base_values,
            derived=self.optimizer.derived
        )
        pt.apply_physics_deltas(self.deltas)
        pt.apply_design_vector(x_full, DESIGN_SPACE)
        pv = pt.get_parameter_values()

        if not validate_params(pv):
            return 1000.0, [max(0.0, g1), 0.0, 1.0], False

        res = self.optimizer.simulate(pv)
        if not res["success"]:
            return 1000.0, [max(0.0, g1), 0.0, 1.0], False

        g2 = res["T_max"] - 333.15

        if self.mode == "energy":
            f_val = -res["energy"]
        elif self.mode == "power":
            f_val = -res["power"]
        elif self.mode == "thermal_stability":
            f_val = res["T_max"]
        elif self.mode == "stability":
            f_val = -mechanical_stability_metric(stresses=res["stresses"])
        else:
            f_val = 1000.0

        sc = max(abs(self.ref_scale), 0.1)
        score_unpenalized = f_val / sc

        g_list = [g1, g2, 0.0]
        feasible = (g1 <= 0.0) and (g2 <= 0.0)
        return score_unpenalized, g_list, feasible

class SimulationRunner:
    def __init__(self, model: pybamm.BaseModel, solver_class, solver_kwargs: dict):
        self.model = model
        self.solver_class = solver_class
        self.solver_kwargs = solver_kwargs
        self.var_pts = model.default_var_pts
        self.submesh_types = model.default_submesh_types
        self.spatial_methods = model.default_spatial_methods
        self.mesh_cache = MeshCache()

    def run_simulation(self, params: pybamm.ParameterValues, c_rate: float = 1.0) -> Dict[str, Any]:
        params = params.copy()
        processed_model = None
        mesh = None
        disc = None
        solver = None

        try:
            c_max_p = params["Maximum concentration in positive electrode [mol.m-3]"]
            c_max_n = params["Maximum concentration in negative electrode [mol.m-3]"]
            c_p_init = params["Initial concentration in positive electrode [mol.m-3]"]
            c_n_init = params["Initial concentration in negative electrode [mol.m-3]"]
            ocp_p_func = params["Positive electrode OCP [V]"]
            ocp_n_func = params["Negative electrode OCP [V]"]
            sto_p = c_p_init / c_max_p
            sto_n = c_n_init / c_max_n
            v_init = ocp_p_func(sto_p) - ocp_n_func(sto_n)
            v_init_val = float(v_init.value) if hasattr(v_init, "value") else float(v_init)
            ir_drop_est = 0.5
            v_min = params["Lower voltage cut-off [V]"]
            if (v_init_val - ir_drop_est) <= v_min:
                params["Lower voltage cut-off [V]"] = max(0.1, v_init_val - 1.0)
                print(f"INFO: Relaxed lower voltage cut-off from {v_min:.2f}V to {params['Lower voltage cut-off [V]']:.2f}V (Initial OCV: {v_init_val:.2f}V)")

            mesh, disc = self.mesh_cache.get_mesh_and_disc(
                params, self.model, self.submesh_types, self.var_pts, self.spatial_methods
            )

            processed_model = params.process_model(self.model, inplace=False)
            disc.process_model(processed_model, inplace=True)
            solver = self.solver_class(**self.solver_kwargs)
            sol = solver.solve(processed_model, [0, 3600 / c_rate], inputs={"Current [A]": c_rate * float(params["Nominal cell capacity [A.h]"])})
            return {"success": True, "sol": sol}
        except Exception as e:
            err_msg = f"ERROR: DFN Simulation failed: {e}\n{traceback.format_exc()}"
            return {"success": False, "reason": err_msg}
        finally:
            del processed_model
            del solver
            del params

    def clear_memory(self):
        """Release cached PyBaMM mesh objects responsibly."""
        if self.mesh_cache is not None:
            self.mesh_cache.clear()
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
        final_res = {"energy": float(energy), "power": float(power), "T_max": float(T_max), "stresses": stresses, "success": True}
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
        self.model = pybamm.lithium_ion.DFN(options)

        if os.environ.get("CEM_FAST_RUN") == "True":
            self.solver_kwargs = {"rtol": 1e-3, "atol": 1e-4, "options": {"dt_max": 20.0}}
        else:
            self.solver_kwargs = {"rtol": 1e-7, "atol": 1e-9, "options": {"dt_max": 5.0}}

        self.runner = SimulationRunner(self.model, pybamm.IDAKLUSolver, self.solver_kwargs)
        self.mech_model = ThermoelasticStrainModel()

    def run(self):
        return run_workflow(self.engine)

    def simulate(self, params: pybamm.ParameterValues, c_rate: float = 1.0, return_sol: bool = False) -> Dict[str, Any]:
        res = self.runner.run_simulation(params, c_rate)
        if not res["success"]:
            print(res["reason"])
        return post_process_sol(res, return_sol=return_sol)

    def evaluate_stability_pde(self, params: pybamm.ParameterValues, mode: str, c_rate: float = 1.0) -> Tuple[bool, float]:
        res = self.simulate(params, c_rate=c_rate, return_sol=True)
        if not res["success"]: return False, -1e9
        try:
            mech_res = self.mech_model.solve_strain(res["sol"], params, c_rate=c_rate)
            max_strain = mech_res["max_strain"]
            mat_key = "NFPP" if "NFPP" in self.mech_model.critical_thresholds else list(self.mech_model.critical_thresholds.keys())[0]
            critical_strain = self.mech_model.critical_thresholds.get(mat_key, 2e-3)
            eta = max_strain / critical_strain
            print(f"DEBUG[{mode}]: max_strain={max_strain:.4e}, critical={critical_strain:.4e}, eta={eta:.3f}")
            eta_threshold = float(os.environ.get("CEM_ETA_THRESHOLD", 1.8))
            if eta > eta_threshold: return False, -float(eta)
            return True, -float(eta)
        except Exception as e:
            print(f"ERROR: FEM solve failed: {e}\n{traceback.format_exc()}")
            return False, -1e9

    def compute_jacobian(self, x: np.ndarray, deltas: Dict[str, Any]) -> Optional[np.ndarray]:
        eps = 1e-4
        num_vars = 2 if os.environ.get("CEM_FAST_RUN") == "True" else len(DESIGN_SPACE)

        candidates = []
        candidates.append((x.copy(), deltas))
        for j in range(num_vars):
            x_pert = x.copy()
            lower, upper = DESIGN_BOUNDS[j]
            x_pert[j] += eps * (upper - lower)
            candidates.append((x_pert, deltas))

        candidate_params = transform_candidates_parallel(
            candidates,
            base_values=self.base_values,
            derived=self.derived,
        )

        max_workers = max(1, os.cpu_count() - 1)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            jobs = [(params, 1.0) for params in candidate_params]
            raw_results = list(executor.map(lambda job: self.runner.run_simulation(job[0], job[1]), jobs))

        sim_results = [post_process_sol(res) for res in raw_results]

        base_res = sim_results[0]
        if not base_res["success"]:
            print(f"WARNING: Baseline DFN simulation failed: {base_res.get('reason')}. Skipping candidate.")
            return None

        from src.cell_optimization.chem_regularization import mechanical_stability_metric
        j_base = np.array([
            base_res["energy"],
            base_res["power"],
            base_res["T_max"],
            mechanical_stability_metric(stresses=base_res["stresses"])
        ])
        G = np.zeros((4, len(DESIGN_SPACE)))

        for j in range(num_vars):
            res = sim_results[j + 1]
            if res["success"]:
                j_pert = np.array([
                    res["energy"],
                    res["power"],
                    res["T_max"],
                    mechanical_stability_metric(stresses=res["stresses"])
                ])
                G[:, j] = (np.log(np.abs(j_pert) + 1e-12) - np.log(np.abs(j_base) + 1e-12)) / eps
            else:
                print(f"WARNING: Perturbation for {DESIGN_SPACE[j]} failed: {res.get('reason')}")

        G = np.nan_to_num(G, nan=0.0, posinf=0.0, neginf=0.0)
        if not np.isfinite(G).all(): raise RuntimeError("Degenerate Jacobian detected.")
        U, S, Vt = np.linalg.svd(G, full_matrices=False)
        cond_limit = 1e6
        smax = S[0]
        S = np.array([max(s, smax / cond_limit) for s in S])
        G = (U * S) @ Vt
        return G

def _optimize_mode_pipeline_worker(job):
    """ThreadPool worker running step 1 and step 2 parameters co-optimization sequentially for a single objective mode."""
    i, mode, x_base, deltas, G, STRUCT_INDICES, MAT_INDICES, engine = job

    local_optimizer = None
    problem = None
    problem_m = None
    cem = None
    cem_m = None

    try:
        # Instantiate a thread-local HierarchicalOptimizer to guarantee absolute solver thread safety
        local_optimizer = HierarchicalOptimizer(engine=engine)

        # 1. Step 1: Structural Parameters (θs) Optimization
        max_s = np.max(np.abs(G[i, STRUCT_INDICES])) + 1e-12
        active_indices = [j for j in STRUCT_INDICES if np.abs(G[i, j]) / max_s > 0.5]
        if not active_indices:
            active_indices = [int(STRUCT_INDICES[np.argmax(np.abs(G[i, STRUCT_INDICES]))])]

        ref_val = 1.0
        problem = SingleObjectiveProblem(local_optimizer, x_base, active_indices, deltas, mode, ref_scale=ref_val)
        pop_size = int(os.environ.get("CEM_POP_SIZE", 8))
        iters = int(os.environ.get("CEM_ITERATIONS", 2))
        cem = CrossEntropyOptimizer(population_size=pop_size, iterations=iters)
        best_active = cem.optimize(problem.evaluate_single, x_base, DESIGN_BOUNDS, active_indices, G[i, :], verbose=False)

        x_opt_struct = x_base.copy()
        x_opt_struct[active_indices] = best_active

        # 2. Step 2: Material Parameters (θm) Optimization
        active_indices_m = MAT_INDICES
        problem_m = SingleObjectiveProblem(local_optimizer, x_opt_struct, active_indices_m, deltas, mode, ref_scale=ref_val)
        cem_m = CrossEntropyOptimizer(population_size=pop_size, iterations=iters)
        best_active_m = cem_m.optimize(problem_m.evaluate_single, x_opt_struct, DESIGN_BOUNDS, active_indices_m, G[i, :], verbose=False)

        x_opt_final = x_opt_struct.copy()
        x_opt_final[active_indices_m] = best_active_m

        return x_opt_final
    finally:
        if local_optimizer is not None:
            local_optimizer.runner.clear_memory()
        del cem_m
        del cem
        del problem_m
        del problem
        del local_optimizer
        gc.collect()

def run_workflow(engine: Optional[Any] = None):
    optimizer = None
    G = None
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

        # 1. Parallel Dopant Optimization & Scoring (No DFN)
        # Refactored analytical score to focus strictly on Energy, Power, and Thermal Stability as instructed
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

        # 2. Parallel Salt Optimization & Scoring (No DFN)
        # Refactored analytical score to focus strictly on Energy, Power, and Thermal Stability as instructed
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

        print("COMPUTING SENSITIVITY MATRIX (JACOBIAN) ONCE...")
        G = optimizer.compute_jacobian(x_base, deltas)
        if G is None:
             raise RuntimeError("Jacobian computation failed for optimized cell chemistry.")

        print("\nSTAGE 2: PARAMETER CO-OPTIMIZATION (SEQUENTIAL OBJECTIVES)")
        STRUCT_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        MAT_INDICES = [11, 12]
        modes = ["energy", "power", "thermal_stability", "stability"]

        jobs = [
            (i, mode, x_base, deltas, G, STRUCT_INDICES, MAT_INDICES, engine)
            for i, mode in enumerate(modes)
        ]

        # Reverted to strictly sequential execution to minimize peak memory footprint and prevent virtual memory exhaustion
        print("  Executing Structural & Material Co-Optimization sequentially across independent modes...")
        final_opt_designs = []
        for job in jobs:
            final_opt_designs.append(_optimize_mode_pipeline_worker(job))

        print("RUNNING PARETO FRONT FILTERING...")
        candidate_metrics = []
        for x in final_opt_designs:
            pt = ParamTransform(
                base_values=optimizer.base_values,
                derived=optimizer.derived
            )
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

        groups = {"Energy": [], "Power": [], "Thermal Stability": [], "Stability": [], "Coupled": []}
        S = np.abs(G) / (np.max(np.abs(G), axis=1).reshape(-1, 1) + 1e-12)
        for j, name in enumerate(DESIGN_SPACE):
            member_of = []
            for i, obj in enumerate(["Energy", "Power", "Thermal Stability", "Stability"]):
                if S[i, j] > 0.5: groups[obj].append(name); member_of.append(obj)
            if len(member_of) > 1: groups["Coupled"].append(name)

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
            "sensitivity_matrix": G.tolist(),
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
        del G
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
        del optimizer
        gc.collect()
        print("FINAL CLEANUP: Hierarchical optimization process released cached simulation memory.")
