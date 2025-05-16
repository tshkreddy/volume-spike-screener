import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

BINANCE_FUTURES_URL = "https://fapi.binance.com"
MAX_LIMIT = 1500
RATE_LIMIT_SLEEP = 1.2  # seconds between requests


# Get all USDT perpetual futures symbols
def get_symbols():
    url = f"{BINANCE_FUTURES_URL}/fapi/v1/exchangeInfo"
    res = requests.get(url)
    data = res.json()
    symbols = [
        s["symbol"]
        for s in data["symbols"]
        if s["contractType"] == "PERPETUAL" and s["quoteAsset"] == "USDT"
    ]
    return symbols


# Paginate klines to fetch full history for Y days
def get_klines(symbol, interval, start_time, end_time):
    url = f"{BINANCE_FUTURES_URL}/fapi/v1/klines"
    klines = []

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": MAX_LIMIT,
        }
        res = requests.get(url, params=params)
        data = res.json()

        if not data or isinstance(data, dict):
            break

        klines.extend(data)

        last_time = datetime.fromtimestamp(data[-1][0] / 1000)
        start_time = last_time + timedelta(minutes=1)
        time.sleep(RATE_LIMIT_SLEEP)

    return klines


# Process raw klines into DataFrame
def build_volume_df(symbol, days):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    raw = get_klines(symbol, "1m", start_time, end_time)
    df = pd.DataFrame(
        raw,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ],
    )
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["volume"] = pd.to_numeric(df["volume"])
    return df[["open_time", "volume"]]


# Detect volume spike
def detect_spike(df, multiplier):
    if len(df) < 2:
        return False, 0, 0
    avg_volume = df.iloc[:-1]["volume"].mean()
    current_volume = df.iloc[-1]["volume"]
    return current_volume >= multiplier * avg_volume, current_volume, avg_volume


# Streamlit UI
st.set_page_config(layout="wide")
st.title("Binance Perpetual Futures Volume Spike Screener")

st.markdown("Detect when the current 1-minute candle volume is **X times** higher than the average over the past **Y days**.")

col1, col2 = st.columns(2)
with col1:
    multiplier = st.number_input("Volume Spike Multiplier (X)", min_value=1.0, value=10.0, step=0.5)
with col2:
    days = st.number_input("Lookback Period (Y days)", min_value=1, max_value=30, value=5)

if st.button("Scan Now"):
    with st.spinner("Fetching data from Binance and analyzing volume spikes..."):
        symbols = get_symbols()
        results = []

        for i, symbol in enumerate(symbols):
            try:
                df = build_volume_df(symbol, days)
                spike, curr_vol, avg_vol = detect_spike(df, multiplier)
                if spike:
                    results.append({
                        "Symbol": symbol,
                        "Current Volume": round(curr_vol, 2),
                        "Average Volume": round(avg_vol, 2),
                        "Spike Ratio": round(curr_vol / avg_vol, 2),
                        "Timestamp": df.iloc[-1]["open_time"],
                    })
            except Exception as e:
                st.warning(f"[{symbol}] Skipped due to error: {e}")
                continue

        if results:
            df_results = pd.DataFrame(results)
            sort_by = st.selectbox("Sort by", ["Spike Ratio", "Current Volume", "Timestamp"])
            ascending = st.radio("Order", ["Descending", "Ascending"]) == "Ascending"

            df_results = df_results.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
            st.dataframe(df_results, use_container_width=True)
        else:
            st.info("No volume spikes detected with the current settings.")
