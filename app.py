
import streamlit as st
from datetime import datetime
import pytz
import json
from PIL import Image
import io
from ftplib import FTP
import os

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
CACHE_FILE = "cache_ultime_foto.json"

# === UI SETUP ===
st.set_page_config(page_title="Dashboard - Ultime Immagini", layout="wide")
st.title("📸 Dashboard - Ultime Immagini per Telecamera")
now_brasil = datetime.now(pytz.timezone("America/Sao_Paulo"))
st.caption(f"🕒 Orario di riferimento (Brasilia): {now_brasil.strftime('%Y-%m-%d %H:%M:%S')}")

# === CARICA DATI ===
if not os.path.exists(CACHE_FILE):
    st.error("❌ File cache non trovato.")
    st.stop()

with open(CACHE_FILE, "r") as f:
    camere_ultime_foto = json.load(f)

if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata nella cache.")
    st.stop()

# === MOSTRA IMMAGINI ===
for cam, data in sorted(camere_ultime_foto.items()):
    try:
        ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
        ts = pytz.timezone("America/Sao_Paulo").localize(ts)
        ore = (now_brasil - ts).total_seconds() // 3600
        stato = "🟢" if ore < 24 else "🔴"

        st.markdown(f"### {stato} {cam}")
        st.write(f"Ultima attività: `{data['timestamp']}` ({int(ore)}h fa)")

        try:
            ftp = FTP(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(data["path"])

            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
            buffer.seek(0)
            image = Image.open(buffer)
            st.image(image, use_container_width=True)
            ftp.quit()
        except Exception as e:
            st.warning(f"Errore caricando immagine da FTP per {cam}: {e}")

        st.markdown("---")
    except Exception as e:
        st.warning(f"Errore nei dati per {cam}: {e}")
