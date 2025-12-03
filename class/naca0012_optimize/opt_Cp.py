import os
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv
from matplotlib.lines import Line2D

# --- 1. CONFIGURATION (AUTOMATIC PATH DETECTION) ---

# Get the directory where this script is currently running
# If you run this file from D:\CFD\SU2_work\Project\CED, this becomes that path.
current_dir = os.getcwd()
base_path = os.path.join(current_dir, "DESIGNS")
save_dir = current_dir

print(f"Current Working Directory: {current_dir}")
print(f"Target Designs Directory:  {base_path}")

# Define which design iterations to compare
initial_folder_name = "DSN_001"
final_eval_num = 32
optimized_folder_name = f"DSN_{final_eval_num:03d}"

# --- 2. DATA EXTRACTION FUNCTION ---
def extract_airfoil_data(vtu_path):
    if not os.path.exists(vtu_path):
        print(f"Error: File not found at {vtu_path}")
        return None

    try:
        # Load the mesh using PyVista
        mesh = pv.read(vtu_path)

        # Extract points
        points = mesh.points
        x = points[:, 0]
        y = points[:, 1]

        # Find Cp data field
        cp_data = None
        if 'Pressure_Coefficient' in mesh.point_data:
            cp_data = mesh.point_data['Pressure_Coefficient']
        elif 'Cp' in mesh.point_data:
            cp_data = mesh.point_data['Cp']
        
        if cp_data is None:
            print("Error: Pressure Coefficient data not found in the vtu file.")
            return None

        # --- Split and Sort Surface Data ---
        # Upper Surface (y >= 0)
        mask_up = y >= 0
        x_up = x[mask_up]
        y_up = y[mask_up]
        cp_up = cp_data[mask_up]
        idx_up = np.argsort(x_up)

        # Lower Surface (y < 0)
        mask_low = y < 0
        x_low = x[mask_low]
        y_low = y[mask_low]
        cp_low = cp_data[mask_low]
        idx_low = np.argsort(x_low)

        return {
            'x_up': x_up[idx_up], 'y_up': y_up[idx_up], 'cp_up': cp_up[idx_up],
            'x_low': x_low[idx_low], 'y_low': y_low[idx_low], 'cp_low': cp_low[idx_low]
        }

    except Exception as e:
        print(f"An error occurred while processing {vtu_path}: {e}")
        return None

# --- 3. MAIN PROCESSING ---
print("Starting Comparison Plot Generation...")

# Construct full paths to the .vtu files relative to the current directory
path_initial = os.path.join(base_path, initial_folder_name, "DIRECT", "surface_flow.vtu")
path_optimized = os.path.join(base_path, optimized_folder_name, "DIRECT", "surface_flow.vtu")

# Extract data
data_init = extract_airfoil_data(path_initial)
data_opt = extract_airfoil_data(path_optimized)

if data_init is not None and data_opt is not None:
    print("Data extraction successful. Creating combined plot...")

    # Create figure and two subplots
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(10, 12), 
                                   sharex=True, 
                                   gridspec_kw={'height_ratios': [2, 1]})

    # --- Subplot 1 (Top): Cp Distribution ---
    # Plot Initial
    ax1.plot(data_init['x_up'], data_init['cp_up'], 'k--', linewidth=1.5)
    ax1.plot(data_init['x_low'], data_init['cp_low'], 'k--', linewidth=1.5)
    
    # Plot Optimized (CHANGED COLOR HERE)
    # 'g-'를 color='hotpink', linestyle='-' 로 변경했습니다.
    ax1.plot(data_opt['x_up'], data_opt['cp_up'], color='hotpink', linestyle='-', linewidth=2)
    ax1.plot(data_opt['x_low'], data_opt['cp_low'], color='hotpink', linestyle='-', linewidth=2)

    # Settings for Cp plot
    ax1.set_ylabel("($C_p$)", fontsize=14, fontweight='bold')
    ax1.set_title(f"NACA0012 vs My_naca0012", fontsize=16)
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.invert_yaxis() # Invert Y for Cp

    # --- Subplot 2 (Bottom): Airfoil Geometry ---
    # Plot Initial
    ax2.plot(data_init['x_up'], data_init['y_up'], 'k--', linewidth=1.5)
    ax2.plot(data_init['x_low'], data_init['y_low'], 'k--', linewidth=1.5)
    
    # Plot Optimized (CHANGED COLOR HERE)
    ax2.plot(data_opt['x_up'], data_opt['y_up'], color='hotpink', linestyle='-', linewidth=2)
    ax2.plot(data_opt['x_low'], data_opt['y_low'], color='hotpink', linestyle='-', linewidth=2)

    # Settings for Geometry plot
    ax2.set_xlabel("($x/c$)", fontsize=14, fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.axis('equal') # Maintain aspect ratio
    
    # --- Legend ---
    legend_elements = [
        Line2D([0], [0], color='k', linestyle='--', linewidth=1.5, label='NACA0012'),
        Line2D([0], [0], color='hotpink', linestyle='-', linewidth=2, label='My_naca0012')
    ]
    ax1.legend(handles=legend_elements, loc='best', fontsize=12)

    # --- Save and Show ---
    plt.tight_layout()
    
    output_filename = "Comparison_Cp_Airfoil.png"
    full_save_path = os.path.join(save_dir, output_filename)
    
    plt.savefig(full_save_path, dpi=300, bbox_inches='tight')
    print(f"Successfully saved plot to: {full_save_path}")
    
    plt.show()

else:
    print("Failed to generate plot due to missing data.")