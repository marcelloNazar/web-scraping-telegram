#!/usr/bin/env python3
"""
Telegram Scraper VM Real-Time Streaming
Escuta mensagens dos 204 grupos em tempo real e processa imediatamente
"""

import json
import boto3
import os
import sys
import asyncio
import time
from datetime import datetime, timezone
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
        logging.FileHandler('telegram_scraper_realtime.log'),
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
total_messages_processed = 0
total_kinesis_sent = 0
total_opensearch_sent = 0
classification_stats = {'POL': 0, 'CONSPIRA': 0, 'NAZ': 0, 'OTHER': 0}

# Buffer Kinesis otimizado (AWS Best Practices)
kinesis_buffer = None

def signal_handler(signum, frame):
    """Handler para parar execução gracefully"""
    global running
    logger.info("🛑 Recebido sinal de parada. Finalizando streaming...")
    running = False

def initialize_elasticsearch():
    """Inicializar cliente OpenSearch/Elasticsearch"""
    global elasticsearch_client
    if elasticsearch_client is None:
        try:
            from utils.aws_elasticsearch import ElasticsearchClient
            elasticsearch_client = ElasticsearchClient()
            logger.info("✅ Cliente OpenSearch inicializado")
        except Exception as e:
            logger.error("❌ Erro ao inicializar OpenSearch: %s", e)
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
        logger.info("📊 ==> CARREGANDO GRUPOS DO GOOGLE SHEETS PARA STREAMING")
        from utils.google_sheets import GoogleSheetsLoader
        
        sheets_loader = GoogleSheetsLoader()
        groups_data = sheets_loader.load_groups()
        
        # Filtrar apenas grupos ativos
        active_groups = [group for group in groups_data if group.get('active', True)]
        
        logger.info("📋 Total grupos na planilha: %d", len(groups_data))
        logger.info("📈 Grupos ativos para streaming: %d", len(active_groups))
        
        # Log dos primeiros grupos para verificação
        for i, group in enumerate(active_groups[:10]):
            logger.info("📱 Grupo %d: %s (%s)", i+1, 
                       group.get('username', 'N/A'), 
                       group.get('spectrum', 'Unknown'))
        
        if len(active_groups) > 10:
            logger.info("📝 ... e mais %d grupos para streaming", len(active_groups) - 10)
            
        return active_groups
        
    except Exception as e:
        logger.error("❌ Erro ao carregar Google Sheets: %s", e)
        # Fallback para grupos de teste
        fallback_groups = [
            {'username': '@SputnikBrasil', 'spectrum': 'right', 'active': True},
            {'username': '@rt_brasil', 'spectrum': 'right', 'active': True},
            {'username': '@plenonews', 'spectrum': 'center', 'active': True}
        ]
        logger.warning("⚠️ ERRO: Google Sheets falhou! Usando grupos de teste para streaming: %d grupos", len(fallback_groups))
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

class KinesisBuffer:
    """Buffer inteligente para envio otimizado ao Kinesis (AWS Best Practices)"""
    
    def __init__(self, max_size=100, max_wait_seconds=2):
        self.buffer = []
        self.max_size = max_size
        self.max_wait = max_wait_seconds
        self.last_flush = time.time()
        self.total_sent = 0
        self.total_failed = 0
    
    async def add_message(self, message_data):
        """Adicionar mensagem ao buffer e flush automático se necessário"""
        self.buffer.append(message_data)
        
        # Flush se buffer cheio OU tempo limite atingido
        if (len(self.buffer) >= self.max_size or 
            time.time() - self.last_flush >= self.max_wait):
            await self.flush()
    
    async def flush(self):
        """Enviar batch atual para Kinesis"""
        if not self.buffer:
            return True
        
        success = await send_batch_to_kinesis_optimized(self.buffer)
        
        if success:
            self.total_sent += len(self.buffer)
            logger.info("📡 Kinesis Batch: %d mensagens enviadas (Total: %d)", 
                       len(self.buffer), self.total_sent)
        else:
            self.total_failed += len(self.buffer)
            logger.error("❌ Kinesis Batch falhou: %d mensagens (Total falhas: %d)", 
                        len(self.buffer), self.total_failed)
        
        self.buffer.clear()
        self.last_flush = time.time()
        return success

def get_partition_key_optimized(group_name, message_id):
    """Gerar chave de partição otimizada para distribuição uniforme entre shards"""
    # Usar grupo + hash do message_id para distribuição uniforme
    hash_suffix = hash(str(message_id)) % 100
    return f"{group_name}#{hash_suffix}"

async def send_batch_to_kinesis_optimized(messages_batch):
    """Enviar mensagens em batch usando PutRecords (AWS Best Practice)"""
    if not messages_batch:
        return True
    
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
                        else:
                            logger.warning("⚠️ Retry parcial: %d ainda falharam", retry_failed)
                    except Exception as retry_error:
                        logger.error("❌ Erro no retry: %s", retry_error)
            
            success_count = len(chunk_records) - failed_count
            logger.info("✅ Kinesis PutRecords: %d/%d records enviados com sucesso", 
                       success_count, len(chunk_records))
        
        return True
        
    except Exception as kinesis_error:
        logger.error("❌ Erro Kinesis PutRecords: %s", kinesis_error)
        return False

def send_message_to_kinesis_complete(message_data, group):
    """FUNÇÃO LEGADA - Manter para compatibilidade (usar buffer é mais eficiente)"""
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
        if es_client and hasattr(es_client, 'index_message'):
            doc_id = "%s_%s_%s" % (
                message_data.get('group_name', 'unknown'),
                message_data.get('message_id', 'unknown'),
                int(datetime.now(timezone.utc).timestamp())
            )
            return es_client.index_message(message_data, doc_id)
        return False
        
    except Exception as es_error:
        logger.error("❌ Erro OpenSearch: %s", es_error)
        return False

async def process_new_message(event, groups_info_dict):
    """Processar nova mensagem recebida em tempo real"""
    global total_messages_processed, total_kinesis_sent, total_opensearch_sent, classification_stats
    
    try:
        # Verificar se é uma mensagem válida
        if not event.message or not event.message.text or len(event.message.text.strip()) <= 10:
            return
        
        # Obter informações do grupo
        chat_id = event.chat_id
        group_info = groups_info_dict.get(chat_id, {})
        group_username = group_info.get('username', f'chat_{chat_id}')
        group_spectrum = group_info.get('spectrum', 'unknown')
        
        # Classificar mensagem
        classification = classify_message(event.message.text)
        classification_stats[classification] = classification_stats.get(classification, 0) + 1
        
        # Preparar dados com informações do Google Sheets
        message_data = {
            'message': event.message.text[:800],
            'group_name': group_username,
            'group_spectrum': group_spectrum,
            'classification': classification,
            'timestamp': event.message.date.isoformat(),
            'date_message': event.message.date.isoformat(),
            'message_id': str(event.message.id),
            'source': 'vm_scraper_realtime',
            'content': event.message.text[:500],
            'indexed_at': datetime.now(timezone.utc).isoformat(),
            'chat_id': str(chat_id)
        }
        
        total_messages_processed += 1
        
        # Enviar para Kinesis usando buffer otimizado (AWS Best Practices)
        if kinesis_buffer:
            try:
                await kinesis_buffer.add_message(message_data)
                total_kinesis_sent += 1  # Contador otimista (ajustado no flush)
            except Exception as e:
                logger.error("❌ Erro Kinesis Buffer: %s", e)
        
        # Enviar para OpenSearch direto
        if elasticsearch_client and send_message_to_opensearch(message_data, elasticsearch_client):
            total_opensearch_sent += 1
        
        # Log da mensagem processada
        logger.info("📨 NOVA MENSAGEM: %s | %s | Total: %d", 
                   group_username, classification, total_messages_processed)
        
        # Enviar métricas para CloudWatch a cada 10 mensagens
        if total_messages_processed % 10 == 0 and cloudwatch_monitor and cloudwatch_monitor.enabled:
            try:
                cloudwatch_monitor.send_metric('RealtimeMessagesProcessed', total_messages_processed, 'Count')
                cloudwatch_monitor.send_metric('RealtimeKinesisSent', total_kinesis_sent, 'Count')
                cloudwatch_monitor.send_metric('RealtimeOpenSearchSent', total_opensearch_sent, 'Count')
                logger.info("📈 Métricas CloudWatch enviadas (a cada 10 msgs)")
            except Exception as e:
                logger.error("❌ Erro métricas CloudWatch: %s", e)
        
    except Exception as e:
        logger.error("❌ Erro processando mensagem: %s", e)
        logger.error("📋 Traceback: %s", traceback.format_exc())

async def setup_realtime_monitoring(groups_data):
    """Configurar monitoramento em tempo real dos grupos"""
    from telethon import TelegramClient, events
    
    # Validar configurações
    config = validate_environment()
    if not config:
        logger.error("❌ Configuração inválida")
        return None
    
    # Criar cliente Telethon usando ConfigLoader
    from src.utils.config_loader import load_config
    config_loader = load_config()
    telegram_creds = config_loader.get_telegram_credentials()
    session_file = telegram_creds['session_file']
    
    if not os.path.exists(session_file):
        logger.error("❌ Arquivo %s não encontrado", session_file)
        return None
    
    logger.info("🔧 Usando session file: %s", session_file)
    client = TelegramClient(session_file, int(config['api_id']), config['api_hash'])
    
    try:
        await client.start()
        
        if not await client.is_user_authorized():
            logger.error("❌ Usuário não autorizado - session inválida")
            return None
        
        logger.info("✅ Cliente Telegram conectado para streaming")
        
        # Criar dicionário de informações dos grupos (chat_id -> info)
        groups_info_dict = {}
        
        # Obter entidades dos grupos e registrar handlers
        logger.info("🔗 ==> CONECTANDO AOS GRUPOS PARA STREAMING")
        connected_groups = 0
        
        for group_info in groups_data:
            group_username = group_info.get('username', '')
            if not group_username:
                continue
                
            try:
                # Obter entidade do grupo
                entity = await client.get_entity(group_username)
                chat_id = entity.id
                
                # Armazenar informações do grupo
                groups_info_dict[chat_id] = group_info
                
                connected_groups += 1
                logger.info("🔗 [%d/%d] Conectado: %s (ID: %s)", 
                           connected_groups, len(groups_data), group_username, chat_id)
                
            except Exception as e:
                logger.warning("⚠️ Erro conectando a %s: %s", group_username, e)
                continue
        
        logger.info("🎯 Total grupos conectados para streaming: %d/%d", connected_groups, len(groups_data))
        
        # Criar lista de chat_ids dos grupos conectados para filtrar o handler
        connected_chat_ids = list(groups_info_dict.keys())
        logger.info("🔍 Filtrando handler para %d grupos específicos", len(connected_chat_ids))
        
        # Registrar handler APENAS para os grupos conectados (filtro na origem)
        @client.on(events.NewMessage(chats=connected_chat_ids))
        async def handler(event):
            await process_new_message(event, groups_info_dict)
        
        logger.info("📡 ==> STREAMING INICIADO! Escutando mensagens em tempo real...")
        logger.info("📊 Grupos monitorados: %d", connected_groups)
        logger.info("⏹️ Para parar: Ctrl+C")
        
        return client, connected_groups
        
    except Exception as e:
        logger.error("❌ Erro ao configurar streaming: %s", e)
        return None

async def print_stats_periodically():
    """Imprimir estatísticas periodicamente"""
    while running:
        await asyncio.sleep(60)  # A cada 1 minuto
        
        if total_messages_processed > 0:
            logger.info("\n" + "="*80)
            logger.info("📊 ESTATÍSTICAS STREAMING - %s", datetime.now().strftime("%H:%M:%S"))
            logger.info("="*80)
            logger.info("📱 Total mensagens processadas: %d", total_messages_processed)
            logger.info("📡 Enviadas para Kinesis: %d", total_kinesis_sent)
            logger.info("🔍 Enviadas para OpenSearch: %d", total_opensearch_sent)
            logger.info("📈 Classificações: %s", classification_stats)
            logger.info("⏱️ Uptime: %s", datetime.now().strftime("%H:%M:%S"))
            logger.info("="*80)

async def main():
    """Função principal do scraper streaming"""
    global running, kinesis_buffer
    
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 ==> INICIANDO TELEGRAM SCRAPER STREAMING REAL-TIME")
    logger.info("📅 Timestamp: %s", datetime.now(timezone.utc).isoformat())
    logger.info("💾 Logs salvos em: telegram_scraper_realtime.log")
    logger.info("⏹️ Para parar: Ctrl+C")
    
    # Inicializar buffer Kinesis otimizado (AWS Best Practices)
    kinesis_buffer = KinesisBuffer(max_size=100, max_wait_seconds=2)
    logger.info("📦 Kinesis Buffer inicializado: max_size=100, max_wait=2s")
    
    # Inicializar clientes
    es_client = initialize_elasticsearch()
    cw_monitor = initialize_cloudwatch()
    
    # Carregar grupos do Google Sheets
    groups_data = load_groups_from_sheets()
    if not groups_data:
        logger.error("❌ Nenhum grupo carregado. Saindo...")
        return
    
    # Configurar streaming
    streaming_result = await setup_realtime_monitoring(groups_data)
    if not streaming_result:
        logger.error("❌ Falha ao configurar streaming. Saindo...")
        return
    
    client, connected_groups = streaming_result
    
    # Iniciar task de estatísticas
    stats_task = asyncio.create_task(print_stats_periodically())
    
    try:
        logger.info("🔄 ==> SISTEMA EM STREAMING! Processando mensagens conforme chegam...")
        
        # Manter o cliente rodando
        while running:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("🛑 Interrupção pelo usuário")
    
    except Exception as e:
        logger.error("❌ Erro crítico no streaming: %s", e)
        logger.error("📋 Traceback: %s", traceback.format_exc())
    
    finally:
        # Cleanup
        logger.info("🧹 Finalizando streaming...")
        running = False
        
        # Flush final do buffer Kinesis (AWS Best Practice)
        if kinesis_buffer:
            try:
                logger.info("📦 Fazendo flush final do Kinesis Buffer...")
                await kinesis_buffer.flush()
                logger.info("✅ Buffer Kinesis finalizado - Total enviado: %d, Total falhas: %d", 
                           kinesis_buffer.total_sent, kinesis_buffer.total_failed)
            except Exception as e:
                logger.error("❌ Erro no flush final do buffer: %s", e)
        
        # Cancelar task de estatísticas
        if stats_task:
            stats_task.cancel()
        
        # Desconectar cliente
        if client:
            await client.disconnect()
            logger.info("📱 Cliente Telegram desconectado")
        
        # Estatísticas finais
        logger.info("📊 ESTATÍSTICAS FINAIS:")
        logger.info("📱 Total mensagens processadas: %d", total_messages_processed)
        logger.info("📡 Total enviadas Kinesis: %d", total_kinesis_sent)
        logger.info("🔍 Total enviadas OpenSearch: %d", total_opensearch_sent)
        logger.info("📈 Classificações finais: %s", classification_stats)
        logger.info("🏁 ==> TELEGRAM SCRAPER STREAMING FINALIZADO")

if __name__ == "__main__":
    asyncio.run(main())
