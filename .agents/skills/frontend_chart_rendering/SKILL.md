---
name: Frontend Chart Rendering Architecture
description: 데이터 시각화 시 서버 사이드 렌더링(Plotly)과 클라이언트 렌더링(Lightweight Charts)의 선택 및 구현 기준 가이드
---

# 프론트엔드 차트 렌더링 아키텍처 철학 (Frontend Chart Rendering Architecture)

## 1. 핵심 철학 (Core Philosophy)
파이썬 백엔드(Streamlit, FastAPI)에서 시계열 데이터(주식, 코인, 거시경제 지표)를 브라우저에 렌더링할 때, **서버가 직접 그림을 그려서 던져주는 방식(Plotly, Matplotlib)을 절대적으로 지양**하고, **순수 JSON 데이터만 던져준 뒤 클라이언트 브라우저가 직접 그리도록 유도하는 방식(TradingView Lightweight Charts, ECharts 등)**을 최우선으로 도입해야 합니다.

## 2. 렌더링 방식 비교 및 판단 기준

### 안티패턴: Server-side Rendering (Plotly, Streamlit Native)
*   **작동 방식:** 파이썬이 데이터를 수집한 뒤, 무거운 그래픽 객체 덩어리를 만들어 브라우저에 HTML/JS 덩어리로 꽂아 넣음.
*   **치명적 단점:** 마우스 휠, 줌인/줌아웃 등 사소한 인터랙션 시마다 버벅거림(Frame Drop) 발생. 다수의 차트를 띄우면 브라우저 메모리 폭주 및 렌더링 속도 기하급수적 하락.
*   **사용처:** 아주 가벼운 1회성 정적 리포팅 목적 외에는 대시보드에서 절대 사용 금지.

### 권장 패턴: Client-side Engine Rendering (Lightweight Charts)
*   **작동 방식:** 서버는 오직 `[{"time": "2023-01-01", "close": 100}]` 형태의 **용량이 극히 적은 순수 JSON 배열**만 던져줌. 브라우저 내의 고성능 자바스크립트 엔진(Lightweight Charts)이 디바이스의 GPU 자원을 바탕으로 직접 초당 60프레임으로 캔버스(Canvas) 위에 렌더링함.
*   **장점:** 백엔드 부하율 0%. 모바일 HTS/MTS 앱 수준의 압도적인 스크롤 및 줌인/줌아웃 부드러움 제공.
*   **사용처:** 실시간 주식 차트, 시계열 데이터 대시보드 등 모든 동적 화면.

## 3. 구현 표준 (Implementation Standard)

### 파이썬(서버) 데이터 규격 (Strict Data Structuring)
서버에서는 프론트엔드 라이브러리가 즉시 이해할 수 있는 순수한 List of Dict를 생성해야 합니다.
```python
# 캔들스틱 (Candlestick Series) 규격
candlestick_data = [
    {"time": "2023-01-01", "open": 100, "high": 120, "low": 90, "close": 110},
    {"time": "2023-01-02", "open": 110, "high": 130, "low": 105, "close": 125}
]

# 라인/영역 차트 (Area/Line Series) 규격
line_data = [
    {"time": "2023-01-01", "value": 110},
    {"time": "2023-01-02", "value": 125}
]
```

### Streamlit HTML/JS 주입 (Injection)
Streamlit에서는 `components.html` 기능을 이용해 위 데이터를 자바스크립트 생태계로 주입시키는 브릿지 코드를 작성합니다. `components/tv_widgets.py` 내의 `render_lightweight_chart(data, title, height)` 정적 팩토리 메서드를 표준 도구로 활용하십시오.

### 데이터 맵핑 및 교체 예시 (리팩토링)
과거의 낡은 코드를 발견하면 아래와 같이 혁신적으로 교체합니다:
```python
# ❌ [Legacy] 무겁고 낡은 Plotly 방식 버리기
# fig = go.Figure(go.Candlestick(x=times, open=opens, high=highs...))
# st.plotly_chart(fig)

# ✅ [Modern] 가벼운 JSON 주입 및 클라이언트 렌더링 (Lightweight)
# API에서 수집된 dict list를 그대로 전달 (format: [{time, open, high, low, close}])
TradingViewWidget.render_lightweight_chart(data=data_list, title="KOSPI", height=300)
```
