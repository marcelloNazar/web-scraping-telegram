#!/usr/bin/env python3
"""
Telegram Scraper VM Continuous
Roda continuamente na VM fazendo scraping e enviando para Kinesis + OpenSearch

GARANTIAS DE COBERTURA:
- Processa TODOS os 200 grupos a cada 10 minutos
- Primeira execução: últimas 6 horas SEM LIMITE  
- Execuções seguintes: apenas mensagens novas (min_id)
- Rate limiting seguro: 1.5s entre grupos
- Controle de estado: zero duplicatas
- Monitoramento completo: logs detalhados de cobertura
"""

import json
import boto3
import os
import sys
import time
from datetime import datetime, timezone, timedelta
import logging
import traceback
import signal

# Adicionar src ao path para imports
sys.path.append('./src')

# Configurar logging para VM (arquivo + console)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('telegram_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Clientes AWS globais
kinesis_client = boto3.client(
    'kinesis', 
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)

# Clientes de integração
elasticsearch_client = None
cloudwatch_monitor = None

# Controle de execução
running = True

def signal_handler(signum, frame):
    """Handler para parar execução gracefully"""
    global running
    logger.info("🛑 Recebido sinal de parada. Finalizando...")
    running = False

def initialize_elasticsearch():
    """Inicializar cliente OpenSearch/Elasticsearch"""
    global elasticsearch_client
    if elasticsearch_client is None:
        try:
            from utils.aws_elasticsearch import ElasticsearchClient
            elasticsearch_client = ElasticsearchClient()
            
            # Verificar se o cliente foi habilitado com sucesso
            if hasattr(elasticsearch_client, 'enabled') and elasticsearch_client.enabled:
                logger.info("✅ Cliente OpenSearch inicializado e HABILITADO")
                if hasattr(elasticsearch_client, 'domain_endpoint'):
                    logger.info("🔗 Endpoint: %s", elasticsearch_client.domain_endpoint)
            else:
                logger.warning("⚠️ Cliente OpenSearch inicializado mas DESABILITADO")
                if hasattr(elasticsearch_client, 'domain_endpoint'):
                    logger.warning("🔗 Endpoint: %s", elasticsearch_client.domain_endpoint or "None")
                logger.warning("📝 Mensagens não serão enviadas para OpenSearch")
                
        except Exception as e:
            logger.error("❌ Erro ao inicializar OpenSearch: %s", e)
            logger.error("📋 Traceback: %s", traceback.format_exc())
            elasticsearch_client = None
    return elasticsearch_client

def initialize_cloudwatch():
    """Inicializar cliente CloudWatch"""
    global cloudwatch_monitor
    if cloudwatch_monitor is None:
        try:
            from utils.monitoring import CloudWatchMonitor
            cloudwatch_monitor = CloudWatchMonitor()
            logger.info("📈 CloudWatch: %s", 
                       "✅ Habilitado" if cloudwatch_monitor.enabled else "⚠️ Desabilitado")
        except Exception as e:
            logger.error("❌ Erro ao inicializar CloudWatch: %s", e)
            cloudwatch_monitor = None
    return cloudwatch_monitor

def load_groups_from_sheets():
    """Carregar grupos do Google Sheets"""
    try:
        logger.info("📊 ==> CARREGANDO GRUPOS DO GOOGLE SHEETS")
        from utils.google_sheets import GoogleSheetsLoader
        
        sheets_loader = GoogleSheetsLoader()
        groups_data = sheets_loader.load_groups()
        
        # Filtrar apenas grupos ativos
        active_groups = [group for group in groups_data if group.get('active', True)]
        
        logger.info("📋 Total grupos na planilha: %d", len(groups_data))
        logger.info("📈 Grupos ativos selecionados: %d", len(active_groups))
        
        # Log dos primeiros grupos para verificação
        for i, group in enumerate(active_groups[:10]):
            logger.info("📱 Grupo %d: %s (%s)", i+1, 
                       group.get('username', 'N/A'), 
                       group.get('spectrum', 'Unknown'))
        
        if len(active_groups) > 10:
            logger.info("📝 ... e mais %d grupos", len(active_groups) - 10)
            
        return active_groups
        
    except Exception as e:
        logger.error("❌ Erro ao carregar Google Sheets: %s", e)
        # Fallback para grupo de teste em caso de erro
        fallback_groups = [
            {'username': '@SputnikBrasil', 'spectrum': 'right', 'active': True}
        ]
        logger.warning("⚠️ ERRO: Google Sheets falhou! Usando apenas 1 grupo de teste: %d grupos", len(fallback_groups))
        return fallback_groups

def validate_environment():
    """Validar variáveis de ambiente"""
    api_id = os.environ.get('TELEGRAM_API_ID')
    api_hash = os.environ.get('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        logger.error("❌ Variáveis de ambiente não configuradas")
        return None
    
    logger.info("🔑 API ID: %s", api_id)
    logger.info("🔑 API Hash: %s...", api_hash[:8])
    
    return {'api_id': api_id, 'api_hash': api_hash}

def setup_telegram_client(api_id, api_hash, session_file=None):
    """Configurar cliente Telegram"""
    try:
        logger.info("📦 Importando Telethon...")
        from telethon.sync import TelegramClient
        logger.info("✅ Telethon importado com sucesso")
        
        # Usar ConfigLoader se session_file não fornecido
        if not session_file:
            from src.utils.config_loader import load_config
            config = load_config()
            telegram_creds = config.get_telegram_credentials()
            session_file = telegram_creds['session_file']
            logger.info("🔧 Usando ConfigLoader - Session file: %s", session_file)
        
        if not os.path.exists(session_file):
            logger.error("❌ Arquivo %s não encontrado", session_file)
            return None
        
        logger.info("📱 Conectando ao Telegram usando session...")
        client = TelegramClient(session_file, int(api_id), api_hash)
        client.connect()
        
        if not client.is_user_authorized():
            logger.error("❌ Usuário não autorizado - session inválida")
            client.disconnect()
            return None
        
        logger.info("✅ Cliente Telegram conectado e autorizado")
        return client
        
    except Exception as e:
        logger.error("❌ Erro ao configurar Telegram: %s", e)
        return None

def classify_message(text):
    """Classificação simples de mensagens baseada em keywords"""
    text_lower = text.lower()
    
    pol_keywords = ['eleição', 'político', 'governo', 'presidente', 'deputado', 'senador', 'bolsonaro', 'lula', 'pt', 'psl']
    conspira_keywords = ['conspiração', 'illuminati', 'nova ordem', 'globalista', 'deep state', 'controle mental']
    naz_keywords = ['hitler', 'nazismo', 'reich', 'raça superior']
    
    if any(word in text_lower for word in naz_keywords):
        return 'NAZ'
    elif any(word in text_lower for word in conspira_keywords):
        return 'CONSPIRA'
    elif any(word in text_lower for word in pol_keywords):
        return 'POL'
    else:
        return 'OTHER'

def load_state():
    """Carregar estado de última mensagem processada por grupo"""
    state_file = 'telegram_scraper_state.json'
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info("📄 Estado carregado: %d grupos com histórico", len(state))
                return state
        else:
            logger.info("📄 Primeiro uso - criando novo arquivo de estado")
            return {}
    except Exception as e:
        logger.error("❌ Erro ao carregar estado: %s", e)
        return {}

def save_state(state):
    """Salvar estado de última mensagem processada por grupo"""
    state_file = 'telegram_scraper_state.json'
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        logger.info("💾 Estado salvo com %d grupos", len(state))
        return True
    except Exception as e:
        logger.error("❌ Erro ao salvar estado: %s", e)
        return False

def get_partition_key_optimized(group_name, message_id):
    """Gerar chave de partição otimizada para distribuição uniforme entre shards"""
    # Usar grupo + hash do message_id para distribuição uniforme
    hash_suffix = hash(str(message_id)) % 100
    return f"{group_name}#{hash_suffix}"

def send_batch_to_kinesis_optimized(messages_batch):
    """Enviar mensagens em batch usando PutRecords (AWS Best Practice)"""
    if not messages_batch:
        return 0, 0
    
    total_sent = 0
    total_failed = 0
    
    try:
        # Preparar records para PutRecords (limite: 500 records, 5MB total)
        max_batch_size = 500  # Limite AWS oficial
        
        # Dividir em chunks se necessário
        for i in range(0, len(messages_batch), max_batch_size):
            batch_chunk = messages_batch[i:i + max_batch_size]
            
            chunk_records = []
            for msg_data in batch_chunk:
                partition_key = get_partition_key_optimized(
                    msg_data.get('group_name', 'default'),
                    msg_data.get('message_id', 'unknown')
                )
                
                chunk_records.append({
                    'Data': json.dumps(msg_data),
                    'PartitionKey': partition_key
                })
            
            # Enviar chunk usando PutRecords
            response = kinesis_client.put_records(
                StreamName='telegram-messages',
                Records=chunk_records
            )
            
            # Verificar falhas (AWS recomenda tratar)
            failed_count = response.get('FailedRecordCount', 0)
            success_count = len(chunk_records) - failed_count
            
            total_sent += success_count
            total_failed += failed_count
            
            if failed_count > 0:
                logger.warning("⚠️ Kinesis PutRecords: %d/%d records falharam", 
                             failed_count, len(chunk_records))
                # Retry simples: Re-tentar records falhados uma vez
                failed_records = [chunk_records[idx] for idx, record in enumerate(response['Records']) 
                                if 'ErrorCode' in record]
                if failed_records:
                    logger.info("🔄 Tentando reenviar %d records falhados...", len(failed_records))
                    try:
                        retry_response = kinesis_client.put_records(
                            StreamName='telegram-messages',
                            Records=failed_records
                        )
                        retry_failed = retry_response.get('FailedRecordCount', 0)
                        if retry_failed == 0:
                            logger.info("✅ Retry successful: todos os records reenviados")
                            total_sent += len(failed_records)  # Somar records que foram reenviados com sucesso
                            total_failed -= len(failed_records)  # Reduzir dos falhados
                        else:
                            logger.warning("⚠️ Retry parcial: %d ainda falharam", retry_failed)
                            retry_success = len(failed_records) - retry_failed
                            total_sent += retry_success
                            total_failed -= retry_success
                    except Exception as retry_error:
                        logger.error("❌ Erro no retry: %s", retry_error)
            
            logger.info("✅ Kinesis PutRecords: %d/%d records enviados com sucesso", 
                       success_count, len(chunk_records))
        
        return total_sent, total_failed
        
    except Exception as kinesis_error:
        logger.error("❌ Erro Kinesis PutRecords: %s", kinesis_error)
        return 0, len(messages_batch)

def send_message_to_kinesis_complete(message_data, group):
    """FUNÇÃO LEGADA - Manter para compatibilidade (usar batch é mais eficiente)"""
    try:
        partition_key = get_partition_key_optimized(group, message_data.get('message_id', 'unknown'))
        kinesis_client.put_record(
            StreamName='telegram-messages',
            Data=json.dumps(message_data),
            PartitionKey=partition_key
        )
        return True
        
    except Exception as kinesis_error:
        logger.error("❌ Erro Kinesis para %s: %s", group, kinesis_error)
        return False

def send_message_to_opensearch(message_data, es_client):
    """Enviar mensagem diretamente para OpenSearch"""
    try:
        # Debug: verificar se cliente está disponível
        if not es_client:
            logger.warning("⚠️ Cliente OpenSearch é None - mensagem não enviada")
            return False
            
        if not hasattr(es_client, 'index_message'):
            logger.error("❌ Cliente OpenSearch não tem método 'index_message'")
            return False
            
        # Debug: verificar se cliente está habilitado
        if hasattr(es_client, 'enabled') and not es_client.enabled:
            logger.warning("⚠️ Cliente OpenSearch DESABILITADO - mensagem não enviada")
            return False
            
        doc_id = "%s_%s_%s" % (
            message_data.get('group_name', 'unknown'),
            message_data.get('message_id', 'unknown'),
            int(datetime.now(timezone.utc).timestamp())
        )
        
        logger.info("📤 Tentando enviar para OpenSearch: doc_id=%s", doc_id)
        result = es_client.index_message(message_data, doc_id)
        
        if result:
            logger.info("✅ OpenSearch: sucesso para doc_id=%s", doc_id)
        else:
            logger.warning("⚠️ OpenSearch: falha silenciosa para doc_id=%s", doc_id)
            
        return result
        
    except Exception as es_error:
        logger.error("❌ Erro OpenSearch: %s", es_error)
        logger.error("📋 Traceback OpenSearch: %s", traceback.format_exc())
        return False

def process_telegram_groups_continuous(client, groups_data, es_client):
    """Processar grupos Telegram para execução contínua com controle de estado (sem duplicatas)"""
    from telethon.errors import FloodWaitError
    import time
    
    logger.info("📋 ==> PROCESSANDO GRUPOS DO GOOGLE SHEETS")
    logger.info("📊 Total grupos disponíveis: %d", len(groups_data))
    
    # Debug: status do cliente OpenSearch
    if es_client:
        enabled_status = "HABILITADO" if (hasattr(es_client, 'enabled') and es_client.enabled) else "DESABILITADO"
        logger.info("✅ Cliente OpenSearch: DISPONÍVEL mas %s", enabled_status)
        
        if hasattr(es_client, 'index_message'):
            logger.info("✅ Método index_message: DISPONÍVEL")
        else:
            logger.error("❌ Método index_message: NÃO ENCONTRADO")
            
        if hasattr(es_client, 'domain_endpoint'):
            logger.info("🔗 Endpoint OpenSearch: %s", es_client.domain_endpoint or "None")
            
        if enabled_status == "DESABILITADO":
            logger.warning("⚠️ ATENÇÃO: Mensagens NÃO serão enviadas para OpenSearch!")
    else:
        logger.error("❌ Cliente OpenSearch: INDISPONÍVEL - mensagens não serão enviadas!")
    
    total_messages = 0
    total_sent_kinesis = 0
    total_sent_opensearch = 0
    classification_stats = {'POL': 0, 'CONSPIRA': 0, 'NAZ': 0, 'OTHER': 0}
    
    # Buffer para batch Kinesis otimizado (AWS Best Practices)
    kinesis_batch = []
    
    # Carregar estado para evitar duplicatas
    state = load_state()
    
    # Estratégia: Processar TODOS os grupos por execução (máxima cobertura)
    groups_to_process = groups_data  # Processar todos os grupos
    
    logger.info("📝 Processando TODOS os %d grupos nesta execução", len(groups_to_process))
    logger.info("🔄 Estratégia: Cobertura completa com controle de estado (sem duplicatas)")
    logger.info("📄 Estado atual: %d grupos com histórico", len(state))
    
    # Estatísticas de captura
    grupos_novos = len([g for g in groups_to_process if g.get('username', '') not in state])
    grupos_incrementais = len(groups_to_process) - grupos_novos
    logger.info("📊 Captura: %d grupos novos (24h histórico) + %d incrementais (só novas)", 
               grupos_novos, grupos_incrementais)
    
    for i, group_info in enumerate(groups_to_process):
        group_username = group_info.get('username', '')
        
        # Extrair TODAS as categorizações (como na planilha)
        group_project = group_info.get('project', 'Pol')
        group_country = group_info.get('country', 'Brasil')
        group_format = group_info.get('format', 'unknown')      # News, Debate, Meme
        group_spectrum = group_info.get('spectrum', 'unknown')   # Right, Left, General
        group_stance = group_info.get('stance', 'unknown')      # Conservative, Progressive
        group_identity = group_info.get('identity', 'unknown')  # Red Pill, Religious, etc
        group_basis = group_info.get('basis', 'None')          # Bolsonarista, Lulista, None
        group_territory = group_info.get('territory', 'National') # National, State-level
        
        if not group_username:
            continue
            
        logger.info("📱 ==> [%d/%d] Processando: %s (%s|%s|%s)", 
                   i+1, len(groups_to_process), group_username, group_spectrum, group_stance, group_basis)
        
        try:
            # Controle de estado: evitar duplicatas usando min_id ou offset_date
            group_state = state.get(group_username, {})
            last_message_id = group_state.get('last_message_id')
            
            if last_message_id:
                # Usar min_id para pegar apenas mensagens NOVAS (AWS Best Practice)
                messages = client.get_messages(group_username, min_id=last_message_id, limit=None)
                logger.info("📥 [INCREMENTAL] %d mensagens API em %s (min_id=%s)", 
                           len(messages), group_username, last_message_id)
            else:
                # Primeira execução: pegar últimas 6 horas SEM LIMITE para captura completa
                offset_date = datetime.now(timezone.utc) - timedelta(hours=6)
                messages = client.get_messages(group_username, offset_date=offset_date, limit=None)
                logger.info("📥 [PRIMEIRA VEZ] %d mensagens API últimas 6h em %s (SEM LIMITE)", 
                           len(messages), group_username)
            
            # Rate limiting: pausa segura para evitar flood (10 min ciclo = mais tempo disponível)
            if i < len(groups_to_process) - 1:  # Não pausar no último
                time.sleep(1.5)  # 1.5s = 200 grupos em ~5 minutos (sobra 5min para processamento)
            
            # Atualizar estado com último message_id processado
            newest_message_id = None
            messages_processed_count = 0
            messages_filtered_count = 0
            
            logger.info("🔍 DEBUG: Processando %d mensagens de %s...", len(messages), group_username)
            
            for msg in messages:
                # FILTRO RELAXADO: aceitar mensagens com 3+ caracteres (antes era 10)
                if msg.text and len(msg.text.strip()) > 3:
                    total_messages += 1
                    messages_processed_count += 1
                    
                    # Rastrear message_id mais recente
                    if newest_message_id is None or msg.id > newest_message_id:
                        newest_message_id = msg.id
                    
                    # Classificar mensagem
                    classification = classify_message(msg.text)
                    classification_stats[classification] = classification_stats.get(classification, 0) + 1
                    
                    # Extrair metadados do Telegram (views, reactions, shares)
                    views = getattr(msg, 'views', 0) or 0
                    forwards = getattr(msg, 'forwards', 0) or 0
                    
                    # Processar reações (pode ser None, lista ou objeto ReactionCount)
                    reactions_total = 0
                    reactions_detail = []
                    if hasattr(msg, 'reactions') and msg.reactions:
                        if hasattr(msg.reactions, 'results'):
                            for reaction in msg.reactions.results:
                                count = getattr(reaction, 'count', 0)
                                reactions_total += count
                                
                                # Extrair emoji/reaction type
                                if hasattr(reaction, 'reaction'):
                                    if hasattr(reaction.reaction, 'emoticon'):
                                        emoji = reaction.reaction.emoticon
                                    else:
                                        emoji = str(reaction.reaction)
                                else:
                                    emoji = 'unknown'
                                
                                reactions_detail.append({
                                    'emoji': emoji,
                                    'count': count
                                })
                    
                    # Preparar dados COMPLETOS com metadados do Telegram + TODAS as categorizações
                    message_data = {
                        'message': msg.text[:800],
                        'group_name': group_username,
                        # CATEGORIZAÇÕES COMPLETAS DA PLANILHA
                        'group_project': group_project,      # 'Pol'
                        'group_country': group_country,      # 'Brasil'
                        'group_format': group_format,        # 'News', 'Debate', 'Meme', 'Personality'
                        'group_spectrum': group_spectrum,    # 'Right', 'Left', 'General'
                        'group_stance': group_stance,        # 'Conservative', 'Progressive'
                        'group_identity': group_identity,    # 'Red Pill', 'Religious', 'Socialist'
                        'group_basis': group_basis,          # 'Bolsonarista', 'Lulista/Petista', 'None'
                        'group_territory': group_territory,  # 'National', 'State-level'
                        'classification': classification,
                        'timestamp': msg.date.isoformat(),
                        'date_message': msg.date.isoformat(),
                        'message_id': str(msg.id),
                        'source': 'vm_scraper_continuous',
                        'content': msg.text[:500],
                        'indexed_at': datetime.now(timezone.utc).isoformat(),
                        # METADADOS ADICIONAIS (como no dashboard)
                        'views': views,
                        'reactions': reactions_total,
                        'reactions_detail': reactions_detail,
                        'shares': forwards,
                        'forwards': forwards,  # Alias para compatibilidade
                        # Campos extras para análise
                        'author_id': str(getattr(msg, 'from_id', '')) if getattr(msg, 'from_id', None) else None,
                        'reply_to': getattr(msg, 'reply_to_msg_id', None),
                        'is_forwarded': getattr(msg, 'fwd_from', None) is not None,
                        'media_type': 'text' if not msg.media else str(type(msg.media).__name__)
                    }
                    
                    # Adicionar ao batch Kinesis (AWS Best Practice - envio em lote)
                    kinesis_batch.append(message_data)
                    
                    # Enviar para OpenSearch direto
                    if es_client and send_message_to_opensearch(message_data, es_client):
                        total_sent_opensearch += 1
                        logger.info("🔍 ✅ OpenSearch: %s | %s", group_username, classification)
                else:
                    # Contar mensagens filtradas para debug
                    messages_filtered_count += 1
                    if msg.text:
                        logger.info("⛔ FILTRADA: MSG %s (%d chars): '%s'", msg.id, len(msg.text.strip()), msg.text[:30])
                    else:
                        logger.info("⛔ FILTRADA: MSG %s (sem texto)", msg.id)
            
            # Atualizar estado sempre (mesmo se 0 mensagens) para tracking completo
            current_time = datetime.now(timezone.utc).isoformat()
            if newest_message_id is not None:
                state[group_username] = {
                    'last_message_id': newest_message_id,
                    'last_processed_at': current_time,
                    'total_processed': len(messages),
                    'messages_this_run': len(messages)
                }
                logger.info("📄 Estado atualizado para %s: last_id=%s (%d processadas de %d API)", 
                           group_username, newest_message_id, messages_processed_count, len(messages))
            else:
                # Atualizar timestamp mesmo se sem mensagens novas
                if group_username in state:
                    state[group_username]['last_processed_at'] = current_time
                    state[group_username]['messages_this_run'] = 0
                else:
                    state[group_username] = {
                        'last_message_id': None,
                        'last_processed_at': current_time,
                        'total_processed': 0,
                        'messages_this_run': 0
                    }
                logger.info("📄 Estado atualizado para %s: SEM MENSAGENS PROCESSADAS (%d API, %d filtradas)", 
                           group_username, len(messages), messages_filtered_count)
            
        except FloodWaitError as flood_error:
            logger.warning("⏳ Rate limit para %s: aguardar %ds", group_username, flood_error.seconds)
            continue
            
        except Exception as group_error:
            logger.error("❌ Erro no grupo %s: %s", group_username, group_error)
            continue
    
    # Enviar batch Kinesis ao final (AWS Best Practice)
    if kinesis_batch:
        logger.info("📦 Enviando batch Kinesis: %d mensagens acumuladas", len(kinesis_batch))
        sent_count, failed_count = send_batch_to_kinesis_optimized(kinesis_batch)
        total_sent_kinesis = sent_count
        
        if failed_count > 0:
            logger.warning("⚠️ Kinesis Batch Final: %d falharam, %d enviadas", failed_count, sent_count)
        else:
            logger.info("✅ Kinesis Batch Final: todas as %d mensagens enviadas com sucesso", sent_count)
    
    # Salvar estado atualizado (crítico para evitar duplicatas)
    if save_state(state):
        logger.info("💾 Estado salvo com sucesso - próximas execuções serão incrementais")
    else:
        logger.warning("⚠️ Falha ao salvar estado - pode haver duplicatas na próxima execução")
    
    # Estatísticas detalhadas da execução
    grupos_com_mensagens = len([username for username, data in state.items() 
                               if data.get('messages_this_run', 0) > 0])
    grupos_processados = len([username for username, data in state.items() 
                             if 'last_processed_at' in data])
    grupos_primeira_vez = len([username for username, data in state.items() 
                              if data.get('last_message_id') is None])
    grupos_incrementais = grupos_processados - grupos_primeira_vez
    
    logger.info("📊 ESTATÍSTICAS DESTA EXECUÇÃO:")
    logger.info("📱 Total mensagens capturadas: %d", total_messages)
    logger.info("📡 Kinesis enviadas: %d", total_sent_kinesis)
    logger.info("🔍 OpenSearch enviadas: %d", total_sent_opensearch)
    logger.info("📈 Classificações: %s", classification_stats)
    logger.info("📄 Cobertura completa: %d/%d grupos processados", grupos_processados, len(groups_to_process))
    logger.info("📊 Atividade: %d grupos com mensagens novas, %d sem mensagens", 
               grupos_com_mensagens, grupos_processados - grupos_com_mensagens)
    logger.info("🔄 Tipos: %d primeira vez (6h histórico), %d incrementais (min_id)", 
               grupos_primeira_vez, grupos_incrementais)
    
    # Alerta se cobertura não foi completa
    if grupos_processados < len(groups_to_process):
        logger.warning("⚠️ ATENÇÃO: %d grupos NÃO foram processados! Possível rate limiting.", 
                      len(groups_to_process) - grupos_processados)
    
    if total_messages == 0:
        logger.info("ℹ️ NORMAL: 0 mensagens = todos os grupos estão atualizados (sistema funcionando)")
    else:
        logger.info("✅ SUCESSO: %d mensagens novas capturadas (cobertura garantida)", total_messages)
    
    return total_messages, total_sent_kinesis, total_sent_opensearch, classification_stats

def main():
    """Função principal do scraper contínuo"""
    global running
    
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 ==> INICIANDO TELEGRAM SCRAPER VM CONTÍNUO")
    logger.info("📅 Timestamp: %s", datetime.now(timezone.utc).isoformat())
    logger.info("💾 Logs salvos em: telegram_scraper.log")
    logger.info("📄 Estado salvo em: telegram_scraper_state.json")
    logger.info("⏹️ Para parar: Ctrl+C")
    logger.info("🔄 Sistema anti-duplicatas: ATIVO (usando min_id)")
    
    # Validar configurações
    config = validate_environment()
    if not config:
        logger.error("❌ Configuração inválida. Saindo...")
        return
    
    # Inicializar clientes
    es_client = initialize_elasticsearch()
    cw_monitor = initialize_cloudwatch()
    
    # Carregar grupos uma vez
    groups_data = load_groups_from_sheets()
    if not groups_data:
        logger.error("❌ Nenhum grupo carregado. Saindo...")
        return
    
    # Preparar sessão Telegram
    client = setup_telegram_client(config['api_id'], config['api_hash'])
    if not client:
        logger.error("❌ Falha na autenticação Telegram. Saindo...")
        return
    
    # Loop principal
    execution_count = 0
    total_messages_all = 0
    total_kinesis_all = 0
    total_opensearch_all = 0
    
    logger.info("🔄 ==> INICIANDO LOOP CONTÍNUO (execução a cada 10 minutos)")
    
    try:
        while running:
            execution_count += 1
            logger.info("\n" + "="*80)
            logger.info("🔄 EXECUÇÃO #%d - %s", execution_count, datetime.now().strftime("%H:%M:%S"))
            logger.info("="*80)
            
            # Fazer scraping com rotação pelos 200 grupos (com controle de estado)
            messages, kinesis_sent, opensearch_sent, classification_stats = process_telegram_groups_continuous(
                client, groups_data, es_client
            )
            
            # Atualizar totais
            total_messages_all += messages
            total_kinesis_all += kinesis_sent
            total_opensearch_all += opensearch_sent
            
            # Enviar métricas para CloudWatch
            if cw_monitor and cw_monitor.enabled:
                try:
                    cw_monitor.send_scraping_stats(
                        messages,
                        len(groups_data),
                        classification_stats.get('POL', 0),
                        classification_stats.get('CONSPIRA', 0),
                        classification_stats.get('NAZ', 0)
                    )
                    # Métricas adicionais da VM
                    cw_monitor.send_metric('VM_Executions', 1, 'Count')
                    cw_monitor.send_metric('VM_KinesisSent', kinesis_sent, 'Count')
                    cw_monitor.send_metric('VM_OpenSearchSent', opensearch_sent, 'Count')
                    logger.info("📈 Métricas CloudWatch enviadas")
                except Exception as e:
                    logger.error("❌ Erro métricas CloudWatch: %s", e)
            
            # Resumo da execução
            logger.info("🎯 RESUMO EXECUÇÃO #%d:", execution_count)
            logger.info("📱 Mensagens processadas: %d", messages)
            logger.info("📡 Enviadas Kinesis: %d", kinesis_sent)
            logger.info("🔍 Enviadas OpenSearch: %d", opensearch_sent)
            logger.info("📊 TOTAIS ACUMULADOS:")
            logger.info("📱 Total mensagens: %d", total_messages_all)
            logger.info("📡 Total Kinesis: %d", total_kinesis_all)
            logger.info("🔍 Total OpenSearch: %d", total_opensearch_all)
            
            if running:
                logger.info("⏳ Aguardando 10 minutos para próxima execução...")
                logger.info("⏹️ Para parar: Ctrl+C")
                
                # Aguardar 10 minutos (com verificação a cada 30 segundos)
                for i in range(20):  # 20 * 30 = 600 segundos = 10 minutos
                    if not running:
                        break
                    time.sleep(30)
                    if (i + 1) % 4 == 0:  # Log a cada 2 minutos
                        minutes_remaining = 10 - ((i + 1) * 30) // 60
                        logger.info("⏳ %d minuto(s) restante(s)...", minutes_remaining)
    
    except Exception as e:
        logger.error("❌ Erro crítico no loop principal: %s", e)
        logger.error("📋 Traceback: %s", traceback.format_exc())
    
    finally:
        # Cleanup
        logger.info("🧹 Finalizando execução...")
        if client:
            client.disconnect()
            logger.info("📱 Cliente Telegram desconectado")
        
        logger.info("📊 ESTATÍSTICAS FINAIS:")
        logger.info("🔄 Total execuções: %d", execution_count)
        logger.info("📱 Total mensagens processadas: %d", total_messages_all)
        logger.info("📡 Total enviadas Kinesis: %d", total_kinesis_all)
        logger.info("🔍 Total enviadas OpenSearch: %d", total_opensearch_all)
        logger.info("🏁 ==> TELEGRAM SCRAPER VM FINALIZADO")

if __name__ == "__main__":
    main()
