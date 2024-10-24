import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from folium import PolyLine
import math

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
        return geodesic(target_coordinates, mid_point_coordinates).meters
    except:
        return None

# Function to calculate the bearing between two GPS points
def calculate_bearing(start_point, end_point):
    lat1, lon1 = math.radians(start_point[0]), math.radians(start_point[1])
    lat2, lon2 = math.radians(end_point[0]), math.radians(end_point[1])
    delta_lon = lon2 - lon1

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return bearing

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

# 슬라이더를 사용해 각 방향별 거리를 입력받기 (0 ~ 10km)
distance_limit_north = st.slider('북쪽 거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0) * 1000  # km를 meter로 변환
distance_limit_east = st.slider('동쪽 거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0) * 1000
distance_limit_south = st.slider('남쪽 거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0) * 1000
distance_limit_west = st.slider('서쪽 거리를 선택하세요 (단위: km)', 0.0, 10.0, 1.0) * 1000

# 케이블 조회
if st.button("케이블 조회"):
    if 'gps_coordinates' not in st.session_state:
        st.error("먼저 GPS 좌표를 조회하세요.")
    else:
        gps_coordinates = st.session_state['gps_coordinates']
        
        # Load Excel file
        file_path = 'AI교육_케이블현황_GIS_경남 양산,SKT_샘플.csv'  # CSV 파일 경로
        data = pd.read_csv(file_path)

        # Calculate distances and filter based on direction
        def filter_by_direction(row):
            distance = calculate_distance(row, gps_coordinates)
            if distance is None:
                return None
            points_str = row['공간위치G'].replace("LINESTRING (", "").replace(")", "").split(", ")
            points = [tuple(map(float, point.split())) for point in points_str]
            mid_point = points[len(points) // 2]
            mid_point_coordinates = (mid_point[1], mid_point[0])
            bearing = calculate_bearing(gps_coordinates, mid_point_coordinates)

            # Determine which quadrant the cable belongs to and apply the distance limit accordingly
            if 0 <= bearing < 90:  # North-East
                return distance if distance <= distance_limit_north else None
            elif 90 <= bearing < 180:  # South-East
                return distance if distance <= distance_limit_east else None
            elif 180 <= bearing < 270:  # South-West
                return distance if distance <= distance_limit_south else None
            else:  # North-West
                return distance if distance <= distance_limit_west else None

        data['계산거리'] = data.apply(filter_by_direction, axis=1)
        filtered_data = data[data['계산거리'].notna()]

        if not filtered_data.empty:
            # Sort the data by 계산거리 in ascending order
            filtered_data = filtered_data.sort_values(by='계산거리')

            # Add 순번 column
            filtered_data.insert(0, '순번', range(1, len(filtered_data) + 1))

            # Display the filtered and sorted data
            result = filtered_data[['순번', '케이블관리번호', '시군구명', '읍면동명', '리명', '사용코어수', '계산거리']]
            st.dataframe(result)

            # Identify the closest cable and the one with the most cores
            closest_cable = filtered_data.iloc[0]
            most_cores_cable = filtered_data.loc[filtered_data['사용코어수'].idxmax()]

            # Display the map with cable lines
            map_center = gps_coordinates
            m = folium.Map(location=map_center, zoom_start=14)
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
