import json
import base64
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Processar mensagens do Kinesis vindas do Jupyter Notebook
    FOCO: Apenas repassar para OpenSearch com mínimo processamento
    """

    print(f"🔄 Lambda iniciado - {len(event.get('Records', []))} mensagens do Kinesis")

    processed_messages = 0
    indexed_messages = 0
    errors = 0

    # Cliente OpenSearch (simples)
    opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')

    for record in event.get('Records', []):
        try:
            # Decodificar dados do Kinesis
            kinesis_data = record['kinesis']['data']
            decoded_data = base64.b64decode(kinesis_data).decode('utf-8')
            message_data = json.loads(decoded_data)

            print(f"📨 Processando: {message_data.get('group_name', 'unknown')}")

            # Adicionar metadados Lambda
            enhanced_message = {
                **message_data,
                'lambda_processed_at': datetime.utcnow().isoformat(),
                'pipeline_version': 'jupyter_kinesis_lambda',
                'kinesis_sequence': record['kinesis']['sequenceNumber']
            }

            # Enviar para OpenSearch via requests direto
            success = send_to_opensearch(enhanced_message, opensearch_endpoint)
            if success:
                indexed_messages += 1
                print(f"✅ Indexado: {enhanced_message.get('message_id')}")

            processed_messages += 1

        except Exception as e:
            print(f"❌ Erro processando: {e}")
            errors += 1
            continue

    # Métricas CloudWatch
    try:
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace='TelegramScrap/Lambda',
            MetricData=[
                {
                    'MetricName': 'ProcessedMessages',
                    'Value': processed_messages,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'IndexedMessages',
                    'Value': indexed_messages,
                    'Unit': 'Count'
                }
            ]
        )
    except Exception as e:
        print(f"⚠️ Erro métricas: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_messages,
            'indexed': indexed_messages,
            'errors': errors
        })
    }

def send_to_opensearch(message, endpoint):
    """Enviar mensagem para OpenSearch usando requests + AWS4Auth"""
    try:
        import requests
        import boto3
        from requests_aws4auth import AWS4Auth

        # Configurar auth
        session = boto3.Session()
        credentials = session.get_credentials()
        region = session.region_name or 'us-east-1'

        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
        )

        # Endpoint de indexação
        index_url = f"{endpoint}/telegram-messages/_doc/{message.get('message_id')}"

        # Enviar
        response = requests.put(
            index_url,
            json=message,
            auth=auth,
            timeout=10,
            verify=False
        )

        return response.status_code in [200, 201]

    except Exception as e:
        print(f"❌ Erro OpenSearch: {e}")
        return False