import streamlit as st
from ftplib import FTP
from datetime import datetime, timedelta
from PIL import Image
import io

# --- CONFIGURAZIONE FTP ---
FTP_HOST = "ftp.drivehq.com"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
CAMERA_FOLDER = "/REO_325"  # cartella root

# --- Connessione al server FTP ---
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore FTP: {e}")
    st.stop()

# --- Lettura immagini ---
st.title("🔧 Pannello Amministratore - Stato Telecamere")

try:
    ftp.cwd(CAMERA_FOLDER)
    mesi = ftp.nlst()  # cartelle tipo 'Luglio', 'Agosto', ecc.

    for mese in mesi:
        try:
            ftp.cwd(f"{CAMERA_FOLDER}/{mese}")
            giorni = ftp.nlst()

            for giorno in giorni:
                path_img = f"{CAMERA_FOLDER}/{mese}/{giorno}"
                ftp.cwd(path_img)

                files = ftp.nlst()
                immagini = sorted([f for f in files if f.endswith(".jpg")], reverse=True)

                if not immagini:
                    continue

                ultima_img = immagini[0]
                timestamp_str = ultima_img.replace(".jpg", "")

                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                except:
                    st.warning(f"📛 Nome file non valido: {ultima_img}")
                    continue

                ore_passate = (datetime.now() - timestamp).total_seconds() // 3600
                stato = "🟢" if ore_passate < 24 else "🔴"

                buffer = io.BytesIO()
                ftp.retrbinary(f"RETR {ultima_img}", buffer.write)
                buffer.seek(0)
                image = Image.open(buffer)

                st.markdown(f"### {stato} {giorno}/{mese} - Ultima immagine: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}` ({int(ore_passate)}h fa)")
                st.image(image, width=400)
                st.markdown("---")

        except Exception as e:
