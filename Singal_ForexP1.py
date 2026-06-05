import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. Konfigurasi Tampilan Dashboard
st.set_page_config(page_title="Alpha Intelligence Terminal", layout="wide")

# CSS Kustom untuk efek Glow, Kartu Premium, dan Running Text Berita
st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    .live-dot { height: 10px; width: 10px; background-color: #00ffcc; border-radius: 50%; display: inline-block; animation: blink 1.5s infinite; box-shadow: 0 0 8px #00ffcc; }
    .trading-card { border: 1px solid #2d2d2d; padding: 15px; border-radius: 12px; background-color: #111111; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .ticker-wrap { width: 100%; background: #1a1a1a; padding: 10px 0; border-top: 1px solid #ffcc00; border-bottom: 1px solid #ffcc00; overflow: hidden; margin-top: 20px; }
    .ticker { display: inline-block; white-space: nowrap; padding-left: 100%; animation: ticker 25s linear infinite; font-weight: bold; color: #ffcc00; }
    @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
    
    /* Memaksa semua teks di dalam kartu premium berwarna putih cerah agar terbaca jelas */
    .trading-card h3, .trading-card h4, .trading-card h5, .trading-card p, .trading-card span, .trading-card b {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGATION SIDEBAR (FOKUS FOREX & GOLD) ---
st.sidebar.title("🎮 Main Navigation")
st.sidebar.markdown("✨ **Mode Aktif:** `🦅 Forex & Gold Terminal`")
st.sidebar.markdown("---")

current_time = datetime.now().strftime("%H:%M:%S WIB")
st.title("🦅 Alpha Intelligence Forex & Gold Terminal")
st.markdown(f"Status Sistem: <span class='live-dot'></span> **LIVE STREAM FEED ACTIVE** | Pembaruan Terakhir: `{current_time}`", unsafe_allow_html=True)
st.markdown("---")

st.sidebar.header("⚙️ Forex Controller")
timeframe_label = st.sidebar.selectbox("Pilih Timeframe Analisis:", ["15 Menit (Scalping)", "1 Jam (Intraday)", "1 Hari (Swing)"])
if st.sidebar.button("🔄 Paksa Sinkronisasi Data Forex"):
    st.cache_data.clear()
    st.sidebar.success("Data Pasar Berhasil Diperbarui!")
    
st.sidebar.markdown("---")
st.sidebar.header("🧮 Kalkulator Risiko Forex")
account_balance = st.sidebar.number_input("Modal Akun Anda ($):", min_value=10, value=1000, step=100)
risk_percentage = st.sidebar.slider("Toleransi Risiko Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

tf_mapping = {"15 Menit (Scalping)": {"interval": "15m", "period": "5d"}, "1 Jam (Intraday)": {"interval": "1h", "period": "7d"}, "1 Hari (Swing)": {"interval": "1d", "period": "60d"}}
selected_interval = tf_mapping[timeframe_label]["interval"]
selected_period = tf_mapping[timeframe_label]["period"]

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    return 100 - (100 / (1 + (gain / loss)))
    
def calculate_atr(high, low, close, window=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()
    
@st.cache_data(ttl=15)
def get_market_data(ticker, period, interval):
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if not df.empty:
        df['RSI'] = calculate_rsi(df['Close'])
        df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'])
    return df
    
pairs_mapping = {'XAU/USD (Gold)': 'GC=F', 'EUR/USD': 'EURUSD=X', 'GBP/USD': 'GBPUSD=X', 'USD/JPY': 'JPY=X', 'AUD/USD': 'AUDUSD=X'}
signals_data = []
all_charts_data = {}

with st.spinner('🔮 Mensinkronisasi satelit forex...'):
    for pair_name, ticker in pairs_mapping.items():
        df = get_market_data(ticker, selected_period, selected_interval)
        if df.empty or len(df) < 15: 
            continue
        all_charts_data[pair_name] = df
        latest = df.iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        current_price = round(latest['Close'], 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(latest['Close'], 4)
        rsi = round(latest['RSI'], 2) if not np.isnan(latest['RSI']) else 50.0
        atr = round(latest['ATR'], 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(latest['ATR'], 4)
        daily_change = round(((latest['Close'] - prev_close) / prev_close) * 100, 2)
        gauge_score = 100 - rsi
        
        if rsi < 35:
            action = "🟩 STRONG BUY"
            sl = round(current_price - (2 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price - (2 * atr), 4)
            tp = round(current_price + (4 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price + (4 * atr), 4)
            reason = f"Aset jenuh jual kritis (RSI: {rsi}). Tekanan beli besar siap masuk."
        elif rsi > 65:
            action = "🟥 STRONG SELL"
            sl = round(current_price + (2 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price + (2 * atr), 4)
            tp = round(current_price - (4 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price - (4 * atr), 4)
            reason = f"Aset jenuh beli berlebih (RSI: {rsi}). Bersiap untuk koreksi turun."
        else:
            action = "🟨 NEUTRAL / WAIT"
            sl, tp = 0.0, 0.0
            reason = f"Pasar seimbang (RSI: {rsi}). Struktur harga membentuk sideways."
            
        signals_data.append({"Asset": pair_name, "Price": current_price, "RSI": rsi, "ATR": atr, "Action": action, "SL": sl, "TP": tp, "Reason": reason, "Score": gauge_score, "Change": daily_change})
        
df_signals = pd.DataFrame(signals_data)

# TAMPILAN UTAMA FOREX
st.write(f"### 🌡️ Alat Ukur Sentimen Pasar ({timeframe_label})")
if not df_signals.empty:
    gauge_cols = st.columns(len(df_signals))
    for index, row in df_signals.iterrows():
        with gauge_cols[index]:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number", value = row["Score"], domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': f"<b>{row['Asset']}</b><br><span style='font-size:0.8em;color:gray'>{row['Action']}</span>", 'font': {'size': 14}},
                gauge = {'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"}, 'bar': {'color': "#00ffcc" if "BUY" in row["Action"] else "#ff3366" if "SELL" in row["Action"] else "#ffcc00"}, 'bgcolor': "#2d2d2d", 'borderwidth': 2, 'bordercolor': "gray",
                         'steps': [{'range': [0, 35], 'color': 'rgba(255, 51, 102, 0.3)'}, {'range': [35, 65], 'color': 'rgba(255, 204, 0, 0.2)'}, {'range': [65, 100], 'color': 'rgba(0, 255, 204, 0.3)'}]}
            ))
            fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark")
            st.plotly_chart(fig_gauge, use_container_width=True)
            
    st.markdown("---")
    st.write("### 📊 Peta Kekuatan Momentum Aset (Daily Performance Heatmap)")
    heatmap_cols = st.columns(len(df_signals))
    for index, row in df_signals.iterrows():
        with heatmap_cols[index]:
            color_box = "#00cc99" if row["Change"] >= 0 else "#ff3366"
            sign = "+" if row["Change"] >= 0 else ""
            st.markdown(f"<div style='background-color:{color_box}; padding:15px; border-radius:8px; text-align:center; color:white; font-weight:bold;'><div>{row['Asset']}</div><div style='font-size:22px; margin-top:5px;'>{sign}{row['Change']}%</div></div>", unsafe_allow_html=True)
            
    st.markdown("---")
    st.write("### 🧠 Ruang Analisis Taktis & Alasan Posisi")
    selected_asset = st.selectbox("Pilih Aset untuk Analisis Visual Mendalam:", list(pairs_mapping.keys()))
    
    asset_info = df_signals[df_signals["Asset"] == selected_asset].iloc[0]
    df_chart = all_charts_data[selected_asset]
    
    left_col, right_col = st.columns([2, 1])
    with left_col:
        fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], increasing_line_color='#00ffcc', decreasing_line_color='#ff3366', name='Candle')])
        fig.update_layout(title=f"Grafik Candlestick Premium - {selected_asset}", xaxis_rangeslider_visible=False, height=450, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
    with right_col:
        risk_amount = (account_balance * risk_percentage) / 100
        if "WAIT" not in asset_info["Action"]:
            pips_to_sl = abs(asset_info["Price"] - asset_info["SL"])
            calculated_lot = risk_amount / (pips_to_sl * (100 if "XAU" in asset_info["Asset"] else 10000)) if pips_to_sl > 0 else 0.01
            lot_output = f"`{round(max(calculated_lot, 0.01), 2)} Standard Lot`"
            risk_money_output = f"`${round(risk_amount, 2)}`"
        else:
            lot_output = "*Tidak ada posisi aktif*"
            risk_money_output = "*Tidak ada risiko*"
            
        st.markdown(f"""
        <div class='trading-card'>
            <h3 style='margin-top:0;'>📋 Dokumen Analisis {selected_asset}</h3>
            <p><b>Harga Running:</b> <span style='color: #00ffcc;'>{asset_info['Price']}</span></p>
            <p><b>Nilai Kekuatan RSI:</b> <span style='color: #ffcc00;'>{asset_info['RSI']}</span></p>
            <p><b>Volatilitas (ATR):</b> {asset_info['ATR']}</p>
            <hr style='border-color:#2d2d2d;'>
            <h4 style='color:#00ffcc;'>💡 Alasan Algoritma:</h4>
            <p>{asset_info['Reason']}</p>
            <hr style='border-color:#2d2d2d;'>
            <h4 style='color:#ffcc00;'>🛡️ Manajemen Resiko:</h4>
            <p><b>Uang Diresikoan:</b> {risk_money_output}</p>
            <p><b>Volume Posisi:</b> <span style='color: #00ffcc;'>{lot_output}</span></p>
        </div>
        """, unsafe_allow_html=True)
        if "WAIT" not in asset_info["Action"]:
            st.write("")
            st.success(f"🎯 **Target TP:** `{asset_info['TP']}`")
            st.error(f"🛡️ **Batas SL:** `{asset_info['SL']}`")
            
st.markdown("---")
st.write("### 📜 Jurnal Historis Performa Algoritma")
mock_history = pd.DataFrame([
    {"Waktu Close": "Hari Ini, 05:30", "Aset": "XAU/USD (Gold)", "Tipe": "BUY", "Harga Entry": 2340.20, "Harga Close": 2355.80, "Hasil": "🟩 HIT TAKE PROFIT (+15.60)"},
    {"Waktu Close": "Kemarin, 21:15", "Aset": "EUR/USD", "Tipe": "SELL", "Harga Entry": 1.0850, "Harga Close": 1.0892, "Hasil": "🟥 HIT STOP LOSS (-0.0042)"}
])
st.dataframe(mock_history, use_container_width=True)
st.markdown("<div class='ticker-wrap'><div class='ticker'>⚠️ BREAKING NEWS: Investor bersiap menghadapi rilis data inflasi AS malam ini --- 📈 Ketegangan geopolitik memicu kenaikan Emas (XAUUSD) ke level baru.</div></div>", unsafe_allow_html=True)
