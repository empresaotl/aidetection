import streamlit as st
from datetime import datetime, timedelta

# Simulazione di una telecamera
cameras = {
    "Cam_01": datetime.now() - timedelta(hours=5),
    "Cam_02": datetime.now() - timedelta(hours=13),
    "Cam_03": datetime.now() - timedelta(days=1),
}

st.title("🔧 Pannello Amministratore - Stato Telecamere")

for cam_name, last_time in cameras.items():
    hours_passed = (datetime.now() - last_time).total_seconds() / 3600
    color = "🟢" if hours_passed < 12 else "🔴"
    st.write(f"{color} **{cam_name}** - Ultima foto: {last_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours_passed)}h fa)")
import streamlit as st
from ftplib import FTP
from datetime import datetime, timedelta
from PIL import Image
import io

import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io

# --- FTP Config ---
FTP_HOST = "ftp.drivehq.com"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
CAMERA_FOLDER = "/REO_325"  # cartella principale

# --- Connessione FTP ---
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore FTP: {e}")
    st.stop()

# --- Naviga nella cartella ---
try:
    ftp.cwd(CAMERA_FOLDER)
    mesi = ftp.nlst()  # ad es. ['Luglio']
    
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
            st.error(f"Errore navigando in {mese}: {e}")

except Exception as e:
    st.error(f"Errore principale: {e}")

ftp.quit()
