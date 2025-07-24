
import json
from ftplib import FTP
from datetime import datetime
import re

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
CACHE_FILE = "cache_ultime_foto.json"

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

def genera_cache_completa():
    camere_ultime_foto = {}

    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(ROOT_FOLDER)
        camere = ftp.nlst()

        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            ultima_trovata = None

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
                                for img in files:
                                    nome_cam, ts = parse_nome_camera_e_data(img)
                                    if nome_cam and ts:
                                        # se non esiste o timestamp più recente
                                        if nome_cam not in camere_ultime_foto or ts > camere_ultime_foto[nome_cam]["timestamp"]:
                                            camere_ultime_foto[nome_cam] = {
                                                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                                                "path": path_img,
                                                "filename": img
                                            }
                            except:
                                continue
            except:
                continue
        ftp.quit()
    except Exception as e:
        print(f"Errore FTP: {e}")

    with open(CACHE_FILE, "w") as f:
        json.dump(camere_ultime_foto, f, indent=2)
    print(f"✅ Cache salvata: {len(camere_ultime_foto)} telecamere")

if __name__ == "__main__":
    genera_cache_completa()
