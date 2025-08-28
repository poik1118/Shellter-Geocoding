import webbrowser
import pandas as pd
import folium
from folium import Popup, Icon, plugins
import json
import re
import requests
import os
import traceback

def download_real_korea_boundaries():
    """실제 한국 행정구역 경계선 GeoJSON을 다운로드합니다."""
    
    geojson_url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea-provinces-2018-geo.json"
    
    try:
        print(f"다운로드 시도: {geojson_url}")
        response = requests.get(geojson_url, timeout=10)
        if response.status_code == 200:
            geojson_data = response.json()
            print(f"성공적으로 다운로드됨: {len(geojson_data['features'])}개 지역")
            return geojson_data
        else:
            print(f"다운로드 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"다운로드 오류: {e}")
        return None

def parse_location_data():
    """지점현황 데이터를 파싱하여 지역별 감정평가기관 수를 계산합니다."""
    
    csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '주택도시보증공사_전세보증금반환보증_선정_정평가기관_GEO.csv')
    df = pd.read_csv(csv_file_path)
    location_counts = {}
    
    print("=== 원본 데이터 확인 ===")
    for index, row in df.iterrows():
        locations = str(row.iloc[7])
        print(f"행 {index+1}: {locations}")
    print("\n")
    
    # 각 행의 지점현황을 파싱
    for index, row in df.iterrows():
        locations = str(row.iloc[7])
        
        # 먼저 괄호가 있는 지역들을 처리
        bracket_pattern = r'([가-힣]+)\([^)]+\)'
        bracket_matches = re.findall(bracket_pattern, locations)
        
        # 괄호가 있는 지역들을 제거한 후 나머지 지역들 처리
        cleaned_locations = re.sub(r'[가-힣]+\([^)]+\)', '', locations)
        
        # 각 행에서 이미 처리된 지역을 추적 (중복 방지)
        processed_regions = set()
        
        # 1. 괄호가 있는 지역들 처리 (메인 지역만 카운트)
        for main_region in bracket_matches:
            # 메인 지역을 정식 명칭으로 변환
            if main_region == '경기':
                main_region = '경기도'
            elif main_region == '강원':
                main_region = '강원도'
            elif main_region == '충북':
                main_region = '충청북도'
            elif main_region == '충남':
                main_region = '충청남도'
            elif main_region == '전북':
                main_region = '전라북도'
            elif main_region == '전남':
                main_region = '전라남도'
            elif main_region == '경북':
                main_region = '경상북도'
            elif main_region == '경남':
                main_region = '경상남도'
            elif main_region == '제주':
                main_region = '제주특별자치도'
            
            # 메인 지역이 이미 처리되지 않았다면 카운트
            if main_region not in processed_regions:
                if main_region in location_counts:
                    location_counts[main_region] += 1
                else:
                    location_counts[main_region] = 1
                processed_regions.add(main_region)
                print(f"괄호 지역: {main_region} (1개 추가)")
        
        # 2. 괄호가 없는 단일 지역들 처리
        if cleaned_locations.strip():
            # 콤마로 분리하고 공백 제거
            single_locations = [loc.strip() for loc in cleaned_locations.split(',') if loc.strip()]
            
            for location in single_locations:
                # 괄호가 제대로 닫히지 않은 경우 처리
                if '(' in location and ')' not in location:
                    location = location.split('(')[0].strip()
                elif ')' in location and '(' not in location:
                    location = location.split(')')[0].strip()
                
                if location and location != '' and len(location) > 1:
                    # 지역명 정규화
                    if location == '경기':
                        location = '경기도'
                    elif location == '강원':
                        location = '강원도'
                    elif location == '충북':
                        location = '충청북도'
                    elif location == '충남':
                        location = '충청남도'
                    elif location == '전북':
                        location = '전라북도'
                    elif location == '전남':
                        location = '전라남도'
                    elif location == '경북':
                        location = '경상북도'
                    elif location == '경남':
                        location = '경상남도'
                    elif location == '제주':
                        location = '제주특별자치도'
                    
                    # 이미 처리되지 않았다면 카운트
                    if location not in processed_regions:
                        if location in location_counts:
                            location_counts[location] += 1
                        else:
                            location_counts[location] = 1
                        processed_regions.add(location)
                        print(f"  단일 지역: {location} (1개 추가)")
    
    return location_counts

def get_color_by_count(count):
    """감정평가기관 수에 따라 색상을 반환합니다. (5단위 세분화)"""
    if count >= 35:
        return '#8B0000'  # 진한 빨강 (35개 이상)
    elif count >= 30:
        return '#DC143C'  # 진한 빨강 (30-34개)
    elif count >= 25:
        return '#FF4500'  # 주황빨강 (25-29개)
    elif count >= 20:
        return '#FF6347'  # 토마토색 (20-24개)
    elif count >= 15:
        return '#FF7F50'  # 산호색 (15-19개)
    elif count >= 10:
        return '#FFA07A'  # 연한 연어색 (10-14개)
    elif count >= 5:
        return '#FFB6C1'  # 연한 분홍색 (5-9개)
    else:
        return '#F0F8FF'  # 연한 하늘색 (5개 미만)

def style_function(feature):
    """GeoJSON 스타일 함수"""
    region_name = feature['properties']['name']
    count = feature['properties'].get('count', 0)
    
    return {
        'fillColor': get_color_by_count(count),
        'color': '#000000',
        'weight': 2,
        'fillOpacity': 0.4,
        'opacity': 0.8
    }

def highlight_function(feature):
    """호버 시 강조 효과"""
    return {
        'fillColor': '#FFFF00',
        'color': '#000000',
        'weight': 3,
        'fillOpacity': 0.9,
        'opacity': 1
    }

def create_integrated_map():
    """마커와 분포도를 통합한 지도를 생성합니다."""
    
    try:
        print("=== 감정평가기관 통합 지도 생성 시작 ===")
        print("CSV 파일을 읽는 중...")
        
        # CSV 파일 읽기
        csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '주택도시보증공사_전세보증금반환보증_선정_정평가기관_GEO.csv')
        df = pd.read_csv(csv_file_path)
        print(f"CSV 파일 읽기 완료. 총 {len(df)}개 행을 읽었습니다.")
        
        # 한국 중심 좌표
        korea_center = [36.5, 127.5]
        
        print("지도를 생성하는 중...")
        # 지도 생성 (기본 타일 없이)
        m = folium.Map(
            location=korea_center,
            zoom_start=7,
            tiles=None,  # 기본 타일 제거
            attributionControl=False  # 저작권 표시 제거
        )
        
        # Google 타일 레이어 4가지 추가
        print("Google 타일 레이어를 추가하는 중...")
        
        # 1. Google 일반지도 (Streets) - 첫 번째 레이어
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='© Google Maps',
            name='Google 일반지도',
            overlay=False,
            control=True
        ).add_to(m)

        # 2. Google 지형지도 (Terrain) - 두 번째 레이어
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            attr='© Google Terrain',
            name='Google 지형지도',
            overlay=False,
            control=True
        ).add_to(m)
        
        # 3. Google 위성지도 (Satellite) - 세 번째 레이어
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='© Google Satellite',
            name='Google 위성지도',
            overlay=False,
            control=True
        ).add_to(m)
        
        # 4. OpenStreetMap - 마지막 레이어 (기본 타일)
        folium.TileLayer(
            tiles='OpenStreetMap',
            attr='© OpenStreetMap contributors',
            name='OpenStreetMap',
            overlay=False,
            control=True
        ).add_to(m)
        
        # 분포도 데이터 처리
        print("지역별 분포도 데이터를 처리하는 중...\n")
        location_counts = parse_location_data()
        
        print("\n=== 최종 지역별 감정평가기관 수 ===")
        for location, count in sorted(location_counts.items()):
            print(f"{location}: {count}개")
        
        # 실제 행정구역 경계선 데이터 가져오기
        geojson_data = download_real_korea_boundaries()
        
        if geojson_data is not None:
            print(f"\n=== GeoJSON 데이터 처리 ===")
            print(f"총 지역 수: {len(geojson_data['features'])}")
            
            # 지역명 매핑 (약칭 -> 정식명칭)
            name_mapping = {
                '서울': '서울특별시',
                '부산': '부산광역시', 
                '대구': '대구광역시',
                '인천': '인천광역시',
                '광주': '광주광역시',
                '대전': '대전광역시',
                '울산': '울산광역시',
                '세종': '세종특별자치시'
            }
            
            # 각 지역의 데이터를 GeoJSON에 추가
            for feature in geojson_data['features']:
                region_name = feature['properties']['name']
                
                # 정식명칭으로 직접 매핑 시도
                if region_name in location_counts:
                    feature['properties']['count'] = location_counts[region_name]
                    print(f"✓ {region_name}: {location_counts[region_name]}개 매핑됨")
                else:
                    # 약칭으로 매핑 시도
                    mapped_count = 0
                    for short_name, full_name in name_mapping.items():
                        if full_name == region_name and short_name in location_counts:
                            mapped_count = location_counts[short_name]
                            break
                    
                    if mapped_count > 0:
                        feature['properties']['count'] = mapped_count
                        print(f"✓ {region_name} ({short_name}): {mapped_count}개 매핑됨")
                    else:
                        feature['properties']['count'] = 0
                        print(f"✗ {region_name}: 데이터 없음 (0개)")
            
            # GeoJSON 레이어 추가 (분포도)
            folium.GeoJson(
                geojson_data,
                name='지역별 분포도',
                style_function=style_function,
                highlight_function=highlight_function,
                overlay=True ,  # 오버레이 레이어로 설정
                control=True,  # 레이어 컨트롤에 표시
                show=False,  # 기본적으로 숨김
                tooltip=folium.GeoJsonTooltip(
                    fields=['name', 'count'],
                    aliases=['지역', '감정평가기관 수'],
                    localize=True,
                    sticky=False,
                    labels=True,
                    style="""
                        background-color: #FFFFFF;
                        border: 2px solid black;
                        border-radius: 3px;
                        box-shadow: 3px;
                    """
                ),
                popup=folium.GeoJsonPopup(
                    fields=['name', 'count'],
                    aliases=['지역', '감정평가기관 수'],
                    localize=True,
                    labels=True,
                    style="background-color: yellow;",
                )
            ).add_to(m)
        
        # 마커 추가
        print("\n마커를 추가하는 중...")
        marker_count = 0
        for idx, row in df.iterrows():
            try:
                # 위도, 경도 추출
                lat = float(row['위도'])
                lng = float(row['경도'])
                
                # 팝업 내용 생성
                popup_content = f"""
                <div style="width: 300px;">
                    <h4 style="margin: 0 0 10px 0; color: #2c3e50;">{row['업체명']}</h4>
                    <p style="margin: 5px 0;"><strong>연락처:</strong> {row['연락처']}</p>
                    <p style="margin: 5px 0;"><strong>주소:</strong> {row['주소']}</p>
                    <p style="margin: 5px 0;"><strong>카카오톡:</strong> {row['이메일']}</p>
                    <p style="margin: 5px 0;"><strong>지점현황:</strong> {row['지점현황']}</p>
                </div>
                """
                
                # 마커 추가
                folium.Marker(
                    location=[lat, lng],
                    popup=Popup(popup_content, max_width=350),
                    tooltip=row['업체명'],
                    icon=Icon(color='red', icon='info-sign')
                ).add_to(m)
                
                marker_count += 1
                
            except (ValueError, TypeError) as e:
                print(f"행 {idx+1} 처리 중 오류: {e}")
                continue
        
        print(f"총 {marker_count}개의 마커를 추가했습니다.\n")
        
        # 범례 추가 (5단위 세분화 색상 기준)
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 20px; right: 20px; width: 220px; height: 310px; 
                    background-color: white; border:2px solid #666; z-index:9999; 
                    font-size:12px; padding: 15px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1)">
        <h4 style="margin: 0 0 5px 0; color: #2c3e50; text-align: center;">감정평가기관 분포</h4>
        <p style="margin: 0 0 15px 0; color: #7f8c8d; text-align: center; font-size: 14px;">상단 메뉴를 통해 켜보세요.</p>
        <p style="margin: 6px 0;"><span style="color:#8B0000; font-size: 16px;">●</span> 35개 이상</p>
        <p style="margin: 6px 0;"><span style="color:#DC143C; font-size: 16px;">●</span> 30-34개</p>
        <p style="margin: 6px 0;"><span style="color:#FF4500; font-size: 16px;">●</span> 25-29개</p>
        <p style="margin: 6px 0;"><span style="color:#FF6347; font-size: 16px;">●</span> 20-24개</p>
        <p style="margin: 6px 0;"><span style="color:#FF7F50; font-size: 16px;">●</span> 15-19개</p>
        <p style="margin: 6px 0;"><span style="color:#FFA07A; font-size: 16px;">●</span> 10-14개</p>
        <p style="margin: 6px 0;"><span style="color:#FFB6C1; font-size: 16px;">●</span> 5-9개</p>
        <p style="margin: 6px 0;"><span style="color:#F0F8FF; font-size: 16px;">●</span> 5개 미만</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # 레이어 컨트롤 추가
        folium.LayerControl().add_to(m)
        
        # 전체화면 버튼 추가
        plugins.Fullscreen().add_to(m)
        
        print("지도를 저장하는 중...")
        # 지도 저장
        output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'html', '감정평가기관_지도.html')
        m.save(output_file)
        
        print(f"통합 지도가 '{output_file}' 파일로 저장되었습니다.")
        print(f"총 {marker_count}개의 감정평가기관이 표시되었습니다.\n")
        
        return m, output_file
        
    except Exception as e:
        print(f"통합 지도 생성 중 오류 발생: {e}")
        traceback.print_exc()
        return None, None

def main():
    """메인 함수 - 통합 지도 생성"""
    
    print("=== 감정평가기관 통합 지도 생성 시스템 ===")
    print("CSV 파일 확인 중...")
    
    # CSV 파일 존재 확인
    csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '주택도시보증공사_전세보증금반환보증 선정 감정평가기관.csv')
    if not os.path.exists(csv_file_path):
        print("CSV 파일을 찾을 수 없습니다!")
        print("현재 디렉토리:", os.getcwd())
        print("찾는 파일 경로:", csv_file_path)
        
        # 프로젝트 루트 디렉토리 확인
        project_root = os.path.dirname(os.path.dirname(__file__))
        print("프로젝트 루트:", project_root)
        
        if os.path.exists(project_root):
            print("프로젝트 루트 파일 목록:", os.listdir(project_root))
            
            data_dir = os.path.join(project_root, 'data')
            if os.path.exists(data_dir):
                print("data 폴더 목록:", os.listdir(data_dir))
            else:
                print("data 폴더가 존재하지 않습니다.")
        else:
            print("프로젝트 루트 디렉토리를 찾을 수 없습니다.")
        return
    
    print("CSV 파일을 찾았습니다.")
    print()
    
    try:
        # 통합 지도 생성
        integrated_map, output_file = create_integrated_map()
        if integrated_map and output_file:
            print("✓ 통합 지도 생성 완료!")
            
            # 브라우저에서 지도 열기
            try:
                webbrowser.open('file://' + os.path.realpath(output_file))
                print("브라우저에서 통합 지도가 열렸습니다.")
            except Exception as e:
                print(f"브라우저 열기 실패: {e}")
                print(f"지도 파일을 수동으로 열어주세요: {output_file}")
        
        print()
        print("=== 통합 지도 생성 완료! ===")
        print(f"생성된 파일: {output_file}")
        
    except Exception as e:
        print(f"지도 생성 중 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()