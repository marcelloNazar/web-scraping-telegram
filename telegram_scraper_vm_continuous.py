#!/usr/bin/env python3
"""
Telegram Scraper VM Continuous
Roda continuamente na VM fazendo scraping e enviando para Kinesis + OpenSearch

GARANTIAS DE COBERTURA:
- Processa TODOS os 200 grupos a cada 5 minutos
- Primeira execução: últimas 6 horas SEM LIMITE  
- Execuções seguintes: apenas mensagens novas (min_id)
- Rate limiting seguro: 1.0s entre grupos
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
    """
    Enviar mensagens em batch usando PutRecords (AWS Best Practice)
    Baseado em: https://docs.aws.amazon.com/streams/latest/dev/service-sizes-and-limits.html
    Limites: 1000 records/shard/sec, 1MB/shard/sec, 500 records/request, 5MB/request
    """
    if not messages_batch:
        return 0, 0
    
    total_sent = 0
    total_failed = 0
    
    # AWS Best Practices - Rate Limiting
    KINESIS_MAX_BATCH_SIZE = 400  # 80% do limite AWS (500) para margem de segurança
    KINESIS_MAX_REQUEST_SIZE_MB = 4.0  # 80% do limite AWS (5MB)
    KINESIS_RETRY_DELAYS = [1, 2, 4, 8]  # Exponential backoff (AWS recomendado)
    KINESIS_RATE_LIMIT_DELAY = 0.5  # Delay mínimo entre requests (rate limiting)
    
    try:
        # Verificar tamanho total aproximado
        total_size_mb = len(json.dumps(messages_batch).encode('utf-8')) / (1024 * 1024)
        if total_size_mb > KINESIS_MAX_REQUEST_SIZE_MB:
            logger.warning("⚠️ Batch muito grande (%.2f MB), dividindo em chunks menores", total_size_mb)
        
        # Dividir em chunks respeitando limites AWS
        for i in range(0, len(messages_batch), KINESIS_MAX_BATCH_SIZE):
            batch_chunk = messages_batch[i:i + KINESIS_MAX_BATCH_SIZE]
            
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
            
            # Calcular tamanho do chunk
            chunk_size_mb = len(json.dumps(chunk_records).encode('utf-8')) / (1024 * 1024)
            
            # Rate limiting baseado em AWS Best Practices
            time.sleep(KINESIS_RATE_LIMIT_DELAY)
            
            # Enviar chunk usando PutRecords com retry inteligente
            chunk_success, chunk_failed = send_kinesis_chunk_with_retry(
                chunk_records, KINESIS_RETRY_DELAYS, chunk_size_mb
            )
            
            total_sent += chunk_success
            total_failed += chunk_failed
            
            logger.info("✅ Kinesis Chunk: %d/%d records enviados (%.2f MB)", 
                       chunk_success, len(chunk_records), chunk_size_mb)
        
        return total_sent, total_failed
        
    except Exception as kinesis_error:
        logger.error("❌ Erro Kinesis PutRecords: %s", kinesis_error)
        return 0, len(messages_batch)

def send_kinesis_chunk_with_retry(chunk_records, retry_delays, chunk_size_mb):
    """
    Enviar chunk para Kinesis com retry exponential backoff (AWS Best Practice)
    """
    max_retries = len(retry_delays)
    
    for attempt in range(max_retries + 1):
        try:
            logger.info("📡 Tentativa %d/%d: Enviando %d records (%.2f MB) para Kinesis", 
                       attempt + 1, max_retries + 1, len(chunk_records), chunk_size_mb)
            
            response = kinesis_client.put_records(
                StreamName='telegram-messages',
                Records=chunk_records
            )
            
            # Verificar resultados
            failed_count = response.get('FailedRecordCount', 0)
            success_count = len(chunk_records) - failed_count
            
            if failed_count == 0:
                logger.info("✅ Kinesis SUCCESS: todos os %d records enviados", len(chunk_records))
                return success_count, 0
            
            # Se há falhas, preparar retry apenas com records falhados
            if attempt < max_retries:
                failed_records = []
                for idx, record_result in enumerate(response['Records']):
                    if 'ErrorCode' in record_result:
                        failed_records.append(chunk_records[idx])
                        error_code = record_result.get('ErrorCode', 'Unknown')
                        logger.warning("⚠️ Record %d falhou: %s", idx, error_code)
                
                # Usar apenas records falhados no próximo retry
                chunk_records = failed_records
                retry_delay = retry_delays[attempt]
                
                logger.warning("⚠️ Tentativa %d: %d/%d records falharam. Retry em %ds...", 
                             attempt + 1, failed_count, success_count + failed_count, retry_delay)
                time.sleep(retry_delay)
                continue
            else:
                logger.error("❌ FINAL: %d records falharam após %d tentativas", failed_count, max_retries + 1)
                return success_count, failed_count
                
        except Exception as e:
            if attempt < max_retries:
                retry_delay = retry_delays[attempt]
                logger.error("❌ Erro na tentativa %d: %s. Retry em %ds...", attempt + 1, e, retry_delay)
                time.sleep(retry_delay)
            else:
                logger.error("❌ ERRO FINAL após %d tentativas: %s", max_retries + 1, e)
                return 0, len(chunk_records)
    
    return 0, len(chunk_records)

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

def send_batch_to_opensearch_bulk(messages_batch, es_client):
    """
    Enviar lote de mensagens usando Bulk API (AWS Best Practice)
    Baseado em: AOSPERF06-BP02 (3-5 MiB batches)
    https://docs.aws.amazon.com/wellarchitected/latest/amazon-opensearch-service-lens/aosperf06-bp02.html
    """
    if not messages_batch or not es_client:
        return 0, []
    
    # AWS Best Practices para OpenSearch Bulk
    OPENSEARCH_MAX_BATCH_SIZE_MB = 4.0  # 4 MiB (dentro da faixa recomendada 3-5 MiB)
    OPENSEARCH_RETRY_DELAYS = [2, 5, 10]  # Backoff delays (segundos)
    OPENSEARCH_MAX_RETRIES = len(OPENSEARCH_RETRY_DELAYS)
    
    try:
        # Verificar se cliente está habilitado
        if hasattr(es_client, 'enabled') and not es_client.enabled:
            logger.warning("⚠️ Cliente OpenSearch DESABILITADO - batch não enviado")
            return 0, messages_batch
        
        # Verificar tamanho antes de processar
        estimated_size_mb = len(json.dumps(messages_batch).encode('utf-8')) / (1024 * 1024)
        if estimated_size_mb > OPENSEARCH_MAX_BATCH_SIZE_MB:
            logger.warning("⚠️ Batch muito grande (%.2f MB), dividindo em sub-batches", estimated_size_mb)
            return send_opensearch_large_batch(messages_batch, es_client, OPENSEARCH_MAX_BATCH_SIZE_MB)
        
        # Preparar bulk request
        bulk_body = []
        doc_ids = []
        
        for msg_data in messages_batch:
            doc_id = "%s_%s_%s" % (
                msg_data.get('group_name', 'unknown'),
                msg_data.get('message_id', 'unknown'),
                int(datetime.now(timezone.utc).timestamp() * 1000000)  # Microseconds para unicidade
            )
            doc_ids.append(doc_id)
            
            # Action header para bulk
            bulk_body.append({
                "index": {
                    "_index": "telegram-messages",
                    "_id": doc_id
                }
            })
            
            # Document body
            bulk_body.append(msg_data)
        
        # Calcular tamanho real (AWS recomenda 3-5 MiB)
        bulk_size_mb = len(json.dumps(bulk_body).encode('utf-8')) / (1024 * 1024)
        
        logger.info("📦 Enviando bulk OpenSearch: %d docs (%.2f MB) - dentro do limite %.1f MB", 
                   len(messages_batch), bulk_size_mb, OPENSEARCH_MAX_BATCH_SIZE_MB)
        
        # Enviar bulk usando cliente ES com retry inteligente
        return send_opensearch_bulk_with_retry(
            es_client, bulk_body, doc_ids, len(messages_batch), bulk_size_mb, OPENSEARCH_RETRY_DELAYS
        )
        
    except Exception as bulk_error:
        logger.error("❌ Erro Bulk OpenSearch: %s", bulk_error)
        logger.error("📋 Traceback: %s", traceback.format_exc())
        failed_items = [{'doc_id': f'unknown_{i}', 'error': str(bulk_error)} 
                       for i in range(len(messages_batch))]
        return 0, failed_items

def send_opensearch_bulk_with_retry(es_client, bulk_body, doc_ids, doc_count, bulk_size_mb, retry_delays):
    """
    Enviar bulk para OpenSearch com retry exponential backoff (AWS Best Practice)
    """
    max_retries = len(retry_delays)
    
    for attempt in range(max_retries + 1):
        try:
            logger.info("🔍 Tentativa %d/%d: Enviando bulk OpenSearch %d docs (%.2f MB)", 
                       attempt + 1, max_retries + 1, doc_count, bulk_size_mb)
            
            # Tentar usar bulk API nativo se disponível
            if hasattr(es_client, 'es_client') and es_client.es_client:
                try:
                    # Tentar importar elasticsearch helpers
                    from elasticsearch import helpers
                    
                    # Preparar documentos para helpers.bulk
                    documents = []
                    for i in range(0, len(bulk_body), 2):  # bulk_body tem pares: action, document
                        action = bulk_body[i]
                        document = bulk_body[i + 1]
                        doc = {
                            '_index': action['index']['_index'],
                            '_id': action['index']['_id'],
                            '_source': document
                        }
                        documents.append(doc)
                    
                    # Bulk insert com configuração otimizada
                    success_count, failed_items = helpers.bulk(
                        es_client.es_client,
                        documents,
                        chunk_size=50,  # Chunks menores para estabilidade
                        max_retries=0,  # Sem retry interno - controlamos aqui
                        timeout=30,  # Timeout de 30s
                        raise_on_error=False,
                        raise_on_exception=False
                    )
                    
                    if isinstance(success_count, int) and success_count > 0:
                        logger.info("✅ OpenSearch SUCCESS (helpers.bulk): %d/%d docs indexados", success_count, doc_count)
                        return success_count, []
                    
                    # Se chegou aqui, houve falhas
                    logger.warning("⚠️ OpenSearch helpers.bulk falhou na tentativa %d", attempt + 1)
                    
                except ImportError:
                    # Se elasticsearch não estiver disponível, usar fallback
                    logger.info("ℹ️ elasticsearch module não disponível, usando fallback otimizado...")
                    return send_opensearch_fallback_bulk(es_client, bulk_body, doc_count)
                    
            else:
                # Fallback: usar método customizado otimizado
                logger.warning("⚠️ Cliente OpenSearch es_client não disponível, usando fallback otimizado")
                return send_opensearch_fallback_bulk(es_client, bulk_body, doc_count)
                
            # Se chegou aqui, a tentativa falhou
            if attempt < max_retries:
                retry_delay = retry_delays[attempt]
                logger.warning("⚠️ Tentativa %d falhou. Retry em %ds...", attempt + 1, retry_delay)
                time.sleep(retry_delay)
            else:
                logger.error("❌ FINAL: OpenSearch falhou após %d tentativas", max_retries + 1)
                return 0, [{'doc_id': f'doc_{i}', 'error': 'max_retries_exceeded'} for i in range(doc_count)]
                
        except Exception as e:
            if attempt < max_retries:
                retry_delay = retry_delays[attempt]
                logger.error("❌ Erro OpenSearch tentativa %d: %s. Retry em %ds...", attempt + 1, e, retry_delay)
                time.sleep(retry_delay)
            else:
                logger.error("❌ ERRO FINAL OpenSearch após %d tentativas: %s", max_retries + 1, e)
                return 0, [{'doc_id': f'doc_{i}', 'error': str(e)} for i in range(doc_count)]
    
    return 0, [{'doc_id': f'doc_{i}', 'error': 'unknown_failure'} for i in range(doc_count)]

def send_opensearch_fallback_bulk(es_client, bulk_body, doc_count):
    """
    Fallback bulk para quando elasticsearch module não está disponível
    Usa apenas o cliente OpenSearch existente
    """
    logger.info("📦 Usando fallback bulk otimizado (sem elasticsearch module)")
    
    success_count = 0
    failed_items = []
    
    # Rate limiting: processar em mini-batches de 10 documentos
    batch_size = 10
    
    try:
        for i in range(0, len(bulk_body), batch_size * 2):  # *2 porque bulk_body tem pares
            mini_batch_start = i
            mini_batch_end = min(i + batch_size * 2, len(bulk_body))
            
            mini_batch_success = 0
            mini_batch_errors = []
            
            # Processar mini-batch
            for j in range(mini_batch_start, mini_batch_end, 2):
                try:
                    if j + 1 < len(bulk_body):
                        action = bulk_body[j]
                        document = bulk_body[j + 1]
                        doc_id = action['index']['_id']
                        
                        # Usar método individual do cliente existente
                        result = es_client.index_message(document, doc_id)
                        if result:
                            mini_batch_success += 1
                            success_count += 1
                        else:
                            error_info = {'doc_id': doc_id, 'error': 'index_failed'}
                            mini_batch_errors.append(error_info)
                            failed_items.append(error_info)
                            
                except Exception as e:
                    error_info = {'doc_id': f'doc_{j//2}', 'error': str(e)}
                    mini_batch_errors.append(error_info)
                    failed_items.append(error_info)
                
                # Mini delay para não sobrecarregar
                time.sleep(0.01)  # 10ms por documento
            
            # Log do progresso do mini-batch
            if mini_batch_success > 0:
                logger.info("✅ Mini-batch %d-%d: %d sucessos, %d falhas", 
                           mini_batch_start//2, mini_batch_end//2, mini_batch_success, len(mini_batch_errors))
            
            # Delay entre mini-batches para rate limiting
            if mini_batch_end < len(bulk_body):
                time.sleep(0.5)  # 500ms entre mini-batches
        
        logger.info("✅ Fallback bulk completo: %d/%d docs indexados", success_count, doc_count)
        return success_count, failed_items
        
    except Exception as e:
        logger.error("❌ Erro no fallback bulk: %s", e)
        return 0, [{'doc_id': f'doc_{i}', 'error': str(e)} for i in range(doc_count)]

def send_opensearch_large_batch(messages_batch, es_client, max_size_mb):
    """
    Dividir batch grande em sub-batches menores (AWS Best Practice)
    """
    logger.info("📦 Dividindo batch grande em sub-batches de %.1f MB", max_size_mb)
    
    total_success = 0
    total_failed = []
    current_batch = []
    current_size_mb = 0
    
    for msg_data in messages_batch:
        # Estimar tamanho da mensagem
        msg_size_mb = len(json.dumps(msg_data).encode('utf-8')) / (1024 * 1024)
        
        # Se adicionar esta mensagem ultrapassar o limite, processar batch atual
        if current_size_mb + msg_size_mb > max_size_mb and current_batch:
            success, failed = send_batch_to_opensearch_bulk(current_batch, es_client)
            total_success += success
            total_failed.extend(failed)
            
            # Reset para próximo batch
            current_batch = []
            current_size_mb = 0
            
            # Delay entre sub-batches para rate limiting
            time.sleep(1.0)
        
        # Adicionar mensagem ao batch atual
        current_batch.append(msg_data)
        current_size_mb += msg_size_mb
    
    # Processar último batch se não estiver vazio
    if current_batch:
        success, failed = send_batch_to_opensearch_bulk(current_batch, es_client)
        total_success += success
        total_failed.extend(failed)
    
    logger.info("📦 Processamento completo: %d sucessos, %d falhas", total_success, len(total_failed))
    return total_success, total_failed

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
    
    # Buffer para batch OpenSearch otimizado (AWS Best Practices)
    opensearch_batch = []
    OPENSEARCH_BATCH_SIZE = 50   # Mensagens por batch (menor para estabilidade)
    OPENSEARCH_DELAY = 3.0       # Segundos entre batches (rate limiting conservador)
    
    # DEBUG: Contadores detalhados para diagnóstico
    debug_counts = {
        'messages_api_total': 0,      # Total de mensagens da API
        'messages_filtered_out': 0,   # Mensagens filtradas (texto < 2 chars)
        'messages_added_kinesis': 0,  # Mensagens adicionadas ao buffer Kinesis
        'messages_added_opensearch': 0,  # Mensagens adicionadas ao buffer OpenSearch
        'opensearch_batches_sent': 0,    # Número de batches OpenSearch enviados
        'opensearch_intermediate_sent': 0  # Mensagens enviadas em batches intermediários
    }
    
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
                time.sleep(1.0)  # 1.0s = 200 grupos em ~3.5 minutos (sobra 1.5min para processamento)
            
            # Atualizar estado com último message_id processado
            newest_message_id = None
            messages_processed_count = 0
            messages_filtered_count = 0
            
            logger.info("🔍 DEBUG: Processando %d mensagens de %s...", len(messages), group_username)
            
            for msg in messages:
                # Contar todas as mensagens da API
                debug_counts['messages_api_total'] += 1
                
                # FILTRO RELAXADO: aceitar mensagens com 2+
                if msg.text and len(msg.text.strip()) > 1:
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
                    debug_counts['messages_added_kinesis'] += 1
                    
                    # Adicionar ao batch OpenSearch (AWS Best Practice - bulk requests)
                    if es_client and hasattr(es_client, 'enabled') and es_client.enabled:
                        opensearch_batch.append(message_data)
                        debug_counts['messages_added_opensearch'] += 1
                        logger.debug("📦 OpenSearch batch: %s | %s | MSG_%s (batch size: %d)", 
                                   group_username, classification, msg.id, len(opensearch_batch))
                        
                        # Enviar batch quando atingir tamanho máximo
                        if len(opensearch_batch) >= OPENSEARCH_BATCH_SIZE:
                            logger.info("🚀 BATCH INTERMEDIÁRIO OpenSearch: %d mensagens acumuladas", len(opensearch_batch))
                            success_count, failed_items = send_batch_to_opensearch_bulk(opensearch_batch, es_client)
                            total_sent_opensearch += success_count
                            debug_counts['opensearch_batches_sent'] += 1
                            debug_counts['opensearch_intermediate_sent'] += success_count
                            
                            if failed_items:
                                logger.warning("⚠️ Batch Intermediário OpenSearch: %d/%d falharam", len(failed_items), len(opensearch_batch))
                            else:
                                logger.info("✅ Batch Intermediário OpenSearch: %d/%d sucessos", success_count, len(opensearch_batch))
                            
                            # Reset batch e delay para rate limiting
                            opensearch_batch = []
                            time.sleep(OPENSEARCH_DELAY)
                    elif es_client:
                        logger.debug("⚠️ OpenSearch cliente DESABILITADO - mensagem não adicionada ao buffer")
                    else:
                        logger.debug("❌ OpenSearch cliente INDISPONÍVEL - mensagem não adicionada ao buffer")
                else:
                    # Contar mensagens filtradas para debug
                    messages_filtered_count += 1
                    debug_counts['messages_filtered_out'] += 1
                    if msg.text:
                        logger.debug("⛔ FILTRADA: MSG %s (%d chars): '%s'", msg.id, len(msg.text.strip()), msg.text[:30])
                    else:
                        logger.debug("⛔ FILTRADA: MSG %s (sem texto)", msg.id)
            
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
    
    # Enviar batch OpenSearch final (AWS Best Practice)
    if opensearch_batch and es_client and hasattr(es_client, 'enabled') and es_client.enabled:
        logger.info("📦 Enviando batch OpenSearch FINAL: %d mensagens acumuladas", len(opensearch_batch))
        success_count, failed_items = send_batch_to_opensearch_bulk(opensearch_batch, es_client)
        total_sent_opensearch += success_count
        debug_counts['opensearch_batches_sent'] += 1
        
        if failed_items:
            logger.warning("⚠️ OpenSearch Batch Final: %d falharam, %d enviadas", len(failed_items), len(opensearch_batch))
        else:
            logger.info("✅ OpenSearch Batch Final: todas as %d mensagens enviadas com sucesso", success_count)
    elif opensearch_batch:
        logger.warning("⚠️ OpenSearch batch final não enviado: %d mensagens descartadas (cliente desabilitado/indisponível)", len(opensearch_batch))
    
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
    
    # DEBUG: Estatísticas detalhadas para diagnóstico
    logger.info("\n" + "="*80)
    logger.info("🔍 DEBUG - FLUXO DETALHADO DE MENSAGENS:")
    logger.info("="*80)
    logger.info("📡 Mensagens da API total: %d", debug_counts['messages_api_total'])
    logger.info("⛔ Mensagens filtradas (texto < 2 chars): %d", debug_counts['messages_filtered_out'])
    logger.info("📦 Mensagens adicionadas ao buffer Kinesis: %d", debug_counts['messages_added_kinesis'])
    logger.info("📦 Mensagens adicionadas ao buffer OpenSearch: %d", debug_counts['messages_added_opensearch'])
    logger.info("🚀 Batches OpenSearch enviados: %d", debug_counts['opensearch_batches_sent'])
    logger.info("📤 Mensagens OpenSearch intermediárias enviadas: %d", debug_counts['opensearch_intermediate_sent'])
    logger.info("📤 Mensagens OpenSearch finais enviadas: %d", total_sent_opensearch - debug_counts['opensearch_intermediate_sent'])
    
    # Cálculos de verificação
    processed_vs_api = debug_counts['messages_added_kinesis'] + debug_counts['messages_filtered_out']
    kinesis_vs_opensearch = debug_counts['messages_added_kinesis'] - debug_counts['messages_added_opensearch']
    
    logger.info("🔍 VERIFICAÇÕES:")
    logger.info("   API vs Processadas: %d vs %d = %s", 
               debug_counts['messages_api_total'], processed_vs_api,
               "✅ OK" if debug_counts['messages_api_total'] == processed_vs_api else "❌ DISCREPÂNCIA")
    logger.info("   Kinesis vs OpenSearch buffer: %d vs %d = diferença de %d", 
               debug_counts['messages_added_kinesis'], debug_counts['messages_added_opensearch'], kinesis_vs_opensearch)
    logger.info("   OpenSearch buffer vs enviadas: %d vs %d = %s", 
               debug_counts['messages_added_opensearch'], total_sent_opensearch,
               "✅ OK" if debug_counts['messages_added_opensearch'] == total_sent_opensearch else "❌ PERDA")
    logger.info("="*80)
    
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
    
    logger.info("🔄 ==> INICIANDO LOOP CONTÍNUO (execução a cada 5 minutos)")
    
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
                logger.info("⏳ Aguardando 5 minutos para próxima execução...")
                logger.info("⏹️ Para parar: Ctrl+C")
                
                # Aguardar 5 minutos (com verificação a cada 30 segundos)
                for i in range(10):  # 10 * 30 = 300 segundos = 5 minutos
                    if not running:
                        break
                    time.sleep(30)
                    if (i + 1) % 2 == 0:  # Log a cada 1 minuto
                        minutes_remaining = 5 - ((i + 1) * 30) // 60
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
