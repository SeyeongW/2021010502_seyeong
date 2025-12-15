import os
import pandas as pd
import matplotlib.pyplot as plt

# ====================================================
# 사용자 설정
# ====================================================
work_dir = r"D:\CFD\SU2_work\Project\VR-12"
aoa_list = range(0, 22, 2)  # 0, 2, ... 20

# 결과 저장 파일명
summary_file = "aerodynamic_coefficients.csv"
# ====================================================

results = []

print("Extracting data from history files...\n")

for aoa in aoa_list:
    case_dir = os.path.join(work_dir, f"deg_{aoa}")
    history_path = os.path.join(case_dir, "history.csv")

    if not os.path.exists(history_path):
        print(f"[Warning] AoA {aoa}: History file not found at {history_path}")
        continue

    try:
        # 1. CSV 파일 읽기
        df = pd.read_csv(history_path)
        
        # 2. 컬럼명 정리 (SU2는 헤더에 공백이나 따옴표가 있을 수 있음)
        df.columns = df.columns.str.replace('"', '').str.strip()
        
        # 3. 마지막 줄(수렴된 값) 가져오기
        last_row = df.iloc[-1]
        
        # 4. 필요한 값 추출 (2D 에어포일은 보통 CMz가 피칭 모멘트)
        # 만약 컬럼명이 다르면 history.csv를 열어서 정확한 이름을 확인해야 함
        cl = last_row.get("CL", last_row.get("Lift", None))
        cd = last_row.get("CD", last_row.get("Drag", None))
        cm = last_row.get("CMz", last_row.get("Momentz", None))

        results.append({
            "AoA": aoa,
            "CL": cl,
            "CD": cd,
            "CM": cm
        })
        print(f"[AoA {aoa}] CL: {cl:.4f}, CD: {cd:.4f}, CM: {cm:.4f}")

    except Exception as e:
        print(f"[Error] AoA {aoa}: Failed to process. {e}")

# ====================================================
# 데이터 저장
# ====================================================
if not results:
    print("\nNo data found.")
    exit()

df_results = pd.DataFrame(results)
save_path = os.path.join(work_dir, summary_file)
df_results.to_csv(save_path, index=False)
print(f"\nData saved to: {save_path}")

# ====================================================
# 그래프 그리기
# ====================================================
plt.style.use('default') # 기본 스타일

# 그래프 3개를 한 번에 그리기 (3행 1열)
fig, ax = plt.subplots(1, 3, figsize=(18, 5))

# 1. AoA vs CL
ax[0].plot(df_results["AoA"], df_results["CL"], marker='o', color='blue', linestyle='-', linewidth=2)
ax[0].set_title("Lift Coefficient ($C_L$)", fontsize=14)
ax[0].set_xlabel("Angle of Attack (deg)", fontsize=12)
ax[0].set_ylabel("$C_L$", fontsize=12)
ax[0].grid(True, linestyle='--', alpha=0.7)
ax[0].set_xticks(aoa_list)

# 2. AoA vs CD
ax[1].plot(df_results["AoA"], df_results["CD"], marker='s', color='red', linestyle='-', linewidth=2)
ax[1].set_title("Drag Coefficient ($C_D$)", fontsize=14)
ax[1].set_xlabel("Angle of Attack (deg)", fontsize=12)
ax[1].set_ylabel("$C_D$", fontsize=12)
ax[1].grid(True, linestyle='--', alpha=0.7)
ax[1].set_xticks(aoa_list)

# 3. AoA vs CM
ax[2].plot(df_results["AoA"], df_results["CM"], marker='^', color='green', linestyle='-', linewidth=2)
ax[2].set_title("Moment Coefficient ($C_M$)", fontsize=14)
ax[2].set_xlabel("Angle of Attack (deg)", fontsize=12)
ax[2].set_ylabel("$C_M$", fontsize=12)
ax[2].grid(True, linestyle='--', alpha=0.7)
ax[2].set_xticks(aoa_list)

plt.suptitle(f"Aerodynamic Coefficients for VR-12 Airfoil", fontsize=16)
plt.tight_layout()

# 그래프 이미지 저장
graph_save_path = os.path.join(work_dir, "Aerodynamic_Coefficients_Plot.png")
plt.savefig(graph_save_path, dpi=300)
print(f"Graph saved to: {graph_save_path}")

plt.show() # 화면에 띄우기