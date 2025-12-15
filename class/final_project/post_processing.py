import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# ====================================================
# 사용자 설정
# ====================================================
work_dir = os.getcwd()
print(work_dir)

# history 파일명 (너 폴더 구조 기준)
history_name = "history.csv"

# 결과 저장 파일명
summary_file = "aerodynamic_coefficients.csv"

# 그래프 저장 파일명
plot_file = "Aerodynamic_Coefficients_Plot.png"

# 값 라벨 표시 옵션 (너무 지저분하면 False)
show_value_labels = True

# 라벨은 몇 개 간격으로 찍을지 (2면 0,4,8...처럼 듬성듬성)
label_every_n_points = 2

# ====================================================


def find_cases(root: str):
    """
    현재 폴더(work_dir) 안에서
    - aoa_00, aoa_02 ... (또는 aoa_0)
    - deg_00, deg_02 ... (또는 deg_0)
    형태를 자동으로 찾아서 (aoa, case_dir) 리스트로 반환
    """
    cases = []
    pattern = re.compile(r"^(aoa|deg)_(\d+)$", re.IGNORECASE)

    for name in os.listdir(root):
        full = os.path.join(root, name)
        if not os.path.isdir(full):
            continue

        m = pattern.match(name)
        if not m:
            continue

        aoa = int(m.group(2))
        cases.append((aoa, full, name))

    cases.sort(key=lambda x: x[0])
    return cases


def get_last_coeffs(history_path: str):
    df = pd.read_csv(history_path)

    # 컬럼명 정리
    df.columns = df.columns.astype(str).str.replace('"', '').str.strip()

    last = df.iloc[-1]

    # SU2 버전에 따라 컬럼명이 다를 수 있어서 후보를 여러 개 둠
    def pick(*keys):
        for k in keys:
            if k in df.columns:
                return float(last[k])
        return None

    cl = pick("CL", "LIFT", "Lift", "CLift", "C_L")
    cd = pick("CD", "DRAG", "Drag", "CDrag", "C_D")
    cm = pick("CMz", "CM_Z", "Momentz", "CM", "C_M")

    return cl, cd, cm


cases = find_cases(work_dir)
if not cases:
    raise RuntimeError(
        f"No case folders found in {work_dir}\n"
        "Expected: aoa_00, aoa_02... or deg_00, deg_02... (also supports aoa_0/deg_0)."
    )

results = []
print("Extracting data from history files...\n")

for aoa, case_dir, case_name in cases:
    history_path = os.path.join(case_dir, history_name)

    if not os.path.exists(history_path):
        print(f"[Warning] AoA {aoa}: history not found -> {history_path}")
        continue

    try:
        cl, cd, cm = get_last_coeffs(history_path)
        results.append({"AoA": aoa, "CL": cl, "CD": cd, "CM": cm})
        print(f"[{case_name}] CL={cl:.6f}, CD={cd:.6f}, CM={cm:.6f}")
    except Exception as e:
        print(f"[Error] {case_name}: failed to parse history.csv -> {e}")

if not results:
    raise RuntimeError("No data extracted. Check history.csv files / column names.")

df_results = pd.DataFrame(results).sort_values("AoA").reset_index(drop=True)

# 저장
save_path = os.path.join(work_dir, summary_file)
df_results.to_csv(save_path, index=False)
print(f"\nData saved to: {save_path}")

# ====================================================
# Plot (Fig 스타일: 3행 1열, 범례 박스/위치 비슷하게)
# ====================================================
plt.style.use("default")

fig, ax = plt.subplots(3, 1, figsize=(7.2, 10.0), sharex=True)

# SU2 line style (너가 준 그림처럼 파란 점선 느낌)
line_kw = dict(linestyle="--", linewidth=2.0, marker="o", markersize=5)

# 1) CL
ax[0].plot(df_results["AoA"], df_results["CL"], label="SU2", **line_kw)
ax[0].set_ylabel("Lift Coefficient")
ax[0].grid(True, linestyle="--", alpha=0.5)
ax[0].legend(loc="lower center", frameon=True)

# 2) CD
ax[1].plot(df_results["AoA"], df_results["CD"], label="SU2", **line_kw)
ax[1].set_ylabel("Drag Coefficient")
ax[1].grid(True, linestyle="--", alpha=0.5)
ax[1].legend(loc="upper left", frameon=True)

# 3) CM
ax[2].plot(df_results["AoA"], df_results["CM"], label="SU2", **line_kw)
ax[2].set_ylabel("Moment Coefficient")
ax[2].set_xlabel("AoA")
ax[2].grid(True, linestyle="--", alpha=0.5)
ax[2].legend(loc="lower left", frameon=True)

# x ticks: 있는 AoA만
ax[2].set_xticks(df_results["AoA"].tolist())

# 값 라벨(적당히): 너무 빽빽하면 간격 둬서 표기
if show_value_labels:
    for i in range(len(df_results)):
        if i % label_every_n_points != 0:
            continue
        aoa = df_results.loc[i, "AoA"]

        # CL 라벨
        cl = df_results.loc[i, "CL"]
        ax[0].annotate(f"{cl:.2f}", (aoa, cl), textcoords="offset points", xytext=(6, 6), fontsize=9)

        # CD 라벨
        cd = df_results.loc[i, "CD"]
        ax[1].annotate(f"{cd:.3f}", (aoa, cd), textcoords="offset points", xytext=(6, 6), fontsize=9)

        # CM 라벨
        cm = df_results.loc[i, "CM"]
        ax[2].annotate(f"{cm:.3f}", (aoa, cm), textcoords="offset points", xytext=(6, 6), fontsize=9)

fig.suptitle("VR-12 Airfoil (Mach=0.3, Re=2.6e6) — SU2 Results", fontsize=12)
plt.tight_layout(rect=[0, 0, 1, 0.97])

plot_path = os.path.join(work_dir, plot_file)
plt.savefig(plot_path, dpi=300)
print(f"Plot saved to: {plot_path}")

plt.show()
