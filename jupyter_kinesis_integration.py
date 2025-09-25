# ===============================================================
# TELEGRAMSCRAP - INTEGRAÇÃO JUPYTER → KINESIS
# ===============================================================
# Código para adicionar no Jupyter Notebook TelegramScrap
# Enviar dados processados diretamente para AWS Kinesis Stream

import boto3
import json
from datetime import datetime

# ===============================================================
# CONFIGURAÇÃO KINESIS
# ===============================================================

# Cliente Kinesis AWS
kinesis_client = boto3.client('kinesis', region_name='us-east-1')
KINESIS_STREAM = 'telegram-messages'
KINESIS_ENABLED = True

def send_to_kinesis(message_data):
    """
    Enviar mensagem para Kinesis Stream

    Args:
        message_data (dict): Dados da mensagem processada do Telegram

    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    try:
        if not KINESIS_ENABLED:
            print("⚠️ Kinesis desabilitado - salvando apenas localmente")
            return False

        # Preparar dados para Kinesis
        kinesis_data = {
            **message_data,
            'sent_to_kinesis_at': datetime.utcnow().isoformat(),
            'source': 'jupyter_notebook',
            'pipeline_version': 'jupyter_kinesis_hybrid_v1'
        }

        # Determinar partition key baseado no grupo
        partition_key = str(message_data.get('message_id', 'default'))
        group_name = message_data.get('group_name', '')
        if group_name:
            partition_key = f"{group_name}_{partition_key}"

        # Enviar para stream
        response = kinesis_client.put_record(
            StreamName=KINESIS_STREAM,
            Data=json.dumps(kinesis_data, ensure_ascii=False),
            PartitionKey=partition_key
        )

        # Log de sucesso
        msg_id = message_data.get('message_id', 'unknown')
        group = message_data.get('group_name', 'unknown')
        classification = message_data.get('classification', 'unknown')

        print(f"✅ → Kinesis: {group} | {msg_id} | {classification}")
        return True

    except Exception as e:
        print(f"❌ Erro enviando para Kinesis: {e}")
        print(f"   Dados: {message_data.get('group_name', 'unknown')} - {message_data.get('message_id', 'unknown')}")
        return False

def send_batch_to_kinesis(messages_list):
    """
    Enviar múltiplas mensagens para Kinesis em batch (mais eficiente)

    Args:
        messages_list (list): Lista de mensagens para enviar

    Returns:
        tuple: (success_count, total_count)
    """
    if not KINESIS_ENABLED or not messages_list:
        return 0, len(messages_list) if messages_list else 0

    success_count = 0

    try:
        # Preparar batch de records
        records = []
        for message_data in messages_list:
            kinesis_data = {
                **message_data,
                'sent_to_kinesis_at': datetime.utcnow().isoformat(),
                'source': 'jupyter_notebook_batch',
                'pipeline_version': 'jupyter_kinesis_hybrid_v1'
            }

            partition_key = str(message_data.get('message_id', 'default'))
            group_name = message_data.get('group_name', '')
            if group_name:
                partition_key = f"{group_name}_{partition_key}"

            records.append({
                'Data': json.dumps(kinesis_data, ensure_ascii=False),
                'PartitionKey': partition_key
            })

        # Enviar em lotes de 500 (limite Kinesis)
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            response = kinesis_client.put_records(
                StreamName=KINESIS_STREAM,
                Records=batch
            )

            # Contar sucessos
            batch_success = len(batch) - response.get('FailedRecordCount', 0)
            success_count += batch_success

            if response.get('FailedRecordCount', 0) > 0:
                print(f"⚠️ Batch {i//batch_size + 1}: {response['FailedRecordCount']} falhas de {len(batch)}")
            else:
                print(f"✅ Batch {i//batch_size + 1}: {len(batch)} mensagens enviadas")

        print(f"🎯 Total enviado para Kinesis: {success_count}/{len(messages_list)} mensagens")
        return success_count, len(messages_list)

    except Exception as e:
        print(f"❌ Erro no batch para Kinesis: {e}")
        return success_count, len(messages_list)

def test_kinesis_connection():
    """
    Testar conexão com Kinesis Stream

    Returns:
        bool: True se conexão OK, False caso contrário
    """
    try:
        # Verificar se stream existe
        response = kinesis_client.describe_stream(StreamName=KINESIS_STREAM)
        stream_status = response['StreamDescription']['StreamStatus']

        if stream_status == 'ACTIVE':
            print(f"✅ Kinesis Stream '{KINESIS_STREAM}' está ATIVO")

            # Informações do stream
            shard_count = len(response['StreamDescription']['Shards'])
            retention = response['StreamDescription']['RetentionPeriodHours']
            print(f"   📊 Shards: {shard_count}, Retenção: {retention}h")

            return True
        else:
            print(f"⚠️ Stream status: {stream_status}")
            return False

    except Exception as e:
        print(f"❌ Erro testando Kinesis: {e}")
        return False

# ===============================================================
# CÓDIGO PARA USAR NO JUPYTER NOTEBOOK
# ===============================================================

def initialize_kinesis_integration():
    """
    Inicializar integração Kinesis no Jupyter
    Executar esta função no início do notebook
    """
    print("🔧 Inicializando integração TelegramScrap → AWS Kinesis...")
    print(f"📡 Stream: {KINESIS_STREAM}")
    print(f"🌍 Região: us-east-1")

    # Testar conexão
    if test_kinesis_connection():
        global KINESIS_ENABLED
        KINESIS_ENABLED = True
        print("✅ Integração Kinesis ATIVA - dados serão enviados para AWS")
        return True
    else:
        KINESIS_ENABLED = False
        print("❌ Integração Kinesis DESABILITADA - dados apenas locais")
        return False

def process_message_with_kinesis(message_data):
    """
    Processar mensagem e enviar para Kinesis
    Usar esta função no lugar do append normal

    Args:
        message_data (dict): Dados da mensagem processada

    Usage no Jupyter:
        # Ao invés de: data.append(message_data)
        # Usar:
        data.append(message_data)  # Manter para arquivo local
        process_message_with_kinesis(message_data)  # Enviar para AWS
    """

    # Validar dados essenciais
    if not message_data.get('message_id'):
        print("⚠️ Mensagem sem ID - pulando Kinesis")
        return False

    if not message_data.get('group_name'):
        print("⚠️ Mensagem sem grupo - pulando Kinesis")
        return False

    # Enviar para Kinesis
    return send_to_kinesis(message_data)

# ===============================================================
# EXEMPLO DE USO NO JUPYTER NOTEBOOK
# ===============================================================

"""
# ===== ADICIONAR ESTA CÉLULA NO INÍCIO DO JUPYTER =====

# Importar integração Kinesis
exec(open('jupyter_kinesis_integration.py').read())

# Inicializar
kinesis_active = initialize_kinesis_integration()

if kinesis_active:
    print("🚀 Sistema híbrido ativo: Jupyter + AWS")
else:
    print("📝 Modo local apenas")

# ===== MODIFICAR O LOOP PRINCIPAL DO SCRAPING =====

# No loop onde você processa mensagens, SUBSTITUIR:
# data.append(message_data)

# PELO CÓDIGO:
data.append(message_data)  # Manter arquivo local
process_message_with_kinesis(message_data)  # Enviar para AWS

# ===== OPCIONAL: ENVIO EM BATCH NO FINAL =====

# Após coletar todas as mensagens, enviar batch:
if kinesis_active and data:
    print(f"📤 Enviando batch final de {len(data)} mensagens...")
    success, total = send_batch_to_kinesis(data)
    print(f"✅ Enviado para AWS: {success}/{total} mensagens")
"""