import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# ====================================================
# [User Settings]
# ====================================================
work_dir = os.getcwd()
print(f"Current Working Directory: {work_dir}")

# File names
history_name = "history.csv"
summary_file = "aerodynamic_coefficients.csv"

# Plot filenames (Separated)
plot_file_cl = "Lift_Coefficient_Plot.png"
plot_file_cd = "Drag_Coefficient_Plot.png"
plot_file_cm = "Moment_Coefficient_Plot.png"

# Plot options
show_value_labels = True  # Show values next to points
label_every_n_points = 1  # Labeling interval

# ====================================================

def find_cases(root: str):
    cases = []
    pattern = re.compile(r"^(aoa|deg)_?(\d+)$", re.IGNORECASE)

    for name in os.listdir(root):
        full_path = os.path.join(root, name)
        if not os.path.isdir(full_path):
            continue

        m = pattern.match(name)
        if not m:
            continue

        aoa = int(m.group(2))
        cases.append((aoa, full_path, name))

    cases.sort(key=lambda x: x[0])
    return cases


def get_last_coeffs(history_path: str):
    try:
        df = pd.read_csv(history_path)
    except Exception as e:
        raise ValueError(f"Cannot read CSV: {e}")

    df.columns = df.columns.astype(str).str.replace('"', '').str.strip()

    if df.empty:
        raise ValueError("CSV is empty.")

    last = df.iloc[-1]

    def pick(*keys):
        for k in keys:
            if k in df.columns:
                return float(last[k])
        return None

    cl = pick("CL", "LIFT", "Lift", "CLift", "C_L")
    cd = pick("CD", "DRAG", "Drag", "CDrag", "C_D")
    cm = pick("CMz", "CM_Z", "Momentz", "CM", "C_M", "MOMENT_Z")

    if cl is None or cd is None:
        raise ValueError(f"Columns not found. Available: {list(df.columns)}")
    
    if cm is None: cm = 0.0

    return cl, cd, cm


# 1. Find and Extract
cases = find_cases(work_dir)
if not cases:
    print(f"[Error] No case folders found.")
    exit(1)

results = []
print("Extracting aerodynamic coefficients...\n")

for aoa, case_dir, case_name in cases:
    history_path = os.path.join(case_dir, history_name)
    if not os.path.exists(history_path):
        continue
    try:
        cl, cd, cm = get_last_coeffs(history_path)
        results.append({"AoA": aoa, "CL": cl, "CD": cd, "CM": cm})
        print(f"[{case_name}] AoA={aoa:2d} | CL={cl:.5f}, CD={cd:.5f}, CM={cm:.5f}")
    except Exception as e:
        print(f"[Fail] {case_name}: {e}")

if not results:
    exit(1)

df_results = pd.DataFrame(results).sort_values("AoA").reset_index(drop=True)
save_path = os.path.join(work_dir, summary_file)
df_results.to_csv(save_path, index=False)
print(f"\nResults saved to: {save_path}")


# ====================================================
# [Plotting Helper Function]
# ====================================================
def plot_single_graph(x_data, y_data, ylabel, title, save_name, invert_yaxis=False):
    plt.figure(figsize=(8, 6)) # Single plot size
    
    # Style
    plot_kw = {
        "linestyle": "-",       
        "linewidth": 2.0,       
        "marker": "o",          
        "markersize": 6,        
        "color": "royalblue",   
        "markerfacecolor": "white", 
        "markeredgewidth": 1.5  
    }
    
    plt.plot(x_data, y_data, **plot_kw)
    plt.xlabel("Angle of Attack (deg)", fontsize=12, fontweight='bold')
    plt.ylabel(ylabel, fontsize=12, fontweight='bold')
    plt.title(title, fontsize=14, fontweight='bold')
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(x_data.tolist()) # Force integer ticks for AoA

    # Set natural Y-limits (Margin)
    ymin, ymax = y_data.min(), y_data.max()
    span = ymax - ymin
    if span == 0: span = 0.1
    margin = 0.1
    plt.ylim(ymin - span*margin, ymax + span*margin)

    # Invert Y-Axis if requested (For Moment)
    if invert_yaxis:
        plt.gca().invert_yaxis()

    # Annotations
    if show_value_labels:
        for i in range(len(df_results)):
            if i % label_every_n_points != 0:
                continue
            
            xi = x_data[i]
            yi = y_data[i]
            
            # Position adjustment based on axis direction
            # Even if inverted, 'offset points' works in screen coordinates (up is up)
            xytext_offset = (0, 8) 
            
            plt.annotate(
                f"{yi:.4f}", 
                (xi, yi), 
                textcoords="offset points", 
                xytext=xytext_offset, 
                ha='center', 
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7)
            )

    plt.tight_layout()
    save_full_path = os.path.join(work_dir, save_name)
    plt.savefig(save_full_path, dpi=300)
    plt.close() # Close figure to free memory
    print(f"Graph saved: {save_full_path}")


# ====================================================
# [Generate 3 Separate Plots]
# ====================================================

x = df_results["AoA"]

# 1. Lift Coefficient (CL)
plot_single_graph(
    x, df_results["CL"], 
    r"Lift Coefficient ($C_L$)", 
    "Lift Coefficient vs AoA", 
    plot_file_cl,
    invert_yaxis=False
)

# 2. Drag Coefficient (CD)
plot_single_graph(
    x, df_results["CD"], 
    r"Drag Coefficient ($C_D$)", 
    "Drag Coefficient vs AoA", 
    plot_file_cd,
    invert_yaxis=False
)

# 3. Moment Coefficient (CM) -> Inverted Y-Axis
plot_single_graph(
    x, df_results["CM"], 
    r"Moment Coefficient ($C_M$)", 
    "Moment Coefficient vs AoA", 
    plot_file_cm,
    invert_yaxis=True  # 음수가 위로 가도록 설정
)