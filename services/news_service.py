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
        load_dotenv()
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
        # Clean the API Key (Remove quotes and spaces that often come from TOML/Secrets copy-paste)
        self.api_key = str(api_key).strip().replace('"', '').replace("'", "") if api_key else None
        self.client = None
        self.last_error = None
        if self.api_key and self.api_key != "None":
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                self.last_error = f"Library Load Error: {str(e)}"

    def translate_headlines(self, titles: List[str]) -> List[str]:
        """기사를 유동적으로 번역하여 리스트로 반환"""
        if not self.api_key:
            self.last_error = "API Key missing"
            return titles
            
        count = len(titles)
        prompt = f"Translate to Korean. Return JSON list. Input: {json.dumps(titles, ensure_ascii=False)}"

        # Models to try in order
        models = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
        
        # Trial 1: SDK (The most robust way if library is present)
        if self.client:
            for model_name in models:
                try:
                    from google.genai import types
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.0)
                    )
                    if response.text:
                        result = parse_json_list(response.text)
                        if result:
                            # Success! Ensure 1:1 mapping
                            final_list = titles.copy()
                            for i, r in enumerate(result[:count]): final_list[i] = r
                            return final_list
                except Exception as e:
                    self.last_error = f"SDK {model_name} Error: {str(e)}"
                    print(f"TranslationService: {model_name} failed. {e}")
                    continue # Try next model
        
        # Trial 2: REST Fallback (Direct request v1)
        # Using a very simple prompt to avoid 400s
        try:
            # v1 is more standard for GA models
            headers = {'Content-Type': 'application/json'}
            # Try both standard and latest names
            for m_id in ["gemini-1.5-flash", "gemini-1.5-flash-latest"]:
                url = f"https://generativelanguage.googleapis.com/v1/models/{m_id}:generateContent?key={self.api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    result = parse_json_list(text)
                    if result:
                        final_list = titles.copy()
                        for i, r in enumerate(result[:count]): final_list[i] = r
                        return final_list
                else:
                    self.last_error = f"REST {m_id} Error {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            self.last_error = f"Connection Error: {str(e)}"

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
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            if env_key.endswith("nRjSY"):
                source = "OS Environment (POISONED - OLD KEY DETECTED)"
                api_key = None 
            else:
                api_key = env_key
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
    if success_count == 0:
        lines.append(f"> 🧪 **Diagnostic**: {source}")
        lines.append(f"> 📂 **Secrets Keys Found**: `{detected_keys if detected_keys else 'None'}`")
        if api_key:
            lines.append(f"> 🛠️ **Key Check**: {key_tag}")
            lines.append(f"> ❌ **번역 실패**: `{service.last_error if service.last_error else 'Unknown error'}`")
        else:
            lines.append("> 🚨 **알림**: 유효한 API 키가 없습니다. 위 'Secrets Keys Found'에 `GEMINI_API_KEY`가 있는지 확인해 주세요.")
    elif success_count < len(titles):
        lines.append(f"> 🔄 **번역 상태**: {success_count}/{len(titles)} 항목 완료 (Source: {source})")
    else:
        lines.append(f"> ✅ **뉴스 번역 완료** (Source: {source})")
    lines.append("")

    for i, item in enumerate(final):
        t = translated[i]
        badge = "🔥" if i < 2 and item["hours_ago"] < 3 else "📢"
        lines.append(f"**{badge} [{item['time']}] {item['source']}** [🔗]({item['link']})  \n&nbsp;&nbsp;&nbsp;&nbsp;{t}\n")
        
    return "\n".join(lines)


def get_translated_economic_events(target_date: Optional[datetime] = None) -> str:
    if target_date is None: target_date = datetime.now()
    return format_economic_calendar(target_date)



def get_translated_economic_events(target_date: Optional[datetime] = None) -> str:
    if target_date is None: target_date = datetime.now()
    return format_economic_calendar(target_date)
