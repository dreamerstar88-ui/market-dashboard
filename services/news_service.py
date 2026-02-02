"""
News Service v17.1 - Quota: Breaking(2), Macro(2), Index(3), Stock(3)
- Breaking: Top 2 freshest items (any category)
- Others: Filtered by category
"""
import os
import requests
import re
import html
import json
from datetime import datetime
from typing import Optional, List, Dict
try:
    import streamlit as st
except ImportError:
    st = None

# Professional Practice: Don't load .env globally in a way that overrides Cloud Secrets
if not st:
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        pass


def get_economic_events_for_date(target_date: datetime) -> List[Dict]:
    """특정 날짜의 경제 이벤트 반환"""
    return [
        {"time": "08:00", "country": "🇰🇷", "event": "산업생산지수 (MoM)", "importance": "중", "forecast": "0.3%", "actual": "0.5%", "previous": "-0.2%"},
        {"time": "08:30", "country": "🇯🇵", "event": "도쿄 핵심 CPI (YoY)", "importance": "높음", "forecast": "2.4%", "actual": None, "previous": "2.2%"},
        {"time": "10:00", "country": "🇨🇳", "event": "제조업 PMI", "importance": "높음", "forecast": "50.2", "actual": None, "previous": "49.8%"},
        {"time": "18:00", "country": "🇪🇺", "event": "소비자물가지수 (CPI) (YoY)", "importance": "높음", "forecast": "2.8%", "actual": None, "previous": "2.9%"},
        {"time": "21:30", "country": "🇺🇸", "event": "PCE 물가지수 (Core)", "importance": "높음", "forecast": "0.2%", "actual": None, "previous": "0.1%"},
        {"time": "22:00", "country": "🇺🇸", "event": "미시간 소비자심리", "importance": "중", "forecast": "72.0", "actual": None, "previous": "71.1%"},
        {"time": "22:45", "country": "🇺🇸", "event": "시카고 PMI", "importance": "낮음", "forecast": "40.5", "actual": None, "previous": "36.9"},
    ]


def format_economic_calendar(target_date: datetime) -> str:
    """경제 캘린더 마크다운 포맷"""
    events = get_economic_events_for_date(target_date)
    date_str = target_date.strftime("%Y-%m-%d")
    lines = [f"### 📅 {date_str} 주요 경제 지표", "", "| 시간 | 국가 | 지표 | 중요도 | 예측 | 실제 | 이전 |", "|:----:|:----:|------|:------:|:----:|:----:|:----:|"]
    for e in events:
        actual = e["actual"] if e["actual"] else "⏳"
        imp = "🔴" if e["importance"] == "높음" else "🟡" if e["importance"] == "중" else "⚪"
        lines.append(f"| {e['time']} | {e['country']} | {e['event']} | {imp} | {e['forecast']} | {actual} | {e['previous']} |")
    
    lines.extend([
        "",
        "---",
        "**📌 중요도 범례:** 🔴 높음 | 🟡 중간 | ⚪ 낮음",
        "> 💡 ⏳ = 발표 대기 중"
    ])
    return "\n".join(lines)


def categorize_news(title: str) -> int:
    """뉴스 카테고리 분류 (1:거시, 2:지수, 3:주식)"""
    t = title.lower()
    macro = ['fed', 'rate', 'inflation', 'cpi', 'gdp', 'job', 'economy', 'recession', 'policy', 'treasury', 'yield', 'war', 'oil', 'gold', '금리', '물가', '연준']
    index = ['s&p', 'nasdaq', 'dow', 'market', 'stocks', 'rally', 'crash', 'bull', 'bear', 'index', 'kospi', 'kosdaq', '지수', '증시', '상승', '하락', 'futures']
    if any(k in t for k in macro): return 1
    if any(k in t for k in index): return 2
    return 3


def fetch_rss_news(feed_url: str, source_name: str) -> List[Dict]:
    """RSS Parser"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(feed_url, headers=headers, timeout=10)
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        news_list = []
        now = datetime.now()
        
        # Increase fetch limit to 30 to ensure we have enough candidates
        for item in items[:30]:
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
            pub_m = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
            
            if title_m:
                t = html.unescape(re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_m.group(1))).strip()
                t = re.sub(r'<[^>]+>', '', t)
                l = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link_m.group(1)).strip() if link_m else ""
                
                h_ago = 999
                t_disp = "최근"
                if pub_m:
                    try:
                        pd_str = pub_m.group(1).strip()[:25]
                        dt = datetime.strptime(pd_str, "%a, %d %b %Y %H:%M:%S")
                        
                        # Timezone handling assumption (UTC if +0000)
                        diff = (datetime.utcnow() - dt).total_seconds() / 3600
                        
                        h_ago = diff
                        if diff < 1: t_disp = f"{int(diff*60)}분 전"
                        elif diff < 24: t_disp = f"{int(diff)}시간 전"
                        else: t_disp = f"{int(diff/24)}일 전"
                    except: pass
                
                news_list.append({
                    "time": t_disp, "source": source_name, "title": t, "link": l,
                    "priority": categorize_news(t), "hours_ago": h_ago
                })
        return news_list
    except: return []


def parse_json_list(text: str) -> List[str]:
    """AI가 반환한 텍스트에서 JSON 리스트만 추출하는 유틸리티"""
    if not text: return []
    try:
        # 1. ```json ... ``` 블록 제거 시도
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r'^```[a-z]*\s*', '', clean_text)
            clean_text = re.sub(r'\s*```$', '', clean_text)
        
        # 2. JSON 파싱
        return json.loads(clean_text)
    except:
        # 3. 정규브로 리스트 형태만 추출 시도 (마지막 수단)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
        return []


class TranslationService:
    """Gemini API를 이용한 전문 번역 서비스 (Python-Pro patterns)"""
    
    def __init__(self, api_key: Optional[str]):
        self.api_key = api_key
        self.client = None
        self.last_error = ""
        self.available_models = []
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception:
                pass

    def discover_models(self) -> List[str]:
        """조회가 가능한 모델 목록을 수동으로 탐색"""
        if not self.api_key: return []
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"].replace("models/", "") for m in models]
        except:
            pass
        return []

    def translate_headlines(self, titles: List[str]) -> List[str]:
        """기사를 유동적으로 번역하여 리스트로 반환"""
        if not self.api_key:
            self.last_error = "API Key missing"
            return titles
            
        count = len(titles)
        # Prompt Engineering for Strict Korean Only
        prompt = f"Translate these headlines to Korean. Return a flat JSON list of strings. Do not include original English text. Input: {json.dumps(titles, ensure_ascii=False)}"

        # Models to try in order (Custom Config: gemini-2.0-flash is standard)
        models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        # Trial 1: SDK (The most robust way if library is present)
        if self.client:
            try:
                from google.genai import types
                # Use the latest confirmed working model
                model_name = "gemini-2.0-flash" 
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                    )
                )
                if response.text:
                    result = parse_json_list(response.text)
                    if result:
                        final_list = titles.copy()
                        for i, r in enumerate(result[:count]): final_list[i] = r
                        return final_list
            except Exception as e:
                self.last_error = f"SDK Error: {str(e)}"
                print(f"TranslationService: {model_name} failed. {e}")
        
        # Trial 2: REST Fallback (Direct request v1 & v1beta)
        try:
            headers = {'Content-Type': 'application/json'}
            # Try combinations based on confirmed 'Available Models' list
            trials = [
                ("v1beta", "gemini-2.0-flash"),
                ("v1beta", "gemini-1.5-flash"),
                ("v1", "gemini-1.5-flash"),
            ]
            
            for ver, m_id in trials:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{m_id}:generateContent?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                        result = parse_json_list(text)
                        if result:
                            final_list = titles.copy()
                            for i, r in enumerate(result[:count]): final_list[i] = r
                            return final_list
                    else:
                        self.last_error = f"REST {ver}/{m_id} Error {resp.status_code}"
                except Exception as e:
                    self.last_error = f"REST {ver}/{m_id} Conn Error: {str(e)}"
                    continue
        except Exception as e:
            self.last_error = f"Global REST Error: {str(e)}"

        return titles


def get_translated_market_news() -> str:
    """뉴스 쿼터 (속보2, 거시2, 지수3, 종목3)"""
    sources = [
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^IXIC,^DJI,NVDA,TSLA,AAPL,MSFT&region=US&lang=en-US", "Yahoo Finance"),
        ("https://kr.investing.com/rss/news_25.rss", "Investing.com"), 
        ("https://kr.investing.com/rss/stock.rss", "Investing.com"),
        ("https://news.google.com/rss/topics/CAAqJggBCiSJQVVCQzFBUWcyTWpCb1kzbG9hWGIwS2hVcGQzQnliMWRpYXlnQVAB?hl=en-US&gl=US&ceid=US:en", "Google News")
    ]
    
    all_items = []
    seen = set()
    for url, src in sources:
        for item in fetch_rss_news(url, src):
            if item["title"] not in seen:
                seen.add(item["title"])
                all_items.append(item)
    
    all_items.sort(key=lambda x: x["hours_ago"])
    
    # Selection logic remains same for consistency
    breaking_quota = 2
    breaking = all_items[:breaking_quota]
    pool = all_items[breaking_quota:]
    buckets = {1: [], 2: [], 3: []}
    for item in pool: buckets[item["priority"]].append(item)
    quotas = {1: 2, 2: 3, 3: 3}
    final = breaking
    for cat in [1, 2, 3]:
        count = quotas[cat]
        final.extend(buckets[cat][:count])
        buckets[cat] = buckets[cat][count:]
    
    if len(final) < 10:
        rem = []
        for cat in [1, 2, 3]: rem.extend(buckets[cat])
        rem.sort(key=lambda x: x["hours_ago"])
        final.extend(rem[:10 - len(final)])
    
    final.sort(key=lambda x: x["hours_ago"])
    final = final[:10]
    
    # --- Professional Translation (Brute-Force Source Control) ---
    api_key = None
    source = "Not Found"
    detected_keys = []
    
    # Priority 1: Manual Session Bypass (Highest)
    if st and "manual_gemini_key" in st.session_state and st.session_state["manual_gemini_key"]:
        api_key = st.session_state["manual_gemini_key"]
        source = "Sidebar Manual Input"
        
    # Priority 2: Streamlit Secrets
    if not api_key and st:
        try:
            detected_keys = list(st.secrets.keys())
            possible_names = ["GEMINI_API_KEY", "gemini_api_key", "GEMINI_KEY", "Gemini_API"]
            for name in possible_names:
                if name in st.secrets:
                    val = st.secrets[name]
                    if val and val != "None":
                        api_key = val
                        source = f"Streamlit Secrets ({name})"
                        break
        except Exception:
            pass
            
    # Priority 3: OS Environment
    if not api_key:
        # Fallback to OS environment
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            api_key = env_key
            # Detect potentially poisoned key (old one)
            if env_key.endswith("nRjSY"):
                source = "OS Environment (OLD KEY DETECTED - 400 ERRORS LIKELY)"
            else:
                source = "OS Environment (.env or System)"
    
    if api_key:
        # Final clean
        api_key = str(api_key).strip().replace('"', '').replace("'", "")
    
    titles = [n["title"] for n in final]
    service = TranslationService(api_key)
    translated = service.translate_headlines(titles)
    
    # Professional Formatter
    lines = ["### 📰 시장 뉴스 (실시간)", ""]
    
    # Diagnostic Status (Safe Key Verification)
    if api_key:
        key_tag = f"`{api_key[:5]}...{api_key[-5:]}`"
    else:
        key_tag = "`Missing / Blocked`"
        
    success_count = sum(1 for i, t in enumerate(translated) if t != titles[i])
    
    # Clean UI: Use expander for logs if anything is less than perfect
    if success_count < len(titles) or source != "Streamlit Secrets":
        with st.expander("🛠️ 시스템 진단 로그 (번역 문제 발생 시 확인)", expanded=(success_count == 0)):
            st.write(f"**Diagnostic**: {source}")
            st.write(f"**Secrets Detection**: `{detected_keys if detected_keys else 'None'}`")
            if api_key:
                st.write(f"**Key Check**: `{api_key[:5]}...{api_key[-5:]}`")
                st.write(f"**Last Error**: `{service.last_error if service.last_error else 'None'}`")
                models = service.discover_models()
                if models: st.write(f"**Available Models**: `{', '.join(models[:5])}...`")
            else:
                st.error("🚨 유효한 API 키가 없습니다. .env 또는 Secrets를 확인해 주세요.")
    
    if success_count == len(titles):
        lines.append(f"> ✅ **뉴스 번역 완료** (Gemini 2.0)")
    elif success_count > 0:
        lines.append(f"> 🔄 **번역 상태**: {success_count}/{len(titles)} 항목 완료")
    else:
        lines.append("> ⏳ **번역 대기 중**: API 설정을 확인해 주세요.")
    lines.append("")

    for i, item in enumerate(final):
        t = translated[i]
        # Logic to detect if it was actually translated
        is_translated = (t != item["title"])
        badge = "🔥" if i < 2 and item["hours_ago"] < 3 else "📢"
        trans_badge = " 🤖" if is_translated else ""
        
        lines.append(f"**{badge} [{item['time']}] {item['source']}**{trans_badge} [🔗]({item['link']})  \n&nbsp;&nbsp;&nbsp;&nbsp;{t}\n")
        
    return "\n".join(lines)


def get_translated_economic_events(target_date: Optional[datetime] = None) -> str:
    if target_date is None: target_date = datetime.now()
    return format_economic_calendar(target_date)



def get_translated_economic_events(target_date: Optional[datetime] = None) -> str:
    if target_date is None: target_date = datetime.now()
    return format_economic_calendar(target_date)
