import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pytz
import warnings
from requests.exceptions import HTTPError, ConnectionError
import urllib3
warnings.filterwarnings('ignore')

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration de la page
st.set_page_config(
    page_title="Tracker Bourse Thaïlande - SET Bangkok",
    page_icon="🇹🇭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration des fuseaux horaires
USER_TIMEZONES = {
    'UTC+4': pytz.timezone('Asia/Dubai'),
    'UTC+3': pytz.timezone('Asia/Riyadh'),
    'UTC+2': pytz.FixedOffset(120),
    'UTC+1': pytz.timezone('Europe/Paris'),
    'UTC': pytz.UTC,
    'UTC-5': pytz.timezone('America/New_York'),
    'UTC-8': pytz.timezone('America/Los_Angeles'),
    'UTC+5:30': pytz.timezone('Asia/Kolkata'),
    'UTC+7': pytz.timezone('Asia/Bangkok'),
    'UTC+8': pytz.timezone('Asia/Singapore'),
    'UTC+9': pytz.timezone('Asia/Tokyo'),
    'UTC+10': pytz.timezone('Australia/Sydney'),
}

# Fuseau horaire par défaut
DEFAULT_USER_TZ = 'UTC+7'

# Fuseau horaire de la Thaïlande
THAILAND_TZ = pytz.timezone('Asia/Bangkok')

if 'selected_timezone' not in st.session_state:
    st.session_state.selected_timezone = DEFAULT_USER_TZ

if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

if 'email_config' not in st.session_state:
    st.session_state.email_config = {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': '',
        'password': ''
    }

if 'last_successful_data' not in st.session_state:
    st.session_state.last_successful_data = {}

# Style CSS personnalisé
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap');
    
    .main-header {
        font-size: 2.5rem;
        color: #00247D;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Prompt', sans-serif;
        background: linear-gradient(135deg, #00247D 0%, #FFFFFF 50%, #F4A900 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .thai-text {
        font-family: 'Sarabun', sans-serif;
        font-size: 1.2rem;
    }
    .stock-price {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00247D;
        text-align: center;
    }
    .stock-change-positive {
        color: #006747;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .stock-change-negative {
        color: #CF1020;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .timezone-badge {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .thai-market-note {
        background: linear-gradient(135deg, #00247D 0%, #FFFFFF 50%, #F4A900 100%);
        color: #000000;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-weight: bold;
        text-align: center;
        font-family: 'Prompt', sans-serif;
    }
    .set-badge {
        background-color: #00247D;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .mai-badge {
        background-color: #F4A900;
        color: #00247D;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .holiday-note {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .tz-selector {
        background-color: #e8f4f8;
        padding: 0.8rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Watchlist des actions thaïlandaises
WATCHLIST = [
    'PTT.BK', 'PTTEP.BK', 'SCB.BK', 'KBANK.BK', 'BBL.BK', 'KTB.BK',
    'ADVANC.BK', 'AOT.BK', 'CPALL.BK', 'CPF.BK', 'TRUE.BK', 'DTAC.BK',
    'INTUCH.BK', 'GULF.BK', 'BGRIM.BK', 'GPSC.BK', 'EA.BK', 'TOP.BK',
    'IRPC.BK', 'SCC.BK', 'SCGP.BK', 'IVL.BK', 'BEM.BK', 'BTS.BK',
    'CRC.BK', 'CPN.BK', 'HMPRO.BK', 'GLOBAL.BK', 'COM7.BK', 'MINT.BK',
    'CENTEL.BK', 'ERW.BK', 'BDMS.BK', 'BH.BK', 'CHG.BK', 'DELTA.BK',
    'HANA.BK', 'KCE.BK', 'SVI.BK', 'TU.BK', 'TKN.BK', 'OSP.BK',
    'SAPPE.BK', 'BJC.BK', 'STA.BK', 'VGI.BK', 'JMART.BK', 'SINGER.BK',
    'THANI.BK', 'MTC.BK', 'SAWAD.BK', 'TIDLOR.BK', 'OR.BK', 'BANPU.BK',
    'TTA.BK', 'PSL.BK', 'RCL.BK', 'WHA.BK', 'AMATA.BK', 'LH.BK',
    'AP.BK', 'SPALI.BK', 'QH.BK', 'SIRI.BK', 'ORI.BK', 'SC.BK'
]

# Jours fériés en Thaïlande 2024
THAI_HOLIDAYS_2024 = [
    '2024-01-01', '2024-01-02', '2024-02-24', '2024-04-06', '2024-04-08',
    '2024-04-13', '2024-04-14', '2024-04-15', '2024-04-16', '2024-05-01',
    '2024-05-04', '2024-05-22', '2024-06-03', '2024-07-20', '2024-07-21',
    '2024-07-22', '2024-07-28', '2024-08-12', '2024-10-13', '2024-10-14',
    '2024-10-23', '2024-12-05', '2024-12-10', '2024-12-31'
]

# Horaires du marché thaïlandais
THAI_MARKET_HOURS = {
    'morning_open': 10,
    'morning_close': 12.5,
    'afternoon_open': 14,
    'afternoon_close': 16.5,
}

def get_exchange_info(symbol):
    """Détermine l'échange pour un symbole"""
    if symbol.endswith('.BK'):
        return 'Stock Exchange of Thailand (SET)', 'Thailand', 'THB'
    return 'International Listing', 'International', 'USD'

def get_currency(symbol):
    """Détermine la devise"""
    return 'THB' if symbol.endswith('.BK') else 'USD'

def format_thai_currency(value):
    """Formate la monnaie thaïlandaise"""
    if value is None or value == 0:
        return "N/A"
    if value >= 1e9:
        return f"{value/1e9:.2f} พันล้านบาท"
    elif value >= 1e6:
        return f"{value/1e6:.2f} ล้านบาท"
    else:
        return f"{value:.2f} บาท"

def send_email_alert(subject, body, to_email):
    """Envoie une notification par email"""
    if not st.session_state.email_config['enabled']:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = st.session_state.email_config['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(
            st.session_state.email_config['smtp_server'],
            st.session_state.email_config['smtp_port']
        )
        server.starttls()
        server.login(
            st.session_state.email_config['email'],
            st.session_state.email_config['password']
        )
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi: {e}")
        return False

def check_price_alerts(current_price, symbol):
    """Vérifie les alertes de prix"""
    triggered = []
    for alert in st.session_state.price_alerts:
        if alert['symbol'] == symbol:
            if alert['condition'] == 'above' and current_price >= alert['price']:
                triggered.append(alert)
            elif alert['condition'] == 'below' and current_price <= alert['price']:
                triggered.append(alert)
    return triggered

def get_market_status():
    """Détermine le statut du marché thaïlandais"""
    now = datetime.now(THAILAND_TZ)
    weekday = now.weekday()
    
    if weekday >= 5:
        return "Fermé (weekend)", "🔴"
    
    date_str = now.strftime('%Y-%m-%d')
    if date_str in THAI_HOLIDAYS_2024:
        return "Fermé (jour férié)", "🔴"
    
    current_time = now.hour + now.minute / 60.0
    
    if (THAI_MARKET_HOURS['morning_open'] <= current_time < THAI_MARKET_HOURS['morning_close']) or \
       (THAI_MARKET_HOURS['afternoon_open'] <= current_time < THAI_MARKET_HOURS['afternoon_close']):
        return "Ouvert", "🟢"
    elif current_time < THAI_MARKET_HOURS['morning_open']:
        return "Fermé (pré-ouverture)", "🟡"
    elif THAI_MARKET_HOURS['morning_close'] <= current_time < THAI_MARKET_HOURS['afternoon_open']:
        return "Pause midi", "🟠"
    else:
        return "Fermé", "🔴"

def get_market_status_with_timezone(user_tz):
    """Statut du marché avec conversion de fuseau horaire"""
    thai_time = datetime.now(THAILAND_TZ)
    user_time = thai_time.astimezone(user_tz)
    status, icon = get_market_status()
    return status, icon, thai_time, user_time

@st.cache_data(ttl=300)
def load_stock_data(symbol, period, interval):
    """Charge les données boursières avec cache"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        info = ticker.info
        
        if hist is not None and not hist.empty:
            if hist.index.tz is None:
                hist.index = hist.index.tz_localize('UTC').tz_convert(THAILAND_TZ)
            else:
                hist.index = hist.index.tz_convert(THAILAND_TZ)
            
            st.session_state.last_successful_data[symbol] = {
                'hist': hist,
                'info': info,
                'timestamp': datetime.now()
            }
            return hist, info
        else:
            st.error(f"❌ Aucune donnée disponible pour {symbol}")
            return None, None
            
    except Exception as e:
        st.error(f"❌ Erreur de chargement pour {symbol}: {str(e)}")
        return None, None

def safe_get_metric(hist, metric, index=-1):
    """Récupère une métrique en toute sécurité"""
    try:
        if hist is not None and not hist.empty and len(hist) > abs(index):
            return hist[metric].iloc[index]
        return 0
    except:
        return 0

# ============================================================================
# INTERFACE PRINCIPALE
# ============================================================================

st.markdown("<h1 class='main-header'>🇹🇭 Tracker Bourse Thaïlande - SET Bangkok</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: Sarabun; font-size: 1.5rem;'>ติดตามตลาดหลักทรัพย์แห่งประเทศไทยแบบเรียลไทม์</p>", unsafe_allow_html=True)

# Sélecteur de fuseau horaire
st.markdown("<div class='tz-selector'>", unsafe_allow_html=True)
col_tz1, col_tz2 = st.columns([3, 1])
with col_tz1:
    st.markdown("**🕐 Votre fuseau horaire**")
    selected_tz_key = st.selectbox(
        "",
        options=list(USER_TIMEZONES.keys()),
        index=list(USER_TIMEZONES.keys()).index(st.session_state.selected_timezone)
    )
    st.session_state.selected_timezone = selected_tz_key
    user_tz = USER_TIMEZONES[selected_tz_key]
with col_tz2:
    st.markdown(f"<br><span class='set-badge'>🇹🇭 UTC+7</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Statut du marché
status, icon, thai_time, user_time = get_market_status_with_timezone(user_tz)

st.markdown(f"""
<div class='timezone-badge'>
    <b>🕐 Informations</b><br>
    🇹🇭 Thaïlande: {thai_time.strftime('%H:%M:%S')} (UTC+7)<br>
    🌍 Votre heure: {user_time.strftime('%H:%M:%S')} ({selected_tz_key})<br>
    📊 Marché SET: {icon} {status}
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='holiday-note'>
    📅 Horaires SET: 10h00-12h30 | 14h00-16h30 (heure Thaïlande)<br>
    📅 Fermé samedi-dimanche et jours fériés
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='thai-market-note'>
    <span class='set-badge'>SET</span> <span class='mai-badge'>MAI</span><br>
    🇹🇭 Stock Exchange of Thailand - ตลาดหลักทรัพย์แห่งประเทศไทย<br>
    Devise: Baht (THB) - บาท
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/thailand.png", width=80)
    st.title("Navigation")
    
    with st.expander("🕐 Fuseau horaire", expanded=True):
        selected_tz_key = st.selectbox(
            "Votre fuseau",
            options=list(USER_TIMEZONES.keys()),
            index=list(USER_TIMEZONES.keys()).index(st.session_state.selected_timezone),
            key="sidebar_tz"
        )
        st.session_state.selected_timezone = selected_tz_key
        user_tz = USER_TIMEZONES[selected_tz_key]
        st.caption(f"🇹🇭 Thaïlande: UTC+7")
        st.caption(f"📍 Heure locale: {datetime.now(user_tz).strftime('%H:%M')}")
    
    st.markdown("---")
    
    menu = st.radio(
        "Section",
        ["📈 Tableau de bord",
         "💰 Portefeuille virtuel",
         "🔔 Alertes de prix",
         "📧 Notifications email",
         "📤 Export des données",
         "🤖 Prédictions ML",
         "🇹🇭 Indices thaïlandais"]
    )
    
    st.markdown("---")
    
    st.subheader("⚙️ Configuration")
    
    symbol_options = ["PTT.BK", "PTTEP.BK", "SCB.BK", "KBANK.BK", "ADVANC.BK", 
                      "CPALL.BK", "AOT.BK", "DELTA.BK", "Autre..."]
    
    selected_option = st.selectbox(
        "Symbole principal",
        options=symbol_options,
        index=0
    )
    
    if selected_option == "Autre...":
        symbol = st.text_input("Symbole", value="PTT.BK").upper()
        if not symbol.endswith('.BK') and not symbol.endswith('.BK'):
            symbol += '.BK'
    else:
        symbol = selected_option
    
    exchange, country, currency = get_exchange_info(symbol)
    st.caption(f"📍 {exchange} | {currency}")
    
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Période",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2
        )
    
    with col2:
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "1d": "1j", "1wk": "1sem", "1mo": "1mois"
        }
        interval = st.selectbox(
            "Intervalle",
            options=list(interval_map.keys()),
            format_func=lambda x: interval_map[x],
            index=4 if period == "1d" else 6
        )
    
    auto_refresh = st.checkbox("Auto-refresh", value=False)
    if auto_refresh:
        refresh_rate = st.slider("Fréquence (s)", 30, 300, 60, 10)

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

with st.spinner(f"🔄 Chargement des données pour {symbol}..."):
    hist, info = load_stock_data(symbol, period, interval)

if hist is None or hist.empty:
    st.markdown(f"""
    <div class='error-message'>
        ❌ Impossible de charger les données pour {symbol}<br>
        Vérifiez que le symbole est correct (ex: PTT.BK, SCB.BK, KBANK.BK)<br>
        Les symboles thaïlandais doivent se terminer par .BK
    </div>
    """, unsafe_allow_html=True)
    st.stop()

current_price = safe_get_metric(hist, 'Close')

# Vérification des alertes
triggered_alerts = check_price_alerts(current_price, symbol)
for alert in triggered_alerts:
    st.balloons()
    st.success(f"🎯 Alerte {symbol} à {format_thai_currency(current_price)}")
    
    if st.session_state.email_config['enabled']:
        subject = f"🚨 Alerte SET - {symbol}"
        body = f"""
        <h2>Alerte de prix - SET Thailand</h2>
        <p><b>Symbole:</b> {symbol}</p>
        <p><b>Prix actuel:</b> {format_thai_currency(current_price)}</p>
        <p><b>Condition:</b> {alert['condition']} {alert['price']:.2f} THB</p>
        <p><b>Thaïlande:</b> {datetime.now(THAILAND_TZ).strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Votre heure:</b> {datetime.now(user_tz).strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        send_email_alert(subject, body, st.session_state.email_config['email'])
    
    if alert.get('one_time', False):
        st.session_state.price_alerts.remove(alert)

# ============================================================================
# SECTION TABLEAU DE BORD
# ============================================================================

if menu == "📈 Tableau de bord":
    status, icon = get_market_status()
    st.info(f"{icon} Thailand SET: {status}")
    
    company_name = info.get('longName', symbol) if info else symbol
    
    st.subheader(f"📊 {company_name}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    previous_close = safe_get_metric(hist, 'Close', -2) if len(hist) > 1 else current_price
    change = current_price - previous_close
    change_pct = (change / previous_close * 100) if previous_close != 0 else 0
    
    with col1:
        st.metric(
            "Prix actuel",
            f"{current_price:.2f} THB",
            delta=f"{change:.2f} ({change_pct:.2f}%)",
            delta_color="normal"
        )
    
    with col2:
        day_high = safe_get_metric(hist, 'High')
        st.metric("Plus haut", f"{day_high:.2f} THB")
    
    with col3:
        day_low = safe_get_metric(hist, 'Low')
        st.metric("Plus bas", f"{day_low:.2f} THB")
    
    with col4:
        volume = safe_get_metric(hist, 'Volume')
        st.metric("Volume", f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.1f}K")
    
    st.caption(f"Dernière MAJ: {hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (Thaïlande)")
    
    # Graphique
    st.subheader("📈 Évolution du prix")
    
    fig = go.Figure()
    
    if interval in ["1m", "5m", "15m", "30m", "1h"]:
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name='Prix',
            increasing_line_color='#006747',
            decreasing_line_color='#CF1020'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist['Close'],
            mode='lines',
            name='Prix',
            line=dict(color='#00247D', width=2)
        ))
    
    if len(hist) >= 20:
        ma20 = hist['Close'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=hist.index, y=ma20,
            mode='lines', name='MA20',
            line=dict(color='orange', width=1, dash='dash')
        ))
    
    if len(hist) >= 50:
        ma50 = hist['Close'].rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=hist.index, y=ma50,
            mode='lines', name='MA50',
            line=dict(color='purple', width=1, dash='dash')
        ))
    
    fig.add_trace(go.Bar(
        x=hist.index, y=hist['Volume'],
        name='Volume', yaxis='y2',
        marker=dict(color='lightgray', opacity=0.3)
    ))
    
    fig.update_layout(
        title=f"{symbol} - {period}",
        yaxis_title="Prix (THB)",
        yaxis2=dict(title="Volume", overlaying='y', side='right'),
        height=600,
        hovermode='x unified',
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Informations entreprise
    with st.expander("ℹ️ Informations"):
        if info:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Nom:** {info.get('longName', 'N/A')}")
                st.write(f"**Secteur:** {info.get('sector', 'N/A')}")
                st.write(f"**Industrie:** {info.get('industry', 'N/A')}")
                st.write(f"**Site:** {info.get('website', 'N/A')}")
            with col2:
                market_cap = info.get('marketCap', 0)
                st.write(f"**Cap.:** {format_thai_currency(market_cap)}")
                st.write(f"**P/E:** {info.get('trailingPE', 'N/A')}")
                dy = info.get('dividendYield', 0)
                st.write(f"**Dividende:** {dy*100:.2f}%" if dy else "**Dividende:** N/A")
                st.write(f"**Beta:** {info.get('beta', 'N/A')}")

# ============================================================================
# SECTION PORTEFEUILLE
# ============================================================================

elif menu == "💰 Portefeuille virtuel":
    st.subheader("💰 Portefeuille virtuel - THB")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### ➕ Ajouter")
        with st.form("add_position"):
            sym = st.text_input("Symbole", "PTT.BK").upper()
            if not sym.endswith('.BK'):
                sym += '.BK'
            
            shares = st.number_input("Actions", 1, 1000000, 100)
            buy_price = st.number_input("Prix achat (THB)", 0.01, 10000.0, 35.0)
            
            if st.form_submit_button("Ajouter"):
                if sym not in st.session_state.portfolio:
                    st.session_state.portfolio[sym] = []
                st.session_state.portfolio[sym].append({
                    'shares': shares,
                    'buy_price': buy_price,
                    'date': datetime.now(user_tz).strftime('%Y-%m-%d %H:%M')
                })
                st.success(f"✅ {shares} {sym} ajoutées")
    
    with col1:
        if st.session_state.portfolio:
            total_value = 0
            total_cost = 0
            data = []
            
            for sym, positions in st.session_state.portfolio.items():
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period='1d')
                    current = hist['Close'].iloc[-1] if not hist.empty else 0
                    
                    for pos in positions:
                        cost = pos['shares'] * pos['buy_price']
                        value = pos['shares'] * current
                        profit = value - cost
                        profit_pct = (profit / cost * 100) if cost else 0
                        
                        total_cost += cost
                        total_value += value
                        
                        data.append({
                            'Symbole': sym,
                            'Actions': pos['shares'],
                            'Achat': f"{pos['buy_price']:.2f}",
                            'Actuel': f"{current:.2f}",
                            'Valeur': f"{value:,.0f}",
                            'P/L': f"{profit:,.0f}",
                            'P/L%': f"{profit_pct:.1f}%"
                        })
                except:
                    st.warning(f"⚠️ {sym} non disponible")
            
            if data:
                total_profit = total_value - total_cost
                total_pct = (total_profit / total_cost * 100) if total_cost else 0
                
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur", f"{total_value:,.0f} THB")
                col_i2.metric("Coût", f"{total_cost:,.0f} THB")
                col_i3.metric("Profit", f"{total_profit:,.0f} THB", f"{total_pct:.1f}%")
                
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
                if st.button("🗑️ Vider"):
                    st.session_state.portfolio = {}
                    st.rerun()
        else:
            st.info("Portefeuille vide")

# ============================================================================
# SECTION ALERTES
# ============================================================================

elif menu == "🔔 Alertes de prix":
    st.subheader("🔔 Alertes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("new_alert"):
            sym = st.text_input("Symbole", symbol).upper()
            if not sym.endswith('.BK'):
                sym += '.BK'
            
            price = st.number_input("Prix (THB)", 0.01, 10000.0, float(current_price * 1.05))
            condition = st.selectbox("Condition", ["above", "below"])
            one_time = st.checkbox("Une fois")
            
            if st.form_submit_button("Créer"):
                st.session_state.price_alerts.append({
                    'symbol': sym,
                    'price': price,
                    'condition': condition,
                    'one_time': one_time,
                    'created': datetime.now(user_tz).strftime('%Y-%m-%d %H:%M')
                })
                st.success(f"✅ Alerte {sym} {condition} {price:.2f}")
    
    with col2:
        if st.session_state.price_alerts:
            for i, alert in enumerate(st.session_state.price_alerts):
                st.markdown(f"""
                <div class='alert-box alert-warning'>
                    <b>{alert['symbol']}</b> {alert['condition']} {alert['price']:.2f} THB<br>
                    <small>{alert['created']}</small>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Supprimer", key=f"del_{i}"):
                    st.session_state.price_alerts.pop(i)
                    st.rerun()
        else:
            st.info("Aucune alerte")

# ============================================================================
# SECTION EMAIL
# ============================================================================

elif menu == "📧 Notifications email":
    st.subheader("📧 Configuration email")
    
    with st.form("email_config"):
        enabled = st.checkbox("Activer", st.session_state.email_config['enabled'])
        
        col1, col2 = st.columns(2)
        with col1:
            server = st.text_input("SMTP", st.session_state.email_config['smtp_server'])
            port = st.number_input("Port", st.session_state.email_config['smtp_port'])
        with col2:
            email = st.text_input("Email", st.session_state.email_config['email'])
            password = st.text_input("Mot de passe", type="password", value=st.session_state.email_config['password'])
        
        test = st.text_input("Email test")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Sauvegarder"):
                st.session_state.email_config = {
                    'enabled': enabled,
                    'smtp_server': server,
                    'smtp_port': port,
                    'email': email,
                    'password': password
                }
                st.success("Configuration sauvegardée")
        
        with col_btn2:
            if st.form_submit_button("📨 Tester") and test:
                if send_email_alert(
                    "Test SET Thailand",
                    f"<h2>Test réussi</h2><p>{datetime.now(THAILAND_TZ)} (Thaïlande)</p>",
                    test
                ):
                    st.success("Email envoyé")
                else:
                    st.error("Échec")

# ============================================================================
# SECTION EXPORT
# ============================================================================

elif menu == "📤 Export des données":
    st.subheader("📤 Export")
    
    if hist is not None:
        st.dataframe(hist.tail(20))
        
        csv = hist.to_csv()
        st.download_button(
            "📥 Télécharger CSV",
            csv,
            f"{symbol}_{datetime.now(THAILAND_TZ).strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        
        stats = {
            'Moyenne': hist['Close'].mean(),
            'Écart-type': hist['Close'].std(),
            'Min': hist['Close'].min(),
            'Max': hist['Close'].max(),
        }
        
        json_data = {
            'symbol': symbol,
            'thailand_time': datetime.now(THAILAND_TZ).isoformat(),
            'user_time': datetime.now(user_tz).isoformat(),
            'user_tz': selected_tz_key,
            'current_price': float(current_price),
            'statistics': stats,
            'data': hist.reset_index().to_dict(orient='records')
        }
        
        st.download_button(
            "📥 Télécharger JSON",
            json.dumps(json_data, indent=2, default=str),
            f"{symbol}_{datetime.now(THAILAND_TZ).strftime('%Y%m%d')}.json",
            "application/json"
        )

# ============================================================================
# SECTION PRÉDICTIONS ML
# ============================================================================

elif menu == "🤖 Prédictions ML":
    st.subheader("🤖 Prédictions")
    
    if len(hist) < 30:
        st.warning("⚠️ Minimum 30 jours requis")
    else:
        df = hist[['Close']].reset_index()
        df['Days'] = (df['Date'] - df['Date'].min()).dt.days
        
        X = df['Days'].values.reshape(-1, 1)
        y = df['Close'].values
        
        col1, col2 = st.columns(2)
        with col1:
            days = st.slider("Jours à prédire", 1, 30, 7)
            degree = st.slider("Degré polynôme", 1, 5, 2)
        with col2:
            conf = st.checkbox("Intervalle confiance", True)
        
        model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
        model.fit(X, y)
        
        last_day = X[-1][0]
        future_days = np.arange(last_day + 1, last_day + days + 1).reshape(-1, 1)
        pred = model.predict(future_days)
        
        last_date = df['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=y, mode='lines', name='Historique'))
        fig.add_trace(go.Scatter(x=future_dates, y=pred, mode='lines+markers', 
                                name='Prédictions', line=dict(dash='dash', color='red')))
        
        if conf:
            resid = y - model.predict(X)
            std = np.std(resid)
            upper = pred + 2*std
            lower = pred - 2*std
            fig.add_trace(go.Scatter(
                x=future_dates + future_dates[::-1],
                y=np.concatenate([upper, lower[::-1]]),
                fill='toself', fillcolor='rgba(255,0,0,0.2)',
                line=dict(color='rgba(255,0,0,0)'), name='IC 95%'
            ))
        
        fig.update_layout(title=f"Prédictions {days} jours", template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(pd.DataFrame({
            'Date': [d.strftime('%Y-%m-%d') for d in future_dates],
            'Prédiction': [f"{p:.2f} THB" for p in pred],
            'Variation': [f"{(p/current_price-1)*100:.1f}%" for p in pred]
        }))

# ============================================================================
# SECTION INDICES
# ============================================================================

elif menu == "🇹🇭 Indices thaïlandais":
    st.subheader("🇹🇭 Indices SET")
    
    indices = {
        '^SET.BK': 'SET Index',
        '^SET50.BK': 'SET50 Index',
        '^SET100.BK': 'SET100 Index',
        '^MAI.BK': 'MAI Index',
        '^sSET.BK': 'sSET Index',
        '^SETHD.BK': 'SETHD Index'
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        idx = st.selectbox("Indice", list(indices.keys()), format_func=lambda x: indices[x])
        period_idx = st.selectbox("Période", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
    
    with col1:
        with st.spinner("Chargement..."):
            ticker = yf.Ticker(idx)
            hist_idx = ticker.history(period=period_idx)
            
            if not hist_idx.empty:
                current = hist_idx['Close'].iloc[-1]
                prev = hist_idx['Close'].iloc[-2] if len(hist_idx) > 1 else current
                change = ((current - prev) / prev * 100)
                
                st.metric(indices[idx], f"{current:,.2f}", f"{change:.2f}%")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_idx.index, y=hist_idx['Close'],
                    mode='lines', name=indices[idx],
                    line=dict(color='#00247D', width=2)
                ))
                fig.update_layout(height=400, template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# WATCHLIST
# ============================================================================

st.markdown("---")
st.subheader("📋 Watchlist SET")

cols_per_row = 4
for i in range(0, len(WATCHLIST), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, sym in enumerate(WATCHLIST[i:i+cols_per_row]):
        with cols[j]:
            try:
                ticker = yf.Ticker(sym)
                hist_w = ticker.history(period='2d')
                if len(hist_w) >= 2:
                    price = hist_w['Close'].iloc[-1]
                    prev = hist_w['Close'].iloc[-2]
                    change = ((price - prev) / prev * 100)
                    st.metric(sym, f"{price:.2f}", f"{change:.1f}%")
                else:
                    st.metric(sym, "N/A", "0.0%")
            except:
                st.metric(sym, "Err", "0.0%")

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "🇹🇭 Tracker Bourse Thaïlande - SET Bangkok | "
    "📊 Données Yahoo Finance | ⏱️ Temps réel différé<br>"
    "🕐 Support multi-fuseaux (UTC+4, +3, +2, +1, UTC, -5, -8, +5:30, +7, +8, +9, +10)"
    "</p>",
    unsafe_allow_html=True
)
