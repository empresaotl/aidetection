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
TTL_CACHE = 300  # 5 minuti

# === AUTO REFRESH ===
st_autorefresh(interval=TTL_CACHE * 1000, key="aggiorna")

# === PAGINA ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📸 Dashboard - Ultime Immagini per Telecamera")
st.caption(f"🕒 Orario di riferimento (Brasilia): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

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
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def carica_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def salva_immagine_locale(nome_camera, image_obj):
    os.makedirs("immagini_cache", exist_ok=True)
    path = os.path.join("immagini_cache", f"{nome_camera}.jpg")
    image_obj.save(path, "JPEG")

# === CARICAMENTO DATI ===
camere_ultime_foto = carica_cache()
if camere_ultime_foto:
    st.success("📦 Cache caricata")
else:
    st.warning("⚠️ Nessuna immagine trovata nella cache.")
    st.stop()

# === UI FILTRI ===
count_attive = 0
count_offline = 0
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)

query = st.text_input("🔍 Cerca per nome camera o cliente:", "").strip().lower()
filtro_offline = st.radio("🔴 Mostra solo offline (>24h)?", ["No", "Sì"], index=0, horizontal=True)
modo_compatto = st.checkbox("🧱 Modalità griglia compatta", value=True)

if st.button("🔄 Forza aggiornamento cache"):
    st.rerun()

# === VISUALIZZAZIONE ===
st.session_state.griglia = []

for cam, data in sorted(camere_ultime_foto.items()):
    ts_str = data["timestamp"]
    ts = datetime.fromisoformat(ts_str)
    if ts.tzinfo is None:
        ts = brasil_tz.localize(ts)

    diff = now_brasil - ts
    diff_ore = diff.total_seconds() // 3600
    stato = "🟢" if diff_ore < 24 else "🔴"

    if filtro_offline == "Sì" and stato == "🟢":
        continue
    if query and query not in cam.lower():
        continue

    buffer = io.BytesIO()
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(data["path"])
        ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
        ftp.quit()

        buffer.seek(0)
        image = Image.open(buffer)
        salva_immagine_locale(cam, image)

        if modo_compatto:
            st.session_state.griglia.append({
                "cam": cam,
                "img": image,
                "stato": stato,
                "timestamp": ts,
                "ore": int(diff_ore),
                "giorni": diff.days
            })
        else:
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(image, caption=data["filename"], width=200)
                with col2:
                    st.markdown(f"### {stato} {cam}")
                    st.write(f"Ultima attività: `{ts.strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"Trascorse: `{int(diff_ore)} ore`")
            st.markdown("---")

    except Exception as e:
        st.warning(f"Errore caricando immagine da FTP per {cam}: {e}")
        continue

# === GRIGLIA COMPATTA ===
if modo_compatto and st.session_state.griglia:
    griglia = st.session_state.griglia
    num_per_riga = 4
    rows = [griglia[i:i+num_per_riga] for i in range(0, len(griglia), num_per_riga)]

    for row in rows:
        cols = st.columns(len(row))
        for idx, camera in enumerate(row):
            with cols[idx]:
                st.image(camera["img"], use_container_width=True)
                giorni_o_ore = f"{camera['giorni']} giorni fa" if camera['giorni'] >= 1 else f"{camera['ore']}h fa"
                st.markdown(f"**{camera['stato']} {camera['cam']}**")
                st.caption(f"{camera['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} • {giorni_o_ore}")

