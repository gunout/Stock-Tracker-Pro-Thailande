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
import os
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pytz
import warnings
import random
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
    'UTC+4': pytz.timezone('Asia/Dubai'),  # Émirats/Golfe
    'UTC+3': pytz.timezone('Asia/Riyadh'),  # Arabie Saoudite
    'UTC+2': pytz.FixedOffset(120),  # Jérusalem/Le Caire
    'UTC+1': pytz.timezone('Europe/Paris'),  # Paris
    'UTC': pytz.UTC,  # UTC
    'UTC-5': pytz.timezone('America/New_York'),  # New York
    'UTC-8': pytz.timezone('America/Los_Angeles'),  # Los Angeles
    'UTC+5:30': pytz.timezone('Asia/Kolkata'),  # Inde
    'UTC+7': pytz.timezone('Asia/Bangkok'),  # Thaïlande (UTC+7 fixe)
    'UTC+8': pytz.timezone('Asia/Singapore'),  # Singapour/Chine
    'UTC+9': pytz.timezone('Asia/Tokyo'),  # Japon/Corée
    'UTC+10': pytz.timezone('Australia/Sydney'),  # Australie
}

# Fuseau horaire par défaut (utilisateur)
DEFAULT_USER_TZ = 'UTC+7'  # Par défaut pour la Thaïlande

# Fuseau horaire de la Thaïlande (fixe UTC+7 toute l'année)
THAILAND_TZ = pytz.timezone('Asia/Bangkok')  # UTC+7 constant

if 'selected_timezone' not in st.session_state:
    st.session_state.selected_timezone = DEFAULT_USER_TZ

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
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
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
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .portfolio-table {
        font-size: 0.9rem;
    }
    .stButton>button {
        width: 100%;
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
    .tfex-badge {
        background-color: #006747;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
    }
    .demo-mode-badge {
        background-color: #ff9800;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 1rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 0.5rem;
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
</style>
""", unsafe_allow_html=True)

# Initialisation des variables de session
if 'price_alerts' not in st.session_state:
    st.session_state.price_alerts = []

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        # SET50 Stocks (larges capitalisations)
        'PTT.BK',  # PTT PCL
        'PTTEP.BK',  # PTT Exploration and Production
        'PTTGC.BK',  # PTT Global Chemical
        'SCB.BK',  # Siam Commercial Bank
        'KBANK.BK',  # Kasikornbank
        'BBL.BK',  # Bangkok Bank
        'KTB.BK',  # Krung Thai Bank
        'ADVANC.BK',  # Advanced Info Service
        'AOT.BK',  # Airports of Thailand
        'CPALL.BK',  # CP All
        'CPF.BK',  # Charoen Pokphand Foods
        'TRUE.BK',  # True Corporation
        'DTAC.BK',  # Total Access Communication
        'INTUCH.BK',  # Intouch Holdings
        'GULF.BK',  # Gulf Energy Development
        'BGRIM.BK',  # B.Grimm Power
        'GPSC.BK',  # Global Power Synergy
        'EA.BK',  # Energy Absolute
        'BPP.BK',  # Banpu Power
        'TOP.BK',  # Thai Oil
        'IRPC.BK',  # IRPC
        'SCC.BK',  # Siam Cement
        'SCGP.BK',  # SCG Packaging
        'IVL.BK',  # Indorama Ventures
        'BEM.BK',  # Bangkok Expressway and Metro
        'BTS.BK',  # BTS Group Holdings
        'CRC.BK',  # Central Retail Corporation
        'CPN.BK',  # Central Pattana
        'HMPRO.BK',  # Home Product Center
        'GLOBAL.BK',  # Siam Global House
        'COM7.BK',  # Com7
        'MINT.BK',  # Minor International
        'CENTEL.BK',  # Central Plaza Hotel
        'ERW.BK',  # The Erawan Group
        'BDMS.BK',  # Bangkok Dusit Medical Services
        'BH.BK',  # Bumrungrad Hospital
        'CHG.BK',  # Chularat Hospital
        'THG.BK',  # Thonburi Healthcare Group
        'DELTA.BK',  # Delta Electronics Thailand
        'HANA.BK',  # Hana Microelectronics
        'KCE.BK',  # KCE Electronics
        'SVI.BK',  # SVI
        'TU.BK',  # Thai Union Group
        'TKN.BK',  # Taokaenoi Food & Marketing
        'OSP.BK',  # Osotspa
        'SAPPE.BK',  # Sappe
        'BJC.BK',  # Berli Jucker
        'STA.BK',  # Sri Trang Agro-Industry
        'VGI.BK',  # VGI
        'JMART.BK',  # JMART Group
        'SINGER.BK',  # Singer Thailand
        'THANI.BK',  # Ratchthani Leasing
        'MTC.BK',  # Muangthai Capital
        'SAWAD.BK',  # Srisawad Corporation
        'TIDLOR.BK',  # Ngern Tid Lor
        'OR.BK',  # PTT Oil and Retail Business
        'BANPU.BK',  # Banpu
        'TTA.BK',  # Thoresen Thai Agencies
        'PSL.BK',  # Precious Shipping
        'RCL.BK',  # Regional Container Lines
        'WHA.BK',  # WHA Corporation
        'AMATA.BK',  # Amata Corporation
        'ROJNA.BK',  # Rojana Industrial Park
        'LH.BK',  # Land and Houses
        'AP.BK',  # AP Thailand
        'SPALI.BK',  # Supalai
        'QH.BK',  # Quality Houses
        'SIRI.BK',  # Sansiri
        'ORI.BK',  # Origin Property
        'SC.BK',  # SC Asset
        'NOBLE.BK',  # Noble Development
        'ANAN.BK',  # Ananda Development
        
        # MAI Stocks (moyennes capitalisations)
        'BEAUTY.BK',  # Beauty Community
        'BGT.BK',  # BGT Corporation
        'BWG.BK',  # Better World Green
        'CAZ.BK',  # CAZ Thailand
        'CHOW.BK',  # Chow Steel Industries
        'CI.BK',  # Charn Issara Development
        'CIG.BK',  # CIG Entertainment
        'CM.BK',  # Chiangmai Frozen Foods
        'CMO.BK',  # CMO
        'CMR.BK',  # CMR
        'COTTO.BK',  # Cotto
        'CPR.BK',  # CPR Gomu Industrial
        'CRD.BK',  # Chaopraya Mahanakorn
        'CSC.BK',  # CSC
        'CSP.BK',  # CSP Steel Center
        'CTW.BK',  # Charn Issara Tower
        'DEMCO.BK',  # Demco
        'DRT.BK',  # Diamond Roofing Tiles
        'DSGT.BK',  # DSG International Thailand
        'DTC.BK',  # DTC Enterprise
        'EASON.BK',  # Eason Paint
        'EKH.BK',  # Ekhachai Medical Care
        'ESSO.BK',  # Esso Thailand
        'FANCY.BK',  # Fancy Wood Industries
        'FLOYD.BK',  # Floyd
        'FORTH.BK',  # Forth Corporation
        'FUTURE.BK',  # Future Park
        'GENCO.BK',  # General Engineering
        'GJS.BK',  # G J Steel
        'GLAND.BK',  # Grand Canal Land
        'GUNKUL.BK',  # Gunkul Engineering
        'HYDRO.BK',  # Hydrotek
        'ICHI.BK',  # Ichitan Group
        'ILINK.BK',  # Interlink Communication
        'INET.BK',  # Internet Thailand
        'INOX.BK',  # POSCO-Thainox
        'INSURE.BK',  # NSI
        'IRC.BK',  # IRC
        'ITD.BK',  # Italian-Thai Development
        'J.BK',  # J
        'JAS.BK',  # Jasmine International
        'JTS.BK',  # Jasmine Telecom Systems
        'JUBILE.BK',  # Jubilee Enterprise
        'KAMART.BK',  # Kamart
        'KC.BK',  # KC Property
        'KGI.BK',  # KGI Securities
        'KIAT.BK',  # Kiattana Transport
        'KKP.BK',  # Kiatnakin Phatra Bank
        'KSL.BK',  # Khonburi Sugar
        'KTIS.BK',  # Kaset Thai International Sugar
        'KWC.BK',  # KWC World
        'KWM.BK',  # K.W. Metal Work
        'LALIN.BK',  # Lalin Property
        'LDC.BK',  # LDC Dental
        'LEO.BK',  # Leo Global Logistics
        'LHK.BK',  # L H K
        'LIT.BK',  # Lit
        'LOXLEY.BK',  # Loxley
        'LPN.BK',  # L.P.N. Development
        'LRH.BK',  # Laguna Resorts & Hotels
        'MACO.BK',  # Master Ad
        'MAJOR.BK',  # Major Cineplex
        'MAKRO.BK',  # Siam Makro
        'MATI.BK',  # Matichon
        'MBAX.BK',  # MBAX
        'MEGA.BK',  # Mega Lifesciences
        'METCO.BK',  # Metro
        'MILL.BK',  # Millcon Steel
        'MJD.BK',  # M.J. Development
        'MK.BK',  # MK Restaurant Group
        'ML.BK',  # M L
        'MODERN.BK',  # Modernform Group
        'MOONG.BK',  # Moong Pattana
        'MPIC.BK',  # M Pictures Entertainment
        'MSC.BK',  # MSC
        'MST.BK',  # M Securities
        'NC.BK',  # New City
        'NCH.BK',  # N C Housing
        'NCL.BK',  # NCL International Logistics
        'NEP.BK',  # Never Die
        'NETBAY.BK',  # Netbay
        'NEWS.BK',  # News Network
        'NFC.BK',  # NFC
        'NMG.BK',  # Nation Group
        'NNCL.BK',  # Navanakorn
        'NOBLE.BK',  # Noble Development
        'NOK.BK',  # NOK Airlines
        'NPP.BK',  # NPP
        'NSI.BK',  # NSI
        'NTV.BK',  # NTV
        'NWR.BK',  # Nawarat Patanakarn
        'OCC.BK',  # O.C.C.
        'OGC.BK',  # Ocean Glass
        'OISHI.BK',  # Oishi Group
        'PACE.BK',  # Pace Development
        'PATO.BK',  # PATO Chemical Industry
        'PB.BK',  # President Bakery
        'PCSGH.BK',  # P.C.S. Machine Group Holding
        'PDG.BK',  # Padaeng Industry
        'PDI.BK',  # Phol Dhanya
        'PERM.BK',  # Permsin Steel Works
        'PJW.BK',  # Panjawattana Plastic
        'PL.BK',  # PL
        'PLANB.BK',  # Plan B Media
        'PLE.BK',  # Power Line Engineering
        'PM.BK',  # Premier Marketing
        'POLAR.BK',  # Polar
        'POST.BK',  # Post Publishing
        'PPM.BK',  # PPM
        'PPP.BK',  # Premier Products
        'PR.BK',  # Preuksa Real Estate
        'PRECHA.BK',  # Precha Group
        'PRG.BK',  # Patara Reinsurance
        'PRIN.BK',  # Principal Capital
        'PRINC.BK',  # Principal Healthcare
        'PRO.BK',  # Professional Waste Technology
        'PROUD.BK',  # Proud Real Estate
        'PS.BK',  # PSG Corporation
        'PSTC.BK',  # Power Solution Technologies
        'PT.BK',  # Premier Technology
        'PTG.BK',  # PTG Energy
        'PTL.BK',  # Pelangi
        'PylON.BK',  # Pylon
        'Q-CON.BK',  # Quality Construction Products
        'QLT.BK',  # QLT
        'QTC.BK',  # QTC Energy
        'RATCH.BK',  # Ratchaburi Electricity
        'RCL.BK',  # Regional Container Lines
        'RICHY.BK',  # Richy Place 2002
        'RML.BK',  # Raimon Land
        'ROBINS.BK',  # Robinson Department Store
        'ROCK.BK',  # R Octagon
        'ROH.BK',  # ROH
        'ROJNA.BK',  # Rojana Industrial Park
        'RPC.BK',  # RPCG
        'RPH.BK',  # Ratchaphruek Hospital
        'RS.BK',  # RS
        'S.BK',  # S
        'S11.BK',  # S11 Group
        'SABINA.BK',  # Sabina
        'SALEE.BK',  # Salee Colour
        'SAM.BK',  # Samchai Steel Industries
        'SAMART.BK',  # Samart Corporation
        'SAMCO.BK',  # Samchai Steel Industries
        'SAMTEL.BK',  # Samart Telcoms
        'SAPPE.BK',  # Sappe
        'SAT.BK',  # Somboon Advance Technology
        'SAUCE.BK',  # Thai Theparos
        'SAWAD.BK',  # Srisawad Corporation
        'SCB.BK',  # Siam Commercial Bank
        'SCC.BK',  # Siam Cement
        'SCG.BK',  # SCG Decor
        'SCI.BK',  # SCI Electric
        'SCN.BK',  # Scan Inter
        'SCP.BK',  # Siam Carabao
        'SEAFCO.BK',  # Seafco
        'SEAOIL.BK',  # Sea Oil
        'SEMA.BK',  # Sema Phatthana
        'SFP.BK',  # S Food
        'SGF.BK',  # SGF
        'SGP.BK',  # Siamgas and Petrochemicals
        'SIAM.BK',  # Siam Motors
        'SICT.BK',  # SICT
        'SIMPLE.BK',  # Simple
        'SINGER.BK',  # Singer Thailand
        'SIRI.BK',  # Sansiri
        'SIS.BK',  # SIS Distribution
        'SISB.BK',  # SISB
        'SITHAI.BK',  # Sithiporn Associates
        'SKN.BK',  # SKN
        'SKR.BK',  # Sikum
        'SM.BK',  # Smart
        'SMC.BK',  # SMC Motors
        'SMIT.BK',  # SMIT
        'SMK.BK',  # SMK
        'SMPC.BK',  # Sahamitr Pressure Container
        'SMT.BK',  # Stars Microelectronics
        'SNC.BK',  # SNC Former
        'SNNP.BK',  # S N N P
        'SNP.BK',  # SNP
        'SOLAR.BK',  # Solar
        'SONIC.BK',  # Sonic Interfreight
        'SORKON.BK',  # Sorkon
        'SPA.BK',  # Siam Wellness Group
        'SPALI.BK',  # Supalai
        'SPC.BK',  # SPC
        'SPCG.BK',  # SPCG
        'SPI.BK',  # Saha Pathanapibul
        'SPRC.BK',  # Star Petroleum Refining
        'SR.BK',  # S
        'SSC.BK',  # SSC
        'SST.BK',  # SST
        'STA.BK',  # Sri Trang Agro-Industry
        'STANLY.BK',  # Thai Stanley Electric
        'STEC.BK',  # Sino-Thai Engineering and Construction
        'STI.BK',  # STC
        'STPI.BK',  # STPI
        'SUC.BK',  # Suc
        'SUPER.BK',  # Super
        'SUSCO.BK',  # Susco
        'SUTHA.BK',  # Sutha
        'SVI.BK',  # SVI
        'SVOA.BK',  # SVOA
        'SWC.BK',  # Swiss
        'SYMC.BK',  # Symc
        'SYNEX.BK',  # Synnex
        'T.BK',  # T
        'TAE.BK',  # TAE
        'TAKUNI.BK',  # Takuni Group
        'TASCO.BK',  # Tipco Asphalt
        'TBSP.BK',  # TBSP
        'TCC.BK',  # TCC
        'TCMC.BK',  # TCMC
        'TEAM.BK',  # Team
        'TEAMG.BK',  # Team Group
        'TFG.BK',  # Thai Foods Group
        'TGE.BK',  # Thachang Green Energy
        'TGPRO.BK',  # Thai Group
        'THAI.BK',  # Thai Airways International
        'THANA.BK',  # Thanasiri Group
        'THANI.BK',  # Ratchthani Leasing
        'THG.BK',  # Thonburi Healthcare Group
        'THIP.BK',  # Thip
        'THRE.BK',  # Thai Reinsurance
        'THREL.BK',  # Thai Reinsurance
        'TIDLOR.BK',  # Ngern Tid Lor
        'TIF1.BK',  # TIF
        'TIGER.BK',  # Tiger
        'TILE.BK',  # TILE
        'TIP.BK',  # Tip
        'TIPCO.BK',  # Tipco
        'TISCO.BK',  # Tisco Financial Group
        'TK.BK',  # Thitikorn
        'TKC.BK',  # TKC
        'TKN.BK',  # Taokaenoi Food & Marketing
        'TKS.BK',  # TKS Technologies
        'TKT.BK',  # TKT
        'TMD.BK',  # TMD
        'TMI.BK',  # TMI
        'TMLL.BK',  # TMILL
        'TMT.BK',  # TMT
        'TNDT.BK',  # TNDT
        'TNITY.BK',  # Trinity
        'TNL.BK',  # Thanulux
        'TNR.BK',  # TNR
        'TOG.BK',  # Thai Optical Group
        'TOP.BK',  # Thai Oil
        'TPAC.BK',  # TPAC
        'TPBI.BK',  # TPBI
        'TPCH.BK',  # TPCS
        'TPCORP.BK',  # TPCS
        'TPCS.BK',  # TPCS
        'TPIPL.BK',  # TPI Polene
        'TPP.BK',  # TPP
        'TR.BK',  # TR
        'TRAIN.BK',  # Train
        'TRC.BK',  # TRC
        'TRT.BK',  # TRT
        'TRU.BK',  # Tru
        'TRUE.BK',  # True Corporation
        'TRV.BK',  # TRV
        'TSC.BK',  # TSC
        'TSE.BK',  # TSE
        'TSTE.BK',  # Thai Sugar Terminal
        'TSTH.BK',  # TSTH
        'TTA.BK',  # Thoresen Thai Agencies
        'TTB.BK',  # TMBThanachart Bank
        'TTCL.BK',  # TTCL
        'TTW.BK',  # TTW
        'TU.BK',  # Thai Union Group
        'TVD.BK',  # TVD
        'TVT.BK',  # TVT
        'TWPC.BK',  # Thai Wah
        'TYCN.BK',  # TYCN
        'U.BK',  # U
        'UAC.BK',  # UAC
        'UBIS.BK',  # UBIS
        'UEC.BK',  # UEC
        'UMI.BK',  # UMI
        'UP.BK',  # UP
        'UPF.BK',  # UPF
        'UPIC.BK',  # UPIC
        'UPLO.BK',  # UPLO
        'UPOIC.BK',  # UPOIC
        'UT.BK',  # UT
        'UTP.BK',  # UTP
        'UV.BK',  # UV
        'VARO.BK',  # VARO
        'VCOM.BK',  # VCOM
        'VGI.BK',  # VGI
        'VIBHA.BK',  # Vibhavadi Medical Center
        'VNG.BK',  # VNG
        'VNT.BK',  # Vinythai
        'WACOAL.BK',  # Thai Wacoal
        'WAVE.BK',  # Wave Entertainment
        'WHA.BK',  # WHA Corporation
        'WHABK.BK',  # WHA Premium Growth
        'WICE.BK',  # WICE Logistics
        'WIN.BK',  # Win
        'WINNER.BK',  # Winner
        'WORK.BK',  # Workpoint Entertainment
        'WP.BK',  # World Property
        'WPH.BK',  # Wattanapat Hospital
        'XPG.BK',  # XPG
        'YCI.BK',  # YCI
        'YGG.BK',  # YGG
        'YUASA.BK',  # Yuasa Battery
        'ZEN.BK',  # Zen
    ]

if 'notifications' not in st.session_state:
    st.session_state.notifications = []

if 'email_config' not in st.session_state:
    st.session_state.email_config = {
        'enabled': False,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email': '',
        'password': ''
    }

if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False

if 'last_successful_data' not in st.session_state:
    st.session_state.last_successful_data = {}

# Mapping des suffixes pour la Thaïlande
THAI_EXCHANGES = {
    '.BK': 'Stock Exchange of Thailand (SET) - ตลาดหลักทรัพย์แห่งประเทศไทย',
    '.BK': 'Market for Alternative Investment (MAI) - ตลาดหลักทรัพย์ เอ็ม เอ ไอ',
    '.BK': 'Thailand Futures Exchange (TFEX) - ตลาดสัญญาซื้อขายล่วงหน้า',
}

# Jours fériés en Thaïlande
THAI_HOLIDAYS_2024 = [
    '2024-01-01',  # New Year's Day
    '2024-01-02',  # New Year's Holiday
    '2024-02-24',  # Makha Bucha Day
    '2024-04-06',  # Chakri Memorial Day
    '2024-04-08',  # Additional holiday
    '2024-04-13',  # Songkran Festival
    '2024-04-14',  # Songkran Festival
    '2024-04-15',  # Songkran Festival
    '2024-04-16',  # Songkran Festival
    '2024-05-01',  # National Labour Day
    '2024-05-04',  # Coronation Day
    '2024-05-22',  # Visakha Bucha Day
    '2024-06-03',  # Queen's Birthday
    '2024-07-20',  # Asalha Puja Day
    '2024-07-21',  # Buddhist Lent Day
    '2024-07-22',  # Buddhist Lent Holiday
    '2024-07-28',  # King's Birthday
    '2024-08-12',  # Mother's Day
    '2024-10-13',  # King Bhumibol Memorial Day
    '2024-10-14',  # Additional holiday
    '2024-10-23',  # Chulalongkorn Day
    '2024-12-05',  # Father's Day
    '2024-12-10',  # Constitution Day
    '2024-12-31',  # New Year's Eve
]

# Données de démonstration pour les principales actions thaïlandaises
DEMO_DATA = {
    'PTT.BK': {
        'name': 'PTT Public Company Limited (ปตท.)',
        'current_price': 35.50,
        'previous_close': 35.25,
        'day_high': 35.75,
        'day_low': 35.00,
        'volume': 25000000,
        'market_cap': 1014000000000,  # 1.014 Trillion THB
        'pe_ratio': 12.5,
        'dividend_yield': 4.8,
        'beta': 0.9,
        'sector': 'Energy',
        'industry': 'Oil & Gas',
        'website': 'www.pttplc.com'
    },
    'PTTEP.BK': {
        'name': 'PTT Exploration and Production (ปตท.สำรวจและผลิตปิโตรเลียม)',
        'current_price': 152.00,
        'previous_close': 151.00,
        'day_high': 153.50,
        'day_low': 150.50,
        'volume': 8000000,
        'market_cap': 603000000000,
        'pe_ratio': 8.2,
        'dividend_yield': 3.5,
        'beta': 1.1,
        'sector': 'Energy',
        'industry': 'Oil & Gas Exploration',
        'website': 'www.pttep.com'
    },
    'SCB.BK': {
        'name': 'Siam Commercial Bank (ธนาคารไทยพาณิชย์)',
        'current_price': 112.00,
        'previous_close': 111.50,
        'day_high': 113.00,
        'day_low': 111.00,
        'volume': 5000000,
        'market_cap': 380000000000,
        'pe_ratio': 9.8,
        'dividend_yield': 5.2,
        'beta': 0.8,
        'sector': 'Financials',
        'industry': 'Banking',
        'website': 'www.scb.co.th'
    },
    'KBANK.BK': {
        'name': 'Kasikornbank (ธนาคารกสิกรไทย)',
        'current_price': 138.00,
        'previous_close': 137.50,
        'day_high': 139.00,
        'day_low': 137.00,
        'volume': 6000000,
        'market_cap': 327000000000,
        'pe_ratio': 10.2,
        'dividend_yield': 4.9,
        'beta': 0.9,
        'sector': 'Financials',
        'industry': 'Banking',
        'website': 'www.kasikornbank.com'
    },
    'ADVANC.BK': {
        'name': 'Advanced Info Service (AIS)',
        'current_price': 220.00,
        'previous_close': 219.00,
        'day_high': 222.00,
        'day_low': 218.00,
        'volume': 3000000,
        'market_cap': 654000000000,
        'pe_ratio': 18.5,
        'dividend_yield': 3.2,
        'beta': 0.7,
        'sector': 'Telecommunications',
        'industry': 'Mobile Services',
        'website': 'www.ais.co.th'
    },
    'CPALL.BK': {
        'name': 'CP All (ซีพี ออลล์)',
        'current_price': 58.00,
        'previous_close': 57.75,
        'day_high': 58.50,
        'day_low': 57.50,
        'volume': 15000000,
        'market_cap': 521000000000,
        'pe_ratio': 22.3,
        'dividend_yield': 2.1,
        'beta': 0.6,
        'sector': 'Consumer',
        'industry': 'Retail',
        'website': 'www.cpall.co.th'
    },
    'AOT.BK': {
        'name': 'Airports of Thailand (ท่าอากาศยานไทย)',
        'current_price': 67.00,
        'previous_close': 66.50,
        'day_high': 67.50,
        'day_low': 66.00,
        'volume': 12000000,
        'market_cap': 957000000000,
        'pe_ratio': 45.2,
        'dividend_yield': 0.8,
        'beta': 1.3,
        'sector': 'Transportation',
        'industry': 'Airport Services',
        'website': 'www.airportthai.co.th'
    },
    'DELTA.BK': {
        'name': 'Delta Electronics Thailand',
        'current_price': 780.00,
        'previous_close': 775.00,
        'day_high': 790.00,
        'day_low': 770.00,
        'volume': 2000000,
        'market_cap': 975000000000,
        'pe_ratio': 65.8,
        'dividend_yield': 0.5,
        'beta': 1.5,
        'sector': 'Technology',
        'industry': 'Electronics',
        'website': 'www.deltathailand.com'
    },
    'SCC.BK': {
        'name': 'Siam Cement (ปูนซิเมนต์ไทย)',
        'current_price': 338.00,
        'previous_close': 336.00,
        'day_high': 340.00,
        'day_low': 335.00,
        'volume': 2000000,
        'market_cap': 406000000000,
        'pe_ratio': 14.3,
        'dividend_yield': 3.8,
        'beta': 1.0,
        'sector': 'Industrial',
        'industry': 'Building Materials',
        'website': 'www.siamcement.com'
    },
    'BDMS.BK': {
        'name': 'Bangkok Dusit Medical Services (กรุงเทพดุสิตเวชการ)',
        'current_price': 28.00,
        'previous_close': 27.75,
        'day_high': 28.25,
        'day_low': 27.50,
        'volume': 25000000,
        'market_cap': 444000000000,
        'pe_ratio': 25.6,
        'dividend_yield': 1.5,
        'beta': 0.5,
        'sector': 'Healthcare',
        'industry': 'Hospitals',
        'website': 'www.bdms.co.th'
    },
    'BH.BK': {
        'name': 'Bumrungrad Hospital (โรงพยาบาลบำรุงราษฎร์)',
        'current_price': 245.00,
        'previous_close': 243.00,
        'day_high': 247.00,
        'day_low': 242.00,
        'volume': 1000000,
        'market_cap': 194000000000,
        'pe_ratio': 32.1,
        'dividend_yield': 1.2,
        'beta': 0.6,
        'sector': 'Healthcare',
        'industry': 'Hospitals',
        'website': 'www.bumrungrad.com'
    },
    'CPF.BK': {
        'name': 'Charoen Pokphand Foods (เจริญโภคภัณฑ์อาหาร)',
        'current_price': 23.50,
        'previous_close': 23.40,
        'day_high': 23.70,
        'day_low': 23.30,
        'volume': 18000000,
        'market_cap': 188000000000,
        'pe_ratio': 18.7,
        'dividend_yield': 4.2,
        'beta': 0.8,
        'sector': 'Agribusiness',
        'industry': 'Food Products',
        'website': 'www.cpfworldwide.com'
    },
    'GULF.BK': {
        'name': 'Gulf Energy Development',
        'current_price': 48.50,
        'previous_close': 48.00,
        'day_high': 49.00,
        'day_low': 47.75,
        'volume': 10000000,
        'market_cap': 570000000000,
        'pe_ratio': 42.3,
        'dividend_yield': 1.0,
        'beta': 1.2,
        'sector': 'Energy',
        'industry': 'Power Generation',
        'website': 'www.gulf.co.th'
    },
    'MINT.BK': {
        'name': 'Minor International (ไมเนอร์ อินเตอร์เนชั่นแนล)',
        'current_price': 28.75,
        'previous_close': 28.50,
        'day_high': 29.00,
        'day_low': 28.25,
        'volume': 12000000,
        'market_cap': 162000000000,
        'pe_ratio': 35.4,
        'dividend_yield': 0.9,
        'beta': 1.4,
        'sector': 'Hospitality',
        'industry': 'Hotels & Restaurants',
        'website': 'www.minorinternational.com'
    },
    'TRUE.BK': {
        'name': 'True Corporation (ทรู คอร์ปอเรชั่น)',
        'current_price': 5.25,
        'previous_close': 5.20,
        'day_high': 5.35,
        'day_low': 5.15,
        'volume': 50000000,
        'market_cap': 180000000000,
        'pe_ratio': 25.6,
        'dividend_yield': 0.0,
        'beta': 1.1,
        'sector': 'Telecommunications',
        'industry': 'Integrated Telecom',
        'website': 'www.truecorp.co.th'
    },
    'TIDLOR.BK': {
        'name': 'Ngern Tid Lor (เงินติดล้อ)',
        'current_price': 21.30,
        'previous_close': 21.10,
        'day_high': 21.50,
        'day_low': 20.90,
        'volume': 8000000,
        'market_cap': 58500000000,
        'pe_ratio': 18.9,
        'dividend_yield': 2.5,
        'beta': 0.9,
        'sector': 'Financials',
        'industry': 'Consumer Finance',
        'website': 'www.tidlor.com'
    },
    'OR.BK': {
        'name': 'PTT Oil and Retail Business',
        'current_price': 17.60,
        'previous_close': 17.50,
        'day_high': 17.80,
        'day_low': 17.30,
        'volume': 20000000,
        'market_cap': 211000000000,
        'pe_ratio': 16.2,
        'dividend_yield': 3.5,
        'beta': 0.8,
        'sector': 'Energy',
        'industry': 'Oil Retail',
        'website': 'www.pttor.com'
    }
}

# Horaires du marché thaïlandais (heure locale)
THAI_MARKET_HOURS = {
    'SET': {
        'morning_open': 10,  # 10:00
        'morning_close': 12,  # 12:00 (midi)
        'afternoon_open': 14,  # 14:00
        'afternoon_close': 16,  # 16:30 (16h30)
        'pre_open': 9,  # 9:00 (pré-ouverture)
        'post_close': 17,  # Après 17:00
        'tz': 'Asia/Bangkok'
    },
    'MAI': {
        'morning_open': 10,
        'morning_close': 12,
        'afternoon_open': 14,
        'afternoon_close': 16,
        'pre_open': 9,
        'post_close': 17,
        'tz': 'Asia/Bangkok'
    },
    'TFEX': {
        'morning_open': 9,
        'morning_close': 12,
        'afternoon_open': 13,
        'afternoon_close': 16,
        'pre_open': 8,
        'post_close': 17,
        'tz': 'Asia/Bangkok'
    }
}

# Jours de trading en Thaïlande (lundi-vendredi)
THAI_TRADING_DAYS = [0, 1, 2, 3, 4]  # Lundi (0) à Vendredi (4)

# Devise
THAI_CURRENCY = 'THB'

# Fonction pour générer des données historiques de démonstration
def generate_demo_history(symbol, period="1mo", interval="1d"):
    """Génère des données historiques simulées pour la démonstration"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    # Prix de base selon le symbole
    if symbol in DEMO_DATA:
        base_price = DEMO_DATA[symbol]['current_price']
        if 'PTT' in symbol:
            volatility = 0.015
        elif 'KBANK' in symbol or 'SCB' in symbol:
            volatility = 0.02
        elif 'ADVANC' in symbol or 'TRUE' in symbol:
            volatility = 0.025
        elif 'DELTA' in symbol:
            volatility = 0.03
        elif 'AOT' in symbol:
            volatility = 0.022
        elif 'CPALL' in symbol:
            volatility = 0.018
        else:
            volatility = 0.02
    else:
        # Détection par suffixe (tous .BK en Thaïlande)
        base_price = random.uniform(10, 500)
        volatility = 0.02
    
    # Générer une série de prix avec une légère tendance
    np.random.seed(hash(symbol) % 42)
    returns = np.random.normal(0.0002, volatility, len(dates))
    price_series = base_price * np.exp(np.cumsum(returns))
    
    # Créer le DataFrame
    df = pd.DataFrame({
        'Open': price_series * (1 - np.random.uniform(0, 0.01, len(dates))),
        'High': price_series * (1 + np.random.uniform(0, 0.02, len(dates))),
        'Low': price_series * (1 - np.random.uniform(0, 0.02, len(dates))),
        'Close': price_series,
        'Volume': np.random.randint(100000, 5000000, len(dates))
    }, index=dates)
    
    # Convertir l'index en timezone-aware (UTC+7)
    df.index = df.index.tz_localize(THAILAND_TZ)
    
    return df

# Fonction pour charger les données avec gestion des erreurs améliorée
@st.cache_data(ttl=600)
def load_stock_data(symbol, period, interval, retry_count=3):
    """Charge les données boursières avec gestion des erreurs et retry"""
    
    # Vérifier si on a des données en cache dans la session
    if st.session_state.demo_mode and symbol in DEMO_DATA:
        return generate_demo_history(symbol, period, interval), DEMO_DATA[symbol]
    
    for attempt in range(retry_count):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval, timeout=10)
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
            
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                st.warning(f"⚠️ Limite de requêtes atteinte. Tentative {attempt + 1}/{retry_count}...")
            else:
                st.warning(f"⚠️ Erreur: {e}. Tentative {attempt + 1}/{retry_count}...")
    
    # Si toutes les tentatives échouent, utiliser les données en cache
    if symbol in st.session_state.last_successful_data:
        cached = st.session_state.last_successful_data[symbol]
        time_diff = datetime.now() - cached['timestamp']
        if time_diff.total_seconds() < 3600:
            st.info(f"📋 Utilisation des données en cache du {cached['timestamp'].strftime('%H:%M:%S')} (heure locale)")
            return cached['hist'], cached['info']
    
    # Activer le mode démo automatiquement
    if not st.session_state.demo_mode:
        st.session_state.demo_mode = True
        st.info("🔄 Mode démonstration activé - Données simulées")
    
    # Données de démonstration par défaut
    demo_info = {
        'longName': f'{symbol} (SET - Mode démo)',
        'sector': random.choice(['Financials', 'Energy', 'Technology', 'Consumer', 'Healthcare']),
        'industry': 'Various',
        'marketCap': random.randint(1000000000, 50000000000),
        'trailingPE': random.uniform(8, 30),
        'dividendYield': random.uniform(0.01, 0.06),
        'beta': random.uniform(0.5, 1.5),
        'website': 'www.set.or.th'
    }
    
    return generate_demo_history(symbol, period, interval), demo_info

def get_exchange_info(symbol):
    """Détermine l'échange pour un symbole thaïlandais"""
    if symbol.endswith('.BK'):
        # Tous les symboles .BK sont sur le SET (y compris MAI)
        return 'Stock Exchange of Thailand (SET)', 'Thailand', 'THB'
    return 'International Listing', 'International', 'USD'

def get_currency(symbol):
    """Détermine la devise pour un symbole"""
    if symbol.endswith('.BK'):
        return 'THB'
    return 'USD'

def format_thai_currency(value, symbol):
    """Formate la monnaie thaïlandaise (Baht)"""
    if value is None or value == 0:
        return "N/A"
    
    if value >= 1e9:  # Billion
        return f"{value/1e9:.2f} พันล้านบาท"  # Billion Baht
    elif value >= 1e6:  # Million
        return f"{value/1e6:.2f} ล้านบาท"  # Million Baht
    elif value >= 1e3:  # Thousand
        return f"{value/1e3:.2f} พันบาท"  # Thousand Baht
    else:
        return f"{value:.2f} บาท"  # Baht

def format_large_number_thai(num):
    """Formate les grands nombres en thaï"""
    if num > 1e12:
        return f"{num/1e12:.2f} ล้านล้าน"  # Trillion
    elif num > 1e9:
        return f"{num/1e9:.2f} พันล้าน"  # Billion
    elif num > 1e6:
        return f"{num/1e6:.2f} ล้าน"  # Million
    else:
        return f"{num:,.0f}"

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
    
    # Jour de la semaine (lundi=0, dimanche=6)
    weekday = now.weekday()
    
    # Weekend en Thaïlande (samedi-dimanche)
    if weekday >= 5:  # Samedi ou Dimanche
        return "Fermé (weekend)", "🔴"
    
    # Jours fériés
    date_str = now.strftime('%Y-%m-%d')
    if date_str in THAI_HOLIDAYS_2024:
        return "Fermé (jour férié)", "🔴"
    
    # Horaires de trading du SET
    current_hour = now.hour
    current_minute = now.minute
    current_time_decimal = current_hour + current_minute / 60.0
    
    morning_open = 10.0  # 10:00
    morning_close = 12.5  # 12:30 (12h30)
    afternoon_open = 14.0  # 14:00
    afternoon_close = 16.5  # 16:30 (16h30)
    
    if (morning_open <= current_time_decimal < morning_close) or \
       (afternoon_open <= current_time_decimal < afternoon_close):
        return "Ouvert", "🟢"
    elif current_time_decimal < morning_open:
        return "Fermé (pré-ouverture)", "🟡"
    elif morning_close <= current_time_decimal < afternoon_open:
        return "Pause midi", "🟠"
    else:
        return "Fermé", "🔴"

def get_market_status_with_timezone(user_tz):
    """Détermine le statut du marché avec conversion de fuseau horaire"""
    # Heure en Thaïlande
    thai_time = datetime.now(THAILAND_TZ)
    
    # Heure de l'utilisateur dans son fuseau
    user_time = thai_time.astimezone(user_tz)
    
    status, icon = get_market_status()
    
    return status, icon, thai_time, user_time

def safe_get_metric(hist, metric, index=-1):
    """Récupère une métrique en toute sécurité"""
    try:
        if hist is not None and not hist.empty and len(hist) > abs(index):
            return hist[metric].iloc[index]
        return 0
    except:
        return 0

# Titre principal
st.markdown("<h1 class='main-header'>🇹🇭 Tracker Bourse Thaïlande - SET Bangkok en Temps Réel</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-family: Sarabun; font-size: 1.5rem;'>ติดตามตลาดหลักทรัพย์แห่งประเทศไทย</p>", unsafe_allow_html=True)

# Sélecteur de fuseau horaire
st.markdown("<div class='tz-selector'>", unsafe_allow_html=True)
col_tz1, col_tz2 = st.columns([3, 1])
with col_tz1:
    st.markdown("**🕐 Sélectionnez votre fuseau horaire / เลือกเขตเวลาของคุณ**")
    selected_tz_key = st.selectbox(
        "",
        options=list(USER_TIMEZONES.keys()),
        index=list(USER_TIMEZONES.keys()).index(st.session_state.selected_timezone)
    )
    st.session_state.selected_timezone = selected_tz_key
    user_tz = USER_TIMEZONES[selected_tz_key]
with col_tz2:
    st.markdown(f"<br><span class='set-badge'>UTC+7 (Thaïlande)</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Obtenir le statut du marché
market_status, market_icon, thai_time, user_time = get_market_status_with_timezone(user_tz)

# Afficher le statut du marché
st.markdown(f"""
<div class='timezone-badge'>
    <b>🕐 Informations fuseaux horaires :</b><br>
    🇹🇭 Heure Thaïlande (SET) : {thai_time.strftime('%H:%M:%S')} (UTC+7)<br>
    🌍 Votre heure ({selected_tz_key}) : {user_time.strftime('%H:%M:%S')}<br>
    📊 Statut du marché SET : {market_icon} {market_status}<br>
    🔄 Décalage : {thai_time.utcoffset().total_seconds()/3600 - user_time.utcoffset().total_seconds()/3600:.1f} heures
</div>
""", unsafe_allow_html=True)

# Note sur les jours de trading
st.markdown("""
<div class='holiday-note'>
    📅 Horaires du SET : Session matin 10h00-12h30, Session après-midi 14h00-16h30 (heure Thaïlande)<br>
    📅 Jours de trading : Lundi au Vendredi (fermé samedi-dimanche et jours fériés)<br>
    🇹🇭 Songkran (Nouvel An thaï) : 13-15 avril - Marchés fermés
</div>
""", unsafe_allow_html=True)

# Mode démo badge
if st.session_state.demo_mode:
    st.markdown("""
    <div style='text-align: center; margin: 10px 0;'>
        <span class='demo-mode-badge'>🎮 MODE DÉMONSTRATION</span>
        <span style='color: #666;'>Données simulées - API temporairement indisponible</span>
    </div>
    """, unsafe_allow_html=True)

# Note sur le marché thaïlandais
st.markdown("""
<div class='thai-market-note'>
    <span class='set-badge'>SET - ตลาดหลักทรัพย์</span> 
    <span class='mai-badge'>MAI - ตลาดเอ็มเอไอ</span>
    <span class='tfex-badge'>TFEX - ตลาดฟิวเจอร์ส</span><br>
    🇹🇭 Principales places financières de Thaïlande<br>
    - Horaires: 10h00-12h30 et 14h00-16h30 (heure Thaïlande UTC+7)<br>
    - Samedi-dimanche: marchés fermés<br>
    - Devise: Baht thaïlandais (THB) - บาท<br>
    - Indices: SET Index, SET50, SET100, MAI Index, sSET, SETHD<br>
    - Secteurs clés: Énergie, Finance, Tourisme, Électronique, Agroalimentaire
</div>
""", unsafe_allow_html=True)

# Sidebar pour la navigation
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/thailand.png", width=80)
    st.title("Navigation")
    
    # Sélecteur de fuseau horaire dans la sidebar
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
    
    # Boutons pour le mode démo
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        if st.button("🎮 Mode Démo"):
            st.session_state.demo_mode = True
            st.rerun()
    with col_demo2:
        if st.button("🔄 Mode Réel"):
            st.session_state.demo_mode = False
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    menu = st.radio(
        "Choisir une section / เลือกหมวดหมู่",
        ["📈 Tableau de bord", 
         "💰 Portefeuille virtuel", 
         "🔔 Alertes de prix",
         "📧 Notifications email",
         "📤 Export des données",
         "🤖 Prédictions ML",
         "🇹🇭 Indices thaïlandais"]
    )
    
    st.markdown("---")
    
    # Configuration commune
    st.subheader("⚙️ Configuration")
    
    # Sélection du symbole principal
    symbol_options = ["PTT.BK (PTT)", "PTTEP.BK (PTTEP)", "SCB.BK (SCB)", 
                      "KBANK.BK (KBANK)", "ADVANC.BK (AIS)", "CPALL.BK (CP All)", 
                      "AOT.BK (AOT)", "DELTA.BK (DELTA)", "Autre..."]
    
    selected_option = st.selectbox(
        "Symbole principal / สัญลักษณ์หลัก",
        options=symbol_options,
        index=0
    )
    
    if selected_option == "Autre...":
        symbol = st.text_input("Entrer un symbole / ป้อนสัญลักษณ์", value="PTT.BK").upper()
        if not symbol.endswith('.BK'):
            symbol += '.BK'
    else:
        symbol = selected_option.split()[0]
    
    # Afficher des informations sur le symbole
    if symbol:
        exchange, country, currency = get_exchange_info(symbol)
        st.caption(f"📍 {exchange}")
        st.caption(f"🌍 {country} | 💱 {currency}")
    
    st.caption("""
    📍 Suffixes:
    - .BK: SET/MAI (Thaïlande)
    - Pas de suffixe pour international
    """)
    
    # Période et intervalle
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox(
            "Période / ระยะเวลา",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2
        )
    
    with col2:
        interval_map = {
            "1m": "1 minute", "5m": "5 minutes", "15m": "15 minutes",
            "30m": "30 minutes", "1h": "1 heure", "1d": "1 jour",
            "1wk": "1 semaine", "1mo": "1 mois"
        }
        interval = st.selectbox(
            "Intervalle / ช่วงเวลา",
            options=list(interval_map.keys()),
            format_func=lambda x: interval_map[x],
            index=4 if period == "1d" else 6
        )
    
    # Auto-refresh
    auto_refresh = st.checkbox("Actualisation automatique", value=False)
    if auto_refresh:
        st.warning("⚠️ L'actualisation automatique peut entraîner des limitations API")
        refresh_rate = st.slider(
            "Fréquence (secondes)",
            min_value=30,
            max_value=300,
            value=60,
            step=10
        )

# Chargement des données
try:
    hist, info = load_stock_data(symbol, period, interval)
except Exception as e:
    st.error(f"Erreur lors du chargement: {e}")
    st.session_state.demo_mode = True
    hist, info = generate_demo_history(symbol, period, interval), DEMO_DATA.get(symbol, {
        'longName': f'{symbol} (SET - Mode démo)',
        'sector': 'N/A',
        'industry': 'N/A'
    })

if hist is None or hist.empty:
    st.warning(f"⚠️ Impossible de charger les données pour {symbol}. Utilisation du mode démo.")
    st.session_state.demo_mode = True
    hist = generate_demo_history(symbol, period, interval)
    info = DEMO_DATA.get(symbol, {
        'longName': f'{symbol} (SET - Mode démo)',
        'sector': 'N/A',
        'industry': 'N/A',
        'marketCap': 10000000000
    })

current_price = safe_get_metric(hist, 'Close')

# Vérification des alertes
triggered_alerts = check_price_alerts(current_price, symbol)
for alert in triggered_alerts:
    st.balloons()
    st.success(f"🎯 Alerte déclenchée pour {symbol} à {format_thai_currency(current_price, symbol)}")
    
    if st.session_state.email_config['enabled']:
        subject = f"🚨 Alerte prix - {symbol}"
        body = f"""
        <h2>Alerte de prix déclenchée</h2>
        <p><b>Symbole:</b> {symbol}</p>
        <p><b>Prix actuel:</b> {format_thai_currency(current_price, symbol)}</p>
        <p><b>Condition:</b> {alert['condition']} {format_thai_currency(alert['price'], symbol)}</p>
        <p><b>Date (Thaïlande):</b> {datetime.now(THAILAND_TZ).strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Date (votre fuseau):</b> {datetime.now(user_tz).strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        send_email_alert(subject, body, st.session_state.email_config['email'])
    
    if alert.get('one_time', False):
        st.session_state.price_alerts.remove(alert)

# ============================================================================
# SECTION 1: TABLEAU DE BORD
# ============================================================================
if menu == "📈 Tableau de bord":
    # Statut du marché thaïlandais
    market_status, market_icon = get_market_status()
    st.info(f"{market_icon} Thailand SET: {market_status}")
    
    if hist is not None and not hist.empty:
        company_name = info.get('longName', symbol) if info else symbol
        if st.session_state.demo_mode:
            company_name += " (Mode démo)"
        
        st.subheader(f"📊 Aperçu en temps réel - {company_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        previous_close = safe_get_metric(hist, 'Close', -2) if len(hist) > 1 else current_price
        change = current_price - previous_close
        change_pct = (change / previous_close * 100) if previous_close != 0 else 0
        
        with col1:
            st.metric(
                label="Prix actuel",
                value=format_thai_currency(current_price, symbol),
                delta=f"{change:.2f} ({change_pct:.2f}%)"
            )
        
        with col2:
            day_high = safe_get_metric(hist, 'High')
            st.metric("Plus haut", format_thai_currency(day_high, symbol))
        
        with col3:
            day_low = safe_get_metric(hist, 'Low')
            st.metric("Plus bas", format_thai_currency(day_low, symbol))
        
        with col4:
            volume = safe_get_metric(hist, 'Volume')
            volume_formatted = f"{volume/1e6:.1f}M" if volume > 1e6 else f"{volume/1e3:.1f}K"
            st.metric("Volume", volume_formatted)
        
        # Afficher les heures dans différents fuseaux
        try:
            thai_time = hist.index[-1].tz_convert(THAILAND_TZ)
            user_time = hist.index[-1].tz_convert(user_tz)
            st.caption(f"Dernière mise à jour: {thai_time.strftime('%Y-%m-%d %H:%M:%S')} (heure Thaïlande) / {user_time.strftime('%H:%M:%S')} (votre heure)")
        except:
            st.caption(f"Dernière mise à jour: {datetime.now(THAILAND_TZ).strftime('%Y-%m-%d %H:%M:%S')} (heure Thaïlande)")
        
        # Graphique principal
        st.subheader("📉 Évolution du prix")
        
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
            ma_20 = hist['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_20,
                mode='lines',
                name='MA 20',
                line=dict(color='orange', width=1, dash='dash')
            ))
        
        if len(hist) >= 50:
            ma_50 = hist['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=ma_50,
                mode='lines',
                name='MA 50',
                line=dict(color='purple', width=1, dash='dash')
            ))
        
        fig.add_trace(go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name='Volume',
            yaxis='y2',
            marker=dict(color='lightgray', opacity=0.3)
        ))
        
        fig.update_layout(
            title=f"{symbol} - {period} (heure Thaïlande UTC+7)",
            yaxis_title=f"Prix (THB)",
            yaxis2=dict(
                title="Volume",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            xaxis_title="Date",
            height=600,
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Informations sur l'entreprise
        with st.expander("ℹ️ Informations sur l'entreprise"):
            if info:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nom :** {info.get('longName', 'N/A')}")
                    st.write(f"**Secteur :** {info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {info.get('industry', 'N/A')}")
                    st.write(f"**Site web :** {info.get('website', 'N/A')}")
                    st.write(f"**Bourse :** SET")
                    st.write(f"**Pays :** Thaïlande")
                    st.write(f"**Devise :** THB")
                
                with col2:
                    market_cap = info.get('marketCap', 0)
                    if market_cap > 0:
                        st.write(f"**Capitalisation :** {format_thai_currency(market_cap, symbol)} ({format_large_number_thai(market_cap)})")
                    else:
                        st.write("**Capitalisation :** N/A")
                    
                    st.write(f"**P/E :** {info.get('trailingPE', 'N/A')}")
                    st.write(f"**Dividende :** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**Dividende :** N/A")
                    st.write(f"**Beta :** {info.get('beta', 'N/A')}")
            else:
                st.write("Informations non disponibles")
    else:
        st.warning(f"Aucune donnée disponible pour {symbol}")

# ============================================================================
# SECTION 2: PORTEFEUILLE VIRTUEL
# ============================================================================
elif menu == "💰 Portefeuille virtuel":
    st.subheader("💰 Gestion de portefeuille virtuel - Actions Thaïlandaises")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### ➕ Ajouter une position")
        with st.form("add_position"):
            symbol_pf = st.text_input("Symbole", value="PTT.BK").upper()
            if not symbol_pf.endswith('.BK'):
                symbol_pf += '.BK'
            
            exchange, country, currency = get_exchange_info(symbol_pf)
            st.caption(f"📍 SET | {currency}")
            
            shares = st.number_input("Nombre d'actions", min_value=1, step=1, value=100)
            buy_price = st.number_input(f"Prix d'achat ({currency})", min_value=0.01, step=1.0, value=35.5)
            
            if st.form_submit_button("Ajouter au portefeuille"):
                if symbol_pf and shares > 0:
                    if symbol_pf not in st.session_state.portfolio:
                        st.session_state.portfolio[symbol_pf] = []
                    
                    st.session_state.portfolio[symbol_pf].append({
                        'shares': shares,
                        'buy_price': buy_price,
                        'currency': currency,
                        'country': 'Thailand',
                        'date': datetime.now(user_tz).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    st.success(f"✅ {shares} actions {symbol_pf} ajoutées")
    
    with col1:
        st.markdown("### 📊 Performance du portefeuille")
        
        if st.session_state.portfolio:
            portfolio_data = []
            total_value = 0
            total_cost = 0
            
            for symbol_pf, positions in st.session_state.portfolio.items():
                try:
                    if st.session_state.demo_mode and symbol_pf in DEMO_DATA:
                        current = DEMO_DATA[symbol_pf]['current_price']
                    else:
                        ticker = yf.Ticker(symbol_pf)
                        hist = ticker.history(period='1d')
                        current = hist['Close'].iloc[-1] if not hist.empty else 0
                    
                    exchange, country, currency = get_exchange_info(symbol_pf)
                    
                    for pos in positions:
                        shares = pos['shares']
                        buy_price = pos['buy_price']
                        cost = shares * buy_price
                        value = shares * current
                        profit = value - cost
                        profit_pct = (profit / cost * 100) if cost > 0 else 0
                        
                        total_cost += cost
                        total_value += value
                        
                        portfolio_data.append({
                            'Symbole': symbol_pf,
                            'Actions': shares,
                            "Prix d'achat": f"{buy_price:,.2f} {currency}",
                            'Prix actuel': f"{current:,.2f} {currency}",
                            'Valeur': f"{value:,.2f} {currency}",
                            'Profit': f"{profit:,.2f} {currency}",
                            'Profit %': f"{profit_pct:.1f}%"
                        })
                except Exception as e:
                    st.warning(f"Impossible de charger {symbol_pf}")
            
            if portfolio_data:
                total_profit = total_value - total_cost
                total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
                
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur totale", f"{total_value:,.2f} THB")
                col_i2.metric("Coût total", f"{total_cost:,.2f} THB")
                col_i3.metric(
                    "Profit total",
                    f"{total_profit:,.2f} THB",
                    delta=f"{total_profit_pct:.1f}%"
                )
                
                st.markdown("### 📋 Positions détaillées")
                df_portfolio = pd.DataFrame(portfolio_data)
                st.dataframe(df_portfolio, use_container_width=True)
                
                try:
                    fig_pie = px.pie(
                        names=[p['Symbole'] for p in portfolio_data],
                        values=[float(p['Valeur'].split()[0].replace(',', '')) for p in portfolio_data],
                        title="Répartition du portefeuille"
                    )
                    st.plotly_chart(fig_pie)
                except:
                    st.warning("Impossible de générer le graphique")
                
                if st.button("🗑️ Vider le portefeuille"):
                    st.session_state.portfolio = {}
                    st.rerun()
            else:
                st.info("Aucune donnée de performance disponible")
        else:
            st.info("Aucune position dans le portefeuille. Ajoutez des actions thaïlandaises pour commencer !")

# ============================================================================
# SECTION 3: ALERTES DE PRIX
# ============================================================================
elif menu == "🔔 Alertes de prix":
    st.subheader("🔔 Gestion des alertes de prix")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ➕ Créer une nouvelle alerte")
        with st.form("new_alert"):
            alert_symbol = st.text_input("Symbole", value=symbol if symbol else "PTT.BK").upper()
            if not alert_symbol.endswith('.BK'):
                alert_symbol += '.BK'
            
            exchange, country, currency = get_exchange_info(alert_symbol)
            st.caption(f"📍 SET | {currency}")
            
            default_price = float(current_price * 1.05) if current_price > 0 else 35.5
            alert_price = st.number_input(
                f"Prix cible ({currency})", 
                min_value=0.01, 
                step=1.0, 
                value=default_price
            )
            
            col_cond, col_type = st.columns(2)
            with col_cond:
                condition = st.selectbox("Condition", ["above (au-dessus)", "below (en-dessous)"])
                condition = condition.split()[0]
            with col_type:
                alert_type = st.selectbox("Type", ["Permanent", "Une fois"])
            
            one_time = alert_type == "Une fois"
            
            if st.form_submit_button("Créer l'alerte"):
                st.session_state.price_alerts.append({
                    'symbol': alert_symbol,
                    'price': alert_price,
                    'condition': condition,
                    'one_time': one_time,
                    'currency': currency,
                    'country': 'Thailand',
                    'created': datetime.now(user_tz).strftime('%Y-%m-%d %H:%M:%S')
                })
                st.success(f"✅ Alerte créée pour {alert_symbol} à {alert_price} {currency}")
    
    with col2:
        st.markdown("### 📋 Alertes actives")
        if st.session_state.price_alerts:
            for i, alert in enumerate(st.session_state.price_alerts):
                with st.container():
                    currency = alert.get('currency', 'THB')
                    st.markdown(f"""
                    <div class='alert-box alert-warning'>
                        <b>{alert['symbol']}</b> - {alert['condition']} {alert['price']:.2f} {currency}<br>
                        <small>Créée: {alert['created']} | {('Usage unique' if alert['one_time'] else 'Permanent')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Supprimer", key=f"del_alert_{i}"):
                        st.session_state.price_alerts.pop(i)
                        st.rerun()
        else:
            st.info("Aucune alerte active")

# ============================================================================
# SECTION 4: NOTIFICATIONS EMAIL
# ============================================================================
elif menu == "📧 Notifications email":
    st.subheader("📧 Configuration des notifications email")
    
    with st.form("email_config"):
        enabled = st.checkbox("Activer les notifications email", value=st.session_state.email_config['enabled'])
        
        col1, col2 = st.columns(2)
        with col1:
            smtp_server = st.text_input("Serveur SMTP", value=st.session_state.email_config['smtp_server'])
            smtp_port = st.number_input("Port SMTP", value=st.session_state.email_config['smtp_port'])
        
        with col2:
            email = st.text_input("Adresse email", value=st.session_state.email_config['email'])
            password = st.text_input("Mot de passe", type="password", value=st.session_state.email_config['password'])
        
        test_email = st.text_input("Email de test (optionnel)")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Sauvegarder"):
                st.session_state.email_config = {
                    'enabled': enabled,
                    'smtp_server': smtp_server,
                    'smtp_port': smtp_port,
                    'email': email,
                    'password': password
                }
                st.success("Configuration sauvegardée !")
        
        with col_btn2:
            if st.form_submit_button("📨 Tester"):
                if test_email:
                    thai_time = datetime.now(THAILAND_TZ)
                    user_time = datetime.now(user_tz)
                    if send_email_alert(
                        "Test de notification - SET Thailand",
                        f"<h2>Test réussi !</h2><p>Votre configuration email fonctionne correctement !</p><p>Heure Thaïlande: {thai_time.strftime('%Y-%m-%d %H:%M:%S')}</p><p>Votre heure: {user_time.strftime('%Y-%m-%d %H:%M:%S')}</p>",
                        test_email
                    ):
                        st.success("Email de test envoyé !")
                    else:
                        st.error("Échec de l'envoi")
    
    with st.expander("📋 Aperçu de la configuration"):
        st.json(st.session_state.email_config)

# ============================================================================
# SECTION 5: EXPORT DES DONNÉES
# ============================================================================
elif menu == "📤 Export des données":
    st.subheader("📤 Export des données")
    
    if hist is not None and not hist.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Données historiques")
            display_hist = hist.copy()
            display_hist.index = display_hist.index.strftime('%Y-%m-%d %H:%M:%S (heure Thaïlande)')
            st.dataframe(display_hist.tail(20))
            
            csv = hist.to_csv()
            st.download_button(
                label="📥 Télécharger en CSV",
                data=csv,
                file_name=f"{symbol}_data_{datetime.now(THAILAND_TZ).strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            st.markdown("### 📈 Rapport")
            st.info("Génération de rapport (simulée)")
            
            st.markdown("**Statistiques:**")
            stats = {
                'Moyenne': hist['Close'].mean(),
                'Écart-type': hist['Close'].std(),
                'Min': hist['Close'].min(),
                'Max': hist['Close'].max(),
                'Variation totale': f"{(hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100:.2f}%" if len(hist) > 1 else "N/A"
            }
            
            for key, value in stats.items():
                if isinstance(value, float):
                    st.write(f"{key}: {format_thai_currency(value, symbol)}")
                else:
                    st.write(f"{key}: {value}")
            
            json_data = {
                'symbol': symbol,
                'exchange': 'Stock Exchange of Thailand',
                'country': 'Thailand',
                'currency': 'THB',
                'last_update_thailand': datetime.now(THAILAND_TZ).isoformat(),
                'last_update_user': datetime.now(user_tz).isoformat(),
                'user_timezone': selected_tz_key,
                'current_price': float(current_price) if current_price else 0,
                'statistics': {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in stats.items()},
                'data': hist.reset_index().to_dict(orient='records')
            }
            
            st.download_button(
                label="📥 Télécharger en JSON",
                data=json.dumps(json_data, indent=2, default=str),
                file_name=f"{symbol}_data_{datetime.now(THAILAND_TZ).strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.warning(f"Aucune donnée à exporter pour {symbol}")

# ============================================================================
# SECTION 6: PRÉDICTIONS ML
# ============================================================================
elif menu == "🤖 Prédictions ML":
    st.subheader("🤖 Prédictions avec Machine Learning - SET Thailand")
    
    if hist is not None and not hist.empty and len(hist) > 30:
        st.markdown("### Modèle de prédiction (Régression polynomiale)")
        
        st.info(f"""
        ⚠️ Facteurs influençant le marché thaïlandais:
        - Tourisme (20% du PIB)
        - Exportations (électronique, automobile, agroalimentaire)
        - Prix du pétrole (impact sur les coûts)
        - Taux d'intérêt de la Banque de Thaïlande
        - Taux de change USD/THB
        - Stabilité politique
        - Investissements étrangers
        - Santé économique de la Chine (principal partenaire)
        - Secteur automobile (hub de production)
        - Agriculture et prix des matières premières
        - Mousson et climat (impact agricole)
        """)
        
        df_pred = hist[['Close']].reset_index()
        df_pred['Days'] = (df_pred['Date'] - df_pred['Date'].min()).dt.days
        
        X = df_pred['Days'].values.reshape(-1, 1)
        y = df_pred['Close'].values
        
        col1, col2 = st.columns(2)
        
        with col1:
            days_to_predict = st.slider("Jours à prédire", min_value=1, max_value=30, value=7)
            degree = st.slider("Degré du polynôme", min_value=1, max_value=5, value=2)
        
        with col2:
            show_confidence = st.checkbox("Afficher l'intervalle de confiance", value=True)
        
        model = make_pipeline(
            PolynomialFeatures(degree=degree),
            LinearRegression()
        )
        model.fit(X, y)
        
        last_day = X[-1][0]
        future_days = np.arange(last_day + 1, last_day + days_to_predict + 1).reshape(-1, 1)
        predictions = model.predict(future_days)
        
        last_date = df_pred['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_predict)]
        
        fig_pred = go.Figure()
        
        fig_pred.add_trace(go.Scatter(
            x=df_pred['Date'],
            y=y,
            mode='lines',
            name='Historique',
            line=dict(color='blue')
        ))
        
        fig_pred.add_trace(go.Scatter(
            x=future_dates,
            y=predictions,
            mode='lines+markers',
            name='Prédictions',
            line=dict(color='red', dash='dash'),
            marker=dict(size=8)
        ))
        
        if show_confidence:
            residuals = y - model.predict(X)
            std_residuals = np.std(residuals)
            
            upper_bound = predictions + 2 * std_residuals
            lower_bound = predictions - 2 * std_residuals
            
            fig_pred.add_trace(go.Scatter(
                x=future_dates + future_dates[::-1],
                y=np.concatenate([upper_bound, lower_bound[::-1]]),
                fill='toself',
                fillcolor='rgba(255,0,0,0.2)',
                line=dict(color='rgba(255,0,0,0)'),
                name='Intervalle confiance 95%'
            ))
        
        fig_pred.update_layout(
            title=f"Prédictions pour {symbol} - {days_to_predict} jours",
            xaxis_title="Date",
            yaxis_title="Prix (THB)",
            hovermode='x unified',
            template='plotly_white'
        )
        
        st.plotly_chart(fig_pred, use_container_width=True)
        
        st.markdown("### 📋 Prédictions détaillées")
        pred_df = pd.DataFrame({
            'Date': [d.strftime('%Y-%m-%d') for d in future_dates],
            'Prix prédit': [f"{p:.2f} THB" for p in predictions],
            'Variation %': [f"{(p/current_price - 1)*100:.2f}%" for p in predictions]
        })
        st.dataframe(pred_df, use_container_width=True)
        
        st.markdown("### 📊 Performance du modèle")
        residuals = y - model.predict(X)
        mse = np.mean(residuals**2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(residuals))
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("RMSE", f"{rmse:.2f} THB")
        col_m2.metric("MAE", f"{mae:.2f} THB")
        col_m3.metric("R²", f"{model.score(X, y):.3f}")
        
        st.markdown("### 📈 Analyse des tendances")
        last_price = current_price
        last_pred = predictions[-1]
        trend = "HAUSSIÈRE 📈" if last_pred > last_price else "BAISSIÈRE 📉" if last_pred < last_price else "NEUTRE ➡️"
        
        if last_pred > last_price * 1.05:
            strength = "Forte tendance haussière 🚀"
        elif last_pred > last_price:
            strength = "Légère tendance haussière 📈"
        elif last_pred < last_price * 0.95:
            strength = "Forte tendance baissière 🔻"
        elif last_pred < last_price:
            strength = "Légère tendance baissière 📉"
        else:
            strength = "Tendance latérale ⏸️"
        
        st.info(f"**Tendance prévue:** {trend} - {strength}")
        
        with st.expander("🇹🇭 Facteurs spécifiques au marché thaïlandais"):
            st.markdown("""
            **Indicateurs économiques clés:**
            
            **Tourisme:**
            - Arrivées de touristes (mensuel)
            - Revenus touristiques
            - Taux d'occupation hôtelière
            - Vols internationaux
            
            **Exportations:**
            - Électronique (disques durs, circuits)
            - Automobile et pièces détachées
            - Produits agricoles (riz, caoutchouc, fruits de mer)
            - Aliments transformés
            
            **Secteurs clés:**
            - **Énergie**: PTT, PTTEP, Bangchak, IRPC
            - **Finance**: SCB, KBANK, BBL, KTB, TISCO
            - **Tourisme**: AOT, MINT, CENTEL, ERW
            - **Commerce**: CPALL, CRC, CPN, HMPRO
            - **Technologie**: DELTA, HANA, KCE
            - **Agroalimentaire**: CPF, TU, TKN
            - **Santé**: BDMS, BH, CHG
            
            **Indicateurs techniques locaux:**
            - SET Index (ตลาดหลักทรัพย์ฯ)
            - SET50 Index (50 grandes capitalisations)
            - SET100 Index (100 grandes capitalisations)
            - MAI Index (moyennes capitalisations)
            - sSET Index (small caps)
            - SETHD Index (high dividend)
            
            **Calendrier économique thaïlandais:**
            - **Résultats trimestriels**: Février, Mai, Août, Novembre
            - **Dividendes**: Généralement semestriels/annuels
            - **Réunion banque centrale**: 8 fois par an
            - **Données touristiques**: Mensuel (25-30 du mois)
            - **Exportations**: Mensuel (21-25 du mois)
            - **Inflation**: Début du mois
            - **PIB**: Trimestriel
            
            **Jours fériés thaïlandais 2024:**
            - **1-2 janvier**: Nouvel An
            - **24 février**: Makha Bucha
            - **6 avril**: Chakri Memorial
            - **13-16 avril**: Songkran (Nouvel An thaï)
            - **1 mai**: Fête du Travail
            - **4 mai**: Fête de la couronne 
            - **22 mai**: Visakha Bucha
            - **3 juin**: Anniversaire de la Reine
            - **20 juillet**: Asalha Puja
            - **21 juillet**: Début du carême bouddhiste
            - **28 juillet**: Anniversaire du Roi
            - **12 août**: Fête des Mères
            - **13 octobre**: Memorial Day
            - **23 octobre**: Chulalongkorn Day
            - **5 décembre**: Fête des Pères
            - **10 décembre**: Constitution Day
            - **31 décembre**: Réveillon du Nouvel An
            
            **Spécificités culturelles:**
            - Respect de la famille royale
            - Influence du bouddhisme sur les pratiques commerciales
            - Importance du "face saving" dans les négociations
            - Hiérarchie et respect des aînés
            - Relation client-fournisseur à long terme
            """)
        
    else:
        st.warning(f"Pas assez de données historiques pour {symbol} (minimum 30 points)")

# ============================================================================
# SECTION 7: INDICES THAÏLANDAIS
# ============================================================================
elif menu == "🇹🇭 Indices thaïlandais":
    st.subheader("🇹🇭 Indices boursiers thaïlandais")
    
    thai_indices = {
        '^SET.BK': 'SET Index - ดัชนีตลาดหลักทรัพย์ฯ',
        '^SET50.BK': 'SET50 Index - ดัชนี SET50',
        '^SET100.BK': 'SET100 Index - ดัชนี SET100',
        '^MAI.BK': 'MAI Index - ดัชนีตลาดเอ็มเอไอ',
        '^sSET.BK': 'sSET Index - ดัชนี sSET',
        '^SETHD.BK': 'SETHD Index - ดัชนี SET High Dividend',
        '^SETCLMV.BK': 'SET CLMV Index - ดัชนี CLMV',
        '^SETESG.BK': 'SET ESG Index - ดัชนี SET ESG',
        '^SETTHSI.BK': 'SET Thailand Sustainability Investment',
        '^SETWB.BK': 'SET Wealth Index',
        '^SETCC.BK': 'SET Consumer Cyclical',
        '^SETF.BK': 'SET Financials',
        '^SETAGRI.BK': 'SET Agri & Food',
        '^SETCONS.BK': 'SET Consumer',
        '^SETENER.BK': 'SET Energy',
        '^SETINDUS.BK': 'SET Industrials',
        '^SETPROP.BK': 'SET Property & Construction',
        '^SETRES.BK': 'SET Resources',
        '^SETSERV.BK': 'SET Services',
        '^SETTECH.BK': 'SET Technology',
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 🌍 Sélection d'indice")
        selected_index = st.selectbox(
            "Choisir un indice",
            options=list(thai_indices.keys()),
            format_func=lambda x: thai_indices[x],
            index=0
        )
        
        st.markdown("### 📊 Performance des indices")
        perf_period = st.selectbox(
            "Période de comparaison",
            options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "5y"],
            index=0
        )
    
    with col1:
        try:
            if st.session_state.demo_mode:
                # Données simulées pour la démo
                index_name = thai_indices[selected_index]
                st.markdown(f"### {index_name} (Mode démo)")
                
                if 'SET50' in selected_index:
                    current_index = random.uniform(850, 950)
                elif 'SET100' in selected_index:
                    current_index = random.uniform(1800, 2000)
                elif 'MAI' in selected_index:
                    current_index = random.uniform(400, 500)
                else:
                    current_index = random.uniform(1400, 1600)
                
                prev_index = current_index * random.uniform(0.97, 1.03)
                index_change = current_index - prev_index
                index_change_pct = (index_change / prev_index * 100)
                
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Valeur", f"{current_index:,.2f}")
                col_i2.metric("Variation", f"{index_change:,.2f}")
                col_i3.metric("Variation %", f"{index_change_pct:.2f}%", delta=f"{index_change_pct:.2f}%")
                
                # Générer un graphique simulé
                dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
                values = current_index * (1 + np.random.normal(0, 0.01, 100).cumsum() / 100)
                
                fig_index = go.Figure()
                fig_index.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines',
                    name=thai_indices[selected_index],
                    line=dict(color='#00247D', width=2)
                ))
                
                fig_index.update_layout(
                    title=f"Évolution simulée - {perf_period}",
                    xaxis_title="Date",
                    yaxis_title="Points",
                    height=500,
                    hovermode='x unified',
                    template='plotly_white'
                )
                
                st.plotly_chart(fig_index, use_container_width=True)
                
            else:
                # Essayer de charger les données réelles
                index_ticker = selected_index
                
                ticker = yf.Ticker(index_ticker)
                index_hist = ticker.history(period=perf_period)
                
                if not index_hist.empty:
                    if index_hist.index.tz is None:
                        index_hist.index = index_hist.index.tz_localize('UTC').tz_convert(THAILAND_TZ)
                    else:
                        index_hist.index = index_hist.index.tz_convert(THAILAND_TZ)
                    
                    current_index = index_hist['Close'].iloc[-1]
                    prev_index = index_hist['Close'].iloc[-2] if len(index_hist) > 1 else current_index
                    index_change = current_index - prev_index
                    index_change_pct = (index_change / prev_index * 100) if prev_index != 0 else 0
                    
                    st.markdown(f"### {thai_indices[selected_index]}")
                    
                    col_i1, col_i2, col_i3 = st.columns(3)
                    col_i1.metric("Valeur", f"{current_index:,.2f}")
                    col_i2.metric("Variation", f"{index_change:,.2f}")
                    col_i3.metric("Variation %", f"{index_change_pct:.2f}%", delta=f"{index_change_pct:.2f}%")
                    
                    st.caption(f"Dernière mise à jour: {index_hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')} (heure Thaïlande)")
                    
                    fig_index = go.Figure()
                    fig_index.add_trace(go.Scatter(
                        x=index_hist.index,
                        y=index_hist['Close'],
                        mode='lines',
                        name=thai_indices[selected_index],
                        line=dict(color='#00247D', width=2)
                    ))
                    
                    if len(index_hist) > 20:
                        ma_20 = index_hist['Close'].rolling(window=20).mean()
                        ma_50 = index_hist['Close'].rolling(window=50).mean()
                        
                        fig_index.add_trace(go.Scatter(
                            x=index_hist.index,
                            y=ma_20,
                            mode='lines',
                            name='MA 20',
                            line=dict(color='orange', width=1, dash='dash')
                        ))
                        
                        fig_index.add_trace(go.Scatter(
                            x=index_hist.index,
                            y=ma_50,
                            mode='lines',
                            name='MA 50',
                            line=dict(color='purple', width=1, dash='dash')
                        ))
                    
                    fig_index.update_layout(
                        title=f"Évolution - {perf_period}",
                        xaxis_title="Date",
                        yaxis_title="Points",
                        height=500,
                        hovermode='x unified',
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig_index, use_container_width=True)
                    
                    st.markdown("### 📈 Statistiques")
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    col_s1.metric("Plus haut", f"{index_hist['High'].max():,.2f}")
                    col_s2.metric("Plus bas", f"{index_hist['Low'].min():,.2f}")
                    col_s3.metric("Moyenne", f"{index_hist['Close'].mean():,.2f}")
                    col_s4.metric("Volatilité", f"{index_hist['Close'].pct_change().std()*100:.2f}%")
                else:
                    st.warning("Données non disponibles - Utilisation du mode démo")
                    st.session_state.demo_mode = True
        except Exception as e:
            st.error(f"Erreur lors du chargement: {e}")
            st.info("Utilisation du mode démonstration")
    
    # Tableau de comparaison des indices
    st.markdown("### 📊 Comparaison des principaux indices")
    
    comparison_data = []
    for idx, name in list(thai_indices.items())[:10]:  # Limiter à 10 pour la clarté
        try:
            if st.session_state.demo_mode:
                if 'SET50' in idx:
                    current = random.uniform(850, 950)
                elif 'SET100' in idx:
                    current = random.uniform(1800, 2000)
                elif 'MAI' in idx:
                    current = random.uniform(400, 500)
                else:
                    current = random.uniform(1400, 1600)
                    
                prev = current * random.uniform(0.98, 1.02)
                change_pct = ((current - prev) / prev * 100)
                
                comparison_data.append({
                    'Indice': name.split(' - ')[0],
                    'Valeur': f"{current:,.0f}",
                    'Variation 5j': f"{change_pct:.2f}%",
                    'Direction': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
                })
            else:
                # Essayer de charger les données réelles
                ticker = yf.Ticker(idx)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[0]
                    change_pct = ((current - prev) / prev * 100) if prev != 0 else 0
                    
                    comparison_data.append({
                        'Indice': name.split(' - ')[0],
                        'Valeur': f"{current:,.0f}",
                        'Variation 5j': f"{change_pct:.2f}%",
                        'Direction': '📈' if change_pct > 0 else '📉' if change_pct < 0 else '➡️'
                    })
        except:
            pass
    
    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True)
    
    with st.expander("ℹ️ À propos des indices thaïlandais"):
        st.markdown("""
        ### Principaux indices du SET
        
        **📊 SET Index:**
        - Indice principal de la bourse de Thaïlande
        - Créé en 1975
        - Environ 600 sociétés cotées
        - Capitalisation totale: ~18 000 milliards THB (~500 milliards USD)
        - Base 100 au 30 avril 1975
        
        **📈 SET50 Index:**
        - 50 plus grandes capitalisations
        - Révisé semestriellement (janvier et juillet)
        - Poids basé sur la capitalisation flottante
        - Environ 70% de la capitalisation totale
        
        **📊 SET100 Index:**
        - 100 plus grandes capitalisations
        - Environ 85% de la capitalisation totale
        - Base 1000 au 16 août 2005
        
        **📈 MAI Index:**
        - Market for Alternative Investment
        - Créé en 2001 pour les PME
        - Environ 150 sociétés
        - Capitalisation: ~500 milliards THB
        
        **📊 sSET Index:**
        - Small cap index (101-200e capitalisations)
        - Créé en 2018
        - Environ 100 sociétés
        
        **📈 SETHD Index:**
        - High dividend yield stocks
        - 30 actions avec les meilleurs dividendes
        - Révisé semestriellement
        
        **Secteurs:**
        - **AGRI**: Agroalimentaire
        - **CONS**: Consommation
        - **ENER**: Énergie
        - **FINA**: Finance
        - **INDUS**: Industrie
        - **PROP**: Immobilier
        - **RES**: Ressources
        - **SERV**: Services
        - **TECH**: Technologie
        
        **Pondération sectorielle approximative:**
        - Énergie: 25%
        - Finance: 20%
        - Technologie: 15%
        - Commerce: 10%
        - Santé: 8%
        - Immobilier: 7%
        - Transport: 5%
        - Autres: 10%
        """)

# ============================================================================
# WATCHLIST
# ============================================================================
st.markdown("---")
col_w1, col_w2 = st.columns([3, 1])

with col_w1:
    st.subheader("📋 Watchlist SET Thailand")
    
    # Trier les actions par catégorie
    set50_stocks = ['PTT.BK', 'PTTEP.BK', 'SCB.BK', 'KBANK.BK', 'BBL.BK', 'ADVANC.BK', 
                    'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'GULF.BK', 'BDMS.BK', 'BH.BK']
    
    set100_stocks = ['CPF.BK', 'TRUE.BK', 'MINT.BK', 'SCC.BK', 'TOP.BK', 'OR.BK', 
                     'CRC.BK', 'CPN.BK', 'HMPRO.BK', 'BTS.BK', 'BEM.BK', 'TIDLOR.BK']
    
    mai_stocks = ['BEAUTY.BK', 'SAPPE.BK', 'TKN.BK', 'PLANB.BK', 'WORK.BK', 'MAJOR.BK']
    
    tabs = st.tabs(["🇹🇭 SET50 (Large Caps)", "🇹🇭 SET100 (Mid Caps)", "🇹🇭 MAI (Small Caps)"])
    
    with tabs[0]:  # SET50
        cols_per_row = 3
        for i in range(0, len(set50_stocks), cols_per_row):
            cols = st.columns(min(cols_per_row, len(set50_stocks) - i))
            for j, sym in enumerate(set50_stocks[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        if st.session_state.demo_mode and sym in DEMO_DATA:
                            price = DEMO_DATA[sym]['current_price']
                            prev_close = DEMO_DATA[sym]['previous_close']
                            change = ((price - prev_close) / prev_close * 100)
                            st.metric(sym, f"{price:.2f} THB", delta=f"{change:.1f}%")
                        else:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                change = ((price - prev_close) / prev_close * 100)
                                st.metric(sym, f"{price:.2f} THB", delta=f"{change:.1f}%")
                            else:
                                st.metric(sym, "N/A")
                    except:
                        price = random.uniform(20, 500)
                        st.metric(sym, f"{price:.2f} THB*", delta=f"{random.uniform(-2, 2):.1f}%")
    
    with tabs[1]:  # SET100
        cols_per_row = 3
        for i in range(0, len(set100_stocks), cols_per_row):
            cols = st.columns(min(cols_per_row, len(set100_stocks) - i))
            for j, sym in enumerate(set100_stocks[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        if st.session_state.demo_mode and sym in DEMO_DATA:
                            price = DEMO_DATA[sym]['current_price']
                            prev_close = DEMO_DATA[sym]['previous_close']
                            change = ((price - prev_close) / prev_close * 100)
                            st.metric(sym, f"{price:.2f} THB", delta=f"{change:.1f}%")
                        else:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                change = ((price - prev_close) / prev_close * 100)
                                st.metric(sym, f"{price:.2f} THB", delta=f"{change:.1f}%")
                            else:
                                st.metric(sym, "N/A")
                    except:
                        price = random.uniform(5, 200)
                        st.metric(sym, f"{price:.2f} THB*", delta=f"{random.uniform(-3, 3):.1f}%")
    
    with tabs[2]:  # MAI
        cols_per_row = 3
        for i in range(0, len(mai_stocks), cols_per_row):
            cols = st.columns(min(cols_per_row, len(mai_stocks) - i))
            for j, sym in enumerate(mai_stocks[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        if st.session_state.demo_mode:
                            price = random.uniform(5, 50)
                            st.metric(sym, f"{price:.2f} THB", delta=f"{random.uniform(-5, 5):.1f}%")
                        else:
                            ticker = yf.Ticker(sym)
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                price = hist['Close'].iloc[-1]
                                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                                change = ((price - prev_close) / prev_close * 100)
                                st.metric(sym, f"{price:.2f} THB", delta=f"{change:.1f}%")
                            else:
                                st.metric(sym, "N/A")
                    except:
                        price = random.uniform(2, 30)
                        st.metric(sym, f"{price:.2f} THB*", delta=f"{random.uniform(-6, 6):.1f}%")

with col_w2:
    # Heures actuelles
    thai_time = datetime.now(THAILAND_TZ)
    user_time = datetime.now(user_tz)
    
    st.markdown("### 🕐 Heures actuelles")
    st.caption(f"🇹🇭 Thaïlande: {thai_time.strftime('%H:%M:%S')}")
    st.caption(f"🌍 Votre heure: {user_time.strftime('%H:%M:%S')}")
    st.caption(f"📊 Fuseau: {selected_tz_key}")
    
    st.markdown("### 📊 Statut du marché")
    status, icon = get_market_status()
    st.caption(f"{icon} SET: {status}")
    
    # Prochaines sessions
    if status == "Fermé (pré-ouverture)":
        next_open = thai_time.replace(hour=10, minute=0, second=0)
        time_to_open = next_open - thai_time
        hours = time_to_open.seconds // 3600
        minutes = (time_to_open.seconds % 3600) // 60
        st.caption(f"⏳ Ouverture dans: {hours}h{minutes:02d}")
    elif status == "Pause midi":
        next_open = thai_time.replace(hour=14, minute=0, second=0)
        time_to_open = next_open - thai_time
        hours = time_to_open.seconds // 3600
        minutes = (time_to_open.seconds % 3600) // 60
        st.caption(f"⏳ Reprise dans: {hours}h{minutes:02d}")
    elif status == "Ouvert":
        if thai_time.hour < 12:
            close_time = thai_time.replace(hour=12, minute=30, second=0)
        else:
            close_time = thai_time.replace(hour=16, minute=30, second=0)
        time_to_close = close_time - thai_time
        minutes = time_to_close.seconds // 60
        st.caption(f"⏳ Fermeture dans: {minutes} min")
    
    if st.session_state.demo_mode:
        st.caption("🎮 Mode démonstration")
    else:
        st.caption(f"Dernière MAJ: {thai_time.strftime('%H:%M:%S')}")
    
    if auto_refresh and hist is not None and not hist.empty:
        time.sleep(refresh_rate)
        st.rerun()

# Note sur Songkran
current_date = datetime.now()
songkran_start = datetime(current_date.year, 4, 13)
songkran_end = datetime(current_date.year, 4, 15)

if songkran_start <= current_date <= songkran_end:
    st.markdown("""
    <div style='background-color: #fef3c7; border-left: 4px solid #d97706; padding: 1rem; margin: 1rem 0; border-radius: 0.5rem;'>
        <b>💦 สวัสดีปีใหม่ไทย - Happy Songkran!</b> - Fête du Nouvel An thaïlandais.
        Les marchés sont fermés du 13 au 15 avril. Reprise le 16 avril.
        ขอให้มีความสุขมากๆ สุขสันต์วันสงกรานต์!
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.8rem;'>"
    "🇹🇭 Tracker Bourse Thaïlande - SET Bangkok | "
    "📊 Données en temps réel du Stock Exchange of Thailand<br>"
    "📅 Horaires: 10h00-12h30 et 14h00-16h30 (heure Thaïlande UTC+7) | Fermé samedi-dimanche et jours fériés<br>"
    "⚠️ Données avec délai possible | 💱 Devise: Baht thaïlandais (THB) | 🕐 Support multi-fuseaux horaires (UTC+4 disponible)"
    "</p>",
    unsafe_allow_html=True
)

# Pied de page avec les informations sur les jours fériés
with st.expander("📅 Calendrier des jours fériés thaïlandais 2024"):
    st.markdown("""
    | Date | Événement (Thai) | Événement (Français) |
    |------|------------------|----------------------|
    | 1-2 janvier | วันขึ้นปีใหม่ | Nouvel An |
    | 24 février | วันมาฆบูชา | Makha Bucha |
    | 6 avril | วันจักรี | Chakri Memorial |
    | 13-16 avril | วันสงกรานต์ | Songkran (Nouvel An thaï) |
    | 1 mai | วันแรงงานแห่งชาติ | Fête du Travail |
    | 4 mai | วันฉัตรมงคล | Coronation Day |
    | 22 mai | วันวิสาขบูชา | Visakha Bucha |
    | 3 juin | วันเฉลิมพระชนมพรรษาสมเด็จพระนางเจ้าฯ | Anniversaire de la Reine |
    | 20 juillet | วันอาสาฬหบูชา | Asalha Puja |
    | 21 juillet | วันเข้าพรรษา | Début du carême bouddhiste |
    | 28 juillet | วันเฉลิมพระชนมพรรษาพระบาทสมเด็จพระเจ้าอยู่หัว | Anniversaire du Roi |
    | 12 août | วันแม่แห่งชาติ | Fête des Mères |
    | 13 octobre | วันคล้ายวันสวรรคตพระบาทสมเด็จพระบรมชนกาธิเบศร มหาภูมิพลอดุลยเดชมหาราช บรมนาถบพิตร | King Bhumibol Memorial |
    | 23 octobre | วันปิยมหาราช | Chulalongkorn Day |
    | 5 décembre | วันพ่อแห่งชาติ | Fête des Pères |
    | 10 décembre | วันรัฐธรรมนูญ | Constitution Day |
    | 31 décembre | วันสิ้นปี | Réveillon du Nouvel An |
    
    *Note: Les dates des fêtes bouddhistes sont basées sur le calendrier lunaire et peuvent varier légèrement.*
    """)

# Message en thaï
thai_time = datetime.now(THAILAND_TZ)
thai_hour = thai_time.hour

if thai_hour < 12:
    greeting = "สวัสดีตอนเช้า"  # Bonjour (matin)
elif thai_hour < 17:
    greeting = "สวัสดีตอนบ่าย"  # Bonjour (après-midi)
else:
    greeting = "สวัสดีตอนเย็น"  # Bonsoir

st.markdown(f"""
<div style='text-align: center; font-family: Sarabun; font-size: 1.2rem; margin-top: 1rem;'>
    <p>{greeting} - ยินดีต้อนรับสู่ตลาดหลักทรัพย์แห่งประเทศไทย</p>
    <p>ติดตามหุ้นไทยแบบเรียลไทม์ | Invest wisely in Thai stocks</p>
</div>
""", unsafe_allow_html=True)

# Information sur les fuseaux horaires supportés
with st.sidebar.expander("🕐 Fuseaux horaires supportés", expanded=False):
    st.markdown("""
    **Fuseaux disponibles:**
    - UTC+4 (Dubai/Moscou)
    - UTC+3 (Riyadh/Istanbul)
    - UTC+2 (Jérusalem/Le Caire)
    - UTC+1 (Paris/Berlin)
    - UTC (Londres)
    - UTC-5 (New York)
    - UTC-8 (Los Angeles)
    - UTC+5:30 (Inde)
    - UTC+7 (Thaïlande - marché)
    - UTC+8 (Singapour/Chine)
    - UTC+9 (Tokyo/Corée)
    - UTC+10 (Sydney)
    
    **Thaïlande:** UTC+7 (pas d'heure d'été)
    """)

# Statistiques rapides
if hist is not None and not hist.empty:
    with st.sidebar.expander("📊 Stats rapides", expanded=False):
        st.markdown(f"**{symbol}**")
        st.markdown(f"Prix: {format_thai_currency(current_price, symbol)}")
        
        if len(hist) > 1:
            returns = hist['Close'].pct_change().dropna()
            st.markdown(f"Volatilité 30j: {returns.tail(30).std()*100:.2f}%")
            st.markdown(f"Performance 30j: {(current_price/hist['Close'].iloc[-30]-1)*100:.2f}%" if len(hist) >= 30 else "N/A")
        
        if info:
            pe = info.get('trailingPE', 'N/A')
            if pe != 'N/A':
                st.markdown(f"P/E: {pe:.2f}")
            
            dy = info.get('dividendYield', 0)
            if dy:
                st.markdown(f"Dividende: {dy*100:.2f}%")

# Gestion des erreurs de connexion
if not st.session_state.demo_mode:
    try:
        test_ticker = yf.Ticker("PTT.BK")
        test_hist = test_ticker.history(period='1d')
        if test_hist.empty:
            st.warning("⚠️ Problème de connexion à l'API Yahoo Finance. Activation du mode démo.")
            st.session_state.demo_mode = True
            time.sleep(2)
            st.rerun()
    except:
        st.warning("⚠️ Problème de connexion à l'API Yahoo Finance. Activation du mode démo.")
        st.session_state.demo_mode = True
        time.sleep(2)
        st.rerun()
