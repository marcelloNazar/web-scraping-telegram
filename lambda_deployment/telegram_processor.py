import json
import base64
import boto3
from datetime import datetime
import re

# Cliente Elasticsearch
es_client = None

def lambda_handler(event, context):
    """
    Processa mensagens do Kinesis e envia para Elasticsearch
    """

    processed_messages = 0
    indexed_messages = 0

    print(f"Recebidas {len(event['Records'])} mensagens do Kinesis")

    for record in event['Records']:
        try:
            # Decodificar dados do Kinesis
            kinesis_data = record['kinesis']['data']
            decoded_data = base64.b64decode(kinesis_data).decode('utf-8')
            message_data = json.loads(decoded_data)

            # Processar mensagem
            processed_msg = process_telegram_message(message_data)

            # Enviar para Elasticsearch (quando disponível)
            if es_client and es_client.enabled:
                success = es_client.index_message(processed_msg)
                if success:
                    indexed_messages += 1

            processed_messages += 1

        except Exception as e:
            print(f"Erro processando mensagem: {e}")
            continue

    # Enviar métricas CloudWatch
    cloudwatch = boto3.client('cloudwatch')
    try:
        cloudwatch.put_metric_data(
            Namespace='TelegramScrap/Lambda',
            MetricData=[
                {
                    'MetricName': 'ProcessedMessages',
                    'Value': processed_messages,
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': 'IndexedMessages',
                    'Value': indexed_messages,
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                }
            ]
        )
    except Exception as e:
        print(f"Erro enviando métricas: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_messages,
            'indexed': indexed_messages
        })
    }

def process_telegram_message(message_data):
    """Processar e enriquecer dados da mensagem"""

    # Classificação automática
    content = message_data.get('content', '').lower()

    # Classificação POL/CONSPIRA/NAZ
    if any(word in content for word in ['governo', 'presidente', 'política', 'eleição']):
        category_1 = 'POL'
    elif any(word in content for word in ['conspiração', 'illuminati', 'deep state']):
        category_1 = 'CONSPIRA'
    elif any(word in content for word in ['supremacia', 'hitler', 'nazismo']):
        category_1 = 'NAZ'
    else:
        category_1 = 'OTHER'

    # Espectro político
    if any(word in content for word in ['bolsonaro', 'direita', 'conservador']):
        category_4 = 'Right'
    elif any(word in content for word in ['lula', 'esquerda', 'progressista']):
        category_4 = 'Left'
    else:
        category_4 = 'General'

    # Análise de sentimento básica
    positive_words = ['bom', 'ótimo', 'excelente', 'sucesso', 'vitória']
    negative_words = ['ruim', 'péssimo', 'terrível', 'fracasso', 'derrota']

    positive_count = sum(1 for word in positive_words if word in content)
    negative_count = sum(1 for word in negative_words if word in content)

    if positive_count > negative_count:
        sentiment = 'positive'
    elif negative_count > positive_count:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'

    # Extrair tokens para word cloud
    content_tokens = re.findall(r'\b\w{4,}\b', content)  # Palavras com 4+ caracteres

    # Enriquecer dados
    message_data.update({
        'category_1': category_1,
        'category_4': category_4,
        'sentiment': sentiment,
        'content_tokens': content_tokens[:20],  # Top 20 palavras
        'lambda_processed_at': datetime.now().isoformat()
    })

    return message_data

def classify_group_type(group_name):
    """Classificar tipo do grupo baseado no nome"""
    name_lower = group_name.lower()

    if any(word in name_lower for word in ['news', 'noticia', 'jornal']):
        return 'News'
    elif any(word in name_lower for word in ['bolsonaro', 'lula', 'político']):
        return 'Political'
    elif any(word in name_lower for word in ['brasil', 'brazil']):
        return 'National'
    else:
        return 'General'