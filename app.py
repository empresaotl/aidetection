import streamlit as st
from ftplib import FTP
from datetime import datetime
from PIL import Image
import io

# --- CONFIGURAÇÃO FTP ---
FTP_HOST = "ftp.drivehq.com"
FTP_USER = "otl.2020"
FTP_PASS = "otl.123"
BASE_FOLDER = "/REO_325"
ANO = "2025"
MES = "07"

# --- INÍCIO ---
st.title("🔧 Painel do Administrador - Câmeras Ativas")
st.info("📡 Conectando ao servidor FTP...")

try:
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    st.success("✅ Conexão FTP bem-sucedida")
except Exception as e:
    st.error(f"❌ Erro na conexão FTP: {e}")
    st.stop()

# --- LISTA TODAS AS CÂMERAS ---
try:
    ftp.cwd(BASE_FOLDER)
    cameras = ftp.nlst()  # Exemplo: ['REO_32', 'REO_323', ...]

    for cam in sorted(cameras):
        path_img = f"{BASE_FOLDER}/{cam}/{ANO}/{MES}"

        try:
            ftp.cwd(path_img)
            arquivos = ftp.nlst()
            imagens = sorted([f for f in arquivos if f.endswith(".jpg")], reverse=True)

            if not imagens:
                st.warning(f"🔴 {cam} - Nenhuma imagem encontrada.")
                continue

            ultima_imagem = imagens[0]
            nome_sem_extensao = ultima_imagem.replace(".jpg", "")
            try:
                timestamp = datetime.strptime(nome_sem_extensao, "%Y-%m-%d_%H-%M-%S")
            except:
                st.warning(f"📛 {cam} - Nome inválido: {ultima_imagem}")
                continue

            horas_passadas = (datetime.now() - timestamp).total_seconds() // 3600
            status = "🟢" if horas_passadas < 24 else "🔴"

            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {ultima_imagem}", buffer.write)
            buffer.seek(0)
            imagem = Image.open(buffer)

            with st.container():
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(imagem, caption=ultima_imagem, width=200)
                with col2:
                    st.markdown(f"### {status} {cam}")
                    st.write(f"🕑 Última imagem: `{timestamp.strftime('%Y-%m-%d %H:%M:%S')}`")
                    st.write(f"⏱️ Tempo desde a última imagem: `{int(horas_passadas)}h`")

            st.markdown("---")

        except Exception as e:
            st.error(f"⚠️ Erro com a câmera {cam}: {e}")

except Exception as e:
    st.error(f"❌ Erro na listagem das câmeras: {e}")

ftp.quit()
