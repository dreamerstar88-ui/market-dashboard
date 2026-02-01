"""
Market Eye - Global Investment Dashboard v14.0
- Yahoo Finance API for US/KR indices
- Real-time news with priority sorting and links
"""
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv(override=True)

from components.tv_widgets import TradingViewWidget
from services.crypto_service import get_kimchi_premium
from services.data_service import log_market_snapshot, load_journal, append_journal_entry
from services.ai_service import generate_market_insight
from services.fred_service import get_treasury_yields
from services.favorites_service import load_favorites, add_favorite, remove_favorite
from services.kr_favorites_service import load_kr_favorites, add_kr_favorite, remove_kr_favorite
from services.kr_stock_service import fetch_kr_stock, get_kr_stock_name
from services.news_service import get_translated_economic_events, get_translated_market_news
from services.commodity_service import get_all_commodities
from services.fear_greed_service import get_fear_greed_index
from services.index_service import get_us_indices, get_kr_indices
from config.settings import APP_TITLE, APP_ICON

# ============================================================
# Page Config
# ============================================================
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        .block-container {padding: 0.5rem;}
        header, footer {visibility: hidden;}
        button[data-baseweb="tab"] {font-size: 0.8rem !important; padding: 0.4rem !important;}
        .stMetric {background: rgba(30,30,30,0.5); border-radius: 8px; padding: 0.5rem;}
        .index-card {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }
        .index-name {font-size: 12px; color: #888;}
        .index-price {font-size: 20px; font-weight: bold; color: #fff;}
        .index-change-up {font-size: 14px; color: #00ff88;}
        .index-change-down {font-size: 14px; color: #ff4444;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# Top Bar: F&G + Ticker Tape
# ============================================================
fg_data = get_fear_greed_index()

col_fg, col_tape = st.columns([2, 8])

with col_fg:
    cnn = fg_data["cnn"]
    crypto = fg_data["crypto"]
    
    if not cnn.error and not crypto.error:
        cnn_color = "#FF4444" if cnn.value <= 25 else "#FF8800" if cnn.value <= 45 else "#FFFF00" if cnn.value <= 55 else "#88FF00" if cnn.value <= 75 else "#00FF00"
        crypto_color = "#FF4444" if crypto.value <= 25 else "#FF8800" if crypto.value <= 45 else "#FFFF00" if crypto.value <= 55 else "#88FF00" if crypto.value <= 75 else "#00FF00"
        
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:8px; padding:5px 0;">
            <span style="background:{cnn_color}; color:#000; padding:3px 10px; border-radius:15px; font-size:12px; font-weight:bold;">📈 CNN {cnn.value}</span>
            <span style="background:{crypto_color}; color:#000; padding:3px 10px; border-radius:15px; font-size:12px; font-weight:bold;">₿ Crypto {crypto.value}</span>
        </div>
        """, unsafe_allow_html=True)

with col_tape:
    TradingViewWidget.render_ticker_tape(locale="kr")

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.header("🤖 AI 어드바이저")
    if st.button("📡 AI 분석", use_container_width=True):
        with st.spinner("분석 중..."):
            kp = get_kimchi_premium()
            insight = generate_market_insight(kp.premium_percent if not kp.error else 0, kp.usd_krw_rate if not kp.error else 1400, load_journal())
            st.success(insight)
    st.divider()
    st.header("📝 투자 일지")
    new_entry = st.text_area("메모", height=80)
    if st.button("💾 저장", use_container_width=True) and new_entry.strip():
        append_journal_entry(new_entry.strip())
        st.success("저장됨!")
        st.rerun()

# ============================================================
# Main Tabs
# ============================================================
tabs = st.tabs(["🇺🇸 미국주식", "🇰🇷 한국주식", "💱 환율/원자재", "🌍 거시경제", "₿ 크립토", "📰 시장정보"])

# --- Tab 1: US Stocks ---
with tabs[0]:
    # Major US Indices (Yahoo Finance API)
    st.subheader("📊 미국 주요 지수")
    
    with st.spinner("지수 로딩..."):
        us_indices = get_us_indices()
    
    cols = st.columns(3)
    icons = ["📈", "📊", "📉"]
    for i, idx in enumerate(us_indices):
        with cols[i]:
            if not idx.error:
                change_color = "#00ff88" if idx.change_percent >= 0 else "#ff4444"
                change_sign = "+" if idx.change_percent >= 0 else ""
                st.markdown(f"""
                <div class="index-card">
                    <div class="index-name">{icons[i]} {idx.name}</div>
                    <div class="index-price">{idx.current_price:,.2f}</div>
                    <div style="color:{change_color};">{change_sign}{idx.change_percent:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"{idx.name}: {idx.error}")
    
    st.divider()
    
    favorites = load_favorites()
    
    st.caption("⭐ 즐겨찾기")
    cols = st.columns(min(len(favorites), 6))
    selected = None
    for i, t in enumerate(favorites):
        name = t.split(":")[-1] if ":" in t else t
        if cols[i % len(cols)].button(name, key=f"us_fav_{t}", use_container_width=True):
            selected = t
    
    with st.expander("⚙️ 즐겨찾기 관리"):
        c1, c2 = st.columns(2)
        with c1:
            new_t = st.text_input("➕ 추가", placeholder="GOOGL", key="us_add")
            if st.button("추가", key="us_add_btn") and new_t:
                add_favorite(new_t)
                st.rerun()
        with c2:
            del_t = st.selectbox("➖ 삭제", favorites, key="us_del")
            if st.button("삭제", key="us_del_btn") and del_t:
                remove_favorite(del_t)
                st.rerun()
    
    st.divider()
    symbol = st.text_input("🔍 티커 검색", value=selected or "NASDAQ:NVDA", placeholder="NASDAQ:AAPL", key="us_search").upper()
    
    TradingViewWidget.render_advanced_chart(symbol, height=400, locale="kr")
    st.caption(f"📊 {symbol} 기술적 분석")
    TradingViewWidget.render_technical_analysis(symbol, height=350, locale="kr")

# --- Tab 2: Korean Stocks ---
with tabs[1]:
    # KOSPI & KOSDAQ Indices (Yahoo Finance API)
    st.subheader("📊 한국 주요 지수")
    
    with st.spinner("지수 로딩..."):
        kr_indices = get_kr_indices()
    
    cols = st.columns(2)
    for i, idx in enumerate(kr_indices):
        with cols[i]:
            if not idx.error:
                change_color = "#00ff88" if idx.change_percent >= 0 else "#ff4444"
                change_sign = "+" if idx.change_percent >= 0 else ""
                st.markdown(f"""
                <div class="index-card">
                    <div class="index-name">🇰🇷 {idx.name}</div>
                    <div class="index-price">{idx.current_price:,.2f}</div>
                    <div style="color:{change_color};">{change_sign}{idx.change_percent:.2f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning(f"{idx.name}: {idx.error}")
    
    st.divider()
    st.info("💡 TradingView 무료 위젯이 한국 개별주식을 지원하지 않아 **Yahoo Finance** 데이터로 표시합니다.")
    
    kr_favorites = load_kr_favorites()
    
    st.caption("⭐ 즐겨찾기")
    cols = st.columns(min(len(kr_favorites), 5))
    kr_selected = None
    for i, t in enumerate(kr_favorites):
        name = get_kr_stock_name(t)
        if cols[i % len(cols)].button(name, key=f"kr_fav_{t}", use_container_width=True):
            kr_selected = t
    
    with st.expander("⚙️ 즐겨찾기 관리"):
        c1, c2 = st.columns(2)
        with c1:
            new_kr = st.text_input("➕ 종목코드", placeholder="005930", key="kr_add")
            if st.button("추가", key="kr_add_btn") and new_kr:
                add_kr_favorite(new_kr)
                st.rerun()
        with c2:
            del_kr = st.selectbox("➖ 삭제", kr_favorites, key="kr_del", format_func=get_kr_stock_name)
            if st.button("삭제", key="kr_del_btn") and del_kr:
                remove_kr_favorite(del_kr)
                st.rerun()
    
    st.divider()
    kr_code = st.text_input("🔍 종목코드", value=kr_selected.replace("KRX:", "") if kr_selected else "005930", placeholder="005930", key="kr_search")
    
    kr_period = st.selectbox("📅 기간", ["30일", "60일", "90일", "180일", "1년"], index=0, key="kr_period")
    kr_days = {"30일": 30, "60일": 60, "90일": 90, "180일": 180, "1년": 365}[kr_period]
    
    with st.spinner(f"{get_kr_stock_name(kr_code)} 데이터 로딩..."):
        kr_data = fetch_kr_stock(kr_code, days=kr_days)
    
    if kr_data.error:
        st.error(f"오류: {kr_data.error}")
    else:
        col1, col2 = st.columns(2)
        col1.metric(f"📈 {kr_data.name}", f"₩{kr_data.current_price:,.0f}" if kr_data.current_price else "N/A")
        if kr_data.change_percent:
            col2.metric("등락률", f"{kr_data.change_percent:+.2f}%", delta=f"{kr_data.change_percent:+.2f}%")
        
        if kr_data.history:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[h[0] for h in kr_data.history],
                y=[h[1] for h in kr_data.history],
                mode="lines",
                line=dict(color="#00CED1", width=2),
                name=kr_data.name,
            ))
            fig.update_layout(
                title=f"{kr_data.name} ({kr_code}) - {kr_period}",
                template="plotly_dark",
                height=350,
                xaxis_title="날짜",
                yaxis_title="가격 (원)",
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Forex & Commodities ---
with tabs[2]:
    st.subheader("💱 원화 기준 환율")
    cols = st.columns(4)
    for i, (label, sym) in enumerate([("🇺🇸 USD", "FX_IDC:USDKRW"), ("🇯🇵 JPY", "FX_IDC:JPYKRW"), ("🇪🇺 EUR", "FX_IDC:EURKRW"), ("🇨🇳 CNY", "FX_IDC:CNYKRW")]):
        with cols[i]:
            st.caption(label)
            TradingViewWidget.render_commodity_mini_chart(sym, height=160, locale="kr")
    
    st.divider()
    st.subheader("🛢️ 원자재 현황")
    
    period = st.selectbox("📅 기간", ["30일", "60일", "90일", "180일", "1년"], index=0, key="commodity_period")
    period_days = {"30일": 30, "60일": 60, "90일": 90, "180일": 180, "1년": 365}[period]
    
    with st.spinner("로딩..."):
        commodities = get_all_commodities(days=period_days)
    
    cols = st.columns(4)
    icons = {"gold": "🥇", "oil": "⛽", "copper": "🔌", "natgas": "🔥"}
    for i, (key, data) in enumerate(commodities.items()):
        with cols[i]:
            if not data.error:
                st.metric(f"{icons.get(key)} {data.name}", f"${data.current_price:,.2f}", f"{data.change_percent:+.2f}%" if data.change_percent else None)
    
    st.divider()
    cols = st.columns(2)
    colors = {"gold": "#FFD700", "oil": "#8B4513", "copper": "#B87333", "natgas": "#00CED1"}
    for i, (key, data) in enumerate(commodities.items()):
        with cols[i % 2]:
            if data.history:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=[h[0] for h in data.history], y=[h[1] for h in data.history], mode="lines", line=dict(color=colors.get(key), width=2)))
                fig.update_layout(title=f"{icons.get(key)} {data.name}", template="plotly_dark", height=180, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

# --- Tab 4: Macro ---
with tabs[3]:
    st.subheader("📈 Fear & Greed Index")
    
    cols = st.columns(2)
    cnn = fg_data["cnn"]
    crypto = fg_data["crypto"]
    
    with cols[0]:
        if not cnn.error:
            color = "#FF4444" if cnn.value <= 25 else "#FF8800" if cnn.value <= 45 else "#FFFF00" if cnn.value <= 55 else "#88FF00" if cnn.value <= 75 else "#00FF00"
            st.markdown(f"""
            <div style="text-align:center; padding:15px; background:linear-gradient(135deg, #1a1a2e, #16213e); border-radius:10px;">
                <div style="font-size:12px; color:#888;">📈 {cnn.source}</div>
                <div style="font-size:48px; font-weight:bold; color:{color};">{cnn.value}</div>
                <div style="font-size:14px;">{cnn.classification}</div>
            </div>
            """, unsafe_allow_html=True)
    
    with cols[1]:
        if not crypto.error:
            color = "#FF4444" if crypto.value <= 25 else "#FF8800" if crypto.value <= 45 else "#FFFF00" if crypto.value <= 55 else "#88FF00" if crypto.value <= 75 else "#00FF00"
            st.markdown(f"""
            <div style="text-align:center; padding:15px; background:linear-gradient(135deg, #1a1a2e, #16213e); border-radius:10px;">
                <div style="font-size:12px; color:#888;">₿ {crypto.source}</div>
                <div style="font-size:48px; font-weight:bold; color:{color};">{crypto.value}</div>
                <div style="font-size:14px;">{crypto.classification}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.info("💡 0-25: 극도의 공포, 75-100: 극도의 탐욕")
    
    st.divider()
    st.subheader("📈 미국 국채 금리")
    
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        with st.spinner("로딩..."):
            yields = get_treasury_yields()
        
        cols = st.columns(3)
        for i, (sid, label) in enumerate(zip(["DGS2", "DGS10", "DGS30"], ["2년물", "10년물", "30년물"])):
            d = yields[sid]
            if not d.error:
                cols[i].metric(label, f"{d.current_value:.2f}%")
        
        fig = go.Figure()
        for sid, name, color in [("DGS2", "2Y", "#00CED1"), ("DGS10", "10Y", "#FFD700"), ("DGS30", "30Y", "#FF6347")]:
            d = yields[sid]
            if d.history:
                fig.add_trace(go.Scatter(x=[h[0] for h in d.history], y=[h[1] for h in d.history], mode="lines", name=name, line=dict(color=color, width=2)))
        fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 5: Crypto ---
with tabs[4]:
    st.subheader("₿ 크립토 & 김치프리미엄")
    
    kp = get_kimchi_premium()
    if not kp.error:
        c1, c2, c3 = st.columns(3)
        c1.metric("BTC (글로벌)", f"${kp.btc_global_usd:,.0f}")
        c2.metric("BTC (국내)", f"₩{kp.btc_korea_krw:,.0f}")
        c3.metric("🌶️ 김프", f"{kp.premium_percent:.2f}%", delta=f"{kp.premium_percent:.2f}%", delta_color="inverse" if kp.premium_percent > 0 else "normal")
        log_market_snapshot(kp.btc_global_usd, kp.btc_korea_krw, kp.premium_percent, kp.usd_krw_rate)
    
    st.divider()
    cols = st.columns(3)
    for i, (label, sym) in enumerate([("₿ BTC", "BINANCE:BTCUSDT"), ("Ξ ETH", "BINANCE:ETHUSDT"), ("📊 USDT.D", "CRYPTOCAP:USDT.D")]):
        with cols[i]:
            st.caption(label)
            TradingViewWidget.render_commodity_mini_chart(sym, height=180, locale="kr")
    
    st.divider()
    crypto_sym = st.text_input("🔍 코인 검색", value="BINANCE:BTCUSDT", key="crypto_search").upper()
    TradingViewWidget.render_advanced_chart(crypto_sym, height=400, locale="kr")

# --- Tab 6: Market Intel ---
with tabs[5]:
    st.subheader("📅 경제 캘린더")
    
    selected_date = st.date_input("📆 날짜 선택", value=datetime.now(), key="calendar_date")
    selected_datetime = datetime.combine(selected_date, datetime.min.time())
    
    st.markdown(get_translated_economic_events(selected_datetime))
    
    st.divider()
    st.subheader("📰 시장 뉴스")
    st.caption("📌 중요도: 거시경제 > 지수 > 개별주식 순으로 정렬")
    
    use_gemini = st.checkbox("🔄 Gemini 한국어 번역", value=True)
    if use_gemini:
        with st.spinner("뉴스 수집 및 번역 중..."):
            st.markdown(get_translated_market_news())
    else:
        TradingViewWidget.render_timeline(height=350, locale="kr")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.link_button("📊 SaveTicker", "https://www.saveticker.com/app/news")
    c2.link_button("🇰🇷 Investing.com", "https://kr.investing.com/economic-calendar/")
