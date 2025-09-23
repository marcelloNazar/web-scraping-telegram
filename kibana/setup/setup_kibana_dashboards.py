#!/usr/bin/env python3
"""
Setup Automático do Kibana para TelegramScrap
Importa index patterns, visualizações e dashboards automaticamente
"""

import json
import requests
import os
from pathlib import Path
import time

class KibanaSetup:
    """Configurador automático do Kibana"""

    def __init__(self, kibana_url=None, username=None, password=None):
        """
        Inicializa configurador Kibana

        Args:
            kibana_url: URL do Kibana (ex: https://search-telegram-xxx.us-east-1.es.amazonaws.com/_dashboards)
            username: Usuário Kibana (opcional para AWS OpenSearch)
            password: Senha Kibana (opcional para AWS OpenSearch)
        """
        self.kibana_url = kibana_url or "https://your-opensearch-domain.us-east-1.es.amazonaws.com/_dashboards"
        self.username = username
        self.password = password
        self.session = requests.Session()

        # Configurar autenticação se fornecida
        if username and password:
            self.session.auth = (username, password)

        # Headers padrão
        self.session.headers.update({
            'Content-Type': 'application/json',
            'kbn-xsrf': 'true'
        })

        self.base_path = Path(__file__).parent.parent  # kibana/
        self.setup_results = {
            'index_patterns': [],
            'visualizations': [],
            'dashboards': [],
            'errors': []
        }

    def test_connection(self):
        """Testa conexão com Kibana"""
        try:
            response = self.session.get(f"{self.kibana_url}/api/status")
            if response.status_code == 200:
                print("✅ Conexão com Kibana estabelecida")
                return True
            else:
                print(f"❌ Erro de conexão: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erro ao conectar com Kibana: {e}")
            return False

    def import_object(self, file_path, object_type):
        """Importa um objeto (index pattern, visualization, dashboard)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Endpoint de importação do Kibana
            url = f"{self.kibana_url}/api/saved_objects/_import"

            # Preparar arquivo para upload
            files = {
                'file': ('export.ndjson', self._convert_to_ndjson(data), 'application/json')
            }

            # Remover Content-Type header para multipart
            headers = {h: v for h, v in self.session.headers.items() if h.lower() != 'content-type'}

            response = self.session.post(url, files=files, headers=headers)

            if response.status_code in [200, 201]:
                print(f"✅ {object_type} importado: {file_path.name}")
                return True
            else:
                print(f"❌ Erro importando {object_type}: {response.status_code} - {response.text}")
                self.setup_results['errors'].append(f"{file_path.name}: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Erro ao importar {file_path}: {e}")
            self.setup_results['errors'].append(f"{file_path.name}: {str(e)}")
            return False

    def _convert_to_ndjson(self, data):
        """Converte JSON para formato NDJSON do Kibana"""
        lines = []
        for obj in data['objects']:
            lines.append(json.dumps(obj))
        return '\n'.join(lines)

    def import_index_patterns(self):
        """Importa index patterns"""
        print("\n📋 Importando Index Patterns...")
        index_patterns_dir = self.base_path / "index-patterns"

        if not index_patterns_dir.exists():
            print("❌ Diretório index-patterns não encontrado")
            return

        for file_path in index_patterns_dir.glob("*.json"):
            success = self.import_object(file_path, "Index Pattern")
            if success:
                self.setup_results['index_patterns'].append(file_path.name)

    def import_visualizations(self):
        """Importa visualizações"""
        print("\n📊 Importando Visualizações...")
        viz_dir = self.base_path / "visualizations"

        if not viz_dir.exists():
            print("❌ Diretório visualizations não encontrado")
            return

        for file_path in viz_dir.glob("*.json"):
            success = self.import_object(file_path, "Visualization")
            if success:
                self.setup_results['visualizations'].append(file_path.name)

    def import_dashboards(self):
        """Importa dashboards"""
        print("\n🎛️ Importando Dashboards...")
        dashboards_dir = self.base_path / "dashboards"

        if not dashboards_dir.exists():
            print("❌ Diretório dashboards não encontrado")
            return

        for file_path in dashboards_dir.glob("*.json"):
            success = self.import_object(file_path, "Dashboard")
            if success:
                self.setup_results['dashboards'].append(file_path.name)

    def setup_elasticsearch_index(self):
        """Configura índice no Elasticsearch se necessário"""
        print("\n🔍 Configurando índice Elasticsearch...")

        # URL do Elasticsearch (remover _dashboards do final)
        es_url = self.kibana_url.replace('/_dashboards', '')
        index_name = "telegram-messages"

        # Mapping otimizado para mensagens do Telegram
        mapping = {
            "mappings": {
                "properties": {
                    "message_id": {"type": "keyword"},
                    "group_name": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "date_message": {"type": "date"},
                    "views": {"type": "long"},
                    "reactions": {"type": "long"},
                    "shares": {"type": "long"},
                    "category_1": {"type": "keyword"},
                    "category_4": {"type": "keyword"},
                    "sentiment": {"type": "keyword"},
                    "content_tokens": {"type": "keyword"},
                    "group_spectrum": {"type": "keyword"},
                    "group_stance": {"type": "keyword"},
                    "processed_at": {"type": "date"},
                    "lambda_processed_at": {"type": "date"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "portuguese": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"]
                        }
                    }
                }
            }
        }

        try:
            # Verificar se índice já existe
            response = self.session.head(f"{es_url}/{index_name}")
            if response.status_code == 200:
                print("✅ Índice telegram-messages já existe")
                return True

            # Criar índice template para futuros índices
            template_name = "telegram-messages-template"
            template = {
                "index_patterns": ["telegram-messages*"],
                "template": mapping
            }

            response = self.session.put(
                f"{es_url}/_index_template/{template_name}",
                json=template
            )

            if response.status_code in [200, 201]:
                print("✅ Template de índice criado")
                return True
            else:
                print(f"⚠️ Erro criando template: {response.status_code}")
                return False

        except Exception as e:
            print(f"⚠️ Erro configurando Elasticsearch: {e}")
            return False

    def run_full_setup(self):
        """Executa setup completo"""
        print("🚀 INICIANDO SETUP COMPLETO DO KIBANA")
        print("=" * 50)

        # Teste de conexão
        if not self.test_connection():
            print("❌ Impossível conectar com Kibana. Verifique URL e credenciais.")
            return False

        # Setup Elasticsearch
        self.setup_elasticsearch_index()

        # Aguardar índices serem criados
        print("\n⏳ Aguardando 5 segundos...")
        time.sleep(5)

        # Importar objetos na ordem correta
        self.import_index_patterns()
        time.sleep(2)

        self.import_visualizations()
        time.sleep(2)

        self.import_dashboards()

        # Relatório final
        self._print_setup_report()

        return len(self.setup_results['errors']) == 0

    def _print_setup_report(self):
        """Imprime relatório do setup"""
        print("\n📋 RELATÓRIO DO SETUP")
        print("=" * 40)

        print(f"✅ Index Patterns: {len(self.setup_results['index_patterns'])}")
        for item in self.setup_results['index_patterns']:
            print(f"  - {item}")

        print(f"✅ Visualizações: {len(self.setup_results['visualizations'])}")
        for item in self.setup_results['visualizations']:
            print(f"  - {item}")

        print(f"✅ Dashboards: {len(self.setup_results['dashboards'])}")
        for item in self.setup_results['dashboards']:
            print(f"  - {item}")

        if self.setup_results['errors']:
            print(f"❌ Erros: {len(self.setup_results['errors'])}")
            for error in self.setup_results['errors']:
                print(f"  - {error}")

        print("\n🌐 ACESSAR KIBANA:")
        print(f"👉 {self.kibana_url}")
        print("👉 Dashboards → TelegramScrap - Dashboard Principal")
        print("👉 Dashboards → TelegramScrap - Análise Política Avançada")


def main():
    """Função principal"""
    print("SETUP AUTOMÁTICO KIBANA - TELEGRAMSCRAP")
    print("=" * 50)

    # Configuração automática - será substituída pela URL real
    kibana_url = os.getenv('KIBANA_URL', 'https://your-opensearch-domain.us-east-1.es.amazonaws.com/_dashboards')

    if 'your-opensearch-domain' in kibana_url:
        print("⚠️ CONFIGURAÇÃO NECESSÁRIA:")
        print("1. Substitua 'your-opensearch-domain' pela URL real do OpenSearch")
        print("2. Execute: export KIBANA_URL='https://real-domain.us-east-1.es.amazonaws.com/_dashboards'")
        print("3. Execute novamente este script")
        return

    # Inicializar setup
    setup = KibanaSetup(kibana_url)

    # Executar setup completo
    success = setup.run_full_setup()

    if success:
        print("\n🎉 SETUP CONCLUÍDO COM SUCESSO!")
        print("🚀 Kibana configurado e pronto para uso")
    else:
        print("\n⚠️ Setup concluído com alguns erros")
        print("📝 Verifique logs acima e tente novamente")

if __name__ == "__main__":
    main()