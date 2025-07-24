import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io
import re
from streamlit_autorefresh import st_autorefresh

# --- AUTOREFRESH OGNI 5 MINUTI ---
st_autorefresh(interval=300000, key="aggiornamento")

# --- CONFIG FTP ---
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"

# --- Parsing nome e data ---
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

# --- UI ---
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("📡 Dashboard - Ultima immagine per telecamera")

# --- Connessione FTP ---
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore FTP: {e}")
    st.stop()

# --- Scansione camere nella root ---
camere_ultime_foto = {}

try:
    ftp.cwd(ROOT_FOLDER)
    camere = ftp.nlst()

    for cam_folder in sorted(camere):
        cam_path = f"/{cam_folder}"
        try:
            ftp.cwd(cam_path)
            anni = sorted(ftp.nlst(), reverse=True)
            for anno in anni:
                ftp.cwd(f"{cam_path}/{anno}")
                mesi = sorted(ftp.nlst(), reverse=True)
                for mese in mesi:
                    ftp.cwd(f"{cam_path}/{anno}/{mese}")
                    giorni = sorted(ftp.nlst(), reverse=True)
                    for giorno in giorni:
                        path_img = f"{cam_path}/{anno}/{mese}/{giorno}"
                        try:
ftp.cwd(f"{cam_path}/{anno}/{mese}/{giorno}")
