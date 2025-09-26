#!/usr/bin/env python3
"""
Telegram Scraper VM Continuous
Roda continuamente na VM fazendo scraping e enviando para Kinesis + OpenSearch
"""

import json
import boto3
import os
import sys
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

def send_message_to_kinesis_complete(message_data, group):
    """Enviar dados completos para Kinesis"""
    try:
        response = kinesis_client.put_record(
            StreamName='telegram-messages',
            Data=json.dumps(message_data),
            PartitionKey=group
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

def process_telegram_groups_continuous(client, groups_data, es_client, execution_count=1):
    """Processar grupos Telegram para execução contínua com rotação pelos 204 grupos"""
    from telethon.errors import FloodWaitError
    import time
    
    logger.info("📋 ==> PROCESSANDO GRUPOS DO GOOGLE SHEETS")
    logger.info("📊 Total grupos disponíveis: %d", len(groups_data))
    
    total_messages = 0
    total_sent_kinesis = 0
    total_sent_opensearch = 0
    classification_stats = {'POL': 0, 'CONSPIRA': 0, 'NAZ': 0, 'OTHER': 0}
    
    # Estratégia: Processar 30 grupos por execução com rotação
    groups_per_execution = 30
    start_index = ((execution_count - 1) * groups_per_execution) % len(groups_data)
    end_index = min(start_index + groups_per_execution, len(groups_data))
    
    # Se chegou ao final, pegar o resto do começo
    if end_index == len(groups_data) and start_index + groups_per_execution > len(groups_data):
        groups_to_process = groups_data[start_index:] + groups_data[:groups_per_execution - (len(groups_data) - start_index)]
    else:
        groups_to_process = groups_data[start_index:end_index]
    
    logger.info("📝 Processando %d grupos nesta execução (posições %d-%d)", 
               len(groups_to_process), start_index + 1, 
               (start_index + len(groups_to_process)) % len(groups_data) if start_index + len(groups_to_process) > len(groups_data) else start_index + len(groups_to_process))
    
    # Mostrar ciclo completo
    total_executions_for_cycle = (len(groups_data) + groups_per_execution - 1) // groups_per_execution
    current_cycle_position = ((execution_count - 1) % total_executions_for_cycle) + 1
    logger.info("🔄 Ciclo: %d/%d (todos os %d grupos serão processados em %d execuções)", 
               current_cycle_position, total_executions_for_cycle, len(groups_data), total_executions_for_cycle)
    
    for i, group_info in enumerate(groups_to_process):
        group_username = group_info.get('username', '')
        group_spectrum = group_info.get('spectrum', 'unknown')
        
        if not group_username:
            continue
            
        logger.info("📱 ==> [%d/%d] Processando: %s (%s)", 
                   i+1, len(groups_to_process), group_username, group_spectrum)
        
        try:
            # Buscar últimas mensagens (aumentando limite para mais dados)
            messages = client.get_messages(group_username, limit=3)
            logger.info("📥 Encontradas %d mensagens em %s", len(messages), group_username)
            
            # Rate limiting: pausa de 1 segundo entre grupos para evitar flood
            if i < len(groups_to_process) - 1:  # Não pausar no último
                time.sleep(1)
            
            for msg in messages:
                if msg.text and len(msg.text.strip()) > 10:
                    total_messages += 1
                    
                    # Classificar mensagem
                    classification = classify_message(msg.text)
                    classification_stats[classification] = classification_stats.get(classification, 0) + 1
                    
                    # Preparar dados com informações do Google Sheets
                    message_data = {
                        'message': msg.text[:800],
                        'group_name': group_username,
                        'group_spectrum': group_spectrum,
                        'classification': classification,
                        'timestamp': msg.date.isoformat(),
                        'date_message': msg.date.isoformat(),
                        'message_id': str(msg.id),
                        'source': 'vm_scraper_continuous',
                        'content': msg.text[:500],
                        'indexed_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Enviar para Kinesis
                    if send_message_to_kinesis_complete(message_data, group_username):
                        total_sent_kinesis += 1
                        logger.info("📡 ✅ Kinesis: %s | %s", group_username, classification)
                    
                    # Enviar para OpenSearch direto
                    if es_client and send_message_to_opensearch(message_data, es_client):
                        total_sent_opensearch += 1
                        logger.info("🔍 ✅ OpenSearch: %s | %s", group_username, classification)
            
        except FloodWaitError as flood_error:
            logger.warning("⏳ Rate limit para %s: aguardar %ds", group_username, flood_error.seconds)
            continue
            
        except Exception as group_error:
            logger.error("❌ Erro no grupo %s: %s", group_username, group_error)
            continue
    
    logger.info("📊 ESTATÍSTICAS DESTA EXECUÇÃO:")
    logger.info("📱 Total mensagens: %d", total_messages)
    logger.info("📡 Kinesis enviadas: %d", total_sent_kinesis)
    logger.info("🔍 OpenSearch enviadas: %d", total_sent_opensearch)
    logger.info("📈 Classificações: %s", classification_stats)
    
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
    logger.info("⏹️ Para parar: Ctrl+C")
    
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
    
    logger.info("🔄 ==> INICIANDO LOOP CONTÍNUO (execução a cada 2 minutos)")
    
    try:
        while running:
            execution_count += 1
            logger.info("\n" + "="*80)
            logger.info("🔄 EXECUÇÃO #%d - %s", execution_count, datetime.now().strftime("%H:%M:%S"))
            logger.info("="*80)
            
            # Fazer scraping com rotação pelos 204 grupos
            messages, kinesis_sent, opensearch_sent, classification_stats = process_telegram_groups_continuous(
                client, groups_data, es_client, execution_count
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
                logger.info("⏳ Aguardando 2 minutos para próxima execução...")
                logger.info("⏹️ Para parar: Ctrl+C")
                
                # Aguardar 2 minutos (com verificação a cada 10 segundos)
                for i in range(12):  # 12 * 10 = 120 segundos = 2 minutos
                    if not running:
                        break
                    time.sleep(10)
                    if (i + 1) % 6 == 0:  # Log a cada minuto
                        logger.info("⏳ %d minuto(s) restante(s)...", 2 - (i + 1) // 6)
    
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
