import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io

# --- CONFIGURAZIONE FTP ---
FTP_HOST = "ftp.drivehq.com"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
BASE_FOLDER = "/REO_325"
ANNO = "2025"
MESE = "07"

# --- Avvio ---
st.title("🔧 Pannello Amministratore - Stato Telecamere")
st.info("📡 Connessione al server FTP...")

try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore nella connessione FTP: {e}")
    st.stop()

# --- Vai nella cartella base ---
try:
    ftp.cwd(BASE_FOLDER)
    camere = ftp.nlst()  # ['REO_Cam001', 'REO_Cam002', ...]

    for cam in camere:
        path_img = f"{BASE_FOLDER}/{cam}/{ANNO}/{MESE}"

        try:
            ftp.cwd(path_img)
            files = ftp.nlst()
            immagini = sorted([f for f in files if f.endswith(".jpg")], reverse=True)

            if not immagini:
                st.warning(f"🔴 {cam} - Nessuna immagine trovata.")
                continue

            ultima_img = immagini[0]
            timestamp_str = ultima_img.replace(".jpg", "")

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
            except:
                st.warning(f"📛 {cam} - Nome file non valido: {ultima_img}")
                continue

            ore_passate = (datetime.now() - timestamp).total_seconds() // 3600
            stato = "🟢" if ore_passate < 24 else "🔴"

            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {ultima_img}", buffer.write)
            buffer.seek(0)
            image = Image.open(buffer)

            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image, caption=ultima_img, width=200)
                with col2:
                    st.markdown(f"### {stato} {cam}")
                    st.write(f"🕑 Ultima immagine: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"⏱️ Tempo trascorso: `{int(ore_passate)}h`")

            st.markdown("---")

        except Exception as e:
            st.error(f"⚠️ Errore con la camera {cam}: {e}")

except Exception as e:
    st.error(f"⚠️ Errore nella cartella principale: {e}")

ftp.quit()
