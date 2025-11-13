import pandas as pd

try:
    df = pd.read_csv("su2.csv")
    print("파일 'su2.csv'을 성공적으로 로드했습니다.")
    
    required_columns = ['Points_0', 'Points_2', 'Pressure_Coefficient']
    
    if all(col in df.columns for col in required_columns):
        df_processed = df[required_columns].copy()
        
        
        min_x = df_processed['Points_0'].min()
        max_x = df_processed['Points_0'].max()
        
        if (max_x - min_x) == 0:
            df_processed['Points_0_Normalized'] = 0.5
        else:
            df_processed['Points_0_Normalized'] = (df_processed['Points_0'] - min_x) / (max_x - min_x)
        
        df_upper = df_processed[df_processed['Points_2'] >= 0].copy()
        df_lower = df_processed[df_processed['Points_2'] < 0].copy()
        
        print(f"윗면 포인트 수: {len(df_upper)}")
        print(f"아랫면 포인트 수: {len(df_lower)}")

        upper_sorted = df_upper[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(by='Points_0_Normalized', ascending=True)
        upper_sorted['Surface'] = 'Upper'
        
        lower_sorted = df_lower[['Points_0_Normalized', 'Pressure_Coefficient']].sort_values(by='Points_0_Normalized', ascending=False)
        lower_sorted['Surface'] = 'Lower'

        combined_data = pd.concat([upper_sorted, lower_sorted])

        combined_data.to_excel('sorted_cp_by_surface.xlsx', index=False)
        
        print("\n데이터 정렬 및 결합 완료. 'sorted_cp_by_surface.csv' 파일로 저장했습니다.")
        print("파일 내용 (상위 5개):")
        print(combined_data.head())
        print("\n파일 내용 (하위 5개):")
        print(combined_data.tail())

    else:
        print(f"오류: 필요한 열 {required_columns} 중 일부가 파일에 없습니다.")

except FileNotFoundError:
    print("오류: 'su2.csv' 파일을 찾을 수 없습니다.")
except Exception as e:
    print(f"데이터 처리 중 오류가 발생했습니다: {e}")