Você tem razão\! Peço desculpas. Ao refatorar o código, algumas das informações de status e descrição de tempo podem ter sido perdidas ou o acesso a elas pode ter mudado. Analisei o código novamente para garantir que as informações de tempo de atividade e inatividade sejam exibidas corretamente.

A principal causa do problema que você mencionou é que, na lógica da "Renderização", a variável `item['descrição']` pode não estar sendo exibida ou formatada da mesma forma que antes.

Além disso, ajustei a forma como as informações são passadas para `processed_cam_data` para garantir que `'descrição'` e `'stato'` estejam sempre presentes e consistentes.

Aqui está o código `app.py` completo e atualizado, com a correção para a exibição das informações de tempo de atividade/inatividade:

```python
import streamlit as st
from ftplib import FTP, error_perm, error_temp
from datetime import datetime, timedelta
import pytz
from PIL import Image, ImageDraw, ImageFont
import io
import re
import json
import os
from streamlit_autorefresh import st_autorefresh
import numpy as np
import cv2
from ultralytics import YOLO

# === CONFIGURAÇÕES ===
FTP_HOST = "66.220.9.45"
FTP_USER = "nicebr"
FTP_PASS = "otl.123"
ROOT_FOLDER = "/"
CACHE_FILE = "cache_ultime_foto.json"
TTL_CACHE = 300  # 5 minutos
LOCAL_IMAGE_CACHE_DIR = "cache_imagens_locais" # Diretório para cache local de imagens
YOLO_MODEL_PATH = "yolov8n.pt" # Caminho para o seu modelo YOLOv8

# Garante que o diretório de cache local exista
os.makedirs(LOCAL_IMAGE_CACHE_DIR, exist_ok=True)

# === ATUALIZAÇÃO AUTOMÁTICA ===
st_autorefresh(interval=TTL_CACHE * 1000, key="aggiorna")

# === CONFIGURAÇÃO DA PÁGINA ===
st.set_page_config(page_title="Dashboard Telecâmeras", layout="wide")
ora_brasile = datetime.now(pytz.timezone('America/Sao_Paulo'))
st.title("📸 Dashboard - Últimas Imagens por Telecâmera")
st.caption(f"🕒 Horário de referência (Brasília): {ora_brasile.strftime('%Y-%m-%d %H:%M:%S')}")

# === FUNÇÕES DE CACHE ===
def salva_cache(data):
    """Salva os metadados das últimas fotos em um arquivo JSON."""
    cache_dir = os.path.dirname(CACHE_FILE)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, default=str, indent=2)
        st.success(f"Cache de metadados salvo em {CACHE_FILE}.")
    except Exception as e:
        st.error(f"Erro ao salvar o cache de metadados: {e}")

def carica_cache():
    """Carrega os metadados das últimas fotos do arquivo JSON."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read()
                if not content.strip(): # Se o arquivo estiver vazio ou só com espaços em branco
                    st.warning("Arquivo de cache de metadados vazio ou inválido. Forçando atualização do FTP.")
                    return {} # Retorna vazio para forçar o recarregamento do FTP
                return json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"❌ Erro ao decodificar o cache JSON '{CACHE_FILE}': {e}. O arquivo pode estar corrompido. Forçando atualização do FTP.")
            try:
                os.remove(CACHE_FILE)
                st.info("Arquivo de cache de metadados corrompido removido.")
            except Exception as remove_e:
                st.warning(f"Não foi possível remover o arquivo de cache corrompido: {remove_e}")
            return {} # Retorna vazio para que o fluxo principal tente atualizar do FTP
        except Exception as e:
            st.error(f"❌ Erro inesperado ao carregar o cache de metadados: {e}. Forçando atualização do FTP.")
            return {}
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
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            st.info(f"Imagem '{filename}' já existe no cache local. Usando a versão em cache.")
            return local_path

        st.info(f"Baixando '{filename}' do FTP para cache local...")
        
        buffer = io.BytesIO()
        ftp_session.retrbinary(f"RETR {filename}", buffer.write)
        buffer.seek(0)
        
        with open(local_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        st.success(f"Imagem '{filename}' baixada e salva em {local_path}.")
        return local_path
    except Exception as e:
        st.warning(f"Erro ao baixar ou salvar '{filename}' do FTP para cache local: {e}")
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                st.info(f"Arquivo parcial '{local_path}' removido.")
            except Exception as remove_e:
                st.warning(f"Não foi possível remover o arquivo parcial: {remove_e}")
        return None

# === PARSER ===
def parse_nome_camera_e_data(nome_file):
    """Extrai o nome da câmera e o timestamp do nome do arquivo."""
    try:
        match = re.match(r"(.+?)_00_(\d{14})\.jpg", nome_file)
        if match:
            nome_camera = match.group(1).strip()
            timestamp_str = match.group(2)
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            return nome_camera, timestamp
    except Exception as e:
        st.error(f"Erro ao parsear nome de arquivo '{nome_file}': {e}")
        return None, None
    return None, None

# === INICIALIZAÇÃO DO MODELO YOLO ===
@st.cache_resource
def load_yolo_model():
    """Carrega o modelo YOLOv8."""
    try:
        model = YOLO(YOLO_MODEL_PATH)
        st.success(f"Modelo YOLO carregado com sucesso de '{YOLO_MODEL_PATH}'.")
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

    if pil_image is None:
        return None, "Imagem inválida para YOLO", [], False

    img_np = np.array(pil_image)
    img_cv2 = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    detections_info = []
    alert_status = "✅ OK"
    alert_triggered = False

    try:
        results = yolo_model(img_cv2, verbose=False, conf=0.25) 

        annotated_image = pil_image
        
        REQUIRED_EPIS = {
            'helmet': False,
            'safety_vest': False
        }
        
        if results:
            r = results[0] 
            annotated_frame_cv2 = r.plot() 
            annotated_image = Image.fromarray(cv2.cvtColor(annotated_frame_cv2, cv2.COLOR_BGR2RGB))

            for box in r.boxes:
                class_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                class_name = yolo_model.names.get(class_id, f"Classe {class_id}")
                
                detections_info.append(
                    f"Detectado: {class_name} (Confiança: {conf:.2f})"
                )
                
                if class_name == 'helmet':
                    REQUIRED_EPIS['helmet'] = True
                if class_name == 'safety_vest':
                    REQUIRED_EPIS['safety_vest'] = True

        if not REQUIRED_EPIS['helmet']:
            alert_status = "🚨 Alerta: Capacete AUSENTE!"
            alert_triggered = True
        elif not REQUIRED_EPIS['safety_vest']:
            alert_status = "⚠️ Atenção: Colete AUSENTE!"
            alert_triggered = True
        
        if not alert_triggered and not detections_info:
            alert_status = "ℹ️ Nenhum EPI detectado (ou não aplicável)"

    except Exception as e:
        st.error(f"Erro durante o processamento YOLO: {e}")
        return pil_image, "Erro no processamento YOLO", [], True

    return annotated_image, alert_status, detections_info, alert_triggered

# === CARREGAMENTO FTP ===
def aggiorna_cache_da_ftp():
    """
    Atualiza o cache de metadados das últimas fotos e baixa as imagens
    mais recentes para o cache local via FTP.
    """
    camere_ultime_foto = {}
    st.info("Iniciando atualização de cache do FTP...")
    ftp = None
    try:
        st.info(f"Conectando ao FTP: {FTP_HOST} com usuário {FTP_USER}")
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        st.info(f"Login FTP bem-sucedido. Mudando para ROOT_FOLDER: {ROOT_FOLDER}")
        ftp.cwd(ROOT_FOLDER)
        
        try:
            camere = ftp.nlst()
            st.info(f"Encontrados {len(camere)} diretórios (câmeras).")
        except error_perm as e:
            st.error(f"Erro de permissão FTP ao listar diretórios no ROOT_FOLDER: {e}. Verifique se o usuário tem acesso ao caminho raíz ('{ROOT_FOLDER}').")
            return {}
        except Exception as e:
            st.error(f"Erro inesperado ao listar diretórios no ROOT_FOLDER: {e}. Verifique a conectividade ou o caminho.")
            return {}

        for cam_folder in sorted(camere):
            if '.' in cam_folder: 
                st.info(f"Pulando entrada '{cam_folder}' no ROOT_FOLDER (parece ser um arquivo).")
                continue

            cam_path = f"/{cam_folder}"
            nome_cam_trovado = None
            st.info(f"Processando pasta da câmera: {cam_folder}")

            try:
                # Salva o diretório atual do FTP antes de entrar na pasta da câmera
                # Isso é crucial para voltar ao ROOT_FOLDER de forma confiável
                original_root_for_cam_processing = ftp.pwd() 
                ftp.cwd(cam_path)
                st.info(f"Entrou na pasta: {cam_path}")
                
                anni = sorted(ftp.nlst(), reverse=True)
                if not anni:
                    st.warning(f"Nenhum ano encontrado para a câmera {cam_folder}. Pulando.")
                    ftp.cwd(original_root_for_cam_processing) # Volta ao diretório original
                    continue
                
                found_image_for_cam = False 
                for anno in anni:
                    if not anno.isdigit() or len(anno) != 4:
                        st.warning(f"Entrada '{anno}' não parece ser um diretório de ano válido para {cam_folder}. Pulando.")
                        continue

                    st.info(f"Procurando no ano: {anno} para {cam_folder}")
                    current_anno_path = f"{cam_path}/{anno}" # Guarda o caminho do ano
                    try:
                        ftp.cwd(current_anno_path)
                    except (error_perm, error_temp) as e:
                        st.warning(f"Erro FTP ao acessar pasta do ano '{anno}' para {cam_folder}: {e}. Pulando este ano.")
                        ftp.cwd(cam_path) # Tenta voltar para a pasta da câmera
                        continue
                    except Exception as e:
                        st.warning(f"Não foi possível acessar a pasta do ano {anno} para {cam_folder}: {e}. Pulando este ano.")
                        ftp.cwd(cam_path) # Tenta voltar para a pasta da câmera
                        continue
                    
                    mesi = sorted(ftp.nlst(), reverse=True)
                    if not mesi:
                        st.warning(f"Nenhum mês encontrado para a câmera {cam_folder} no ano {anno}. Pulando.")
                        ftp.cwd(current_anno_path) # Tenta voltar para a pasta do ano
                        continue

                    for mese in mesi:
                        if not mese.isdigit() or not (1 <= int(mese) <= 12):
                            st.warning(f"Entrada '{mese}' não parece ser um diretório de mês válido para {cam_folder}/{anno}. Pulando.")
                            continue

                        st.info(f"Procurando no mês: {mese} para {cam_folder}/{anno}")
                        current_mese_path = f"{cam_path}/{anno}/{mese}" # Guarda o caminho do mês
                        try:
                            ftp.cwd(current_mese_path)
                        except (error_perm, error_temp) as e:
                            st.warning(f"Erro FTP ao acessar pasta do mês '{mese}' para {cam_folder}/{anno}: {e}. Pulando este mês.")
                            ftp.cwd(current_anno_path) # Tenta voltar para a pasta do ano
                            continue
                        except Exception as e:
                            st.warning(f"Não foi possível acessar a pasta do mês {mese} para {cam_folder}/{anno}: {e}. Pulando este mês.")
                            ftp.cwd(current_anno_path) # Tenta voltar para a pasta do ano
                            continue

                        giorni = sorted(ftp.nlst(), reverse=True)
                        if not giorni:
                            st.warning(f"Nenhum dia encontrado para a câmera {cam_folder} em {anno}/{mese}. Pulando.")
                            ftp.cwd(current_mese_path) # Tenta voltar para a pasta do mês
                            continue

                        for giorno in giorni:
                            if not giorno.isdigit() or not (1 <= int(giorno) <= 31):
                                st.warning(f"Entrada '{giorno}' não parece ser um diretório de dia válido para {cam_folder}/{anno}/{mese}. Pulando.")
                                continue

                            path_img_ftp = f"{cam_path}/{anno}/{mese}/{giorno}"
                            st.info(f"Procurando em: {path_img_ftp}")
                            try:
                                # Muda para o diretório do dia para listar arquivos
                                ftp.cwd(path_img_ftp) 
                                files = sorted([f for f in ftp.nlst() if f.endswith(".jpg")], reverse=True)
                                if not files:
                                    st.warning(f"Nenhum arquivo JPG encontrado em {path_img_ftp}. Pulando.")
                                    ftp.cwd(current_mese_path) # Volta para a pasta do mês
                                    continue
                                ultima_img = files[0]
                                st.info(f"Última imagem encontrada para {cam_folder}: {ultima_img}")
                                nome_cam, timestamp = parse_nome_camera_e_data(ultima_img)
                                
                                if nome_cam and timestamp:
                                    st.info(f"Parseado: Câmera={nome_cam}, Timestamp={timestamp}")
                                    
                                    local_image_file = download_image_from_ftp_and_cache(ftp, path_img_ftp, ultima_img)
                                    if local_image_file:
                                        camere_ultime_foto[nome_cam] = {
                                            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                            "path_ftp": path_img_ftp,
                                            "filename_ftp": ultima_img,
                                            "path_local": local_image_file
                                        }
                                        nome_cam_trovado = nome_cam
                                        found_image_for_cam = True
                                        break # Sai do loop de dias, pois encontrou a última imagem
                                    else:
                                        st.warning(f"Falha ao baixar {ultima_img} para o cache local. Esta imagem não será exibida.")
                                else:
                                    st.warning(f"Não foi possível parsear o nome da câmera ou timestamp para: {ultima_img}. Pulando.")
                            except (error_perm, error_temp) as e:
                                st.warning(f"Erro FTP ao processar arquivos em {path_img_ftp}: {e}. Pulando este diretório.")
                                ftp.cwd(current_mese_path) # Tenta voltar para a pasta do mês
                            except Exception as e:
                                st.warning(f"Erro inesperado ao processar arquivos em {path_img_ftp}: {e}. Pulando este diretório.")
                                ftp.cwd(current_mese_path) # Tenta voltar para a pasta do mês
                            finally:
                                # Garantir que o CWD esteja de volta no diretório do mês
                                try:
                                    ftp.cwd(current_mese_path) 
                                except Exception as e:
                                    st.error(f"Erro ao retornar para a pasta do mês '{mese}': {e}. Tentando retornar ao diretório da câmera.")
                                    ftp.cwd(cam_path) # Tenta voltar para a raiz da câmera
                                    break # Sai do loop de dias se não conseguir voltar para o mês

                        if found_image_for_cam:
                            break # Sai do loop de meses
                    if found_image_for_cam:
                        break # Sai do loop de anos
                
                if not found_image_for_cam:
                    st.warning(f"Nenhuma imagem válida encontrada para a câmera {cam_folder} após varrer todos os diretórios de data.")
                
            except Exception as e:
                st.error(f"Erro inesperado ao processar a câmera {cam_folder}: {e}. Pulando esta câmera.")
            finally:
                # Sempre tenta voltar ao ROOT_FOLDER global para a próxima câmera
                try:
                    ftp.cwd(ROOT_FOLDER)
                except Exception as e:
                    st.error(f"Erro fatal: Não foi possível retornar ao ROOT_FOLDER ('{ROOT_FOLDER}') após processar {cam_folder}: {e}. A conexão FTP pode estar instável. Interrompendo varredura.")
                    break # Sai do loop principal de câmeras (fatal)

        st.info("Varredura FTP concluída.")
        
    except error_perm as e:
        st.error(f"Erro de permissão FTP geral: {e}. Verifique as credenciais ou permissões de diretório.")
    except Exception as e:
        st.error(f"Erro crítico na conexão ou operação FTP: {e}. Verifique as credenciais ou a conectividade.")
    finally:
        if ftp:
            try:
                ftp.quit()
                st.info("Conexão FTP fechada.")
            except Exception as e:
                st.warning(f"Erro ao fechar conexão FTP: {e}")
    
    st.info(f"Retornando {len(camere_ultime_foto)} câmeras processadas com sucesso.")
    return camere_ultime_foto

# === CARREGAMENTO DE DADOS PRINCIPAL ===
carica_nuova_cache = False
if st.button("🔄 Forçar atualização do FTP e reprocessar"):
    st.cache_data.clear()
    
    for f in os.listdir(LOCAL_IMAGE_CACHE_DIR):
        try:
            os.remove(os.path.join(LOCAL_IMAGE_CACHE_DIR, f))
        except Exception as e:
            st.warning(f"Não foi possível remover arquivo de cache local {f}: {e}")
    st.info("Cache de imagens locais limpo.")
    
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
            st.info("Arquivo de cache de metadados principal removido para forçar recriação.")
        except Exception as e:
            st.warning(f"Não foi possível remover o arquivo de cache principal: {e}")

    carica_nuova_cache = True
    st.success("✅ Cache forçado do FTP e caches locais limpos. Rebuscando dados.")

if carica_nuova_cache:
    camere_ultime_foto = aggiorna_cache_da_ftp()
    salva_cache(camere_ultime_foto)
else:
    camere_ultime_foto = carica_cache() 
    if not camere_ultime_foto:
        st.warning("Cache vazio ou inválido. Tentando atualizar do FTP...")
        camere_ultime_foto = aggiorna_cache_da_ftp()
        salva_cache(camere_ultime_foto)
    else:
        st.success("📦 Cache de metadados carregado corretamente.")


if not camere_ultime_foto:
    st.warning("⚠️ Nenhuma imagem encontrada ou erro no FTP/cache. Por favor, tente forçar a atualização.")
    st.stop()

# === ANÁLISE GERAL E PRÉ-PROCESSAMENTO ===
brasil_tz = pytz.timezone('America/Sao_Paulo')
now_brasil = datetime.now(brasil_tz)
count_attive = 0
count_offline = 0
count_alertas_epi = 0

processed_cam_data = {}
for cam, data in camere_ultime_foto.items():
    ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
    ts = brasil_tz.localize(ts)
    diff = now_brasil - ts
    # Use as variáveis 'ore' e 'giorni' que já são calculadas
    ore = diff.total_seconds() / 3600
    giorni = int(diff.days)

    stato_operacional = "🟢" if ore < 24 else "🔴"
    # Calcula a descrição com base nos dias/horas de inatividade
    if giorni >= 1:
        descrizione_atividade = f"{giorni} dia{'s' if giorni != 1 else ''} atrás"
    else:
        descrizione_atividade = f"{int(ore)}h atrás"


    image_pil = None
    if data.get("path_local") and os.path.exists(data["path_local"]):
        try:
            image_pil = Image.open(data["path_local"])
        except Exception as e:
            st.warning(f"Erro ao carregar imagem do cache local para {cam} (pré-processamento): {e}")
            image_pil = None
    else:
        st.warning(f"Caminho da imagem local não encontrado ou arquivo ausente para {cam}: {data.get('path_local', 'N/A')}")
    
    processed_image, epi_alert_status, epi_detections_list, is_alert_triggered = (
        process_image_with_yolo(image_pil) if image_pil else (None, "Imagem não disponível", [], False)
    )

    if stato_operacional == "🟢":
        count_attive += 1
    else:
        count_offline += 1
    
    if is_alert_triggered:
        count_alertas_epi += 1

    processed_cam_data[cam] = {
        "img": processed_image,
        "stato": stato_operacional, # Passa o status de operação da câmera
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "descrição": descrizione_atividade, # Passa a descrição de atividade
        "epi_alert": epi_alert_status,
        "epi_detections": epi_detections_list,
        "is_alert_triggered": is_alert_triggered,
        "cam": cam # Garante que 'cam' esteja sempre presente no dicionário
    }

st.subheader(f"Total de câmeras: {len(processed_cam_data)} | ✅ Ativas: {count_attive} | 🔴 Offline: {count_offline} | 🚨 Alertas EPI: {count_alertas_epi}")

query = st.text_input("🔍 Buscar por nome da câmera ou cliente:", "").strip().lower()
filtro_offline = st.checkbox("🔴 Mostrar apenas câmeras offline (>24h)", value=False)
filtro_alerta_epi = st.checkbox("🚨 Mostrar apenas câmeras com alerta de EPI", value=False)
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
    # === RENDERIZAÇÃO ===
    if modo_compatto:
        num_per_riga = 4
        for i in range(0, len(risultati_filtrati), num_per_riga):
            cols = st.columns(num_per_riga)
            for j, item in enumerate(risultati_filtrati[i:i+num_per_riga]):
                with cols[j]:
                    if item["img"] is not None:
                        st.image(item["img"], use_container_width=True, caption=f"{item['epi_alert']}")
                    else:
                        st.warning("Imagem não disponível.")
                    st.markdown(f"**{item['stato']} {item['cam']}**")
                    # **Correção aqui:** Garante que 'descrição' é acessada corretamente
                    st.caption(f"{item['timestamp']} • {item['descrição']}") 
                    if item["epi_detections"]:
                        with st.expander("Det. EPI"):
                            for det in item["epi_detections"]:
                                st.markdown(f"- {det}")
    else:
        for item in risultati_filtrati:
            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    if item["img"] is not None:
                        st.image(item["img"], width=250, caption=f"{item['epi_alert']}")
                    else:
                        st.warning("Imagem não disponível.")
                with col2:
                    st.markdown(f"### {item['stato']} {item['epi_alert']} {item['cam']}")
                    st.write(f"Última atividade: `{item['timestamp']}`")
                    # **Correção aqui:** Garante que 'descrição' é acessada corretamente
                    st.write(f"Inativa desde: `{item['descrição']}`") 
                    if item["epi_detections"]:
                        with st.expander("Detalhes da Detecção EPI"):
                            for det in item["epi_detections"]:
                                st.write(det)
            st.markdown("---")
```
