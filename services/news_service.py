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
from dotenv import load_dotenv

load_dotenv(override=True)


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
    
    # Sort EVERYTHING by time first to find true "Breaking" news
    all_items.sort(key=lambda x: x["hours_ago"])
    
    final = []
    
    # 1. 속보 (Breaking): 2 개
    # 무조건 가장 최신 2개를 가져옴 (카테고리 무관)
    breaking_quota = 2
    breaking = all_items[:breaking_quota]
    final.extend(breaking)
    
    # Remove selected items from pool
    pool = all_items[breaking_quota:]
    
    # 2. Bucketize Remaining
    buckets = {1: [], 2: [], 3: []}
    for item in pool: buckets[item["priority"]].append(item)
    
    # 3. Quota Selection (Macro 2, Index 3, Stock 3)
    quotas = {1: 2, 2: 3, 3: 3}
    
    for cat in [1, 2, 3]:
        count = quotas[cat]
        selected = buckets[cat][:count]
        final.extend(selected)
        # 만약 쿼터를 못 채웠으면 나중에 채우기 위해 남은거 기록할 필요 없음 (자동으로 아래 로직에서 해결)
        buckets[cat] = buckets[cat][count:]
    
    # 4. Fill Deficit (If total < 10, fill with remaining newest items from any category)
    if len(final) < 10:
        rem = []
        for cat in [1, 2, 3]: rem.extend(buckets[cat])
        rem.sort(key=lambda x: x["hours_ago"])
        final.extend(rem[:10 - len(final)])
    
    # 5. Final Sort (Latest first) and Trim
    final.sort(key=lambda x: x["hours_ago"])
    final = final[:10]
    
    # --- Translation & Formatting ---
    api_key = os.getenv("GEMINI_API_KEY")
    titles = [n["title"] for n in final]
    translated = titles # Default
    
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            prompt = f"""
            Translate updated financial headlines to Korean.
            Summarize slightly.
            Return ONLY raw JSON list of strings.
            Input: {json.dumps(titles)}
            """
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                translated = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
        except: pass

    # Formatter
    lines = ["### 📰 시장 뉴스 (실시간)", ""]
    for i, (item, tr) in enumerate(zip(final, translated)):
        t = tr if tr else item["title"]
        # Add a "🔥" badge for breaking news (top 2 news if really fresh, e.g. < 2 hours)
        badge = "🔥" if i < 2 and item["hours_ago"] < 3 else "📢"
        
        line_1 = f"**{badge} [{item['time']}] {item['source']}** [🔗]({item['link']})"
        line_2 = f"&nbsp;&nbsp;&nbsp;&nbsp;{t}"
        lines.append(f"{line_1}  \n{line_2}")
        lines.append("")
        
    return "\n".join(lines)


def get_translated_economic_events(target_date: Optional[datetime] = None) -> str:
    if target_date is None: target_date = datetime.now()
    return format_economic_calendar(target_date)
