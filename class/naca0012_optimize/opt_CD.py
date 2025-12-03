import os
import pandas as pd
import matplotlib.pyplot as plt

# 1. Path and Settings
current_dir = os.getcwd()
base_path = os.path.join(current_dir, "DESIGNS")
save_path = current_dir
excel_path = current_dir
num_evaluations = 32

evaluations = []
drag_values = []

print("Starting data extraction...")

# 2. Iterate through folders
for i in range(1, num_evaluations + 1):
    folder_name = f"DSN_{i:03d}"
    
    # Define file paths (checking both no extension and .csv)
    # Path: D:\...\DSN_XXX\DIRECT\history_direct
    path_no_ext = os.path.join(base_path, folder_name, "DIRECT", "history_direct")
    path_csv = os.path.join(base_path, folder_name, "DIRECT", "history_direct.csv")
    
    target_file = ""
    
    # Check which file exists
    if os.path.exists(path_no_ext):
        target_file = path_no_ext
    elif os.path.exists(path_csv):
        target_file = path_csv
    
    if target_file:
        try:
            # Read CSV file
            df = pd.read_csv(target_file)
            
            # Get the last value of column J (Index 9)
            last_cd = df.iloc[-1, 8] 
            
            evaluations.append(i)
            drag_values.append(last_cd)
            
        except Exception as e:
            print(f"Error reading {folder_name}: {e}")
    else:
        print(f"File not found in: {folder_name}/DIRECT")

# 3. Save to Excel and Plot Graph
if drag_values:
    # --- Save Data to Excel (.xlsx) ---
    output_df = pd.DataFrame({
        'Evaluation': evaluations,
        'Drag_Coefficient': drag_values
    })
    
    excel_filename = "Optimization_Results.xlsx"
    save_path = os.path.join(save_path, excel_filename)
    
    try:
        output_df.to_excel(save_path, index=False)
        print(f"Excel file saved successfully: {save_path}")
    except Exception as e:
        print(f"Error saving Excel file: {e}")

    # --- Plot Graph ---
    plt.figure(figsize=(10, 8))
    
    # Plot style: Green line with diamond markers
    plt.plot(evaluations, drag_values, color='hotpink', marker='s', 
             linestyle='-', markersize=5, linewidth=1.5, label='Drag')

    # Axis labels
    plt.xlabel('EVALUATION', fontsize=12, fontweight='bold')
    plt.ylabel('DRAG', fontsize=12, fontweight='bold')
    
    # Tick settings
    plt.minorticks_on()
    plt.tick_params(axis='both', which='major', direction='in', length=6, width=1)
    plt.tick_params(axis='both', which='minor', direction='in', length=3, width=1)
    
    # Set limits
    plt.xlim(0, 33)
    image_filename = "Optimization_CD_Graph.png"
    save_path_image = os.path.join(excel_path, image_filename)
    plt.savefig(save_path_image, dpi=300, bbox_inches='tight')
    print(f"save CD_graph: {save_path_image}")
    plt.show()
    print("Graph generation complete.")
else:
    print("No data found. Please check the directory path.")