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
 
# Initialize session state for multi-page navigation
if "page" not in st.session_state:
    st.session_state.page = 1
if "selected_stocks" not in st.session_state:
    st.session_state.selected_stocks = list(DEFAULT_WATCHLIST.keys())
if "active_stock" not in st.session_state:
    st.session_state.active_stock = "REC Ltd"
 
def go_to_page(page_num):
    st.session_state.page = page_num
 
def set_active_stock(stock_name):
    st.session_state.active_stock = stock_name
    st.session_state.page = 3
 
# -------------------------------------------------------------
# Technical Calculations
# -------------------------------------------------------------
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))
 
@st.cache_data(ttl=900)
def fetch_stock_data(ticker_symbol: str):
    ticker_clean = ticker_symbol.strip().upper()
    if not ticker_clean.endswith(".NS") and not ticker_clean.endswith(".BO"):
        ticker_clean = ticker_clean + ".NS"
        
    stock = yf.Ticker(ticker_clean)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 30:
        return None, dict()
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    
    try:
        info_data = stock.info
        if not isinstance(info_data, dict):
            info_data = dict()
    except Exception:
        info_data = dict()
        
    return df, info_data
 
# -------------------------------------------------------------
# Sidebar Settings
# -------------------------------------------------------------
st.sidebar.title("Risk Management")
portfolio_size = st.sidebar.number_input("Portfolio Capital (INR)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
 
# =============================================================
# PAGE 1: Stock Selection
# =============================================================
if st.session_state.page == 1:
    st.title("Step 1: Select or Add Equities")
    st.write("Choose from the predefined list or enter custom NSE stock symbols.")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.subheader("Select from Watchlist")
        selected_presets = st.multiselect(
            "Choose tickers to analyze:",
            options=list(DEFAULT_WATCHLIST.keys()),
            default=list(DEFAULT_WATCHLIST.keys())
        )
        
    with col2:
        st.subheader("Add Custom NSE Symbols")
        custom_input = st.text_input("Enter NSE Symbols (comma-separated, e.g. TRENT, BEL, COALINDIA):", "")
        custom_tickers = [x.strip().upper() for x in custom_input.split(",") if x.strip()]
 
    st.write("")
    if st.button("Analyze & Generate Overview Table", type="primary", use_container_width=True):
        combined = list(selected_presets)
        for c in custom_tickers:
            if c not in combined:
                combined.append(c)
        
        if not combined:
            st.error("Please pick or type at least one stock to proceed.")
        else:
            st.session_state.selected_stocks = combined
            go_to_page(2)
            st.rerun()
 
# =============================================================
# PAGE 2: Comparison Dashboard
# =============================================================
elif st.session_state.page == 2:
    st.title("Step 2: Multi-Asset Comparative Overview")
    
    if st.button("Back to Stock Selection"):
        go_to_page(1)
        st.rerun()
 
    rows = []
    failed = []
 
    with st.spinner("Fetching market quotes and technical metrics..."):
        for item in st.session_state.selected_stocks:
            ticker = DEFAULT_WATCHLIST.get(item, item + ".NS")
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
                
                # Setup score
                score = 0
                if pd.notna(pe) and pe < 15:
                    score += 2
                if div_yield > 3.0:
                    score += 2
                if dist_to_low < 8.0:
                    score += 3
                if rsi_val < 40:
                    score += 2
                
                rows.append({
                    "Stock": item,
                    "CMP": cmp_price,
                    "52W High": high_52w,
                    "52W Low": low_52w,
                    "Dist to Low (%)": dist_to_low,
                    "P/E": pe if pd.notna(pe) else "N/A",
                    "Div Yield": str(div_yield) + "%",
                    "RSI (14)": rsi_val,
                    "Score": score
                })
            else:
                failed.append(item)
 
    if rows:
        summary_df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
        st.subheader("Asset Comparison Matrix")
        st.dataframe(summary_df, use_container_width=True)
 
        st.subheader("Select Stock for Detailed Deep Dive:")
        num_cols = min(len(summary_df), 4)
        btn_cols = st.columns(num_cols if num_cols > 0 else 1)
        for index, row in summary_df.reset_index().iterrows():
            col_idx = index % (num_cols if num_cols > 0 else 1)
            with btn_cols[col_idx]:
                btn_label = row['Stock'] + " (Score: " + str(row['Score']) + ")"
                if st.button(btn_label, key="btn_" + str(row['Stock']), use_container_width=True):
                    set_active_stock(row['Stock'])
                    st.rerun()
 
    if failed:
        st.warning("Could not load data for: " + ", ".join(failed) + ". Verify the symbols.")
 
# =============================================================
# PAGE 3: Detailed Chart & Execution Setup
# =============================================================
elif st.session_state.page == 3:
    stock_name = st.session_state.active_stock
    ticker = DEFAULT_WATCHLIST.get(stock_name, stock_name + ".NS")
    
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("Back to Table"):
            go_to_page(2)
            st.rerun()
    with col_title:
        st.title("Detailed Analysis: " + stock_name + " (" + ticker + ")")
 
    df, info = fetch_stock_data(ticker)
 
    if df is not None:
        cmp_price = round(float(df['Close'].iloc[-1]), 2)
        low_52w = round(float(df['Low'].min()), 2)
        high_52w = round(float(df['High'].max()), 2)
        rsi_val = round(float(df['RSI'].iloc[-1]), 2)
        
        sma_20 = round(float(df['SMA_20'].iloc[-1]), 2) if not pd.isna(df['SMA_20'].iloc[-1]) else cmp_price
        sma_50 = round(float(df['SMA_50'].iloc[-1]), 2) if not pd.isna(df['SMA_50'].iloc[-1]) else round(cmp_price * 1.05, 2)
        sma_200 = round(float(df['SMA_200'].iloc[-1]), 2) if not pd.isna(df['SMA_200'].iloc[-1]) else round(cmp_price * 1.10, 2)
 
        # Risk & Target Calculations
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
        m2.metric("Stop Loss", "₹" + str(sl), "-₹" + str(risk_per_share))
        m3.metric("Target 1 (50 DMA)", "₹" + str(t1), "+" + str(round(((t1 - cmp_price) / cmp_price) * 100, 1)) + "%")
        m4.metric("Position Size", str(position_qty) + " Shares", "Max Risk: ₹" + str(int(max_risk_inr)))
 
        # Candlestick Chart
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
 
        fig.add_hline(y=sl, line_dash="dash", line_color="red", annotation_text="Stop-Loss Floor")
        fig.add_hline(y=t1, line_dash="dot", line_color="green", annotation_text="Target 1")
 
        fig.update_layout(
            title=stock_name + " Daily Price Chart with Key Moving Averages",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=500,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
 
        # Tab views
        tab1, tab2, tab3 = st.tabs(["Execution Setup", "Fundamentals", "Invalidation Rules"])
        
        with tab1:
            st.markdown("### Actionable Trading Setup")
            st.write("- **Entry Range:** ₹" + str(round(cmp_price * 0.99, 2)) + " to ₹" + str(cmp_price))
            st.write("- **Stop-Loss:** ₹" + str(sl) + " (1% under 52W low of ₹" + str(low_52w) + ")")
            st.write("- **Target 1 (50 DMA):** ₹" + str(t1) + " (Book 40%)")
            st.write("- **Target 2 (200 DMA):** ₹" + str(t2) + " (Book 35%)")
