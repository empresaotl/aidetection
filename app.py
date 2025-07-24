import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io
import re
from streamlit_autorefresh import st_autorefresh

# --- AUTOREFRESH OGNI 5 MINUTI (300.000 ms) ---
st_autorefresh(interval=300000, key="aggiornamento_automatico")

# --- CONFIG FTP ---
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"

# --- Parsing nome file ---
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

# --- Titolo ---
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("📡 Dashboard - Ultime immagini inviate (Auto Refresh ogni 5 minuti)")

# --- Connessione FTP ---
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore FTP: {e}")
    st.stop()

# --- Cerca ultima immagine per ogni camera ---
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
                            break  # fermati al primo file trovato
                        except:
                            continue
                    if nome_cam in camere_ultime_foto:
                        break
                if nome_cam in camere_ultime_foto:
                    break
        except:
            continue
except Exception as e:
    st.error(f"❌ Errore lettura camere: {e}")

# --- MOSTRA RISULTATI ---
if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata.")
else:
    for cam, data in sorted(camere_ultime_foto.items()):
        ts = data["timestamp"]
        diff_ore = (datetime.now() - ts).total_seconds() // 3600
        stato = "🟢" if diff_ore < 24 else "🔴"

        buffer = io.BytesIO()
        try:
            ftp.cwd(data["path"])
            ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
            buffer.seek(0)
            image = Image.open(buffer)

            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image, caption=data["filename"], width=200)
                with col2:
                    st.markdown(f"### {stato} {cam}")
                    st.write(f"🕒 Ultima attività: `{ts.strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"⏱️ Tempo trascorso: `{int(diff_ore)} ore`")
            st.markdown("---")

        except Exception as e:
            st.warning(f"⚠️ Errore caricando immagine '{cam}': {e}")
            continue

# --- Chiusura FTP ---
try:
    ftp.quit()
except Exception as e:
    st.warning(f"⚠️ FTP chiuso con errore: {e}")
