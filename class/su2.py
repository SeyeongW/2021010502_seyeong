import pandas as pd
import numpy as np

try:
    # 1. CSV 파일 로드
    df = pd.read_csv("su2_0.5.csv")
    print("파일 로드 성공.")

    # 2. 회전 보정을 위한 LE/TE 찾기
    id_max = df['Points_1'].idxmax()
    id_min = df['Points_1'].idxmin()

    p_max = df.loc[id_max, ['Points_1', 'Points_0']].values
    p_min = df.loc[id_min, ['Points_1', 'Points_0']].values

    # 3. 회전 각도(Theta) 계산 및 보정
    # (데이터가 기울어져 있을 수 있으므로 수평으로 눕혀줍니다)
    dx = p_max[0] - p_min[0]
    dy = p_max[1] - p_min[1]
    theta = np.arctan2(dy, dx)
    
    cos_t = np.cos(-theta)
    sin_t = np.sin(-theta)

    x = df['Points_1'].values
    y = df['Points_0'].values

    # 회전된 좌표
    df['x_rot'] = x * cos_t - y * sin_t
    df['y_rot'] = x * sin_t + y * cos_t

    # 4. [핵심 수정] 정규화 방향 반전 (Flip)
    # 이전: 최대값이 0 (Max -> Min 방향)
    # 수정: 최소값이 0 (Min -> Max 방향) -> 그래프 좌우 반전 해결
    max_x_rot = df['x_rot'].max()
    min_x_rot = df['x_rot'].min()
    chord_len = max_x_rot - min_x_rot
    
    # 최소값(Min) 지점이 앞전(0)이 되도록 설정
    df['x_c'] = (df['x_rot'] - min_x_rot) / chord_len

    # 5. 윗면/아랫면 자동 감지 (압력 기준)
    # 일단 y_rot 평균을 기준으로 그룹을 나눕니다.
    y_mean = df['y_rot'].mean()
    
    group_A = df[df['y_rot'] < y_mean].copy()
    group_B = df[df['y_rot'] >= y_mean].copy()

    # 물리 법칙 적용: 평균 압력계수(Cp)가 더 낮은(음수 쪽) 그룹이 '윗면(Upper)'입니다.
    mean_cp_A = group_A['Pressure_Coefficient'].mean()
    mean_cp_B = group_B['Pressure_Coefficient'].mean()

    if mean_cp_A < mean_cp_B:
        df_upper = group_A
        df_lower = group_B
        print("감지됨: Y좌표가 작은 쪽이 윗면(Upper)")
    else:
        df_upper = group_B
        df_lower = group_A
        print("감지됨: Y좌표가 큰 쪽이 윗면(Upper)")

    # 6. 정렬 및 저장 (그래프 그리기 좋게 정렬)
    # 윗면: 앞전(0) -> 뒷전(1)
    upper_sorted = df_upper[['x_c', 'Pressure_Coefficient']].sort_values(by='x_c', ascending=True)
    upper_sorted['Surface'] = 'Upper'

    # 아랫면: 뒷전(1) -> 앞전(0) (루프 형태 유지를 위해 역순 정렬 추천, 필요시 ascending=True로 변경 가능)
    lower_sorted = df_lower[['x_c', 'Pressure_Coefficient']].sort_values(by='x_c', ascending=False)
    lower_sorted['Surface'] = 'Lower'

    combined_data = pd.concat([upper_sorted, lower_sorted])
    combined_data.to_excel('CT_Blade_0.5_Reversed_Final.xlsx', index=False)

    print("\n[완료] 앞뒤 반전 및 상하 분리 보정 완료.")
    print("'CT_Blade_0.5_Reversed_Final.xlsx' 파일로 저장되었습니다.")
    print("\n[데이터 미리보기 - 윗면 앞부분]")
    print(combined_data.head())

except Exception as e:
    print(f"오류 발생: {e}")