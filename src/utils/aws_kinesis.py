#!/usr/bin/env python3
"""
AWS Kinesis Client para TelegramScrap
Envia mensagens do Telegram para Kinesis Data Streams em tempo real
"""

import json
import boto3
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError

class KinesisStreamer:
    """Cliente para enviar dados do Telegram para AWS Kinesis"""

    def __init__(self,
                 stream_name: str = "telegram-messages",
                 region_name: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Inicializa cliente Kinesis

        Args:
            stream_name: Nome do stream Kinesis
            region_name: Região AWS
            aws_access_key_id: Chave de acesso AWS (opcional, pode usar IAM role)
            aws_secret_access_key: Chave secreta AWS (opcional, pode usar IAM role)
        """
        self.stream_name = stream_name
        self.region_name = region_name
        self.enabled = False
        self.kinesis_client = None
        self.batch_size = 10  # Enviar em lotes de 10
        self.message_buffer = []
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'batches_sent': 0,
            'last_send_time': None
        }

        # Inicializar cliente
        self._initialize_client(aws_access_key_id, aws_secret_access_key)

    def _initialize_client(self, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """Inicializa cliente Kinesis com credenciais"""
        try:
            # Configurar credenciais
            kwargs = {'region_name': self.region_name}
            if access_key and secret_key:
                kwargs.update({
                    'aws_access_key_id': access_key,
                    'aws_secret_access_key': secret_key
                })

            self.kinesis_client = boto3.client('kinesis', **kwargs)

            # Testar conectividade
            self._test_connection()
            self.enabled = True
            print(f"✅ Kinesis conectado: stream '{self.stream_name}' na região {self.region_name}")

        except (NoCredentialsError, ClientError) as e:
            print(f"⚠️ Kinesis não disponível: {e}")
            print("📝 Continuando sem streaming (apenas logs locais)")
            self.enabled = False

    def _test_connection(self):
        """Testa conexão com Kinesis"""
        try:
            response = self.kinesis_client.describe_stream(StreamName=self.stream_name)
            status = response['StreamDescription']['StreamStatus']

            if status != 'ACTIVE':
                raise Exception(f"Stream não está ativo: {status}")

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"⚠️ Stream '{self.stream_name}' não existe. Criando...")
                self._create_stream()
            else:
                raise e

    def _create_stream(self, shard_count: int = 1):
        """Cria stream Kinesis se não existir"""
        try:
            self.kinesis_client.create_stream(
                StreamName=self.stream_name,
                ShardCount=shard_count
            )
            print(f"⏳ Aguardando criação do stream '{self.stream_name}'...")

            # Aguardar stream ficar ativo
            waiter = self.kinesis_client.get_waiter('stream_exists')
            waiter.wait(StreamName=self.stream_name)

            print(f"✅ Stream '{self.stream_name}' criado com sucesso")

        except ClientError as e:
            print(f"❌ Erro ao criar stream: {e}")
            raise e

    def send_message(self, message_data: Dict[str, Any], partition_key: Optional[str] = None) -> bool:
        """
        Envia mensagem individual para Kinesis

        Args:
            message_data: Dados da mensagem
            partition_key: Chave de partição (usa group como padrão)

        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if not self.enabled:
            return False

        try:
            # Preparar dados
            prepared_data = self._prepare_message(message_data)

            # Definir partition key
            if not partition_key:
                partition_key = message_data.get('group', 'default')

            # Enviar para Kinesis
            response = self.kinesis_client.put_record(
                StreamName=self.stream_name,
                Data=json.dumps(prepared_data, ensure_ascii=False, default=str),
                PartitionKey=partition_key
            )

            # Atualizar estatísticas
            self.stats['messages_sent'] += 1
            self.stats['last_send_time'] = datetime.now()

            return True

        except Exception as e:
            print(f"❌ Erro ao enviar mensagem para Kinesis: {e}")
            self.stats['messages_failed'] += 1
            return False

    def send_batch(self, messages: List[Dict[str, Any]]) -> int:
        """
        Envia lote de mensagens para Kinesis

        Args:
            messages: Lista de mensagens

        Returns:
            Número de mensagens enviadas com sucesso
        """
        if not self.enabled or not messages:
            return 0

        try:
            # Preparar records para batch
            records = []
            for msg in messages:
                prepared_data = self._prepare_message(msg)
                partition_key = msg.get('group', 'default')

                records.append({
                    'Data': json.dumps(prepared_data, ensure_ascii=False, default=str),
                    'PartitionKey': partition_key
                })

            # Enviar batch
            response = self.kinesis_client.put_records(
                StreamName=self.stream_name,
                Records=records
            )

            # Contar sucessos
            successful = len(records) - response['FailedRecordCount']

            # Atualizar estatísticas
            self.stats['messages_sent'] += successful
            self.stats['messages_failed'] += response['FailedRecordCount']
            self.stats['batches_sent'] += 1
            self.stats['last_send_time'] = datetime.now()

            if response['FailedRecordCount'] > 0:
                print(f"⚠️ {response['FailedRecordCount']} mensagens falharam no batch")

            return successful

        except Exception as e:
            print(f"❌ Erro ao enviar batch para Kinesis: {e}")
            self.stats['messages_failed'] += len(messages)
            return 0

    def add_to_buffer(self, message_data: Dict[str, Any]):
        """
        Adiciona mensagem ao buffer para envio em batch

        Args:
            message_data: Dados da mensagem
        """
        self.message_buffer.append(message_data)

        # Enviar batch se buffer está cheio
        if len(self.message_buffer) >= self.batch_size:
            self.flush_buffer()

    def flush_buffer(self) -> int:
        """
        Envia todas as mensagens do buffer

        Returns:
            Número de mensagens enviadas
        """
        if not self.message_buffer:
            return 0

        sent_count = self.send_batch(self.message_buffer)
        self.message_buffer.clear()

        return sent_count

    def _prepare_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara mensagem para envio (adiciona metadados)"""
        prepared = message_data.copy()

        # Adicionar timestamp se não existir
        if 'timestamp' not in prepared:
            prepared['timestamp'] = datetime.now().isoformat()

        # Adicionar metadata
        prepared['metadata'] = {
            'source': 'telegram-scraper',
            'version': '1.0',
            'processed_at': datetime.now().isoformat()
        }

        # Garantir que campos obrigatórios existam
        required_fields = ['group', 'content', 'date']
        for field in required_fields:
            if field not in prepared:
                prepared[field] = None

        return prepared

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de envio"""
        return self.stats.copy()

    def reset_stats(self):
        """Reseta estatísticas"""
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'batches_sent': 0,
            'last_send_time': None
        }

    def is_healthy(self) -> bool:
        """Verifica se o serviço está saudável"""
        if not self.enabled:
            return False

        try:
            # Verificar status do stream
            response = self.kinesis_client.describe_stream(StreamName=self.stream_name)
            status = response['StreamDescription']['StreamStatus']
            return status == 'ACTIVE'

        except Exception:
            return False

    def close(self):
        """Finaliza cliente (envia buffer restante)"""
        if self.message_buffer:
            print(f"📤 Enviando {len(self.message_buffer)} mensagens restantes...")
            self.flush_buffer()

        print(f"📊 Estatísticas finais: {self.get_stats()}")


# Função de conveniência
def create_kinesis_streamer(stream_name: str = "telegram-messages",
                          region: str = "us-east-1") -> KinesisStreamer:
    """
    Cria cliente Kinesis com configurações padrão

    Args:
        stream_name: Nome do stream
        region: Região AWS

    Returns:
        Cliente Kinesis configurado
    """
    return KinesisStreamer(stream_name=stream_name, region_name=region)


# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade
    print("🧪 Testando KinesisStreamer...")

    kinesis = KinesisStreamer()

    if kinesis.enabled:
        # Mensagem de teste
        test_message = {
            'group': '@test_group',
            'content': 'Mensagem de teste',
            'date': datetime.now().isoformat(),
            'views': 100,
            'reactions': 5,
            'classification': 'TEST'
        }

        # Testar envio individual
        success = kinesis.send_message(test_message)
        print(f"📤 Envio individual: {'✅' if success else '❌'}")

        # Testar envio em batch
        test_batch = [test_message.copy() for _ in range(3)]
        sent_count = kinesis.send_batch(test_batch)
        print(f"📦 Batch enviado: {sent_count}/3 mensagens")

        # Mostrar estatísticas
        print(f"📊 Estatísticas: {kinesis.get_stats()}")

        kinesis.close()
    else:
        print("⚠️ Kinesis não está habilitado")