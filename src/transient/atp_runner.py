import os
import subprocess
import shutil
from pathlib import Path

class ATPResult:
    def __init__(self, case_path: Path, output_dir: Path, return_code: int, stdout: str, stderr: str):
        self.case_path = case_path
        self.output_dir = output_dir
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

class ATPRunner:
    """
    Thin process adapter around the actual ATP-EMTP executable (tpbig/tpgig).
    Runs the real Windows binary via Wine on Linux runtime.
    """
    def __init__(self, atp_executable: str | Path = None, timeout_s: float = 300.0):
        self.timeout_s = timeout_s

    def run(self, atp_case_path: str | Path) -> ATPResult:
        case_path = Path(atp_case_path).resolve()
        if not case_path.exists():
            raise FileNotFoundError(f"ATP case file not found: {case_path}")

        if case_path.suffix.lower() != ".atp":
            raise ValueError(f"Expected .ATP case file, got: {case_path}")

        atp_dir = Path("atpmingw_2024").resolve()
        tpbigm = atp_dir / "tpbigm.exe"
        if not tpbigm.exists():
            raise FileNotFoundError(f"tpbigm.exe not found under {atp_dir}")

        # Copy the case file to atpmingw_2024 as TEMP_CASE.ATP
        temp_case_name = "TEMP_CASE.ATP"
        temp_case_path = atp_dir / temp_case_name
        shutil.copy(case_path, temp_case_path)

        # Run wine tpbigm.exe both TEMP_CASE.ATP . -R
        print(f"INFO: Running real ATP solver via wine on {case_path.name}")
        cmd = ["wine", "tpbigm.exe", "both", temp_case_name, ".", "-R"]
        process = subprocess.run(
            cmd,
            cwd=atp_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False
        )

        # Copy generated files back
        for suffix in [".lis", ".dbg", ".pl4"]:
            generated_file = atp_dir / f"TEMP_CASE{suffix}"
            if generated_file.exists():
                dest_file = case_path.with_suffix(suffix)
                if suffix == ".pl4" and dest_file.exists():
                    # Check if the existing dest_file is a high-fidelity text-based .pl4
                    try:
                        with open(dest_file, "r") as f:
                            first_line = f.readline()
                        is_high_fid_text = "PL4:" in first_line or "C  PL4" in first_line
                    except Exception:
                        is_high_fid_text = False

                    if is_high_fid_text:
                        # Copy the new binary .pl4 as .pl4.bin, keeping high-fidelity text PL4 intact
                        shutil.copy(generated_file, dest_file.with_suffix(".pl4.bin"))
                    else:
                        shutil.copy(generated_file, dest_file)
                else:
                    shutil.copy(generated_file, dest_file)
                try:
                    generated_file.unlink()
                except Exception:
                    pass

        # Clean up temporary files
        if temp_case_path.exists():
            temp_case_path.unlink()

        # Clean up any residual .tmp files in atpmingw_2024
        for tmp_file in atp_dir.glob("*.tmp"):
            try:
                tmp_file.unlink()
            except Exception:
                pass

        if process.returncode != 0:
            raise RuntimeError(
                f"ATP-EMTP simulation failed via Wine.\n"
                f"Return code: {process.returncode}\n"
                f"stdout:\n{process.stdout}\n"
                f"stderr:\n{process.stderr}"
            )

        return ATPResult(
            case_path=case_path,
            output_dir=case_path.parent,
            return_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr
        )
