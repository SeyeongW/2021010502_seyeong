#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
import sys
from pathlib import Path

# =========================================================
# USER SETTINGS (네 조건을 여기다 "고정"해둠)
# =========================================================
CASE_DIR = Path(".")               # 이 스크립트를 deg_0 같은 폴더에 넣고 거기서 실행
CFG1 = "turb1_VR12.cfg"            # 1차 cfg
CFG2 = "turb2_VR12.cfg"            # 2차 cfg
MESH = "VR-12.su2"                 # 메쉬 파일명
AOA_START = 0
AOA_END = 20
AOA_STEP = 2

MPI_N = 8
MPIEXEC = "mpiexec"                # Windows: 보통 mpiexec
SU2_EXE = "SU2_CFD"                # PATH에 잡혀있거나, 절대경로로 바꿔도 됨

STOP_ON_FAILURE = True             # 실패하면 즉시 CFD 종료(=스크립트 종료)

# 결과 파일명 덮어쓰기 방지(각 AoA / stage별로 파일명 분리)
SEPARATE_OUTPUTS = True

# Stage2 성공 후 Stage1 restart 삭제할지
DELETE_STAGE1_RESTART_AFTER_STAGE2 = False

# 로그에서 이런 문구가 보이면 "실패"로 판정
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
    cfg에서 overrides 키에 해당하는 기존 KEY= 라인을 제거하고,
    파일 끝에 KEY= value 형태로 덧붙임.
    """
    keys = sorted(overrides.keys(), key=len, reverse=True)
    key_pattern = "|".join(re.escape(k) for k in keys)
    drop_re = re.compile(rf"^\s*({key_pattern})\s*=", re.IGNORECASE)

    cleaned = [ln for ln in base_lines if not drop_re.match(ln)]
    cleaned.append("\n% --- Auto overrides by run_2stage_sweep.py ---\n")
    for k, v in overrides.items():
        cleaned.append(f"{k}= {v}\n")
    return cleaned


def run_cmd_stream(cwd: Path, cmd: list[str]) -> tuple[int, str]:
    """
    실행하면서 콘솔로 출력도 하고, 로그 텍스트도 수집해서 반환.
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
    SU2 restart 파일명을 base로 두고, 흔한 확장자 후보를 탐색.
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


def main():
    case_dir = CASE_DIR.resolve()
    cfg1_path = case_dir / CFG1
    cfg2_path = case_dir / CFG2
    mesh_path = case_dir / MESH

    if not case_dir.is_dir():
        print(f"[ERROR] CASE_DIR not found: {case_dir}")
        sys.exit(1)
    if not cfg1_path.is_file():
        print(f"[ERROR] cfg1 not found: {cfg1_path}")
        sys.exit(1)
    if not cfg2_path.is_file():
        print(f"[ERROR] cfg2 not found: {cfg2_path}")
        sys.exit(1)
    if not mesh_path.is_file():
        print(f"[ERROR] mesh not found: {mesh_path}")
        sys.exit(1)

    base1 = read_lines(cfg1_path)
    base2 = read_lines(cfg2_path)

    angles = list(range(AOA_START, AOA_END + 1, AOA_STEP))

    print("====================================================")
    print("[INFO] 2-stage SU2 sweep")
    print(f"[INFO] case-dir: {case_dir}")
    print(f"[INFO] mesh: {mesh_path.name}")
    print(f"[INFO] cfg1: {cfg1_path.name}")
    print(f"[INFO] cfg2: {cfg2_path.name}")
    print(f"[INFO] angles: {angles}")
    print(f"[INFO] mpi: {MPIEXEC} -n {MPI_N}")
    print(f"[INFO] stop-on-failure: {STOP_ON_FAILURE}")
    print("====================================================\n")

    for aoa in angles:
        tag = f"aoa{aoa}".replace("-", "m")
        rst1_base = f"restart_stage1_{tag}"
        rst2_base = f"restart_stage2_{tag}"

        run1_cfg = case_dir / (f"run_stage1_{tag}.cfg" if SEPARATE_OUTPUTS else "run_stage1.cfg")
        run2_cfg = case_dir / (f"run_stage2_{tag}.cfg" if SEPARATE_OUTPUTS else "run_stage2.cfg")

        # ---------------- Stage 1 ----------------
        ov1 = {
            "AOA": str(float(aoa)),
            "MESH_FILENAME": mesh_path.name,
            "RESTART_SOL": "NO",
            "RESTART_FILENAME": rst1_base,
        }

        if SEPARATE_OUTPUTS:
            ov1.update({
                "CONV_FILENAME": f"history_stage1_{tag}",
                "VOLUME_FILENAME": f"flow_stage1_{tag}",
                "SURFACE_FILENAME": f"surface_flow_stage1_{tag}",
                "MESH_OUT_FILENAME": f"mesh_out_stage1_{tag}.su2",
            })

        write_lines(run1_cfg, apply_overrides(base1, ov1))

        print("\n====================================================")
        print(f"[STAGE 1] AoA={aoa} deg")
        print("====================================================")
        cmd1 = [MPIEXEC, "-n", str(MPI_N), SU2_EXE, run1_cfg.name]
        ret1, log1 = run_cmd_stream(case_dir, cmd1)

        if ret1 != 0 or log_has_fatal(log1):
            print(f"\n[FAIL] Stage1 failed at AoA={aoa} deg (ret={ret1})")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        rst1_file = find_restart_file(case_dir, rst1_base)
        if rst1_file is None:
            print(f"\n[FAIL] Stage1 finished but restart file not found: {rst1_base}.*")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        print(f"\n[OK] Stage1 success. Restart file: {rst1_file.name}")

        # ---------------- Stage 2 ----------------
        ov2 = {
            "AOA": str(float(aoa)),
            "MESH_FILENAME": mesh_path.name,
            "RESTART_SOL": "YES",
            # 핵심: Stage1 restart를 읽어서 Stage2를 시작
            "SOLUTION_FILENAME": rst1_file.name,
            "RESTART_FILENAME": rst2_base,
        }

        if SEPARATE_OUTPUTS:
            ov2.update({
                "CONV_FILENAME": f"history_stage2_{tag}",
                "VOLUME_FILENAME": f"flow_stage2_{tag}",
                "SURFACE_FILENAME": f"surface_flow_stage2_{tag}",
                "MESH_OUT_FILENAME": f"mesh_out_stage2_{tag}.su2",
            })

        write_lines(run2_cfg, apply_overrides(base2, ov2))

        print("\n====================================================")
        print(f"[STAGE 2] AoA={aoa} deg (restart from stage1)")
        print("====================================================")
        cmd2 = [MPIEXEC, "-n", str(MPI_N), SU2_EXE, run2_cfg.name]
        ret2, log2 = run_cmd_stream(case_dir, cmd2)

        if ret2 != 0 or log_has_fatal(log2):
            print(f"\n[FAIL] Stage2 failed at AoA={aoa} deg (ret={ret2})")
            if STOP_ON_FAILURE:
                print("[STOP] Abort all CFD runs now.")
                sys.exit(1)
            else:
                break

        rst2_file = find_restart_file(case_dir, rst2_base)
        if rst2_file:
            print(f"\n[SUCCESS] AoA={aoa} deg completed. Final restart: {rst2_file.name}")
        else:
            print(f"\n[SUCCESS] AoA={aoa} deg completed. (Final restart not found: {rst2_base}.*)")

        # Optional cleanup
        if DELETE_STAGE1_RESTART_AFTER_STAGE2:
            try:
                rst1_file.unlink()
                print(f"[CLEAN] Deleted stage1 restart: {rst1_file.name}")
            except Exception as e:
                print(f"[WARN] Could not delete stage1 restart: {e}")

    print("\n[DONE] Sweep finished.")


if __name__ == "__main__":
    main()
