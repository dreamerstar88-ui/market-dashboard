"""
AI Service - Gemini Integration for Market Insights
Generates one-line strategic advice based on market data and user journal.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


try:
    import streamlit as st
except ImportError:
    st = None

def generate_market_insight(
    kimchi_premium: float,
    usd_krw: float,
    journal_text: str
) -> Optional[str]:
    """
    Gemini AI를 사용하여 시장 데이터와 투자 일지를 기반으로 한 줄 인사이트를 생성합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if st:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass
            
    if api_key:
        api_key = str(api_key).strip().replace('"', '').replace("'", "")

    if not api_key or api_key == "None":
        return "⚠️ GEMINI_API_KEY가 설정되지 않았습니다."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""당신은 세계적인 투자 전략가입니다. 아래 정보를 바탕으로 간결하고 실행 가능한 한 줄 인사이트를 제공하세요.

**현재 시장 데이터:**
- 김치프리미엄: {kimchi_premium:.2f}%
- 원달러 환율: {usd_krw:,.0f}원

**사용자의 최근 투자 메모:**
{journal_text[-500:] if journal_text else "(없음)"}

**요청:**
위 정보를 종합하여, 지금 시점에서 사용자가 주목해야 할 핵심 포인트를 이모지와 함께 한 줄(50자 이내)로 조언해 주세요. 예시: "💡 김프 역전! 해외 직구 타이밍 검토" 
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=100,
                temperature=0.7,
            ),
        )
        return response.text.strip()

    except ImportError:
        return "⚠️ google-genai 라이브러리가 설치되지 않았습니다. `pip install google-genai`"
    except Exception as e:
        return f"⚠️ AI 분석 오류: {str(e)}"
