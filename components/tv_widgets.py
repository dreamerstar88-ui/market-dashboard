"""
TradingView Widget Library v7.0
Added symbol-info widget for indices
"""
import streamlit.components.v1 as components


class TradingViewWidget:
    """TradingView 위젯 생성기 - v7.0"""

    @staticmethod
    def render_ticker_tape(locale: str = "kr") -> None:
        """상단 시세표"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
          {{
            "symbols": [
              {{"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"}},
              {{"proName": "FOREXCOM:NSXUSD", "title": "Nasdaq 100"}},
              {{"proName": "FX_IDC:USDKRW", "title": "USD/KRW"}},
              {{"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"}},
              {{"proName": "TVC:GOLD", "title": "Gold"}}
            ],
            "showSymbolLogo": true,
            "colorTheme": "dark",
            "isTransparent": false,
            "displayMode": "adaptive",
            "locale": "{locale}"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=46)

    @staticmethod
    def render_advanced_chart(symbol: str = "NASDAQ:AAPL", height: int = 400, locale: str = "kr") -> None:
        """고급 차트"""
        html_code = f"""
        <div class="tradingview-widget-container" style="height:{height}px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "height": "{height}",
            "width": "100%",
            "symbol": "{symbol}",
            "interval": "D",
            "timezone": "Asia/Seoul",
            "theme": "dark",
            "style": "1",
            "locale": "{locale}",
            "enable_publishing": false,
            "hide_top_toolbar": false,
            "hide_legend": false,
            "save_image": false,
            "calendar": false,
            "hide_volume": false,
            "support_host": "https://www.tradingview.com"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)

    @staticmethod
    def render_technical_analysis(symbol: str = "NASDAQ:TSLA", height: int = 350, locale: str = "kr") -> None:
        """기술적 분석"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
          {{
            "interval": "1D",
            "width": "100%",
            "isTransparent": true,
            "height": {height},
            "symbol": "{symbol}",
            "showIntervalTabs": true,
            "displayMode": "single",
            "locale": "{locale}",
            "colorTheme": "dark"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)

    @staticmethod
    def render_commodity_mini_chart(symbol: str = "TVC:GOLD", height: int = 180, locale: str = "kr") -> None:
        """원자재/환율 미니 차트 (CFD 심볼 전용)"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
          {{
            "symbol": "{symbol}",
            "width": "100%",
            "height": {height},
            "locale": "{locale}",
            "dateRange": "1M",
            "colorTheme": "dark",
            "isTransparent": false,
            "autosize": false,
            "largeChartUrl": ""
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)

    @staticmethod
    def render_symbol_info(symbol: str = "NASDAQ:AAPL", height: int = 180, locale: str = "kr") -> None:
        """심볼 정보 + 미니 차트 (지수 지원)"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js" async>
          {{
            "symbol": "{symbol}",
            "width": "100%",
            "locale": "{locale}",
            "colorTheme": "dark",
            "isTransparent": false
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)

    @staticmethod
    def render_single_ticker(symbol: str = "NASDAQ:AAPL", locale: str = "kr") -> None:
        """단일 티커 (가격/변동률 표시)"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
          {{
            "symbol": "{symbol}",
            "width": "100%",
            "colorTheme": "dark",
            "isTransparent": false,
            "locale": "{locale}"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=60)

    @staticmethod
    def render_economic_calendar(height: int = 400, locale: str = "kr") -> None:
        """경제 캘린더"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {{
            "colorTheme": "dark",
            "isTransparent": false,
            "width": "100%",
            "height": {height},
            "locale": "{locale}",
            "importanceFilter": "-1,0,1",
            "countryFilter": "us,kr,cn,jp"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)

    @staticmethod
    def render_timeline(height: int = 350, locale: str = "kr") -> None:
        """시장 뉴스"""
        html_code = f"""
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
          {{
            "feedMode": "all_symbols",
            "colorTheme": "dark",
            "isTransparent": false,
            "displayMode": "regular",
            "width": "100%",
            "height": {height},
            "locale": "{locale}"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=height)
