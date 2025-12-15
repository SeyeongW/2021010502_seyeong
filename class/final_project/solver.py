#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import shutil
import subprocess
import sys
from pathlib import Path

# =========================================================
# USER SETTINGS
# =========================================================
ROOT_DIR = Path(".").resolve()     # 여기(상위 폴더)에서 실행한다고 가정
CFG1_NAME = "turb1_VR12.cfg"       # 1차 cfg (상위 폴더에 위치)
CFG2_NAME = "turb2_VR12.cfg"       # 2차 cfg (상위 폴더에 위치)
MESH_NAME = "VR-12.su2"            # 메쉬 파일 (상위 폴더에 위치)

AOA_START = 0
AOA_END = 20
AOA_STEP = 2

MPIEXEC = "mpiexec"
MPI_N = 8
SU2_EXE = "SU2_CFD"

STOP_ON_FAILURE = True            # 실패하면 즉시 종료

# 1차 restart 이름은 "restart_flow"로 고정 (2차가 덮어써도 됨)
RESTART_BASE = "restart_flow"

# 로그에서 이런 문구가 보이면 실패로 판정
FATAL_PATTERNS = [
    "FGMRES orthogonalization failed",
    "linear solver diverged",
    "Error Exit",
    "nan",
    "inf",
]
# =========================================================


def read_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8", errors="ignore").splitlines(True)


def write_lines(p: Path, lines: list[str]) -> None:
    p.write_text("".join(lines), encoding="utf-8", newline="\n")


def apply_overrides(base_lines: list[str], overrides: dict[str, str]) -> list[str]:
    """
    cfg에서 overrides에 있는 KEY= 라인을 제거하고,
    끝에 KEY= value로 덧붙임.
    """
    keys = sorted(overrides.keys(), key=len, reverse=True)
    key_pattern = "|".join(re.escape(k) for k in keys)
    drop_re = re.compile(rf"^\s*({key_pattern})\s*=", re.IGNORECASE)

    cleaned = [ln for ln in base_lines if not drop_re.match(ln)]
    cleaned.append("\n% --- Auto overrides by run_2stage_sweep_folders.py ---\n")
    for k, v in overrides.items():
        cleaned.append(f"{k}= {v}\n")
    return cleaned


def run_cmd_stream(cwd: Path, cmd: list[str]) -> tuple[int, str]:
    """
    실행하면서 화면 출력 + 로그 캡처
    """
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    log_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        log_lines.append(line)
    ret = proc.wait()
    return ret, "".join(log_lines)


def log_has_fatal(log_text: str) -> bool:
    low = log_text.lower()
    return any(p.lower() in low for p in FATAL_PATTERNS)


def find_restart_file(case_dir: Path, base: str) -> Path | None:
    """
    SU2 restart 파일 탐색 (restart_flow.dat 등)
    """
    candidates = [
        f"{base}.dat",
        f"{base}.dat.gz",
        f"{base}.csv",
        f"{base}.su2",
        base,
    ]
    for c in candidates:
        p = case_dir / c
        if p.is_file():
            return p
    for p in case_dir.iterdir():
        if p.is_file() and p.name.startswith(base):
            return p
    return None


def make_case_folder_name(aoa: int) -> str:
    # aoa_00, aoa_02 ... aoa_20
    return f"aoa_{aoa:02d}"


def main():
    cfg1_path = ROOT_DIR / CFG1_NAME
    cfg2_path = ROOT_DIR / CFG2_NAME
    mesh_path = ROOT_DIR / MESH_NAME

    if not cfg1_path.is_file():
        print(f"[ERROR] Missing cfg1: {cfg1_path}")
        sys.exit(1)
    if not cfg2_path.is_file():
        print(f"[ERROR] Missing cfg2: {cfg2_path}")
        sys.exit(1)
    if not mesh_path.is_file():
        print(f"[ERROR] Missing mesh: {mesh_path}")
        sys.exit(1)

    base1 = read_lines(cfg1_path)
    base2 = read_lines(cfg2_path)

    angles = list(range(AOA_START, AOA_END + 1, AOA_STEP))

    print("====================================================")
    print("[INFO] SU2 2-stage sweep (folder-per-angle)")
    print(f"[INFO] root: {ROOT_DIR}")
    print(f"[INFO] mesh: {MESH_NAME}")
    print(f"[INFO] cfg1: {CFG1_NAME}")
    print(f"[INFO] cfg2: {CFG2_NAME}")
    print(f"[INFO] angles: {angles}")
    print(f"[INFO] mpi: {MPIEXEC} -n {MPI_N}")
    print(f"[INFO] stop-on-failure: {STOP_ON_FAILURE}")
    print("====================================================\n")

    for aoa in angles:
        case_name = make_case_folder_name(aoa)
        case_dir = ROOT_DIR / case_name
        case_dir.mkdir(parents=True, exist_ok=True)

        # 폴더 안에 mesh/cfg 템플릿 복사 (원래 방식대로 “각 폴더에서 완결”)
        shutil.copy2(mesh_path, case_dir / MESH_NAME)

        # Stage1 cfg 생성 (폴더 안에서 실행)
        stage1_cfg = case_dir / "run_stage1.cfg"
        ov1 = {
            "AOA": str(float(aoa)),
            "MESH_FILENAME": MESH_NAME,
            "RESTART_SOL": "NO",
            "RESTART_FILENAME": RESTART_BASE,
        }
        write_lines(stage1_cfg, apply_overrides(base1, ov1))

        # Stage2 cfg 생성
        stage2_cfg = case_dir / "run_stage2.cfg"
        # (SOLUTION_FILENAME는 stage1 실행 후 restart 파일명을 확인해서 넣음)

        print("\n====================================================")
        print(f"[AoA {aoa:2d} deg] folder: {case_dir.name}")
        print("====================================================")

        # ---------------- Stage 1 ----------------
        print("\n---------------- STAGE 1 ----------------")
        cmd1 = [MPIEXEC, "-n", str(MPI_N), SU2_EXE, stage1_cfg.name]
        ret1, log1 = run_cmd_stream(case_dir, cmd1)

        if ret1 != 0 or log_has_fatal(log1):
            print(f"\n[FAIL] Stage1 failed at AoA={aoa} deg (ret={ret1})")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        rst1_file = find_restart_file(case_dir, RESTART_BASE)
        if rst1_file is None:
            print(f"\n[FAIL] Stage1 finished but restart file not found: {RESTART_BASE}.*")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        print(f"\n[OK] Stage1 success. restart: {rst1_file.name}")
        print("NOTE: Stage2 will overwrite flow/surface/history in this folder (as requested).")

        # ---------------- Stage 2 ----------------
        print("\n---------------- STAGE 2 ----------------")
        ov2 = {
            "AOA": str(float(aoa)),
            "MESH_FILENAME": MESH_NAME,
            "RESTART_SOL": "YES",
            "SOLUTION_FILENAME": rst1_file.name,   # Stage1 restart에서 시작
            "RESTART_FILENAME": RESTART_BASE,      # Stage2도 같은 이름으로 restart 저장 (덮어씀)
        }
        write_lines(stage2_cfg, apply_overrides(base2, ov2))

        cmd2 = [MPIEXEC, "-n", str(MPI_N), SU2_EXE, stage2_cfg.name]
        ret2, log2 = run_cmd_stream(case_dir, cmd2)

        if ret2 != 0 or log_has_fatal(log2):
            print(f"\n[FAIL] Stage2 failed at AoA={aoa} deg (ret={ret2})")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        print(f"\n[SUCCESS] AoA={aoa} deg finished (Stage2 overwrote Stage1 outputs in {case_dir.name}).")

    print("\n[DONE] Sweep finished.")


if __name__ == "__main__":
    main()
