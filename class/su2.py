import pandas as pd
import numpy as np
import time
import sys

try:
    # ==============================================================================
    # [사용자 설정]
    # ==============================================================================
    FLIP_AXIS = True  # 코(LE)=1, 꼬리(TE)=0 (반대)
    
    # 물리 상수
    P_inf = 101325.0
    T_inf = 288.15
    Blade_Radius = 1.14322
    Section_Ratio = 0.5
    RPM = 2500
    rho = 1.225
    Input_File = f'{Section_Ratio}.csv'
    output_filename = f'CT_Blade_rR{Section_Ratio}.xlsx'
    
    # ==============================================================================
    # [계산 시작]
    # ==============================================================================
    
    df = pd.read_csv(Input_File)
    
    Omega = RPM * (2 * np.pi) / 60
    r_local = Blade_Radius * Section_Ratio
    v_local = r_local * Omega
    q_inf = 0.5 * rho * (v_local ** 2)

    print(f">>> 총 {len(df)}개 포인트에 대한 Cp 계산을 시작합니다...\n")
    print(f"{'ID':<5} | {'Pressure (Pa)':<15} | {'Calculated Cp':<15}")
    print("-" * 45)
    
    cp_list = []
    
    for index, row in df.iterrows():
        pressure = row['Pressure']
        cp = (pressure - P_inf) / q_inf
        cp_list.append(cp)
        
        print(f"{index:<5} | {pressure:<15.2f} | {cp:<15.4f}")
        time.sleep(0.005) 

    df['Cp_Calculated'] = cp_list
    print("-" * 45)
    print(">>> Cp 계산 완료.\n")

    # ==============================================================================
    # [형상 정렬 및 저장] (출력 최소화)
    # ==============================================================================
    print(">>> 형상 정렬 및 파일 저장 중...", end="")
    
    idx_stag = df['Pressure'].idxmax()
    le_x = df.loc[idx_stag, 'Points_1']
    le_y = df.loc[idx_stag, 'Points_0']

    df['x_trans'] = df['Points_1'] - le_x
    df['y_trans'] = df['Points_0'] - le_y

    df['dist'] = np.sqrt(df['x_trans']**2 + df['y_trans']**2)
    idx_te = df['dist'].idxmax()
    
    te_x = df.loc[idx_te, 'x_trans']
    te_y = df.loc[idx_te, 'y_trans']

    angle = np.arctan2(te_y, te_x)
    cos_a = np.cos(-angle)
    sin_a = np.sin(-angle)

    x = df['x_trans'].values
    y = df['y_trans'].values

    df['x_rot'] = x * cos_a - y * sin_a
    df['y_rot'] = x * sin_a + y * cos_a

    chord_len = df.loc[idx_te, 'x_rot']
    df['x_c'] = df['x_rot'] / chord_len
    
    if FLIP_AXIS:
        df['x_c'] = 1.0 - df['x_c']

    group_A = df[df['y_rot'] <= 0].copy()
    group_B = df[df['y_rot'] > 0].copy()

    if group_A['Cp_Calculated'].mean() < group_B['Cp_Calculated'].mean():
        df_upper = group_A
        df_lower = group_B
    else:
        df_upper = group_B
        df_lower = group_A

    te_row = df.loc[idx_te].copy()
    if idx_te not in df_upper.index:
        df_upper = pd.concat([df_upper, te_row.to_frame().T])
    if idx_te not in df_lower.index:
        df_lower = pd.concat([df_lower, te_row.to_frame().T])

    upper_sorted = df_upper.sort_values(by='x_c', ascending=True)
    lower_sorted = df_lower.sort_values(by='x_c', ascending=False)
    
    cols = ['x_c', 'Cp_Calculated']
    upper_final = upper_sorted[cols].copy()
    upper_final.columns = ['x_c', 'Pressure_Coefficient']
    upper_final['Surface'] = 'Upper'
    
    lower_final = lower_sorted[cols].copy()
    lower_final.columns = ['x_c', 'Pressure_Coefficient']
    lower_final['Surface'] = 'Lower'

    combined_data = pd.concat([upper_final, lower_final])
    combined_data.to_excel(output_filename, index=False)
    
    print(f" 완료!\n>>> 파일명: '{output_filename}'")

except Exception as e:
    print(f"오류 발생: {e}")