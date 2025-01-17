import streamlit as st
import pandas as pd
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
from folium import Polygon, CircleMarker
import datetime
import pytz
from openai import OpenAI  # OpenAI API 추가

# Streamlit Secrets 설정
NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", None)
NAVER_CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET", None)
WEATHER_API_KEY = st.secrets.get("WEATHER_API_KEY", None)
WEATHER_BASE_URL = st.secrets.get("WEATHER_BASE_URL", None)
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)

# 환경 변수 확인
if not all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, WEATHER_API_KEY, WEATHER_BASE_URL, OPENAI_API_KEY]):
    st.error("필수 API 키 또는 URL이 누락되었습니다. Streamlit Cloud Secrets를 확인하세요.")

# OpenAI client 설정
client = OpenAI(api_key=OPENAI_API_KEY)

# 전역변수 선언
seoul_tz = pytz.timezone('Asia/Seoul')
now = datetime.datetime.now(seoul_tz) - datetime.timedelta(hours=1)  # 현재시간 대비 1시간 전 날씨
base_date = now.strftime("%Y%m%d")
base_time = now.strftime("%H00")  # 정시에 업데이트 되므로 "HH00" 형태로 시간 설정

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
    if not WEATHER_BASE_URL:
        st.error("기상청 API URL이 설정되지 않았습니다.")
        return None

    now = datetime.datetime.now(seoul_tz) - datetime.timedelta(hours=1)
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")
    nx, ny = 55, 127
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
            st.write("**응답 디버깅**: ", response.text)  # 응답 내용 출력
            return None
    else:
        st.error(f"API 요청에 실패했습니다. 상태 코드: {response.status_code}")
        return None

# Function to predict fire spread using OpenAI API
def predict_fire_spread(gps_coordinates, wind_speed, wind_direction, distance_limit):
    try:
        prompt = (
            f"현재 GPS 좌표: {gps_coordinates}, 풍속: {wind_speed}m/s, 풍향: {wind_direction}°, "
            f"영향 반경: {distance_limit}m. "
            "1시간, 2시간, 3시간 후의 화재 확산 예상 범위를 타원형으로 추정해 주세요. "
            "타원의 중심 좌표와 각 축의 길이를 제시하고, 각 시간별 확산 방향을 고려하여 범위를 표시해 주세요."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 화재 확산 예측 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        st.write("**OpenAI 응답 디버깅**", response)  # 응답 내용 출력
        fire_spread_prediction = response.choices[0].message.content
        return fire_spread_prediction
    except Exception as e:
        st.error(f"OpenAI API 요청에 실패했습니다: {e}")
        return None

# Function to display fire spread on map
def display_fire_spread_map(gps_coordinates, predictions):
    m = folium.Map(location=gps_coordinates, zoom_start=13)

    # 현재 발생 지점 표시
    folium.Marker(
        location=gps_coordinates,
        popup="현재 화재 발생 지점",
        icon=folium.Icon(icon="fire", color="red")
    ).add_to(m)

    # 예측된 확산 범위 표시
    for prediction in predictions:
        center = prediction['center']
        axes = prediction['axes']
        direction = prediction['direction']
        time = prediction['time']

        folium.Marker(
            location=center,
            popup=f"{time} 후 중심: {center}",
            icon=folium.Icon(icon="info-sign", color="blue")
        ).add_to(m)

        folium.Polygon(
            locations=[
                [center[0] + axes[0] * 0.00001, center[1] + axes[1] * 0.00001],
                [center[0] - axes[0] * 0.00001, center[1] - axes[1] * 0.00001],
                [center[0] + axes[0] * 0.00001, center[1] - axes[1] * 0.00001],
                [center[0] - axes[0] * 0.00001, center[1] + axes[1] * 0.00001],
            ],
            color="blue" if time == "1시간" else ("orange" if time == "2시간" else "green"),
            fill=True,
            fill_opacity=0.4,
            popup=f"{time} 후 확산 범위"
        ).add_to(m)

    folium_static(m)

# Main Streamlit app
st.title("🔥 화재 영향권 케이블 조회 🗺️")

st.text_area("", """    ○ 화재 발생 지점 인근의 케이블을 조회하는 프로그램v3.2입니다.
    ○ 양산지역만 샘플로 구현된 버전입니다.
    ○ 지도표시 케이블(파란색: 영향 범위 내, 검은색 : 영향 범위 외, 빨간색: 중요케이블)                 
""")

# UI for Address and Distance Input
def address_and_distance_input():
    with st.container():
        address = st.text_input("🏠화재발생 주소를 입력하세요 :", "경남 양산시 중뼄길 36", key='address_input', help="주소를 입력하고 GPS 좌표를 조회하세요.")
        distance_limit_str = st.text_input('📏화재영향 거리를 입력하세요 :', '1000', key='distance_input')

        if st.button("화재발생지점 조회 🚁️", key='gps_button', help="입력된 주소의 GPS 좌표를 조회합니다."):
            gps_coordinates = get_gps_from_address(address)
            if gps_coordinates:
                st.session_state['gps_coordinates'] = gps_coordinates  # Store in session_state
                st.success(f"📍 GPS 좌표 (네이버맵): {gps_coordinates[0]}, {gps_coordinates[1]}")
                # Fetch weather information for the given coordinates
                weather_data = get_weather_info(gps_coordinates[0], gps_coordinates[1])
                if weather_data:
                    wind_speed = next((item['obsrValue'] for item in weather_data if item['category'] == 'WSD'), None)
                    wind_direction = next((item['obsrValue'] for item in weather_data if item['category'] == 'VEC'), None)
                    if wind_speed and wind_direction:
                        try:
                            distance_limit = float(distance_limit_str)
                        except ValueError:
                            st.error("유효한 숫자를 입력하세요.")
                            return

                        fire_spread_prediction = predict_fire_spread(gps_coordinates, wind_speed, wind_direction, distance_limit)
                        if fire_spread_prediction:
                            st.markdown("**화재 확산 예측 결과**")
                            st.text(fire_spread_prediction)
                            # 지도에 표시
                            display_fire_spread_map(gps_coordinates, fire_spread_prediction)
                    else:
                        st.error("풍속 또는 풍향 데이터를 가져올 수 없습니다.")
            else:
                st.error("GPS 좌표를 가져올 수 없습니다.")

# Run the address and distance input function
address_and_distance_input()
