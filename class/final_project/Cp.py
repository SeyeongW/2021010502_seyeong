import os
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv
from matplotlib.lines import Line2D  # [추가] 커스텀 범례를 만들기 위해 필요

# ====================================================
# [사용자 설정]
# ====================================================
work_dir = os.getcwd()
print(f"Current Working Directory: {work_dir}")

# 분석할 각도 리스트
target_aoas = [0, 8, 12, 16, 20]

# 결과 저장 파일명
plot_file = "Cp_Comparison_Final.png"

# 그래프에 표시할 유동 조건 (범례에 추가될 내용)
flow_condition_text = [
    r"$Mach=0.3$", 
    r"$Re=2,600,000$"
]

# ====================================================

def extract_cp_data(vtu_path):
    """
    vtu 파일에서 Cp 데이터를 추출하여 Upper/Lower로 분리
    """
    if not os.path.exists(vtu_path):
        return None

    try:
        mesh = pv.read(vtu_path)
        points = mesh.points
        x = points[:, 0]
        y = points[:, 1]

        # Cp 데이터 찾기
        cp_data = None
        possible_names = ['Pressure_Coefficient', 'Cp', 'C_p']
        for name in possible_names:
            if name in mesh.point_data:
                cp_data = mesh.point_data[name]
                break
        
        if cp_data is None:
            return None

        # Upper/Lower 분리 및 정렬
        mask_up = y >= 0
        x_up = x[mask_up]
        cp_up = cp_data[mask_up]
        idx_up = np.argsort(x_up)

        mask_low = y < 0
        x_low = x[mask_low]
        cp_low = cp_data[mask_low]
        idx_low = np.argsort(x_low)

        return {
            'x_up': x_up[idx_up], 'cp_up': cp_up[idx_up],
            'x_low': x_low[idx_low], 'cp_low': cp_low[idx_low]
        }

    except Exception as e:
        print(f"Error reading {vtu_path}: {e}")
        return None

# ====================================================
# [메인 그래프 생성]
# ====================================================

# 5개의 행을 가진 서브플롯 생성
fig, axes = plt.subplots(nrows=len(target_aoas), ncols=1, figsize=(8, 16), sharex=True)

print("Starting Cp Comparison Analysis...")

for i, aoa in enumerate(target_aoas):
    ax = axes[i]
    
    # 폴더명 추정 (deg_00, deg_08 ...)
    case_name = f"deg_{aoa:02d}"
    vtu_path = os.path.join(work_dir, case_name, "surface_flow.vtu")
    
    print(f"Processing {case_name}...")
    
    data = extract_cp_data(vtu_path)
    
    if data is not None:
        # 스타일: Upper(파랑 실선), Lower(빨강 점선)
        ax.plot(data['x_up'], data['cp_up'], color='royalblue', linestyle='-', linewidth=2)
        ax.plot(data['x_low'], data['cp_low'], color='firebrick', linestyle='--', linewidth=2)
        
        # 텍스트 박스 (각도 표시 - 왼쪽 아래)
        ax.text(0.02, 0.1, f"AoA = {aoa}°", transform=ax.transAxes, 
                fontsize=12, fontweight='bold', 
                bbox=dict(boxstyle="round", fc="white", ec="black", alpha=0.8))
        
    else:
        ax.text(0.5, 0.5, f"{case_name}: Data Not Found", ha='center', transform=ax.transAxes)

    # 공통 스타일
    ax.set_ylabel(r"$C_p$", fontsize=12, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # [핵심] Y축 반전 (음수가 위로)
    ax.invert_yaxis()
    
    # [범례 설정] 첫 번째 그래프(0도)에만 범례 표시
    if i == 0:
        # 커스텀 범례 항목 생성
        legend_elements = [
            # 1. Upper Surface (파란 실선)
            Line2D([0], [0], color='royalblue', lw=2, linestyle='-', label='Upper Surface'),
            # 2. Lower Surface (빨간 점선)
            Line2D([0], [0], color='firebrick', lw=2, linestyle='--', label='Lower Surface'),
            # 3. 빈 공간 (구분선 역할)
            Line2D([0], [0], color='none', label=' '), 
            # 4. Mach 정보 (투명 선 + 라벨)
            Line2D([0], [0], color='none', label=flow_condition_text[0]), 
            # 5. Reynolds 정보 (투명 선 + 라벨)
            Line2D([0], [0], color='none', label=flow_condition_text[1])
        ]
        
        # 범례 추가
        ax.legend(handles=legend_elements, loc='lower right', fontsize=10, frameon=True)

# X축 라벨은 맨 아래에만
axes[-1].set_xlabel(r"Normalized Chord ($x/c$)", fontsize=14, fontweight='bold')
axes[-1].set_xlim(0, 1)

# 여백 조정 및 저장
plt.tight_layout(rect=[0, 0, 1, 0.98])

save_path = os.path.join(work_dir, plot_file)
plt.savefig(save_path, dpi=300)

print(f"\nSuccessfully saved final comparison plot to: {save_path}")
plt.show()