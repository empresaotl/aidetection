import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io
import re
from streamlit_autorefresh import st_autorefresh

# 🔄 AUTO REFRESH ogni 5 minuti
st_autorefresh(interval=300000, key="aggiornamento")

# --- CONFIG FTP ---
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"

# --- PARSER nome camera e timestamp ---
def parse_nome_camera_e_data(nome_file):
    try:
        match = re.match(r"(.+?)_00_(\d{14})\.jpg", nome_file)
        if match:
            nome_camera = match.group(1).strip()
            timestamp_str = match.group(2)
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            return nome_camera, timestamp
    except:
        return None, None
    return None, None

# --- UI setup ---
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("📡 Dashboard - Ultima immag
