import streamlit as st
import os
import json
from datetime import datetime
from PIL import Image
from streamlit_autorefresh import st_autorefresh
from ultralytics import YOLO
import cv2
import numpy as np
from ftplib import FTP

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_LOCAL_FOLDER = "/mount/ftp"
CACHE_FILE = "cache_camere.json"
DETECTION_MODEL_PATH = "models/yolov8n.pt"

st.set_page_config(page_title="Monitoramento de Câmeras", layout="wide")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

# === FUNÇÕES DE CACHE ===

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Cache corrompido: {e}")
    return {}

def salva_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def parse_timestamp(nome_arquivo):
    try:
        parts = nome_arquivo.split("_")
        timestamp_str = parts[-1].split(".")[0]
        return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
    except Exception:
        return None

# === FUNÇÃO PRINCIPAL PARA BUSCAR IMAGENS LOCAIS ===

def aggiorna_cache():
    camere = {}
    for root, _, files in os.walk(ROOT_LOCAL_FOLDER):
        for file in sorted(files, reverse=True):
            if file.endswith((".jpg", ".jpeg")):
                nome_camera = "_".join(file.split("_")[:-1])
                timestamp = parse_timestamp(file)
                if nome_camera not in camere or (timestamp and timestamp > datetime.strptime(camere[nome_camera]["timestamp"], "%Y-%m-%d %H:%M:%S")):
                    camere[nome_camera] = {
                        "filename": file,
                        "path": os.path.join(root, file),
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "desconhecido"
                    }
    return camere

# === ALTERNATIVA VIA FTP ===

def aggiorna_cache_da_ftp():
    camere = {}
    try:
        with FTP(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd("/")
            for nome_camera in ftp.nlst():
                if nome_camera == "." or nome_camera == "..":
                    continue
                ftp.cwd(f"/{nome_camera}")
                years = ftp.nlst()
                if not years:
                    continue
                latest_year = sorted(years)[-1]
                ftp.cwd(f"/{nome_camera}/{latest_year}")
                months = ftp.nlst()
                if not months:
                    continue
                latest_month = sorted(months)[-1]
                ftp.cwd(f"/{nome_camera}/{latest_year}/{latest_month}")
                days = ftp.nlst()
                if not days:
                    continue
                latest_day = sorted(days)[-1]
                ftp.cwd(f"/{nome_camera}/{latest_year}/{latest_month}/{latest_day}")
                files = sorted(ftp.nlst())
                if not files:
                    continue
                last_file = files[-1]
                camere[nome_camera] = {
                    "filename": last_file,
                    "timestamp": "desconhecido",
                    "path": f"/{nome_camera}/{latest_year}/{latest_month}/{latest_day}/{last_file}"
                }
    except Exception as e:
        st.warning(f"Erro FTP: {e}")
    return camere

# === FUNÇÕES DE PROCESSAMENTO DE IMAGEM ===

def get_local_image_path(filename):
    for root, _, files in os.walk(ROOT_LOCAL_FOLDER):
        if filename in files:
            return os.path.join(root, filename)
    return None

def yolo_detect(img_path):
    model = YOLO(DETECTION_MODEL_PATH)
    result = model.predict(source=img_path, save=False, verbose=False, conf=0.3)
    if result and result[0].boxes is not None:
        return result[0]
    return None

def detecta_pessoas(imagem_path):
    imagem = cv2.imread(imagem_path)
    result = yolo_detect(imagem_path)
    if result is None:
        return imagem, 0
    boxes = result.boxes
    count = 0
    for box in boxes:
        cls = int(box.cls[0])
        if cls == 0:  # classe 0 = pessoa
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(imagem, (x1, y1), (x2, y2), (0, 255, 0), 2)
            count += 1
    return imagem, count

def processa_imagem(image_path):
    try:
        img, num_pessoas = detecta_pessoas(image_path)
        return img, num_pessoas
    except Exception as e:
        st.warning(f"Erro ao processar imagem: {e}")
        return None, 0

# === APP ===

st.title("📷 Últimas imagens recebidas com detecção")

try:
    camere_ultime_foto = carica_cache()
    st.success("📦 Cache carregado.")
except Exception as e:
    st.error(f"Erro no cache: {e}")
    camere_ultime_foto = aggiorna_cache()
    salva_cache(camere_ultime_foto)

if not camere_ultime_foto:
    camere_ultime_foto = aggiorna_cache()
    salva_cache(camere_ultime_foto)

if not camere_ultime_foto:
    st.warning("Nenhuma imagem disponível.")
else:
    for nome_camera, dados in camere_ultime_foto.items():
        st.subheader(f"{nome_camera}")
        st.text(f"Última atualização: {dados['timestamp']}")
        path = dados["path"]
        if not os.path.exists(path):
            path = get_local_image_path(dados["filename"])
        if path:
            img, count = processa_imagem(path)
            if img is not None:
                st.image(img, caption=f"{dados['filename']} - Pessoas detectadas: {count}", use_column_width=True)
        else:
            st.warning("Imagem não encontrada.")

