import os
import shutil
import subprocess
import re

# ====================================================
# 사용자 설정
# ====================================================
work_dir = r"D:\CFD\SU2_work\Project\VR-12"
base_cfg_name = "turb_VR12.cfg"
mesh_name = "VR-12.su2"  # 복사될 메쉬 파일 이름
aoa_list = range(0, 22, 2)  # [0, 2, 4 ...] 필요에 따라 range 조절

# 남길 파일 목록 (정확한 파일명 또는 확장자)
# 주의: SU2 설정 파일(.cfg)에서 OUTPUT_FORMAT= PARAVIEW 로 설정되어 있어야 .vtu가 나옵니다.
files_to_keep = ["history.csv", "flow.vtu", "surface_flow.vtu", "surface.vtu"]

# ====================================================

mesh_path = os.path.join(work_dir, mesh_name)
base_cfg_path = os.path.join(work_dir, base_cfg_name)

# 메쉬 파일 존재 확인
if not os.path.exists(mesh_path):
    raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

# 기본 설정 파일 읽기
with open(base_cfg_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

# 기존 AOA, MESH_FILENAME만 제거 (MGLEVEL 등 다른 설정은 건드리지 않음)
# AOA는 루프에서 변경되고, MESH_FILENAME은 로컬 경로로 다시 지정해야 하므로 제거
regex_drop = re.compile(r"^\s*(AOA|MESH_FILENAME)\s*=", re.IGNORECASE)
clean_lines = [l for l in lines if not regex_drop.match(l)]

print(f"Base config loaded. Optimization settings preserved.")
print(f"Running {len(list(aoa_list))} cases.\n")

for aoa in aoa_list:
    case_dir = os.path.join(work_dir, f"deg_{aoa}")

    # 1. 케이스 폴더 생성 (이미 있으면 삭제 후 재생성)
    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)
    os.makedirs(case_dir)

    # 2. 메쉬 파일 복사
    shutil.copy(mesh_path, os.path.join(case_dir, mesh_name))

    # 3. 실행용 cfg 파일 작성
    cfg_path = os.path.join(case_dir, "run.cfg")
    with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(clean_lines)
        f.write("\n% --- Auto Generated settings ---\n")
        f.write(f"AOA= {float(aoa)}\n")
        f.write(f"MESH_FILENAME= {mesh_name}\n")
        # MGLEVEL 등을 강제로 덮어쓰는 코드는 삭제함

    print(f"==========================================")
    print(f"[Start] AoA = {aoa} deg Simulation")
    print(f"==========================================\n")

    # 4. SU2 실행
    cmd = ["mpiexec", "-n", "8", "SU2_CFD", "run.cfg"]

    try:
        subprocess.run(
            cmd,
            cwd=case_dir,
            check=True
        )
        print(f"\n[Success] AoA = {aoa} deg finished.")
        
        # 5. 파일 정리 (원하는 파일만 남기고 삭제)
        print("Cleaning up files...")
        for filename in os.listdir(case_dir):
            file_path = os.path.join(case_dir, filename)
            
            # 남길 파일 목록에 포함되지 않으면 삭제
            if filename not in files_to_keep:
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")

    except subprocess.CalledProcessError:
        print(f"\n[Failed] AoA = {aoa} deg execution error.\n")

print("All cases finished.")