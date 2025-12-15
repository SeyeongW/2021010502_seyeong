import os
import subprocess
import re
from dataclasses import dataclass
from typing import List


@dataclass
class Settings:
    base_cfg_name: str = "turb_VR12_2nd.cfg"
    mesh_name: str = "VR-12.su2"

    aoa_start: int = 0
    aoa_end_inclusive: int = 20
    aoa_step: int = 2

    case_prefix: str = "deg_"
    case_zero_pad: int = 2

    mpi_exec: str = "mpiexec"
    mpi_ranks: int = 8
    su2_exec: str = "SU2_CFD"

    run_cfg_name: str = "run2.cfg"
    stop_on_failure: bool = True

    cfg_encoding: str = "utf-8"

    restart_file_name: str = "restart_flow.dat"


def build_aoa_list(s: Settings) -> List[int]:
    if s.aoa_step == 0:
        raise ValueError("aoa_step must not be 0.")
    return list(range(s.aoa_start, s.aoa_end_inclusive + 1, s.aoa_step))


def ensure_exists(path: str, label: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")


def load_base_cfg_lines(base_cfg_path: str, encoding: str) -> List[str]:
    with open(base_cfg_path, "r", encoding=encoding, errors="ignore") as f:
        lines = f.readlines()
    drop = re.compile(r"^\s*(AOA|MESH_FILENAME)\s*=", re.IGNORECASE)
    return [l for l in lines if not drop.match(l)]


def write_case_cfg(cfg_path: str, base_lines: List[str], aoa: float, mesh_filename: str, encoding: str) -> None:
    with open(cfg_path, "w", encoding=encoding, newline="\n") as f:
        f.writelines(base_lines)
        f.write("\n% --- Auto Generated settings ---\n")
        f.write(f"AOA= {aoa:.6f}\n")
        f.write(f"MESH_FILENAME= {mesh_filename}\n")


def run_one_case(root: str, s: Settings, base_lines: List[str], aoa: int) -> bool:
    case_name = f"{s.case_prefix}{aoa:0{s.case_zero_pad}d}"
    case_dir = os.path.join(root, case_name)

    if not os.path.isdir(case_dir):
        print(f"[FAIL] Missing case folder: {case_dir}")
        return False

    mesh_path = os.path.join(case_dir, s.mesh_name)
    rst_path = os.path.join(case_dir, s.restart_file_name)

    if not os.path.exists(mesh_path):
        print(f"[FAIL] Missing mesh in {case_name}: {s.mesh_name}")
        return False

    if not os.path.exists(rst_path):
        print(f"[FAIL] Missing restart in {case_name}: {s.restart_file_name}")
        return False

    cfg_path = os.path.join(case_dir, s.run_cfg_name)
    write_case_cfg(cfg_path, base_lines, float(aoa), s.mesh_name, s.cfg_encoding)

    cmd = [s.mpi_exec, "-n", str(s.mpi_ranks), s.su2_exec, s.run_cfg_name]

    print("====================================================")
    print(f"[STAGE 2 | AoA {aoa:>3d} deg] folder: {case_name}")
    print("====================================================")
    print(f"[CMD] {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, cwd=case_dir, check=True)
        print(f"\n[SUCCESS] Stage 2 AoA={aoa} finished.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] Stage 2 AoA={aoa} failed (returncode={e.returncode}).\n")
        return False


def main():
    root = os.getcwd()
    s = Settings()

    base_cfg_path = os.path.join(root, s.base_cfg_name)
    ensure_exists(base_cfg_path, "Base cfg file")

    base_lines = load_base_cfg_lines(base_cfg_path, s.cfg_encoding)
    aoa_list = build_aoa_list(s)

    print("====================================================")
    print("[INFO] SU2 Stage-2 AoA sweep (no folder recreate)")
    print(f"[INFO] root: {root}")
    print(f"[INFO] base cfg: {s.base_cfg_name}")
    print(f"[INFO] mesh: {s.mesh_name} (must exist inside each case folder)")
    print(f"[INFO] restart: {s.restart_file_name} (must exist inside each case folder)")
    print(f"[INFO] angles: {aoa_list}")
    print(f"[INFO] mpi: {s.mpi_exec} -n {s.mpi_ranks}")
    print(f"[INFO] stop-on-failure: {s.stop_on_failure}")
    print("====================================================\n")

    for aoa in aoa_list:
        ok = run_one_case(root, s, base_lines, aoa)
        if not ok and s.stop_on_failure:
            print("[STOP] Abort stage-2 now.")
            break

    print("Done.")


if __name__ == "__main__":
    main()