"""
BIST 100 Technical Analysis Dashboard
======================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BIST 100 | Technical Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Full BIST 100 ticker list (Yahoo Finance format: TICKER.IS)
BIST100_TICKERS = {
    "THYAO": "Türk Hava Yolları", "EREGL": "Ereğli Demir Çelik",
    "AKBNK": "Akbank", "GARAN": "Garanti Bankası", "ISCTR": "İş Bankası C",
    "YKBNK": "Yapı Kredi Bankası", "HALKB": "Halkbank", "VAKBN": "Vakıfbank",
    "KRDMD": "Kardemir D", "SISE":  "Şişe Cam", "TOASO": "Tofaş Oto",
    "FROTO": "Ford Otosan", "ARCLK": "Arçelik", "BIMAS": "BİM Mağazalar",
    "MGROS": "Migros", "SODA":  "Soda Sanayii", "TUPRS": "Tüpraş",
    "PETKM": "Petkim", "AEFES": "Anadolu Efes", "SAHOL": "Sabancı Holding",
    "KCHOL": "Koç Holding", "EKGYO": "Emlak Konut GYO", "ENKAI": "Enka İnşaat",
    "CCOLA": "Coca-Cola İçecek", "DOHOL": "Doğan Holding", "TTKOM": "Türk Telekom",
    "TCELL": "Turkcell", "ASELS": "Aselsan", "OTKAR": "Otokar",
    "PGSUS": "Pegasus", "LOGO":  "Logo Yazılım", "NETAS": "Netaş Telekomünikasyon",
    "HEKTS": "Hektaş", "KLNMA": "Türkiye Kalkınma Bankası", "KOZAL": "Koza Altın",
    "KOZAA": "Koza Anadolu Metal", "IPEKE": "İpek Doğal Enerji", "ZOREN": "Zorlu Enerji",
    "AKSEN": "Aksa Enerji", "AKENR": "Ak Enerji", "BRISA": "Brisa",
    "CEMTS": "Çemtaş", "CIMSA": "Çimsa", "ADANA": "Adana Çimento A",
    "AKCNS": "Akçansa", "BOLUC": "Bolu Çimento", "FMIZP": "Ereğli Demir F",
    "GOODY": "Goodyear", "KARSN": "Karsan", "ALARK": "Alarko Holding",
    "ALCTL": "Alcatel Lucent Teletaş", "ALGYO": "Alarko GYO", "ALYAG": "Alternatif Yatırım",
    "ANACM": "Anadolu Cam", "ANHYT": "Anadolu Hayat Emeklilik", "ANSGR": "Anadolu Sigorta",
    "ATAGY": "Ata GYO", "AYCES": "Altın Yunus", "BAGFS": "Bagfaş",
    "BANVT": "Bandırma Vitaminli", "BJKAS": "Beşiktaş Futbol", "BRYAT": "Borusan Birleşik",
    "BUCIM": "Bursa Çimento", "CLEBI": "Çelebi Hava Servisi", "CRDFA": "Creditwest Faktoring",
    "CVKMD": "Çukurova Holding", "DESAS": "Desa Deri", "DEVA":  "Deva Holding",
    "DGZTE": "Doğan Gazetecilik", "DMSAS": "Demisaş", "DYOBY": "DYO Boya",
    "ECZYT": "Eczacıbaşı Yatırım", "EGEEN": "Ege Endüstri", "EGSER": "Ege Seramik",
    "EMKEL": "Emkel", "EPLAS": "Egeplast", "ESCOM": "Escort Teknoloji",
    "FENER": "Fenerbahçe Futbol", "FLAP":  "Flap Kongre", "GENTS": "Gentaş",
    "GOLTS": "Göltaş Çimento", "GRSEL": "Güres Turizm", "GUBRF": "Gübre Fabrikaları",
    "GWIND": "Galata Wind", "HATEK": "Hateks", "INDES": "İndeks Bilgisayar",
    "INTEM": "İntem Bilgisayar", "ITTFH": "İttifak Holding", "IZOCM": "İzocam",
    "JANTS": "Jantsa", "KAREL": "Karel Elektronik", "KATMR": "Katmerciler",
    "KERVT": "Kerevitaş", "KNFRT": "Konfrut", "KONYA": "Konya Çimento",
    "KORDS": "Kordsa", "KUTPO": "Kütahya Porselen", "LINK":  "Link Bilgisayar",
    "LKMNH": "Lokman Hekim", "MAVI":  "Mavi Giyim", "MBNKP": "Merkez Bankası",
    "MNDRS": "Menderes Tekstil", "MPACT": "Mondi", "MPARK": "MLP Sağlık",
    "NTHOL": "Net Holding", "ODAS":  "Odaş Elektrik", "OYAKC": "Oyak Çimento",
    "PARSN": "Parsan", "POLHO": "Polisan Holding", "PRKME": "Park Elektrik",
    "SELEC": "Selçuk Ecza",
}

FREQ_OPTIONS = {
    "1 Hour":  {"period": "60d",  "interval": "1h"},
    "1 Day":   {"period": "2y",   "interval": "1d"},
    "1 Week":  {"period": "5y",   "interval": "1wk"},
}

SIGNAL_COLORS = {
    "Strong Buy":  "#00C853", "Buy": "#69F0AE", "Hold": "#FFD740",
    "Sell": "#FF6D00", "Strong Sell": "#D50000",
}

SIGNAL_EMOJI = {
    "Strong Buy":  "🟢", "Buy": "🟩", "Hold": "🟡",
    "Sell": "🟧", "Strong Sell": "🔴",
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA & INDICATORS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Download OHLCV from Yahoo Finance using a custom session to prevent blocks."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    try:
        df = yf.download(
            f"{ticker}.IS",
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            session=session
        )
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        df = df.dropna(subset=["close"])
        return df
    except Exception:
        return pd.DataFrame()

def compute_indicators(df: pd.DataFrame, macd_fast=12, macd_slow=26, macd_sig=9,
                       rsi_len=14, mom_len=10, cci_len=20, stoch_k=14, stoch_d=3,
                       willr_len=14) -> dict:
    """Compute all 6 indicators using pure Pandas to avoid Numba/C-compiler crashes."""
    if len(df) < 30:
        return {}
    
    ind = {}
    close = df["close"]
    high = df["high"]
    low = df["low"]

    try:
        # MACD
        ema_fast = close.ewm(span=macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=macd_sig, adjust=False).mean()
        macd_hist = macd_line - signal_line
        # Keep dict keys matched to old code to prevent scoring logic from breaking
        ind["macd"] = pd.DataFrame({
            "MACD_12_26_9": macd_line, 
            "MACDs_12_26_9": signal_line, 
            "MACDh_12_26_9": macd_hist
        })

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/rsi_len, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/rsi_len, adjust=False).mean()
        rs = gain / loss
        ind["rsi"] = 100 - (100 / (1 + rs))

        # MOM
        ind["mom"] = close.diff(mom_len)

        # CCI
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(cci_len).mean()
        mad = tp.rolling(cci_len).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
        ind["cci"] = (tp - sma_tp) / (0.015 * mad)

        # STOCHASTIC
        l_k = low.rolling(stoch_k).min()
        h_k = high.rolling(stoch_k).max()
        k = 100 * (close - l_k) / (h_k - l_k)
        d = k.rolling(stoch_d).mean()
        ind["stoch"] = pd.DataFrame({
            "STOCHk_14_3_3": k, 
            "STOCHd_14_3_3": d
        })

        # WILLIAMS %R
        l_w = low.rolling(willr_len).min()
        h_w = high.rolling(willr_len).max()
        ind["willr"] = -100 * (h_w - close) / (h_w - l_w)

    except Exception:
        return {}
        
    return ind

# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _score_rsi(val: float) -> int:
    if pd.isna(val): return 0
    if val >= 70:  return -2
    if val >= 60:  return -1
    if val <= 30:  return  2
    if val <= 40:  return  1
    return 0

def _score_macd(macd_val, signal_val, hist_val) -> int:
    if any(pd.isna(x) for x in [macd_val, signal_val, hist_val]): return 0
    score = 0
    score += 1 if macd_val > signal_val else -1
    score += 1 if hist_val > 0 else -1
    return max(-2, min(2, score))

def _score_cci(val: float) -> int:
    if pd.isna(val): return 0
    if val >= 200:  return  2
    if val >= 100:  return  1
    if val <= -200: return -2
    if val <= -100: return -1
    return 0

def _score_mom(val: float) -> int:
    if pd.isna(val): return 0
    if val >  2: return  2
    if val >  0: return  1
    if val < -2: return -2
    return -1

def _score_stoch(k: float, d: float) -> int:
    if any(pd.isna(x) for x in [k, d]): return 0
    if k < 20 and d < 20: return  2
    if k > 80 and d > 80: return -2
    if k < 20:            return  1
    if k > 80:            return -1
    return 1 if k > d else -1

def _score_willr(val: float) -> int:
    if pd.isna(val): return 0
    if val <= -80:  return  2
    if val <= -50:  return  1
    if val >= -20:  return -2
    return -1

def _label(total: int) -> str:
    if total >=  6: return "Strong Buy"
    if total >=  2: return "Buy"
    if total <= -6: return "Strong Sell"
    if total <= -2: return "Sell"
    return "Hold"

def compute_signal(ind: dict) -> dict:
    if not ind:
        return {"signal": "N/A", "score": 0, "details": {}}

    macd_df = ind["macd"]
    stoch_df = ind["stoch"]

    s_macd  = _score_macd(
        macd_df["MACD_12_26_9"].iloc[-1],
        macd_df["MACDs_12_26_9"].iloc[-1],
        macd_df["MACDh_12_26_9"].iloc[-1],
    )
    s_rsi   = _score_rsi(ind["rsi"].iloc[-1])
    s_mom   = _score_mom(ind["mom"].iloc[-1])
    s_cci   = _score_cci(ind["cci"].iloc[-1])
    s_stoch = _score_stoch(
        stoch_df["STOCHk_14_3_3"].iloc[-1],
        stoch_df["STOCHd_14_3_3"].iloc[-1],
    )
    s_willr = _score_willr(ind["willr"].iloc[-1])

    total = s_rsi + s_macd + s_cci + s_mom + s_stoch + s_willr

    return {
        "signal": _label(total),
        "score":  total,
        "details": {
            "RSI":       (s_rsi,   round(ind["rsi"].iloc[-1], 2)),
            "MACD":      (s_macd,  round(macd_df["MACD_12_26_9"].iloc[-1], 4)),
            "CCI":       (s_cci,   round(ind["cci"].iloc[-1], 2)),
            "Momentum":  (s_mom,   round(ind["mom"].iloc[-1], 4)),
            "Stochastic":(s_stoch, round(stoch_df["STOCHk_14_3_3"].iloc[-1], 2)),
            "Williams%R":(s_willr, round(ind["willr"].iloc[-1], 2)),
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def build_charts(df: pd.DataFrame, ind: dict, ticker: str, name: str) -> go.Figure:
    fig = make_subplots(
        rows=7, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2],
        subplot_titles=[
            f"{ticker} – {name}",
            "MACD", "RSI", "Momentum", "CCI", "Stochastic", "Williams %R"
        ],
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#26A69A", decreasing_line_color="#EF5350",
        showlegend=False, name="Price",
    ), row=1, col=1)

    macd_df = ind["macd"]
    hist    = macd_df["MACDh_12_26_9"]
    colors  = ["#26A69A" if v >= 0 else "#EF5350" for v in hist]
    fig.add_trace(go.Bar(
        x=df.index, y=hist, marker_color=colors, name="MACD Hist", showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_df["MACD_12_26_9"], line=dict(color="#2962FF", width=1.2), name="MACD",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_df["MACDs_12_26_9"], line=dict(color="#FF6D00", width=1.2, dash="dot"), name="Signal",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=ind["rsi"], line=dict(color="#AB47BC", width=1.5), name="RSI", showlegend=False,
    ), row=3, col=1)
    for lvl, color in [(70, "rgba(239,83,80,0.3)"), (30, "rgba(38,166,154,0.3)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=color, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="grey", line_width=0.7, row=3, col=1)

    mom = ind["mom"]
    mom_colors = ["#26A69A" if v >= 0 else "#EF5350" for v in mom]
    fig.add_trace(go.Bar(
        x=df.index, y=mom, marker_color=mom_colors, name="Momentum", showlegend=False,
    ), row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="grey", line_width=0.7, row=4, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=ind["cci"], line=dict(color="#FFA726", width=1.5), name="CCI", showlegend=False,
    ), row=5, col=1)
    for lvl, color in [(100, "rgba(239,83,80,0.3)"), (-100, "rgba(38,166,154,0.3)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=color, row=5, col=1)

    stoch_df = ind["stoch"]
    fig.add_trace(go.Scatter(
        x=df.index, y=stoch_df["STOCHk_14_3_3"], line=dict(color="#42A5F5", width=1.5), name="%K",
    ), row=6, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=stoch_df["STOCHd_14_3_3"], line=dict(color="#EF5350", width=1.2, dash="dot"), name="%D",
    ), row=6, col=1)
    for lvl, color in [(80, "rgba(239,83,80,0.3)"), (20, "rgba(38,166,154,0.3)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=color, row=6, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=ind["willr"], line=dict(color="#EC407A", width=1.5), name="Williams %R", showlegend=False,
    ), row=7, col=1)
    for lvl, color in [(-20, "rgba(239,83,80,0.3)"), (-80, "rgba(38,166,154,0.3)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=color, row=7, col=1)

    fig.update_layout(
        height=1050, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        font=dict(color="#FAFAFA", family="Inter, sans-serif", size=11),
        xaxis_rangeslider_visible=False, margin=dict(l=50, r=20, t=40, b=20),
        legend=dict(orientation="h", x=0, y=1.01, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hovermode="x unified",
    )
    for i in range(1, 8):
        fig.update_xaxes(showgrid=True, gridcolor="#1E2130", gridwidth=0.5, zeroline=False, row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#1E2130", gridwidth=0.5, zeroline=False, row=i, col=1)

    return fig

# ─────────────────────────────────────────────────────────────────────────────
# CSS & UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-header { background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%); border-bottom: 1px solid #2d3748; padding: 1.2rem 2rem; margin: -1rem -1rem 1.5rem -1rem; }
.main-header h1 { margin: 0; font-size: 1.6rem; font-weight: 700; background: linear-gradient(90deg, #63b3ed, #68d391); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.main-header p  { margin: 0.2rem 0 0 0; color: #718096; font-size: 0.82rem; }
.signal-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.03em; }
.signal-strong-buy  { background: #003d1f; color: #00C853; border: 1px solid #00C853; }
.signal-buy         { background: #1a3a2a; color: #69F0AE; border: 1px solid #69F0AE; }
.signal-hold        { background: #3a3000; color: #FFD740; border: 1px solid #FFD740; }
.signal-sell        { background: #3a1a00; color: #FF6D00; border: 1px solid #FF6D00; }
.signal-strong-sell { background: #3a0000; color: #FF5252; border: 1px solid #FF5252; }
.metric-card { background: #161b2e; border: 1px solid #2d3748; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }
.metric-card .label { font-size: 0.72rem; color: #718096; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
.metric-card .value { font-size: 1.4rem; font-weight: 700; }
.metric-card .score-sub { font-size: 0.78rem; color: #718096; margin-top: 0.15rem; }
.score-bar-container { margin: 0.3rem 0; }
.score-bar-label { font-size: 0.75rem; color: #a0aec0; width: 90px; display: inline-block; }
.score-bar { display: inline-block; height: 8px; border-radius: 4px; vertical-align: middle; }
.footer { text-align: center; color: #4a5568; font-size: 0.75rem; padding: 1.5rem 0; border-top: 1px solid #1a202c; margin-top: 2rem; }
</style>
"""

def signal_badge_html(signal: str) -> str:
    css_class = {
        "Strong Buy": "signal-strong-buy", "Buy": "signal-buy",
        "Hold": "signal-hold", "Sell": "signal-sell",
        "Strong Sell": "signal-strong-sell", "N/A": "signal-hold",
    }.get(signal, "signal-hold")
    emoji = SIGNAL_EMOJI.get(signal, "⚪")
    return f'<span class="signal-badge {css_class}">{emoji} {signal}</span>'

def score_to_bar(score: int) -> str:
    colors = {-2: "#EF5350", -1: "#FF8A65", 0: "#FFD740", 1: "#66BB6A", 2: "#26A69A"}
    labels = {-2: "−2", -1: "−1", 0: " 0", 1: "+1", 2: "+2"}
    width  = abs(score) * 20 + 10
    color  = colors.get(score, "#FFD740")
    return f'<div class="score-bar-container"><span class="score-bar" style="width:{width}px; background:{color};"></span> <small style="color:{color}; font-weight:600;">{labels.get(score, "0")}</small></div>'

def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        freq = st.selectbox("Timeframe", list(FREQ_OPTIONS.keys()), index=1, help="All data updates when you change this.")
        st.markdown("---")
        st.markdown("### Indicator Parameters")
        with st.expander("Customize", expanded=False):
            rsi_len   = st.slider("RSI Period",      7, 30, 14)
            macd_fast = st.slider("MACD Fast",       5, 20, 12)
            macd_slow = st.slider("MACD Slow",      15, 50, 26)
            macd_sig  = st.slider("MACD Signal",     3, 15,  9)
            cci_len   = st.slider("CCI Period",     10, 50, 20)
            mom_len   = st.slider("Momentum Period", 5, 30, 10)
            stoch_k   = st.slider("Stoch %K",        5, 30, 14)
            stoch_d   = st.slider("Stoch %D",        2, 10,  3)
            willr_len = st.slider("Williams %R",     5, 30, 14)
        st.markdown("---")
        st.markdown("### Stock Subset")
        all_stocks = list(BIST100_TICKERS.keys())
        selected_subset = st.multiselect(
            "Filter stocks (empty = all)",
            options=all_stocks,
            default=["THYAO", "EREGL", "AKBNK", "GARAN", "TUPRS"],
            help="Select specific stocks to show in Page 1, or leave empty for all.",
        )
        st.markdown("---")
        st.caption(f"Data cached for 1 hour • Last refresh: {datetime.now().strftime('%H:%M')}")

    params = {
        "freq": freq, "period": FREQ_OPTIONS[freq]["period"], "interval": FREQ_OPTIONS[freq]["interval"],
        "rsi_len": rsi_len, "macd_fast": macd_fast, "macd_slow": macd_slow, "macd_sig": macd_sig,
        "cci_len": cci_len, "mom_len": mom_len, "stoch_k": stoch_k, "stoch_d": stoch_d,
        "willr_len": willr_len, "subset": selected_subset if selected_subset else all_stocks,
    }
    return params

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 – SCREENING TABLE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def build_screening_table(tickers_tuple, period, interval,
                           rsi_len, macd_fast, macd_slow, macd_sig,
                           cci_len, mom_len, stoch_k, stoch_d, willr_len):
    rows = []
    for ticker in list(tickers_tuple):
        df = fetch_data(ticker, period, interval)
        if df.empty or len(df) < 30:
            continue

        ind = compute_indicators(
            df, macd_fast, macd_slow, macd_sig, rsi_len, 
            mom_len, cci_len, stoch_k, stoch_d, willr_len
        )
        if not ind:
            continue

        sig   = compute_signal(ind)
        price = df["close"].iloc[-1]
        chg   = ((df["close"].iloc[-1] / df["close"].iloc[-2]) - 1) * 100 if len(df) > 1 else 0

        row = {
            "Ticker":  ticker, "Name": BIST100_TICKERS.get(ticker, ""),
            "Price":   round(price, 2), "Change%": round(chg, 2),
            "Signal":  sig["signal"], "Score":   sig["score"],
        }
        for ind_name, (score, _) in sig["details"].items():
            row[ind_name] = score
        rows.append(row)

    return pd.DataFrame(rows)

def render_page1(params):
    st.markdown("## 📋 Market Screener — BIST Stocks")
    st.markdown(f"Showing **{len(params['subset'])} stocks** • Timeframe: **{params['freq']}** • Signals based on 6 indicators (max score ±12)")

    progress = st.progress(0, text="Loading market data...")
    with st.spinner(""):
        df_all = build_screening_table(
            tuple(params["subset"]), params["period"], params["interval"],
            params["rsi_len"], params["macd_fast"], params["macd_slow"],
            params["macd_sig"], params["cci_len"], params["mom_len"],
            params["stoch_k"], params["stoch_d"], params["willr_len"],
        )
    progress.empty()

    if df_all.empty:
        st.warning("No data returned. Check your internet connection or try again.")
        return

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1: sig_filter = st.multiselect("Filter by Signal", ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"], default=[])
    with col2: sort_by = st.selectbox("Sort by", ["Score", "Change%", "Ticker", "Price"])
    with col3: ascending = st.radio("Order", ["Descending", "Ascending"], horizontal=True) == "Ascending"

    display_df = df_all.copy()
    if sig_filter: display_df = display_df[display_df["Signal"].isin(sig_filter)]
    display_df = display_df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

    counts = df_all["Signal"].value_counts()
    badge_cols = st.columns(5)
    for i, sig in enumerate(["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]):
        with badge_cols[i]:
            cnt = counts.get(sig, 0)
            st.markdown(f'<div class="metric-card"><div class="label">{sig}</div><div class="value" style="color:{SIGNAL_COLORS[sig]}">{cnt}</div><div class="score-sub">{round(cnt/len(df_all)*100)}%</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    ind_cols = ["RSI", "MACD", "CCI", "Momentum", "Stochastic", "Williams%R"]
    headers  = ["Ticker", "Name", "Price (₺)", "Chg %", "Signal", "Score"] + ind_cols

    header_html = "<table style='width:100%; border-collapse:collapse; font-size:0.83rem;'><thead><tr style='border-bottom:2px solid #2d3748; color:#718096;'>"
    for h in headers: header_html += f"<th style='padding:0.5rem 0.6rem; text-align:left;'>{h}</th>"
    header_html += "</tr></thead><tbody>"

    for _, row in display_df.iterrows():
        price_str = f"{row['Price']:,.2f}" if pd.notna(row["Price"]) else "—"
        chg_val   = row["Change%"]
        chg_color = "#26A69A" if pd.notna(chg_val) and chg_val >= 0 else "#EF5350"
        chg_str   = f"{chg_val:+.2f}%" if pd.notna(chg_val) else "—"

        header_html += f"<tr style='border-bottom:1px solid #1a202c;'><td style='padding:0.45rem 0.6rem; font-weight:600; color:#63b3ed;'>{row['Ticker']}</td><td style='padding:0.45rem 0.6rem; color:#a0aec0; font-size:0.78rem;'>{row['Name']}</td><td style='padding:0.45rem 0.6rem;'>{price_str}</td><td style='padding:0.45rem 0.6rem; color:{chg_color}; font-weight:600;'>{chg_str}</td><td style='padding:0.45rem 0.6rem;'>{signal_badge_html(row['Signal'])}</td>"
        score_color = "#26A69A" if row["Score"] >= 2 else ("#EF5350" if row["Score"] <= -2 else "#FFD740")
        header_html += f"<td style='padding:0.45rem 0.6rem; font-weight:700; color:{score_color};'>{row['Score']:+d}</td>"
        for ic in ind_cols: header_html += f"<td style='padding:0.45rem 0.6rem;'>{score_to_bar(int(row.get(ic, 0)))}</td>"
        header_html += "</tr>"

    header_html += "</tbody></table>"
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("⬇ Export to CSV", data=display_df.to_csv(index=False), file_name="bist_ta_signals.csv", mime="text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 – SINGLE STOCK DETAIL
# ─────────────────────────────────────────────────────────────────────────────

def render_page2(params):
    st.markdown("## 📈 Stock Detail — Indicators")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        ticker = st.selectbox("Select Stock", options=params["subset"], format_func=lambda t: f"{t} — {BIST100_TICKERS.get(t, '')}")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    if not ticker:
        st.info("Select a stock above.")
        return

    with st.spinner(f"Loading {ticker}..."):
        df = fetch_data(ticker, params["period"], params["interval"])

    if df.empty:
        st.error(f"No data for {ticker}. It may be delisted or temporarily unavailable.")
        return

    ind = compute_indicators(
        df, params["macd_fast"], params["macd_slow"], params["macd_sig"],
        params["rsi_len"], params["mom_len"], params["cci_len"],
        params["stoch_k"], params["stoch_d"], params["willr_len"]
    )
    if not ind:
        st.error("Not enough data points to compute indicators.")
        return

    sig = compute_signal(ind)
    price   = df["close"].iloc[-1]
    chg_pct = ((df["close"].iloc[-1] / df["close"].iloc[-2]) - 1) * 100 if len(df) > 1 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-card"><div class="label">Price</div><div class="value">₺{price:,.2f}</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><div class="label">Change ({params["freq"]})</div><div class="value" style="color:{"#26A69A" if chg_pct >= 0 else "#EF5350"}">{chg_pct:+.2f}%</div></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><div class="label">TA Signal</div><div class="value" style="color:{SIGNAL_COLORS.get(sig["signal"], "#FFD740")}">{sig["signal"]}</div></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-card"><div class="label">Composite Score</div><div class="value" style="color:{SIGNAL_COLORS.get(sig["signal"], "#FFD740")}">{sig["score"]:+d}</div><div class="score-sub">Range: −12 to +12</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("📊 Indicator Score Breakdown", expanded=True):
        bc1, bc2, bc3 = st.columns(3)
        for i, (ind_name, (score, val)) in enumerate(sig["details"].items()):
            score_col = SIGNAL_COLORS.get({2:"Strong Buy",1:"Buy",0:"Hold",-1:"Sell",-2:"Strong Sell"}.get(score,"Hold"), "#FFD740")
            with [bc1, bc2, bc3][i % 3]:
                st.markdown(f'<div class="metric-card"><div class="label">{ind_name}</div><div class="value" style="color:{score_col}">{score:+d}</div><div class="score-sub">Value: {val}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.plotly_chart(build_charts(df, ind, ticker, BIST100_TICKERS.get(ticker, "")), use_container_width=True, config={"displayModeBar": True})

    with st.expander("📄 Raw Data Preview"):
        show_df = df.tail(50).copy()
        show_df.index = show_df.index.strftime("%Y-%m-%d %H:%M" if "h" in params["interval"] else "%Y-%m-%d")
        st.dataframe(show_df.style.format("{:.2f}"), use_container_width=True)

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown('<div class="main-header"><h1>📊 BIST Technical Analysis Dashboard</h1><p>Automated screening & charting • 6 indicators • 5-level signals • Powered by Yahoo Finance</p></div>', unsafe_allow_html=True)
    params = render_sidebar()
    page = st.radio("Navigate", ["📋 Page 1 — Market Screener", "📈 Page 2 — Stock Detail"], horizontal=True, label_visibility="hidden")
    st.markdown("---")
    
    if "Page 1" in page: render_page1(params)
    else: render_page2(params)
    
    st.markdown(f'<div class="footer">Data from Yahoo Finance • Native Pandas Math • Not financial advice • Updated: {datetime.now().strftime("%d %b %Y %H:%M")}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
