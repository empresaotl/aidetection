import streamlit as st
from ftplib import FTP
from datetime import datetime, timedelta
import pytz
from PIL import Image, ImageDraw, ImageFont # Adicionado ImageDraw, ImageFont para anotação
import io
import re
import json
import os
from streamlit_autorefresh import st_autorefresh
import numpy as np # Adicionado para manipulação de imagem com OpenCV
import cv2 # Adicionado para manipulação de imagem com OpenCV
from ultralytics import YOLO # Adicionado para YOLO

# === CONFIG ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
CACHE_FILE = "cache_ultime_foto.json"
TTL_CACHE = 300  # 5 minutos
LOCAL_IMAGE_CACHE_DIR = "cache_imagens_locais" # NOVO: Diretório para cache local de imagens
YOLO_MODEL_PATH = "yolov8n.pt" # NOVO: Caminho para o seu modelo YOLOv8

# Garante que o diretório de cache local exista
os.makedirs(LOCAL_IMAGE_CACHE_DIR, exist_ok=True)

# === FUNÇÕES CACHE ===
def salva_cache(data):
    # Certifica-se de que a pasta CACHE_FILE existe (embora CACHE_FILE seja um arquivo, não uma pasta)
    # A pasta para CACHE_FILE é a raiz do app.
    # Certifica-se de que o diretório do arquivo de cache existe, se CACHE_FILE contiver um caminho.
    cache_dir = os.path.dirname(CACHE_FILE)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, default=str, indent=2)

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                # Tenta carregar o JSON. Se estiver vazio ou inválido, isso lançará um erro.
                content = f.read()
                if not content.strip(): # Se o arquivo estiver vazio ou só com espaços em branco
                    st.warning("Arquivo de cache vazio ou inválido. Forçando atualização do FTP.")
                    return {} # Retorna vazio para forçar o recarregamento do FTP
                return json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"❌ Erro ao decodificar o cache JSON '{CACHE_FILE}': {e}. O arquivo pode estar corrompido. Forçando atualização do FTP.")
            # Opcional: tentar remover o arquivo corrompido para que um novo seja criado
            try:
                os.remove(CACHE_FILE)
                st.info("Arquivo de cache corrompido removido.")
            except Exception as remove_e:
                st.warning(f"Não foi possível remover o arquivo de cache corrompido: {remove_e}")
            return {} # Retorna vazio para que o fluxo principal tente atualizar do FTP
        except Exception as e:
            st.error(f"❌ Erro inesperado ao carregar o cache: {e}. Forçando atualização do FTP.")
            return {}
    return {}

# ... (restante do seu código) ...

# === CARICAMENTO DADOS PRINCIPAL ===
carica_nuova_cache = False
if st.button("🔄 Forçar atualização do FTP e reprocessar"):
    st.cache_data.clear()
    # Limpa o cache de imagens local também para garantir download fresco
    for f in os.listdir(LOCAL_IMAGE_CACHE_DIR):
        os.remove(os.path.join(LOCAL_IMAGE_CACHE_DIR, f))
    
    # NOVO: Remove explicitamente o arquivo de cache principal para forçar um novo
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
            st.info("Arquivo de cache principal removido para forçar recriação.")
        except Exception as e:
            st.warning(f"Não foi possível remover o arquivo de cache principal: {e}")

    carica_nuova_cache = True
    st.success("✅ Cache forçado do FTP e imagens locais limpas.")

if carica_nuova_cache:
    camere_ultime_foto = aggiorna_cache_da_ftp() # Esta função já faz o cache local da imagem
    salva_cache(camere_ultime_foto)
else:
    # A chamada a carica_cache() já lida com erros e retorna {} se o cache estiver inválido.
    camere_ultime_foto = carica_cache() 
    if not camere_ultime_foto: # Se o cache estiver vazio ou falhou ao carregar
        st.warning("Cache vazio ou inválido. Tentando atualizar do FTP...")
        camere_ultime_foto = aggiorna_cache_da_ftp() # Tenta buscar do FTP se o cache falhar
        salva_cache(camere_ultime_foto) # Salva a nova cache
    else:
        st.success("📦 Cache carregado corretamente.")

# ... (restante do código) ...

# === AUTO REFRESH ===
st_autorefresh(interval=TTL_CACHE * 1000, key="aggiorna")

# === PAGINA ===
st.set_page_config(page_title="Dashboard Telecamere", layout="wide")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📸 Dashboard - Ultime Imagens por Telecamera")
st.caption(f"🕒 Horário de referência (Brasília): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === FUNÇÕES CACHE ===
def salva_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, default=str, indent=2)

def carica_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def get_local_image_path(filename):
    """Retorna o caminho completo para a imagem no cache local."""
    return os.path.join(LOCAL_IMAGE_CACHE_DIR, filename)

def download_image_from_ftp_and_cache(ftp_session, remote_folder_path, filename):
    """
    Baixa uma imagem do FTP e a salva no cache local.
    Retorna o caminho local do arquivo ou None em caso de erro.
    """
    local_path = get_local_image_path(filename)
    try:
        # Se o arquivo já existe e tem tamanho, assumimos que está ok para simplificar
        # Para produção, você poderia verificar o timestamp ou hash
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        # Altera para o diretório correto no FTP antes de baixar
        original_cwd = ftp_session.pwd() # Guarda o diretório atual do FTP
        ftp_session.cwd(remote_folder_path) # Vai para a pasta da imagem
        
        with open(local_path, 'wb') as f:
            ftp_session.retrbinary(f"RETR {filename}", f.write)
        
        ftp_session.cwd(original_cwd) # Volta para o diretório original
        return local_path
    except Exception as e:
        st.warning(f"Erro ao baixar ou salvar '{filename}' do FTP para cache local: {e}")
        # Tenta remover o arquivo parcialmente baixado se houver um erro
        if os.path.exists(local_path):
            os.remove(local_path)
        return None

# === PARSER ===
def parse_nome_camera_e_data(nome_file):
    try:
        match = re.match(r"(.+?)_00_(\d{14})\.jpg", nome_file)
        if match:
            nome_camera = match.group(1).strip()
            timestamp_str = match.group(2)
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            return nome_camera, timestamp
    except Exception as e:
        # st.error(f"Erro ao parsear nome de arquivo '{nome_file}': {e}") # Debug
        return None, None
    return None, None

# === INICIALIZAÇÃO DO MODELO YOLO ===
@st.cache_resource # Usa o cache de recursos do Streamlit para carregar o modelo uma vez
def load_yolo_model():
    try:
        model = YOLO(YOLO_MODEL_PATH)
        return model
    except Exception as e:
        st.error(f"Erro ao carregar o modelo YOLO de '{YOLO_MODEL_PATH}': {e}. Certifique-se de que o arquivo existe e é válido.")
        return None

yolo_model = load_yolo_model()
if not yolo_model:
    st.warning("O modelo YOLO não pôde ser carregado. A detecção de EPI não funcionará.")

# === FUNÇÃO DE DETECÇÃO YOLO ===
def process_image_with_yolo(pil_image):
    """
    Processa uma imagem PIL com o modelo YOLO, desenha bounding boxes
    e determina o status do alerta EPI.
    Retorna a imagem anotada, status de alerta, lista de detecções e booleano de alerta.
    """
    if not yolo_model:
        return pil_image, "Modelo YOLO não carregado", [], False

    # Converte PIL Image para array numpy (BGR para OpenCV)
    # YOLO Ultralytics pode aceitar PIL Image diretamente, mas para desenhar com OpenCV
    # ou para garantir compatibilidade, é bom converter.
    img_np = np.array(pil_image)
    img_cv2 = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    results = yolo_model(img_cv2, verbose=False, conf=0.25) # verbose=False para não imprimir logs. conf=0.25 é um bom default.

    annotated_image = pil_image # Imagem original caso não haja detecções ou anotações
    detections_info = []
    alert_status = "✅ OK" # Status padrão de EPI
    alert_triggered = False

    # Exemplo de classes de EPI que você espera detectar (ajuste conforme seu modelo)
    # Mapeie os nomes das classes do seu modelo YOLO para o que você quer monitorar
    # Para saber os nomes das classes do seu modelo, você pode inspecionar yolo_model.names
    
    # Exemplo: supondo que 'helmet' seja a classe 0, 'safety_vest' a classe 1, etc.
    # Você precisará ajustar isso para os índices de classe REAIS do seu modelo treinado.
    REQUIRED_EPIS = {
        'helmet': False, # Flag para verificar se capacete foi encontrado
        'safety_vest': False # Flag para verificar se colete foi encontrado
    }
    
    # Processa apenas o primeiro resultado (para uma única imagem)
    if results:
        r = results[0] 
        # r.plot() já retorna a imagem com as caixas desenhadas
        annotated_frame_cv2 = r.plot() 
        annotated_image = Image.fromarray(cv2.cvtColor(annotated_frame_cv2, cv2.COLOR_BGR2RGB))

        for box in r.boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            box_coords = [int(x) for x in box.xyxy[0]] # [x1, y1, x2, y2]

            class_name = yolo_model.names[class_id] if class_id in yolo_model.names else f"Classe {class_id}"
            
            detections_info.append(
                f"Detectado: {class_name} (Confiança: {conf:.2f})"
            )
            
            # Atualiza flags para EPIs necessários
            if class_name == 'helmet': # Ajuste 'helmet' para o nome exato da classe do seu modelo
                REQUIRED_EPIS['helmet'] = True
            if class_name == 'safety_vest': # Ajuste 'safety_vest' para o nome exato da classe do seu modelo
                REQUIRED_EPIS['safety_vest'] = True

    # Lógica de alerta baseada nos EPIs esperados
    # ESTA LÓGICA DEVE SER AJUSTADA CONFORME SUAS REGRAS DE NEGÓCIO
    if not REQUIRED_EPIS['helmet']: # Se capacete não foi detectado
        alert_status = "🚨 Alerta: Capacete AUSENTE!"
        alert_triggered = True
    elif not REQUIRED_EPIS['safety_vest']: # Se colete não foi detectado (e capacete foi, se a regra for essa)
        alert_status = "⚠️ Atenção: Colete AUSENTE!"
        alert_triggered = True
    
    # Se nenhuma detecção específica de EPI foi feita, mas não há um alerta crítico
    if not alert_triggered and not detections_info:
        alert_status = "ℹ️ Nenhum EPI detectado (ou não aplicável)"

    return annotated_image, alert_status, detections_info, alert_triggered


# === CARICAMENTO DADOS PRINCIPAL ===
carica_nuova_cache = False
if st.button("🔄 Forçar atualização do FTP e reprocessar"): # Mudança no texto do botão
    st.cache_data.clear()
    # Limpa o cache de imagens local também para garantir download fresco
    for f in os.listdir(LOCAL_IMAGE_CACHE_DIR):
        os.remove(os.path.join(LOCAL_IMAGE_CACHE_DIR, f))
    carica_nuova_cache = True
    st.success("✅ Cache forçado do FTP e imagens locais limpas.")

if carica_nuova_cache:
    camere_ultime_foto = aggiorna_cache_da_ftp() # Esta função já faz o cache local da imagem
    salva_cache(camere_ultime_foto)
else:
    try:
        camere_ultime_foto = carica_cache()
        st.success("📦 Cache carregado corretamente.")
    except Exception as e:
        st.error(f"❌ Erro no carregamento cache: {e}. Tentando atualizar do FTP.")
        camere_ultime_foto = aggiorna_cache_da_ftp() # Tenta buscar do FTP se o cache falhar
        salva_cache(camere_ultime_foto) # Salva a nova cache


if not camere_ultime_foto:
    st.warning("⚠️ Nenhuma imagem encontrada ou erro no FTP/cache. Por favor, tente forçar a atualização.")
    st.stop()

# === ANÁLISE GERAL ===
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)
count_attive = 0
count_offline = 0
count_alertas_epi = 0

# Iterar sobre as câmeras para pré-processar o status e contar
# Isso é importante para que os filtros funcionem corretamente com os resultados do YOLO
processed_cam_data = {}
for cam, data in camere_ultime_foto.items():
    ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
    ts = brasil_tz.localize(ts)
    diff = now_brasil - ts
    ore = diff.total_seconds() / 3600
    giorni = int(diff.days)

    # Status de atividade da câmera (verde/vermelho)
    stato_operacional = "🟢" if ore < 24 else "🔴"

    image_pil = None
    if data.get("path_local") and os.path.exists(data["path_local"]):
        try:
            image_pil = Image.open(data["path_local"])
        except Exception as e:
            st.warning(f"Erro ao carregar imagem do cache local para {cam} (pre-processamento): {e}")
            image_pil = None
    
    # Processa a imagem com YOLO AQUI
    processed_image, epi_alert_status, epi_detections_list, is_alert_triggered = (
        process_image_with_yolo(image_pil) if image_pil else (None, "N/A", [], False)
    )

    if stato_operacional == "🟢":
        count_attive += 1
    else:
        count_offline += 1
    
    if is_alert_triggered:
        count_alertas_epi += 1

    processed_cam_data[cam] = {
        "img": processed_image, # Imagem já processada pelo YOLO
        "stato": stato_operacional,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "descrizione": f"{giorni} dia{'s' if dias != 1 else ''} atrás" if dias >= 1 else f"{int(ore)}h atrás",
        "epi_alert": epi_alert_status,
        "epi_detections": epi_detections_list,
        "is_alert_triggered": is_alert_triggered
    }

st.subheader(f"Total de câmeras: {len(processed_cam_data)} | ✅ Ativas: {count_attive} | 🔴 Offline: {count_offline} | 🚨 Alertas EPI: {count_alertas_epi}")

query = st.text_input("🔍 Buscar por nome da câmera ou cliente:", "").strip().lower()
filtro_offline = st.checkbox("🔴 Mostrar apenas câmeras offline (>24h)", value=False)
filtro_alerta_epi = st.checkbox("🚨 Mostrar apenas câmeras com alerta de EPI", value=False) # NOVO FILTRO
modo_compatto = st.checkbox("🖼️ Modo compacto (grade)", value=True)

# === FILTRAGEM E VISUALIZAÇÃO ===
risultati_filtrati = []
for cam, data in sorted(processed_cam_data.items()):
    if query and query not in cam.lower():
        continue

    if filtro_offline and data["stato"] == "🟢":
        continue

    if filtro_alerta_epi and not data["is_alert_triggered"]:
        continue
    
    risultati_filtrati.append(data)


if not risultati_filtrati:
    st.info("Nenhuma câmera corresponde aos filtros aplicados.")
else:
    # === RENDERING ===
    if modo_compatto:
        num_per_riga = 4
        for i in range(0, len(risultati_filtrati), num_per_riga):
            cols = st.columns(num_per_riga)
            for j, item in enumerate(risultati_filtrati[i:i+num_per_riga]):
                with cols[j]:
                    if item["img"]:
                        st.image(item["img"], use_container_width=True, caption=f"{item['epi_alert']}")
                    else:
                        st.warning("Imagem não disponível.")
                    st.markdown(f"**{item['stato']} {item['cam']}**")
                    st.caption(f"{item['timestamp']} • {item['descrizione']}")
                    if item["epi_detections"]:
                        with st.expander("Det. EPI"): # Expander compacto
                            for det in item["epi_detections"]:
                                st.markdown(f"- {det}")
    else:
        for item in risultati_filtrati:
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    if item["img"]:
                        st.image(item["img"], width=250, caption=f"{item['epi_alert']}")
                    else:
                        st.warning("Imagem não disponível.")
                with col2:
                    st.markdown(f"### {item['stato']} {item['epi_alert']} {item['cam']}")
                    st.write(f"Última atividade: `{item['timestamp']}`")
                    st.write(f"Inativa desde: `{item['descrizione']}`")
                    if item["epi_detections"]:
                        with st.expander("Detalhes da Detecção EPI"):
                            for det in item["epi_detections"]:
                                st.write(det)
            st.markdown("---")
