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
CACHE_FILE = "cache_ultime_foto.json"

# === FUNZIONI CACHE ===
def salva_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def carica_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

# === PARSER nome camera e timestamp ===
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

# === UI setup ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("Dashboard - Ultima immagine per telecamera")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.caption(f"Orario di riferimento (Brasilia): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === AUTO REFRESH ===
st_autorefresh(interval=300000, key="aggiornamento")

# === CONNESSIONE FTP ===
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("Connessione FTP riuscita")
except Exception as e:
    st.error(f"Errore FTP: {e}")
    st.stop()

# === RACCOLTA ultime immagini
camere_ultime_foto = {}

try:
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
                                    "timestamp": timestamp.isoformat(),
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

except Exception as e:
    st.error(f"Errore lettura camere: {e}")

# === SALVATAGGIO CACHE ===
if camere_ultime_foto:
    salva_cache(camere_ultime_foto)
    print("✅ Cache salvata con", len(camere_ultime_foto), "telecamere.")
else:
    st.warning("⚠️ Nessuna immagine trovata.")
    st.stop()

# === STATISTICHE E FILTRI ===
count_attive = 0
count_offline = 0
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)

for cam, data in camere_ultime_foto.items():
    ts = datetime.fromisoformat(data["timestamp"])
    if ts.tzinfo is None:
        ts = brasil_tz.localize(ts)
    ore = (now_brasil - ts).total_seconds() // 3600
    if ore < 24:
        count_attive += 1
    else:
        count_offline += 1

st.subheader(f"Totale camere: {len(camere_ultime_foto)} | Attive: {count_attive} | Offline: {count_offline}")

# --- CHIUSURA FTP ---
try:
    ftp.quit()
except:
    pass

