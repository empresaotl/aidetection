import streamlit as st
import os
import json
import time
import numpy as np
from datetime import datetime
from PIL import Image
from streamlit_autorefresh import st_autorefresh
import cv2  # Corrigido: garantir que está presente
from ultralytics import YOLO

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_LOCAL_FOLDER = "/mount/ftp"
CACHE_FILE = "cache_camere.json"

st.set_page_config(page_title="Monitoramento de Câmeras", layout="wide")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")  # Atualiza a cada 5 min

# === FUNÇÕES ===

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

def get_local_image_path(filename):
    for root, _, files in os.walk(ROOT_LOCAL_FOLDER):
        if filename in files:
            return os.path.join(root, filename)
    return None

def parse_timestamp(nome_arquivo):
    try:
        parts = nome_arquivo.split("_")
        timestamp_str = parts[-1].split(".")[0]
        return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
    except Exception:
        return None

def aggiorna_cache():
    camere = {}
    for root, _, files in os.walk(ROOT_LOCAL_FOLDER):
        for file in sorted(files, reverse=True):
            if file.endswith(".jpg") or file.endswith(".jpeg"):
                nome_camera = "_".join(file.split("_")[:-1])
                timestamp = parse_timestamp(file)
                if nome_camera not in camere or (timestamp and timestamp > camere[nome_camera]["timestamp"]):
                    camere[nome_camera] = {
                        "filename": file,
                        "path": os.path.join(root, file),
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "desconhecido"
                    }
    return camere

# === INÍCIO ===

st.title("📷 Últimas imagens recebidas")

if os.path.exists(CACHE_FILE):
    try:
        camere_ultime_foto = carica_cache()
        st.success("📦 Cache carregado corretamente.")
    except Exception as e:
        st.error(f"❌ Erro ao carregar cache: {e}. Atualizando via FTP...")
        camere_ultime_foto = aggiorna_cache()
        salva_cache(camere_ultime_foto)
else:
    camere_ultime_foto = aggiorna_cache()
    salva_cache(camere_ultime_foto)

if not camere_ultime_foto:
    st.warning("Nenhuma imagem encontrada.")
else:
    for nome_camera, dados in camere_ultime_foto.items():
        st.subheader(f"{nome_camera}")
        st.text(f"Última atualização: {dados['timestamp']}")
        try:
            image = Image.open(dados["path"])
            st.image(image, caption=dados["filename"], use_column_width=True)
        except Exception as e:
            st.warning(f"Erro ao carregar imagem: {e}")
