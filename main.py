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

# Load environment variables cautiously
load_dotenv(override=True) # Force .env to win over local system environment variables

from components.tv_widgets import TradingViewWidget
from services.crypto_service import get_kimchi_premium
from services.data_service import log_market_snapshot, load_journal, append_journal_entry
from services.ai_service import generate_market_insight
from services.fred_service import get_treasury_yields
from services.favorites_service import load_favorites, add_favorite, remove_favorite
from services.kr_stock_service import (
    get_kr_stock_name,
    fetch_kr_stock,
    fetch_kr_index_history
)
from services.kr_favorites_service import load_kr_favorites, add_kr_favorite, remove_kr_favorite
from services.news_service import get_translated_economic_events, get_translated_market_news
from services.commodity_service import get_all_commodities
from services.fear_greed_service import get_fear_greed_index
from services.index_service import get_us_indices, get_kr_indices
from config.settings import APP_TITLE, APP_ICON

# ============================================================
# ============================================================
# Page Config
# ============================================================
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="collapsed")
st.caption("🚀 Invest Dashboard ver 1.0")

# Use slightly different CSS to accommodate widgets
st.markdown("""
    <style>
        .block-container {padding: 0.5rem;}
        header, footer {visibility: hidden;}
        /* Widget containers */
        iframe {margin-bottom: 0px !important;}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# State Management (Fix Favorites)
# ============================================================
if "us_symbol" not in st.session_state:
    st.session_state["us_symbol"] = "NASDAQ:NVDA"
    
if "kr_symbol" not in st.session_state:
    st.session_state["kr_symbol"] = "005930"

# ============================================================
# Sidebar Configuration
# ============================================================
with st.sidebar:
    st.header("⚙️ 서비스 설정")
    manual_gemini_key = st.text_input(
        "Gemini API Key (Bypass)", 
        value=st.session_state.get("manual_gemini_key", ""), 
        type="password"
    )
    if manual_gemini_key:
        st.session_state["manual_gemini_key"] = manual_gemini_key

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
# Sidebar Actions
# ============================================================
with st.sidebar:
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
    st.subheader("📊 미국 주요 지수 (실시간)")
    
    # Replace Static Grid with TradingView Mini Charts
    cols = st.columns(3)
    indices = [
        ("S&P 500", "FOREXCOM:SPXUSD"), 
        ("Nasdaq 100", "FOREXCOM:NSXUSD"), 
        ("Dow 30", "FOREXCOM:DJI")
    ]
    for i, (name, sym) in enumerate(indices):
        with cols[i]:
            st.caption(name)
            TradingViewWidget.render_commodity_mini_chart(sym, height=180, locale="kr")
    
    st.divider()
    
    # Favorites Logic
    favorites = load_favorites()
    st.caption("⭐ 즐겨찾기")
    
    # Dynamic Columns for Buttons
    f_cols = st.columns(min(len(favorites), 6) if favorites else 1)
    
    for i, t in enumerate(favorites):
        name = t.split(":")[-1] if ":" in t else t
        # If clicked, update session state and rerun
        if f_cols[i % len(f_cols)].button(name, key=f"us_fav_{t}", use_container_width=True):
            st.session_state["us_symbol"] = t
            st.rerun()
            
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
    
    # Search input linked to Session State
    def on_us_search_change():
        st.session_state["us_symbol"] = st.session_state.us_search_input.upper()

    symbol = st.text_input(
        "🔍 티커 검색", 
        value=st.session_state["us_symbol"], 
        key="us_search_input",
        on_change=on_us_search_change
    ).upper()
    
    TradingViewWidget.render_advanced_chart(symbol, height=500, locale="kr")
    st.caption(f"📊 {symbol} 기술적 분석")
    TradingViewWidget.render_technical_analysis(symbol, height=350, locale="kr")

# --- Tab 2: Korean Stocks ---
with tabs[1]:
    st.subheader("📊 한국 주요 지수")
    
    # 차트용 데이터 로딩 (Plotly Candlestick)
    with st.spinner("차트 데이터 로딩 중..."):
        kospi_data = fetch_kr_index_history("KOSPI", days=365)
        kosdaq_data = fetch_kr_index_history("KOSDAQ", days=365)
    
    # 지수 정보 추출
    def get_index_info(data, name):
        if not data:
            return {"name": name, "price": 0, "pct": 0, "color": "#777", "sign": ""}
        latest = data[-1]
        prev = data[-2] if len(data) > 1 else latest
        price = latest['close']
        pct = ((price - prev['close']) / prev['close']) * 100
        color = "#00ff88" if pct >= 0 else "#ff4444"
        sign = "+" if pct >= 0 else ""
        return {"name": name, "price": price, "pct": pct, "color": color, "sign": sign}
    
    k_info = get_index_info(kospi_data, "KOSPI")
    kq_info = get_index_info(kosdaq_data, "KOSDAQ")
    
    # 클릭 가능한 지수 카드 (네이버 금융 링크)
    st.markdown(f"""
    <style>
    .kr-index-grid {{ display: flex; gap: 15px; margin-bottom: 20px; }}
    .kr-index-card {{
        flex: 1; padding: 15px; border-radius: 10px; text-align: center;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #3b3c46; text-decoration: none; display: block;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    .kr-index-card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }}
    .kr-idx-name {{ font-size: 14px; color: #b0b0b0; margin-bottom: 5px; }}
    .kr-idx-price {{ font-size: 22px; font-weight: bold; color: #fff; }}
    .kr-idx-link {{ font-size: 11px; color: #6b7280; margin-top: 8px; }}
    </style>
    <div class="kr-index-grid">
        <a href="https://finance.naver.com/sise/sise_index.naver?code=KOSPI" target="_blank" class="kr-index-card">
            <div class="kr-idx-name">🇰🇷 {k_info['name']}</div>
            <div class="kr-idx-price">{k_info['price']:,.2f}</div>
            <div style="color:{k_info['color']}; font-size: 14px; font-weight: bold;">{k_info['sign']}{k_info['pct']:.2f}%</div>
            <div class="kr-idx-link">실시간 보기 →</div>
        </a>
        <a href="https://finance.naver.com/sise/sise_index.naver?code=KOSDAQ" target="_blank" class="kr-index-card">
            <div class="kr-idx-name">🇰🇷 {kq_info['name']}</div>
            <div class="kr-idx-price">{kq_info['price']:,.2f}</div>
            <div style="color:{kq_info['color']}; font-size: 14px; font-weight: bold;">{kq_info['sign']}{kq_info['pct']:.2f}%</div>
            <div class="kr-idx-link">실시간 보기 →</div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Charts (Plotly - 안정적인 렌더링)
    st.caption("📉 차트 (FinanceData 실시간 반영)")
    k_chart_cols = st.columns(2)
    
    def render_index_chart(data, title):
        """Plotly 기반 지수 차트 렌더링"""
        if not data or len(data) == 0:
            st.warning(f"{title} 데이터 없음")
            return
            
        fig = go.Figure()
        
        # Candlestick Chart
        fig.add_trace(go.Candlestick(
            x=[d['time'] for d in data],
            open=[d['open'] for d in data],
            high=[d['high'] for d in data],
            low=[d['low'] for d in data],
            close=[d['close'] for d in data],
            name=title,
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ))
        
        fig.update_layout(
            template="plotly_dark",
            height=280,
            margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(19,23,34,1)',
            xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=True, gridcolor='rgba(42,46,57,0.5)'),
            title=dict(text=title, font=dict(size=14, color='#d1d4dc'), x=0.5),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with k_chart_cols[0]:
        render_index_chart(kospi_data, "KOSPI")
        
    with k_chart_cols[1]:
        render_index_chart(kosdaq_data, "KOSDAQ")

    st.divider()
    
    kr_favorites = load_kr_favorites()
    st.caption("⭐ 즐겨찾기")
    
    kf_cols = st.columns(min(len(kr_favorites), 6) if kr_favorites else 1)
    
    for i, t in enumerate(kr_favorites):
        name = get_kr_stock_name(t)
        if kf_cols[i % len(kf_cols)].button(name, key=f"kr_fav_{t}", use_container_width=True):
            st.session_state["kr_symbol"] = t
            st.rerun()
            
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
    
    def on_kr_search_change():
        st.session_state["kr_symbol"] = st.session_state.kr_search_input

    kr_code_full = st.text_input(
        "🔍 종목코드", 
        value=st.session_state["kr_symbol"], 
        key="kr_search_input",
        on_change=on_kr_search_change
    )
    kr_code = kr_code_full.replace("KRX:", "") 
    
    with st.spinner(f"{get_kr_stock_name(kr_code)} 데이터 로딩..."):
        kr_data = fetch_kr_stock(kr_code, days=365)
    
    if kr_data.error:
        st.error(f"오류: {kr_data.error} (종목코드를 확인하세요)")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric(
                f"📈 {kr_data.name}", 
                f"₩{kr_data.current_price:,.0f}" if kr_data.current_price else "N/A",
                f"{kr_data.change_percent:+.2f}%" if kr_data.change_percent else "0%"
            )
        with col2:
            st.caption("최근 1년 주가 추이 (Fast Engine)")
            if kr_data.history:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[h[0] for h in kr_data.history],
                    y=[h[1] for h in kr_data.history],
                    mode="lines",
                    line=dict(color="#00CED1", width=2),
                    name=kr_data.name,
                    fill='tozeroy',
                    fillcolor='rgba(0, 206, 209, 0.1)'
                ))
                fig.update_layout(
                    template="plotly_dark",
                    height=300,
                    margin=dict(l=0,r=0,t=0,b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                )
                st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Forex & Commodities ---
with tabs[2]:
    st.subheader("💱 실시간 환율 & 원자재")
    cols = st.columns(4)
    # Restore full list: USD, JPY, EUR, CNY
    forex_list = [
        ("🇺🇸 USD/KRW", "FX_IDC:USDKRW"), 
        ("🇯🇵 JPY/KRW", "FX_IDC:JPYKRW"), 
        ("🇪🇺 EUR/KRW", "FX_IDC:EURKRW"), 
        ("🇨🇳 CNY/KRW", "FX_IDC:CNYKRW")
    ]
    for i, (label, sym) in enumerate(forex_list):
        with cols[i]:
            st.caption(label)
            TradingViewWidget.render_commodity_mini_chart(sym, height=180, locale="kr")
            
    st.divider()
    
    # Enable horizontal scrolling for commodities if many
    c_cols = st.columns(4)
    # Use Unrestricted CFDs for Widgets
    comm_list = [
        ("🥇 Gold", "TVC:GOLD"), 
        ("⛽ Oil", "TVC:USOIL"), 
        ("🔌 Copper (CFD)", "CAPITALCOM:COPPER"),       # CFD Proxy
        ("🔥 NatGas (CFD)", "CAPITALCOM:NATURALGAS")    # CFD Proxy
    ]
    for i, (label, sym) in enumerate(comm_list):
        with c_cols[i]:
            st.caption(label)
            TradingViewWidget.render_commodity_mini_chart(sym, height=180, locale="kr")

# --- Tab 4: Macro ---
with tabs[3]:
    st.subheader("📈 Fear & Greed Index")
    
    cols = st.columns(2)
    cnn = fg_data["cnn"]
    crypto = fg_data["crypto"]
    
    # Restore Visuals
    with cols[0]:
        if not cnn.error:
            # Simple Gauge Color Logic
            val = int(cnn.value)
            color = "#FF4444" if val <= 25 else "#FF8800" if val <= 45 else "#FFFF00" if val <= 55 else "#88FF00" if val <= 75 else "#00FF00"
            st.markdown(f"""
            <div style="text-align:center; padding:15px; background:linear-gradient(135deg, #1a1a2e, #16213e); border-radius:10px; border: 1px solid {color};">
                <div style="font-size:14px; color:#ccc;">CNN Market Mood</div>
                <div style="font-size:42px; font-weight:bold; color:{color};">{val}</div>
                <div style="font-size:16px; color:#fff;">{cnn.classification}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("CNN Data Error")
    
    with cols[1]:
        if not crypto.error:
            val = int(crypto.value)
            color = "#FF4444" if val <= 25 else "#FF8800" if val <= 45 else "#FFFF00" if val <= 55 else "#88FF00" if val <= 75 else "#00FF00"
            st.markdown(f"""
            <div style="text-align:center; padding:15px; background:linear-gradient(135deg, #1a1a2e, #16213e); border-radius:10px; border: 1px solid {color};">
                <div style="font-size:14px; color:#ccc;">Crypto Fear & Greed</div>
                <div style="font-size:42px; font-weight:bold; color:{color};">{val}</div>
                <div style="font-size:16px; color:#fff;">{crypto.classification}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Crypto Data Error")
    
    st.divider()
    st.subheader("🇺🇸 미국 국채 금리")
    
    # Revert to FRED Data (No 'Restricted Symbol' errors)
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        with st.spinner("FRED 데이터 로딩..."):
            yields = get_treasury_yields()
        
        y_cols = st.columns(3)
        for i, (sid, label) in enumerate(zip(["DGS2", "DGS10", "DGS30"], ["2년물", "10년물", "30년물"])):
            d = yields[sid]
            with y_cols[i]:
                if not d.error:
                    change_color = "#00ff88" if d.change >= 0 else "#ff4444"
                    st.markdown(f"""
                    <div class="index-card">
                        <div class="index-name">{label}</div>
                        <div class="index-price">{d.current_value:.2f}%</div>
                        <div style="color:{change_color};">{d.change:+.2f}bp</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"{label} 로딩 실패")
        
        # Restore Graph
        st.write("") 
        fig = go.Figure()
        for sid, name, color in [("DGS2", "2Y", "#00CED1"), ("DGS10", "10Y", "#FFD700"), ("DGS30", "30Y", "#FF6347")]:
            d = yields[sid]
            if d.history:
                fig.add_trace(go.Scatter(x=[h[0] for h in d.history], y=[h[1] for h in d.history], mode="lines", name=name, line=dict(color=color, width=2)))
        fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 5: Crypto ---
with tabs[4]:
    st.subheader("₿ 실시간 크립토")
    c_cols = st.columns(3)
    for i, (label, sym) in enumerate([("₿ BTC/USDT", "BINANCE:BTCUSDT"), ("Ξ ETH/USDT", "BINANCE:ETHUSDT"), ("🐕 DOGE/USDT", "BINANCE:DOGEUSDT")]):
        with c_cols[i]:
            st.caption(label)
            TradingViewWidget.render_commodity_mini_chart(sym, height=180, locale="kr")
    
    st.divider()
    kp = get_kimchi_premium()
    if not kp.error:
         st.metric("🌶️ 김치 프리미엄", f"{kp.premium_percent:.2f}%", f"{kp.btc_korea_krw:,.0f} KRW (Upbit) / ${kp.btc_global_usd:,.0f} (Binance)")

    st.divider()
    
    # Restore Advanced Chart for Crypto
    def on_crypto_search_change():
        st.session_state["crypto_symbol"] = st.session_state.crypto_search_input

    if "crypto_symbol" not in st.session_state: st.session_state["crypto_symbol"] = "BINANCE:BTCUSDT"

    crypto_sym = st.text_input("🔍 코인 검색", value=st.session_state["crypto_symbol"], key="crypto_search_input", on_change=on_crypto_search_change).upper()
    TradingViewWidget.render_advanced_chart(crypto_sym, height=500, locale="kr")

# --- Tab 6: Market Intel ---
with tabs[5]:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📅 경제 캘린더 (실시간)")
        TradingViewWidget.render_economic_calendar(height=600, locale="kr")
        
    with c2:
        st.subheader("📰 시장 뉴스 (AI 번역)")
        use_gemini = st.checkbox("Gemini 번역 활성화", value=True)
        if use_gemini:
            st.markdown(get_translated_market_news())
        else:
            TradingViewWidget.render_timeline(height=600, locale="kr")
