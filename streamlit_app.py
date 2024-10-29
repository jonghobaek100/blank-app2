import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from folium import PolyLine
import streamlit.components.v1 as components
import datetime

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
        try:
            data = response.json()
            if data.get("response").get("header").get("resultCode") == "00":
                items = data.get("response").get("body").get("items").get("item")
                return items
            else:
                st.error("데이터 조회에 실패했습니다.")
                return None
        except ValueError:
            st.error("응답에서 JSON을 파싱하는 데 실패했습니다. 응답 내용이 올바르지 않을 수 있습니다.")
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

st.text_area("", """    ○ 화재 발생 지점 인근의 케이블을 조회하는 프로그램v1.0입니다.
    ○ 양산지역만 샘플로 구현된 버전입니다.
    ○ 지도표시 케이블(파란색: 영향 범위 내, 검은색 : 영향 범위 외, 빨간색: 중요케이블)                 
""")

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
    .result-section {
        background-color: #f0f0f0;
        padding: 20px;
        border-radius: 15px;
        margin-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# UI for Address and Distance Input
def address_and_distance_input():
    with st.container():
        address = st.text_input("🏠화재발생 주소를 입력하세요 :", "경남 양산시 중뫼길 36", key='address_input', help="주소를 입력하고 GPS 좌표를 조회하세요.")
        distance_limit_str = st.text_input('📏화재영향 거리를 입력하세요 :', '1000', key='distance_input')

        if st.button("화재발생지점 조회 🛰️", key='gps_button', help="입력된 주소의 GPS 좌표를 조회합니다."):
            gps_coordinates = get_gps_from_address(address)
            if gps_coordinates:
                st.session_state['gps_coordinates'] = gps_coordinates  # Store in session_state
                st.success(f"📍 GPS 좌표: {gps_coordinates[0]}, {gps_coordinates[1]}")
                # Fetch weather information for the given coordinates
                display_weather_info(gps_coordinates)
                # Automatically query and display cable information after getting GPS coordinates
                try:
                    distance_limit = float(distance_limit_str)  # 입력값 그대로 m 단위 사용
                except ValueError:
                    st.error("유효한 숫자를 입력하세요.")
                    distance_limit = None

                if distance_limit is not None:
                    query_and_display_cables(gps_coordinates, distance_limit)
            else:
                st.error("GPS 좌표를 가져올 수 없습니다.")

# Function to Display Weather Information
def display_weather_info(gps_coordinates):
    weather_data = get_weather_info(gps_coordinates[0], gps_coordinates[1])
    if weather_data:
        st.markdown('<div class="result-section">🌤️ <b>날씨 정보</b></div>', unsafe_allow_html=True)
        category_mapping = {
            "T1H": "기온 (°C)",
            "RN1": "1시간 강수량 (mm)",
            "REH": "습도 (%)",
            "VEC": "풍향 (°)",
            "WSD": "풍속 (m/s)"
        }
        selected_categories = ["T1H", "REH", "RN1", "VEC", "WSD"]
        for item in weather_data:
            category = item.get("category")
            if category in selected_categories:
                obsr_value = item.get("obsrValue")
                category_name = category_mapping.get(category, category)
                st.write(f"{category_name}: {obsr_value}")

# Function to Query and Display Cable Information
def query_and_display_cables(gps_coordinates, distance_limit):
    # Load Excel file
    file_path = 'AI교육_케이블현황_GIS_경남 양산,SKT_샘플2.csv'  # CSV 파일 경로
    data = pd.read_csv(file_path)
    # Calculate distances and filter within the selected distance
    data['계산거리'] = data.apply(lambda row: calculate_distance(row, gps_coordinates), axis=1)
    filtered_data = data[data['계산거리'] <= distance_limit]
    if not filtered_data.empty:
        # Sort the data by 계산거리 in ascending order
        filtered_data = filtered_data.sort_values(by='계산거리')
        # Add 순번 column
        filtered_data.insert(0, '순번', range(1, len(filtered_data) + 1))
        # Display the filtered and sorted data
        st.markdown('<div class="result-section">📋 <b>조회된 케이블 목록</b></div>', unsafe_allow_html=True)
        result = filtered_data[['순번', '계산거리', '케이블관리번호', '시군구명', '읍면동명', '리명', '사용코어수', '중계기회선수', '중요선로' ]]
        st.dataframe(result)

        # Display the map with cable lines
        display_cable_map(gps_coordinates, filtered_data, data)
    else:
        st.write(f"{distance_limit}m 내에 케이블이 없습니다.")

# Function to Display Cable Map
def display_cable_map(gps_coordinates, filtered_data, data):
    map_center = gps_coordinates
    m = folium.Map(location=map_center, zoom_start=14)

    # Add fire marker for the GPS coordinates
    folium.Marker(
        location=gps_coordinates,
        popup="화재 발생 지점",
        icon=folium.Icon(icon='fire', color='red')
    ).add_to(m)

    # Plot all cables in black initially
    for _, row in data.iterrows():
        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
        points = [tuple(map(float, point.split())) for point in points_str]
        line_coordinates = [(point[1], point[0]) for point in points]
        folium.PolyLine(line_coordinates, color="black", weight=2).add_to(m)

    # Highlight filtered cables
    closest_cable = None
    min_distance = float('inf')
    for _, row in filtered_data.iterrows():
        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
        points = [tuple(map(float, point.split())) for point in points_str]
        line_coordinates = [(point[1], point[0]) for point in points]
        color = 'red' if row['중요선로'] == 'O' else 'blue'
        folium.PolyLine(line_coordinates, color=color, weight=2.5, popup=f"케이블관리번호: {row['케이블관리번호']}").add_to(m)

        # Add markers to indicate both ends of the cable
        folium.CircleMarker(
            location=(line_coordinates[0][0], line_coordinates[0][1]),
            radius=2.5 * 0.55,  # Make the radius 1.1 times the line thickness
            color=color,
            fill=True,
            fill_color=color
        ).add_to(m)
        folium.CircleMarker(
            location=(line_coordinates[-1][0], line_coordinates[-1][1]),
            radius=2.5 * 0.55,  # Make the radius 1.1 times the line thickness
            color=color,
            fill=True,
            fill_color=color
        ).add_to(m)

        # Find the closest cable
        if row['계산거리'] < min_distance:
            min_distance = row['계산거리']
            closest_cable = line_coordinates

    # Draw a line from the fire location to the closest cable
    if closest_cable:
        closest_point = closest_cable[len(closest_cable) // 2]  # Use the midpoint of the closest cable
        folium.PolyLine([gps_coordinates, closest_point], color='red', weight=2, dash_array='5, 10').add_to(m)
        folium.Marker(
            location=((gps_coordinates[0] + closest_point[0]) / 2, (gps_coordinates[1] + closest_point[1]) / 2),
            icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: red; white-space: nowrap;">거리: {min_distance:.2f}m</div>')
        ).add_to(m)

    folium_static(m)

# Run the address and distance input function
address_and_distance_input()
