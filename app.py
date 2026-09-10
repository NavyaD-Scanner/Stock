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
    page_title="Institutional Equity Terminal & Live Charting",
    page_icon="📈",
    layout="wide"
)
 
# Core Watchlist
DEFAULT_WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
# Algorithmic Suggestions from Broader Market
SUGGESTIONS = {
    "PFC (Power Finance Corp)": "PFC.NS",
    "BEL (Bharat Electronics)": "BEL.NS",
    "Trent Ltd": "TRENT.NS",
    "Coal India": "COALINDIA.NS",
    "RVNL (Rail Vikas Nigam)": "RVNL.NS",
    "BHEL": "BHEL.NS"
}
 
# Session State Management
if "page" not in st.session_state:
    st.session_state.page = 1
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
# Math & Indicators Engine
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
    ticker_clean = ticker_symbol.strip().upper()
    if not ticker_clean.endswith(".NS") and not ticker_clean.endswith(".BO"):
        ticker_clean += ".NS"
        
    stock = yf.Ticker(ticker_clean)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 25:
        return None, dict()
    
    # Technicals
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
# Sidebar: Navigation & Controls
# -------------------------------------------------------------
st.sidebar.title("Navigation & Parameters")
 
# Sidebar Direct Navigation Option
app_mode = st.sidebar.radio(
    "Go To Page:",
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
st.sidebar.subheader("Position Sizing Controls")
portfolio_size = st.sidebar.number_input("Total Trading Capital (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Max Account Risk per Trade (%)", 0.25, 3.0, 1.0, 0.05)
 
st.sidebar.divider()
st.sidebar.subheader("Quick Switch Stock (Page 3)")
selected_quick = st.sidebar.selectbox("Active Stock:", st.session_state.selected_stocks, index=0)
if selected_quick != st.session_state.active_stock:
    st.session_state.active_stock = selected_quick
    if st.session_state.page == 3:
        st.rerun()
 
# =============================================================
# PAGE 1: Stock Selection & Suggestions
# =============================================================
if st.session_state.page == 1:
    st.title("Step 1: Build Your Watchlist")
    st.write("Select from default universe, enter custom NSE tickers, or pick from our curated market recommendations.")
 
    col1, col2 = st.columns([1.2, 1])
 
    with col1:
        st.subheader("Current Watchlist Selection")
        selected_presets = st.multiselect(
            "Select tickers to evaluate:",
            options=list(DEFAULT_WATCHLIST.keys()),
            default=[s for s in st.session_state.selected_stocks if s in DEFAULT_WATCHLIST]
        )
 
        st.subheader("Manual Custom Addition")
        custom_input = st.text_input("Enter NSE Symbols (comma separated, e.g. TRENT, BEL, COALINDIA):", "")
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
 
    with col2:
        st.subheader("Smart Suggestions (High-Beta / Value Catalysts)")
        st.caption("Curated picks displaying strong sector rotation or mean-reversion characteristics:")
        picked_suggestions = []
        for name, tick in SUGGESTIONS.items():
            if st.checkbox(f"{name} ({tick})", value=False, key=f"sug_{tick}"):
                picked_suggestions.append(name.split(" ")[0])
 
    st.write("")
    if st.button("Generate Comparative Overview Table", type="primary", use_container_width=True):
        combined = list(set(selected_presets + custom_tickers + picked_suggestions))
        if not combined:
            st.error("Please select at least one stock to proceed.")
        else:
            st.session_state.selected_stocks = combined
            navigate_to(2)
            st.rerun()
 
# =============================================================
# PAGE 2: Comparison Dashboard with Hover Tooltips
# =============================================================
elif st.session_state.page == 2:
    st.title("Step 2: Multi-Asset Comparative Overview")
    
    col_nav1, col_nav2 = st.columns([1, 4])
    with col_nav1:
        if st.button("Back to Stock Selection"):
            navigate_to(1)
            st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching market quotes, computing indicators, and evaluating setup scores..."):
        for item in st.session_state.selected_stocks:
            ticker = DEFAULT_WATCHLIST.get(item, item if item.endswith(".NS") else item + ".NS")
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
                
                # Scoring
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
                    "Div Yield (%)": f"{div_yield}%",
                    "RSI (14)": rsi_val,
                    "Score": score
                })
            else:
                failed.append(item)
 
    if rows:
        summary_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
        st.subheader("Asset Comparison Matrix (Hover column headers for info)")
        
        # Interactive Table with Hover Tooltips
        st.dataframe(
            summary_df,
            use_container_width=True,
            column_config={
                "Stock": st.column_config.TextColumn("Stock", help="Name or ticker symbol of the equity."),
                "CMP (₹)": st.column_config.NumberColumn("CMP (₹)", help="Current Market Price based on the latest NSE session close."),
                "52W High (₹)": st.column_config.NumberColumn("52W High (₹)", help="Highest traded price over the last 252 trading sessions. Key structural resistance."),
                "52W Low (₹)": st.column_config.NumberColumn("52W Low (₹)", help="Lowest traded price over the last 252 sessions. Acts as multi-month floor support."),
                "Dist to 52W Low (%)": st.column_config.NumberColumn("Dist to 52W Low (%)", help="Percentage distance from 52-week low. Values below 8% signify potential bottom defense zones with tight stop-loss placement."),
                "P/E Ratio": st.column_config.TextColumn("P/E Ratio", help="Trailing Twelve Month Price-to-Earnings ratio. <15 indicates value; >50 indicates high premium."),
                "Div Yield (%)": st.column_config.TextColumn("Div Yield (%)", help="Annualized dividend yield. >3% provides a defensive valuation floor during corrections."),
                "RSI (14)": st.column_config.NumberColumn("RSI (14)", help="14-day Relative Strength Index. <30 is Oversold (potential rebound); >70 is Overbought."),
                "Score": st.column_config.ProgressColumn("Score", help="Proprietary Asymmetry Score (0 to 9). Higher scores reflect favorable risk-reward setups (low P/E, high yield, oversold RSI, close to structural support).", min_value=0, max_value=9)
            }
        )
 
        st.subheader("Select Stock to View Live Chart & Full Breakdown:")
        n_cols = min(len(summary_df), 4)
        btn_cols = st.columns(n_cols if n_cols > 0 else 1)
        for index, row in summary_df.reset_index().iterrows():
            col_idx = index % (n_cols if n_cols > 0 else 1)
            with btn_cols[col_idx]:
                if st.button(f"{row['Stock']} (Score: {row['Score']})", key=f"btn_{row['Stock']}", use_container_width=True):
                    inspect_stock(row['Stock'])
                    st.rerun()
 
    if failed:
        st.warning(f"Could not load data for: {', '.join(failed)}. Ensure symbol is valid on NSE.")
 
# =============================================================
# PAGE 3: Live Chart & Comprehensive Deep Dive
# =============================================================
elif st.session_state.page == 3:
    stock_name = st.session_state.active_stock
    ticker = DEFAULT_WATCHLIST.get(stock_name, stock_name if stock_name.endswith(".NS") else stock_name + ".NS")
    symbol_tv = ticker.replace(".NS", "")
    
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("Back to Table"):
            navigate_to(2)
            st.rerun()
    with col_title:
        st.title(f"Detailed Analysis: {stock_name} (NSE: {symbol_tv})")
 
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
 
        # Risk Math & Targets
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
 
        # Top Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CMP", f"₹{cmp_price}")
        m2.metric("Calculated Stop-Loss", f"₹{sl}", f"-₹{risk_per_share} risk/sh")
        m3.metric("Target 1 (50 DMA)", f"₹{t1}", f"+{round(((t1 - cmp_price)/cmp_price)*100, 1)}%")
        m4.metric("Position Size", f"{position_qty} Shares", f"Risk: ₹{int(max_risk_inr):,}")
 
        # Live Chart vs Static Indicator Chart Toggle
        chart_mode = st.radio("Chart Engine:", ["Live TradingView Advanced Chart", "Technical Indicators & Moving Averages"], horizontal=True)
 
        if chart_mode == "Live TradingView Advanced Chart":
            st.caption("Live streaming candlestick chart powered by TradingView. Supports drawings, sub-minute intervals, and direct indicators.")
            # Embed TradingView Advanced Real-Time Widget
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
                title=f"{stock_name} Technical Structure with Key DMAs",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=500,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
 
        # Tabbed Analysis Section
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Execution Plan", 
            "📈 Technical Analysis", 
            "📊 Fundamental Analysis", 
            "⚠️ Risks & Invalidation"
        ])
 
        with tab1:
            st.markdown("### Actionable Trade Setup")
            st.write(f"* **Entry Range:** ₹{round(cmp_price * 0.99, 2)} – ₹{cmp_price}")
            st.write(f"* **Protective Stop-Loss:** ₹{sl} (Placed 1% below structural 52-week support of ₹{low_52w})")
            st.write(f"* **Target 1 (50 DMA Retest):** ₹{t1} *(Exit 40%)*")
            st.write(f"* **Target 2 (200 DMA Mean Reversion):** ₹{t2} *(Exit 35%)*")
            st.write(f"* **Target 3 (Swing High):** ₹{t3} *(Exit 25%)*")
            st.write(f"* **Risk-to-Reward Ratio:** 1 : {rr_ratio}")
            st.write(f"* **Allocated Capital Required:** ₹{capital_outlay:,.2f}")
 
        with tab2:
            st.markdown("### Detailed Technical Indicators")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.write(f"* **14-Day RSI:** `{rsi_val}` ({'Oversold Rebound Zone' if rsi_val < 35 else 'Neutral Drift' if rsi_val <= 60 else 'Overbought'})")
                st.write(f"* **MACD Line:** `{macd_val}` | **Signal Line:** `{macd_sig}`")
                st.write(f"* **MACD Histogram:** `{'Positive Divergence / Bullish' if macd_val > macd_sig else 'Bearish Momentum'}`")
            with t_col2:
                st.write(f"* **20 DMA:** ₹{sma_20} ({'Above' if cmp_price > sma_20 else 'Below'})")
                st.write(f"* **50 DMA:** ₹{sma_50} ({'Above' if cmp_price > sma_50 else 'Below'})")
                st.write(f"* **200 DMA:** ₹{sma_200} ({'Bullish Long-term Trend' if cmp_price > sma_200 else 'Corrective Phase'})")
 
        with tab3:
            st.markdown("### Fundamental Metrics & Health")
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
 
            st.write("**Company Business Profile:**")
            summary = info.get('longBusinessSummary', 'No description available for this ticker.')
            st.write(summary[:650] + "...")
 
        with tab4:
            st.error(f"**Trade Invalidation:** A daily close below ₹{sl} breaks structural support. Exit all positions immediately to protect portfolio equity.")
            st.warning("Ensure position risk does not exceed your defined capital limits. PSU stocks carry policy and disinvestment beta.")
    else:
        st.error("Unable to load data for this ticker. Verify the symbol on NSE.")
 
