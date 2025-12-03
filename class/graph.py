import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

try:
    # ==============================================================================
    # [사용자 설정] 물리 상수 및 파일
    # ==============================================================================
    Input_File = "32.csv"  # 사용하실 파일명 확인 필요
    
    # 1. 대기 조건 (요청하신 값 적용)
    P_inf = 101325.0       # Pa (압력)
    T_inf = 273.15         # K (온도)
    Gamma = 1.4            # 비열비 (공기 표준)
    
    # 2. 비행 조건
    Mach = 0.8             # 마하수
    AoA = 0.0              # 받음각 (deg) - 참고용
    
    # 3. 동압(q) 계산 식: q = 0.5 * gamma * P * M^2 (압축성 유동)
    q_inf = 0.5 * Gamma * P_inf * (Mach ** 2)
    
    print(f">>> 해석 조건 설정:")
    print(f"    - Mach: {Mach}")
    print(f"    - Pressure: {P_inf} Pa")
    print(f"    - Temperature: {T_inf} K")
    print(f"    - AoA: {AoA} deg")
    print(f"    => 계산된 동압(q_inf): {q_inf:.2f} Pa")
    print("\n>>> 데이터 처리 시작...")

    # 1. 파일 로드
    df = pd.read_csv(Input_File)
    print(f"파일 '{Input_File}' 로드 성공.")
    
    # 2. 압력 계수(Cp) 직접 계산
    #    데이터에 'Pressure' 열이 있으면 공식을 써서 새로 계산합니다.
    if 'Pressure' in df.columns:
        df['Cp_Calculated'] = (df['Pressure'] - P_inf) / q_inf
        print("Cp 재계산 완료: (P - P_inf) / q_inf")
    else:
        # 만약 Pressure 열이 없고 이미 Cp만 있다면 기존 열 사용
        print("주의: 'Pressure' 열이 없어 기존 'Pressure_Coefficient'를 사용합니다.")
        df['Cp_Calculated'] = df['Pressure_Coefficient']

    # 3. 필요한 열 선택 및 전처리
    #    Points_0: X좌표 (Chord 방향)
    #    Points_2: Z좌표 (Upper/Lower 구분용 - Onera M6 기준)
    required_columns = ['Points_0', 'Points_2', 'Cp_Calculated']
    
    if all(col in df.columns for col in required_columns):
        df_processed = df[required_columns].copy()

        # 4. 정규화 (Normalize X) -> x/c 계산
        min_x = df_processed['Points_0'].min()
        max_x = df_processed['Points_0'].max()
        chord_len = max_x - min_x
        
        if chord_len == 0:
            df_processed['x_c'] = 0.5
        else:
            df_processed['x_c'] = (df_processed['Points_0'] - min_x) / chord_len

        # 5. 윗면/아랫면 분리 (Points_2 기준)
        #    Onera M6는 일반적으로 Z > 0 이 윗면(Upper)입니다.
        df_upper = df_processed[df_processed['Points_2'] >= 0].copy()
        df_lower = df_processed[df_processed['Points_2'] < 0].copy()

        # 6. 정렬 (그래프 그리기 좋게 X축 기준 정렬)
        #    윗면: 앞(0) -> 뒤(1)
        upper_sorted = df_upper.sort_values(by='x_c', ascending=True)
        #    아랫면: 앞(0) -> 뒤(1) (따로 그릴 때는 오름차순이 편합니다)
        lower_sorted = df_lower.sort_values(by='x_c', ascending=True)

        # 7. 엑셀 저장 (뒷날 닫기 포함)
        upper_sorted['Surface'] = 'Upper'
        lower_sorted['Surface'] = 'Lower'
        
        # 뒷날(Trailing Edge) 닫아주기
        if not upper_sorted.empty and not lower_sorted.empty:
            upper_last = upper_sorted.iloc[-1]
            lower_last = lower_sorted.iloc[-1]
            te_cp = (upper_last['Cp_Calculated'] + lower_last['Cp_Calculated']) / 2
            closing_point = pd.DataFrame({'x_c': [1.0], 'Cp_Calculated': [te_cp], 'Surface': ['TE_Close']})
            
            combined_data = pd.concat([upper_sorted, closing_point, lower_sorted])
        else:
            combined_data = pd.concat([upper_sorted, lower_sorted])

        output_excel = 'OneraM6_Calculated_Cp_M0.8.xlsx'
        combined_data.to_excel(output_excel, index=False)
        print(f"[완료] 데이터 저장됨: {output_excel}")

        # ==============================================================================
        # [그래프 그리기] Matplotlib
        # ==============================================================================
        print(">>> 그래프 생성 중...")
        plt.figure(figsize=(10, 6))

        # 윗면 (빨간색 실선)
        plt.plot(upper_sorted['x_c'], upper_sorted['Cp_Calculated'], 'r-', label='Upper Surface', linewidth=1.5)
        
        # 아랫면 (파란색 실선)
        plt.plot(lower_sorted['x_c'], lower_sorted['Cp_Calculated'], 'b-', label='Lower Surface', linewidth=1.5)

        # 설정
        plt.gca().invert_yaxis()  # [중요] 공력 그래프는 Y축을 반대로 그립니다 (-Cp가 위로)
        plt.xlabel('x/c', fontsize=12)
        plt.ylabel('Pressure Coefficient (-Cp)', fontsize=12)
        plt.title(f'Onera M6 Pressure Distribution (Mach {Mach}, AoA {AoA} deg)', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()

        # 저장 및 출력
        output_img = 'Cp_Plot.png'
        plt.savefig(output_img, dpi=300)
        print(f"[완료] 그래프 이미지 저장됨: '{output_img}'")
        plt.show()

    else:
        print(f"오류: 필요한 열 {required_columns} 중 일부가 파일에 없습니다.")

except FileNotFoundError:
    print(f"오류: '{Input_File}' 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"오류 발생: {e}")