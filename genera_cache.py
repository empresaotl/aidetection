import json
import re
from ftplib import FTP
from datetime import datetime

# === CONFIG FTP ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
CACHE_FILE = "cache_ultime_foto.json"

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

# === GENERA CACHE ===
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
                                    "timestamp": timestamp.isoformat(),
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

    # Salva su file cache
    with open(CACHE_FILE, "w") as f:
        json.dump(camere_ultime_foto, f, indent=2)

    print(f"✅ Cache generata con {len(camere_ultime_foto)} telecamere salvate.")

except Exception as e:
    print(f"❌ Errore durante la generazione della cache: {e}")
