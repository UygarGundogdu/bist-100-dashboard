"""
Global Technical Analysis Dashboard  v3
=========================================
Page 1 : Indices + Commodities + Forex + Crypto  (always visible)
Page 2 : Stock Screener  (BIST 100 and/or S&P 500)

Data sources
  BIST 100 constituents : Borsa Istanbul official CSV  (live, daily updated)
                          https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv
                          Fallback: hardcoded list from Investing.com (Jun 2025)
  S&P 500 constituents  : GitHub datasets/s-and-p-500-companies raw CSV  (live)
                          Fallback: hardcoded top-50 list

Run : streamlit run app.py
"""

import time
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import io

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global TA Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ASSET REGISTRIES  (Page 1)
# ─────────────────────────────────────────────────────────────────────────────

INDICES = {
    "BIST 100":      {"ticker": "XU100.IS",  "currency": "₺", "region": "🇹🇷 Turkey"},
    "BIST 30":       {"ticker": "XU030.IS",  "currency": "₺", "region": "🇹🇷 Turkey"},
    "S&P 500":       {"ticker": "^GSPC",     "currency": "$", "region": "🇺🇸 US"},
    "NASDAQ 100":    {"ticker": "^NDX",      "currency": "$", "region": "🇺🇸 US"},
    "Dow Jones":     {"ticker": "^DJI",      "currency": "$", "region": "🇺🇸 US"},
    "EuroStoxx 50":  {"ticker": "^STOXX50E", "currency": "€", "region": "🇪🇺 Europe"},
    "DAX":           {"ticker": "^GDAXI",    "currency": "€", "region": "🇩🇪 Germany"},
    "CAC 40":        {"ticker": "^FCHI",     "currency": "€", "region": "🇫🇷 France"},
    "FTSE 100":      {"ticker": "^FTSE",     "currency": "£", "region": "🇬🇧 UK"},
    "Nikkei 225":    {"ticker": "^N225",     "currency": "¥", "region": "🇯🇵 Japan"},
    "Hang Seng":     {"ticker": "^HSI",      "currency": "HK$","region": "🇭🇰 HK"},
    "Shanghai Comp": {"ticker": "000001.SS", "currency": "¥", "region": "🇨🇳 China"},
    "KOSPI":         {"ticker": "^KS11",     "currency": "₩", "region": "🇰🇷 Korea"},
    "ASX 200":       {"ticker": "^AXJO",     "currency": "A$","region": "🇦🇺 Australia"},
    "SENSEX":        {"ticker": "^BSESN",    "currency": "₹", "region": "🇮🇳 India"},
}

COMMODITIES = {
    "Gold":        {"ticker": "GC=F",     "region": "⛏️ Metals"},
    "Silver":      {"ticker": "SI=F",     "region": "⛏️ Metals"},
    "Copper":      {"ticker": "HG=F",     "region": "⛏️ Metals"},
    "Platinum":    {"ticker": "PL=F",     "region": "⛏️ Metals"},
    "Oil WTI":     {"ticker": "CL=F",     "region": "🛢️ Energy"},
    "Oil Brent":   {"ticker": "BZ=F",     "region": "🛢️ Energy"},
    "Natural Gas": {"ticker": "NG=F",     "region": "🛢️ Energy"},
    "Wheat":       {"ticker": "ZW=F",     "region": "🌾 Agriculture"},
    "Corn":        {"ticker": "ZC=F",     "region": "🌾 Agriculture"},
    "Soybeans":    {"ticker": "ZS=F",     "region": "🌾 Agriculture"},
    "Coffee":      {"ticker": "KC=F",     "region": "🌾 Agriculture"},
    "Sugar":       {"ticker": "SB=F",     "region": "🌾 Agriculture"},
    "Cotton":      {"ticker": "CT=F",     "region": "🌾 Agriculture"},
}

CRYPTO = {
    "Bitcoin":  {"ticker": "BTC-USD", "region": "₿ Crypto"},
    "Ethereum": {"ticker": "ETH-USD", "region": "₿ Crypto"},
    "BNB":      {"ticker": "BNB-USD", "region": "₿ Crypto"},
    "Solana":   {"ticker": "SOL-USD", "region": "₿ Crypto"},
    "XRP":      {"ticker": "XRP-USD", "region": "₿ Crypto"},
}

FOREX = {
    "EUR/USD":        {"ticker": "EURUSD=X",  "region": "💱 Forex"},
    "GBP/USD":        {"ticker": "GBPUSD=X",  "region": "💱 Forex"},
    "USD/JPY":        {"ticker": "JPY=X",     "region": "💱 Forex"},
    "USD/TRY":        {"ticker": "TRY=X",     "region": "💱 Forex"},
    "USD/CNY":        {"ticker": "CNY=X",     "region": "💱 Forex"},
    "USD/CHF":        {"ticker": "CHF=X",     "region": "💱 Forex"},
    "USD Index (DXY)":{"ticker": "DX-Y.NYB",  "region": "💱 Forex"},
}

# ─────────────────────────────────────────────────────────────────────────────
# STOCK UNIVERSE  (Page 2)
# ─────────────────────────────────────────────────────────────────────────────

# ── BIST 100 hardcoded fallback (from Investing.com, June 2025) ──────────────
# Tickers as Yahoo Finance format (TICKER.IS).
# Dynamic fetch from Borsa Istanbul is attempted first.
BIST100_FALLBACK = {
    "AEFES.IS": "Anadolu Efes",      "AKBNK.IS": "Akbank",
    "AKSA.IS":  "Aksa Akrilik",      "AKSEN.IS": "Aksa Enerji",
    "ALARK.IS": "Alarko Holding",    "ANSGR.IS": "Anadolu Sigorta",
    "ARCLK.IS": "Arçelik",           "ASELS.IS": "Aselsan",
    "ASTOR.IS": "Astor Enerji",      "BIMAS.IS": "BIM Mağazalar",
    "BISAS.IS": "Ral Yatırım",       "BRSAN.IS": "Borusan Birleşik",
    "BRYAT.IS": "Borusan Yatırım",   "BSOKE.IS": "Batısöke",
    "BTCIM.IS": "Batıçim",           "CCOLA.IS": "Coca Cola İçecek",
    "CIMSA.IS": "Çimsa",             "CVKMD.IS": "CVK Maden",
    "CWENE.IS": "CW Enerji",         "CAN2T.IS": "Can2 Termik",
    "DAPGM.IS": "DAP GYO",           "DOAS.IS":  "Doğuş Otomotiv",
    "DOHOL.IS": "Doğan Holding",     "ECILC.IS": "Eczacıbaşı İlaç",
    "EFOR.IS":  "Efor Yatırım",      "EKGYO.IS": "Emlak Konut GYO",
    "ENERYA.IS":"Enerya Enerji",      "ENJSA.IS": "Enerjisa Enerji",
    "ENKAI.IS": "Enka İnşaat",       "EREGL.IS": "Ereğli Demir Çelik",
    "EUPWR.IS": "Europower Enerji",   "FENER.IS": "Fenerbahçe",
    "FROTO.IS": "Ford Otosan",        "GARAN.IS": "Garanti BBVA",
    "GENIL.IS": "Gen İlaç",           "GLRMK.IS": "Gulermak",
    "GRSEL.IS": "Gursel Turizm",      "GRTHO.IS": "Grainturk Holding",
    "GSRAY.IS": "Galatasaray",        "GUBRF.IS": "Gübre Fabrikaları",
    "GUSGR.IS": "Türkiye Sigorta",    "GWIND.IS": "Galata Wind",
    "HALKB.IS": "Halkbank",           "HEKTS.IS": "Hektaş",
    "IPEKE.IS": "İpek Doğal Enerji",  "ISCTR.IS": "İş Bankası C",
    "ISGSY.IS": "İş Yatırım",         "IZMDC.IS": "İzdemir Enerji",
    "KATEV.IS": "Katılımevim",         "KCHOL.IS": "Koç Holding",
    "KLGYO.IS": "Kiler Holding",       "KMPUR.IS": "Kontrolmatik",
    "KOZAA.IS": "Anadolu Metal",       "KOZAL.IS": "Türk Altın İşletmeleri",
    "KRDMD.IS": "Kardemir D",          "KUYAG.IS": "Kuyas Yatırım",
    "MAGEN.IS": "Margun Enerji",       "MAVI.IS":  "Mavi Giyim",
    "MGROS.IS": "Migros",              "MIATK.IS": "Mia Teknoloji",
    "MPARK.IS": "MLP Sağlık",          "MRDIN.IS": "Oyak Çimento",
    "OBAMD.IS": "Oba Makarna",         "ODAS.IS":  "ODAS Elektrik",
    "OTKAR.IS": "Otokar",              "PAGYO.IS": "Pasifik GYO",
    "PASEU.IS": "Pasifik Eurasia",     "PEKGY.IS": "Pasifik Lojistik",
    "PETKM.IS": "Petkim",              "PGSUS.IS": "Pegasus",
    "PSGYO.IS": "Pasifik Holding",     "QUAGR.IS": "Qua Granite",
    "REEDR.IS": "Reeder Teknoloji",    "SAHOL.IS": "Sabancı Holding",
    "SARKY.IS": "Sarkuysan",           "SASA.IS":  "SASA Polyester",
    "SISE.IS":  "Şişecam",             "SKBNK.IS": "Şekerbank",
    "SOKM.IS":  "Şok Marketler",       "TABGD.IS": "Tab Gıda",
    "TAVHL.IS": "TAV Havalimanları",   "TCELL.IS": "Turkcell",
    "THYAO.IS": "Türk Hava Yolları",   "TKFEN.IS": "Tekfen Holding",
    "TOASO.IS": "Tofaş Oto",           "TSKB.IS":  "TSKB",
    "TTKOM.IS": "Türk Telekom",         "TUKAS.IS": "Tukaş Gıda",
    "TUPRS.IS": "Tüpraş",              "TURKS.IS": "Tureks Turizm",
    "ULKER.IS": "Ülker Bisküvi",        "VAKBN.IS": "Vakıfbank",
    "VESTL.IS": "Vestel",               "YAZIC.IS": "AG Anadolu Group",
    "YKBNK.IS": "Yapı Kredi",           "ZOREN.IS": "Zorlu Enerji",
    "DSFKTR.IS":"Destek Finans",         "BALSU.IS": "Balsu Gıda",
    "ALTIN.IS": "Altınay Savunma",       "EUROPEN.IS":"Europen Endüstri",
}

# ── S&P 500 hardcoded fallback (top 50 by market cap) ────────────────────────
SP500_FALLBACK = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","AMZN":"Amazon",
    "META":"Meta","GOOGL":"Alphabet A","GOOG":"Alphabet C","BRK-B":"Berkshire B",
    "LLY":"Eli Lilly","JPM":"JPMorgan","V":"Visa","XOM":"ExxonMobil",
    "UNH":"UnitedHealth","TSLA":"Tesla","MA":"Mastercard","PG":"P&G",
    "COST":"Costco","JNJ":"Johnson & Johnson","HD":"Home Depot","MRK":"Merck",
    "ABBV":"AbbVie","CVX":"Chevron","CRM":"Salesforce","BAC":"Bank of America",
    "WMT":"Walmart","NFLX":"Netflix","AMD":"AMD","KO":"Coca-Cola",
    "PEP":"PepsiCo","TMO":"Thermo Fisher","ACN":"Accenture","MCD":"McDonald's",
    "ORCL":"Oracle","CSCO":"Cisco","ABT":"Abbott","LIN":"Linde",
    "ADBE":"Adobe","GE":"GE Aerospace","DHR":"Danaher","TXN":"Texas Instruments",
    "PM":"Philip Morris","AMGN":"Amgen","CAT":"Caterpillar","INTU":"Intuit",
    "IBM":"IBM","SPGI":"S&P Global","NOW":"ServiceNow","GS":"Goldman Sachs",
    "ISRG":"Intuitive Surgical","BKNG":"Booking Holdings",
}

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

FREQ_OPTIONS = {
    "1 Hour":  {"period": "60d",  "interval": "1h"},
    "1 Day":   {"period": "2y",   "interval": "1d"},
    "1 Week":  {"period": "5y",   "interval": "1wk"},
}

SIGNAL_COLORS = {
    "Strong Buy":  "#00C853",
    "Buy":         "#26A69A",
    "Hold":        "#FFD740",
    "Sell":        "#FF6D00",
    "Strong Sell": "#D50000",
    "N/A":         "#666666",
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.hdr {
    background: linear-gradient(135deg,#1a1f3a,#0d1117);
    border-bottom: 2px solid #2E75B6;
    padding: 1rem 2rem 0.8rem; margin: -1rem -1rem 1.2rem -1rem;
}
.hdr h1 { margin:0; font-size:1.45rem; font-weight:700;
    background:linear-gradient(90deg,#63b3ed,#68d391);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hdr p  { margin:.1rem 0 0; color:#718096; font-size:.78rem; }

.sbar-sec {
    font-size:.68rem; font-weight:700; letter-spacing:.1em;
    color:#63b3ed; text-transform:uppercase;
    padding:.55rem 0 .15rem; margin-top:.3rem;
    border-top:1px solid #2d3748;
}

.mcard {
    background:#161b2e; border:1px solid #2d3748; border-radius:9px;
    padding:.75rem .9rem; text-align:center;
}
.mcard .lbl { font-size:.64rem; color:#718096;
    text-transform:uppercase; letter-spacing:.07em; margin-bottom:.2rem; }
.mcard .val { font-size:1.2rem; font-weight:700; }
.mcard .sub { font-size:.68rem; color:#718096; margin-top:.1rem; }

.sig {
    display:inline-block; padding:.18rem .6rem; border-radius:20px;
    font-size:.72rem; font-weight:600; letter-spacing:.03em;
}
.sig-sb  { background:#003d1f; color:#00C853; border:1px solid #00C853; }
.sig-b   { background:#0d2e2a; color:#26A69A; border:1px solid #26A69A; }
.sig-h   { background:#3a3000; color:#FFD740; border:1px solid #FFD740; }
.sig-s   { background:#3a1a00; color:#FF6D00; border:1px solid #FF6D00; }
.sig-ss  { background:#3a0000; color:#FF5252; border:1px solid #FF5252; }
.sig-na  { background:#1a1a1a; color:#888888; border:1px solid #444; }

.source-note {
    font-size:.7rem; color:#4a5568;
    border:1px solid #2d3748; border-radius:6px;
    padding:.4rem .8rem; margin-bottom:.6rem;
}

.footer { text-align:center; color:#4a5568; font-size:.7rem;
    padding:1rem 0; border-top:1px solid #1a202c; margin-top:1.2rem; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# LIVE CONSTITUENT FETCHING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)   # refresh once per day
def fetch_bist100_live() -> dict:
    """
    Fetch official BIST 100 constituent list from Borsa Istanbul.
    URL: https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv
    The CSV has columns: TICKER, INDEX_CODE, ... (semicolon-separated, latin-1)
    Returns {TICKER.IS: display_name} for all XU100 members.
    Falls back to BIST100_FALLBACK on any error.
    """
    try:
        import urllib.request, ssl
        url = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "text/csv,application/octet-stream,*/*",
            "Referer": "https://www.borsaistanbul.com/en/indices/bist-stock-indices",
        }
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            raw = r.read()

        # Try encodings common for Turkish CSVs
        for enc in ("utf-8-sig", "utf-8", "windows-1252", "iso-8859-9"):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        else:
            return BIST100_FALLBACK

        # Parse — Borsa Istanbul CSV uses semicolons
        df = pd.read_csv(io.StringIO(text), sep=";", dtype=str)
        df.columns = [c.strip().upper() for c in df.columns]

        # Find ticker and index columns (column names may vary slightly)
        ticker_col = next((c for c in df.columns if "TICKER" in c or "KOD" in c or "CODE" in c), None)
        index_col  = next((c for c in df.columns if "ENDEKS" in c or "INDEX" in c), None)
        name_col   = next((c for c in df.columns if "ISIM" in c or "NAME" in c or "SIRKET" in c or "UNVAN" in c), None)

        if ticker_col is None or index_col is None:
            return BIST100_FALLBACK

        # Filter for XU100 members
        mask   = df[index_col].str.strip().str.upper() == "XU100"
        bist_df = df[mask]

        if bist_df.empty:
            return BIST100_FALLBACK

        result = {}
        for _, row in bist_df.iterrows():
            ticker = str(row[ticker_col]).strip().upper()
            name   = str(row[name_col]).strip() if name_col and name_col in row else ticker
            result[f"{ticker}.IS"] = name

        return result if len(result) >= 50 else BIST100_FALLBACK

    except Exception:
        return BIST100_FALLBACK


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sp500_live() -> dict:
    """
    Fetch S&P 500 constituents from GitHub datasets/s-and-p-500-companies.
    This is the most reliable free source — updated within days of index changes.
    Returns {TICKER: company_name}.
    Falls back to SP500_FALLBACK on any error.
    """
    try:
        import urllib.request
        url = ("https://raw.githubusercontent.com/datasets/"
               "s-and-p-500-companies/main/data/constituents.csv")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(text))
        # Columns: Symbol, Security, GICS Sector, ...
        sym_col  = "Symbol"   if "Symbol"   in df.columns else df.columns[0]
        name_col = "Security" if "Security" in df.columns else df.columns[1]
        # Yahoo Finance uses '-' not '.' for BRK.B etc.
        result = {
            str(r[sym_col]).replace(".", "-"): str(r[name_col])
            for _, r in df.iterrows()
        }
        return result if len(result) >= 400 else SP500_FALLBACK
    except Exception:
        return SP500_FALLBACK


# ─────────────────────────────────────────────────────────────────────────────
# PRICE DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(full_ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Universal OHLCV fetch with one retry on transient Yahoo throttling."""
    last_err = None
    for _ in range(2):
        try:
            df = yf.download(
                full_ticker, period=period, interval=interval,
                auto_adjust=True, progress=False, threads=False,
            )
            if df is None or df.empty:
                last_err = "empty"
                time.sleep(1.1)
                continue
            # Flatten MultiIndex (yfinance wraps even single-ticker downloads)
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = df.columns.get_level_values(0).astype(str)
                lvl1 = df.columns.get_level_values(1).astype(str)
                df.columns = lvl1 if full_ticker in lvl0.values else lvl0
            df.columns = [str(c).lower() for c in df.columns]
            if not {"open","high","low","close"}.issubset(set(df.columns)):
                last_err = "missing_cols"
                time.sleep(1.1)
                continue
            df.index = pd.to_datetime(df.index)
            df = df.dropna(subset=["close"])
            if df.empty:
                last_err = "all_nan"
                time.sleep(1.1)
                continue
            return df
        except Exception as e:
            last_err = str(e)[:80]
            time.sleep(1.1)
    st.session_state.setdefault("_ferr", {})[full_ticker] = last_err
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# INDICATORS & SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _s_rsi(v):
    if pd.isna(v): return 0
    if v >= 70: return -2
    if v >= 60: return -1
    if v <= 30: return  2
    if v <= 40: return  1
    return 0

def _s_macd(m, s, h):
    if any(pd.isna(x) for x in [m,s,h]): return 0
    return max(-2, min(2, (1 if m>s else -1)+(1 if h>0 else -1)))

def _s_cci(v):
    if pd.isna(v): return 0
    if v >= 200: return  2
    if v >= 100: return  1
    if v <=-200: return -2
    if v <=-100: return -1
    return 0

def _s_mom(v):
    if pd.isna(v): return 0
    if v >  2: return  2
    if v >  0: return  1
    if v < -2: return -2
    return -1

def _s_stoch(k, d):
    if any(pd.isna(x) for x in [k,d]): return 0
    if k<20 and d<20: return  2
    if k>80 and d>80: return -2
    if k<20: return  1
    if k>80: return -1
    return 1 if k>d else -1

def _s_willr(v):
    if pd.isna(v): return 0
    if v<=-80: return  2
    if v<=-50: return  1
    if v>=-20: return -2
    return -1

def _label(t):
    if t >=  6: return "Strong Buy"
    if t >=  2: return "Buy"
    if t <= -6: return "Strong Sell"
    if t <= -2: return "Sell"
    return "Hold"


def compute_signal(df: pd.DataFrame, p: dict) -> dict:
    empty = {"signal":"N/A","score":0,"details":{},"ind_series":{}}
    if len(df) < 35: return empty
    try:
        d = df.tail(150).copy()
        macd_df = ta.macd(d["close"], fast=p["macd_fast"],
                          slow=p["macd_slow"], signal=p["macd_sig"])
        rsi   = ta.rsi(d["close"],  length=p["rsi_len"])
        mom   = ta.mom(d["close"],  length=p["mom_len"])
        cci   = ta.cci(d["high"], d["low"], d["close"], length=p["cci_len"])
        stoch = ta.stoch(d["high"], d["low"], d["close"],
                         k=p["stoch_k"], d=p["stoch_d"])
        willr = ta.willr(d["high"], d["low"], d["close"], length=p["willr_len"])

        sm  = _s_macd(macd_df["MACD_12_26_9"].iloc[-1],
                      macd_df["MACDs_12_26_9"].iloc[-1],
                      macd_df["MACDh_12_26_9"].iloc[-1])
        sr  = _s_rsi(rsi.iloc[-1])
        smo = _s_mom(mom.iloc[-1])
        sc  = _s_cci(cci.iloc[-1])
        ss  = _s_stoch(stoch["STOCHk_14_3_3"].iloc[-1],
                       stoch["STOCHd_14_3_3"].iloc[-1])
        sw  = _s_willr(willr.iloc[-1])
        total = sr + sm + sc + smo + ss + sw

        return {
            "signal": _label(total), "score": total,
            "ind_series": {"macd":macd_df,"rsi":rsi,"mom":mom,
                           "cci":cci,"stoch":stoch,"willr":willr},
            "details": {
                "RSI":        (sr,  round(float(rsi.iloc[-1]),       2)),
                "MACD":       (sm,  round(float(macd_df["MACD_12_26_9"].iloc[-1]), 4)),
                "CCI":        (sc,  round(float(cci.iloc[-1]),       2)),
                "Momentum":   (smo, round(float(mom.iloc[-1]),       4)),
                "Stochastic": (ss,  round(float(stoch["STOCHk_14_3_3"].iloc[-1]),2)),
                "Williams%R": (sw,  round(float(willr.iloc[-1]),     2)),
            },
        }
    except Exception:
        return empty


def one_row(full_ticker, name, atype, region, period, interval, p) -> dict:
    base = {"Ticker":full_ticker,"Name":name,"Type":atype,"Region":region,
            "Price":None,"Change%":None,"Signal":"N/A","Score":0,
            "RSI":0,"MACD":0,"CCI":0,"Momentum":0,"Stochastic":0,"Williams%R":0}
    df = fetch_data(full_ticker, period, interval)
    if df.empty or len(df) < 35: return base
    sig   = compute_signal(df, p)
    price = float(df["close"].iloc[-1])
    chg   = float((df["close"].iloc[-1]/df["close"].iloc[-2]-1)*100) if len(df)>1 else 0.0
    row   = {**base,
             "Price":   round(price, 4 if price < 10 else 2),
             "Change%": round(chg, 2),
             "Signal":  sig["signal"],
             "Score":   sig["score"]}
    for k,(sc,_) in sig.get("details",{}).items():
        row[k] = sc
    return row


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def sidebar() -> dict:
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        # Timeframe
        st.markdown('<div class="sbar-sec">Timeframe</div>', unsafe_allow_html=True)
        freq = st.selectbox("tf", list(FREQ_OPTIONS.keys()),
                            index=1, label_visibility="collapsed")

        # Indicator params
        st.markdown('<div class="sbar-sec">Indicator Parameters</div>',
                    unsafe_allow_html=True)
        with st.expander("Customize", expanded=False):
            rsi_len   = st.slider("RSI period",       7, 30, 14)
            macd_fast = st.slider("MACD fast",         5, 20, 12)
            macd_slow = st.slider("MACD slow",        15, 50, 26)
            macd_sig  = st.slider("MACD signal",       3, 15,  9)
            cci_len   = st.slider("CCI period",       10, 50, 20)
            mom_len   = st.slider("Momentum period",   5, 30, 10)
            stoch_k   = st.slider("Stochastic %K",    5, 30, 14)
            stoch_d   = st.slider("Stochastic %D",    2, 10,  3)
            willr_len = st.slider("Williams %R",       5, 30, 14)

        # Page 1 assets
        st.markdown('<div class="sbar-sec">Page 1 — Markets</div>',
                    unsafe_allow_html=True)
        with st.expander("🌍 Indices", expanded=True):
            sel_idx = st.multiselect(
                "idx", list(INDICES.keys()),
                default=list(INDICES.keys()),
                label_visibility="collapsed",
            )
        with st.expander("🏅 Commodities", expanded=False):
            sel_com = st.multiselect(
                "com", list(COMMODITIES.keys()),
                default=["Gold","Silver","Oil WTI","Oil Brent","Natural Gas","Copper"],
                label_visibility="collapsed",
            )
        with st.expander("💱 Forex", expanded=False):
            sel_fx = st.multiselect(
                "fx", list(FOREX.keys()),
                default=["EUR/USD","USD/TRY","USD/JPY","USD Index (DXY)"],
                label_visibility="collapsed",
            )
        with st.expander("₿ Crypto", expanded=False):
            sel_cr = st.multiselect(
                "cr", list(CRYPTO.keys()),
                default=["Bitcoin","Ethereum"],
                label_visibility="collapsed",
            )

        st.markdown("---")
        if st.button("🗑️ Clear cache", use_container_width=True):
            st.cache_data.clear()
            for k in ["screener_p1","screener_p2"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.caption(f"Cache TTL: 1h  •  {datetime.now().strftime('%H:%M %d %b')}")

    p = dict(rsi_len=rsi_len, macd_fast=macd_fast, macd_slow=macd_slow,
             macd_sig=macd_sig, cci_len=cci_len, mom_len=mom_len,
             stoch_k=stoch_k, stoch_d=stoch_d, willr_len=willr_len,
             freq=freq,
             period=FREQ_OPTIONS[freq]["period"],
             interval=FREQ_OPTIONS[freq]["interval"],
             sel_idx=sel_idx, sel_com=sel_com, sel_fx=sel_fx, sel_cr=sel_cr)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# SHARED SCREENER TABLE RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_table(df_all: pd.DataFrame):
    """Filter/sort controls + coloured dataframe."""
    fc1, fc2, fc3, fc4 = st.columns([2,2,2,2])
    with fc1:
        tf = st.multiselect("Type", sorted(df_all["Type"].unique()), default=[])
    with fc2:
        sf = st.multiselect("Signal",
             ["Strong Buy","Buy","Hold","Sell","Strong Sell"], default=[])
    with fc3:
        sb = st.selectbox("Sort by", ["Score","Change%","Ticker","Type"])
    with fc4:
        asc = st.radio("Order", ["Desc","Asc"], horizontal=True) == "Asc"

    disp = df_all.copy()
    if tf: disp = disp[disp["Type"].isin(tf)]
    if sf: disp = disp[disp["Signal"].isin(sf)]
    disp = disp.sort_values(sb, ascending=asc).reset_index(drop=True)

    # Summary badges
    counts = df_all["Signal"].value_counts()
    bc = st.columns(5)
    for i, sig in enumerate(["Strong Buy","Buy","Hold","Sell","Strong Sell"]):
        cnt = counts.get(sig, 0)
        col = SIGNAL_COLORS[sig]
        pct = round(cnt/len(df_all)*100) if len(df_all) else 0
        with bc[i]:
            st.markdown(
                f'<div class="mcard"><div class="lbl">{sig}</div>'
                f'<div class="val" style="color:{col}">{cnt}</div>'
                f'<div class="sub">{pct}%</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<br>", unsafe_allow_html=True)

    show = ["Ticker","Name","Type","Region","Price","Change%","Signal","Score",
            "RSI","MACD","CCI","Momentum","Stochastic","Williams%R"]

    def cs(v):
        c = SIGNAL_COLORS.get(v,"")
        return f"color:{c}; font-weight:600;" if c else ""
    def cc(v):
        if pd.isna(v): return ""
        return "color:#26A69A;" if v>=0 else "color:#EF5350;"
    def csc(v):
        if pd.isna(v): return ""
        if v>=2:  return "color:#26A69A; font-weight:600;"
        if v<=-2: return "color:#EF5350; font-weight:600;"
        return "color:#FFD740;"

    styled = (disp[show].style
              .map(cs,  subset=["Signal"])
              .map(cc,  subset=["Change%"])
              .map(csc, subset=["Score"])
              .format({"Price":"{:.2f}","Change%":"{:+.2f}%"}, na_rep="—"))
    st.dataframe(styled, use_container_width=True, height=520)

    csv = disp[show].to_csv(index=False)
    st.download_button("⬇ Export CSV", csv,
        f"ta_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — MARKET OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def page1(p):
    st.markdown("## 📋 Market Overview")

    # Build asset list from sidebar selection
    assets = []
    for name in p["sel_idx"]:
        m = INDICES[name]
        assets.append((m["ticker"], name, "Index", m["region"]))
    for name in p["sel_com"]:
        m = COMMODITIES[name]
        assets.append((m["ticker"], name, "Commodity", m["region"]))
    for name in p["sel_fx"]:
        m = FOREX[name]
        assets.append((m["ticker"], name, "Forex", m["region"]))
    for name in p["sel_cr"]:
        m = CRYPTO[name]
        assets.append((m["ticker"], name, "Crypto", m["region"]))

    n = len(assets)
    st.markdown(
        f"**{n} assets** selected  •  Timeframe: **{p['freq']}**  •  "
        f"Composite score −12 → +12"
    )

    col_btn, col_info = st.columns([1,5])
    with col_btn:
        run = st.button("▶ Run Screener", type="primary", use_container_width=True)
    with col_info:
        st.caption("Results cached 1 hour. Change timeframe or assets in sidebar, then press Run.")

    if run:
        st.session_state.pop("screener_p1", None)
        rows   = []
        bar    = st.progress(0, "Starting…")
        status = st.empty()
        for i,(ticker,name,atype,region) in enumerate(assets):
            status.caption(f"⏳ {ticker} — {name}  ({i+1}/{n})")
            rows.append(one_row(ticker,name,atype,region,
                                p["period"],p["interval"],p))
            bar.progress((i+1)/n, f"{ticker}")
        bar.empty(); status.empty()
        st.session_state["screener_p1"] = pd.DataFrame(rows)

    df_all = st.session_state.get("screener_p1")
    if df_all is None or df_all.empty:
        st.caption("Press **Run Screener** to load data.")
        return
    render_table(df_all)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — STOCK SCREENER
# ─────────────────────────────────────────────────────────────────────────────

def page2(p):
    st.markdown("## 📈 Stock Screener")

    # ── Data source selector ──────────────────────────────────────────────────
    st.markdown("#### Select Universe")
    u_col1, u_col2, u_col3 = st.columns([2,2,3])

    with u_col1:
        do_bist = st.checkbox("🇹🇷 BIST 100  (~100 stocks)", value=True)
    with u_col2:
        do_sp   = st.checkbox("🇺🇸 S&P 500  (~503 stocks)", value=False)
    with u_col3:
        st.markdown(
            '<div class="source-note">'
            '📡 <b>BIST 100</b>: Borsa Istanbul official CSV (live) · '
            '<b>S&P 500</b>: GitHub/datasets (live, updated daily)'
            '</div>',
            unsafe_allow_html=True,
        )

    if not do_bist and not do_sp:
        st.info("Select at least one universe above.")
        return

    # Fetch constituent lists (cached 24 h)
    with st.spinner("Checking constituent lists…"):
        bist_universe = fetch_bist100_live()  if do_bist else {}
        sp_universe   = fetch_sp500_live()    if do_sp   else {}

    # Count & source info
    info_parts = []
    if do_bist:
        src = "live (Borsa Istanbul)" if bist_universe is not BIST100_FALLBACK else "fallback (hardcoded)"
        info_parts.append(f"BIST 100: **{len(bist_universe)} stocks** — {src}")
    if do_sp:
        src = "live (GitHub/datasets)" if sp_universe is not SP500_FALLBACK else "fallback (top 50)"
        info_parts.append(f"S&P 500: **{len(sp_universe)} stocks** — {src}")

    st.markdown("  •  ".join(info_parts))

    # Build full asset list
    assets = []
    for full_ticker, name in bist_universe.items():
        assets.append((full_ticker, name, "BIST 100", "🇹🇷 Turkey"))
    for ticker, name in sp_universe.items():
        assets.append((ticker, name, "S&P 500", "🇺🇸 US"))

    n = len(assets)
    est_min = round(n * 1.2 / 60, 1)

    col_btn2, col_info2 = st.columns([1,5])
    with col_btn2:
        run2 = st.button("▶ Run Stock Screener", type="primary",
                         use_container_width=True)
    with col_info2:
        st.caption(
            f"**{n} stocks** to screen · Est. time: ~{est_min} min "
            f"(~1.2 s/stock with retry). "
            f"Timeframe: **{p['freq']}**. Results cached 1 hour."
        )

    if run2:
        st.session_state.pop("screener_p2", None)
        rows   = []
        bar    = st.progress(0, "Starting…")
        status = st.empty()
        for i,(ticker,name,atype,region) in enumerate(assets):
            status.caption(f"⏳ {ticker} — {name}  ({i+1}/{n})")
            rows.append(one_row(ticker,name,atype,region,
                                p["period"],p["interval"],p))
            bar.progress((i+1)/n, f"{ticker}")
        bar.empty(); status.empty()
        st.session_state["screener_p2"] = pd.DataFrame(rows)

    df_all = st.session_state.get("screener_p2")
    if df_all is None or df_all.empty:
        st.caption("Press **Run Stock Screener** to load data.")
        return
    render_table(df_all)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — ASSET DETAIL (charts)
# ─────────────────────────────────────────────────────────────────────────────

def build_charts(df, ind, ticker, name):
    fig = make_subplots(
        rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.025,
        row_heights=[3,1.2,1.2,1.2,1.2,1.2,1.2],
        subplot_titles=[f"{ticker} — {name}","MACD","RSI","Momentum",
                        "CCI","Stochastic","Williams %R"],
    )
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"],
        close=df["close"], increasing_line_color="#26A69A",
        decreasing_line_color="#EF5350", showlegend=False,
    ), row=1, col=1)

    md = ind["macd"]; h = md["MACDh_12_26_9"]
    fig.add_trace(go.Bar(x=df.index, y=h, showlegend=False,
        marker_color=["#26A69A" if v>=0 else "#EF5350" for v in h]), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=md["MACD_12_26_9"],
        line=dict(color="#2962FF",width=1.3), name="MACD"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=md["MACDs_12_26_9"],
        line=dict(color="#FF6D00",width=1.2,dash="dot"), name="Signal"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=ind["rsi"],
        line=dict(color="#AB47BC",width=1.5), showlegend=False), row=3, col=1)
    for lv,c in [(70,"rgba(239,83,80,.35)"),(30,"rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="grey", line_width=.6, row=3, col=1)

    mom = ind["mom"]
    fig.add_trace(go.Bar(x=df.index, y=mom, showlegend=False,
        marker_color=["#26A69A" if v>=0 else "#EF5350" for v in mom]), row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="grey", line_width=.6, row=4, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=ind["cci"],
        line=dict(color="#FFA726",width=1.5), showlegend=False), row=5, col=1)
    for lv,c in [(100,"rgba(239,83,80,.35)"),(-100,"rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=5, col=1)

    st_ = ind["stoch"]
    fig.add_trace(go.Scatter(x=df.index, y=st_["STOCHk_14_3_3"],
        line=dict(color="#42A5F5",width=1.5), name="%K"), row=6, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=st_["STOCHd_14_3_3"],
        line=dict(color="#EF5350",width=1.2,dash="dot"), name="%D"), row=6, col=1)
    for lv,c in [(80,"rgba(239,83,80,.35)"),(20,"rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=6, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=ind["willr"],
        line=dict(color="#EC407A",width=1.5), showlegend=False), row=7, col=1)
    for lv,c in [(-20,"rgba(239,83,80,.35)"),(-80,"rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=7, col=1)

    fig.update_layout(
        height=1060, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        font=dict(color="#FAFAFA", family="Inter,sans-serif", size=11),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50,r=20,t=40,b=20), hovermode="x unified",
        legend=dict(orientation="h",x=0,y=1.01,bgcolor="rgba(0,0,0,0)"),
    )
    for i in range(1,8):
        fig.update_xaxes(showgrid=True,gridcolor="#1E2130",gridwidth=.5,row=i,col=1)
        fig.update_yaxes(showgrid=True,gridcolor="#1E2130",gridwidth=.5,row=i,col=1)
    return fig


def page3(p):
    st.markdown("## 🔍 Asset Detail")

    # Collect all screened assets from both pages
    all_assets: list[tuple] = []
    if "screener_p1" in st.session_state:
        df1 = st.session_state["screener_p1"]
        for _, r in df1.iterrows():
            all_assets.append((r["Ticker"], r["Name"], r["Type"], r["Region"]))
    if "screener_p2" in st.session_state:
        df2 = st.session_state["screener_p2"]
        for _, r in df2.iterrows():
            all_assets.append((r["Ticker"], r["Name"], r["Type"], r["Region"]))

    if not all_assets:
        st.info("Run the screener on Page 1 or Page 2 first — the results will appear here.")
        return

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for item in all_assets:
        if item[0] not in seen:
            seen.add(item[0]); unique.append(item)

    label_map = {t: f"[{at}]  {t}  —  {n}" for t,n,at,r in unique}

    col_sel, col_ref = st.columns([5,1])
    with col_sel:
        ticker = st.selectbox("Asset", [t for t,*_ in unique],
                              format_func=lambda t: label_map.get(t,t),
                              label_visibility="collapsed")
    with col_ref:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_data.clear(); st.rerun()

    meta = next(((t,n,at,r) for t,n,at,r in unique if t==ticker), (ticker,ticker,"",""))
    _, name, atype, region = meta

    with st.spinner(f"Loading {ticker}…"):
        df = fetch_data(ticker, p["period"], p["interval"])

    if df.empty:
        err = st.session_state.get("_ferr",{}).get(ticker,"unknown")
        st.error(f"No data for **{ticker}** — reason: `{err}`. Try Refresh.")
        return

    sig = compute_signal(df, p)
    price   = float(df["close"].iloc[-1])
    chg_pct = float((df["close"].iloc[-1]/df["close"].iloc[-2]-1)*100) if len(df)>1 else 0.
    chg_col = "#26A69A" if chg_pct>=0 else "#EF5350"
    sig_col = SIGNAL_COLORS.get(sig["signal"],"#FFD740")
    p_fmt   = f"{price:,.4f}" if price<10 else f"{price:,.2f}"

    # Header cards
    c1,c2,c3,c4,c5 = st.columns(5)
    for col,(lbl,val,col_) in zip(
        [c1,c2,c3,c4,c5],
        [("Asset",name,"#FAFAFA"),("Type",atype,"#63b3ed"),
         ("Price",p_fmt,"#FAFAFA"),
         (f"Change ({p['freq']})",f"{chg_pct:+.2f}%",chg_col),
         ("Signal",sig["signal"],sig_col)],
    ):
        with col:
            st.markdown(
                f'<div class="mcard"><div class="lbl">{lbl}</div>'
                f'<div class="val" style="color:{col_};font-size:1rem;">{val}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Indicator breakdown
    with st.expander("📊 Score Breakdown", expanded=True):
        SL = {2:"Strong Buy",1:"Buy",0:"Hold",-1:"Sell",-2:"Strong Sell"}
        bc2 = st.columns(6)
        for i,(k,(sc,vl)) in enumerate(sig.get("details",{}).items()):
            with bc2[i]:
                cc = SIGNAL_COLORS.get(SL.get(sc,"Hold"),"#FFD740")
                st.markdown(
                    f'<div class="mcard"><div class="lbl">{k}</div>'
                    f'<div class="val" style="color:{cc}">{sc:+d}</div>'
                    f'<div class="sub">{vl}</div></div>',
                    unsafe_allow_html=True,
                )
        st.markdown("<br>", unsafe_allow_html=True)
        total = sig["score"]
        st.markdown(
            f"**Composite: {total:+d}** / ±12 &nbsp;"
            f'<span class="sig sig-{sig["signal"].lower().replace(" ","-")}">'
            f'{sig["signal"]}</span>',
            unsafe_allow_html=True,
        )
        st.progress(int((total+12)/24*100))

    st.markdown("<br>", unsafe_allow_html=True)

    ind = sig.get("ind_series",{})
    if ind:
        st.plotly_chart(build_charts(df,ind,ticker,name),
                        use_container_width=True, config={"displayModeBar":True})
    else:
        st.warning("Not enough data for charts (need ≥ 35 bars).")

    with st.expander("📄 Raw data (last 50 bars)"):
        fmt = "%Y-%m-%d %H:%M" if "h" in p["interval"] else "%Y-%m-%d"
        sd = df.tail(50).copy(); sd.index = sd.index.strftime(fmt)
        st.dataframe(sd.style.format("{:.4f}"), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="hdr">'
        '<h1>📊 Global Technical Analysis Dashboard</h1>'
        '<p>Indices · Commodities · Forex · Crypto · BIST 100 · S&P 500 stocks  '
        '•  6 indicators  •  5-level signals  •  Yahoo Finance</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    p = sidebar()

    pg = st.radio("nav", ["📋 Market Overview", "📈 Stock Screener", "🔍 Asset Detail"],
                  horizontal=True, label_visibility="hidden")
    st.markdown("---")

    if "Overview" in pg:
        page1(p)
    elif "Stock" in pg:
        page2(p)
    else:
        page3(p)

    st.markdown(
        f'<div class="footer">Data: Yahoo Finance · Borsa Istanbul · GitHub/datasets  '
        f'•  Indicators: pandas-ta  •  Not financial advice  '
        f'•  {datetime.now().strftime("%d %b %Y %H:%M")}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
