import streamlit as st
from ftplib import FTP
from datetime import datetime, timedelta
import pytz
from PIL import Image
import io
import re
import json
import os
from streamlit_autorefresh import st_autorefresh

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
STORICO_FILE = "storico_immagini.json"
TTL_CACHE = 300  # 5 minuti

# === AUTO REFRESH ===
st_autorefresh(interval=TTL_CACHE * 1000, key="aggiorna")

# === PAGINA ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📈 Dashboard Amministratore")
st.caption(f"🕒 Orario di riferimento (Brasilia): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === UTILS ===
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

# === CACHE FTP ===
@st.cache_data(ttl=TTL_CACHE)
def carica_ultime_foto():
    camere_ultime_foto = {}

    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(ROOT_FOLDER)
        camere = ftp.nlst()

        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            nome_cam_trovato = None

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
                                ftp.cwd(path_img)
                                files = sorted([f for f in ftp.nlst() if f.endswith(".jpg")], reverse=True)
                                if not files:
                                    continue
                                ultima_img = files[0]
                                nome_cam, timestamp = parse_nome_camera_e_data(ultima_img)
                                if nome_cam and timestamp:
                                    camere_ultime_foto[nome_cam] = {
                                        "timestamp": timestamp,
                                        "path": path_img,
                                        "filename": ultima_img
                                    }
                                    nome_cam_trovato = nome_cam
                                    break
                            except:
                                continue
                        if nome_cam_trovato:
                            break
                    if nome_cam_trovato:
                        break
            except:
                continue
        ftp.quit()
    except Exception as e:
        st.error(f"Errore FTP: {e}")
    return camere_ultime_foto

# === STORICO ===
def aggiorna_storico(camere_ultime_foto):
    oggi = datetime.now().strftime("%Y-%m-%d")
    storico = {}
    if os.path.exists(STORICO_FILE):
        with open(STORICO_FILE, "r") as f:
            storico = json.load(f)
    for cam, data in camere_ultime_foto.items():
        storico.setdefault(cam, {})
        storico[cam].setdefault(oggi, 0)
        storico[cam][oggi] += 1
    with open(STORICO_FILE, "w") as f:
        json.dump(storico, f, indent=2)

# === MAIN ===
camere_ultime_foto = carica_ultime_foto()
if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata.")
    st.stop()

aggiorna_storico(camere_ultime_foto)

# === STATISTICHE ===
count_attive = 0
count_offline = 0
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)

for data in camere_ultime_foto.values():
    ts = data["timestamp"]
    if ts.tzinfo is None:
        ts = brasil_tz.localize(ts)
    ore = (now_brasil - ts).total_seconds() // 3600
    if ore < 24:
        count_attive += 1
    else:
        count_offline += 1

st.subheader(f"Totale camere: {len(camere_ultime_foto)} | ✅ Attive: {count_attive} | 🔴 Offline: {count_offline}")

# === BOTTONI ===
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Forza aggiornamento"):
        st.cache_data.clear()
        st.experimental_rerun()

with col2:
    nome_sel = st.selectbox("📷 Scegli una telecamera per vedere storico:", ["--"] + sorted(camere_ultime_foto.keys()))

# === GRAFICO STORICO PER CAMERA ===
if nome_sel and nome_sel != "--":
    if os.path.exists(STORICO_FILE):
        with open(STORICO_FILE, "r") as f:
            storico = json.load(f)
        dati_cam = storico.get(nome_sel, {})
        if dati_cam:
            st.bar_chart(dati_cam)
        else:
            st.info("Nessun dato storico per questa camera.")


