# ... (seu código existente) ...

# === CARREGAMENTO FTP ===
def aggiorna_cache_da_ftp():
    camere_ultime_foto = {}
    st.info("Iniciando atualização de cache do FTP...") # Debug: início da função
    ftp = None # Inicializa ftp como None
    try:
        st.info(f"Conectando ao FTP: {FTP_HOST} com usuário {FTP_USER}") # Debug: conexão
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        st.info(f"Login FTP bem-sucedido. Mudando para ROOT_FOLDER: {ROOT_FOLDER}") # Debug: login
        ftp.cwd(ROOT_FOLDER)
        
        # Obter a lista de diretórios (câmeras)
        try:
            camere = ftp.nlst()
            st.info(f"Encontrados {len(camere)} diretórios (câmeras).") # Debug: número de câmeras
        except Exception as e:
            st.error(f"Erro ao listar diretórios no ROOT_FOLDER: {e}")
            return {} # Retorna vazio se não conseguir listar diretórios

        for cam_folder in sorted(camere):
            cam_path = f"/{cam_folder}"
            nome_cam_trovado = None
            st.info(f"Processando pasta da câmera: {cam_folder}") # Debug: câmera atual

            try:
                # Tenta mudar para o diretório da câmera
                ftp.cwd(cam_path)
                st.info(f"Entrou na pasta: {cam_path}") # Debug: entrou na pasta
                
                # Procura o ano mais recente
                anni = sorted(ftp.nlst(), reverse=True)
                if not anni:
                    st.warning(f"Nenhum ano encontrado para a câmera {cam_folder}.")
                    continue
                
                for anno in anni:
                    st.info(f"Procurando no ano: {anno}")
                    try:
                        ftp.cwd(f"{cam_path}/{anno}")
                    except Exception as e:
                        st.warning(f"Não foi possível acessar a pasta do ano {anno} para {cam_folder}: {e}")
                        continue
                    
                    # Procura o mês mais recente
                    mesi = sorted(ftp.nlst(), reverse=True)
                    if not mesi:
                        st.warning(f"Nenhum mês encontrado para a câmera {cam_folder} no ano {anno}.")
                        continue

                    for mese in mesi:
                        st.info(f"Procurando no mês: {mese}")
                        try:
                            ftp.cwd(f"{cam_path}/{anno}/{mese}")
                        except Exception as e:
                            st.warning(f"Não foi possível acessar a pasta do mês {mese} para {cam_folder}/{anno}: {e}")
                            continue

                        # Procura o dia mais recente
                        giorni = sorted(ftp.nlst(), reverse=True)
                        if not giorni:
                            st.warning(f"Nenhum dia encontrado para a câmera {cam_folder} em {anno}/{mese}.")
                            continue

                        for giorno in giorni:
                            path_img_ftp = f"{cam_path}/{anno}/{mese}/{giorno}"
                            st.info(f"Procurando no dia: {giorno} em {path_img_ftp}")
                            try:
                                ftp.cwd(path_img_ftp)
                                files = sorted([f for f in ftp.nlst() if f.endswith(".jpg")], reverse=True)
                                if not files:
                                    st.warning(f"Nenhum arquivo JPG encontrado em {path_img_ftp}.")
                                    continue
                                ultima_img = files[0]
                                st.info(f"Última imagem encontrada para {cam_folder}: {ultima_img}")
                                nome_cam, timestamp = parse_nome_camera_e_data(ultima_img)
                                
                                if nome_cam and timestamp:
                                    st.info(f"Parseado: Câmera={nome_cam}, Timestamp={timestamp}")
                                    
                                    # Baixa e salva a imagem no cache local
                                    local_image_file = download_image_from_ftp_and_cache(ftp, path_img_ftp, ultima_img)
                                    if local_image_file:
                                        st.info(f"Imagem {ultima_img} baixada para cache local: {local_image_file}")
                                        camere_ultime_foto[nome_cam] = {
                                            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                            "path_ftp": path_img_ftp,
                                            "filename_ftp": ultima_img,
                                            "path_local": local_image_file
                                        }
                                        nome_cam_trovado = nome_cam
                                        break # Sai do loop de dias, pois encontrou a última imagem
                                    else:
                                        st.warning(f"Falha ao baixar {ultima_img} para o cache local.")
                                else:
                                    st.warning(f"Não foi possível parsear o nome da câmera ou timestamp para: {ultima_img}")
                            except Exception as e:
                                st.warning(f"Erro ao processar arquivos em {path_img_ftp}: {e}")
                                # Não continue aqui, tenta a próxima câmera ou volta no diretório.
                            finally:
                                # Garante que volta para a pasta pai da data para a próxima iteração do dia/mês/ano
                                try:
                                    ftp.cwd(cam_path) # Volta para a pasta raiz da câmera
                                except Exception as e:
                                    st.error(f"Erro ao retornar para a pasta raiz da câmera {cam_folder}: {e}")
                                    # Se não conseguir voltar, o estado do FTP está comprometido, melhor sair
                                    nome_cam_trovado = True # Sinaliza para sair de todos os loops
                                    break

                        if nome_cam_trovado:
                            break # Sai do loop de dias
                    if nome_cam_trovado:
                        break # Sai do loop de meses
                if nome_cam_trovado:
                    pass # Continua para a próxima câmera
                else:
                    st.warning(f"Nenhuma imagem válida encontrada para a câmera {cam_folder} após varrer todos os diretórios de data.")
            except Exception as e:
                st.error(f"Erro inesperado ao processar a câmera {cam_folder}: {e}")
            finally:
                # Tenta voltar para o ROOT_FOLDER antes da próxima iteração da câmera
                try:
                    ftp.cwd(ROOT_FOLDER)
                except Exception as e:
                    st.error(f"Erro fatal: Não foi possível retornar ao ROOT_FOLDER após processar {cam_folder}: {e}")
                    # Se não conseguir voltar ao root, o FTP pode estar num estado irrecuperável para este ciclo
                    break # Sai do loop principal de câmeras

        st.info("Varredura FTP concluída.") # Debug: fim da varredura
        
    except Exception as e:
        st.error(f"Erro crítico no FTP ou no processo: {e}")
    finally:
        if ftp: # Garante que ftp não é None antes de tentar fechar
            try:
                ftp.quit()
                st.info("Conexão FTP fechada.") # Debug: conexão fechada
            except Exception as e:
                st.warning(f"Erro ao fechar conexão FTP: {e}")
    
    st.info(f"Retornando {len(camere_ultime_foto)} câmeras.") # Debug: retorno da função
    return camere_ultime_foto

# ... (restante do código) ...
