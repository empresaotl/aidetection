
from ftplib import FTP
import re
from datetime import datetime

FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"

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

def esplora_camere():
    try:
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(ROOT_FOLDER)
        camere = ftp.nlst()

        print(f"🔍 Trovate {len(camere)} cartelle camera")

        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            print(f"📁 {cam_folder}")
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
                                    print(f"  📂 {anno}/{mese}/{giorno}: Nessuna immagine")
                                    continue
                                print(f"  📂 {anno}/{mese}/{giorno}: {len(files)} immagini")
                                for f in files[:3]:  # mostra le prime 3 per esempio
                                    nome_cam, ts = parse_nome_camera_e_data(f)
                                    if nome_cam:
                                        print(f"    ✅ {f} → {nome_cam} @ {ts}")
                                    else:
                                        print(f"    ⚠️ Non parsato: {f}")
                            except Exception as e:
                                print(f"  ❌ Errore accedendo {path_img}: {e}")
            except Exception as e:
                print(f"❌ Errore con {cam_folder}: {e}")
        ftp.quit()
    except Exception as e:
        print(f"❌ Errore FTP iniziale: {e}")

if __name__ == "__main__":
    esplora_camere()
