import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from folium import PolyLine, Circle, Polygon
import streamlit.components.v1 as components
import datetime
import math

# Naver Map API keys (set your own API keys)
NAVER_CLIENT_ID = '5b3r8u2xce'
NAVER_CLIENT_SECRET = '1iz0tE4nqXs9SK3Rtjjj3F2esabQzg78hZfbIJ9V'
# Weather API settings
WEATHER_API_KEY = '+E2kZoggsplAVHSalBbmXsDDqs2L5eIkLgHoW6HN/wtAOAVtxMFMQDaOL/G6hMb3Oq76ApjHSUd88VjRdfk6CQ=='
WEATHER_BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"

# Function to get GPS coordinates from Naver API using an address
def get_gps_from_address(address):
    url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {"query": address}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        result = response.json()
        if result['meta']['totalCount'] > 0:
            lat = result['addresses'][0]['y']
            lon = result['addresses'][0]['x']
            return float(lat), float(lon)
        else:
            return None
    else:
        st.error("Failed to get GPS coordinates from Naver API")
        return None

# Function to get weather information from the Korea Meteorological Administration (KMA) API
def get_weather_info(latitude, longitude):
    now = datetime.datetime.now()
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")  # 정시에 업데이트 되므로 "HH00" 형태로 시간 설정
    nx, ny = 55, 127  # 예시 좌표로 설정 (사용자 정의 또는 계산 필요)
    params = {
        "serviceKey": WEATHER_API_KEY,
        "numOfRows": 10,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }
    response = requests.get(WEATHER_BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("response").get("header").get("resultCode") == "00":
            items = data.get("response").get("body").get("items").get("item")
            return items
        else:
            st.error("데이터 조회에 실패했습니다.")
            return None
    else:
        st.error(f"API 요청에 실패했습니다. 상태 코드: {response.status_code}")
        return None

# Function to calculate distance from target coordinates
def calculate_distance(row, target_coordinates):
    try:
        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
        points = [tuple(map(float, point.split())) for point in points_str]
        mid_point = points[len(points) // 2]
        mid_point_coordinates = (mid_point[1], mid_point[0])
        return geodesic(target_coordinates, mid_point_coordinates).meters
    except:
        return None

# Main Streamlit app
st.title("🔥 화재발생 영향권 케이블 조회 🗺️")

# Custom CSS for rounded edges and section styling
st.markdown(
    """
    <style>
    .section {
        background-color: #f9f9f9;
        padding: 20px;
        margin-bottom: 20px;
        border-radius: 15px;
    }
    .rounded-input {
        border-radius: 15px;
        border: 1px solid #ccc;
        padding: 10px;
        width: 100%;
    }
    .button-style {
        border-radius: 12px;
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        text-align: center;
        font-size: 16px;
        margin: 10px 2px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Container for address input and GPS result
with st.container():
    st.markdown('<div class="section">🏠 <b>주소 입력 및 GPS 조회</b></div>', unsafe_allow_html=True)
    address = st.text_input("", "경남 양산시 용주로 368", key='address_input', help="주소를 입력하고 GPS 좌표를 조회하세요.")
    if st.button("GPS 좌표 조회 🛰️", key='gps_button', help="입력된 주소의 GPS 좌표를 조회합니다."):
        gps_coordinates = get_gps_from_address(address)
        if gps_coordinates:
            st.session_state['gps_coordinates'] = gps_coordinates  # Store in session_state
            st.success(f"📍 GPS 좌표: {gps_coordinates[0]}, {gps_coordinates[1]}")

            # Fetch weather information for the given coordinates
            weather_data = get_weather_info(gps_coordinates[0], gps_coordinates[1])
            if weather_data:
                st.markdown('<div class="section">🌤️ <b>날씨 정보</b></div>', unsafe_allow_html=True)
                category_mapping = {
                    "T1H": "기온 (°C)",
                    "RN1": "1시간 강수량 (mm)",
                    "REH": "습도 (%)",
                    "VEC": "풍향 (°)",
                    "WSD": "풍속 (m/s)"
                }
                selected_categories = ["T1H", "REH", "RN1", "VEC", "WSD"]
                weather_info = {}
                for item in weather_data:
                    category = item.get("category")
                    if category in selected_categories:
                        obsr_value = item.get("obsrValue")
                        category_name = category_mapping.get(category, category)
                        st.write(f"{category_name}: {obsr_value}")
                        weather_info[category] = obsr_value
                
                # Store weather info in session_state
                st.session_state['weather_info'] = weather_info

# Container for distance selection and cable query
with st.container():
    st.markdown('<div class="section">📏 <b>반경 거리 설정 및 케이블 조회</b></div>', unsafe_allow_html=True)
    distance_limit = st.slider('반경을 선택하세요 (단위: km)', 0.0, 10.0, 1.0, key='distance_slider') * 1000  # km를 meter로 변환
    if st.button("케이블 조회 🕵️", key='cable_button', help="GPS 좌표를 바탕으로 주변 케이블을 조회합니다."):
        if 'gps_coordinates' not in st.session_state:
            st.error("먼저 GPS 좌표를 조회하세요.")
        else:
            gps_coordinates = st.session_state['gps_coordinates']
            # Load Excel file
            file_path = 'AI교육_케이블현황_GIS_경남 양산,SKT_샘플2.csv'  # CSV 파일 경로
            data = pd.read_csv(file_path)
            
            # Calculate distances and filter within the selected distance
            data['계산거리'] = data.apply(lambda row: calculate_distance(row, gps_coordinates), axis=1)
            filtered_data = data[data['계산거리'] <= distance_limit]
            
            # 지도 1: 전체 케이블 및 반경 범위 시각화
            map1 = folium.Map(location=gps_coordinates, zoom_start=14)
            
            # 전체 케이블 검정색으로 표시
            for _, row in data.iterrows():
                points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                points = [tuple(map(float, point.split())) for point in points_str]
                line_coordinates = [(point[1], point[0]) for point in points]
                folium.PolyLine(line_coordinates, color="black", weight=2).add_to(map1)
            
            # 화재지점 표시
            folium.Marker(
                location=gps_coordinates,
                popup="화재 발생 지점",
                icon=folium.Icon(icon='fire', color='red')
            ).add_to(map1)
            
            # 반경 범위를 원으로 표시 (반투명)
            folium.Circle(
                location=gps_coordinates,
                radius=distance_limit,
                color='blue',
                fill=True,
                fill_opacity=0.2
            ).add_to(map1)
            
            # 필터링된 케이블 표시
            for _, row in filtered_data.iterrows():
                points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                points = [tuple(map(float, point.split())) for point in points_str]
                line_coordinates = [(point[1], point[0]) for point in points]
                folium.PolyLine(line_coordinates, color='blue', weight=2.5, popup=f"케이블관리번호: {row['케이블관리번호']}").add_to(map1)
            
            st.markdown('<div class="section">🌍 <b>지도 1: 전체 케이블 및 반경 범위</b></div>', unsafe_allow_html=True)
            folium_static(map1)

            # 지도 2: 풍향 및 풍속을 반영한 타원형 영향 범위 시각화
            if 'weather_info' in st.session_state:
                weather_info = st.session_state['weather_info']
                if 'VEC' in weather_info and 'WSD' in weather_info:
                    wind_direction = float(weather_info['VEC'])  # 풍향 (°)
                    wind_speed = float(weather_info['WSD'])  # 풍속 (m/s)
                    time_hours = st.slider('예상 영향 시간을 선택하세요 (단위: 시간)', 1, 24, 1, key='time_slider')
                    
                    # 예상 영향 거리 계산 (m)
                    distance = wind_speed * 3600 * time_hours
                    
                    # 타원형 영향 범위 계산
                    lat_offset = distance * math.cos(math.radians(wind_direction)) / 111000
                    lon_offset = distance * math.sin(math.radians(wind_direction)) / (111000 * math.cos(math.radians(gps_coordinates[0])))
                    
                    # 타원형의 네 개의 주요 좌표 계산 (북, 남, 동, 서 방향)
                    ellipse_coordinates = [
                        (gps_coordinates[0] + lat_offset, gps_coordinates[1]),  # 북쪽
                        (gps_coordinates[0] - lat_offset, gps_coordinates[1]),  # 남쪽
                        (gps_coordinates[0], gps_coordinates[1] + lon_offset),  # 동쪽
                        (gps_coordinates[0], gps_coordinates[1] - lon_offset)   # 서쪽
                    ]
                    
                    # 지도 2 생성
                    map2 = folium.Map(location=gps_coordinates, zoom_start=14)
                    
                    # 전체 케이블 검정색으로 표시
                    for _, row in data.iterrows():
                        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                        points = [tuple(map(float, point.split())) for point in points_str]
                        line_coordinates = [(point[1], point[0]) for point in points]
                        folium.PolyLine(line_coordinates, color="black", weight=2).add_to(map2)
                    
                    # 화재지점 표시
                    folium.Marker(
                        location=gps_coordinates,
                        popup="화재 발생 지점",
                        icon=folium.Icon(icon='fire', color='red')
                    ).add_to(map2)
                    
                    # 타원형 영향 범위 그리기
                    folium.Polygon(
                        locations=ellipse_coordinates,
                        color='red',
                        fill=True,
                        fill_opacity=0.2,
                        popup="예상 화재 영향 범위"
                    ).add_to(map2)
                    
                    # 필터링된 케이블 표시 (타원형 영향 범위 내)
                    filtered_data_ellipse = data[data['계산거리'] <= distance]
                    for _, row in filtered_data_ellipse.iterrows():
                        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                        points = [tuple(map(float, point.split())) for point in points_str]
                        line_coordinates = [(point[1], point[0]) for point in points]
                        folium.PolyLine(line_coordinates, color='red', weight=2.5, popup=f"케이블관리번호: {row['케이블관리번호']}").add_to(map2)
                    
                    st.markdown('<div class="section">🌍 <b>지도 2: 풍향 및 풍속을 반영한 영향 범위</b></div>', unsafe_allow_html=True)
                    folium_static(map2)

            # 필터링된 케이블 목록 표시
            if not filtered_data.empty:
                st.markdown('<div class="section">📋 <b>조회된 케이블 목록</b></div>', unsafe_allow_html=True)
                result = filtered_data[['케이블관리번호', '시군구명', '읍면동명', '리명', '사용코어수', '중계기회선수', '중요선로']]
                st.dataframe(result)

            else:
                st.write(f"{distance_limit / 1000}km 내에 케이블이 없습니다.")
