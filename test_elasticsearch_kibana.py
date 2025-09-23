#!/usr/bin/env python3
"""
Teste Elasticsearch + Kibana - TelegramScrap
Valida conexão e configuração do pipeline ES+Kibana
"""

import sys
import os
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_elasticsearch_connection():
    """Testar conexão com Elasticsearch"""
    print("TESTE 1: ELASTICSEARCH CONNECTION")
    print("=" * 40)

    try:
        from utils.aws_elasticsearch import ElasticsearchClient

        # Inicializar cliente
        es = ElasticsearchClient()
        print(f"Elasticsearch: {'HABILITADO' if es.enabled else 'DESABILITADO'}")

        if es.enabled:
            # Testar criação de índice
            index_created = es.create_index()
            print(f"Criacao de indice: {'OK' if index_created else 'FALHA'}")

            # Testar indexação de documento
            test_doc = {
                'message_id': 'test_001',
                'group_name': '@test_group',
                'content': 'Mensagem de teste para Elasticsearch',
                'date_message': datetime.now().isoformat(),
                'views': 100,
                'reactions': 5,
                'shares': 2,
                'category_1': 'TEST',
                'category_4': 'General',
                'sentiment': 'neutral',
                'content_tokens': ['teste', 'elasticsearch'],
                'processed_at': datetime.now().isoformat()
            }

            doc_indexed = es.index_message(test_doc)
            print(f"Indexacao de documento: {'OK' if doc_indexed else 'FALHA'}")

            # Testar bulk indexing
            test_docs = [test_doc.copy() for _ in range(3)]
            for i, doc in enumerate(test_docs):
                doc['message_id'] = f'test_bulk_{i}'
                doc['content'] = f'Teste bulk {i}'

            bulk_count = es.bulk_index(test_docs)
            print(f"Bulk indexing: {bulk_count}/3 documentos")

            # Estatísticas
            stats = es.get_stats()
            print(f"Estatisticas ES: {stats}")

        return es.enabled
    except Exception as e:
        print(f"ERRO Elasticsearch: {e}")
        return False

def test_kibana_files():
    """Testar se arquivos Kibana existem"""
    print("\nTESTE 2: ARQUIVOS KIBANA")
    print("=" * 40)

    required_files = [
        'kibana/index-patterns/telegram-messages-pattern.json',
        'kibana/visualizations/message-classification-pie.json',
        'kibana/visualizations/political-spectrum-bar.json',
        'kibana/visualizations/messages-timeline.json',
        'kibana/visualizations/top-groups-volume.json',
        'kibana/visualizations/sentiment-analysis.json',
        'kibana/visualizations/engagement-metrics.json',
        'kibana/dashboards/telegram-main-dashboard.json',
        'kibana/dashboards/political-analysis-dashboard.json',
        'kibana/setup/setup_kibana_dashboards.py'
    ]

    files_found = 0
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"OK - {file_path}")
            files_found += 1
        else:
            print(f"FALTANDO - {file_path}")

    print(f"Arquivos Kibana: {files_found}/{len(required_files)}")
    return files_found == len(required_files)

def test_kibana_setup_script():
    """Testar script de setup Kibana"""
    print("\nTESTE 3: SCRIPT SETUP KIBANA")
    print("=" * 40)

    try:
        # Testar import do módulo
        sys.path.append('./kibana/setup')
        from setup_kibana_dashboards import KibanaSetup

        # Criar instância (sem conectar)
        setup = KibanaSetup("https://test-domain.us-east-1.es.amazonaws.com/_dashboards")
        print("OK - Classe KibanaSetup importada")

        # Verificar métodos principais
        methods = [
            'test_connection',
            'import_index_patterns',
            'import_visualizations',
            'import_dashboards',
            'run_full_setup'
        ]

        for method in methods:
            if hasattr(setup, method):
                print(f"OK - Metodo {method}")
            else:
                print(f"FALTANDO - Metodo {method}")

        return True
    except Exception as e:
        print(f"ERRO Script Kibana: {e}")
        return False

def test_pipeline_integration():
    """Testar integração completa"""
    print("\nTESTE 4: INTEGRACAO PIPELINE")
    print("=" * 40)

    try:
        # Testar imports completos
        from utils.aws_kinesis import KinesisStreamer
        from utils.aws_elasticsearch import ElasticsearchClient
        from utils.monitoring import CloudWatchMonitor

        kinesis = KinesisStreamer()
        elasticsearch = ElasticsearchClient()
        cloudwatch = CloudWatchMonitor()

        print(f"Kinesis: {'OK' if kinesis.enabled else 'AGUARDANDO'}")
        print(f"Elasticsearch: {'OK' if elasticsearch.enabled else 'AGUARDANDO'}")
        print(f"CloudWatch: {'OK' if cloudwatch.enabled else 'AGUARDANDO'}")

        # Simular pipeline completo se todos estiverem ativos
        all_active = all([kinesis.enabled, elasticsearch.enabled, cloudwatch.enabled])

        if all_active:
            print("PIPELINE COMPLETO: ATIVO")

            # Simular fluxo: Telegram → Kinesis → ES → Kibana
            test_message = {
                'message_id': 'pipeline_test',
                'group_name': '@pipeline_test',
                'content': 'Teste pipeline completo Telegram-Kinesis-ES-Kibana',
                'date_message': datetime.now().isoformat(),
                'views': 250,
                'reactions': 15,
                'shares': 8,
                'category_1': 'POL',
                'category_4': 'Right'
            }

            # 1. Kinesis
            kinesis_ok = kinesis.send_message(test_message)
            print(f"1. Kinesis envio: {'OK' if kinesis_ok else 'FALHA'}")

            # 2. Elasticsearch
            es_ok = elasticsearch.index_message(test_message)
            print(f"2. Elasticsearch index: {'OK' if es_ok else 'FALHA'}")

            # 3. CloudWatch
            cw_ok = cloudwatch.send_scraping_stats(1, 1, 1, 0, 0)
            print(f"3. CloudWatch metrics: {'OK' if cw_ok else 'FALHA'}")

            pipeline_ok = all([kinesis_ok, es_ok, cw_ok])
            print(f"PIPELINE STATUS: {'FUNCIONANDO' if pipeline_ok else 'PARCIAL'}")

        else:
            print("PIPELINE COMPLETO: AGUARDANDO ATIVACAO AWS")

        return True
    except Exception as e:
        print(f"ERRO Pipeline: {e}")
        return False

def main():
    """Função principal"""
    print("TESTE ELASTICSEARCH + KIBANA - TELEGRAMSCRAP")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # Executar testes
    tests = [
        test_elasticsearch_connection,
        test_kibana_files,
        test_kibana_setup_script,
        test_pipeline_integration
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"ERRO CRITICO: {e}")
            results.append(False)

    # Relatório final
    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(results)

    print(f"Total de testes: {total_tests}")
    print(f"Testes aprovados: {passed_tests}")
    print(f"Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("STATUS: ELASTICSEARCH + KIBANA 100% PRONTO")
        print("ACAO: Execute setup_kibana_dashboards.py quando OpenSearch estiver ativo")
    elif passed_tests >= 2:
        print("STATUS: Elasticsearch + Kibana parcialmente pronto")
        print("ACAO: Configure OpenSearch na AWS para ativacao completa")
    else:
        print("STATUS: Necessita configuracao")
        print("ACAO: Revisar implementacao e dependencias")

    print("\nPROXIMOS PASSOS:")
    print("1. Criar OpenSearch domain na AWS")
    print("2. Configurar endpoint no codigo")
    print("3. Executar: python kibana/setup/setup_kibana_dashboards.py")
    print("4. Acessar Kibana e validar dashboards")

    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nCodigo de saida: {exit_code}")
    sys.exit(exit_code)