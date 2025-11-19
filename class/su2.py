import pandas as pd

try:
    # 1. Load the CSV file
    #    'su2.csv' contains the sectional data extracted from SU2
    df = pd.read_csv("su2.csv")
    print("Successfully loaded 'su2.csv' file.")
    
    # 2. Required columns:
    #    Points_0 → chordwise x-coordinate (Excel column M)
    #    Points_2 → spanwise/height coordinate used to distinguish upper/lower surface (Excel column O)
    #    Pressure_Coefficient → Cp values (Excel column R)
    required_columns = ['Points_0', 'Points_2', 'Pressure_Coefficient']
    
    # 3. Check that all required columns exist in the CSV
    if all(col in df.columns for col in required_columns):
        
        # Work on a copy that only contains the necessary columns
        df_processed = df[required_columns].copy()
        
        # 4. Normalize Points_0 (x-coordinate) to the range [0, 1]
        #    This scales the airfoil chord so Cp can be plotted vs x/c
        min_x = df_processed['Points_0'].min()
        max_x = df_processed['Points_0'].max()
        
        if (max_x - min_x) == 0:
            # If all x values are identical, avoid division by zero
            df_processed['Points_0_Normalized'] = 0.5
        else:
            df_processed['Points_0_Normalized'] = (df_processed['Points_0'] - min_x) / (max_x - min_x)
        
        # 5. Split data into upper and lower surfaces using Points_2
        #    Points_2 > 0  → upper surface
        #    Points_2 < 0  → lower surface
        #    (In this SU2 setup, the sign of Points_2 indicates which side of the section the point lies on.)
        df_upper = df_processed[df_processed['Points_2'] >= 0].copy()
        df_lower = df_processed[df_processed['Points_2'] < 0].copy()

        # 6. Sort upper surface points in ascending x (from LE to TE)
        #    Pressure_Coefficient moves along with the normalized x-coordinate
        upper_sorted = df_upper[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(
            by='Points_0_Normalized', ascending=True)
        upper_sorted['Surface'] = 'Upper'
        
        # 7. Sort lower surface points in descending x (to follow the typical Cp loop order)
        lower_sorted = df_lower[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(
            by='Points_0_Normalized', ascending=False)
        lower_sorted['Surface'] = 'Lower'

        # 8. Combine the two surfaces: upper first, then lower
        combined_data = pd.concat([upper_sorted, lower_sorted])

        # 9. Save the combined Cp data to an Excel file
        #    The file will contain:
        #      Points_0_Normalized | Pressure_Coefficient | Surface (Upper/Lower)
        combined_data.to_excel('sorted_cp_by_surface.xlsx', index=False)
        
        print("\nData sorting and combination complete. Saved to 'sorted_cp_by_surface.xlsx'.")

    else:
        print(f"Error: Required columns {required_columns} not found in the file.")

except FileNotFoundError:
    print("Error: 'su2.csv' file not found.")
except Exception as e:
    print(f"An error occurred during data processing: {e}")
