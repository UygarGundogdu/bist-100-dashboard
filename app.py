"""
Global Technical Analysis Dashboard  v4
=========================================
Fixes vs v3:
  - BIST ticker suffix bug: 'AKSEN.E' stripped to 'AKSEN' before .IS appended
  - Speed: single retry, 0.5s sleep, no sleep on confirmed-empty response
  - Momentum scoring: % change (price-agnostic) instead of absolute value
  - Charts: rangebreaks to remove weekends/after-hours gaps
  - Page 1 menu: tree-style checkboxes (asset class → expander → items)
  - Page 3: category tabs + text search for fast asset selection
Run: streamlit run app.py
"""

import io, time
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(
    page_title="Global TA Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ASSET REGISTRIES
# ─────────────────────────────────────────────────────────────────────────────

INDICES = {
    "BIST 100":       {"ticker": "XU100.IS",  "currency": "₺", "region": "🇹🇷 Turkey"},
    "BIST 30":        {"ticker": "XU030.IS",  "currency": "₺", "region": "🇹🇷 Turkey"},
    "S&P 500":        {"ticker": "^GSPC",     "currency": "$", "region": "🇺🇸 US"},
    "NASDAQ 100":     {"ticker": "^NDX",      "currency": "$", "region": "🇺🇸 US"},
    "Dow Jones":      {"ticker": "^DJI",      "currency": "$", "region": "🇺🇸 US"},
    "EuroStoxx 50":   {"ticker": "^STOXX50E", "currency": "€", "region": "🇪🇺 Europe"},
    "DAX":            {"ticker": "^GDAXI",    "currency": "€", "region": "🇩🇪 Germany"},
    "CAC 40":         {"ticker": "^FCHI",     "currency": "€", "region": "🇫🇷 France"},
    "FTSE 100":       {"ticker": "^FTSE",     "currency": "£", "region": "🇬🇧 UK"},
    "Nikkei 225":     {"ticker": "^N225",     "currency": "¥", "region": "🇯🇵 Japan"},
    "Hang Seng":      {"ticker": "^HSI",      "currency": "HK$", "region": "🇭🇰 HK"},
    "Shanghai Comp":  {"ticker": "000001.SS", "currency": "¥", "region": "🇨🇳 China"},
    "KOSPI":          {"ticker": "^KS11",     "currency": "₩", "region": "🇰🇷 Korea"},
    "ASX 200":        {"ticker": "^AXJO",     "currency": "A$","region": "🇦🇺 Australia"},
    "SENSEX":         {"ticker": "^BSESN",    "currency": "₹", "region": "🇮🇳 India"},
}

COMMODITIES = {
    "Gold":           {"ticker": "GC=F",  "region": "⛏️ Metals"},
    "Silver":         {"ticker": "SI=F",  "region": "⛏️ Metals"},
    "Copper":         {"ticker": "HG=F",  "region": "⛏️ Metals"},
    "Platinum":       {"ticker": "PL=F",  "region": "⛏️ Metals"},
    "Oil WTI":        {"ticker": "CL=F",  "region": "🛢️ Energy"},
    "Oil Brent":      {"ticker": "BZ=F",  "region": "🛢️ Energy"},
    "Natural Gas":    {"ticker": "NG=F",  "region": "🛢️ Energy"},
    "Wheat":          {"ticker": "ZW=F",  "region": "🌾 Agri"},
    "Corn":           {"ticker": "ZC=F",  "region": "🌾 Agri"},
    "Soybeans":       {"ticker": "ZS=F",  "region": "🌾 Agri"},
    "Coffee":         {"ticker": "KC=F",  "region": "🌾 Agri"},
    "Sugar":          {"ticker": "SB=F",  "region": "🌾 Agri"},
}

FOREX = {
    "EUR/USD":         {"ticker": "EURUSD=X", "region": "💱 Forex"},
    "GBP/USD":         {"ticker": "GBPUSD=X", "region": "💱 Forex"},
    "USD/JPY":         {"ticker": "JPY=X",    "region": "💱 Forex"},
    "USD/TRY":         {"ticker": "TRY=X",    "region": "💱 Forex"},
    "USD/CNY":         {"ticker": "CNY=X",    "region": "💱 Forex"},
    "USD/CHF":         {"ticker": "CHF=X",    "region": "💱 Forex"},
    "USD Index (DXY)": {"ticker": "DX-Y.NYB", "region": "💱 Forex"},
}

CRYPTO = {
    "Bitcoin":  {"ticker": "BTC-USD", "region": "₿ Crypto"},
    "Ethereum": {"ticker": "ETH-USD", "region": "₿ Crypto"},
    "BNB":      {"ticker": "BNB-USD", "region": "₿ Crypto"},
    "Solana":   {"ticker": "SOL-USD", "region": "₿ Crypto"},
    "XRP":      {"ticker": "XRP-USD", "region": "₿ Crypto"},
}

# ── BIST 100 fallback (Investing.com, Jun 2025 — exact Yahoo Finance tickers) ─
BIST100_FALLBACK = {
    "AEFES.IS":"Anadolu Efes",    "AKBNK.IS":"Akbank",
    "AKSA.IS":"Aksa Akrilik",     "AKSEN.IS":"Aksa Enerji",
    "ALARK.IS":"Alarko Holding",  "ANSGR.IS":"Anadolu Sigorta",
    "ARCLK.IS":"Arçelik",         "ASELS.IS":"Aselsan",
    "ASTOR.IS":"Astor Enerji",    "BIMAS.IS":"BIM Mağazalar",
    "BRSAN.IS":"Borusan Birleşik","BRYAT.IS":"Borusan Yatırım",
    "BSOKE.IS":"Batısöke",        "BTCIM.IS":"Batıçim",
    "CCOLA.IS":"Coca Cola İçecek","CIMSA.IS":"Çimsa",
    "CVKMD.IS":"CVK Maden",       "CWENE.IS":"CW Enerji",
    "DAPGM.IS":"DAP GYO",         "DOAS.IS":"Doğuş Otomotiv",
    "DOHOL.IS":"Doğan Holding",   "ECILC.IS":"Eczacıbaşı İlaç",
    "EFOR.IS":"Efor Yatırım",     "EKGYO.IS":"Emlak Konut GYO",
    "ENERYA.IS":"Enerya Enerji",  "ENJSA.IS":"Enerjisa Enerji",
    "ENKAI.IS":"Enka İnşaat",     "EREGL.IS":"Ereğli Demir Çelik",
    "EUPWR.IS":"Europower Enerji","FENER.IS":"Fenerbahçe",
    "FROTO.IS":"Ford Otosan",     "GARAN.IS":"Garanti BBVA",
    "GENIL.IS":"Gen İlaç",        "GLRMK.IS":"Gulermak",
    "GRSEL.IS":"Gursel Turizm",   "GSRAY.IS":"Galatasaray",
    "GUBRF.IS":"Gübre Fabrikaları","GWIND.IS":"Galata Wind",
    "HALKB.IS":"Halkbank",        "HEKTS.IS":"Hektaş",
    "IPEKE.IS":"İpek Doğal Enerji","ISCTR.IS":"İş Bankası C",
    "ISGSY.IS":"İş Yatırım",      "IZMDC.IS":"İzdemir Enerji",
    "KATEV.IS":"Katılımevim",     "KCHOL.IS":"Koç Holding",
    "KMPUR.IS":"Kontrolmatik",    "KOZAA.IS":"Koza Anadolu Metal",
    "KOZAL.IS":"Türk Altın İşletmeleri","KRDMD.IS":"Kardemir D",
    "KUYAG.IS":"Kuyas Yatırım",   "MAGEN.IS":"Margun Enerji",
    "MAVI.IS":"Mavi Giyim",       "MGROS.IS":"Migros",
    "MIATK.IS":"Mia Teknoloji",   "MPARK.IS":"MLP Sağlık",
    "ODAS.IS":"ODAS Elektrik",    "OTKAR.IS":"Otokar",
    "PAGYO.IS":"Pasifik GYO",     "PETKM.IS":"Petkim",
    "PGSUS.IS":"Pegasus",         "QUAGR.IS":"Qua Granite",
    "REEDR.IS":"Reeder Teknoloji","SAHOL.IS":"Sabancı Holding",
    "SARKY.IS":"Sarkuysan",       "SASA.IS":"SASA Polyester",
    "SISE.IS":"Şişecam",          "SKBNK.IS":"Şekerbank",
    "SOKM.IS":"Şok Marketler",    "TABGD.IS":"Tab Gıda",
    "TAVHL.IS":"TAV Havalimanları","TCELL.IS":"Turkcell",
    "THYAO.IS":"Türk Hava Yolları","TKFEN.IS":"Tekfen Holding",
    "TOASO.IS":"Tofaş Oto",       "TSKB.IS":"TSKB",
    "TTKOM.IS":"Türk Telekom",    "TUKAS.IS":"Tukaş Gıda",
    "TUPRS.IS":"Tüpraş",          "ULKER.IS":"Ülker Bisküvi",
    "VAKBN.IS":"Vakıfbank",       "VESTL.IS":"Vestel",
    "YKBNK.IS":"Yapı Kredi",      "ZOREN.IS":"Zorlu Enerji",
    "ALTIN.IS":"Altınay Savunma", "BALSU.IS":"Balsu Gıda",
    "DSFKTR.IS":"Destek Finans",  "GRTHO.IS":"Grainturk Holding",
    "KLGYO.IS":"Kiler Holding",   "OBAMD.IS":"Oba Makarna",
    "PASEU.IS":"Pasifik Eurasia", "PSKGYO.IS":"Pasifik GYO",
    "TURKS.IS":"Tureks Turizm",   "YAZIC.IS":"AG Anadolu Group",
    "MRDIN.IS":"Oyak Çimento",    "GUSGR.IS":"Türkiye Sigorta",
    "CAN2T.IS":"Can2 Termik",     "EUPWR.IS":"Europower",
}

# ── S&P 500 fallback (top 50) ─────────────────────────────────────────────────
SP500_FALLBACK = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","AMZN":"Amazon",
    "META":"Meta","GOOGL":"Alphabet A","GOOG":"Alphabet C","BRK-B":"Berkshire B",
    "LLY":"Eli Lilly","JPM":"JPMorgan","V":"Visa","XOM":"ExxonMobil",
    "UNH":"UnitedHealth","TSLA":"Tesla","MA":"Mastercard","PG":"P&G",
    "COST":"Costco","JNJ":"J&J","HD":"Home Depot","MRK":"Merck",
    "ABBV":"AbbVie","CVX":"Chevron","CRM":"Salesforce","BAC":"Bank of America",
    "WMT":"Walmart","NFLX":"Netflix","AMD":"AMD","KO":"Coca-Cola",
    "PEP":"PepsiCo","TMO":"Thermo Fisher","ACN":"Accenture","MCD":"McDonald's",
    "ORCL":"Oracle","CSCO":"Cisco","ABT":"Abbott","LIN":"Linde",
    "ADBE":"Adobe","GE":"GE Aerospace","DHR":"Danaher","TXN":"Texas Instruments",
    "PM":"Philip Morris","AMGN":"Amgen","CAT":"Caterpillar","INTU":"Intuit",
    "IBM":"IBM","SPGI":"S&P Global","NOW":"ServiceNow","GS":"Goldman Sachs",
    "ISRG":"Intuitive Surgical","BKNG":"Booking Holdings",
}

FREQ_OPTIONS = {
    "1 Hour":  {"period": "60d",  "interval": "1h"},
    "1 Day":   {"period": "2y",   "interval": "1d"},
    "1 Week":  {"period": "5y",   "interval": "1wk"},
}

SIG_COLORS = {
    "Strong Buy": "#00C853", "Buy": "#26A69A",
    "Hold": "#FFD740", "Sell": "#FF6D00",
    "Strong Sell": "#D50000", "N/A": "#555555",
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}

.hdr{background:linear-gradient(135deg,#1a1f3a,#0d1117);
  border-bottom:2px solid #2E75B6;padding:.9rem 2rem .7rem;
  margin:-1rem -1rem 1rem -1rem;}
.hdr h1{margin:0;font-size:1.4rem;font-weight:700;
  background:linear-gradient(90deg,#63b3ed,#68d391);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.hdr p{margin:.1rem 0 0;color:#718096;font-size:.76rem;}

/* sidebar section label */
.ss{font-size:.66rem;font-weight:700;letter-spacing:.1em;color:#63b3ed;
  text-transform:uppercase;padding:.5rem 0 .1rem;border-top:1px solid #2d3748;margin-top:.4rem;}

/* metric card */
.mc{background:#161b2e;border:1px solid #2d3748;border-radius:8px;
  padding:.7rem .85rem;text-align:center;}
.mc .lb{font-size:.62rem;color:#718096;text-transform:uppercase;
  letter-spacing:.07em;margin-bottom:.18rem;}
.mc .vl{font-size:1.15rem;font-weight:700;}
.mc .sb{font-size:.65rem;color:#718096;margin-top:.1rem;}

/* signal badge */
.sig{display:inline-block;padding:.18rem .6rem;border-radius:20px;
  font-size:.72rem;font-weight:600;letter-spacing:.03em;}
.sig-strong-buy {background:#003d1f;color:#00C853;border:1px solid #00C853;}
.sig-buy        {background:#0d2e2a;color:#26A69A;border:1px solid #26A69A;}
.sig-hold       {background:#3a3000;color:#FFD740;border:1px solid #FFD740;}
.sig-sell       {background:#3a1a00;color:#FF6D00;border:1px solid #FF6D00;}
.sig-strong-sell{background:#3a0000;color:#FF5252;border:1px solid #FF5252;}
.sig-na         {background:#1a1a1a;color:#888;border:1px solid #444;}

.srcnote{font-size:.68rem;color:#4a5568;border:1px solid #2d3748;
  border-radius:5px;padding:.35rem .7rem;margin-bottom:.5rem;}

.footer{text-align:center;color:#4a5568;font-size:.68rem;
  padding:.9rem 0;border-top:1px solid #1a202c;margin-top:1rem;}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# CONSTITUENT FETCHING  (live, cached 24 h)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_bist100_live() -> dict:
    """
    Fetches https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv
    The CSV contains tickers like 'AKSEN.E' (with Borsa Istanbul market code).
    We strip the market-code suffix (.E, .F, .C, .D etc.) before adding .IS.
    Falls back to BIST100_FALLBACK on any error.
    """
    import urllib.request, ssl, re
    try:
        url = "https://www.borsaistanbul.com/datum/hisse_endeks_ds.csv"
        hdrs = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept": "text/csv,*/*",
            "Referer": "https://www.borsaistanbul.com/en/indices/bist-stock-indices",
        }
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            raw = r.read()

        for enc in ("utf-8-sig", "utf-8", "windows-1252", "iso-8859-9"):
            try: text = raw.decode(enc); break
            except: pass
        else:
            return BIST100_FALLBACK

        df = pd.read_csv(io.StringIO(text), sep=";", dtype=str, on_bad_lines="skip")
        df.columns = [c.strip().upper() for c in df.columns]

        # Identify columns by pattern
        ticker_col = next((c for c in df.columns
                           if any(k in c for k in ("TICKER","KOD","SEMBOL","SYMBOL","CODE"))), None)
        index_col  = next((c for c in df.columns
                           if any(k in c for k in ("ENDEKS","INDEX","INDICE"))), None)
        name_col   = next((c for c in df.columns
                           if any(k in c for k in ("ISIM","NAME","SIRKET","UNVAN","COMPANY","ACIKLAMA"))), None)

        if not ticker_col or not index_col:
            return BIST100_FALLBACK

        # Filter XU100 rows
        bdf = df[df[index_col].str.strip().str.upper() == "XU100"]
        if bdf.empty:
            return BIST100_FALLBACK

        result = {}
        for _, row in bdf.iterrows():
            raw_ticker = str(row[ticker_col]).strip().upper()
            # Strip Borsa Istanbul market-segment suffix: AKSEN.E → AKSEN
            clean = re.sub(r'\.[A-Z]{1,2}$', '', raw_ticker)
            name  = str(row[name_col]).strip() if name_col and name_col in row else clean
            result[f"{clean}.IS"] = name

        return result if len(result) >= 50 else BIST100_FALLBACK

    except Exception:
        return BIST100_FALLBACK


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sp500_live() -> dict:
    """GitHub datasets/s-and-p-500-companies — updated daily, 503 tickers."""
    import urllib.request
    try:
        url = ("https://raw.githubusercontent.com/datasets/"
               "s-and-p-500-companies/main/data/constituents.csv")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(text))
        sym  = "Symbol"   if "Symbol"   in df.columns else df.columns[0]
        name = "Security" if "Security" in df.columns else df.columns[1]
        result = {str(r[sym]).replace(".", "-"): str(r[name]) for _, r in df.iterrows()}
        return result if len(result) >= 400 else SP500_FALLBACK
    except Exception:
        return SP500_FALLBACK

# ─────────────────────────────────────────────────────────────────────────────
# PRICE DATA
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(full_ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Universal OHLCV fetch. Single retry with short sleep on failure."""
    for attempt in range(2):
        try:
            df = yf.download(
                full_ticker, period=period, interval=interval,
                auto_adjust=True, progress=False, threads=False,
            )
            if df is None or df.empty:
                if attempt == 0: time.sleep(0.5)
                continue

            # Flatten MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = df.columns.get_level_values(0).astype(str)
                lvl1 = df.columns.get_level_values(1).astype(str)
                # Level that contains field names (Open/High/Low/Close/Volume)
                fields = {"Open","High","Low","Close","Volume","Adj Close"}
                df.columns = lvl0 if len(fields & set(lvl0.values)) >= 3 else lvl1

            df.columns = [str(c).lower() for c in df.columns]
            if not {"open","high","low","close"}.issubset(set(df.columns)):
                if attempt == 0: time.sleep(0.5)
                continue

            df.index = pd.to_datetime(df.index)
            df = df.dropna(subset=["close"])
            if not df.empty:
                return df

            if attempt == 0: time.sleep(0.5)
        except Exception:
            if attempt == 0: time.sleep(0.5)

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
    if any(pd.isna(x) for x in [m, s, h]): return 0
    return max(-2, min(2, (1 if m > s else -1) + (1 if h > 0 else -1)))

def _s_cci(v):
    if pd.isna(v): return 0
    if v >= 200: return  2
    if v >= 100: return  1
    if v <=-200: return -2
    if v <=-100: return -1
    return 0

def _s_mom_pct(pct):
    """Momentum as % change — price-agnostic, works for any market/currency."""
    if pd.isna(pct): return 0
    if pct >  3.0: return  2   # > +3%
    if pct >  0.0: return  1   # > 0%
    if pct < -3.0: return -2   # < -3%
    return -1                  # < 0%

def _s_stoch(k, d):
    if any(pd.isna(x) for x in [k, d]): return 0
    if k < 20 and d < 20: return  2
    if k > 80 and d > 80: return -2
    if k < 20: return  1
    if k > 80: return -1
    return 1 if k > d else -1

def _s_willr(v):
    if pd.isna(v): return 0
    if v <= -80: return  2
    if v <= -50: return  1
    if v >= -20: return -2
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
        d = df.tail(200).copy()   # 200 rows: enough for slow MACD + buffer
        mf, ms, mg = p["macd_fast"], p["macd_slow"], p["macd_sig"]
        rl, ml, cl = p["rsi_len"], p["mom_len"], p["cci_len"]
        sk, sd, wl = p["stoch_k"], p["stoch_d"], p["willr_len"]

        macd_df = ta.macd(d["close"], fast=mf, slow=ms, signal=mg)
        rsi     = ta.rsi(d["close"], length=rl)
        mom     = ta.mom(d["close"], length=ml)
        cci     = ta.cci(d["high"], d["low"], d["close"], length=cl)
        stoch   = ta.stoch(d["high"], d["low"], d["close"], k=sk, d=sd)
        willr   = ta.willr(d["high"], d["low"], d["close"], length=wl)

        # Momentum as % change (price-agnostic fix)
        close_n_ago = d["close"].shift(ml)
        mom_pct_series = (mom / close_n_ago.replace(0, float("nan"))) * 100

        # Dynamic MACD column names (depend on fast/slow/signal params)
        macd_col  = f"MACD_{mf}_{ms}_{mg}"
        macds_col = f"MACDs_{mf}_{ms}_{mg}"
        macdh_col = f"MACDh_{mf}_{ms}_{mg}"
        stk_col   = f"STOCHk_{sk}_{sd}_{sd}"
        std_col   = f"STOCHd_{sk}_{sd}_{sd}"

        sm  = _s_macd(macd_df[macd_col].iloc[-1],
                      macd_df[macds_col].iloc[-1],
                      macd_df[macdh_col].iloc[-1])
        sr  = _s_rsi(rsi.iloc[-1])
        smo = _s_mom_pct(float(mom_pct_series.iloc[-1]))
        sc  = _s_cci(cci.iloc[-1])
        ss  = _s_stoch(stoch[stk_col].iloc[-1], stoch[std_col].iloc[-1])
        sw  = _s_willr(willr.iloc[-1])
        total = sr + sm + sc + smo + ss + sw

        return {
            "signal": _label(total), "score": total,
            "ind_series": {
                "macd": macd_df, "rsi": rsi, "mom_pct": mom_pct_series,
                "cci": cci, "stoch": stoch, "willr": willr,
                "macd_col": macd_col, "macds_col": macds_col,
                "macdh_col": macdh_col, "stk_col": stk_col, "std_col": std_col,
            },
            "details": {
                "RSI":         (sr,  round(float(rsi.iloc[-1]), 2)),
                "MACD":        (sm,  round(float(macd_df[macd_col].iloc[-1]), 4)),
                "CCI":         (sc,  round(float(cci.iloc[-1]), 2)),
                "Momentum%":   (smo, round(float(mom_pct_series.iloc[-1]), 2)),
                "Stochastic":  (ss,  round(float(stoch[stk_col].iloc[-1]), 2)),
                "Williams%R":  (sw,  round(float(willr.iloc[-1]), 2)),
            },
        }
    except Exception:
        return empty


def one_row(full_ticker, name, atype, region, period, interval, p) -> dict:
    base = {"Ticker": full_ticker, "Name": name, "Type": atype, "Region": region,
            "Price": None, "Change%": None, "Signal": "N/A", "Score": 0,
            "RSI": 0, "MACD": 0, "CCI": 0, "Momentum%": 0,
            "Stochastic": 0, "Williams%R": 0}
    df = fetch_data(full_ticker, period, interval)
    if df.empty or len(df) < 35: return base
    sig   = compute_signal(df, p)
    price = float(df["close"].iloc[-1])
    chg   = float((df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100) if len(df) > 1 else 0.0
    row   = {**base,
             "Price":   round(price, 4 if price < 10 else 2),
             "Change%": round(chg, 2),
             "Signal":  sig["signal"],
             "Score":   sig["score"]}
    for k, (sc, _) in sig.get("details", {}).items():
        row[k] = sc
    return row

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS  (with rangebreaks to remove weekend/overnight gaps)
# ─────────────────────────────────────────────────────────────────────────────

def build_charts(df: pd.DataFrame, ind: dict,
                 ticker: str, name: str, interval: str) -> go.Figure:
    fig = make_subplots(
        rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.022,
        row_heights=[3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2],
        subplot_titles=[
            f"{ticker} — {name}", "MACD", "RSI (14)",
            "Momentum % (10)", "CCI (20)", "Stochastic (14/3)", "Williams %R (14)",
        ],
    )

    # ── Candlestick ───────────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        increasing_line_color="#26A69A", decreasing_line_color="#EF5350",
        showlegend=False, name="Price",
    ), row=1, col=1)

    # ── MACD ─────────────────────────────────────────────────────────────────
    md = ind["macd"]
    hc, mc, sc_col = ind["macdh_col"], ind["macd_col"], ind["macds_col"]
    h  = md[hc]
    fig.add_trace(go.Bar(x=df.index, y=h, showlegend=False,
        marker_color=["#26A69A" if v >= 0 else "#EF5350" for v in h],
        name="Hist"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=md[mc],
        line=dict(color="#2962FF", width=1.3), name="MACD"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=md[sc_col],
        line=dict(color="#FF6D00", width=1.2, dash="dot"), name="Signal"), row=2, col=1)

    # ── RSI ───────────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(x=df.index, y=ind["rsi"],
        line=dict(color="#AB47BC", width=1.5), showlegend=False), row=3, col=1)
    for lv, c in [(70, "rgba(239,83,80,.4)"), (30, "rgba(38,166,154,.4)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="grey",
                  line_width=.6, row=3, col=1)

    # ── Momentum % ────────────────────────────────────────────────────────────
    mom_pct = ind["mom_pct"]
    fig.add_trace(go.Bar(x=df.index, y=mom_pct, showlegend=False,
        marker_color=["#26A69A" if v >= 0 else "#EF5350" for v in mom_pct],
        name="Mom%"), row=4, col=1)
    for lv, c in [(3, "rgba(239,83,80,.35)"), (-3, "rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="grey",
                  line_width=.6, row=4, col=1)

    # ── CCI ───────────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(x=df.index, y=ind["cci"],
        line=dict(color="#FFA726", width=1.5), showlegend=False), row=5, col=1)
    for lv, c in [(100, "rgba(239,83,80,.35)"), (-100, "rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=5, col=1)

    # ── Stochastic ────────────────────────────────────────────────────────────
    stk, std = ind["stk_col"], ind["std_col"]
    fig.add_trace(go.Scatter(x=df.index, y=ind["stoch"][stk],
        line=dict(color="#42A5F5", width=1.5), name="%K"), row=6, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ind["stoch"][std],
        line=dict(color="#EF5350", width=1.2, dash="dot"), name="%D"), row=6, col=1)
    for lv, c in [(80, "rgba(239,83,80,.35)"), (20, "rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=6, col=1)

    # ── Williams %R ───────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(x=df.index, y=ind["willr"],
        line=dict(color="#EC407A", width=1.5), showlegend=False), row=7, col=1)
    for lv, c in [(-20, "rgba(239,83,80,.35)"), (-80, "rgba(38,166,154,.35)")]:
        fig.add_hline(y=lv, line_dash="dash", line_color=c, row=7, col=1)

    # ── Rangebreaks: remove weekends + overnight gaps ─────────────────────────
    rb_daily  = [dict(bounds=["sat", "mon"])]          # weekends
    rb_hourly = [dict(bounds=["sat", "mon"]),           # weekends
                 dict(bounds=[21, 9], pattern="hour")]  # outside ~trading hours
    rb = rb_hourly if interval == "1h" else rb_daily

    fig.update_layout(
        height=1080,
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        font=dict(color="#FAFAFA", family="Inter,sans-serif", size=11),
        xaxis_rangeslider_visible=False,
        margin=dict(l=55, r=20, t=38, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", x=0, y=1.01,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    )
    for i in range(1, 8):
        fig.update_xaxes(
            showgrid=True, gridcolor="#1E2130", gridwidth=.5,
            rangebreaks=rb, row=i, col=1,
        )
        fig.update_yaxes(
            showgrid=True, gridcolor="#1E2130", gridwidth=.5,
            zeroline=False, row=i, col=1,
        )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def sidebar() -> dict:
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        st.markdown('<div class="ss">Timeframe</div>', unsafe_allow_html=True)
        freq = st.selectbox("tf", list(FREQ_OPTIONS.keys()),
                            index=1, label_visibility="collapsed")

        st.markdown('<div class="ss">Indicator Parameters</div>',
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

        # ── Page 1 market selections ─────────────────────────────────────────
        # Pattern: one expander per class; first row = "Select all" toggle,
        # then one checkbox per item (grouped by sub-category where relevant).
        st.markdown('<div class="ss">Page 1 — Market Selection</div>',
                    unsafe_allow_html=True)

        # ── Indices ───────────────────────────────────────────────────────────
        with st.expander("🌍 Indices", expanded=True):
            all_idx = st.checkbox("Select all indices", value=True, key="all_idx")
            st.markdown("---")
            regions = {}
            for name, m in INDICES.items():
                regions.setdefault(m["region"], []).append(name)
            sel_idx = []
            for reg, names in regions.items():
                st.caption(reg)
                for name in names:
                    default = all_idx if all_idx else st.session_state.get(f"idx_{name}", True)
                    if st.checkbox(name, value=all_idx, key=f"idx_{name}"):
                        sel_idx.append(name)

        # ── Commodities ───────────────────────────────────────────────────────
        with st.expander("🏅 Commodities", expanded=False):
            all_com = st.checkbox("Select all commodities", value=True, key="all_com")
            st.markdown("---")
            subs = {}
            for name, m in COMMODITIES.items():
                subs.setdefault(m["region"], []).append(name)
            sel_com = []
            for sub, names in subs.items():
                st.caption(sub)
                for name in names:
                    if st.checkbox(name, value=all_com, key=f"com_{name}"):
                        sel_com.append(name)

        # ── Forex ─────────────────────────────────────────────────────────────
        with st.expander("💱 Forex", expanded=False):
            all_fx = st.checkbox("Select all pairs", value=False, key="all_fx")
            st.markdown("---")
            sel_fx = []
            for name in FOREX:
                if st.checkbox(name, value=all_fx, key=f"fx_{name}"):
                    sel_fx.append(name)

        # ── Crypto ────────────────────────────────────────────────────────────
        with st.expander("₿ Crypto", expanded=False):
            all_cr = st.checkbox("Select all crypto", value=False, key="all_cr")
            st.markdown("---")
            sel_cr = []
            for name in CRYPTO:
                if st.checkbox(name, value=all_cr, key=f"cr_{name}"):
                    sel_cr.append(name)

        st.markdown("---")
        if st.button("🗑️ Clear cache", use_container_width=True):
            st.cache_data.clear()
            for k in ["screener_p1", "screener_p2"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.caption(f"Cache: 1h  •  {datetime.now().strftime('%H:%M %d %b')}")

    p = dict(
        freq=freq,
        period=FREQ_OPTIONS[freq]["period"],
        interval=FREQ_OPTIONS[freq]["interval"],
        rsi_len=rsi_len, macd_fast=macd_fast, macd_slow=macd_slow,
        macd_sig=macd_sig, cci_len=cci_len, mom_len=mom_len,
        stoch_k=stoch_k, stoch_d=stoch_d, willr_len=willr_len,
        sel_idx=sel_idx, sel_com=sel_com, sel_fx=sel_fx, sel_cr=sel_cr,
    )
    return p

# ─────────────────────────────────────────────────────────────────────────────
# SHARED TABLE RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_table(df_all: pd.DataFrame):
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        tf = st.multiselect("Type", sorted(df_all["Type"].unique()), default=[])
    with f2:
        sf = st.multiselect("Signal",
            ["Strong Buy","Buy","Hold","Sell","Strong Sell"], default=[])
    with f3:
        sb = st.selectbox("Sort by", ["Score","Change%","Ticker","Type"])
    with f4:
        asc = st.radio("Order", ["Desc","Asc"], horizontal=True) == "Asc"

    disp = df_all.copy()
    if tf: disp = disp[disp["Type"].isin(tf)]
    if sf: disp = disp[disp["Signal"].isin(sf)]
    disp = disp.sort_values(sb, ascending=asc).reset_index(drop=True)

    counts = df_all["Signal"].value_counts()
    bc = st.columns(5)
    for i, sig in enumerate(["Strong Buy","Buy","Hold","Sell","Strong Sell"]):
        cnt  = counts.get(sig, 0)
        col  = SIG_COLORS[sig]
        pct  = round(cnt / len(df_all) * 100) if len(df_all) else 0
        with bc[i]:
            st.markdown(
                f'<div class="mc"><div class="lb">{sig}</div>'
                f'<div class="vl" style="color:{col}">{cnt}</div>'
                f'<div class="sb">{pct}%</div></div>',
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    ind_cols = ["RSI","MACD","CCI","Momentum%","Stochastic","Williams%R"]
    show = ["Ticker","Name","Type","Region","Price","Change%",
            "Signal","Score"] + ind_cols

    def cs(v):
        c = SIG_COLORS.get(v, "")
        return f"color:{c};font-weight:600;" if c else ""
    def cc(v):
        if pd.isna(v): return ""
        return "color:#26A69A;" if v >= 0 else "color:#EF5350;"
    def csc(v):
        if pd.isna(v): return ""
        if v >= 2:  return "color:#26A69A;font-weight:600;"
        if v <= -2: return "color:#EF5350;font-weight:600;"
        return "color:#FFD740;"

    styled = (disp[show].style
              .map(cs,  subset=["Signal"])
              .map(cc,  subset=["Change%"])
              .map(csc, subset=["Score"])
              .format({"Price":"{:.2f}","Change%":"{:+.2f}%"}, na_rep="—"))
    st.dataframe(styled, use_container_width=True, height=530)

    csv = disp[show].to_csv(index=False)
    st.download_button("⬇ Export CSV", csv,
        f"ta_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — MARKET OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def page1(p):
    st.markdown("## 📋 Market Overview")

    assets = []
    for name in p["sel_idx"]:
        m = INDICES[name]; assets.append((m["ticker"], name, "Index", m["region"]))
    for name in p["sel_com"]:
        m = COMMODITIES[name]; assets.append((m["ticker"], name, "Commodity", m["region"]))
    for name in p["sel_fx"]:
        m = FOREX[name]; assets.append((m["ticker"], name, "Forex", m["region"]))
    for name in p["sel_cr"]:
        m = CRYPTO[name]; assets.append((m["ticker"], name, "Crypto", m["region"]))

    n = len(assets)
    c1, c2 = st.columns([1, 5])
    with c1:
        run = st.button("▶ Run", type="primary", use_container_width=True)
    with c2:
        st.caption(f"**{n} assets** · Timeframe: **{p['freq']}** · Score range: −12 → +12")

    if run:
        st.session_state.pop("screener_p1", None)
        rows = []; bar = st.progress(0); status = st.empty()
        for i, (t, nm, at, reg) in enumerate(assets):
            status.caption(f"⏳ {t} — {nm}  ({i+1}/{n})")
            rows.append(one_row(t, nm, at, reg, p["period"], p["interval"], p))
            bar.progress((i+1)/n)
        bar.empty(); status.empty()
        st.session_state["screener_p1"] = pd.DataFrame(rows)

    df_all = st.session_state.get("screener_p1")
    if df_all is None or df_all.empty:
        st.caption("Press **Run** to load data.")
        return
    render_table(df_all)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — STOCK SCREENER
# ─────────────────────────────────────────────────────────────────────────────

def page2(p):
    st.markdown("## 📈 Stock Screener")

    c1, c2, c3 = st.columns([1, 1, 3])
    do_bist = c1.checkbox("🇹🇷 BIST 100", value=True)
    do_sp   = c2.checkbox("🇺🇸 S&P 500",  value=False)
    c3.markdown(
        '<div class="srcnote">📡 <b>BIST 100</b>: Borsa Istanbul official CSV (live, daily) · '
        '<b>S&P 500</b>: GitHub/datasets (live, daily) · Fallback to hardcoded list on error</div>',
        unsafe_allow_html=True)

    if not do_bist and not do_sp:
        st.info("Select at least one market above.")
        return

    with st.spinner("Checking constituent lists…"):
        bist_u = fetch_bist100_live() if do_bist else {}
        sp_u   = fetch_sp500_live()   if do_sp   else {}

    info = []
    if do_bist:
        src = "live" if bist_u is not BIST100_FALLBACK else "fallback"
        info.append(f"BIST 100: **{len(bist_u)} stocks** ({src})")
    if do_sp:
        src = "live" if sp_u is not SP500_FALLBACK else "fallback"
        info.append(f"S&P 500: **{len(sp_u)} stocks** ({src})")
    st.markdown("  •  ".join(info))

    assets = []
    for ft, nm in bist_u.items():
        assets.append((ft, nm, "BIST 100", "🇹🇷 Turkey"))
    for tk, nm in sp_u.items():
        assets.append((tk, nm, "S&P 500", "🇺🇸 US"))

    n = len(assets)
    est = round(n * 0.8 / 60, 1)   # ~0.8s per stock with single retry

    c1, c2 = st.columns([1, 5])
    with c1:
        run2 = st.button("▶ Run Screener", type="primary", use_container_width=True)
    with c2:
        st.caption(f"**{n} stocks** · Est. ~{est} min · Timeframe: **{p['freq']}** · Cached 1 hour")

    if run2:
        st.session_state.pop("screener_p2", None)
        rows = []; bar = st.progress(0); status = st.empty()
        for i, (ft, nm, at, reg) in enumerate(assets):
            status.caption(f"⏳ {ft} — {nm}  ({i+1}/{n})")
            rows.append(one_row(ft, nm, at, reg, p["period"], p["interval"], p))
            bar.progress((i+1)/n)
        bar.empty(); status.empty()
        st.session_state["screener_p2"] = pd.DataFrame(rows)

    df_all = st.session_state.get("screener_p2")
    if df_all is None or df_all.empty:
        st.caption("Press **Run Screener** to load data.")
        return
    render_table(df_all)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — ASSET DETAIL  (improved navigation)
# ─────────────────────────────────────────────────────────────────────────────

def page3(p):
    st.markdown("## 🔍 Asset Detail")

    # ── Collect all screened assets from both pages + permanent macro assets ──
    # Macro assets always available even if screener hasn't been run
    macro = []
    for nm, m in INDICES.items():
        macro.append((m["ticker"], nm, "Index", m["region"]))
    for nm, m in COMMODITIES.items():
        macro.append((m["ticker"], nm, "Commodity", m["region"]))
    for nm, m in FOREX.items():
        macro.append((m["ticker"], nm, "Forex", m["region"]))
    for nm, m in CRYPTO.items():
        macro.append((m["ticker"], nm, "Crypto", m["region"]))

    stock_assets = []
    for key in ("screener_p2",):
        if key in st.session_state:
            df2 = st.session_state[key]
            for _, r in df2.iterrows():
                stock_assets.append((r["Ticker"], r["Name"], r["Type"], r["Region"]))

    all_assets = macro + stock_assets

    # Deduplicate
    seen, unique = set(), []
    for item in all_assets:
        if item[0] not in seen:
            seen.add(item[0]); unique.append(item)

    # ── Category tabs for navigation ──────────────────────────────────────────
    cats = ["🌍 Indices", "🏅 Commodities", "💱 Forex", "₿ Crypto", "📈 Stocks"]
    tabs = st.tabs(cats)

    def assets_in_cat(cat):
        if cat == "🌍 Indices":
            return [a for a in unique if a[2] == "Index"]
        if cat == "🏅 Commodities":
            return [a for a in unique if a[2] == "Commodity"]
        if cat == "💱 Forex":
            return [a for a in unique if a[2] == "Forex"]
        if cat == "₿ Crypto":
            return [a for a in unique if a[2] == "Crypto"]
        if cat == "📈 Stocks":
            return [a for a in unique if a[2] not in
                    ("Index","Commodity","Forex","Crypto")]
        return []

    selected_ticker = None
    for tab, cat in zip(tabs, cats):
        with tab:
            pool = assets_in_cat(cat)
            if not pool:
                if cat == "📈 Stocks":
                    st.info("Run the Stock Screener (Page 2) first to browse stocks here.")
                else:
                    st.info("No assets in this category.")
                continue

            # Text search filter
            search = st.text_input(
                "🔍 Search", placeholder="Type name or ticker…",
                key=f"search_{cat}", label_visibility="collapsed",
            )
            if search:
                q = search.lower()
                pool = [a for a in pool
                        if q in a[0].lower() or q in a[1].lower()]

            # Selectbox
            if pool:
                opts    = [a[0] for a in pool]
                labels  = {a[0]: f"{a[0]}  —  {a[1]}" for a in pool}
                chosen  = st.selectbox(
                    "asset", opts, format_func=lambda t: labels.get(t, t),
                    key=f"sel_{cat}", label_visibility="collapsed",
                )
                if st.button(f"Load chart", key=f"load_{cat}", type="primary"):
                    st.session_state["detail_ticker"] = chosen
                    st.session_state["detail_meta"]   = next(
                        a for a in pool if a[0] == chosen)

    # ── Chart area ────────────────────────────────────────────────────────────
    if "detail_ticker" not in st.session_state:
        st.info("↑ Select an asset from any category above and press **Load chart**.")
        return

    full_ticker = st.session_state["detail_ticker"]
    _, name, atype, region = st.session_state["detail_meta"]

    col_info, col_ref = st.columns([5, 1])
    with col_info:
        st.markdown(f"**{full_ticker}** — {name} &nbsp;|&nbsp; {atype} &nbsp;|&nbsp; {region}")
    with col_ref:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_data.clear(); st.rerun()

    with st.spinner(f"Loading {full_ticker}…"):
        df = fetch_data(full_ticker, p["period"], p["interval"])

    if df.empty:
        st.error(f"No data for **{full_ticker}**. Try Refresh or check the ticker.")
        return

    sig = compute_signal(df, p)
    price   = float(df["close"].iloc[-1])
    chg_pct = float((df["close"].iloc[-1]/df["close"].iloc[-2]-1)*100) if len(df)>1 else 0.
    chg_col = "#26A69A" if chg_pct >= 0 else "#EF5350"
    sc_col  = SIG_COLORS.get(sig["signal"], "#FFD740")
    p_fmt   = f"{price:,.4f}" if price < 10 else f"{price:,.2f}"

    # Header cards
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, (lbl, val, clr) in zip(
        [c1,c2,c3,c4,c5],
        [("Asset", name, "#FAFAFA"), ("Type", atype, "#63b3ed"),
         ("Price", p_fmt, "#FAFAFA"),
         (f"Change ({p['freq']})", f"{chg_pct:+.2f}%", chg_col),
         ("TA Signal", sig["signal"], sc_col)],
    ):
        with col:
            st.markdown(
                f'<div class="mc"><div class="lb">{lbl}</div>'
                f'<div class="vl" style="color:{clr};font-size:1rem;">{val}</div></div>',
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Score breakdown
    with st.expander("📊 Score Breakdown", expanded=True):
        SL = {2:"Strong Buy",1:"Buy",0:"Hold",-1:"Sell",-2:"Strong Sell"}
        bc2 = st.columns(6)
        for i, (k, (sc, vl)) in enumerate(sig.get("details", {}).items()):
            cc = SIG_COLORS.get(SL.get(sc,"Hold"), "#FFD740")
            with bc2[i]:
                st.markdown(
                    f'<div class="mc"><div class="lb">{k}</div>'
                    f'<div class="vl" style="color:{cc}">{sc:+d}</div>'
                    f'<div class="sb">{vl}</div></div>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        total = sig["score"]
        css_cls = sig["signal"].lower().replace(" ", "-")
        st.markdown(
            f"**Composite: {total:+d}** / ±12 &nbsp;"
            f'<span class="sig sig-{css_cls}">{sig["signal"]}</span>',
            unsafe_allow_html=True)
        st.progress(int((total+12)/24*100))

    st.markdown("<br>", unsafe_allow_html=True)

    ind = sig.get("ind_series", {})
    if ind:
        st.plotly_chart(
            build_charts(df, ind, full_ticker, name, p["interval"]),
            use_container_width=True, config={"displayModeBar": True},
        )
    else:
        st.warning("Not enough data for charts (need ≥ 35 bars).")

    with st.expander("📄 Raw data (last 50 bars)"):
        fmt = "%Y-%m-%d %H:%M" if p["interval"] == "1h" else "%Y-%m-%d"
        sd = df.tail(50).copy(); sd.index = sd.index.strftime(fmt)
        st.dataframe(sd.style.format("{:.4f}"), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="hdr"><h1>📊 Global Technical Analysis Dashboard</h1>'
        '<p>Indices · Commodities · Forex · Crypto · BIST 100 · S&P 500 stocks  '
        '•  6 indicators  •  5-level signals</p></div>',
        unsafe_allow_html=True)

    p  = sidebar()
    pg = st.radio("nav",
        ["📋 Market Overview", "📈 Stock Screener", "🔍 Asset Detail"],
        horizontal=True, label_visibility="hidden")
    st.markdown("---")

    if "Overview" in pg:   page1(p)
    elif "Stock"   in pg:  page2(p)
    else:                  page3(p)

    st.markdown(
        f'<div class="footer">Data: Yahoo Finance · Borsa Istanbul · GitHub/datasets  '
        f'•  Indicators: pandas-ta  •  Not financial advice  '
        f'•  {datetime.now().strftime("%d %b %Y %H:%M")}</div>',
        unsafe_allow_html=True)

if __name__ == "__main__":
    main()
