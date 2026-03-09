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
            "displayMode": "compact",
            "locale": "{locale}"
          }}
          </script>
        </div>
        """
        components.html(html_code, height=76)

    @staticmethod
    def render_advanced_chart(symbol: str = "NASDAQ:AAPL", height: int = 400, locale: str = "kr", minimal: bool = False) -> None:
        """고급 차트 (minimal=True 시 미니 차트처럼 연출)"""
        hide_ui = "true" if minimal else "false"
        
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
            "hide_top_toolbar": {hide_ui},
            "hide_legend": false,
            "save_image": false,
            "calendar": false,
            "hide_volume": true,
            "hide_side_toolbar": {hide_ui},
            "allow_symbol_change": {"false" if minimal else "true"},
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

    @staticmethod
    def render_lightweight_chart(data: list, title: str, height: int = 300) -> None:
        """
        Custom Data를 사용해 TradingView Lightweight Charts 렌더링
        Args:
            data: [{'time': 'YYYY-MM-DD', 'open': 10, ...}] (Candlestick)
                  또는 [{'time': 'YYYY-MM-DD', 'value': 10}] (Area)
            title: 차트 제목
            height: 높이
        """
        import uuid
        import json
        
        if not data:
            components.html(f"<div style='color:#6b7280; font-family:sans-serif; padding:20px; background:#131722; height:{height}px;'>No Data for {title}</div>", height=height)
            return

        is_candle = 'open' in data[0]
        series_type = 'addCandlestickSeries' if is_candle else 'addAreaSeries'
        chart_id = f"chart_{uuid.uuid4().hex}"
        
        # Color & Series Config
        layout_cfg = {"background": {"type": "solid", "color": "#131722"}, "textColor": "#d1d4dc"}
        grid_cfg = {"vertLines": {"color": "rgba(42, 46, 57, 0.1)"}, "horzLines": {"color": "rgba(42, 46, 57, 0.1)"}}
        
        if is_candle:
            series_cfg = {"upColor": "#26a69a", "downColor": "#ef5350", "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"}
        else:
            series_cfg = {"topColor": "rgba(41, 98, 255, 0.5)", "bottomColor": "rgba(41, 98, 255, 0.0)", "lineColor": "#2962ff", "lineWidth": 2}

        # Data JSON
        data_json = json.dumps(data)

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ margin: 0; padding: 0; background-color: #131722; overflow: hidden; }}
                #{chart_id} {{ width: 100%; height: {height}px; position: relative; }}
                .watermark {{
                    position: absolute; top: 8px; left: 8px; font-size: 16px;
                    color: rgba(255, 255, 255, 0.1); font-family: sans-serif;
                    z-index: 5; pointer-events: none; font-weight: bold;
                }}
            </style>
            <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
        </head>
        <body>
            <div id="{chart_id}"><div class="watermark">{title}</div></div>
            <script>
            (function() {{
                const container = document.getElementById('{chart_id}');
                const chartData = {data_json};
                
                function init() {{
                    if (typeof LightweightCharts === 'undefined') {{
                        setTimeout(init, 50);
                        return;
                    }}
                    
                    try {{
                        const chart = LightweightCharts.createChart(container, {{
                            width: container.clientWidth || 300,
                            height: {height},
                            layout: {json.dumps(layout_cfg)},
                            grid: {json.dumps(grid_cfg)},
                            timeScale: {{ borderColor: "rgba(197, 203, 206, 0.5)" }},
                            rightPriceScale: {{ borderColor: "rgba(197, 203, 206, 0.5)" }}
                        }});

                        const series = chart.{series_type}({json.dumps(series_cfg)});
                        series.setData(chartData);
                        chart.timeScale().fitContent();

                        // Dynamic Resize
                        const ro = new ResizeObserver(entries => {{
                            for (let entry of entries) {{
                                if (entry.contentRect.width > 0) {{
                                    chart.applyOptions({{ width: entry.contentRect.width }});
                                    chart.timeScale().fitContent();
                                }}
                            }}
                        }});
                        ro.observe(container);
                    }} catch (e) {{
                        container.innerHTML = `<div style="color:#ef5350;padding:10px;font-family:sans-serif;">Error: ${{e.message}}</div>`;
                    }}
                }}
                
                if (document.readyState === 'complete') init();
                else window.addEventListener('load', init);
            }})();
            </script>
        </body>
        </html>
        """
        components.html(html_code, height=height)
