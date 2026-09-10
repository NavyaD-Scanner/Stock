import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 
# -------------------------------------------------------------
# Configuration & Layout
# -------------------------------------------------------------
st.set_page_config(
    page_title="Institutional Equity Terminal & Live Patterns",
    page_icon="📈",
    layout="wide"
)
 
DEFAULT_WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
SUGGESTIONS = {
    "PFC (Power Finance Corp)": "PFC.NS",
    "BEL (Bharat Electronics)": "BEL.NS",
    "Trent Ltd": "TRENT.NS",
    "Coal India": "COALINDIA.NS",
    "RVNL (Rail Vikas)": "RVNL.NS",
    "BHEL": "BHEL.NS",
    "Tata Power": "TATAPOWER.NS"
}
 
# -------------------------------------------------------------
# Session State
# -------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 1
 
if "ticker_registry" not in st.session_state:
    reg = dict(DEFAULT_WATCHLIST)
    reg.update(SUGGESTIONS)
    st.session_state.ticker_registry = reg
 
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = list(DEFAULT_WATCHLIST.keys())
 
if "active_stock" not in st.session_state:
    st.session_state.active_stock = "REC Ltd"
 
def navigate_to(page_num):
    st.session_state.page = page_num
 
def inspect_stock(name):
    st.session_state.active_stock = name
    st.session_state.page = 3
 
# -------------------------------------------------------------
# Quantitative Indicators & Pattern Recognition
# -------------------------------------------------------------
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))
 
def calculate_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
 
def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['Pattern'] = ""
    o, h, l, c = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(c - o)
 
    for i in range(1, len(df)):
        if (min(o.iloc[i], c.iloc[i]) - l.iloc[i]) > 2 * body.iloc[i] and (h.iloc[i] - max(o.iloc[i], c.iloc[i])) < 0.2 * body.iloc[i]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🔨 Bullish Hammer"
        elif (h.iloc[i] - max(o.iloc[i], c.iloc[i])) > 2 * body.iloc[i] and (min(o.iloc[i], c.iloc[i]) - l.iloc[i]) < 0.2 * body.iloc[i]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "⭐ Shooting Star"
        elif c.iloc[i-1] < o.iloc[i-1] and c.iloc[i] > o.iloc[i] and c.iloc[i] >= o.iloc[i-1] and o.iloc[i] <= c.iloc[i-1]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🟢 Bullish Engulfing"
        elif c.iloc[i-1] > o.iloc[i-1] and c.iloc[i] < o.iloc[i] and o.iloc[i] >= c.iloc[i-1] and c.iloc[i] <= o.iloc[i-1]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🔴 Bearish Engulfing"
 
    return df
 
@st.cache_data(ttl=600)
def fetch_stock_data(ticker_symbol: str):
    clean_ticker = ticker_symbol.strip().upper()
    if not clean_ticker.endswith(".NS") and not clean_ticker.endswith(".BO"):
        clean_ticker += ".NS"
        
    stock = yf.Ticker(clean_ticker)
    try:
        df = stock.history(period="1y", interval="1d")
    except Exception:
        return None, dict()
    
    if df is None or df.empty or len(df) < 20:
        return None, dict()
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['BB_Mid'] = df['SMA_20']
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
    df['RSI'] = calculate_rsi(df['Close'])
    macd, signal, hist = calculate_macd(df['Close'])
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['MACD_Hist'] = hist
    df = detect_candlestick_patterns(df)
 
    try:
        info_data = stock.info
        if not isinstance(info_data, dict):
            info_data = dict()
    except Exception:
        info_data = dict()
        
    return df, info_data
 
# -------------------------------------------------------------
# Sidebar Navigation
# -------------------------------------------------------------
st.sidebar.title("Navigation & Risk")
 
app_mode = st.sidebar.radio(
    "Go to Step:",
    ["1. Stock Selector & Add", "2. Comparison Screener", "3. Deep-Dive & Live Chart"],
    index=st.session_state.page - 1
)
 
if app_mode.startswith("1") and st.session_state.page != 1:
    navigate_to(1)
    st.rerun()
elif app_mode.startswith("2") and st.session_state.page != 2:
    navigate_to(2)
    st.rerun()
elif app_mode.startswith("3") and st.session_state.page != 3:
    navigate_to(3)
    st.rerun()
 
st.sidebar.divider()
portfolio_size = st.sidebar.number_input("Portfolio Equity (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Max Account Risk / Trade (%)", 0.25, 3.0, 1.0, 0.05)
 
st.sidebar.divider()
available_stocks = [s for s in st.session_state.selected_stocks if s in st.session_state.ticker_registry]
if not available_stocks:
    available_stocks = list(DEFAULT_WATCHLIST.keys())
 
current_idx = available_stocks.index(st.session_state.active_stock) if st.session_state.active_stock in available_stocks else 0
selected_quick = st.sidebar.selectbox("Active Stock (Page 3):", available_stocks, index=current_idx)
 
if selected_quick != st.session_state.active_stock:
    st.session_state.active_stock = selected_quick
    if st.session_state.page == 3:
        st.rerun()
 
# =============================================================
# PAGE 1: Stock Selection & Suggestion Addition
# =============================================================
if st.session_state.page == 1:
    st.title("🎯 Step 1: Build Your Watchlist")
    st.write("Select preset stocks, add our suggested market picks, or type any custom NSE equity.")
 
    col1, col2 = st.columns([1.2, 1])
 
    with col1:
        st.subheader("Default Watchlist Selection")
        selected_presets = st.multiselect(
            "Select tickers to evaluate:",
            options=list(DEFAULT_WATCHLIST.keys()),
            default=[s for s in st.session_state.selected_stocks if s in DEFAULT_WATCHLIST]
        )
 
        st.subheader("Manual Custom Addition")
        custom_input = st.text_input("Enter NSE Symbols (comma separated, e.g. TRENT, BEL, COALINDIA):", "")
 
    with col2:
        st.subheader("💡 Smart Suggestions (High-Probability Catalysts)")
        st.caption("Select stocks to automatically include in the comparison table and deep-dive analysis:")
        picked_suggestions = []
        for name, ticker_code in SUGGESTIONS.items():
            is_checked = name in st.session_state.selected_stocks
            if st.checkbox(name + " (" + ticker_code + ")", value=is_checked, key="chk_" + ticker_code):
                picked_suggestions.append(name)
 
    st.write("")
    if st.button("🚀 Analyze & Generate Overview Table", type="primary", use_container_width=True):
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
        
        for c in custom_tickers:
            st.session_state.ticker_registry[c] = c + ".NS"
 
        final_list = list(selected_presets)
        for s in picked_suggestions:
            if s not in final_list:
                final_list.append(s)
        for c in custom_tickers:
            if c not in final_list:
                final_list.append(c)
 
        if not final_list:
            st.error("Please select at least one stock to proceed.")
        else:
            st.session_state.selected_stocks = final_list
            if st.session_state.active_stock not in final_list:
                st.session_state.active_stock = final_list[0]
            navigate_to(2)
            st.rerun()
 
# =============================================================
# PAGE 2: Comparison Dashboard
# =============================================================
elif st.session_state.page == 2:
    st.title("📊 Step 2: Multi-Asset Comparative Screener")
    
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("⬅️ Back to Stock Selection"):
            navigate_to(1)
            st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching market metrics and computing technical patterns..."):
        for item in st.session_state.selected_stocks:
            ticker = st.session_state.ticker_registry.get(item, item if item.endswith(".NS") else item + ".NS")
            df, info = fetch_stock_data(ticker)
            
            if df is not None and not df.empty:
                cmp_price = round(float(df['Close'].iloc[-1]), 2)
                low_52w = round(float(df['Low'].min()), 2)
                high_52w = round(float(df['High'].max()), 2)
                rsi_val = round(float(df['RSI'].iloc[-1]), 2) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
                
                pe_raw = info.get('trailingPE', np.nan)
                pe = round(float(pe_raw), 2) if pd.notna(pe_raw) else np.nan
                
                dy_raw = info.get('dividendYield', 0)
                div_yield = round(float(dy_raw) * 100, 2) if dy_raw else 0.0
                dist_to_low = round(((cmp_price - low_52w) / (low_52w + 1e-5)) * 100, 2)
                
                recent_patterns = [p for p in df['Pattern'].iloc[-3:].tolist() if p]
                pattern_tag = recent_patterns[-1] if recent_patterns else "Consolidation"
 
                score = 0
                if pd.notna(pe) and pe < 15: score += 2
                if div_yield > 3.0: score += 2
                if dist_to_low < 8.0: score += 3
                if rsi_val < 40: score += 2
                if "Bullish" in pattern_tag: score += 1
                
                rows.append({
                    "Stock": item,
                    "CMP (₹)": cmp_price,
                    "52W High (₹)": high_52w,
                    "52W Low (₹)": low_52w,
                    "Dist to 52W Low (%)": dist_to_low,
                    "P/E Ratio": pe if pd.notna(pe) else "N/A",
                    "Div Yield (%)": str(div_yield) + "%",
                    "RSI (14)": rsi_val,
                    "Recent Pattern": pattern_tag,
                    "Score": score
                })
            else:
                failed.append(item)
 
    # Safe Guard: Ensure rows is not empty before building summary_df
    if len(rows) > 0:
        summary_df = pd.DataFrame(rows).sort_valu
 
    # Safe Guard: Ensure rows is not empty before building summary_df
    if len(rows) > 0:
        summary_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
        st.subheader("Asset Comparison Matrix (Hover column headers for info)")
        
        st.dataframe(
            summary_df,
            use_container_width=True,
            column_config={
                "Stock": st.column_config.TextColumn("Stock", help="Name or ticker symbol of the equity."),
                "CMP (₹)": st.column_config.NumberColumn("CMP (₹)", help="Current Market Price based on the latest NSE close."),
                "52W High (₹)": st.column_config.NumberColumn("52W High (₹)", help="Highest traded price over 52 weeks (major structural resistance)."),
                "52W Low (₹)": st.column_config.NumberColumn("52W Low (₹)", help="Lowest traded price over 52 weeks (key structural floor)."),
                "Dist to 52W Low (%)": st.column_config.NumberColumn("Dist to 52W Low (%)", help="Percentage distance above 52-week low. Lower values offer favorable risk-defined entries."),
                "P/E Ratio": st.column_config.TextColumn("P/E Ratio", help="Trailing Twelve Month Price-to-Earnings ratio."),
                "Div Yield (%)": st.column_config.TextColumn("Div Yield (%)", help="Annualized dividend yield percentage."),
                "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="Relative Strength Index. <35 indicates oversold rebound potential; >70 is overbought."),
                "Recent Pattern": st.column_config.TextColumn("Recent Pattern", help="Candlestick pattern identified in recent trading sessions."),
                "Score": st.column_config.ProgressColumn("Score", help="Asymmetry Score (0 to 10) evaluating valuation, support base defense, and oversold indicators.", min_value=0, max_value=10)
            }
        )
 
        st.subheader("🔍 Select Stock for Live Chart & Technical Breakdown:")
        n_cols = min(len(summary_df), 4)
        btn_cols = st.columns(n_cols if n_cols > 0 else 1)
        for index, row in summary_df.reset_index().iterrows():
            col_idx = index % (n_cols if n_cols > 0 else 1)
            with btn_cols[col_idx]:
                btn_name = row['Stock']
                if st.button(btn_name + " (Score: " + str(row['Score']) + ")", key="btn_" + str(btn_name), use_container_width=True):
                    inspect_stock(btn_name)
                    st.rerun()
    else:
        st.error("No valid stock data could be retrieved. Please go back to Step 1 and select valid NSE tickers.")
 
    if failed:
        st.warning("Could not fetch data for: " + ", ".join(failed) + ". Verify that these tickers trade on NSE.")
 
# =============================================================
# PAGE 3: Live Chart & Pattern Visualizer
# =============================================================
elif st.session_state.page == 3:
    stock_name = st.session_state.active_stock
    ticker = st.session_state.ticker_registry.get(stock_name, stock_name if stock_name.endswith(".NS") else stock_name + ".NS")
    symbol_tv = ticker.replace(".NS", "").replace(".BO", "")
    
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Back to Table"):
            navigate_to(2)
            st.rerun()
    with col_title:
        st.title("Analysis & Pattern Chart: " + stock_name + " (NSE: " + symbol_tv + ")")
 
    df, info = fetch_stock_data(ticker)
 
    if df is not None and not df.empty:
        cmp_price = round(float(df['Close'].iloc[-1]), 2)
        low_52w = round(float(df['Low'].min()), 2)
        high_52w = round(float(df['High'].max()), 2)
        rsi_val = round(float(df['RSI'].iloc[-1]), 2) if not pd.isna(df['RSI'].iloc[-1]) else 50.0
        macd_val = round(float(df['MACD'].iloc[-1]), 2) if not pd.isna(df['MACD'].iloc[-1]) else 0.0
        macd_sig = round(float(df['MACD_Signal'].iloc[-1]), 2) if not pd.isna(df['MACD_Signal'].iloc[-1]) else 0.0
        
        sma_20 = round(float(df['SMA_20'].iloc[-1]), 2) if not pd.isna(df['SMA_20'].iloc[-1]) else cmp_price
        sma_50 = round(float(df['SMA_50'].iloc[-1]), 2) if not pd.isna(df['SMA_50'].iloc[-1]) else round(cmp_price * 1.05, 2)
        sma_200 = round(float(df['SMA_200'].iloc[-1]), 2) if not pd.isna(df['SMA_200'].iloc[-1]) else round(cmp_price * 1.10, 2)
 
        sl = round(low_52w * 0.99, 2)
        risk_per_share = round(cmp_price - sl, 2)
        if risk_per_share <= 0:
            risk_per_share = round(cmp_price * 0.03, 2)
            sl = round(cmp_price - risk_per_share, 2)
 
        max_risk_inr = portfolio_size * (risk_per_trade_pct / 100)
        position_qty = int(max_risk_inr / risk_per_share) if risk_per_share > 0 else 0
        capital_outlay = round(position_qty * cmp_price, 2)
        
        t1 = sma_50
        t2 = sma_200
        t3 = round(cmp_price + (risk_per_share * 3.0), 2)
        rr_ratio = round((t2 - cmp_price) / (risk_per_share + 1e-5), 2)
 
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CMP", "₹" + str(cmp_price))
        m2.metric("Protective SL", "₹" + str(sl), "-₹" + str(risk_per_share))
        m3.metric("Target 1 (50 DMA)", "₹" + str(t1), "+" + str(round(((t1 - cmp_price)/cmp_price)*100, 1)) + "%")
        m4.metric("Recommended Qty", str(position_qty) + " Shares", "Risk: ₹" + str(int(max_risk_inr)))
 
        chart_choice = st.radio(
            "Select Chart View:",
            ["Interactive Pattern & Technical Chart (Moving Averages + Bollinger Bands + RSI + MACD)", "TradingView Live Widget"],
            horizontal=True
        )
 
        if chart_choice.startswith("Interactive"):
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f"{stock_name} Daily Candlesticks, Patterns & Overlays", "Volume", "RSI (14) & MACD"),
                row_heights=[0.6, 0.2, 0.2]
            )
 
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name="Price"
            ), row=1, col=1)
 
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20 DMA', line=dict(color='yellow', width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='50 DMA', line=dict(color='cyan', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], mode='lines', name='200 DMA', line=dict(color='magenta', width=1.8)), row=1, col=1)
 
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], mode='lines', name='Upper BB (2σ)', line=dict(color='rgba(255,255,255,0.3)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], mode='lines', name='Lower BB (2σ)', line=dict(color='rgba(255,255,255,0.3)', dash='dot')), row=1, col=1)
 
            pattern_points = df[df['Pattern'] != ""]
            if not pattern_points.empty:
                fig.add_trace(go.Scatter(
                    x=pattern_points.index,
                    y=pattern_points['High'] * 1.015,
                    mode='text+markers',
                    name='Detected Pattern',
                    text=pattern_points['Pattern'],
                    textposition='top center',
                    marker=dict(symbol='triangle-down', size=11, color='#FFA500')
                ), row=1, col=1)
 
            fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="SL Floor", row=1, col=1)
            fig.add_hline(y=t1, line_dash="dot", line_color="green", annotation_text="Target 1", row=1, col=1)
 
            vol_colors = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name="Volume"), row=2, col=1)
 
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00FFCC')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
 
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=720,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
 
        else:
            st.caption("Live streaming chart via TradingView Official Web Component:")
            tradingview_code = f"""
            <div style="height:600px;width:100%;">
                <div class="tradingview-widget-container" style="height:100%;width:100%">
                  <iframe 
                    src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=NSE%3A{symbol_tv}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%22RSI%40tv-basicstudies%22%2C%22MASimple%40tv-basicstudies%22%5D&theme=dark&style=1&timezone=Asia%2FKolkata&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en&utm_source=localhost"
                    style="width: 100%; height: 100%; border: none;"
                    allowtransparency="true" 
                    scrolling="no" 
                    allowfullscreen>
                  </iframe>
                </div>
            </div>
            """
            components.html(tradingview_code, height=620)
            st.info(f"If the embedded TradingView iframe is blocked by your browser extensions, view directly on [TradingView: NSE:{symbol_tv}](https://in.tradingview.com/chart/?symbol=NSE:{symbol_tv}) or [Chartink Screener](https://chartink.com/stocks/{symbol_tv.lower()}.html).")
 
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Execution Plan", 
            "📈 Pattern & Technical Analysis", 
            "📊 Fundamental Metrics", 
            "⚠️ Invalidation Rules"
        ])
 
        with tab1:
            st.markdown("### Actionable Trade Setup")
            st.write(f"* **Entry Range:** ₹{round(cmp_price * 0.99, 2)} – ₹{cmp_price}")
            st.write(f"* **Protective Stop-Loss:** ₹{sl} *(1% below 52-week support of ₹{low_52w})*")
            st.write(f"* **Target 1 (50 DMA Retest):** ₹{t1} *(Book 40%)*")
            st.write(f"* **Target 2 (200 DMA Mean Reversion):** ₹{t2} *(Book 35%)*")
            st.write(f"* **Target 3 (Swing High):** ₹{t3} *(Book 25%)*")
            st.write(f"* **Calculated Risk-to-Reward:** 1 : {rr_ratio}")
            st.write(f"* **Allocated Capital Outlay:** ₹{capital_outlay:,.2f}")
 
        with tab2:
            st.markdown("### Automated Technical & Pattern Diagnostics")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"* **14-Day RSI:** `{rsi_val}` ({'Oversold Rebound' if rsi_val < 35 else 'Neutral' if rsi_val <= 60 else 'Overbought'})")
                st.write(f"* **MACD Status:** `{'Bullish Crossover' if macd_val > macd_sig else 'Bearish Pressure'}` (Line: {macd_val} | Signal: {macd_sig})")
                bb_squeeze = (df['BB_Upper'].iloc[-1] - df['BB_Lower'].iloc[-1]) / cmp_price < 0.10
                st.write(f"* **Bollinger Band Squeeze:** `{'Volatility Tightening' if bb_squeeze else 'Normal Expansion'}`")
            with c2:
                st.write(f"* **20 DMA (Short-term Mean):** ₹{sma_20} ({'Above' if cmp_price > sma_20 else 'Below'})")
                st.write(f"* **50 DMA (Medium-term Pivot):** ₹{sma_50} ({'Above' if cmp_price > sma_50 else 'Below'})")
                st.write(f"* **200 DMA (Long-term Trend):** ₹{sma_200} ({'Bullish Macro' if cmp_price > sma_200 else 'Corrective Macro'})")
 
        with tab3:
            st.markdown("### Fundamental Health & Valuation")
            pe_val = info.get('trailingPE', 'N/A')
            pb_val = info.get('priceToBook', 'N/A')
            dy = round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0.0
            roe = round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 'N/A'
            pm = round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 'N/A'
            de = round(info.get('debtToEquity', 0), 2) if info.get('debtToEquity') else 'N/A'
            mcap = f"₹{round(info.get('marketCap', 0) / 1e7, 2):,.2f} Cr" if info.get('marketCap') else "N/A"
            
            f1, f2 = st.columns(2)
            with f1:
                st.write(f"* **Market Cap:** {mcap}")
                st.write(f"* **Trailing P/E:** {pe_val}")
                st.write(f"* **Price-to-Book (P/B):** {pb_val}")
                st.write(f"* **Dividend Yield:** {dy}%")
            with f2:
                st.write(f"* **Return on Equity (ROE):** {roe}%" if roe != 'N/A' else "* **ROE:** N/A")
                st.write(f"* **Net Profit Margin:** {pm}%" if pm != 'N/A' else "* **Net Profit Margin:** N/A")
                st.write(f"* **Debt to Equity:** {de}")
 
            st.write("**Company Overview:**")
            summary = info.get('longBusinessSummary', 'No description available for this ticker.')
            st.write(summary[:650] + "...")
 
        with tab4:
            st.error(f"**Trade Invalidation:** A daily close below ₹{sl} decisively breaks support. Close open positions immediately to preserve capital.")
    else:
        st.error("Unable to load data for this symbol. Check that the ticker exists on NSE.")
 import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
 
# -------------------------------------------------------------
# Configuration & Layout
# -------------------------------------------------------------
st.set_page_config(
    page_title="Institutional Equity Terminal & Live Patterns",
    page_icon="📈",
    layout="wide"
)
 
DEFAULT_WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
SUGGESTIONS = {
    "PFC (Power Finance Corp)": "PFC.NS",
    "BEL (Bharat Electronics)": "BEL.NS",
    "Trent Ltd": "TRENT.NS",
    "Coal India": "COALINDIA.NS",
    "RVNL (Rail Vikas)": "RVNL.NS",
    "BHEL": "BHEL.NS",
    "Tata Power": "TATAPOWER.NS"
}
 
# -------------------------------------------------------------
# Session State
# -------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 1
 
if "ticker_registry" not in st.session_state:
    reg = dict(DEFAULT_WATCHLIST)
    reg.update(SUGGESTIONS)
    st.session_state.ticker_registry = reg
 
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = list(DEFAULT_WATCHLIST.keys())
 
if "active_stock" not in st.session_state:
    st.session_state.active_stock = "REC Ltd"
 
def navigate_to(page_num):
    st.session_state.page = page_num
 
def inspect_stock(name):
    st.session_state.active_stock = name
    st.session_state.page = 3
 
# -------------------------------------------------------------
# Quantitative Indicators & Pattern Recognition
# -------------------------------------------------------------
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))
 
def calculate_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
 
def detect_candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Detects classic candlestick reversal and continuation patterns."""
    df = df.copy()
    df['Pattern'] = ""
    
    o, h, l, c = df['Open'], df['High'], df['Low'], df['Close']
    body = abs(c - o)
    candle_range = h - l + 1e-5
 
    for i in range(1, len(df)):
        # Bullish Hammer: Small body at high, long lower shadow (>= 2x body)
        if (min(o.iloc[i], c.iloc[i]) - l.iloc[i]) > 2 * body.iloc[i] and (h.iloc[i] - max(o.iloc[i], c.iloc[i])) < 0.2 * body.iloc[i]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🔨 Bullish Hammer"
 
        # Shooting Star: Small body at low, long upper shadow (>= 2x body)
        elif (h.iloc[i] - max(o.iloc[i], c.iloc[i])) > 2 * body.iloc[i] and (min(o.iloc[i], c.iloc[i]) - l.iloc[i]) < 0.2 * body.iloc[i]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "⭐ Shooting Star"
 
        # Bullish Engulfing: Current green candle completely covers previous red candle body
        elif c.iloc[i-1] < o.iloc[i-1] and c.iloc[i] > o.iloc[i] and c.iloc[i] >= o.iloc[i-1] and o.iloc[i] <= c.iloc[i-1]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🟢 Bullish Engulfing"
 
        # Bearish Engulfing: Current red candle completely covers previous green candle body
        elif c.iloc[i-1] > o.iloc[i-1] and c.iloc[i] < o.iloc[i] and o.iloc[i] >= c.iloc[i-1] and c.iloc[i] <= o.iloc[i-1]:
            df.iloc[i, df.columns.get_loc('Pattern')] = "🔴 Bearish Engulfing"
 
    return df
 
@st.cache_data(ttl=600)
def fetch_stock_data(ticker_symbol: str):
    clean_ticker = ticker_symbol.strip().upper()
    if not clean_ticker.endswith(".NS") and not clean_ticker.endswith(".BO"):
        clean_ticker += ".NS"
        
    stock = yf.Ticker(clean_ticker)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 25:
        return None, dict()
    
    # Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
 
    # Bollinger Bands
    df['BB_Mid'] = df['SMA_20']
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])
 
    # Oscillators
    df['RSI'] = calculate_rsi(df['Close'])
    macd, signal, hist = calculate_macd(df['Close'])
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['MACD_Hist'] = hist
 
    # Candlestick Patterns
    df = detect_candlestick_patterns(df)
 
    try:
        info_data = stock.info
        if not isinstance(info_data, dict):
            info_data = dict()
    except Exception:
        info_data = dict()
        
    return df, info_data
 
# -------------------------------------------------------------
# Sidebar Navigation
# -------------------------------------------------------------
st.sidebar.title("Navigation & Risk")
 
app_mode = st.sidebar.radio(
    "Go to Step:",
    ["1. Stock Selector & Add", "2. Comparison Screener", "3. Deep-Dive & Live Chart"],
    index=st.session_state.page - 1
)
 
if app_mode.startswith("1") and st.session_state.page != 1:
    navigate_to(1)
    st.rerun()
elif app_mode.startswith("2") and st.session_state.page != 2:
    navigate_to(2)
    st.rerun()
elif app_mode.startswith("3") and st.session_state.page != 3:
    navigate_to(3)
    st.rerun()
 
st.sidebar.divider()
portfolio_size = st.sidebar.number_input("Portfolio Equity (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Max Account Risk / Trade (%)", 0.25, 3.0, 1.0, 0.05)
 
st.sidebar.divider()
available_stocks = [s for s in st.session_state.selected_stocks if s in st.session_state.ticker_registry]
if not available_stocks:
    available_stocks = list(DEFAULT_WATCHLIST.keys())
 
current_idx = available_stocks.index(st.session_state.active_stock) if st.session_state.active_stock in available_stocks else 0
selected_quick = st.sidebar.selectbox("Active Stock (Page 3):", available_stocks, index=current_idx)
 
if selected_quick != st.session_state.active_stock:
    st.session_state.active_stock = selected_quick
    if st.session_state.page == 3:
        st.rerun()
 
# =============================================================
# PAGE 1: Stock Selection & Suggestion Addition
# =============================================================
if st.session_state.page == 1:
    st.title("🎯 Step 1: Build Your Watchlist")
    st.write("Select preset stocks, add our suggested market picks, or type any custom NSE equity.")
 
    col1, col2 = st.columns([1.2, 1])
 
    with col1:
        st.subheader("Default Watchlist Selection")
        selected_presets = st.multiselect(
            "Select tickers to evaluate:",
            options=list(DEFAULT_WATCHLIST.keys()),
            default=[s for s in st.session_state.selected_stocks if s in DEFAULT_WATCHLIST]
        )
 
        st.subheader("Manual Custom Addition")
        custom_input = st.text_input("Enter NSE Symbols (comma separated, e.g. TRENT, BEL, COALINDIA):", "")
 
    with col2:
        st.subheader("💡 Smart Suggestions (High-Probability Catalysts)")
        st.caption("Select stocks to automatically include in the comparison table and deep-dive analysis:")
        picked_suggestions = []
        for name, ticker_code in SUGGESTIONS.items():
            is_checked = name in st.session_state.selected_stocks
            if st.checkbox(name + " (" + ticker_code + ")", value=is_checked, key="chk_" + ticker_code):
                picked_suggestions.append(name)
 
    st.write("")
    if st.button("🚀 Analyze & Generate Overview Table", type="primary", use_container_width=True):
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
        
        for c in custom_tickers:
            st.session_state.ticker_registry[c] = c + ".NS"
 
        final_list = list(selected_presets)
        for s in picked_suggestions:
            if s not in final_list:
                final_list.append(s)
        for c in custom_tickers:
            if c not in final_list:
                final_list.append(c)
 
        if not final_list:
            st.error("Please select at least one stock to proceed.")
        else:
            st.session_state.selected_stocks = final_list
            if st.session_state.active_stock not in final_list:
                st.session_state.active_stock = final_list[0]
            navigate_to(2)
            st.rerun()
 
# =============================================================
# PAGE 2: Comparison Dashboard with Tooltips
# =============================================================
elif st.session_state.page == 2:
    st.title("📊 Step 2: Multi-Asset Comparative Screener")
    
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("⬅️ Back to Stock Selection"):
            navigate_to(1)
            st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching live metrics and computing patterns..."):
        for item in st.session_state.selected_stocks:
            ticker = st.session_state.ticker_registry.get(item, item if item.endswith(".NS") else item + ".NS")
            df, info = fetch_stock_data(ticker)
            
            if df is not None:
                cmp_price = round(float(df['Close'].iloc[-1]), 2)
                low_52w = round(float(df['Low'].min()), 2)
                high_52w = round(float(df['High'].max()), 2)
                rsi_val = round(float(df['RSI'].iloc[-1]), 2)
                
                pe_raw = info.get('trailingPE', np.nan)
                pe = round(float(pe_raw), 2) if pd.notna(pe_raw) else np.nan
                
                dy_raw = info.get('dividendYield', 0)
                div_yield = round(float(dy_raw) * 100, 2) if dy_raw else 0.0
                dist_to_low = round(((cmp_price - low_52w) / (low_52w + 1e-5)) * 100, 2)
                
                # Check for recent pattern in last 3 trading bars
                recent_patterns = [p for p in df['Pattern'].iloc[-3:].tolist() if p]
                pattern_tag = recent_patterns[-1] if recent_patterns else "Consolidation"
 
                score = 0
                if pd.notna(pe) and pe < 15: score += 2
                if div_yield > 3.0: score += 2
                if dist_to_low < 8.0: score += 3
                if rsi_val < 40: score += 2
                if "Bullish" in pattern_tag: score += 1
                
                rows.append({
                    "Stock": item,
                    "CMP (₹)": cmp_price,
                    "52W High (₹)": high_52w,
                    "52W Low (₹)": low_52w,
                    "Dist to 52W Low (%)": st.column_config.NumberColumn("Dist to 52W Low (%)", help="Percentage distance above 52-week low. Lower values offer high-probability support entries."),
                    "P/E Ratio": st.column_config.TextColumn("P/E Ratio", help="Trailing Twelve Month Price-to-Earnings ratio. Lower indicates attractive value."),
                    "Div Yield (%)": st.column_config.TextColumn("Div Yield (%)", help="Annualized dividend yield percentage."),
                    "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="Relative Strength Index. <35 indicates oversold rebound potential; >70 is overbought."),
                    "Recent Pattern": st.column_config.TextColumn("Recent Pattern", help="Candlestick pattern identified in recent trading sessions (Engulfing, Hammer, Shooting Star)."),
                    "Score": st.column_config.ProgressColumn("Score", help="Asymmetric trade setup score (0 to 10) combining valuation, support proximity, and oversold indicators.", min_value=0, max_value=10)
            }
        )
 
        st.subheader("🔍 Select Stock for Live Chart & Technical Breakdown:")
        n_cols = min(len(summary_df), 4)
        btn_cols = st.columns(n_cols if n_cols > 0 else 1)
        for index, row in summary_df.reset_index().iterrows():
            col_idx = index % (n_cols if n_cols > 0 else 1)
            with btn_cols[col_idx]:
                btn_name = row['Stock']
                if st.button(btn_name + " (Score: " + str(row['Score']) + ")", key="btn_" + str(btn_name), use_container_width=True):
                    inspect_stock(btn_name)
                    st.rerun()
 
    if failed:
        st.warning("Could not load data for: " + ", ".join(failed))
 
# =============================================================
# PAGE 3: Live Chart & Pattern Visualizer
# =============================================================
elif st.session_state.page == 3:
    stock_name = st.session_state.active_stock
    ticker = st.session_state.ticker_registry.get(stock_name, stock_name if stock_name.endswith(".NS") else stock_name + ".NS")
    symbol_tv = ticker.replace(".NS", "").replace(".BO", "")
    
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Back to Table"):
            navigate_to(2)
            st.rerun()
    with col_title:
        st.title("Analysis & Pattern Chart: " + stock_name + " (NSE: " + symbol_tv + ")")
 
    df, info = fetch_stock_data(ticker)
 
    if df is not None:
        cmp_price = round(float(df['Close'].iloc[-1]), 2)
        low_52w = round(float(df['Low'].min()), 2)
        high_52w = round(float(df['High'].max()), 2)
        rsi_val = round(float(df['RSI'].iloc[-1]), 2)
        macd_val = round(float(df['MACD'].iloc[-1]), 2)
        macd_sig = round(float(df['MACD_Signal'].iloc[-1]), 2)
        
        sma_20 = round(float(df['SMA_20'].iloc[-1]), 2) if not pd.isna(df['SMA_20'].iloc[-1]) else cmp_price
        sma_50 = round(float(df['SMA_50'].iloc[-1]), 2) if not pd.isna(df['SMA_50'].iloc[-1]) else round(cmp_price * 1.05, 2)
        sma_200 = round(float(df['SMA_200'].iloc[-1]), 2) if not pd.isna(df['SMA_200'].iloc[-1]) else round(cmp_price * 1.10, 2)
 
        # Risk Management Engine
        sl = round(low_52w * 0.99, 2)
        risk_per_share = round(cmp_price - sl, 2)
        if risk_per_share <= 0:
            risk_per_share = round(cmp_price * 0.03, 2)
            sl = round(cmp_price - risk_per_share, 2)
 
        max_risk_inr = portfolio_size * (risk_per_trade_pct / 100)
        position_qty = int(max_risk_inr / risk_per_share) if risk_per_share > 0 else 0
        capital_outlay = round(position_qty * cmp_price, 2)
        
        t1 = sma_50
        t2 = sma_200
        t3 = round(cmp_price + (risk_per_share * 3.0), 2)
        rr_ratio = round((t2 - cmp_price) / (risk_per_share + 1e-5), 2)
 
        # Metrics display
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CMP", "₹" + str(cmp_price))
        m2.metric("Protective SL", "₹" + str(sl), "-₹" + str(risk_per_share))
        m3.metric("Target 1 (50 DMA)", "₹" + str(t1), "+" + str(round(((t1 - cmp_price)/cmp_price)*100, 1)) + "%")
        m4.metric("Recommended Qty", str(position_qty) + " Shares", "Risk: ₹" + str(int(max_risk_inr)))
 
        chart_choice = st.radio(
            "Select Chart View:",
            ["Interactive Pattern & Technical Chart (Moving Averages + Bollinger Bands + RSI + MACD)", "TradingView Live Widget"],
            horizontal=True
        )
 
        # OPTION 1: Interactive Multi-Panel Indicator & Pattern Chart
        if chart_choice.startswith("Interactive"):
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f"{stock_name} Daily Candlesticks, Patterns & Overlays", "Volume", "RSI (14) & MACD"),
                row_heights=[0.6, 0.2, 0.2]
            )
 
            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name="Candlestick"
            ), row=1, col=1)
 
            # Moving averages
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20 DMA', line=dict(color='yellow', width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='50 DMA', line=dict(color='cyan', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], mode='lines', name='200 DMA', line=dict(color='magenta', width=1.8)), row=1, col=1)
 
            # Bollinger Bands
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], mode='lines', name='Upper BB (2σ)', line=dict(color='rgba(255,255,255,0.3)', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], mode='lines', name='Lower BB (2σ)', line=dict(color='rgba(255,255,255,0.3)', dash='dot')), row=1, col=1)
 
            # Pattern Annotations (Markers on Chart)
            pattern_points = df[df['Pattern'] != ""]
            if not pattern_points.empty:
                fig.add_trace(go.Scatter(
                    x=pattern_points.index,
                    y=pattern_points['High'] * 1.015,
                    mode='text+markers',
                    name='Detected Pattern',
                    text=pattern_points['Pattern'],
                    textposition='top center',
                    marker=dict(symbol='triangle-down', size=11, color='#FFA500')
                ), row=1, col=1)
 
            # Horizontal SL and Target reference lines
            fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="SL Floor", row=1, col=1)
            fig.add_hline(y=t1, line_dash="dot", line_color="green", annotation_text="Target 1", row=1, col=1)
 
            # Volume
            vol_colors = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name="Volume"), row=2, col=1)
 
            # RSI & Overbought/Oversold
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI (14)', line=dict(color='#00FFCC')), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
 
            fig.update_layout(
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=720,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
 
        # OPTION 2: TradingView Official Embedded Widget
        else:
            st.caption("Live streaming chart via TradingView Official Web Component:")
            tradingview_code = f"""
            <div style="height:600px;width:100%;">
                <!-- TradingView Widget BEGIN -->
                <div class="tradingview-widget-container" style="height:100%;width:100%">
                  <iframe 
                    src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=NSE%3A{symbol_tv}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%22RSI%40tv-basicstudies%22%2C%22MASimple%40tv-basicstudies%22%5D&theme=dark&style=1&timezone=Asia%2FKolkata&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en&utm_source=localhost"
                    style="width: 100%; height: 100%; border: none;"
                    allowtransparency="true" 
                    scrolling="no" 
                    allowfullscreen>
                  </iframe>
                </div>
                <!-- TradingView Widget END -->
            </div>
            """
            components.html(tradingview_code, height=620)
            
            # External Quick-Links in case browser blocks iframe
            st.info(f"If the embedded TradingView iframe is blocked by your browser extensions, view directly on [TradingView: NSE:{symbol_tv}](https://in.tradingview.com/chart/?symbol=NSE:{symbol_tv}) or [Chartink Screener](https://chartink.com/stocks/{symbol_tv.lower()}.html).")
 
        # Tabs for full institutional breakdown
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Execution Plan", 
            "📈 Pattern & Technical Analysis", 
            "📊 Fundamental Metrics", 
            "⚠️ Invalidation Rules"
        ])
 
        with tab1:
            st.markdown("### Actionable Trade Setup")
            st.write(f"* **Entry Range:** ₹{round(cmp_price * 0.99, 2)} – ₹{cmp_price}")
            st.write(f"* **Protective Stop-Loss:** ₹{sl} *(1% below 52-week support of ₹{low_52w})*")
            st.write(f"* **Target 1 (50 DMA Retest):** ₹{t1} *(Book 40%)*")
            st.write(f"* **Target 2 (200 DMA Mean Reversion):** ₹{t2} *(Book 35%)*")
            st.write(f"* **Target 3 (Swing High):** ₹{t3} *(Book 25%)*")
            st.write(f"* **Calculated Risk-to-Reward:** 1 : {rr_ratio}")
            st.write(f"* **Allocated Capital Outlay:** ₹{capital_outlay:,.2f}")
 
        with tab2:
            st.markdown("### Automated Technical & Pattern Diagnostics")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"* **14-Day RSI:** `{rsi_val}` ({'Oversold Rebound' if rsi_val < 35 else 'Neutral' if rsi_val <= 60 else 'Overbought'})")
                st.write(f"* **MACD Status:** `{'Bullish Crossover' if macd_val > macd_sig else 'Bearish Pressure'}` (Line: {macd_val} | Signal: {macd_sig})")
                st.write(f"* **Bollinger Band Squeeze:** `{'Volatility Tightening' if (df['BB_Upper'].iloc[-1] - df['BB_Lower'].iloc[-1]) / cmp_price < 0.10 else 'Normal Expansion'}`")
            with c2:
                st.write(f"* **20 DMA (Short-term Mean):** ₹{sma_20} ({'Above' if cmp_price > sma_20 else 'Below'})")
                st.write(f"* **50 DMA (Medium-term Pivot):** ₹{sma_50} ({'Above' if cmp_price > sma_50 else 'Below'})")
                st.write(f"* **200 DMA (Long-term Structural Trend):** ₹{sma_200} ({'Bullish Macro' if cmp_price > sma_200 else 'Corrective Macro'})")
 
        with tab3:
            st.markdown("### Fundamental Health & Valuation")
            pe_val = info.get('trailingPE', 'N/A')
            pb_val = info.get('priceToBook', 'N/A')
            dy = round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0.0
            roe = round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 'N/A'
            pm = round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 'N/A'
            de = round(info.get('debtToEquity', 0), 2) if info.get('debtToEquity') else 'N/A'
            mcap = f"₹{round(info.get('marketCap', 0) / 1e7, 2):,.2f} Cr" if info.get('marketCap') else "N/A"
            
            f1, f2 = st.columns(2)
            with f1:
                st.write(f"* **Market Cap:** {mcap}")
                st.write(f"* **Trailing P/E:** {pe_val}")
                st.write(f"* **Price-to-Book (P/B):** {pb_val}")
                st.write(f"* **Dividend Yield:** {dy}%")
            with f2:
                st.write(f"* **Return on Equity (ROE):** {roe}%" if roe != 'N/A' else "* **ROE:** N/A")
                st.write(f"* **Net Profit Margin:** {pm}%" if pm != 'N/A' else "* **Net Profit Margin:** N/A")
                st.write(f"* **Debt to Equity:** {de}")
 
            st.write("**Company Overview:**")
            summary = info.get('longBusinessSummary', 'No description available for this ticker.')
            st.write(summary[:650] + "...")
 
        with tab4:
            st.error(f"**Trade Invalidation:** A daily close below ₹{sl} decisively breaks support. Close open positions immediately to preserve capital.")
    else:
        st.error("Unable to load data for this symbol. Check that the ticker exists on NSE.")
 
