import os
import shutil
import subprocess
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


# ====================================================
# Config (edit here)
# ====================================================
@dataclass
class Settings:
    work_dir: str = r"D:\CFD\SU2_work\Project\VR-12"

    # Inputs
    base_cfg_name: str = "turb_VR12.cfg"
    mesh_name: str = "VR-12.su2"

    # AoA sweep
    aoa_start: int = 0
    aoa_end_inclusive: int = 20
    aoa_step: int = 2

    # Case folder naming
    case_prefix: str = "deg_"          # e.g., deg_0, deg_2 ...
    case_zero_pad: int = 2             # 2 -> deg_00, deg_02 ...

    # Run command
    mpi_exec: str = "mpiexec"
    mpi_ranks: int = 8
    su2_exec: str = "SU2_CFD"
    run_cfg_name: str = "run.cfg"

    # Behavior
    stop_on_failure: bool = True       # 실패하면 break
    recreate_case_dir: bool = True     # 케이스 폴더가 있으면 삭제 후 재생성

    # Cleanup (optional)
    do_cleanup: bool = False           # True면 성공 후 필요 파일만 남기고 삭제
    files_to_keep: List[str] = None    # do_cleanup=True일 때 사용

    # Encoding
    cfg_encoding: str = "utf-8"


def build_aoa_list(s: Settings) -> List[int]:
    if s.aoa_step == 0:
        raise ValueError("aoa_step must not be 0.")
    if (s.aoa_end_inclusive - s.aoa_start) * s.aoa_step < 0:
        raise ValueError("aoa_step sign does not move from start to end.")
    return list(range(s.aoa_start, s.aoa_end_inclusive + (1 if s.aoa_step > 0 else -1), s.aoa_step))


def safe_rmtree(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path)


def ensure_exists(path: str, kind: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{kind} not found: {path}")


def load_base_cfg_lines(base_cfg_path: str, encoding: str) -> List[str]:
    with open(base_cfg_path, "r", encoding=encoding, errors="ignore") as f:
        lines = f.readlines()

    # Remove only AOA and MESH_FILENAME so we can inject per-case values
    regex_drop = re.compile(r"^\s*(AOA|MESH_FILENAME)\s*=", re.IGNORECASE)
    clean_lines = [l for l in lines if not regex_drop.match(l)]
    return clean_lines


def write_case_cfg(cfg_path: str, base_lines: List[str], aoa: float, mesh_filename: str, encoding: str) -> None:
    with open(cfg_path, "w", encoding=encoding, newline="\n") as f:
        f.writelines(base_lines)
        f.write("\n% --- Auto Generated settings ---\n")
        f.write(f"AOA= {aoa:.6f}\n")
        f.write(f"MESH_FILENAME= {mesh_filename}\n")


def cleanup_case_dir(case_dir: str, keep: List[str]) -> None:
    keep_set = set(keep)
    for name in os.listdir(case_dir):
        p = os.path.join(case_dir, name)
        if name in keep_set:
            continue
        try:
            if os.path.isfile(p) or os.path.islink(p):
                os.unlink(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)
        except Exception as e:
            print(f"[WARN] Failed to delete {p}: {e}")


def run_one_case(s: Settings, base_lines: List[str], aoa: int) -> bool:
    case_name = f"{s.case_prefix}{aoa:0{s.case_zero_pad}d}"
    case_dir = os.path.join(s.work_dir, case_name)

    # (1) Prepare folder
    if s.recreate_case_dir:
        safe_rmtree(case_dir)
    os.makedirs(case_dir, exist_ok=True)

    # (2) Copy mesh
    src_mesh = os.path.join(s.work_dir, s.mesh_name)
    dst_mesh = os.path.join(case_dir, s.mesh_name)
    shutil.copy(src_mesh, dst_mesh)

    # (3) Write cfg
    cfg_path = os.path.join(case_dir, s.run_cfg_name)
    write_case_cfg(cfg_path, base_lines, float(aoa), s.mesh_name, s.cfg_encoding)

    # (4) Run SU2
    cmd = [s.mpi_exec, "-n", str(s.mpi_ranks), s.su2_exec, s.run_cfg_name]

    print("====================================================")
    print(f"[AoA {aoa:>3d} deg] folder: {case_name}")
    print("====================================================")
    print(f"[CMD] {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, cwd=case_dir, check=True)
        print(f"\n[SUCCESS] AoA={aoa} finished.\n")

        # (5) Optional cleanup
        if s.do_cleanup:
            if not s.files_to_keep:
                raise ValueError("do_cleanup=True but files_to_keep is empty.")
            print("[INFO] Cleaning up files...")
            cleanup_case_dir(case_dir, s.files_to_keep)
            print("[INFO] Cleanup done.\n")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] AoA={aoa} failed (returncode={e.returncode}).\n")
        return False


def main():
    s = Settings(
        # 너가 원하면 여기서 바로 덮어써도 됨
        work_dir=r"D:\CFD\SU2_work\Project\VR-12",
        base_cfg_name="turb_VR12.cfg",
        mesh_name="VR-12.su2",

        aoa_start=0,
        aoa_end_inclusive=20,
        aoa_step=2,

        mpi_exec="mpiexec",
        mpi_ranks=8,
        su2_exec="SU2_CFD",

        stop_on_failure=True,
        recreate_case_dir=True,

        # 성공한 폴더에서 결과 파일만 남기고 싶으면 True로
        do_cleanup=False,
        files_to_keep=["history.csv", "flow.vtu", "surface_flow.vtu", "surface.vtu", "restart_flow.dat"],
    )

    mesh_path = os.path.join(s.work_dir, s.mesh_name)
    base_cfg_path = os.path.join(s.work_dir, s.base_cfg_name)

    ensure_exists(mesh_path, "Mesh file")
    ensure_exists(base_cfg_path, "Base cfg file")

    base_lines = load_base_cfg_lines(base_cfg_path, s.cfg_encoding)
    aoa_list = build_aoa_list(s)

    print("====================================================")
    print("[INFO] SU2 AoA sweep (folder-per-angle)")
    print(f"[INFO] root: {s.work_dir}")
    print(f"[INFO] mesh: {s.mesh_name}")
    print(f"[INFO] base cfg: {s.base_cfg_name}")
    print(f"[INFO] angles: {aoa_list}")
    print(f"[INFO] mpi: {s.mpi_exec} -n {s.mpi_ranks}")
    print(f"[INFO] stop-on-failure: {s.stop_on_failure}")
    print("====================================================\n")

    for aoa in aoa_list:
        ok = run_one_case(s, base_lines, aoa)
        if not ok and s.stop_on_failure:
            print("[STOP] Abort all CFD runs now.")
            break

    print("Done.")


if __name__ == "__main__":
    main()
