#!/usr/bin/env python3
"""
Lambda Function - Telegram Scraper COMPLETO
Carrega grupos do Google Sheets, faz scraping e envia para Kinesis + OpenSearch
"""

import json
import boto3
import os
import sys
from datetime import datetime, timezone
import logging
import traceback

# Adicionar src ao path para imports
sys.path.append('./src')

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS globais (fora do handler)
kinesis_client = boto3.client(
    'kinesis', 
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
    config=boto3.session.Config(
        connect_timeout=30,
        read_timeout=30
    )
)

# Cliente OpenSearch global
elasticsearch_client = None

# Cliente CloudWatch global
cloudwatch_monitor = None

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
        # Fallback para grupo de teste em caso de erro (apenas 1 para teste)
        fallback_groups = [
            {'username': '@SputnikBrasil', 'spectrum': 'right', 'active': True}
        ]
        logger.warning("⚠️ ERRO: Google Sheets falhou! Usando apenas 1 grupo de teste: %d grupos", len(fallback_groups))
        return fallback_groups

def lambda_handler(event, context):
    """Handler principal da Lambda function"""
    logger.info("🚀 ==> INICIANDO LAMBDA TELEGRAM SCRAPER COMPLETO")
    logger.info("📅 Timestamp: %s", datetime.now(timezone.utc).isoformat())
    
    try:
        # 1. Validar configurações
        config = validate_environment()
        if 'error' in config:
            return config
        
        # 2. Carregar grupos do Google Sheets
        groups_data = load_groups_from_sheets()
        if not groups_data:
            logger.error("❌ Nenhum grupo carregado")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Nenhum grupo carregado do Google Sheets'})
            }
        
        # 3. Inicializar OpenSearch
        es_client = initialize_elasticsearch()
        if not es_client:
            logger.warning("⚠️ OpenSearch não disponível - apenas Kinesis será usado")
        
        # 4. Inicializar CloudWatch
        cw_monitor = initialize_cloudwatch()
        if not cw_monitor:
            logger.warning("⚠️ CloudWatch não disponível - sem métricas")
        
        # 5. Preparar sessão Telegram
        client = setup_telegram_client(config['api_id'], config['api_hash'])
        if not client:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Falha na autenticação Telegram'})
            }
        
        # 6. Fazer scraping com grupos do Google Sheets
        total_messages, total_sent_kinesis, total_sent_opensearch, classification_stats = process_telegram_groups_complete(
            client, groups_data, es_client
        )
        
        # 7. Enviar métricas para CloudWatch
        if cw_monitor and cw_monitor.enabled:
            try:
                cw_monitor.send_scraping_stats(
                    total_messages,
                    len(groups_data),
                    classification_stats.get('POL', 0),
                    classification_stats.get('CONSPIRA', 0),
                    classification_stats.get('NAZ', 0)
                )
                # Métricas adicionais específicas da Lambda
                cw_monitor.send_metric('Lambda_Executions', 1, 'Count')
                cw_monitor.send_metric('KinesisSent', total_sent_kinesis, 'Count')
                cw_monitor.send_metric('OpenSearchSent', total_sent_opensearch, 'Count')
                logger.info("📈 Métricas CloudWatch enviadas com sucesso")
            except Exception as e:
                logger.error("❌ Erro ao enviar métricas CloudWatch: %s", e)
        
        # 8. Cleanup
        client.disconnect()
        logger.info("📱 Cliente Telegram desconectado")
        
        # 9. Resultado final
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'message': '✅ Scraping completo concluído com sucesso!',
                'total_messages_found': total_messages,
                'total_sent_to_kinesis': total_sent_kinesis,
                'total_sent_to_opensearch': total_sent_opensearch,
                'groups_processed': len(groups_data),
                'google_sheets_groups': len(groups_data),
                'classification_stats': classification_stats,
                'cloudwatch_enabled': cw_monitor.enabled if cw_monitor else False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }
        
        logger.info("🎉 SUCESSO COMPLETO: %d mensagens encontradas", total_messages)
        logger.info("📡 Kinesis: %d enviadas | 🔍 OpenSearch: %d enviadas", 
                   total_sent_kinesis, total_sent_opensearch)
        logger.info("📊 Grupos processados: %d (do Google Sheets)", len(groups_data))
        logger.info("📈 Classificações: POL=%d, CONSPIRA=%d, NAZ=%d, OTHER=%d",
                   classification_stats.get('POL', 0), classification_stats.get('CONSPIRA', 0),
                   classification_stats.get('NAZ', 0), classification_stats.get('OTHER', 0))
        logger.info("🏁 ==> LAMBDA TELEGRAM SCRAPER FINALIZADA")
        
        return result
        
    except Exception as e:
        error_msg = "❌ Erro crítico na Lambda: %s" % str(e)
        logger.error(error_msg)
        logger.error("📋 Traceback: %s", traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

def validate_environment():
    """Validar variáveis de ambiente"""
    api_id = os.environ.get('TELEGRAM_API_ID')
    api_hash = os.environ.get('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        logger.error("❌ Variáveis de ambiente não configuradas")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Variáveis de ambiente não configuradas'})
        }
    
    logger.info("🔑 API ID: %s", api_id)
    logger.info("🔑 API Hash: %s...", api_hash[:8])
    
    return {'api_id': api_id, 'api_hash': api_hash}

def setup_telegram_client(api_id, api_hash):
    """Configurar e conectar cliente Telegram"""
    try:
        # Importar Telethon
        logger.info("📦 Importando Telethon...")
        from telethon.sync import TelegramClient
        logger.info("✅ Telethon importado com sucesso")
        
        # Preparar arquivo de sessão
        session_file = '/tmp/ergoncugler_cinco.session'
        
        import shutil
        if os.path.exists('ergoncugler_cinco.session'):
            shutil.copy('ergoncugler_cinco.session', session_file)
            logger.info("✅ Arquivo session copiado para /tmp")
        else:
            logger.error("❌ Arquivo ergoncugler_cinco.session não encontrado")
            return None
        
        # Conectar
        logger.info("📱 Conectando ao Telegram...")
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

def process_telegram_groups_complete(client, groups_data, es_client):
    """Processar grupos Telegram completos com Google Sheets, Kinesis e OpenSearch"""
    from telethon.errors import FloodWaitError
    
    logger.info("📋 ==> PROCESSANDO GRUPOS DO GOOGLE SHEETS")
    logger.info("📊 Total grupos a processar: %d", len(groups_data))
    
    total_messages = 0
    total_sent_kinesis = 0
    total_sent_opensearch = 0
    classification_stats = {'POL': 0, 'CONSPIRA': 0, 'NAZ': 0, 'OTHER': 0}
    
    # Limitar para teste (primeiro máx 10 grupos para não ultrapassar limites)
    groups_to_process = groups_data[:10]  # Ajuste conforme necessário
    logger.info("📝 Processando primeiros %d grupos para teste", len(groups_to_process))
    
    for i, group_info in enumerate(groups_to_process):
        group_username = group_info.get('username', '')
        group_spectrum = group_info.get('spectrum', 'unknown')
        
        if not group_username:
            continue
            
        logger.info("📱 ==> [%d/%d] Processando: %s (%s)", 
                   i+1, len(groups_to_process), group_username, group_spectrum)
        
        try:
            # Buscar últimas mensagens (limite baixo para não ultrapassar rate limits)
            messages = client.get_messages(group_username, limit=3)
            logger.info("📥 Encontradas %d mensagens em %s", len(messages), group_username)
            
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
                        'source': 'lambda_scraper_sheets',
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
    
    logger.info("📊 ESTATÍSTICAS FINAIS:")
    logger.info("📱 Total mensagens: %d", total_messages)
    logger.info("📡 Kinesis enviadas: %d", total_sent_kinesis)
    logger.info("🔍 OpenSearch enviadas: %d", total_sent_opensearch)
    logger.info("📈 Classificações: %s", classification_stats)
    
    return total_messages, total_sent_kinesis, total_sent_opensearch, classification_stats

def process_telegram_groups(client):
    """Processar grupos Telegram (função legacy)"""
    from telethon.errors import FloodWaitError
    
    groups = ['@SputnikBrasil', '@rt_brasil', '@plenonews']
    logger.info("📋 Grupos para scraping: %s", groups)
    
    total_messages = 0
    total_sent = 0
    
    for group in groups:
        logger.info("📱 ==> Fazendo scraping do grupo: %s", group)
        
        try:
            messages = client.get_messages(group, limit=5)
            logger.info("📥 Encontradas %d mensagens em %s", len(messages), group)
            
            for msg in messages:
                if msg.text and len(msg.text.strip()) > 10:
                    total_messages += 1
                    
                    if send_message_to_kinesis(msg, group):
                        total_sent += 1
            
        except FloodWaitError as flood_error:
            logger.warning("⏳ Rate limit para %s: aguardar %ds", group, flood_error.seconds)
            continue
            
        except Exception as group_error:
            logger.error("❌ Erro no grupo %s: %s", group, group_error)
            continue
    
    return total_messages, total_sent

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

def send_message_to_kinesis(msg, group):
    """Enviar mensagem individual para Kinesis (função legacy)"""
    try:
        classification = classify_message(msg.text)
        
        message_data = {
            'message': msg.text[:800],
            'group_name': group,
            'classification': classification,
            'timestamp': msg.date.isoformat(),
            'date_message': msg.date.isoformat(),
            'message_id': str(msg.id),
            'source': 'lambda_scraper',
            'content': msg.text[:500],
            'indexed_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = kinesis_client.put_record(
            StreamName='telegram-messages',
            Data=json.dumps(message_data),
            PartitionKey=group
        )
        
        logger.info("📡 ✅ Kinesis: %s | %s | Seq: %s...", 
                   group, classification, response['SequenceNumber'][:10])
        return True
        
    except Exception as kinesis_error:
        logger.error("❌ Erro Kinesis para %s: %s", group, kinesis_error)
        return False

def classify_message(text):
    """
    Classificação simples de mensagens baseada em keywords
    """
    if not text:
        return 'OTHER'
    
    text_lower = text.lower()
    
    # Keywords para classificação
    pol_keywords = [
        'eleição', 'político', 'governo', 'presidente', 'deputado', 'senador',
        'ministro', 'congresso', 'câmara', 'senado', 'supremo', 'stf',
        'política', 'partidário', 'eleitor', 'voto', 'urna', 'democracia'
    ]
    
    conspira_keywords = [
        'conspiração', 'illuminati', 'nova ordem', 'globalista', 'elite global',
        'deep state', 'estado profundo', 'maçonaria', 'reptiliano', 'chemtrail',
        'terra plana', 'vacina', 'microchip', 'controle mental'
    ]
    
    # Verificar classificação
    if any(word in text_lower for word in conspira_keywords):
        return 'CONSPIRA'
    elif any(word in text_lower for word in pol_keywords):
        return 'POL'
    else:
        return 'OTHER'
