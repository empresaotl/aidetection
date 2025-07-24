import streamlit as st
from ftplib import FTP
from datetime import datetime
import pytz
from PIL import Image
import io
import re
import os
import json
from streamlit_autorefresh import st_autorefresh

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
CACHE_FILE = "cache_ultime_foto.json"
REFRESH_INTERVAL = 300000  # 5 minuti

# === FUNZIONI UTILI ===
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
        for k in data:
            if isinstance(data[k]["timestamp"], datetime):
                data[k]["timestamp"] = data[k]["timestamp"].isoformat()
        json.dump(data, f, indent=2)
    st.success(f"📦 Cache salvata con {len(data)} telecamere.")

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                for k in data:
                    data[k]["timestamp"] = datetime.fromisoformat(data[k]["timestamp"])
                return data
        except Exception as e:
            st.warning(f"⚠️ Cache corrotta: {e}")
    return {}

def aggiorna_da_ftp():
    camere_ultime_foto = {}
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
                                        "timestamp": timestamp,
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
    except Exception as e:
        st.error(f"Errore FTP: {e}")
    return camere_ultime_foto

# === IMPOSTAZIONI PAGINA ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📸 Dashboard - Ultime Immagini per Telecamera")
st.caption(f"🕒 Orario di riferimento (Brasilia): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === CARICAMENTO DATI ===
camere_ultime_foto = carica_cache()
if not camere_ultime_foto:
    st.info("📡 Connessione a FTP per generare nuova cache...")
    camere_ultime_foto = aggiorna_da_ftp()
    if camere_ultime_foto:
        salva_cache(camere_ultime_foto)
else:
    st.success("📦 Cache caricata")

# === BOTTONE PER FORZARE AGGIORNAMENTO ===
if st.button("🔄 Forza aggiornamento da FTP"):
    camere_ultime_foto = aggiorna_da_ftp()
    if camere_ultime_foto:
        salva_cache(camere_ultime_foto)
    st.experimental_rerun()

# === FILTRI E RICERCA ===
query = st.text_input("🔍 Cerca per nome camera o cliente:", "").strip().lower()
noms = sorted(camere_ultime_foto.keys())
selected_cam = st.selectbox("🎯 Seleziona una camera:", ["-- Nessuna --"] + noms)
filtro_offline = st.radio("📊 Mostra solo telecamere offline (>24h)?", ["No", "Sì"], horizontal=True)
modo_compatto = st.checkbox("🖼️ Modalità compatta (griglia)", value=True)

# === VISUALIZZAZIONE ===
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)
attive, offline = 0, 0
st.session_state.griglia = []

for cam, data in sorted(camere_ultime_foto.items()):
    ts = data["timestamp"]
    if ts.tzinfo is None:
        ts = brasil_tz.localize(ts)
    diff_ore = (now_brasil - ts).total_seconds() // 3600
    stato = "🟢" if diff_ore < 24 else "🔴"

    if filtro_offline == "Sì" and stato == "🟢":
        continue
    if query and query not in cam.lower():
        continue
    if selected_cam != "-- Nessuna --" and cam != selected_cam:
        continue

    if diff_ore < 24:
        attive += 1
    else:
        offline += 1

    buffer = io.BytesIO()
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(data["path"])
        ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
        buffer.seek(0)
        image = Image.open(buffer)
        ftp.quit()

        if modo_compatto:
            st.session_state.griglia.append({
                "cam": cam,
                "img": image,
                "stato": stato,
                "timestamp": ts,
                "ore": int(diff_ore)
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

# === RIEPILOGO ===
st.subheader(f"Totale: {len(camere_ultime_foto)} | ✅ Attive: {attive} | 🔴 Offline: {offline}")

# === GRIGLIA COMPATTA ===
if modo_compatto and st.session_state.griglia:
    griglia = st.session_state.griglia
    num_per_riga = 4
    rows = [griglia[i:i + num_per_riga] for i in range(0, len(griglia), num_per_riga)]
    for row in rows:
        cols = st.columns(len(row))
        for idx, camera in enumerate(row):
            with cols[idx]:
                st.image(camera["img"], use_container_width=True)
                st.markdown(f"**{camera['stato']} {camera['cam']}**")
                st.caption(f"{camera['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} • {camera['ore']}h fa")

