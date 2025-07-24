
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

# === FUNZIONE: Carica cache locale ===
def carica_cache_locale():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

# === FUNZIONE: Forza aggiornamento da FTP ===
def aggiorna_cache_da_ftp():
    dati = {}
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        camere = ftp.nlst()
        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            try:
                ftp.cwd(cam_path)
                anni = sorted(ftp.nlst(), reverse=True)[:1]
                for anno in anni:
                    ftp.cwd(f"{cam_path}/{anno}")
                    mesi = sorted(ftp.nlst(), reverse=True)[:1]
                    for mese in mesi:
                        ftp.cwd(f"{cam_path}/{anno}/{mese}")
                        giorni = sorted(ftp.nlst(), reverse=True)[:1]
                        for giorno in giorni:
                            path_img = f"{cam_path}/{anno}/{mese}/{giorno}"
                            try:
                                ftp.cwd(path_img)
                                files = sorted([f for f in ftp.nlst() if f.endswith(".jpg")], reverse=True)
                                if not files:
                                    continue
                                ultima_img = files[0]
                                nome_camera = ultima_img.split("_00_")[0].strip()
                                timestamp_str = ultima_img.split("_00_")[-1].replace(".jpg", "")
                                timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                                dati[nome_camera] = {
                                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                    "path": path_img,
                                    "filename": ultima_img
                                }
                                break
                            except:
                                continue
                        break
                    break
            except:
                continue
        ftp.quit()
    except Exception as e:
        st.error(f"Errore FTP: {e}")
        return {}

    with open(CACHE_FILE, "w") as f:
        json.dump(dati, f, indent=2)
    return dati

# === UI ===
st.set_page_config(page_title="Dashboard - Cache Locale", layout="wide")
st.title("🗂️ Dashboard Cache Locale (Ultime Immagini)")
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)
st.caption(f"🕒 Orario di riferimento (Brasilia): {now_brasil.strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("🔄 Forza aggiornamento da FTP"):
    cache = aggiorna_cache_da_ftp()
    st.success("Cache aggiornata.")
else:
    cache = carica_cache_locale()

if not cache:
    st.warning("⚠️ Nessuna immagine trovata.")
else:
    for cam, data in sorted(cache.items()):
        try:
            ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
            ore = (now_brasil - ts).total_seconds() // 3600
            stato = "🟢" if ore < 24 else "🔴"
            st.markdown(f"### {stato} {cam}")
            st.write(f"Ultima attività: `{data['timestamp']}` ({int(ore)}h fa)")

            # Prova a caricare l'immagine da FTP
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
                st.error(f"Errore caricando immagine da FTP: {e}")

            st.markdown("---")
        except Exception as e:
            st.warning(f"Errore dati per {cam}: {e}")

