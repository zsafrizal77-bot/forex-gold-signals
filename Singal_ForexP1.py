import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. Konfigurasi Halaman Dashboard (Alpha Terminal Theme)
st.set_page_config(page_title="Alpha Intelligence Forex Dashboard", layout="wide")

# CSS Kustom untuk efek Glow, Animasi Berkedip, dan Desain Kartu
st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    .live-dot { height: 10px; width: 10px; background-color: #00ffcc; border-radius: 50%; display: inline-block; animation: blink 1.5s infinite; box-shadow: 0 0 8px #00ffcc; }
    .trading-card { border: 1px solid #2d2d2d; padding: 15px; border-radius: 12px; background-color: #111111; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    </style>
    """, unsafe_allow_html=True)

# Header Utama Terminal
current_time = datetime.now().strftime("%H:%M:%S WIB")
st.title("🦅 Alpha Intelligence Forex & Gold Terminal")
st.markdown(f"Status Sistem: <span class='live-dot'></span> **LIVE STREAM FEED ACTIVE** | Pembaruan Terakhir: `{current_time}`", unsafe_allow_html=True)
st.markdown("---")

# --- SIDEBAR PENGATURAN & KALKULATOR RISIKO ---
st.sidebar.header("⚙️ Terminal Controller")
timeframe_label = st.sidebar.selectbox(
    "Pilih Timeframe Analisis:",
    ["15 Menit (Scalping)", "1 Jam (Intraday)", "1 Hari (Swing)"]
)

st.sidebar.markdown("---")
st.sidebar.header("🧮 Kalkulator Manajemen Risiko")
st.sidebar.caption("Hitung lot aman sebelum melakukan open posisi berdasarkan sinyal aktif.")
account_balance = st.sidebar.number_input("Modal Akun Anda ($):", min_value=10, value=1000, step=100)
risk_percentage = st.sidebar.slider("Toleransi Risiko Per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)

tf_mapping = {
    "15 Menit (Scalping)": {"interval": "15m", "period": "5d"},
    "1 Jam (Intraday)": {"interval": "1h", "period": "7d"},
    "1 Hari (Swing)": {"interval": "1d", "period": "60d"}
}

selected_interval = tf_mapping[timeframe_label]["interval"]
selected_period = tf_mapping[timeframe_label]["period"]

# Fungsi Perhitungan Matematis Indikator
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, window=14):
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

@st.cache_data(ttl=15)
def get_market_data(ticker, period, interval):
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if not df.empty:
        df['RSI'] = calculate_rsi(df['Close'], window=14)
        df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'], window=14)
    return df

pairs_mapping = {
    'XAU/USD (Gold)': 'GC=F',
    'EUR/USD': 'EURUSD=X',
    'GBP/USD': 'GBPUSD=X',
    'USD/JPY': 'JPY=X',
    'AUD/USD': 'AUDUSD=X'
}

signals_data = []
all_charts_data = {}

with st.spinner('🔮 Mensinkronisasi dengan satelit pasar global...'):
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
        
        # Hitung persentase perubahan harian untuk Heatmap kekuatan mata uang
        daily_change = round(((latest['Close'] - prev_close) / prev_close) * 100, 2)
        
        gauge_score = 100 - rsi 
        
        if rsi < 35:
            action = "🟩 STRONG BUY"
            sl = round(current_price - (2 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price - (2 * atr), 4)
            tp = round(current_price + (4 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price + (4 * atr), 4)
            reason = f"Aset berada di area jenuh jual kritis (**RSI: {rsi}**). Volume penjualan habis, tekanan beli besar siap masuk."
        elif rsi > 65:
            action = "🟥 STRONG SELL"
            sl = round(current_price + (2 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price + (2 * atr), 4)
            tp = round(current_price - (4 * atr), 2) if 'XAU' in pair_name or 'JPY' in pair_name else round(current_price - (4 * atr), 4)
            reason = f"Aset mengalami kenaikan berlebih (**RSI: {rsi}**). Pembeli mulai mengambil profit, bersiap untuk koreksi turun."
        else:
            action = "🟨 NEUTRAL / WAIT"
            sl, tp = 0.0, 0.0
            reason = f"Pasar dalam kondisi seimbang (**RSI: {rsi}**). Struktur harga membentuk sideways, minim volatilitas."
            
        signals_data.append({
            "Asset": pair_name, "Price": current_price, "RSI": rsi, "ATR": atr,
            "Action": action, "SL": sl, "TP": tp, "Reason": reason, "Score": gauge_score, "Change": daily_change
        })

df_signals = pd.DataFrame(signals_data)

# 2. SEKTOR SPEEDOMETER SENTIMEN PASAR
st.write(f"### 🌡️ Alat Ukur Sentimen Pasar ({timeframe_label})")
gauge_cols = st.columns(len(df_signals))

for index, row in df_signals.iterrows():
    with gauge_cols[index]:
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = row["Score"],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"<b>{row['Asset']}</b><br><span style='font-size:0.8em;color:gray'>{row['Action']}</span>", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#00ffcc" if "BUY" in row["Action"] else "#ff3366" if "SELL" in row["Action"] else "#ffcc00"},
                'bgcolor': "#2d2d2d",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 35], 'color': 'rgba(255, 51, 102, 0.3)'},
                    {'range': [35, 65], 'color': 'rgba(255, 204, 0, 0.2)'},
                    {'range': [65, 100], 'color': 'rgba(0, 255, 204, 0.3)'}
                ],
            }
        ))
        fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark")
        st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")

# 3. FITUR BARU: CURRENCY STRENGTH HEATMAP (Peta Kekuatan Pasar Hari Ini)
st.write("### 📊 Peta Kekuatan Momentum Aset (Daily Performance Heatmap)")
heatmap_cols = st.columns(len(df_signals))
for index, row in df_signals.iterrows():
    with heatmap_cols[index]:
        color_box = "#00cc99" if row["Change"] >= 0 else "#ff3366"
        sign = "+" if row["Change"] >= 0 else ""
        st.markdown(f"""
        <div style='background-color:{color_box}; padding:15px; border-radius:8px; text-align:center; color:white; font-weight:bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
            <div style='font-size:14px; opacity:0.9;'>{row['Asset']}</div>
            <div style='font-size:22px; margin-top:5px;'>{sign}{row['Change']}%</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 4. RUANG ANALISIS TAKTIS, GRAFIK CANDLESTICK & RISK CALCULATOR OUTPUT
st.write("### 🧠 Ruang Analisis Taktis & Alasan Posisi")
selected_asset = st.selectbox("Pilih Aset untuk Analisis Visual Mendalam:", list(pairs_mapping.keys()))

asset_info = df_signals[df_signals["Asset"] == selected_asset].iloc[0]
df_chart = all_charts_data[selected_asset]

left_col, right_col = st.columns([2, 1])

with left_col:
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'],
        increasing_line_color='#00ffcc', decreasing_line_color='#ff3366', name='Candle'
    )])
    fig.update_layout(
        title=f"Grafik Candlestick Premium - {selected_asset}",
        xaxis_rangeslider_visible=False, height=450, template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

with right_col:
    # Perhitungan Live dari Sektor Kalkulator Risiko di Sidebar
    risk_amount = (account_balance * risk_percentage) / 100
    
    if "WAIT" not in asset_info["Action"]:
        # Hitung jarak pips/poin dari entry ke SL untuk menentukan ukuran Lot aman
        pips_to_sl = abs(asset_info["Price"] - asset_info["SL"])
        if "XAU" in asset_info["Asset"]:
            # Perhitungan khusus emas (Gold standar leverage kontrak)
            calculated_lot = risk_amount / (pips_to_sl * 100) if pips_to_sl > 0 else 0.01
        else:
            # Perhitungan pasang mata uang forex biasa
            calculated_lot = risk_amount / (pips_to_sl * 10000) if pips_to_sl > 0 else 0.01
        lot_output = f"`{round(max(calculated_lot, 0.01), 2)} Standard Lot`"
        risk_money_output = f"`${round(risk_amount, 2)}`"
    else:
        lot_output = "*Tidak ada posisi aktif*"
        risk_money_output = "*Tidak ada risiko*"

    # Tampilan Kartu Informasi Finansial
    st.markdown(f"""
    <div class='trading-card' style='color: #ffffff; background-color: #161616; padding: 20px; border-radius: 12px; border: 1px solid #2d2d2d;'>
        <h3 style='margin-top:0; color: #ffffff;'>📋 Dokumen Analisis {selected_asset}</h3>
        <p style='color: #e0e0e0; margin-bottom: 8px;'><b>Harga Running:</b> <span style='color: #00ffcc; font-weight: bold;'>{asset_info['Price']}</span></p>
        <p style='color: #e0e0e0; margin-bottom: 8px;'><b>Nilai Kekuatan RSI:</b> <span style='color: #ffcc00;'>{asset_info['RSI']}</span></p>
        <p style='color: #e0e0e0; margin-bottom: 8px;'><b>Volatilitas Pasar (ATR):</b> {asset_info['ATR']}</p>
        <hr style='border-color:#2d2d2d; margin: 15px 0;'>
        <h4 style='color:#00ffcc; margin-bottom: 10px;'>💡 Alasan Algoritma:</h4>
        <p style='font-size:14px; color: #f0f0f0; line-height: 1.5;'>{asset_info['Reason']}</p>
        <hr style='border-color:#2d2d2d; margin: 15px 0;'>
        <h4 style='color:#ffcc00; margin-bottom: 10px;'>🛡️ Manajemen Resiko Rekomendasi:</h4>
        <p style='color: #e0e0e0; margin-bottom: 6px;'><b>Uang yang Diresikoan:</b> {risk_money_output}</p>
        <p style='color: #e0e0e0;'><b>Ukuran Volume Posisi:</b> <span style='color: #00ffcc; font-weight: bold;'>{lot_output}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if "WAIT" not in asset_info["Action"]:
        st.success(f"🎯 **Target Ambil Untung (Take Profit):** `{asset_info['TP']}`")
        st.error(f"🛡️ **Batas Toleransi Risiko (Stop Loss):** `{asset_info['SL']}`")
    else:
        st.info("⚡ *Sistem menyarankan mode pemantauan saja (No Action Required).*")
