import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
 
# -------------------------------------------------------------
# Configuration & Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="Institutional Equities Terminal",
    page_icon="📈",
    layout="wide"
)
 
# Preset Watchlist mapping
DEFAULT_WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
# Initialize session state for navigation
if "page" not in st.session_state:
    st.session_state.page = 1
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = list(DEFAULT_WATCHLIST.keys())
if "active_stock" not in st.session_state:
    st.session_state.active_stock = "REC Ltd"
 
# Helper navigation functions
def go_to_page(page_num):
    st.session_state.page = page_num
 
def set_active_stock(stock_name):
    st.session_state.active_stock = stock_name
    st.session_state.page = 3
 
# -------------------------------------------------------------
# Data Processing Engine
# -------------------------------------------------------------
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))
 
@st.cache_data(ttl=900)
def fetch_stock_data(ticker_symbol: str):
    # Ensure .NS suffix for Indian equities if not provided
    if not ticker_symbol.endswith(".NS") and not ticker_symbol.endswith(".BO"):
        ticker_symbol = f"{ticker_symbol.strip().upper()}.NS"
        
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 30:
        return None, None
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    
    try:
        info = stock.info
    except Exception:
        info = {}
        
    return df, info
 
# -------------------------------------------------------------
# Sidebar Settings
# -------------------------------------------------------------
st.sidebar.title("Trading Risk Parameters")
portfolio_size = st.sidebar.number_input("Trading Portfolio (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Max Account Risk / Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
 
# =============================================================
# PAGE 1: Stock Selection & Custom Addition
# =============================================================
if st.session_state.page == 1:
    st.title("🎯 Step 1: Select or Add Equities")
    st.write("Choose from the curated universe or manually add any NSE symbol.")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.subheader("Select from Preset Watchlist")
        selected_presets = st.multiselect(
            "Choose tickers to analyze:",
            options=list(DEFAULT_WATCHLIST.keys()),
            default=list(DEFAULT_WATCHLIST.keys())
        )
        
    with col2:
        st.subheader("Add Custom NSE Stocks")
        custom_input = st.text_input("Enter NSE Symbols (comma separated, e.g. TRENT, BEL, COALINDIA):", "")
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
 
    st.write("")
    if st.button("🚀 Analyze & Generate Overview Table", type="primary", use_container_width=True):
        combined = list(selected_presets)
        for c in custom_tickers:
            if c not in combined:
                combined.append(c)
        
        if not combined:
            st.error("Please choose or type at least one stock to proceed.")
        else:
            st.session_state.selected_stocks = combined
            go_to_page(2)
            st.rerun()
 
# =============================================================
# PAGE 2: Comparison Dashboard & Opportunity Table
# =============================================================
elif st.session_state.page == 2:
    st.title("📊 Step 2: Multi-Asset Comparative Overview")
    
    nav_col1, nav_col2 = st.columns([1, 4])
    with nav_col1:
        if st.button("⬅️ Change Stock List"):
            go_to_page(1)
            st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching market quotes, computing DMAs, and scoring..."):
        for item in st.session_state.selected_stocks:
            ticker = DEFAULT_WATCHLIST.get(item, f"{item}.NS")
            df, info = fetch_stock_data(ticker)
            
            if df is not None:
                cmp = round(df['Close'].iloc[-1], 2)
                low_52w = round(df['Low'].min(), 2)
                high_52w = round(df['High'].max(), 2)
                rsi = round(df['RSI'].iloc[-1], 2)
                pe = round(info.get('trailingPE', np.nan), 2) if info and info.get('trailingPE') else np.nan
                div_yield = round(info.get('dividendYield', 0) * 100, 2) if info and info.get('dividendYield') else 0.0
                dist_to_low = round(((cmp - low_52w) / low_52w) * 100, 2)
                
                # Scoring for mean-reversion setup
                score = 0
                if pd.notna(pe) and pe < 15: score += 2
                if div_yield > 3.0: score += 2
                if dist_to_low < 8.0: score += 3
                if rsi < 40: score += 2
                
                rows.append({
                    "Stock": item,
                    "Ticker": ticker,
                    "CMP (₹)": cmp,
                    "52W High (₹)": high_52w,
                    "52W Low (₹)": low_52w,
                    "Dist to 52W Low (%)": dist_to_low,
                    "P/E": pe if pd.notna(pe) else "N/A",
                    "Div Yield (%)": f"{div_yield}%",
                    "RSI (14)": rsi,
                    "Score": score
                })
            else:
                failed.append(item)
 
    if rows:
        summary_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
        st.subheader("Asset Comparison Matrix")
        st.caption("Higher score implies superior asymmetric risk-reward (support proximity, oversold condition & reasonable valuation).")
        
        # Display Overview Table
        st.dataframe(summary_df.drop(columns=["Ticker"]), use_container_width=True)
 
        st.subheader("🔍 Click a stock to open Chart & Trade Setup:")
        # Render a button grid for deep dive
        btn_cols = st.columns(min(len(summary_df), 4))
        for index, row in summary_df.reset_index().iterrows():
            col_idx = index % min(len(summary_df), 4)
            with btn_cols[col_idx]:
                if st.button(f"Analyze {row['Stock']} (Score: {row['Score']})", key=f"btn_{row['Stock']}", use_container_width=True):
                    set_active_stock(row['Stock'])
                    st.rerun()
 
    if failed:
        st.warning(f"Could not retrieve market data for: {', '.join(failed)}. Please verify their NSE ticker codes.")
 
# =============================================================
# PAGE 3: Detailed Chart & Execution Setup
# =============================================================
elif st.session_state.page == 3:
    stock_name = st.session_state.active_stock
    ticker = DEFAULT_WATCHLIST.get(stock_name, f"{stock_name}.NS")
    
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ Back to Table"):
            go_to_page(2)
            st.rerun()
    with col_title:
        st.title(f"Detailed Analysis: {stock_name} ({ticker})")
 
    df, info = fetch_stock_data(ticker)
 
    if df is not None:
        cmp = round(df['Close'].iloc[-1], 2)
        low_52w = round(df['Low'].min(), 2)
        high_52w = round(df['High'].max(), 2)
        rsi = round(df['RSI'].iloc[-1], 2)
        sma_20 = round(df['SMA_20'].iloc[-1], 2) if not pd.isna(df['SMA_20'].iloc[-1]) else cmp
        sma_50 = round(df['SMA_50'].iloc[-1], 2) if not pd.isna(df['SMA_50'].iloc[-1]) else cmp * 1.05
        sma_200 = round(df['SMA_200'].iloc[-1], 2) if not pd.isna(df['SMA_200'].iloc[-1]) else cmp * 1.10
 
        # Mathematical Execution Engine
        sl = round(low_52w * 0.99, 2)  # 1% below structural 52W low
        risk_per_share = round(cmp - sl, 2)
        max_risk_inr = portfolio_size * (risk_per_trade_pct / 100)
        
        position_qty = int(max_risk_inr / risk_per_share) if risk_per_share > 0 else 0
        capital_outlay = round(position_qty * cmp, 2)
        t1 = sma_50
        t2 = sma_200
        t3 = round(cmp + (risk_per_share * 3.0), 2)
 
        # Top Metric Cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price (CMP)", f"₹{cmp}")
        m2.metric("Stop Loss (Exit)", f"₹{sl}", f"-₹{risk_per_share}")
        m3.metric("Target 1 (50 DMA)", f"₹{t1}", f"+{round(((t1-cmp)/cmp)*100, 1)}%")
        m4.metric("Position Sizing", f"{position_qty} Shares", f"Risk: ₹{max_risk_inr:,.0f}")
 
        # Interactive Candlestick Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="Candlestick"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='20 DMA', line=dict(color='yellow', width=1.2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='50 DMA', line=dict(color='cyan', width=1.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], mode='lines', name='200 DMA', line=dict(color='magenta', width=1.8)))
 
        # Target and SL horizontal references
        fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="Stop-Loss Floor")
        fig.add_hline(y=t1, line_dash="dot", line_color="green", annotation_text="Target 1 (50 DMA)")
 
        fig.update_layout(
            title=f"{stock_name} Daily Price Action with 20, 50 & 200 DMAs",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=520,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
 
        # Tabbed Analytical Details
        tab1, tab2, tab3 = st.tabs(["📋 Execution Trade Plan", "📊 Fundamentals & Valuation", "⚠️ Risk & Invalidation Rules"])
        
        with tab1:
            st.markdown(f"""
            ### Actionable Trading Setup
            - **Entry Zone:** ₹{round(cmp * 0.99, 2)} – ₹{cmp}
            - **Protective Stop-Loss:** **₹{sl}** *(1% under the 52-week low floor of ₹{low_52w})*
            - **Target 1 (Mean Reversion to 50 DMA):** ₹{t1} *(Book 40%)*
            - **Target 2 (Structural Pivot / 200 DMA):** ₹{t2} *(Book 35%)*
            - **Target 3 (Extended Swing Resistance):** ₹{t3} *(Book remaining 25%)*
            - **Calculated Risk-to-Reward:** **1 :
