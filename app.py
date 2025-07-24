import streamlit as st
from ftplib import FTP
from datetime import datetime, timedelta
from PIL import Image
import io

# --- CONFIG FTP ---
FTP_HOST = "ftp.drivehq.com"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
CAMERA_FOLDER = "/REO_325"

# ✅ [1] Mostra titolo e messaggio iniziale
st.title("🔧 Pannello Amministratore - Stato Telecamere")
st.info("📡 Inizializzazione...")

# ✅ [2] Connessione FTP con messaggio visibile
try:
    st.info("🔌 Connessione al server FTP...")
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Connessione FTP riuscita")
except Exception as e:
    st.error(f"❌ Errore nella connessione FTP: {e}")
    st.stop()

# ✅ [3] Navigazione limitata (solo 1 mese e 1 giorno)
try:
    ftp.cwd(CAMERA_FOLDER)
    mesi = ftp.nlst()[:1]  # ✅ Limita a 1 solo mese

    for mese in mesi:
        try:
            ftp.cwd(f"{CAMERA_FOLDER}/{mese}")
            giorni = ftp.nlst()[:1]  # ✅ Limita a 1 solo giorno

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
                try:
                    ftp.retrbinary(f"RETR {ultima_img}", buffer.write)
                    buffer.seek(0)
                    image = Image.open(buffer)
                except:
                    st.error(f"⚠️ Errore nel caricamento immagine {ultima_img}")
                    continue

                st.markdown(f"### {stato} {giorno}/{mese} - Ultima immagine: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}` ({int(ore_passate)}h fa)")
                st.image(image, width=400)
                st.markdown("---")

        except Exception as e:
            st.error(f"⚠️ Errore navigando in {mese}: {e}")

except Exception as e:
    st.error(f"⚠️ Errore principale: {e}")

ftp.quit()
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
    try:
        ftp.retrbinary(f"RETR {ultima_img}", buffer.write)
        buffer.seek(0)
        image = Image.open(buffer)
    except:
        st.error(f"⚠️ Errore nel caricamento immagine {ultima_img}")
        continue

    # ✅ MOSTRA BLOCCO VISUALE CAMERA
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(image, caption=ultima_img, width=200)
        with col2:
            st.markdown(f"### {stato} Telecamera: `{giorno}/{mese}`")
            st.write(f"🕑 Ultima immagine: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}`")
            st.write(f"⏱️ Tempo trascorso: `{int(ore_passate)}h`")
    st.markdown("---")
