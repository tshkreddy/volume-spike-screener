# Binance Volume Spike Screener

A Streamlit app that detects 1-minute volume spikes on Binance USDT perpetual futures.

## Features

- Monitors all Binance USDT perpetual futures
- Detects spikes when current 1m volume > X × average of last Y days
- Interactive UI with sorting

## How to Run

```bash
pip install -r requirements.txt
streamlit run volume_spike_screener.py
```

## Deploy Online

- [Streamlit Cloud](https://streamlit.io/cloud): Push to GitHub, then deploy using their UI
