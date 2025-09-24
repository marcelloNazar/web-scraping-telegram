#!/usr/bin/env python3
"""
AWS Elasticsearch Client para TelegramScrap
Interface para Amazon Elasticsearch Service (OpenSearch)
"""

import json
import boto3
import requests
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from requests.auth import HTTPBasicAuth
from botocore.exceptions import ClientError, NoCredentialsError
import urllib3

# Suprimir warnings SSL para desenvolvimento
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ElasticsearchClient:
    """Cliente para interagir com AWS Elasticsearch/OpenSearch"""

    def __init__(self,
                 domain_name: str = None,
                 region_name: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Inicializa cliente Elasticsearch

        Args:
            domain_name: Nome do domínio Elasticsearch
            region_name: Região AWS
            aws_access_key_id: Chave de acesso AWS (opcional)
            aws_secret_access_key: Chave secreta AWS (opcional)
        """
        # Usar variável de ambiente ou parâmetro ou fallback
        if domain_name is None:
            domain_name = os.getenv('OPENSEARCH_DOMAIN', 'telegramscrap-search')
        
        self.domain_name = domain_name
        self.region_name = region_name
        self.enabled = False
        self.es_client = None
        self.domain_endpoint = None
        self.index_name = "telegram-messages"
        self.stats = {
            'documents_indexed': 0,
            'indexing_errors': 0,
            'last_index_time': None
        }

        # Inicializar cliente
        self._initialize_client(aws_access_key_id, aws_secret_access_key)

    def _initialize_client(self, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """Inicializa cliente Elasticsearch"""
        try:
            # Configurar credenciais
            kwargs = {'region_name': self.region_name}
            if access_key and secret_key:
                kwargs.update({
                    'aws_access_key_id': access_key,
                    'aws_secret_access_key': secret_key
                })

            self.es_client = boto3.client('es', **kwargs)

            # Obter endpoint do domínio
            self._get_domain_endpoint()

            if self.domain_endpoint:
                self._test_connection()
                self.enabled = True
                print(f"✅ Elasticsearch endpoint configurado: {self.domain_endpoint}")
            else:
                print("⚠️ Elasticsearch não disponível: domínio não encontrado")

        except (NoCredentialsError, ClientError) as e:
            print(f"⚠️ Elasticsearch não disponível: {e}")
            print("📝 Continuando sem indexação")
            self.enabled = False

    def _get_domain_endpoint(self):
        """Obtém endpoint do domínio Elasticsearch"""
        try:
            response = self.es_client.describe_elasticsearch_domain(DomainName=self.domain_name)
            domain_info = response['DomainStatus']

            if domain_info['Processing']:
                print(f"⏳ Domínio '{self.domain_name}' ainda está sendo processado...")
                return

            if not domain_info['Created']:
                print(f"❌ Domínio '{self.domain_name}' não foi criado")
                return

            # Para dominios VPC, a estrutura pode ser diferente
            endpoint = None
            
            # Tentar diferentes estruturas de endpoint
            if 'Endpoint' in domain_info:
                endpoint = domain_info['Endpoint']
            elif 'Endpoints' in domain_info and 'vpc' in domain_info['Endpoints']:
                endpoint = domain_info['Endpoints']['vpc']
            elif 'VPCOptions' in domain_info and 'Endpoint' in domain_info['VPCOptions']:
                endpoint = domain_info['VPCOptions']['Endpoint']
            
            # Se não encontrou via API, tentar variável de ambiente
            if not endpoint:
                endpoint = os.getenv('OPENSEARCH_ENDPOINT')
                if endpoint:
                    print(f"🔧 Usando endpoint da variável de ambiente: {endpoint}")
                    # Remover https:// se já tiver
                    if endpoint.startswith('https://'):
                        endpoint = endpoint[8:]
                    elif endpoint.startswith('http://'):
                        endpoint = endpoint[7:]
            
            if endpoint:
                self.domain_endpoint = f"https://{endpoint}"
                print(f"🔗 Endpoint configurado: {self.domain_endpoint}")
            else:
                print(f"❌ Não foi possível obter endpoint do domínio '{self.domain_name}'")
                print(f"📋 Debug - domain_info keys: {list(domain_info.keys())}")
                return

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"⚠️ Domínio '{self.domain_name}' não existe")
                self.domain_endpoint = None
            else:
                raise e

    def _test_connection(self):
        """Testa conexão com Elasticsearch"""
        try:
            response = requests.get(
                f"{self.domain_endpoint}/_cluster/health",
                timeout=10,
                verify=False  # Para desenvolvimento
            )
            response.raise_for_status()

            health = response.json()
            status = health.get('status', 'unknown')

            if status in ['red']:
                print(f"⚠️ Cluster Elasticsearch não está saudável: {status}")
            else:
                print(f"✅ Cluster Elasticsearch saudável: {status}")

        except Exception as e:
            print(f"❌ Erro ao testar conexão: {e}")
            print("⚠️ OpenSearch VPC requer assinatura AWS4")
            print("📝 Continuando sem teste de conectividade...")
            # Não fazer raise - permite que o sistema continue
            return

    def index_message(self, message_data: Dict[str, Any], doc_id: Optional[str] = None) -> bool:
        """
        Indexa mensagem individual no Elasticsearch

        Args:
            message_data: Dados da mensagem
            doc_id: ID do documento (opcional, será gerado automaticamente)

        Returns:
            True se indexado com sucesso, False caso contrário
        """
        if not self.enabled:
            return False

        try:
            # Preparar documento
            document = self._prepare_document(message_data)

            # Definir ID do documento
            if not doc_id:
                doc_id = f"{document.get('group', 'unknown')}_{document.get('message_id', 'unknown')}_{int(datetime.now().timestamp())}"

            # URL de indexação
            url = f"{self.domain_endpoint}/{self.index_name}/_doc/{doc_id}"

            # Enviar para Elasticsearch
            response = requests.put(
                url,
                json=document,
                headers={'Content-Type': 'application/json'},
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            # Atualizar estatísticas
            self.stats['documents_indexed'] += 1
            self.stats['last_index_time'] = datetime.now()

            return True

        except Exception as e:
            print(f"❌ Erro ao indexar mensagem: {e}")
            self.stats['indexing_errors'] += 1
            return False

    def bulk_index(self, messages: List[Dict[str, Any]]) -> int:
        """
        Indexa múltiplas mensagens usando bulk API

        Args:
            messages: Lista de mensagens

        Returns:
            Número de documentos indexados com sucesso
        """
        if not self.enabled or not messages:
            return 0

        try:
            # Preparar bulk payload
            bulk_body = ""
            for msg in messages:
                document = self._prepare_document(msg)
                doc_id = f"{document.get('group', 'unknown')}_{document.get('message_id', 'unknown')}_{int(datetime.now().timestamp())}"

                # Action metadata
                action = {
                    "index": {
                        "_index": self.index_name,
                        "_id": doc_id
                    }
                }
                bulk_body += json.dumps(action) + "\n"
                bulk_body += json.dumps(document) + "\n"

            # Enviar bulk request
            url = f"{self.domain_endpoint}/_bulk"
            response = requests.post(
                url,
                data=bulk_body,
                headers={'Content-Type': 'application/x-ndjson'},
                timeout=60,
                verify=False
            )
            response.raise_for_status()

            # Analisar resultado
            result = response.json()
            successful = 0
            errors = 0

            for item in result.get('items', []):
                if item.get('index', {}).get('status') in [200, 201]:
                    successful += 1
                else:
                    errors += 1

            # Atualizar estatísticas
            self.stats['documents_indexed'] += successful
            self.stats['indexing_errors'] += errors
            self.stats['last_index_time'] = datetime.now()

            if errors > 0:
                print(f"⚠️ {errors} documentos falharam na indexação bulk")

            return successful

        except Exception as e:
            print(f"❌ Erro na indexação bulk: {e}")
            self.stats['indexing_errors'] += len(messages)
            return 0

    def search_messages(self, query: Dict[str, Any], size: int = 100) -> List[Dict[str, Any]]:
        """
        Busca mensagens no Elasticsearch

        Args:
            query: Query Elasticsearch DSL
            size: Número máximo de resultados

        Returns:
            Lista de documentos encontrados
        """
        if not self.enabled:
            return []

        try:
            url = f"{self.domain_endpoint}/{self.index_name}/_search"
            search_body = {
                "query": query,
                "size": size,
                "sort": [{"@timestamp": {"order": "desc"}}]
            }

            response = requests.post(
                url,
                json=search_body,
                headers={'Content-Type': 'application/json'},
                timeout=30,
                verify=False
            )
            response.raise_for_status()

            result = response.json()
            hits = result.get('hits', {}).get('hits', [])

            return [hit['_source'] for hit in hits]

        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return []

    def get_stats_summary(self) -> Dict[str, Any]:
        """Obtém estatísticas do índice"""
        if not self.enabled:
            return {}

        try:
            url = f"{self.domain_endpoint}/{self.index_name}/_stats"
            response = requests.get(url, timeout=30, verify=False)
            response.raise_for_status()

            stats = response.json()
            indices = stats.get('indices', {})
            index_stats = indices.get(self.index_name, {})

            return {
                'total_documents': index_stats.get('total', {}).get('docs', {}).get('count', 0),
                'index_size': index_stats.get('total', {}).get('store', {}).get('size_in_bytes', 0),
                'client_stats': self.stats
            }

        except Exception as e:
            print(f"❌ Erro ao obter estatísticas: {e}")
            return {'client_stats': self.stats}

    def _prepare_document(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara documento para indexação"""
        document = message_data.copy()

        # Adicionar timestamp para Elasticsearch
        document['@timestamp'] = datetime.now().isoformat()

        # Garantir campos obrigatórios
        required_fields = {
            'group': 'unknown',
            'content': '',
            'date': datetime.now().isoformat(),
            'views': 0,
            'reactions': 0,
            'classification': 'UNKNOWN'
        }

        for field, default_value in required_fields.items():
            if field not in document or document[field] is None:
                document[field] = default_value

        # Adicionar metadados de indexação
        document['indexed_at'] = datetime.now().isoformat()
        document['source'] = 'telegram-scraper'

        return document

    def create_index_template(self):
        """Cria template de índice com mapeamentos otimizados"""
        if not self.enabled:
            return False

        template = {
            "index_patterns": [f"{self.index_name}-*"],
            "template": {
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "group": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        "date": {"type": "date"},
                        "views": {"type": "integer"},
                        "reactions": {"type": "integer"},
                        "classification": {"type": "keyword"},
                        "url": {"type": "keyword"},
                        "indexed_at": {"type": "date"}
                    }
                }
            }
        }

        try:
            url = f"{self.domain_endpoint}/_index_template/{self.index_name}-template"
            response = requests.put(
                url,
                json=template,
                headers={'Content-Type': 'application/json'},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            print(f"✅ Template de índice criado: {self.index_name}-template")
            return True

        except Exception as e:
            print(f"❌ Erro ao criar template: {e}")
            return False

    def is_healthy(self) -> bool:
        """Verifica se o serviço está saudável"""
        if not self.enabled:
            return False

        try:
            response = requests.get(
                f"{self.domain_endpoint}/_cluster/health",
                timeout=10,
                verify=False
            )
            health = response.json()
            return health.get('status') in ['green', 'yellow']

        except Exception:
            return False


# Função de conveniência
def create_elasticsearch_client(domain_name: str = None,
                              region: str = "us-east-1") -> ElasticsearchClient:
    """
    Cria cliente Elasticsearch com configurações padrão

    Args:
        domain_name: Nome do domínio
        region: Região AWS

    Returns:
        Cliente Elasticsearch configurado
    """
    return ElasticsearchClient(domain_name=domain_name, region_name=region)


# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade
    print("🧪 Testando ElasticsearchClient...")

    es_client = ElasticsearchClient()

    if es_client.enabled:
        # Documento de teste
        test_doc = {
            'group': '@test_group',
            'content': 'Mensagem de teste para Elasticsearch',
            'date': datetime.now().isoformat(),
            'views': 150,
            'reactions': 10,
            'classification': 'TEST',
            'message_id': '12345'
        }

        # Testar indexação
        success = es_client.index_message(test_doc)
        print(f"📤 Indexação: {'✅' if success else '❌'}")

        # Mostrar estatísticas
        stats = es_client.get_stats_summary()
        print(f"📊 Estatísticas: {stats}")

    else:
        print("⚠️ Elasticsearch não está habilitado")