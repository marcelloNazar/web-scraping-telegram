#!/usr/bin/env python3
"""
AWS Integration para TelegramScrap
Integração limpa e externa para não poluir o notebook
"""

import boto3
import json
import os
from datetime import datetime
import time

class AWSIntegration:
    """Classe para gerenciar integração AWS completa"""

    def __init__(self):
        self.kinesis_client = None
        self.kinesis_enabled = False
        self.kinesis_stream = 'telegram-messages'
        self.monitor = None
        self.setup_aws()

    def setup_aws(self):
        """Configurar credenciais e clientes AWS"""
        try:
            # Configurar credenciais se necessário
            if not os.environ.get('AWS_ACCESS_KEY_ID'):
                print("⚠️ AWS credentials not found in environment variables")
                print("💡 Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
                self.kinesis_enabled = False
                return

            # Criar cliente Kinesis
            self.kinesis_client = boto3.client('kinesis', region_name='us-east-1')

            # Testar conectividade
            self.kinesis_enabled = self._test_kinesis_connection()

            # Inicializar CloudWatch Monitor
            try:
                import sys
                sys.path.append('./src')
                from utils.monitoring import CloudWatchMonitor
                self.monitor = CloudWatchMonitor()
                print(f"📈 CloudWatch: {'✅ Habilitado' if self.monitor.enabled else '⚠️ Desabilitado'}")
            except ImportError:
                print("⚠️ CloudWatch Monitor não disponível")
                self.monitor = None

        except Exception as e:
            print(f"⚠️ Erro configurando AWS: {e}")
            self.kinesis_enabled = False

    def _test_kinesis_connection(self):
        """Testar conexão Kinesis"""
        try:
            response = self.kinesis_client.describe_stream(StreamName=self.kinesis_stream)
            stream_status = response['StreamDescription']['StreamStatus']

            if stream_status == 'ACTIVE':
                print(f"✅ Kinesis Stream '{self.kinesis_stream}' está ATIVO")
                return True
            else:
                print(f"⚠️ Stream status: {stream_status}")
                return False
        except Exception as e:
            print(f"❌ Erro testando Kinesis: {e}")
            return False

    def send_message_to_kinesis(self, message_data):
        """Enviar mensagem individual para Kinesis"""
        if not self.kinesis_enabled:
            return False

        try:
            # Preparar dados para Kinesis
            kinesis_data = {
                **message_data,
                'sent_to_kinesis_at': datetime.utcnow().isoformat(),
                'source': 'jupyter_notebook',
                'pipeline_version': 'jupyter_kinesis_hybrid_v1'
            }

            # Partition key
            partition_key = str(message_data.get('message_id', 'default'))
            group_name = message_data.get('group_name', '')
            if group_name:
                partition_key = f"{group_name}_{partition_key}"

            # Enviar
            response = self.kinesis_client.put_record(
                StreamName=self.kinesis_stream,
                Data=json.dumps(kinesis_data, ensure_ascii=False),
                PartitionKey=partition_key
            )

            return True

        except Exception as e:
            print(f"❌ Erro enviando para Kinesis: {e}")
            return False

    def send_batch_to_kinesis(self, messages_list):
        """Enviar batch para Kinesis"""
        if not self.kinesis_enabled or not messages_list:
            return 0, len(messages_list) if messages_list else 0

        success_count = 0

        try:
            # Preparar records
            records = []
            for message_data in messages_list:
                kinesis_data = {
                    **message_data,
                    'sent_to_kinesis_at': datetime.utcnow().isoformat(),
                    'source': 'jupyter_notebook_batch',
                    'pipeline_version': 'jupyter_kinesis_hybrid_v1'
                }

                partition_key = str(message_data.get('Message ID', 'default'))
                group_name = message_data.get('Group', '')
                if group_name:
                    partition_key = f"{group_name}_{partition_key}"

                records.append({
                    'Data': json.dumps(kinesis_data, ensure_ascii=False),
                    'PartitionKey': partition_key
                })

            # Enviar em lotes de 500
            batch_size = 500
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                response = self.kinesis_client.put_records(
                    StreamName=self.kinesis_stream,
                    Records=batch
                )

                batch_success = len(batch) - response.get('FailedRecordCount', 0)
                success_count += batch_success

            return success_count, len(messages_list)

        except Exception as e:
            print(f"❌ Erro no batch Kinesis: {e}")
            return success_count, len(messages_list)

    def send_cloudwatch_metrics(self, stats):
        """Enviar métricas para CloudWatch"""
        if self.monitor and hasattr(self.monitor, 'enabled') and self.monitor.enabled:
            try:
                return self.monitor.send_scraping_stats(
                    stats.get('total_messages', 0),
                    stats.get('groups_count', 0),
                    stats.get('pol_count', 0),
                    stats.get('conspira_count', 0),
                    stats.get('naz_count', 0)
                )
            except Exception as e:
                print(f"⚠️ Erro métricas CloudWatch: {e}")
                return False
        return False

    def get_status(self):
        """Retornar status da integração"""
        return {
            'kinesis_enabled': self.kinesis_enabled,
            'kinesis_stream': self.kinesis_stream,
            'cloudwatch_enabled': self.monitor.enabled if self.monitor else False,
            'aws_ready': self.kinesis_enabled
        }

# Funções de conveniência para compatibilidade
def initialize_aws_integration():
    """Inicializar integração AWS"""
    print("🔧 Inicializando integração AWS...")
    aws = AWSIntegration()
    status = aws.get_status()

    if status['aws_ready']:
        print("🚀 Sistema híbrido ativo: Jupyter + AWS")
        print(f"📡 Stream: {status['kinesis_stream']}")
        print(f"📈 CloudWatch: {'✅' if status['cloudwatch_enabled'] else '⚠️'}")
    else:
        print("📝 Modo local apenas (AWS não conectado)")

    return aws

# Instância global para uso no notebook
aws_integration = None

def get_aws_integration():
    """Obter instância da integração AWS"""
    global aws_integration
    if aws_integration is None:
        aws_integration = initialize_aws_integration()
    return aws_integration

# Funções de compatibilidade para o notebook
def send_to_kinesis(message_data):
    """Função de compatibilidade"""
    aws = get_aws_integration()
    return aws.send_message_to_kinesis(message_data)

def send_batch_to_kinesis(messages_list):
    """Função de compatibilidade"""
    aws = get_aws_integration()
    return aws.send_batch_to_kinesis(messages_list)

def test_kinesis_connection():
    """Função de compatibilidade"""
    aws = get_aws_integration()
    return aws.kinesis_enabled