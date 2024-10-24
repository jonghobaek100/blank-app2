import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static

# Naver Map API keys (set your own API keys)
NAVER_CLIENT_ID = '5b3r8u2xce'
NAVER_CLIENT_SECRET = '1iz0tE4nqXs9SK3Rtjjj3F2esabQzg78hZfbIJ9V'

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

# Function to calculate distance from target coordinates
def calculate_distance(row, target_coordinates):
    try:
        points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
        points = [tuple(map(float, point.split())) for point in points_str]
        mid_point = points[len(points) // 2]
        mid_point_coordinates = (mid_point[1], mid_point[0])
        if abs(mid_point_coordinates[0] - target_coordinates[0]) > 0.01 or abs(mid_point_coordinates[1] - target_coordinates[1]) > 0.01:
            return None
        return geodesic(target_coordinates, mid_point_coordinates).meters
    except:
        return None

# Main Streamlit app
st.title("케이블 조회 및 지도 표시")

# Address input form
address = st.text_input("주소를 입력하세요", "경남 양산시 용주로 368")

if st.button("GPS 좌표 조회"):
    gps_coordinates = get_gps_from_address(address)
    if gps_coordinates:
        st.session_state['gps_coordinates'] = gps_coordinates  # Store in session_state
        st.write(f"GPS 좌표: {gps_coordinates[0]}, {gps_coordinates[1]}")
    else:
        st.error("GPS 좌표를 가져올 수 없습니다.")

# 슬라이더를 사용해 거리를 입력받기 (0 ~ 10km)
distance_limit = st.slider('거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0) * 1000  # km를 meter로 변환

# 케이블 조회
if st.button("케이블 조회"):
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
            result = filtered_data[['순번', '케이블관리번호', '시군구명', '읍면동명', '리명', '사용코어수', '계산거리']]
            st.dataframe(result)

            # Display the map with cable lines
            map_center = gps_coordinates
            m = folium.Map(location=map_center, zoom_start=14)
            for _, row in filtered_data.iterrows():
                points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
                points = [tuple(map(float, point.split())) for point in points_str]
                line_coordinates = [(point[1], point[0]) for point in points]
                folium.PolyLine(line_coordinates, color="blue", weight=2.5).add_to(m)
            folium.Marker(location=map_center, popup="Target Point", icon=folium.Icon(color='red')).add_to(m)

            folium_static(m)
        else:
            st.write(f"{distance_limit / 1000}km 내에 케이블이 없습니다.")
