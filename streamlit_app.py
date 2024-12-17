# Streamlit 메인 페이지 코드 (이미지 추가)
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="동부유선Infra팀 AI Tool 모음",
    page_icon="🌐",
    layout="wide"
)

# 대문 제목과 이미지
st.image(
    "./대문.webp",
    use_column_width=True,
    caption="동부유선Infra팀 AI Tool 모음"
)
st.title("🌐 동부유선Infra팀 AI Tool 모음")
st.markdown("""
### 환영합니다! 👋
여기는 **동부유선Infra팀**에서 사용하는 AI 도구들을 한 곳에 모아놓은 페이지입니다.  
효율적인 광선로 관리와 업무 향상을 위한 다양한 AI 도구를 확인하고 활용해 보세요!
""")

# 섹션 구분선
st.markdown("---")

# AI 도구 카테고리
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📊 데이터 분석")
    st.markdown("""
    - [트래픽 분석 도구](#)
    - [장애 예측 모델](#)
    - [성능 최적화 시뮬레이터](#)
    """)

with col2:
    st.subheader("🛠️ 유지보수 지원")
    st.markdown("""
    - [자동화 점검 도구](#)
    - [장애 복구 가이드](#)
    - [장비 상태 모니터링](#)
    """)

with col3:
    st.subheader("📈 의사결정 지원")
    st.markdown("""
    - [시각화 대시보드](#)
    - [최적 경로 분석](#)
    - [비용 효율성 평가](#)
    """)

# 푸터
st.markdown("---")
st.markdown("""
**문의 사항:**  
동부유선Infra팀 | 📧 jonghobaek@sk.com | 📞 123-456-7890
""")

# 참고: 이미지 파일 경로를 수정하거나 URL을 대체하여 로컬 혹은 인터넷에서 이미지를 불러올 수 있습니다.
