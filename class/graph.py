import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

try:
    # ==============================================================================
    # [사용자 설정] 물리 상수 및 파일
    # ==============================================================================
    Input_File = "su2.csv"
    
    # 대기 조건 (아까와 동일한 상수 적용)
    P_inf = 101325.0       # Pa
    T_inf = 288.15         # K
    Gamma = 1.4            # 비열비
    
    # [중요] 동압(q) 계산 기준
    # Onera M6(고정익)라면 Mach를 사용하고, 로터라면 RPM/Radius를 사용해야 합니다.
    # 여기서는 Onera M6 표준 조건(Mach 0.8395)을 적용했습니다.
    Mach = 0.8395          
    
    # 동압 계산 식: q = 0.5 * gamma * P * M^2 (압축성 유동)
    q_inf = 0.5 * Gamma * P_inf * (Mach ** 2)
    
    print(f">>> 설정된 동압(q_inf): {q_inf:.2f} Pa (Mach={Mach})")
    print(">>> 데이터 처리 시작...")

    # 1. 파일 로드
    df = pd.read_csv(Input_File)
    print(f"파일 '{Input_File}' 로드 성공.")
    
    # 2. Cp 계산 (Pressure 열이 있어야 함)
    if 'Pressure' in df.columns:
        df['Cp_Calculated'] = (df['Pressure'] - P_inf) / q_inf
        print("Cp 재계산 완료.")
    else:
        # 만약 Pressure 열이 없고 이미 Cp만 있다면 기존 열 사용
        print("주의: 'Pressure' 열이 없어 기존 'Pressure_Coefficient'를 사용합니다.")
        df['Cp_Calculated'] = df['Pressure_Coefficient']

    # 3. 필요한 열 선택 및 전처리
    #    Points_0: X좌표, Points_2: 표면 구분(Z좌표)
    required_columns = ['Points_0', 'Points_2', 'Cp_Calculated']
    df_processed = df[required_columns].copy()

    # 4. 정규화 (Normalize X)
    min_x = df_processed['Points_0'].min()
    max_x = df_processed['Points_0'].max()
    chord_len = max_x - min_x
    
    if chord_len == 0:
        df_processed['x_c'] = 0.5
    else:
        df_processed['x_c'] = (df_processed['Points_0'] - min_x) / chord_len

    # 5. 윗면/아랫면 분리 (Points_2 기준)
    #    Onera M6는 Z > 0 이 윗면
    df_upper = df_processed[df_processed['Points_2'] >= 0].copy()
    df_lower = df_processed[df_processed['Points_2'] < 0].copy()

    # 6. 정렬
    # 윗면: LE(0) -> TE(1)
    upper_sorted = df_upper.sort_values(by='x_c', ascending=True)
    # 아랫면: LE(0) -> TE(1) (그래프 그리기 좋게 오름차순 정렬)
    lower_sorted = df_lower.sort_values(by='x_c', ascending=True)

    # 7. 엑셀 저장
    upper_sorted['Surface'] = 'Upper'
    lower_sorted['Surface'] = 'Lower'
    
    # 뒷날 닫기 (선택 사항)
    upper_last = upper_sorted.iloc[-1]
    lower_last = lower_sorted.iloc[-1] # 둘 다 오름차순이므로 마지막이 TE
    te_cp = (upper_last['Cp_Calculated'] + lower_last['Cp_Calculated']) / 2
    closing_point = pd.DataFrame({'x_c': [1.0], 'Cp_Calculated': [te_cp], 'Surface': ['TE_Close']})

    combined_data = pd.concat([upper_sorted, closing_point, lower_sorted])
    output_excel = 'OneraM6_Calculated_Cp.xlsx'
    combined_data.to_excel(output_excel, index=False)
    print(f"[완료] 엑셀 저장됨: {output_excel}")

    # ==============================================================================
    # [그래프 그리기] Matplotlib
    # ==============================================================================
    print(">>> 그래프 생성 중...")
    plt.figure(figsize=(10, 6))

    # 윗면 (빨간색)
    plt.plot(upper_sorted['x_c'], upper_sorted['Cp_Calculated'], 'r-', label='Upper Surface', linewidth=1.5)
    
    # 아랫면 (파란색)
    plt.plot(lower_sorted['x_c'], lower_sorted['Cp_Calculated'], 'b-', label='Lower Surface', linewidth=1.5)

    # 설정
    plt.gca().invert_yaxis()  # Y축 반전 (공력 그래프 표준)
    plt.xlabel('x/c', fontsize=12)
    plt.ylabel('Pressure Coefficient (-Cp)', fontsize=12)
    plt.title(f'Pressure Distribution (Mach {Mach})', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # 저장 및 출력
    plt.savefig('Cp_Plot_OneraM6.png', dpi=300)
    print("[완료] 그래프 이미지 저장됨: 'Cp_Plot_OneraM6.png'")
    plt.show()

except Exception as e:
    print(f"오류 발생: {e}")