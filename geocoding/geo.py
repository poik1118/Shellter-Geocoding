# CSV 파일에서 주소를 읽어서 경도, 위도로 변환하는 코드 (VWorld API 사용)
import requests
import os
import pandas as pd
import time
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# .env 파일 로드
load_dotenv()

# .env 파일에서 VWorld API 인증키 가져오기
VWORLD_API_KEY = os.getenv('VWORLD_API_KEY')

def get_coordinates(address):
    """주소를 받아서 경도, 위도를 반환하는 함수"""
    if not VWORLD_API_KEY:
        print("❌ 오류: .env 파일에서 VWORLD_API_KEY를 찾을 수 없습니다.")
        return None, None
    
    # 1단계: VWorld API로 원본 주소 시도
    print(f"🔄 VWorld API로 시도 중...")
    result = try_address_vworld(address)
    if result[0] is not None:
        return result
    
    # 2단계: VWorld API로 콤마 분리 후 재시도
    if ',' in address:
        parts = address.split(',')
        if len(parts) > 1:
            front_address = parts[0].strip()
            print(f"❗ 콤마 분리 주소: '{front_address}'")
            print(f"🔄 콤마 분리 후 VWorld API 재처리중...")
            result = try_address_vworld(front_address)
            if result[0] is not None:
                return result
    
    # 3단계: geopy로 시도
    print(f"⚠️ geopy로 시도 중...")
    result = get_coordinates_geopy(address)
    if result[0] is not None:
        return result
    
    # 4단계: geopy로 콤마 분리 후 재시도
    if ',' in address:
        parts = address.split(',')
        if len(parts) > 1:
            front_address = parts[0].strip()
            print(f"❗ 콤마 분리 주소: '{front_address}'")
            print(f"🔄 콤마 분리 후 geopy 재처리중...")
            return get_coordinates_geopy(front_address)
    
    return None, None

def get_coordinates_geopy(address):
    """geopy를 사용하여 주소를 경도, 위도로 변환하는 함수"""
    try:
        # Nominatim geocoder 초기화 (OpenStreetMap 기반)
        geolocator = Nominatim(user_agent="my_geocoder")
        
        # 주소 정제 (한국 주소에 맞게)
        cleaned_address = clean_address_for_geopy(address)
        
        # 위치 검색
        location = geolocator.geocode(cleaned_address, timeout=10)
        
        if location:
            print(f"✅ geopy 성공: {cleaned_address} → ({location.longitude}, {location.latitude})")
            return location.longitude, location.latitude
        else:
            print(f"❌ geopy 주소 변환 실패: {cleaned_address}")
            return None, None
            
    except GeocoderTimedOut:
        print(f"❌ geopy 타임아웃: {address}")
        return None, None
    except GeocoderUnavailable:
        print(f"❌ geopy 서비스 불가: {address}")
        return None, None
    except Exception as e:
        print(f"❌ geopy 오류: {address} - {str(e)}")
        return None, None

def clean_address_for_geopy(address):
    """geopy용 주소 정제 함수"""
    if not address:
        return address
    
    # 한국 주소에 맞게 정제
    import re
    
    # 특수문자 제거
    address = re.sub(r'\([^)]*\)', '', address)  # 괄호 안 내용 제거
    address = re.sub(r'[0-9]+층', '', address)   # 층수 제거
    address = re.sub(r'[0-9]+호', '', address)   # 호수 제거
    address = address.replace('㈜', '').replace('㈐', '')
    
    # 한국 주소 형식으로 변환
    address = address.strip()
    
    # "Korea" 추가 (geopy가 한국 주소를 더 잘 인식하도록)
    if address and not address.endswith('Korea'):
        address = f"{address}, Korea"
    
    return address

def try_address_vworld(address):
    """VWorld API 호출을 시도하는 함수"""
    apiurl = "https://api.vworld.kr/req/address?"
    params = {
        "service": "address",
        "request": "getcoord",
        "crs": "epsg:4326",
        "address": address,
        "format": "json",
        "type": "road",
        "key": VWORLD_API_KEY
    }
    
    try:
        response = requests.get(apiurl, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['response']['status'] == 'OK':
                point = data['response']['result']['point']
                longitude = point['x']
                latitude = point['y']
                print(f"✅ VWorld API 성공: {address} → ({longitude}, {latitude})")
                return longitude, latitude
            else:
                print(f"❌ VWorld API 주소 변환 실패: {address} - {data['response']['status']}")
                return None, None
        else:
            print(f"❌ VWorld API 요청 실패: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"❌ VWorld API 오류 발생: {address} - {str(e)}")
        return None, None

def process_csv(input_file, output_file, address_column):
    """CSV 파일을 읽어서 주소를 경도, 위도로 변환하고 새로운 CSV로 저장"""
    
    # CSV 파일 읽기
    try:
        df = pd.read_csv(input_file, encoding='utf-8')
        print(f"✅ CSV 파일 읽기 성공: {len(df)}개 행")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(input_file, encoding='cp949')
            print(f"✅ CSV 파일 읽기 성공 (cp949): {len(df)}개 행")
        except Exception as e:
            print(f"❌ CSV 파일 읽기 실패: {str(e)}")
            return
    
    # 주소 컬럼이 존재하는지 확인
    if address_column not in df.columns:
        print(f"❌ 오류: '{address_column}' 컬럼을 찾을 수 없습니다.")
        print(f"사용 가능한 컬럼: {list(df.columns)}")
        return
    
    # 주소 컬럼의 위치 찾기
    address_index = df.columns.get_loc(address_column)
    
    # 경도, 위도 컬럼을 주소 다음에 삽입
    df.insert(address_index + 1, '경도', None)
    df.insert(address_index + 2, '위도', None)
    
    print(f"📋 컬럼 순서: {list(df.columns)}")
    
    print(f"🔄 총 {len(df)}개 주소를 처리합니다...")
    
    # 각 주소에 대해 좌표 변환
    for index, row in df.iterrows():
        address = str(row[address_column]).strip()
        if pd.isna(address) or address == '' or address == 'nan':
            print(f"⚠️  빈 주소 건너뛰기: 행 {index + 1}")
            continue
            
        print(f"🔄 처리 중 ({index + 1}/{len(df)}): {address}")
        
        longitude, latitude = get_coordinates(address)
        df.at[index, '경도'] = longitude
        df.at[index, '위도'] = latitude
        
        # API 호출 제한을 위한 대기 (2.0초)
        time.sleep(2.0)
    
    # 결과를 새로운 CSV 파일로 저장
    try:
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 결과 저장 완료: {output_file}")
        
        # 성공/실패 통계
        success_count = df['경도'].notna().sum()
        total_count = len(df)
        print(f"📊 처리 결과: {success_count}/{total_count}개 성공")
        
    except Exception as e:
        print(f"❌ 파일 저장 실패: {str(e)}")

def main():
    """메인 함수"""
    if not VWORLD_API_KEY:
        print("❌ 오류: .env 파일에서 VWORLD_API_KEY를 찾을 수 없습니다.")
        print("다음과 같이 .env 파일을 생성해주세요:")
        print("VWORLD_API_KEY=your_vworld_api_key_here")
        return
    
    # 파일 경로 설정 (사용자가 수정해야 함)
    input_file = "./data/주택도시보증공사_전세보증금반환보증 선정 감정평가기관.csv"  # 입력 CSV 파일명
    output_file = "./data/주택도시보증공사_전세보증금반환보증_선정_정평가기관_GEO.csv"  # 출력 CSV 파일명
    address_column = "주소"  # 주소가 있는 컬럼명
    
    print("🏠 주택도시보증공사 CSV 주소 좌표 변환 프로그램 (VWorld API)")
    print("=" * 50)
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print(f"주소 컬럼: {address_column}")
    print("=" * 50)
    
    # 파일 존재 확인
    if not os.path.exists(input_file):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
        print("CSV 파일을 프로젝트 폴더에 넣어주세요.")
        return
    
    # CSV 처리 시작
    process_csv(input_file, output_file, address_column)

if __name__ == "__main__":
    main()