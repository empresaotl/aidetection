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

# ---- CONFIG FTP ----
FTP_HOST = "ftp://cftp_nicebr@ftp.drivehq.com"        # Sostituisci con il tuo host
FTP_USER = "nicebr"           # Sostituisci
FTP_PASS = "otl.123"           # Sostituisci
CARTELLA_ROOT = "/"                 # o "/telecamere", se usi una sottocartella

NUM_CAMERE = 200  # quante ne hai

# ---- CONNETTI AL SERVER FTP ----
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore nella connessione FTP: {e}")
    st.stop()

st.title("🔧 Dashboard Amministratore - Stato Telecamere")

# ---- SCORRI TUTTE LE CAMERE ----
for i in range(1, NUM_CAMERE + 1):
    cam_id = f"Cam_{i:03d}"  # Cam_001, Cam_002, ...
    try:
        ftp.cwd(f"{CARTELLA_ROOT}/{cam_id}")
        files = ftp.nlst()
        immagini = sorted([f for f in files if f.endswith(".jpg")], reverse=True)

        if not immagini:
            st.error(f"🔴 {cam_id} - Nessuna immagine trovata.")
            continue

        ultima_img = immagini[0]
        timestamp_str = ultima_img.replace(".jpg", "")
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
        ore_passate = (datetime.now() - timestamp).total_seconds() // 3600

        stato = "🟢" if ore_passate < 24 else "🔴"

        # Scarica immagine
        buffer = io.BytesIO()
        ftp.retrbinary(f"RETR {ultima_img}", buffer.write)
        buffer.seek(0)
        image = Image.open(buffer)

        st.markdown(f"### {stato} {cam_id} - Ultima immagine: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}` ({int(ore_passate)}h fa)")
        st.image(image, width=400)
        st.markdown("---")

    except Exception as e:
        st.error(f"⚠️ Errore con {cam_id}: {e}")

ftp.quit()
