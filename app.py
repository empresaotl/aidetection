import os
import json
import streamlit as st
import cv2
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from ultralytics import YOLO

# === CONFIGURAÇÕES ===
BASE_PATH = "FreeFileSync"
CACHE_FILE = "cache.json"
MODEL_PATH = "best.pt"

# === AUTOREFRESH ===
st_autorefresh(interval=5 * 60 * 1000, key="refresh")

st.title("📸 Monitoramento de Câmeras - EmpresaOTL")

# === FUNÇÕES UTILITÁRIAS ===
def carica_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                st.warning("⚠️ Cache corrompido. Será regenerado.")
                return {}
    return {}

def salva_cache(dados):
    with open(CACHE_FILE, "w") as f:
        json.dump(dados, f)

def extrai_info_arquivo(nome_arquivo):
    try:
        partes = nome_arquivo.split("_")
        nome_camera = "_".join(partes[:-1])
        timestamp_str = partes[-1].split(".")[0]
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        return nome_camera, timestamp
    except:
        return None, None

def atualiza_cache_local():
    st.info("🔄 Lendo estrutura local para atualizar cache...")
    cameras = {}
    for root, _, files in os.walk(BASE_PATH):
        for nome_arquivo in sorted(files, reverse=True):
            if nome_arquivo.lower().endswith(".jpg"):
                nome_camera, timestamp = extrai_info_arquivo(nome_arquivo)
                if nome_camera and nome_camera not in cameras:
                    cameras[nome_camera] = {
                        "ultima_imagem": os.path.join(root, nome_arquivo),
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    }
    return cameras

def mostra_imagem(path, nome_camera, timestamp):
    st.subheader(f"📷 {nome_camera}")
    st.image(path, caption=f"Última imagem às {timestamp}", use_column_width=True)

def detectar_epi(path_imagem, modelo):
    try:
        img = cv2.imread(path_imagem)
        results = model(img)
        boxes = results[0].boxes
        classes_detectadas = [results[0].names[int(c)] for c in boxes.cls]
        return classes_detectadas
    except Exception as e:
        return [f"Erro na detecção: {e}"]

# === CARREGAMENTO INICIAL ===
if "forcar_cache" in st.query_params:
    camere_ultime_foto = atualiza_cache_local()
    salva_cache(camere_ultime_foto)
else:
    camere_ultime_foto = carica_cache()
    if not camere_ultime_foto:
        camere_ultime_foto = atualiza_cache_local()
        salva_cache(camere_ultime_foto)

if not camere_ultime_foto:
    st.warning("Nenhuma câmera encontrada.")
    st.stop()

# === INTERFACE ===
model = YOLO(MODEL_PATH)
nome_camera_selecionada = st.selectbox("Selecione a câmera:", sorted(camere_ultime_foto.keys()))

dados = camere_ultime_foto[nome_camera_selecionada]
path_img = dados["ultima_imagem"]
timestamp = dados["timestamp"]

if os.path.exists(path_img):
    mostra_imagem(path_img, nome_camera_selecionada, timestamp)

    st.markdown("### 🦺 Detecção de EPIs")
    with st.spinner("Executando detecção..."):
        resultados = detectar_epi(path_img, model)
    st.success("Detecção concluída.")
    for item in resultados:
        st.markdown(f"- {item}")
else:
    st.error(f"Imagem não encontrada: {path_img}")

