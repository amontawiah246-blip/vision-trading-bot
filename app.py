import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Forex Live Scalper + Log", layout="wide")

# Initialize Log in Session State (This keeps the history while tab is open)
if 'history' not in st.session_state:
    st.session_state.history = []

FOREX_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "BTC/USD": "BTC-USD"
}

# --- SIDEBAR ---
st.sidebar.header("🕹️ Bot Controls")
selected_label = st.sidebar.selectbox("Select Currency Pair", list(FOREX_PAIRS.keys()))
ticker = FOREX_PAIRS[selected_label]
refresh_rate = st.sidebar.slider("Refresh Rate (Seconds)", 30, 120, 60)

if st.sidebar.button("Clear Trade Log"):
    st.session_state.history = []
    st.rerun()

# --- LIVE FRAGMENT (The Engine) ---
@st.fragment(run_every=refresh_rate)
def run_scanner():
    try:
        # 1. Fetch Data
        df = yf.download(ticker, period="2d", interval="1m", progress=False)
        if df.empty or len(df) < 25:
            st.warning("Waiting for market data feed...")
            return

        # 2. Indicators
        df.ta.rsi(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        # 3. Dynamic Column Logic (The "No Error" Fix)
        rsi_col = [c for c in df.columns if 'RSI' in str(c)][0]
        l_band = [c for c in df.columns if 'BBL' in str(c)][0]
        u_band = [c for c in df.columns if 'BBU' in str(c)][0]

        last_row = df.iloc[-1]
        price = last_row['Close']
        rsi_val = last_row[rsi_col]

        # 4. Signal Logic
        signal = "NEUTRAL"
        if price <= last_row[l_band] and rsi_val > 30:
            signal = "BUY (CALL)"
        elif price >= last_row[u_band] and rsi_val < 70:
            signal = "SELL (PUT)"

        # 5. Log the Signal if it's not Neutral
        if signal != "NEUTRAL":
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Only add if it's different from the last logged signal to avoid duplicates
            if not st.session_state.history or st.session_state.history[0]['Price'] != f"{price:.4f}":
                st.session_state.history.insert(0, {
                    "Time": timestamp,
                    "Pair": selected_label,
                    "Signal": signal,
                    "Price": f"{price:.4f}",
                    "RSI": f"{rsi_val:.1f}"
                })

        # --- UI DISPLAY ---
        st.title(f"🚀 Live Scalper: {selected_label}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Price", f"{price:.4f}")
        
        color = "green" if "BUY" in signal else "red" if "SELL" in signal else "gray"
        c2.markdown(f"### Signal: :{color}[{signal}]")
        c3.write(f"**Last Sync:** {datetime.now().strftime('%H:%M:%S')}")

        st.line_chart(df['Close'].tail(50))

        # --- TRADE LOG TABLE ---
        st.divider()
        st.subheader("📝 Recent Signal History")
        if st.session_state.history:
            log_df = pd.DataFrame(st.session_state.history)
            st.table(log_df.head(10)) # Shows last 10 signals
        else:
            st.info("Scanning for signals... History will appear here.")

    except Exception as e:
        st.info("Reconnecting to market feed...")

# Execute the Bot
run_scanner()