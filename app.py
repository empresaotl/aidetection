import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io
import re
from streamlit_autorefresh import st_autorefresh

# 🔄 AUTO REFRESH ogni 5 minuti
st_autorefresh(interval=300000, key="aggiornamento")

# --- CONFIG FTP ---
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"

# --- PARSER nome camera e timestamp ---
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

# --- UI setup ---
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
st.title("\ud83d\udcf1 Dashboard - Ultima immagine per telecamera")

# --- CONNESSIONE FTP ---
try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("\u2705 Connessione FTP riuscita")
except Exception as e:
    st.error(f"\u274c Errore FTP: {e}")
    st.stop()

# --- RACCOLTA ultime immagini
camere_ultime_foto = {}

try:
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

except Exception as e:
    st.error(f"\u274c Errore lettura camere: {e}")

# --- STATISTICHE E FILTRI ---
if not camere_ultime_foto:
    st.warning("\u26a0\ufe0f Nessuna immagine trovata.")
else:
    count_attive = 0
    count_offline = 0

    for data in camere_ultime_foto.values():
        ts = data["timestamp"]
        ore = (datetime.now() - ts).total_seconds() // 3600
        if ore < 24:
            count_attive += 1
        else:
            count_offline += 1

    st.subheader(f"\ud83d\udcca Totale camere: {len(camere_ultime_foto)} | \ud83d\udfe2 Attive: {count_attive} | \ud83d\udd34 Offline: {count_offline}")

    query = st.text_input("\ud83d\udd0e Cerca per nome camera o cliente:", "").strip().lower()
    noms = sorted(camere_ultime_foto.keys())
    selected_cam = st.selectbox("\ud83d\udcc2 Seleziona una camera:", ["-- Nessuna --"] + noms)

    filtro_offline = st.radio(
        "\ud83d\udc41\ufe0f Mostra solo telecamere offline (>24h)?",
        ["No", "S\u00ec"],
        index=0,
        horizontal=True
    )

    modo_compatto = st.checkbox("\ud83e\uddf1 Modalit\u00e0 compatta (griglia)", value=False)

    if st.button("\ud83d\udd00 Mostra tutte le camere"):
        query = ""
        selected_cam = "-- Nessuna --"

    if modo_compatto:
        st.session_state.griglia = []

    for cam, data in sorted(camere_ultime_foto.items()):
        ts = data["timestamp"]
        diff_ore = (datetime.now() - ts).total_seconds() // 3600
        stato = "\ud83d\udfe2" if diff_ore < 24 else "\ud83d\udd34"

        if filtro_offline == "S\u00ec" and stato == "\ud83d\udfe2":
            continue
        if query and query not in cam.lower():
            continue
        if selected_cam != "-- Nessuna --" and cam != selected_cam:
            continue

        buffer = io.BytesIO()
        try:
            ftp.cwd(data["path"])
            ftp.retrbinary(f"RETR {data['filename']}", buffer.write)
            buffer.seek(0)
            image = Image.open(buffer)

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
                        st.write(f"\ud83d\udd52 Ultima attivit\u00e0: `{ts.strftime('%Y-%m-%d %H:%M:%S')}`")
                        st.write(f"\u23f1\ufe0f Trascorse: `{int(diff_ore)} ore`")
                st.markdown("---")

        except Exception as e:
            st.warning(f"\u26a0\ufe0f Errore caricando immagine '{cam}': {e}")
            continue

    # --- GRIGLIA IMMAGINI COMPATTA ---
    if modo_compatto and "griglia" in st.session_state:
        griglia = st.session_state.griglia
        num_per_riga = 4
        rows = [griglia[i:i+num_per_riga] for i in range(0, len(griglia), num_per_riga)]

        for row in rows:
            cols = st.columns(len(row))
            for idx, camera in enumerate(row):
                with cols[idx]:
                    st.image(camera["img"], use_column_width="always")
                    st.markdown(f"**{camera['stato']} {camera['cam']}**")
                    st.caption(f"\ud83d\udd52 {camera['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} • {camera['ore']}h fa")

# --- CHIUSURA FTP ---
try:
    ftp.quit()
except Exception as e:
    st.warning(f"\u26a0\ufe0f Connessione FTP chiusa con errore: {e}")

