import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io
import re

# --- CONFIG ---
FTP_HOST = "66.220.9.45"
FTP_USER = "otl.2020"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"  # <- root reale

# --- Estrai nome camera e timestamp da filename ---
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

# --- AVVIO APP ---
st.title("📡 Dashboard - Ultime immagini da tutte le camere")
try:
    st.info("🔌 Connessione al server FTP...")
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore connessione FTP: {e}")
    st.stop()

# --- Scorri tutte le camere nella root ---
camere_ultime_foto = {}

try:
    ftp.cwd(ROOT_FOLDER)
    camere = ftp.nlst()  # es: ['REO_32', 'REO_323', ...]

    for cam in sorted(camere):
        cam_path = f"/{cam}"
        try:
            ftp.cwd(cam_path)
            anni = ftp.nlst()
            for anno in sorted(anni, reverse=True):
                ftp.cwd(f"{cam_path}/{anno}")
                mesi = ftp.nlst()
                for mese in sorted(mesi, reverse=True):
                    ftp.cwd(f"{cam_path}/{anno}/{mese}")
                    giorni = ftp.nlst()
                    for giorno in sorted(giorni, reverse=True):
                        path_img = f"{cam_path}/{anno}/{mese}/{giorno}"
                        try:
                            ftp.cwd(path_img)
                            files = ftp.nlst()
                            for nome_file in files:
                                if not nome_file.endswith(".jpg"):
                                    continue
                                nome_cam, timestamp = parse_nome_camera_e_data(nome_file)
                                if nome_cam and timestamp:
                                    if (nome_cam not in camere_ultime_foto) or (timestamp > camere_ultime_foto[nome_cam]["timestamp"]):
                                        camere_ultime_foto[nome_cam] = {
                                            "timestamp": timestamp,
                                            "path": path_img,
                                            "filename": nome_file
                                        }
                        except:
                            continue
        except:
            continue

except Exception as e:
    st.error(f"❌ Errore nella lettura delle camere: {e}")

# --- MOSTRA ULTIMA IMMAGINE PER CAMERA ---
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
                    st.image(image, caption=data['filename'], width=200)
                with col2:
                    st.markdown(f"### {stato} {cam}")
                    st.write(f"📅 Ultima immagine: `{ts.strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"⏱️ Tempo trascorso: `{int(diff_ore)} ore`")
            st.markdown("---")
        except Exception as e:
            st.error(f"❌ Errore caricando immagine `{cam}`: {e}")

ftp.quit()

