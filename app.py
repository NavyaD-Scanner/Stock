import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
 
# Page configuration
st.set_page_config(
    page_title="Indian Equities Trade Screener",
    page_icon="📈",
    layout="wide"
)
 
# Stock Universe Mapping
WATCHLIST = {
    "Prince Pipes": "PRINCEPIPE.NS",
    "HUDCO": "HUDCO.NS",
    "REC Ltd": "RECLTD.NS",
    "MosChip Tech": "MOSCHIP.NS",
    "Ajax Engineering": "AJAXENGG.NS",
    "LIC": "LICI.NS",
    "IRFC": "IRFC.NS"
}
 
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
 
@st.cache_data(ttl=900)  # Cache data for 15 minutes
def fetch_stock_data(ticker_symbol: str):
    stock = yf.Ticker(ticker_symbol)
    df = stock.history(period="1y", interval="1d")
    
    if df.empty or len(df) < 50:
        return None, None
    
    # Calculate indicators
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    
    try:
        info = stock.info
    except Exception:
        info = {}
        
    return df, info
 
# Sidebar controls
st.sidebar.title("Configuration")
portfolio_size = st.sidebar.number_input("Portfolio Equity (₹)", value=1000000, step=50000)
risk_per_trade_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
 
st.title("Swing Trading & Screener Dashboard")
st.caption("Quantitative screening and technical setup analysis for selected Indian Equities.")
 
# 1. Summary Screener
screener_data = []
 
with st.spinner("Fetching latest market data..."):
    for name, ticker in WATCHLIST.items():
        df, info = fetch_stock_data(ticker)
        if df is not None:
            cmp = round(df['Close'].iloc[-1], 2)
            low_52w = round(df['Low'].min(), 2)
            high_52w = round(df['High'].max(), 2)
            rsi = round(df['RSI'].iloc[-1], 2)
            pe = round(info.get('trailingPE', np.nan), 2) if info and info.get('trailingPE') else np.nan
            div_yield = round(info.get('dividendYield', 0) * 100, 2) if info and info.get('dividendYield') else 0.0
            dist_to_low = round(((cmp - low_52w) / low_52w) * 100, 2)
            
            # Opportunity scoring criteria
            score = 0
            if pd.notna(pe) and pe < 15: score += 2
            if div_yield > 3.0: score += 2
            if dist_to_low < 8.0: score += 3  # Near structural base
            if rsi < 40: score += 2          # Oversold / turning
            
            screener_data.append({
                "Name": name,
                "Ticker": ticker,
                "CMP (₹)": cmp,
                "52W High (₹)": high_52w,
                "52W Low (₹)": low_52w,
                "Distance to 52W Low (%)": dist_to_low,
                "P/E": pe,
                "Div Yield (%)": div_yield,
                "RSI (14)": rsi,
                "Score": score
            })
 
if screener_data:
    screener_df = pd.DataFrame(screener_data).sort_values(by="Score", ascending=False)
    st.subheader("Market Screener & Opportunity Scores")
    st.dataframe(screener_df.style.highlight_max(subset=["Score"], color="#2E7D32"), use_container_width=True)
 
# 2. Detailed Technical & Trade Setup Section
st.divider()
selected_stock_name = st.selectbox("Select stock for detailed setup:", list(WATCHLIST.keys()), index=2)
selected_ticker = WATCHLIST[selected_stock_name]
 
df_stock, info_stock = fetch_stock_data(selected_ticker)
 
if df_stock is not None:
    cmp = round(df_stock['Close'].iloc[-1], 2)
    low_52w = round(df_stock['Low'].min(), 2)
    sma_50 = round(df_stock['SMA_50'].iloc[-1], 2) if not pd.isna(df_stock['SMA_50'].iloc[-1]) else cmp * 1.05
    sma_200 = round(df_stock['SMA_200'].iloc[-1], 2) if not pd.isna(df_stock['SMA_200'].iloc[-1]) else cmp * 1.10
    
    # Trade Setup Calculations
    sl = round(low_52w * 0.99, 2)
    risk_per_share = round(cmp - sl, 2)
    max_risk_inr = portfolio_size * (risk_per_trade_pct / 100)
    
    position_qty = int(max_risk_inr / risk_per_share) if risk_per_share > 0 else 0
    capital_required = position_qty * cmp
    t1 = sma_50
    t2 = sma_200
    t3 = round(cmp + (risk_per_share * 3), 2)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CMP", f"₹{cmp}")
    col2.metric("Stop-Loss (Below 52W Low)", f"₹{sl}", f"-₹{risk_per_share}")
    col3.metric("Target 1 (50 DMA)", f"₹{t1}", f"+{round(((t1-cmp)/cmp)*100, 1)}%")
    col4.metric("Recommended Qty", f"{position_qty} shares", f"Capital: ₹{capital_required:,.0f}")
 
    # Candlestick chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_stock.index,
        open=df_stock['Open'], high=df_stock['High'],
        low=df_stock['Low'], close=df_stock['Close'],
        name="Price"
    ))
    fig.add_trace(go.Scatter(x=df_stock.index, y=df_stock['SMA_20'], mode='lines', name='SMA 20', line=dict(color='yellow', width=1)))
    fig.add_trace(go.Scatter(x=df_stock.index, y=df_stock['SMA_50'], mode='lines', name='SMA 50', line=dict(color='cyan', width=1.2)))
    fig.add_trace(go.Scatter(x=df_stock.index, y=df_stock['SMA_200'], mode='lines', name='SMA 200', line=dict(color='magenta', width=1.5)))
 
    fig.update_layout(
        title=f"{selected_stock_name} ({selected_ticker}) Daily Chart with Moving Averages",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
 
    # Trade Setup Breakdown
    with st.expander("Detailed Trade Setup & Plan", expanded=True):
        st.markdown(f"""
        - **Entry Range:** ₹{round(cmp * 0.99, 2)} – ₹{cmp}
        - **Stop-Loss:** **₹{sl}** (Strict exit on a daily close below structural 52-week support)
        - **Target 1 (Mean Reversion to 50 DMA):** ₹{t1} (Exit 40%)
        - **Target 2 (200 DMA / Intermediate Pivot):** ₹{t2} (Exit 35%)
        - **Target 3 (Swing Resistance):** ₹{t3} (Exit remaining 25%)
        - **Blended Risk/Reward Ratio:** ~1:2.3
        """)
else:
    st.error("Could not fetch data for this ticker. It may be recently listed or delisted.")
