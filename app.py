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

# === AUTO REFRESH ogni 5 minuti ===
st_autorefresh(interval=300000, key="aggiorna")

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

def salva_cache(data):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        st.success(f"📦 Cache salvata con {len(data)} telecamere.")
    except Exception as e:
        st.error(f"Errore salvataggio cache: {e}")

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning("⚠️ Cache corrotta. Verrà rigenerata.")
            os.remove(CACHE_FILE)
            return {}
    return {}

def carica_dati_da_ftp():
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
        ftp.quit()
    except Exception as e:
        st.error(f"Errore FTP: {e}")
    return camere_ultime_foto

# === UI ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📸 Dashboard - Ultime Immagini per Telecamera")
st.caption(f"🕒 Orario di riferimento (Brasilia): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === CACHE HANDLING ===
camere_ultime_foto = carica_cache()

if not camere_ultime_foto:
    st.info("🔄 Caricamento da FTP...")
    camere_ultime_foto = carica_dati_da_ftp()
    if camere_ultime_foto:
        salva_cache(camere_ultime_foto)

if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata.")
    st.stop()

# === VISUALIZZAZIONE ===
for cam, data in sorted(camere_ultime_foto.items()):
    try:
        ts = datetime.fromisoformat(data["timestamp"])
        brasil_tz = pytz.timezone('America/Sao_Paulo')
        now_brasil = datetime.now(brasil_tz)

        if ts.tzinfo is None:
            ts = brasil_tz.localize(ts)

        ore = int((now_brasil - ts).total_seconds() // 3600)
        stato = "🟢" if ore < 24 else "🔴"

        st.markdown(f"### {stato} {cam}")
        st.write(f"Ultima attività: `{ts.strftime('%Y-%m-%d %H:%M:%S')}` ({ore}h fa)")

        # Scarica e mostra immagine
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(data["path"])
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
        buffer.seek(0)
        image = Image.open(buffer)
        st.image(image, use_container_width=True)
        ftp.quit()

        st.markdown("---")

    except Exception as e:
        st.warning(f"Errore caricando immagine da FTP per {cam}: {e}")
        continue

