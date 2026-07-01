"""
Global Technical Analysis Dashboard
=====================================
Assets : Indices · BIST Stocks · S&P 500 · NASDAQ 100 · DAX · CAC 40 ·
         FTSE 100 · Commodities · Forex · Crypto
Run    : streamlit run app.py
"""

import time
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global TA Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# ASSET REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
# Each entry: "Display Name" -> {"ticker": "YF_SYMBOL", "currency": "₺/$/ etc"}
# ticker is the EXACT Yahoo Finance symbol (no suffix added automatically)

INDICES = {
    # Turkish
    "BIST 100":        {"ticker": "XU100.IS",  "currency": "₺",  "region": "🇹🇷 Turkey"},
    "BIST 30":         {"ticker": "XU030.IS",  "currency": "₺",  "region": "🇹🇷 Turkey"},
    # US
    "S&P 500":         {"ticker": "^GSPC",     "currency": "$",  "region": "🇺🇸 United States"},
    "NASDAQ 100":      {"ticker": "^NDX",      "currency": "$",  "region": "🇺🇸 United States"},
    "Dow Jones":       {"ticker": "^DJI",      "currency": "$",  "region": "🇺🇸 United States"},
    # Europe
    "EuroStoxx 50":    {"ticker": "^STOXX50E", "currency": "€",  "region": "🇪🇺 Europe"},
    "DAX":             {"ticker": "^GDAXI",    "currency": "€",  "region": "🇩🇪 Germany"},
    "CAC 40":          {"ticker": "^FCHI",     "currency": "€",  "region": "🇫🇷 France"},
    "FTSE 100":        {"ticker": "^FTSE",     "currency": "£",  "region": "🇬🇧 UK"},
    # Asia-Pacific
    "Nikkei 225":      {"ticker": "^N225",     "currency": "¥",  "region": "🇯🇵 Japan"},
    "Hang Seng":       {"ticker": "^HSI",      "currency": "HK$","region": "🇭🇰 Hong Kong"},
    "Shanghai Comp":   {"ticker": "000001.SS", "currency": "¥",  "region": "🇨🇳 China"},
    "KOSPI":           {"ticker": "^KS11",     "currency": "₩",  "region": "🇰🇷 Korea"},
    "ASX 200":         {"ticker": "^AXJO",     "currency": "A$", "region": "🇦🇺 Australia"},
    "SENSEX":          {"ticker": "^BSESN",    "currency": "₹",  "region": "🇮🇳 India"},
}

COMMODITIES = {
    # Metals
    "Gold":            {"ticker": "GC=F",      "currency": "$",  "region": "⛏️ Metals"},
    "Silver":          {"ticker": "SI=F",      "currency": "$",  "region": "⛏️ Metals"},
    "Copper":          {"ticker": "HG=F",      "currency": "$",  "region": "⛏️ Metals"},
    "Platinum":        {"ticker": "PL=F",      "currency": "$",  "region": "⛏️ Metals"},
    "Palladium":       {"ticker": "PA=F",      "currency": "$",  "region": "⛏️ Metals"},
    # Energy
    "Oil WTI":         {"ticker": "CL=F",      "currency": "$",  "region": "🛢️ Energy"},
    "Oil Brent":       {"ticker": "BZ=F",      "currency": "$",  "region": "🛢️ Energy"},
    "Natural Gas":     {"ticker": "NG=F",      "currency": "$",  "region": "🛢️ Energy"},
    # Agri
    "Wheat":           {"ticker": "ZW=F",      "currency": "$",  "region": "🌾 Agriculture"},
    "Corn":            {"ticker": "ZC=F",      "currency": "$",  "region": "🌾 Agriculture"},
    "Soybeans":        {"ticker": "ZS=F",      "currency": "$",  "region": "🌾 Agriculture"},
    "Coffee":          {"ticker": "KC=F",      "currency": "$",  "region": "🌾 Agriculture"},
    "Sugar":           {"ticker": "SB=F",      "currency": "$",  "region": "🌾 Agriculture"},
    "Cotton":          {"ticker": "CT=F",      "currency": "$",  "region": "🌾 Agriculture"},
}

CRYPTO = {
    "Bitcoin":         {"ticker": "BTC-USD",   "currency": "$",  "region": "₿ Crypto"},
    "Ethereum":        {"ticker": "ETH-USD",   "currency": "$",  "region": "₿ Crypto"},
    "BNB":             {"ticker": "BNB-USD",   "currency": "$",  "region": "₿ Crypto"},
    "Solana":          {"ticker": "SOL-USD",   "currency": "$",  "region": "₿ Crypto"},
    "XRP":             {"ticker": "XRP-USD",   "currency": "$",  "region": "₿ Crypto"},
}

FOREX = {
    "EUR/USD":         {"ticker": "EURUSD=X",  "currency": "",   "region": "💱 Forex"},
    "GBP/USD":         {"ticker": "GBPUSD=X",  "currency": "",   "region": "💱 Forex"},
    "USD/JPY":         {"ticker": "JPY=X",     "currency": "",   "region": "💱 Forex"},
    "USD/TRY":         {"ticker": "TRY=X",     "currency": "",   "region": "💱 Forex"},
    "USD/CNY":         {"ticker": "CNY=X",     "currency": "",   "region": "💱 Forex"},
    "USD/CHF":         {"ticker": "CHF=X",     "currency": "",   "region": "💱 Forex"},
    "USD Index (DXY)": {"ticker": "DX-Y.NYB",  "currency": "",   "region": "💱 Forex"},
}

# ── Equity constituents ───────────────────────────────────────────────────────
# These are fetched dynamically from Wikipedia but have hardcoded fallbacks.
# Tickers here are BASE symbols; fetch_equity() appends the correct suffix.

BIST_STOCKS = {
    "THYAO": "Türk Hava Yolları",   "EREGL": "Ereğli Demir Çelik",
    "AKBNK": "Akbank",              "GARAN": "Garanti Bankası",
    "ISCTR": "İş Bankası C",        "YKBNK": "Yapı Kredi",
    "HALKB": "Halkbank",            "VAKBN": "Vakıfbank",
    "KRDMD": "Kardemir D",          "SISE":  "Şişe Cam",
    "TOASO": "Tofaş Oto",           "FROTO": "Ford Otosan",
    "ARCLK": "Arçelik",             "BIMAS": "BİM Mağazalar",
    "MGROS": "Migros",              "SODA":  "Soda Sanayii",
    "TUPRS": "Tüpraş",              "PETKM": "Petkim",
    "AEFES": "Anadolu Efes",        "SAHOL": "Sabancı Holding",
    "KCHOL": "Koç Holding",         "EKGYO": "Emlak Konut GYO",
    "ENKAI": "Enka İnşaat",         "CCOLA": "Coca-Cola İçecek",
    "DOHOL": "Doğan Holding",       "TTKOM": "Türk Telekom",
    "TCELL": "Turkcell",            "ASELS": "Aselsan",
    "OTKAR": "Otokar",              "PGSUS": "Pegasus",
    "LOGO":  "Logo Yazılım",        "KOZAL": "Koza Altın",
    "KOZAA": "Koza Anadolu Metal",  "IPEKE": "İpek Doğal Enerji",
    "ZOREN": "Zorlu Enerji",        "AKSEN": "Aksa Enerji",
    "BRISA": "Brisa",               "CIMSA": "Çimsa",
    "AKCNS": "Akçansa",             "GUBRF": "Gübre Fabrikaları",
    "GWIND": "Galata Wind",         "MAVI":  "Mavi Giyim",
    "MPARK": "MLP Sağlık",          "KORDS": "Kordsa",
    "CLEBI": "Çelebi Hava Servisi", "ANSGR": "Anadolu Sigorta",
    "ANHYT": "Anadolu Hayat",       "ANACM": "Anadolu Cam",
    "ALARK": "Alarko Holding",      "DEVA":  "Deva Holding",
}

# Top 50 S&P 500 by market cap (fallback; refreshed dynamically if Wikipedia works)
SP500_FALLBACK = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","AMZN":"Amazon",
    "META":"Meta","GOOGL":"Alphabet A","GOOG":"Alphabet C","BRK-B":"Berkshire B",
    "LLY":"Eli Lilly","JPM":"JPMorgan","V":"Visa","XOM":"ExxonMobil",
    "UNH":"UnitedHealth","TSLA":"Tesla","MA":"Mastercard","PG":"Procter & Gamble",
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

# Top 30 NASDAQ 100 by market cap (fallback)
NDX_FALLBACK = {
    "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","AMZN":"Amazon",
    "META":"Meta","GOOGL":"Alphabet A","GOOG":"Alphabet C","TSLA":"Tesla",
    "AVGO":"Broadcom","COST":"Costco","NFLX":"Netflix","AMD":"AMD",
    "ADBE":"Adobe","PEP":"PepsiCo","CSCO":"Cisco","QCOM":"Qualcomm",
    "INTU":"Intuit","TXN":"Texas Instruments","AMGN":"Amgen","ISRG":"Intuitive Surgical",
    "HON":"Honeywell","CMCSA":"Comcast","BKNG":"Booking Holdings","VRTX":"Vertex Pharma",
    "MU":"Micron","PANW":"Palo Alto","ADP":"ADP","LRCX":"Lam Research",
    "SBUX":"Starbucks","MELI":"MercadoLibre",
}

# Top 40 DAX (all 40 constituents)
DAX_STOCKS = {
    "ADS.DE":"Adidas",       "AIR.DE":"Airbus",        "ALV.DE":"Allianz",
    "BAS.DE":"BASF",         "BAYN.DE":"Bayer",         "BMW.DE":"BMW",
    "BNR.DE":"Brenntag",     "CON.DE":"Continental",    "1COV.DE":"Covestro",
    "DBK.DE":"Deutsche Bank","DB1.DE":"Deutsche Börse", "DPW.DE":"DHL Group",
    "DTE.DE":"Deutsche Telekom","ENR.DE":"Siemens Energy","EOAN.DE":"E.ON",
    "FRE.DE":"Fresenius",    "FME.DE":"Fresenius Med",  "HNR1.DE":"Hannover Re",
    "HEI.DE":"HeidelbergMat","HEN3.DE":"Henkel",        "IFX.DE":"Infineon",
    "LHA.DE":"Lufthansa",    "MBG.DE":"Mercedes-Benz",  "MRK.DE":"Merck KGaA",
    "MTX.DE":"MTU Aero",     "MUV2.DE":"Munich Re",     "P911.DE":"Porsche",
    "PAH3.DE":"Porsche Auto", "QGEN.DE":"Qiagen",        "RHM.DE":"Rheinmetall",
    "RWE.DE":"RWE",          "SAP.DE":"SAP",            "SHL.DE":"Siemens Health",
    "SIE.DE":"Siemens",      "SY1.DE":"Symrise",        "VOW3.DE":"Volkswagen",
    "VNA.DE":"Vonovia",      "ZAL.DE":"Zalando",        "BEI.DE":"Beiersdorf",
    "MAN.DE":"MAN",
}

# CAC 40 constituents
CAC40_STOCKS = {
    "AI.PA":"Air Liquide",   "AIR.PA":"Airbus",         "ALO.PA":"Alstom",
    "MT.AS":"ArcelorMittal", "CS.PA":"AXA",             "BNP.PA":"BNP Paribas",
    "EN.PA":"Bouygues",      "CAP.PA":"Capgemini",       "CA.PA":"Carrefour",
    "ACA.PA":"Crédit Agricole","BN.PA":"Danone",         "DSY.PA":"Dassault Sys",
    "ENGI.PA":"Engie",       "EL.PA":"EssilorLuxottica", "RMS.PA":"Hermès",
    "KER.PA":"Kering",       "OR.PA":"L'Oréal",          "LR.PA":"Legrand",
    "MC.PA":"LVMH",          "MLM.PA":"Michelin",        "ORA.PA":"Orange",
    "RI.PA":"Pernod Ricard", "PUB.PA":"Publicis",        "RNO.PA":"Renault",
    "SAF.PA":"Safran",       "SGO.PA":"Saint-Gobain",    "SAN.PA":"Sanofi",
    "SU.PA":"Schneider",     "GLE.PA":"Société Générale","STLAM.MI":"Stellantis",
    "STM.PA":"STMicro",      "TEP.PA":"Teleperformance", "HO.PA":"Thales",
    "TTE.PA":"TotalEnergies","URW.AS":"Unibail-Rodamco", "VIE.PA":"Veolia",
    "DG.PA":"Vinci",         "VIV.PA":"Vivendi",         "WLN.PA":"Worldline",
    "FR.PA":"Valeo",
}

# FTSE 100 top 40 by market cap
FTSE_STOCKS = {
    "AZN.L":"AstraZeneca",   "SHEL.L":"Shell",          "HSBA.L":"HSBC",
    "ULVR.L":"Unilever",     "BP.L":"BP",               "GSK.L":"GSK",
    "RIO.L":"Rio Tinto",     "BHP.L":"BHP",             "REL.L":"RELX",
    "DGE.L":"Diageo",        "NG.L":"National Grid",    "VOD.L":"Vodafone",
    "LLOY.L":"Lloyds",       "BARC.L":"Barclays",       "NWG.L":"NatWest",
    "PRU.L":"Prudential",    "AAL.L":"Anglo American",  "GLEN.L":"Glencore",
    "CPG.L":"Compass",       "LSEG.L":"London Stock Ex","CNA.L":"Centrica",
    "WPP.L":"WPP",           "IMB.L":"Imperial Brands", "BATS.L":"BAT",
    "MNG.L":"M&G",           "EXPN.L":"Experian",       "STAN.L":"Standard Chart",
    "ABDN.L":"abrdn",        "BA.L":"BAE Systems",      "RR.L":"Rolls-Royce",
    "INF.L":"Informa",       "III.L":"3i Group",        "SGRO.L":"Segro",
    "LAND.L":"Land Securities","BT-A.L":"BT Group",     "TUI.L":"TUI",
    "JD.L":"JD Sports",      "MANU.L":"Manchester Utd", "SKG.L":"Smurfit Kappa",
    "SDKD.L":"SDK",
}

# Map index name → (stock_dict, ticker_suffix)
# suffix: ".IS" for BIST, "" for US, already embedded for others
INDEX_STOCKS = {
    "BIST 100":   (BIST_STOCKS,   ".IS"),
    "BIST 30":    (BIST_STOCKS,   ".IS"),   # subset of BIST 100
    "S&P 500":    (SP500_FALLBACK, ""),
    "NASDAQ 100": (NDX_FALLBACK,   ""),
    "DAX":        (DAX_STOCKS,     ""),     # tickers already include .DE
    "CAC 40":     (CAC40_STOCKS,   ""),     # tickers already include .PA / .AS etc.
    "FTSE 100":   (FTSE_STOCKS,    ""),     # tickers already include .L
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
    "N/A":         "#555555",
}

SIGNAL_EMOJI = {
    "Strong Buy": "🟢", "Buy": "🟩", "Hold": "🟡",
    "Sell": "🟧", "Strong Sell": "🔴", "N/A": "⚪",
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a1f3a 0%, #0d1117 100%);
    border-bottom: 2px solid #2E75B6;
    padding: 1.1rem 2rem 0.9rem 2rem;
    margin: -1rem -1rem 1.2rem -1rem;
}
.main-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(90deg, #63b3ed, #68d391);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.main-header p { margin: 0.15rem 0 0 0; color: #718096; font-size: 0.8rem; }

/* ── Sidebar section headers ── */
.sidebar-section {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    color: #63b3ed; text-transform: uppercase;
    padding: 0.6rem 0 0.2rem 0; margin-top: 0.4rem;
    border-top: 1px solid #2d3748;
}
.sidebar-section:first-of-type { border-top: none; }

/* ── Metric cards ── */
.metric-card {
    background: #161b2e; border: 1px solid #2d3748; border-radius: 10px;
    padding: 0.85rem 1rem; text-align: center; height: 100%;
}
.metric-card .label { font-size: 0.68rem; color: #718096;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.25rem; }
.metric-card .value { font-size: 1.35rem; font-weight: 700; }
.metric-card .sub   { font-size: 0.72rem; color: #718096; margin-top: 0.1rem; }

/* ── Signal badge ── */
.sig-badge {
    display: inline-block; padding: 0.2rem 0.65rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em;
}
.sig-strong-buy  { background:#003d1f; color:#00C853; border:1px solid #00C853; }
.sig-buy         { background:#0d2e2a; color:#26A69A; border:1px solid #26A69A; }
.sig-hold        { background:#3a3000; color:#FFD740; border:1px solid #FFD740; }
.sig-sell        { background:#3a1a00; color:#FF6D00; border:1px solid #FF6D00; }
.sig-strong-sell { background:#3a0000; color:#FF5252; border:1px solid #FF5252; }
.sig-na          { background:#1a1a1a; color:#888888; border:1px solid #555555; }

/* ── Asset-type pill ── */
.type-pill {
    display: inline-block; padding: 0.12rem 0.5rem; border-radius: 12px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.04em;
}
.type-index  { background:#1a2a4a; color:#63b3ed; }
.type-stock  { background:#1a3a2a; color:#68d391; }
.type-commodity { background:#3a2a00; color:#FFD740; }
.type-crypto { background:#2a1a3a; color:#c084fc; }
.type-forex  { background:#1a2e2e; color:#5eead4; }

.footer { text-align:center; color:#4a5568; font-size:0.72rem;
    padding:1.2rem 0; border-top:1px solid #1a202c; margin-top:1.5rem; }

/* ── Page nav tabs ── */
div[data-testid="stHorizontalBlock"] > div { gap: 0.4rem; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(full_ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    Universal fetch: works for indices (^GSPC), BIST (.IS), commodities (GC=F),
    forex (EURUSD=X), crypto (BTC-USD), and European stocks (.DE, .PA, .L).
    Retries once on transient Yahoo throttling.
    """
    last_err = None
    for attempt in range(2):
        try:
            df = yf.download(
                full_ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if df is None or df.empty:
                last_err = "empty_response"
                time.sleep(1.0)
                continue

            # Flatten MultiIndex (yfinance sometimes wraps even single tickers)
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = df.columns.get_level_values(0)
                lvl1 = df.columns.get_level_values(1)
                t = full_ticker
                if t in lvl0.astype(str).values:
                    df.columns = lvl1
                else:
                    df.columns = lvl0

            df.columns = [str(c).lower() for c in df.columns]
            required = {"open", "high", "low", "close"}
            if not required.issubset(set(df.columns)):
                last_err = f"missing_columns"
                time.sleep(1.0)
                continue

            df.index = pd.to_datetime(df.index)
            df = df.dropna(subset=["close"])
            if df.empty:
                last_err = "all_nan"
                time.sleep(1.0)
                continue
            return df

        except Exception as e:
            last_err = str(e)[:120]
            time.sleep(1.0)

    return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sp500_tickers() -> dict:
    """Fetch live S&P 500 constituents from Wikipedia. Falls back to hardcoded list."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        # Column may be 'Symbol' or 'Ticker'
        sym_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
        name_col = "Security" if "Security" in df.columns else df.columns[1]
        result = dict(zip(df[sym_col].str.replace(".", "-", regex=False),
                          df[name_col]))
        return result if len(result) > 400 else SP500_FALLBACK
    except Exception:
        return SP500_FALLBACK


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_ndx_tickers() -> dict:
    """Fetch live NASDAQ 100 constituents from Wikipedia. Falls back to hardcoded list."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            if "Ticker" in t.columns or "Symbol" in t.columns:
                sym_col  = "Ticker" if "Ticker" in t.columns else "Symbol"
                name_col = "Company" if "Company" in t.columns else t.columns[1]
                result = dict(zip(t[sym_col], t[name_col]))
                if len(result) > 90:
                    return result
    except Exception:
        pass
    return NDX_FALLBACK


def get_stock_universe(index_name: str) -> dict[str, str]:
    """Return {full_yf_ticker: display_name} for a given index."""
    if index_name not in INDEX_STOCKS:
        return {}

    stock_dict, suffix = INDEX_STOCKS[index_name]

    # For S&P 500 / NASDAQ 100 try live Wikipedia fetch
    if index_name == "S&P 500":
        stock_dict = fetch_sp500_tickers()
    elif index_name == "NASDAQ 100":
        stock_dict = fetch_ndx_tickers()

    # Build full ticker → name mapping
    result = {}
    for base_ticker, name in stock_dict.items():
        full = base_ticker if (suffix == "" or "." in base_ticker or
                                base_ticker.endswith(suffix))  \
               else f"{base_ticker}{suffix}"
        result[full] = name
    return result


# ─────────────────────────────────────────────────────────────────────────────
# INDICATORS & SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _score_rsi(v):
    if pd.isna(v): return 0
    if v >= 70: return -2
    if v >= 60: return -1
    if v <= 30: return  2
    if v <= 40: return  1
    return 0

def _score_macd(m, s, h):
    if any(pd.isna(x) for x in [m, s, h]): return 0
    return max(-2, min(2, (1 if m > s else -1) + (1 if h > 0 else -1)))

def _score_cci(v):
    if pd.isna(v): return 0
    if v >= 200: return  2
    if v >= 100: return  1
    if v <=-200: return -2
    if v <=-100: return -1
    return 0

def _score_mom(v):
    if pd.isna(v): return 0
    if v >  2: return  2
    if v >  0: return  1
    if v < -2: return -2
    return -1

def _score_stoch(k, d):
    if any(pd.isna(x) for x in [k, d]): return 0
    if k < 20 and d < 20: return  2
    if k > 80 and d > 80: return -2
    if k < 20: return  1
    if k > 80: return -1
    return 1 if k > d else -1

def _score_willr(v):
    if pd.isna(v): return 0
    if v <= -80: return  2
    if v <= -50: return  1
    if v >= -20: return -2
    return -1

def _label(total):
    if total >=  6: return "Strong Buy"
    if total >=  2: return "Buy"
    if total <= -6: return "Strong Sell"
    if total <= -2: return "Sell"
    return "Hold"


def compute_signal(df: pd.DataFrame, p: dict) -> dict:
    """Compute all indicators and return signal dict. p = params."""
    empty = {"signal": "N/A", "score": 0, "details": {}}
    if len(df) < 35:
        return empty
    try:
        df = df.tail(150).copy()   # enough for all indicators, keeps RAM low
        macd_df = ta.macd(df["close"], fast=p["macd_fast"],
                          slow=p["macd_slow"], signal=p["macd_sig"])
        rsi     = ta.rsi(df["close"],  length=p["rsi_len"])
        mom     = ta.mom(df["close"],  length=p["mom_len"])
        cci     = ta.cci(df["high"], df["low"], df["close"], length=p["cci_len"])
        stoch   = ta.stoch(df["high"], df["low"], df["close"],
                           k=p["stoch_k"], d=p["stoch_d"])
        willr   = ta.willr(df["high"], df["low"], df["close"], length=p["willr_len"])

        s_macd  = _score_macd(
            macd_df["MACD_12_26_9"].iloc[-1],
            macd_df["MACDs_12_26_9"].iloc[-1],
            macd_df["MACDh_12_26_9"].iloc[-1],
        )
        s_rsi   = _score_rsi(rsi.iloc[-1])
        s_mom   = _score_mom(mom.iloc[-1])
        s_cci   = _score_cci(cci.iloc[-1])
        s_stoch = _score_stoch(stoch["STOCHk_14_3_3"].iloc[-1],
                               stoch["STOCHd_14_3_3"].iloc[-1])
        s_willr = _score_willr(willr.iloc[-1])
        total   = s_rsi + s_macd + s_cci + s_mom + s_stoch + s_willr

        # Build indicator series dict for charting (Page 2)
        ind_series = {
            "macd": macd_df, "rsi": rsi, "mom": mom,
            "cci": cci, "stoch": stoch, "willr": willr,
        }

        return {
            "signal": _label(total),
            "score":  total,
            "ind_series": ind_series,
            "details": {
                "RSI":        (s_rsi,   round(float(rsi.iloc[-1]),    2)),
                "MACD":       (s_macd,  round(float(macd_df["MACD_12_26_9"].iloc[-1]), 4)),
                "CCI":        (s_cci,   round(float(cci.iloc[-1]),    2)),
                "Momentum":   (s_mom,   round(float(mom.iloc[-1]),    4)),
                "Stochastic": (s_stoch, round(float(stoch["STOCHk_14_3_3"].iloc[-1]), 2)),
                "Williams%R": (s_willr, round(float(willr.iloc[-1]),  2)),
            },
        }
    except Exception:
        return empty


def signal_row(full_ticker: str, name: str, asset_type: str,
               region: str, currency: str,
               period: str, interval: str, p: dict) -> dict:
    """Fetch + score one asset. Returns a flat dict for the screener table."""
    base = {
        "Ticker": full_ticker, "Name": name, "Type": asset_type,
        "Region": region, "Currency": currency,
        "Price": None, "Change%": None,
        "Signal": "N/A", "Score": 0,
        "RSI": 0, "MACD": 0, "CCI": 0, "Momentum": 0,
        "Stochastic": 0, "Williams%R": 0,
    }
    df = fetch_data(full_ticker, period, interval)
    if df.empty or len(df) < 35:
        return base

    sig = compute_signal(df, p)
    price = float(df["close"].iloc[-1])
    chg   = float((df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100) \
            if len(df) > 1 else 0.0

    row = {**base,
           "Price":   round(price, 4 if price < 10 else 2),
           "Change%": round(chg, 2),
           "Signal":  sig["signal"],
           "Score":   sig["score"],
    }
    for k, (score, _) in sig.get("details", {}).items():
        row[k] = score
    return row


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        # ── Timeframe ──────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Timeframe</div>',
                    unsafe_allow_html=True)
        freq = st.selectbox("Timeframe", list(FREQ_OPTIONS.keys()),
                            index=1, label_visibility="collapsed")

        # ── Indicator parameters ───────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Indicator Parameters</div>',
                    unsafe_allow_html=True)
        with st.expander("Customize periods", expanded=False):
            rsi_len   = st.slider("RSI period",       7, 30, 14)
            macd_fast = st.slider("MACD fast",         5, 20, 12)
            macd_slow = st.slider("MACD slow",        15, 50, 26)
            macd_sig  = st.slider("MACD signal",       3, 15,  9)
            cci_len   = st.slider("CCI period",       10, 50, 20)
            mom_len   = st.slider("Momentum period",   5, 30, 10)
            stoch_k   = st.slider("Stochastic %K",    5, 30, 14)
            stoch_d   = st.slider("Stochastic %D",    2, 10,  3)
            willr_len = st.slider("Williams %R",       5, 30, 14)

        # ── Asset selection ────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Asset Classes</div>',
                    unsafe_allow_html=True)

        with st.expander("🌍 Indices", expanded=True):
            sel_indices = st.multiselect(
                "Select indices",
                options=list(INDICES.keys()),
                default=list(INDICES.keys())[:6],
                label_visibility="collapsed",
            )

        with st.expander("📈 Stocks by Index", expanded=False):
            st.caption("Select an index to screen its constituent stocks.")
            sel_stock_indices = st.multiselect(
                "Include stocks from",
                options=list(INDEX_STOCKS.keys()),
                default=[],
                label_visibility="collapsed",
            )
            if sel_stock_indices:
                max_stocks = st.select_slider(
                    "Max stocks per index",
                    options=[20, 30, 50, 100, 200, 500],
                    value=50,
                )
            else:
                max_stocks = 50

        with st.expander("🏅 Commodities", expanded=False):
            sel_commodities = st.multiselect(
                "Select commodities",
                options=list(COMMODITIES.keys()),
                default=["Gold", "Oil WTI", "Silver", "Natural Gas", "Copper"],
                label_visibility="collapsed",
            )

        with st.expander("💱 Forex", expanded=False):
            sel_forex = st.multiselect(
                "Select pairs",
                options=list(FOREX.keys()),
                default=["EUR/USD", "USD/TRY", "USD/JPY", "USD Index (DXY)"],
                label_visibility="collapsed",
            )

        with st.expander("₿ Crypto", expanded=False):
            sel_crypto = st.multiselect(
                "Select crypto",
                options=list(CRYPTO.keys()),
                default=["Bitcoin", "Ethereum"],
                label_visibility="collapsed",
            )

        st.markdown("---")
        if st.button("🗑️ Clear cache & refresh", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop("screener_df", None)
            st.rerun()

        st.caption(f"Cache: 1h  •  {datetime.now().strftime('%H:%M %d %b')}")

    # ── Build flat asset list ordered: Indices → Stocks → Commodities → Forex → Crypto
    assets = []  # list of (full_ticker, name, asset_type, region, currency)

    for name in sel_indices:
        meta = INDICES[name]
        assets.append((meta["ticker"], name, "Index",
                        meta["region"], meta["currency"]))

    for idx_name in sel_stock_indices:
        universe = get_stock_universe(idx_name)
        items    = list(universe.items())[:max_stocks]
        for full_ticker, sname in items:
            region = INDICES.get(idx_name, {}).get("region", idx_name)
            assets.append((full_ticker, sname, f"{idx_name} Stock",
                           region, ""))

    for name in sel_commodities:
        meta = COMMODITIES[name]
        assets.append((meta["ticker"], name, "Commodity",
                        meta["region"], meta["currency"]))

    for name in sel_forex:
        meta = FOREX[name]
        assets.append((meta["ticker"], name, "Forex",
                        meta["region"], ""))

    for name in sel_crypto:
        meta = CRYPTO[name]
        assets.append((meta["ticker"], name, "Crypto",
                        meta["region"], meta["currency"]))

    return {
        "freq":       freq,
        "period":     FREQ_OPTIONS[freq]["period"],
        "interval":   FREQ_OPTIONS[freq]["interval"],
        "rsi_len":    rsi_len,
        "macd_fast":  macd_fast, "macd_slow": macd_slow, "macd_sig": macd_sig,
        "cci_len":    cci_len,   "mom_len":   mom_len,
        "stoch_k":    stoch_k,   "stoch_d":   stoch_d,
        "willr_len":  willr_len,
        "assets":     assets,   # list of tuples
    }


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 – SCREENER
# ─────────────────────────────────────────────────────────────────────────────

def render_page1(params: dict):
    assets = params["assets"]
    n = len(assets)

    st.markdown("## 📋 Market Screener")
    st.markdown(
        f"**{n} assets** selected  •  Timeframe: **{params['freq']}**  •  "
        f"Score range: −12 → +12  •  6 indicators"
    )

    col_run, col_info = st.columns([1, 4])
    with col_run:
        run = st.button("▶ Run Screener", type="primary", use_container_width=True)
    with col_info:
        st.caption(
            "Results are cached for 1 hour. Add/remove asset classes in the sidebar, "
            "then press Run. For large stock sets (500+) this may take a few minutes."
        )

    if run:
        st.session_state.pop("screener_df", None)   # force fresh run
        rows   = []
        bar    = st.progress(0, text="Starting…")
        status = st.empty()

        for i, (full_ticker, name, atype, region, currency) in enumerate(assets):
            status.caption(f"⏳ {full_ticker}  —  {name}  ({i+1}/{n})")
            row = signal_row(
                full_ticker, name, atype, region, currency,
                params["period"], params["interval"], params,
            )
            rows.append(row)
            bar.progress((i + 1) / n, text=f"{full_ticker}")

        bar.empty()
        status.empty()
        st.session_state["screener_df"] = pd.DataFrame(rows)

    # ── Show results ─────────────────────────────────────────────────────────
    df_all = st.session_state.get("screener_df")
    if df_all is None or df_all.empty:
        st.caption("Press **Run Screener** to load data.")
        return

    # ── Filter / sort bar ────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    with fc1:
        type_filter = st.multiselect(
            "Asset type", sorted(df_all["Type"].unique()), default=[],
        )
    with fc2:
        sig_filter = st.multiselect(
            "Signal", ["Strong Buy","Buy","Hold","Sell","Strong Sell"], default=[],
        )
    with fc3:
        sort_by = st.selectbox("Sort by", ["Score","Change%","Ticker","Price","Type"])
    with fc4:
        asc = st.radio("Order", ["Descending","Ascending"], horizontal=True) == "Ascending"

    display_df = df_all.copy()
    if type_filter:
        display_df = display_df[display_df["Type"].isin(type_filter)]
    if sig_filter:
        display_df = display_df[display_df["Signal"].isin(sig_filter)]
    display_df = display_df.sort_values(sort_by, ascending=asc).reset_index(drop=True)

    # ── Signal summary badges ─────────────────────────────────────────────────
    counts     = df_all["Signal"].value_counts()
    badge_cols = st.columns(5)
    for i, sig in enumerate(["Strong Buy","Buy","Hold","Sell","Strong Sell"]):
        with badge_cols[i]:
            cnt   = counts.get(sig, 0)
            color = SIGNAL_COLORS[sig]
            pct   = round(cnt / len(df_all) * 100) if len(df_all) > 0 else 0
            st.markdown(
                f'<div class="metric-card"><div class="label">{sig}</div>'
                f'<div class="value" style="color:{color}">{cnt}</div>'
                f'<div class="sub">{pct}%</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    ind_cols  = ["RSI","MACD","CCI","Momentum","Stochastic","Williams%R"]
    show_cols = ["Ticker","Name","Type","Region","Price","Change%",
                 "Signal","Score"] + ind_cols

    def _c_signal(v):
        c = SIGNAL_COLORS.get(v, "")
        return f"color:{c}; font-weight:600;" if c else ""
    def _c_score(v):
        if pd.isna(v): return ""
        if v >= 2:  return "color:#26A69A; font-weight:600;"
        if v <= -2: return "color:#EF5350; font-weight:600;"
        return "color:#FFD740;"
    def _c_chg(v):
        if pd.isna(v): return ""
        return "color:#26A69A;" if v >= 0 else "color:#EF5350;"

    styled = (
        display_df[show_cols]
        .style
        .map(_c_signal, subset=["Signal"])
        .map(_c_score,  subset=["Score"])
        .map(_c_chg,    subset=["Change%"])
        .format({"Price": "{:.2f}", "Change%": "{:+.2f}%"}, na_rep="—")
    )
    st.dataframe(styled, use_container_width=True, height=550)

    # ── Export ────────────────────────────────────────────────────────────────
    csv = display_df[show_cols].to_csv(index=False)
    st.download_button(
        "⬇ Export CSV", data=csv,
        file_name=f"ta_screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS (Page 2)
# ─────────────────────────────────────────────────────────────────────────────

def build_charts(df: pd.DataFrame, ind: dict, ticker: str, name: str) -> go.Figure:
    fig = make_subplots(
        rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.025,
        row_heights=[3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2],
        subplot_titles=[
            f"{ticker} — {name}", "MACD (12/26/9)", "RSI (14)",
            "Momentum (10)", "CCI (20)", "Stochastic (14/3)", "Williams %R (14)",
        ],
    )
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        increasing_line_color="#26A69A", decreasing_line_color="#EF5350",
        showlegend=False, name="Price",
    ), row=1, col=1)

    # MACD
    macd_df = ind["macd"]
    hist    = macd_df["MACDh_12_26_9"]
    fig.add_trace(go.Bar(
        x=df.index, y=hist,
        marker_color=["#26A69A" if v >= 0 else "#EF5350" for v in hist],
        name="Histogram", showlegend=False,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_df["MACD_12_26_9"],
        line=dict(color="#2962FF", width=1.3), name="MACD",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=macd_df["MACDs_12_26_9"],
        line=dict(color="#FF6D00", width=1.2, dash="dot"), name="Signal",
    ), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=df.index, y=ind["rsi"],
        line=dict(color="#AB47BC", width=1.5), name="RSI", showlegend=False,
    ), row=3, col=1)
    for lvl, col in [(70, "rgba(239,83,80,0.35)"), (30, "rgba(38,166,154,0.35)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=col, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="grey", line_width=0.6,
                  row=3, col=1)

    # Momentum
    mom = ind["mom"]
    fig.add_trace(go.Bar(
        x=df.index, y=mom,
        marker_color=["#26A69A" if v >= 0 else "#EF5350" for v in mom],
        name="Momentum", showlegend=False,
    ), row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="grey",
                  line_width=0.6, row=4, col=1)

    # CCI
    fig.add_trace(go.Scatter(
        x=df.index, y=ind["cci"],
        line=dict(color="#FFA726", width=1.5), name="CCI", showlegend=False,
    ), row=5, col=1)
    for lvl, col in [(100, "rgba(239,83,80,0.35)"),
                     (-100, "rgba(38,166,154,0.35)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=col, row=5, col=1)

    # Stochastic
    stoch_df = ind["stoch"]
    fig.add_trace(go.Scatter(
        x=df.index, y=stoch_df["STOCHk_14_3_3"],
        line=dict(color="#42A5F5", width=1.5), name="%K",
    ), row=6, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=stoch_df["STOCHd_14_3_3"],
        line=dict(color="#EF5350", width=1.2, dash="dot"), name="%D",
    ), row=6, col=1)
    for lvl, col in [(80, "rgba(239,83,80,0.35)"),
                     (20, "rgba(38,166,154,0.35)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=col, row=6, col=1)

    # Williams %R
    fig.add_trace(go.Scatter(
        x=df.index, y=ind["willr"],
        line=dict(color="#EC407A", width=1.5), name="Williams %R",
        showlegend=False,
    ), row=7, col=1)
    for lvl, col in [(-20, "rgba(239,83,80,0.35)"),
                     (-80, "rgba(38,166,154,0.35)")]:
        fig.add_hline(y=lvl, line_dash="dash", line_color=col, row=7, col=1)

    fig.update_layout(
        height=1080,
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        font=dict(color="#FAFAFA", family="Inter, sans-serif", size=11),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=40, b=20),
        legend=dict(orientation="h", x=0, y=1.01,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hovermode="x unified",
    )
    for i in range(1, 8):
        fig.update_xaxes(showgrid=True, gridcolor="#1E2130",
                         gridwidth=0.5, zeroline=False, row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor="#1E2130",
                         gridwidth=0.5, zeroline=False, row=i, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 – ASSET DETAIL
# ─────────────────────────────────────────────────────────────────────────────

def render_page2(params: dict):
    st.markdown("## 📈 Asset Detail — Indicators")

    assets  = params["assets"]
    options = [(t, n) for t, n, *_ in assets]

    if not options:
        st.info("No assets selected. Use the sidebar to add indices, stocks, or commodities.")
        return

    # Asset selector with type context
    col_sel, col_ref = st.columns([4, 1])
    with col_sel:
        labels      = {t: f"{t}  —  {n}" for t, n in options}
        full_ticker = st.selectbox(
            "Select asset",
            options=[t for t, _ in options],
            format_func=lambda t: labels.get(t, t),
            label_visibility="collapsed",
        )
    with col_ref:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_data.clear()
            st.rerun()

    # Find asset metadata
    asset_meta = next(
        ((t, n, at, reg, cur) for t, n, at, reg, cur in assets if t == full_ticker),
        (full_ticker, full_ticker, "", "", ""),
    )
    _, asset_name, asset_type, asset_region, currency = asset_meta

    with st.spinner(f"Loading {full_ticker}…"):
        df = fetch_data(full_ticker, params["period"], params["interval"])

    if df.empty:
        st.error(
            f"No data returned for **{full_ticker}**. "
            f"This may be a temporary Yahoo Finance issue — try **Refresh** above."
        )
        return

    sig = compute_signal(df, params)

    # ── Metric cards ─────────────────────────────────────────────────────────
    price   = float(df["close"].iloc[-1])
    chg_pct = float((df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100) \
              if len(df) > 1 else 0.0
    chg_col = "#26A69A" if chg_pct >= 0 else "#EF5350"
    sig_col = SIGNAL_COLORS.get(sig["signal"], "#FFD740")
    price_fmt = f"{currency}{price:,.4f}" if price < 10 else f"{currency}{price:,.2f}"

    m1, m2, m3, m4, m5 = st.columns(5)
    cards = [
        (m1, "Asset",    asset_name,     "#FAFAFA"),
        (m2, "Type",     asset_type,     "#63b3ed"),
        (m3, "Price",    price_fmt,      "#FAFAFA"),
        (m4, f"Change ({params['freq']})", f"{chg_pct:+.2f}%", chg_col),
        (m5, "TA Signal", sig["signal"], sig_col),
    ]
    for col, label, value, color in cards:
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="label">{label}</div>'
                f'<div class="value" style="color:{color}; font-size:1.1rem;">'
                f'{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Indicator breakdown ───────────────────────────────────────────────────
    with st.expander("📊 Indicator Score Breakdown", expanded=True):
        score_label = {
            2: "Strong Buy", 1: "Buy", 0: "Hold", -1: "Sell", -2: "Strong Sell",
        }
        bc = st.columns(6)
        for i, (ind_name, (score, val)) in enumerate(sig.get("details", {}).items()):
            s_color = SIGNAL_COLORS.get(score_label.get(score, "Hold"), "#FFD740")
            with bc[i]:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="label">{ind_name}</div>'
                    f'<div class="value" style="color:{s_color}">{score:+d}</div>'
                    f'<div class="sub">val: {val}</div></div>',
                    unsafe_allow_html=True,
                )

        # Composite score bar
        st.markdown("<br>", unsafe_allow_html=True)
        total      = sig["score"]
        bar_pct    = (total + 12) / 24 * 100
        bar_color  = sig_col
        st.markdown(
            f"**Composite Score: {total:+d}** / ±12 &nbsp;&nbsp;"
            f'<span class="sig-badge sig-{sig["signal"].lower().replace(" ","-")}">'
            f'{SIGNAL_EMOJI.get(sig["signal"], "")} {sig["signal"]}</span>',
            unsafe_allow_html=True,
        )
        st.progress(int(bar_pct))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    ind = sig.get("ind_series", {})
    if ind:
        fig = build_charts(df, ind, full_ticker, asset_name)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": True})
    else:
        st.warning("Not enough data to render charts (need at least 35 bars).")

    # ── Raw data ──────────────────────────────────────────────────────────────
    with st.expander("📄 Raw Data (last 50 bars)"):
        fmt = "%Y-%m-%d %H:%M" if "h" in params["interval"] else "%Y-%m-%d"
        show_df = df.tail(50).copy()
        show_df.index = show_df.index.strftime(fmt)
        st.dataframe(show_df.style.format("{:.4f}"), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="main-header">'
        '<h1>📊 Global Technical Analysis Dashboard</h1>'
        '<p>Indices · Stocks · Commodities · Forex · Crypto  '
        '•  6 indicators  •  5-level signals  •  Powered by Yahoo Finance</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    params = render_sidebar()

    # Page navigation
    page = st.radio(
        "page", ["📋  Screener", "📈  Asset Detail"],
        horizontal=True, label_visibility="hidden",
    )
    st.markdown("---")

    if "Screener" in page:
        render_page1(params)
    else:
        render_page2(params)

    st.markdown(
        f'<div class="footer">Data: Yahoo Finance (yfinance)  •  '
        f'Indicators: pandas-ta  •  Not financial advice  •  '
        f'{datetime.now().strftime("%d %b %Y %H:%M")}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
