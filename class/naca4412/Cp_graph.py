import os
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv

# --- 1. CONFIGURATION (AUTOMATIC PATH DETECTION) ---
current_dir = os.getcwd()
base_path = current_dir
save_dir = current_dir

# --- 2. DATA EXTRACTION FUNCTIONS ---

def extract_airfoil_data(vtu_path):
    if not os.path.exists(vtu_path):
        print(f"Error: File not found at {vtu_path}")
        return None

    try:
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

def load_nasa_data(filename):
    """Loads NASA experimental data from a text file."""
    filepath = os.path.join(base_path, filename)
    if not os.path.exists(filepath):
        print(f"Warning: NASA data file '{filename}' not found.")
        return None, None
    
    try:
        # Skip the first 4 header lines based on your file format
        data = np.loadtxt(filepath, skiprows=4)
        x = data[:, 0]
        cp = data[:, 2]
        return x, cp
    except Exception as e:
        print(f"Error reading NASA data: {e}")
        return None, None

# --- 3. MAIN PROCESSING ---
print("Starting Cp Comparison Plot Generation...")

# Construct full paths
path_optimized = os.path.join(base_path, "surface_flow.vtu")

# Extract VTU data
data_opt = extract_airfoil_data(path_optimized)

# Load NASA data
nasa_x, nasa_cp = load_nasa_data("nasa_dat.txt")

if data_opt is not None:
    print("Data extraction successful. Creating plot...")

    # Create figure (Single plot, no subplots for geometry)
    fig, ax1 = plt.subplots(figsize=(10, 8))

    # --- Plot VTU Data (Current Result) ---
    # Plotting Upper and Lower surfaces with lines
    ax1.plot(data_opt['x_up'], data_opt['cp_up'], color='aquamarine', linestyle='-', linewidth=2, label='generated')
    ax1.plot(data_opt['x_low'], data_opt['cp_low'], color='aquamarine', linestyle='-', linewidth=2)

    # --- Plot NASA Data (Experiment) ---
    if nasa_x is not None and nasa_cp is not None:
        # Plotting as circular markers ('o') with no line connection
        # 'mfc' is marker face color (white/none for empty circles), 'mec' is edge color
        ax1.plot(nasa_x, nasa_cp, 'o', color='black', markerfacecolor='none', label='NASA Experiment (Coles & Wadcock)')
    else:
        print("Skipping NASA data plot due to loading error.")

    # --- Settings for Cp plot ---
    ax1.set_xlabel("$x/c$", fontsize=14, fontweight='bold')
    ax1.set_ylabel("$C_p$", fontsize=14, fontweight='bold')
    ax1.set_title("Pressure Coefficient Comparison(generated)", fontsize=16)
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Invert Y-axis for Cp convention
    ax1.invert_yaxis() 
    
    # Add legend
    ax1.legend(loc='best', fontsize=12)

    # --- Save and Show ---
    plt.tight_layout()
    
    output_filename = "my_4412_Cp.png"
    full_save_path = os.path.join(save_dir, output_filename)
    
    plt.savefig(full_save_path, dpi=300, bbox_inches='tight')
    print(f"Successfully saved plot to: {full_save_path}")
    
    plt.show()

else:
    print("Failed to generate plot due to missing VTU data.")