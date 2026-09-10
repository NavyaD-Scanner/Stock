import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
 
# -------------------------------------------------------------
# Configuration & Layout
# -------------------------------------------------------------
st.set_page_config(
    page_title="Institutional Equity Terminal & Screener",
    page_icon="📈",
    layout="wide"
)
 
# Default Watchlist
DEFAULT_WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
# Curated High-Probability Suggestion Candidates
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
# Session State Initialization
# -------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = 1
 
# Master dictionary of Name -> NSE Ticker mapping
if "ticker_registry" not in st.session_state:
    initial_registry = dict(DEFAULT_WATCHLIST)
    initial_registry.update(SUGGESTIONS)
    st.session_state.ticker_registry = initial_registry
 
# List of currently active stock names to analyze
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = list(DEFAULT_WATCHLIST.keys())
 
# Current stock selected for deep dive on Page 3
if "active_stock" not in st.session_state:
    st.session_state.active_stock = "REC Ltd"
 
def navigate_to(page_num):
    st.session_state.page = page_num
 
def inspect_stock(name):
    st.session_state.active_stock = name
    st.session_state.page = 3
 
# -------------------------------------------------------------
# Quantitative Indicators & Data Engine
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
 
@st.cache_data(ttl=600)
def fetch_stock_data(ticker_symbol: str):
    clean_ticker = ticker_symbol.strip().upper()
    if not clean_ticker.endswith(".NS") and not clean_ticker.endswith(".BO"):
        clean_ticker = clean_ticker + ".NS"
        
    stock = yf.Ticker(clean_ticker)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 25:
        return None, dict()
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    macd, signal, hist = calculate_macd(df['Close'])
    df['MACD'] = macd
    df['MACD_Signal'] = signal
    df['MACD_Hist'] = hist
 
    try:
        info_data = stock.info
        if not isinstance(info_data, dict):
            info_data = dict()
    except Exception:
        info_data = dict()
        
    return df, info_data
 
# -------------------------------------------------------------
# Sidebar Navigation & Settings
# -------------------------------------------------------------
st.sidebar.title("Terminal Navigation")
 
app_mode = st.sidebar.radio(
    "Jump to Step:",
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
st.sidebar.subheader("Risk Parameters")
portfolio_size = st.sidebar.number_input("Portfolio Equity (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Risk Limit per Trade (%)", 0.25, 3.0, 1.0, 0.05)
 
st.sidebar.divider()
st.sidebar.subheader("Quick Stock Switcher")
# Ensure current active stock is selectable in sidebar
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
    st.title("Step 1: Build Your Watchlist")
    st.write("Select preset stocks, add our suggested market tickers, or type any custom NSE equity.")
 
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
        st.subheader("Smart Suggestions (High-Probability Catalysts)")
        st.caption("Check any of these stocks to include them in the screener table and full deep-dive pages:")
        picked_suggestions = []
        for name, ticker_code in SUGGESTIONS.items():
            # Check if this suggestion was already previously selected
            is_checked = name in st.session_state.selected_stocks
            if st.checkbox(name + " (" + ticker_code + ")", value=is_checked, key="chk_" + ticker_code):
                picked_suggestions.append(name)
 
    st.write("")
    if st.button("🚀 Analyze & Generate Overview Table", type="primary", use_container_width=True):
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
        
        # Register custom tickers in global dictionary
        for c in custom_tickers:
            st.session_state.ticker_registry[c] = c + ".NS"
 
        # Combine presets, suggestions, and custom tickers
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
    st.title("Step 2: Multi-Asset Comparative Screener")
    
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("⬅️ Back to Stock Selection"):
            navigate_to(1)
            st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching market quotes, indicators, and asymmetric scores..."):
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
                
                # Asymmetry score logic
                score = 0
                if pd.notna(pe) and pe < 15: score += 2
                if div_yield > 3.0: score += 2
                if dist_to_low < 8.0: score += 3
                if rsi_val < 40: score += 2
                
                rows.append({
                    "Stock": item,
                    "CMP (₹)": cmp_price,
                    "52W High (₹)": high_52w,
                    "52W Low (₹)": low_52w,
                    "Dist to 52W Low (%)": dist_to_low,
                    "P/E Ratio": pe if pd.notna(pe) else "N/A",
                    "Div Yield (%)": str(div_yield) + "%",
                    "RSI (14)": rsi_val,
                    "Score": score
                })
            else:
                failed.append(item)
 
    if rows:
        summary_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
        st.subheader("Asset Comparison Matrix (Hover headers for explanations)")
        
        # Interactive table with column hover tooltips
        st.dataframe(
            summary_df,
            use_container_width=True,
            column_config={
                "Stock": st.column_config.TextColumn("Stock", help="Name or ticker symbol of the equity."),
                "CMP (₹)": st.column_config.NumberColumn("CMP (₹)", help="Current Market Price based on latest NSE session close."),
                "52W High (₹)": st.column_config.NumberColumn("52W High (₹)", help="Highest traded price in 52 weeks. Structural overhead resistance."),
                "52W Low (₹)": st.column_config.NumberColumn("52W Low (₹)", help="Lowest traded price in 52 weeks. Represents long-term support base."),
                "Dist to 52W Low (%)": st.column_config.NumberColumn("Dist to 52W Low (%)", help="Percentage distance from 52-week low. Under 8% offers tight risk-defined trade setups."),
                "P/E Ratio": st.column_config.TextColumn("P/E Ratio", help="Trailing Twelve Month Price-to-Earnings ratio. <15 represents value, >50 implies premium growth."),
                "Div Yield (%)": st.column_config.TextColumn("Div Yield (%)", help="Annual dividend yield. >3% provides a defensive cushion against market corrections."),
                "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="14-Day Relative Strength Index. Below 35 indicates oversold rebound potential; above 70 indicates overbought."),
                "Score": st.column_config.ProgressColumn("Score", help="Opportunity Score (0-9). Evaluates asymmetric risk-reward based on support proximity, valuation, and oversold indicators.", min_value=0, max_value=9)
            }
        )
 
        st.subheader("🔍 Click a stock to open Live Chart & Full Breakdown:")
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
        st.warning("Could not fetch data for: " + ", ".join(failed) + ". Please check ticker spelling.")
 
# =============================================================
# PAGE 3: Live Chart & Comprehensive Deep Dive
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
        st.title("Detailed Analysis: " + stock_name + " (NSE: " + symbol_tv + ")")
 
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
 
        # Overview Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CMP", "₹" + str(cmp_price))
        m2.metric("Stop-Loss (Exit)", "₹" + str(sl), "-₹" + str(risk_per_share))
        m3.metric("Target 1 (50 DMA)", "₹" + str(t1), "+" + str(round(((t1 - cmp_price)/cmp_price)*100, 1)) + "%")
        m4.metric("Recommended Qty", str(position_qty) + " Shares", "Max Risk: ₹" + str(int(max_risk_inr)))
 
        # Chart Engine Selector
        chart_mode = st.radio("Chart View:", ["Live TradingView Advanced Chart", "Technical Indicators & Moving Averages"], horizontal=True)
 
        if chart_mode == "Live TradingView Advanced Chart":
            st.caption("Live streaming candlestick chart powered by TradingView. Supports drawings, sub-minute intervals, and direct indicators.")
            tv_html = f"""
            <div class="tradingview-widget-container" style="height:550px;width:100%;">
              <div id="tradingview_widget" style="height:calc(100% - 32px);width:100%;"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget({{
                "autosize": true,
                "symbol": "NSE:{symbol_tv}",
                "interval": "D",
                "timezone": "Asia/Kolkata",
                "theme": "dark",
                "style": "1",
                "locale": "in",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "allow_symbol_change": true,
                "container_id": "tradingview_widget"
              }});
              </script>
            </div>
            """
            components.html(tv_html, height=560)
        else:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'],
                name="Price"
            ))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20 DMA', line=dict(color='yellow', width=1.2)))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='50 DMA', line=dict(color='cyan', width=1.5)))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], mode='lines', name='200 DMA', line=dict(color='magenta', width=1.8)))
            fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="Stop-Loss Level")
            fig.add_hline(y=t1, line_dash="dot", line_color="green", annotation_text="Target 1 (50 DMA)")
 
            fig.update_layout(
                title=stock_name + " Daily Price Action with Key DMAs",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=500,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
 
        # Tabbed Detail Analysis
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Execution Plan", 
            "📈 Technical Analysis", 
            "📊 Fundamental Analysis", 
            "⚠️ Risks & Invalidation"
        ])
 
        with tab1:
            st.markdown("### Actionable Trade Setup")
            st.write(f"* **Entry Range:** ₹{round(cmp_price * 0.99, 2)} – ₹{cmp_price}")
            st.write(f"* **Protective Stop-Loss:** ₹{sl} *(1% below 52-week support of ₹{low_52w})*")
            st.write(f"* **Target 1 (50 DMA Retest):** ₹{t1} *(Book 40%)*")
            st.write(f"* **Target 2 (200 DMA Mean Reversion):** ₹{t2} *(Book 35%)*")
            st.write(f"* **Target 3 (Swing High):** ₹{t3} *(Book 25%)*")
            st.write(f"* **Risk-to-Reward Ratio:** 1 : {rr_ratio}")
            st.write(f"* **Allocated Capital Outlay:** ₹{capital_outlay:,.2f}")
 
        with tab2:
            st.markdown("### Technical Indicator Summary")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.write(f"* **14-Day RSI:** `{rsi_val}` ({'Oversold Rebound Zone' if rsi_val < 35 else 'Neutral' if rsi_val <= 60 else 'Overbought'})")
                st.write(f"* **MACD Line:** `{macd_val}` | **Signal Line:** `{macd_sig}`")
                st.write(f"* **MACD Histogram:** `{'Bullish Divergence' if macd_val > macd_sig else 'Bearish Pressure'}`")
            with t_col2:
                st.write(f"* **20 DMA:** ₹{sma_20} ({'Above' if cmp_price > sma_20 else 'Below'})")
                st.write(f"* **50 DMA:** ₹{sma_50} ({'Above' if cmp_price > sma_50 else 'Below'})")
                st.write(f"* **200 DMA:** ₹{sma_200} ({'Bullish Long-term' if cmp_price > sma_200 else 'Corrective Phase'})")
 
        with tab3:
            st.markdown("### Fundamental Metrics & Financial Health")
            pe_val = info.get('trailingPE', 'N/A')
            pb_val = info.get('priceToBook', 'N/A')
            dy = round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0.0
            roe = round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 'N/A'
            pm = round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 'N/A'
            de = round(info.get('debtToEquity', 0), 2) if info.get('debtToEquity') else 'N/A'
            mcap = f"₹{round(info.get('marketCap', 0) / 1e7, 2):,.2f} Cr" if info.get('marketCap') else "N/A"
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.write(f"* **Market Cap:** {mcap}")
                st.write(f"* **Trailing P/E:** {pe_val}")
                st.write(f"* **Price-to-Book (P/B):** {pb_val}")
                st.write(f"* **Dividend Yield:** {dy}%")
            with f_col2:
                st.write(f"* **Return on Equity (ROE):** {roe}%" if roe != 'N/A' else "* **ROE:** N/A")
                st.write(f"* **Net Profit Margin:** {pm}%" if pm != 'N/A' else "* **Net Profit Margin:** N/A")
                st.write(f"* **Debt to Equity:** {de}")
 
            st.write("**Business Description:**")
            summary = info.get('longBusinessSummary', 'No description available for this ticker.')
            st.write(summary[:650] + "...")
 
        with tab4:
            st.error(f"**Trade Invalidation:** A daily close below ₹{sl} breaks structural support. Close open positions immediately to preserve capital.")
            st.warning("Adhere to your risk parameters. Do not exceed allocated risk per trade.")
    else:
        st.error("Unable to load data for this symbol. Check that the ticker exists on NSE.")
 
