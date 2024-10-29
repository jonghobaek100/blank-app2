import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from folium import PolyLine
import streamlit.components.v1 as components
from datetime import datetime
import json

# Naver Map API keys (set your own API keys)
NAVER_CLIENT_ID = '5b3r8u2xce'
NAVER_CLIENT_SECRET = '1iz0tE4nqXs9SK3Rtjjj3F2esabQzg78hZfbIJ9V'

# KMA API base URL and service key
KMA_API_BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
KMA_SERVICE_KEY = '+E2kZoggsplAVHSalBbmXsDDqs2L5eIkLgHoW6HN/wtAOAVtxMFMQDaOL/G6hMb3Oq76ApjHSUd88VjRdfk6CQ=='  # Replace with your KMA service key

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
        try:
            result = response.json()
            if result['meta']['totalCount'] > 0:
                lat = result['addresses'][0]['y']
                lon = result['addresses'][0]['x']
                return float(lat), float(lon)
            else:
                return None
        except json.JSONDecodeError:
            st.error("Failed to decode GPS response from Naver API.")
            return None
    else:
        st.error(f"Failed to get GPS coordinates from Naver API: {response.status_code}")
        return None

# Function to get weather data from KMA API using GPS coordinates
def get_weather_from_gps(lat, lon):
    # Convert latitude and longitude to grid x, y using an approximate method
    nx = int((lon - 123.0) * 5)  # Example conversion, adjust as needed
    ny = int((lat - 32.0) * 5)   # Example conversion, adjust as needed

    # Get the current date and adjust base time to the nearest hour for KMA API request
    now = datetime.now()
    if now.minute < 30:
        now = now - timedelta(hours=1)
    base_date = now.strftime('%Y%m%d')
    base_time = now.strftime('%H') + '30'  # KMA API provides data every hour at HH30

    params = {
        'serviceKey': KMA_SERVICE_KEY,
        'numOfRows': 100,
        'pageNo': 1,
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': nx,
        'ny': ny
    }

    response = requests.get(KMA_API_BASE_URL, params=params)
    if response.status_code == 200:
        try:
            result = response.json()
            if 'response' in result and 'body' in result['response']:
                items = result['response']['body']['items']['item']
                # Extract temperature, wind speed, wind direction, and humidity
                weather_data = {
                    'temperature': -999,
                    'wind_speed': -999,
                    'wind_direction': -999,
                    'humidity': -999
                }
                for item in items:
                    if item['category'] == 'T1H':
                        weather_data['temperature'] = item.get('obsrValue', -999)
                    elif item['category'] == 'WSD':
                        weather_data['wind_speed'] = item.get('obsrValue', -999)
                    elif item['category'] == 'VEC':
                        weather_data['wind_direction'] = item.get('obsrValue', -999)
                    elif item['category'] == 'REH':
                        weather_data['humidity'] = item.get('obsrValue', -999)
                return weather_data
            else:
                st.error("Unexpected response format from KMA API.")
                return None
        except json.JSONDecodeError:
            st.error("Failed to decode weather data response from KMA API.")
            st.text(f"Response content: {response.text}")  # Log response for debugging
            return None
    else:
        st.error(f"Failed to get weather information from KMA API: {response.status_code}")
        st.text(f"Response content: {response.text}")  # Log response for debugging
        return None


# Function to calculate distance from target coordinates
def calculate_distance(row, target_coordinates):
    try:
        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
        points = [tuple(map(float, point.split())) for point in points_str]
        mid_point = points[len(points) // 2]
        mid_point_coordinates = (mid_point[1], mid_point[0])
        return geodesic(target_coordinates, mid_point_coordinates).meters
    except Exception as e:
        st.error(f"Error calculating distance: {e}")
        return None

# Main Streamlit app
st.title("🔥화재발생 영향권 케이블조회🗺️")

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

            # Get weather data
            weather_data = get_weather_from_gps(gps_coordinates[0], gps_coordinates[1])
            if weather_data:
                st.session_state['weather_data'] = weather_data  # Store in session_state
                st.markdown(
                    f"""<div class="section">🌤️ <b>날씨 정보</b><br>
                    온도: {weather_data['temperature']}℃<br>
                    풍속: {weather_data['wind_speed']} m/s<br>
                    풍향: {weather_data['wind_direction']}°<br>
                    습도: {weather_data['humidity']}%<br></div>""",
                    unsafe_allow_html=True
                )
        else:
            st.error("GPS 좌표를 가져올 수 없습니다.")

# Container for distance selection and cable query
with st.container():
    st.markdown('<div class="section">📏 <b>거리 설정 및 케이블 조회</b></div>', unsafe_allow_html=True)
    distance_limit = st.slider('거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0, key='distance_slider') * 1000  # km를 meter로 변환
    if st.button("케이블 조회 🕵️", key='cable_button', help="GPS 좌표를 바탕으로 주변 케이블을 조회합니다."):
        if 'gps_coordinates' not in st.session_state:
            st.error("먼저 GPS 좌표를 조회하세요.")
        else:
            gps_coordinates = st.session_state['gps_coordinates']
            
            # Load Excel file
            file_path = 'AI교육_케이블현황_GIS_경남 양산,SKT_샘플.csv'  # CSV 파일 경로
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
                st.markdown('<div class="section">📋 <b>조회된 케이블 목록</b></div>', unsafe_allow_html=True)
                result = filtered_data[['순번', '케이블관리번호', '시군구명', '읍면동명', '리명', '사용코어수', '계산거리']]
                st.dataframe(result)

                # Identify the closest cable and the one with the most cores
                closest_cable = filtered_data.iloc[0]
                most_cores_cable = filtered_data.loc[filtered_data['사용코어수'].idxmax()]

                # Display the map with cable lines
                map_center = gps_coordinates
                m = folium.Map(location=map_center, zoom_start=14)

                # Plot all cables in black initially
                for _, row in data.iterrows():
                    points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                    points = [tuple(map(float, point.split())) for point in points_str]
                    line_coordinates = [(point[1], point[0]) for point in points]
                    folium.PolyLine(line_coordinates, color="black", weight=2).add_to(m)

                # Highlight filtered cables in blue
                for _, row in filtered_data.iterrows():
                    points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                    points = [tuple(map(float, point.split())) for point in points_str]
                    line_coordinates = [(point[1], point[0]) for point in points]
                    folium.PolyLine(line_coordinates, color="blue", weight=2.5, popup=f"케이블관리번호: {row['케이블관리번호']}").add_to(m)

                    # Add markers to indicate both ends of the cable
                    folium.CircleMarker(
                        location=(line_coordinates[0][0], line_coordinates[0][1]),
                        radius=2.5 * 1.1,  # Make the radius 1.1 times the line thickness
                        color='blue',
                        fill=True,
                        fill_color='blue'
                    ).add_to(m)
                    folium.CircleMarker(
                        location=(line_coordinates[-1][0], line_coordinates[-1][1]),
                        radius=2.5 * 1.1,  # Make the radius 1.1 times the line thickness
                        color='blue',
                        fill=True,
                        fill_color='blue'
                    ).add_to(m)

                # Draw a straight line between the target point and the middle point of the closest cable
                closest_mid_point = closest_cable['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                closest_mid_point_coords = [tuple(map(float, point.split())) for point in closest_mid_point]
                mid_point = closest_mid_point_coords[len(closest_mid_point_coords) // 2]
                mid_point_coordinates = (mid_point[1], mid_point[0])

                folium.PolyLine(
                    locations=[gps_coordinates, mid_point_coordinates],
                    color="red",
                    weight=2.5,
                    dash_array='5, 5'
                ).add_to(m)

                # Highlight the closest cable in green
                folium.PolyLine(
                    locations=[(point[1], point[0]) for point in closest_mid_point_coords],
                    color="green",
                    weight=4
                ).add_to(m)

                # Add markers to indicate both ends of the closest cable in green
                folium.CircleMarker(
                    location=(mid_point_coordinates[0], mid_point_coordinates[1]),
                    radius=2.5 * 1.1,  # Make the radius 1.1 times the line thickness
                    color='green',
                    fill=True,
                    fill_color='green'
                ).add_to(m)

                folium.CircleMarker(
                    location=(closest_mid_point_coords[0][1], closest_mid_point_coords[0][0]),
                    radius=2.5 * 1.1,
                    color='green',
                    fill=True,
                    fill_color='green'
                ).add_to(m)

                folium.CircleMarker(
                    location=(closest_mid_point_coords[-1][1], closest_mid_point_coords[-1][0]),
                    radius=2.5 * 1.1,
                    color='green',
                    fill=True,
                    fill_color='green'
                ).add_to(m)

                # Add markers to indicate the distance
                folium.Marker(
                    location=(mid_point_coordinates[0], mid_point_coordinates[1]),
                    popup=f"거리: {closest_cable['계산거리']:.2f} meters",
                    icon=folium.Icon(color='blue', icon='info-sign')
                ).add_to(m)

                # Add a label indicating distance in the middle of the red dashed line
                mid_lat = (gps_coordinates[0] + mid_point_coordinates[0]) / 2
                mid_lon = (gps_coordinates[1] + mid_point_coordinates[1]) / 2
                folium.Marker(
                    location=(mid_lat, mid_lon),
                    icon=folium.DivIcon(html=f"<div style='color: red; font-weight: bold;'>{closest_cable['계산거리']:.1f}m</div>")
                ).add_to(m)

                folium.Marker(
                    location=map_center,
                    popup="출발점",
                    icon=folium.Icon(icon='fire', color='red')  # Change icon to fire icon to indicate incident point
                ).add_to(m)

                folium_static(m)
            else:
                st.write(f"{distance_limit / 1000}km 내에 케이블이 없습니다.")
