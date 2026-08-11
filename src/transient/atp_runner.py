import os
import subprocess
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
    This class does NOT solve the network directly.
    Expects Linux binaries to be placed in: src/transient/bin/tpbig or src/transient/bin/tpgig
    In headless sandbox environments where the licensed executable is missing,
    it executes the mock tpbig solver in '__mocks__' via subprocess.run to maintain
    perfect alignment with the command line ATP-EMTP solver interface.
    """
    def __init__(self, atp_executable: str | Path = None, timeout_s: float = 300.0):
        env_exe = os.environ.get("ATP_EXECUTABLE", "")

        bin_tpbig = Path("src/transient/bin/tpbig")
        bin_tpgig = Path("src/transient/bin/tpgig")

        if atp_executable is not None:
            self.atp_executable = Path(atp_executable)
        elif env_exe:
            self.atp_executable = Path(env_exe)
        elif bin_tpbig.exists():
            self.atp_executable = bin_tpbig
        elif bin_tpgig.exists():
            self.atp_executable = bin_tpgig
        else:
            self.atp_executable = Path("/usr/bin/tpbig") # Default system path

        self.timeout_s = timeout_s

    def run(self, atp_case_path: str | Path) -> ATPResult:
        case_path = Path(atp_case_path).resolve()
        if not case_path.exists():
            raise FileNotFoundError(f"ATP case file not found: {case_path}")

        if case_path.suffix.lower() != ".atp":
            raise ValueError(f"Expected .ATP case file, got: {case_path}")

        # If the real ATP executable exists on disk, invoke it via subprocess
        if self.atp_executable and self.atp_executable.exists():
            print(f"INFO: Invoking actual ATP-EMTP solver: {self.atp_executable}")
            process = subprocess.run(
                [str(self.atp_executable), str(case_path)],
                cwd=case_path.parent,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False
            )
            if process.returncode != 0:
                raise RuntimeError(
                    f"ATP-EMTP simulation failed.\n"
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

        # Sandbox / Fallback solver: Invokes mock tpbig solver via subprocess
        print("INFO: Licensed tpbig/tpgig solver missing on system. Invoking mock tpbig solver via subprocess...")
        mock_script = Path("__mocks__/tpbig.py").resolve()
        if not mock_script.exists():
            raise FileNotFoundError(f"Mock ATP solver script not found at {mock_script}")

        process = subprocess.run(
            ["python", str(mock_script), str(case_path)],
            cwd=case_path.parent,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"Mock ATP-EMTP simulation failed.\n"
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
