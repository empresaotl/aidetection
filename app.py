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

# === FUNZIONI CACHE ===
def salva_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, default=str, indent=2)

def carica_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

# === PARSER ===
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

# === CARICAMENTO FTP ===
def aggiorna_cache_da_ftp():
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
    except Exception as e:
        st.error(f"Errore FTP: {e}")
    return camere_ultime_foto

# === CARICAMENTO DATI ===
carica_nuova_cache = False
if st.button("🔄 Forza aggiornamento"):
    st.cache_data.clear()
    carica_nuova_cache = True
    st.success("✅ Cache forzata da FTP.")

if carica_nuova_cache:
    camere_ultime_foto = aggiorna_cache_da_ftp()
    salva_cache(camere_ultime_foto)
else:
    try:
        camere_ultime_foto = carica_cache()
        st.success("📦 Cache caricata correttamente.")
    except Exception as e:
        st.error(f"❌ Errore nel caricamento cache: {e}")
        camere_ultime_foto = {}

if not camere_ultime_foto:
    st.warning("⚠️ Nessuna immagine trovata.")
    st.stop()

# === ANALISI ===
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)
count_attive = 0
count_offline = 0

for cam, data in camere_ultime_foto.items():
    ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
    ts = brasil_tz.localize(ts)
    diff_ore = (now_brasil - ts).total_seconds() / 3600
    if diff_ore < 24:
        count_attive += 1
    else:
        count_offline += 1

st.subheader(f"Totale camere: {len(camere_ultime_foto)} | ✅ Attive: {count_attive} | 🔴 Offline: {count_offline}")

query = st.text_input("🔍 Cerca per nome camera o cliente:", "").strip().lower()
filtro_offline = st.checkbox("🔴 Mostra solo telecamere offline (>24h)", value=False)
modo_compatto = st.checkbox("🖼️ Modalità compatta (griglia)", value=True)

# === VISUALIZZAZIONE ===
risultati = []
for cam, data in sorted(camere_ultime_foto.items()):
    if query and query not in cam.lower():
        continue

    ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
    ts = brasil_tz.localize(ts)
    diff = now_brasil - ts
    ore = diff.total_seconds() / 3600
    giorni = int(diff.days)

    stato = "🟢" if ore < 24 else "🔴"
    if filtro_offline and stato == "🟢":
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
    except Exception as e:
        st.warning(f"Errore caricando immagine da FTP per {cam}: {e}")
        image = None

    risultati.append({
        "cam": cam,
        "img": image,
        "stato": stato,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "descrizione": f"{giorni} giorno{'i' if giorni != 1 else ''} fa" if giorni >= 1 else f"{int(ore)}h fa"
    })

# === RENDERING ===
if modo_compatto:
    num_per_riga = 4
    for i in range(0, len(risultati), num_per_riga):
        cols = st.columns(num_per_riga)
        for j, item in enumerate(risultati[i:i+num_per_riga]):
            with cols[j]:
                if item["img"]:
                    st.image(item["img"], use_container_width=True)
                st.markdown(f"**{item['stato']} {item['cam']}**")
                st.caption(f"{item['timestamp']} • {item['descrizione']}")
else:
    for item in risultati:
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                if item["img"]:
                    st.image(item["img"], width=250)
            with col2:
                st.markdown(f"### {item['stato']} {item['cam']}")
                st.write(f"Ultima attività: `{item['timestamp']}`")
                st.write(f"Inattiva da: `{item['descrizione']}`")
        st.markdown("---")

