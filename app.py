import streamlit as st
from ftplib import FTP
from datetime import datetime
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
st_autorefresh(interval=TTL_CACHE * 1000, key="refresh")

# === PAGINA ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("📸 Dashboard - Ultime Immagini per Telecamera")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
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

# === CARICAMENTO FTP E CACHE ===
camere_ultime_foto = {}

if not os.path.exists(CACHE_FILE) or st.button("🔄 Forza aggiornamento da FTP"):
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(ROOT_FOLDER)
        camere = ftp.nlst()

        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            nome_cam_trovato = None

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
                                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                        "path": path_img,
                                        "filename": ultima_img
                                    }
                                    nome_cam_trovato = nome_cam
                                    break
                            except:
                                continue
                        if nome_cam_trovato:
                            break
                    if nome_cam_trovato:
                        break
            except:
                continue
        ftp.quit()
        salva_cache(camere_ultime_foto)
        st.success("✅ Cache aggiornata")
    except Exception as e:
        st.error(f"Errore FTP: {e}")
else:
    camere_ultime_foto = carica_cache()
    st.info("📦 Cache caricata")

# === VISUALIZZAZIONE ===
if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata.")
else:
    brasil_tz = pytz.timezone('America/Sao_Paulo')
    now_brasil = datetime.now(brasil_tz)

    query = st.text_input("🔍 Cerca per nome camera o cliente:").strip().lower()
    filtro_offline = st.radio("📡 Mostra solo offline (>24h)?", ["No", "Sì"], horizontal=True)
    modo_compatto = st.checkbox("🧱 Visualizzazione compatta (griglia)", value=True)

    griglia = []

    for cam, data in sorted(camere_ultime_foto.items()):
        try:
            ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
            ts = brasil_tz.localize(ts)
            diff_ore = (now_brasil - ts).total_seconds() // 3600
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

                griglia.append({
                    "cam": cam,
                    "img": image,
                    "stato": stato,
                    "timestamp": ts,
                    "ore": int(diff_ore)
                })
            except Exception as e:
                st.warning(f"Errore caricando immagine da FTP per {cam}: {e}")
                continue
        except Exception as e:
            st.warning(f"Errore nei dati per {cam}: {e}")
            continue

    # === VISUALIZZA IN GRIGLIA O LISTA ===
    if modo_compatto:
        num_per_riga = 4
        rows = [griglia[i:i+num_per_riga] for i in range(0, len(griglia), num_per_riga)]

        for row in rows:
            cols = st.columns(len(row))
            for idx, camera in enumerate(row):
                with cols[idx]:
                    st.image(camera["img"], use_container_width=True)
                    st.markdown(f"**{camera['stato']} {camera['cam']}**")
                    st.caption(f"{camera['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} • {camera['ore']}h fa")
    else:
        for camera in griglia:
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(camera["img"], width=200)
                with col2:
                    st.markdown(f"### {camera['stato']} {camera['cam']}")
                    st.write(f"Ultima attività: `{camera['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"Trascorse: `{camera['ore']} ore`")
            st.markdown("---")

