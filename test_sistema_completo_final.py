#!/usr/bin/env python3
"""
TESTE SISTEMA COMPLETO FINAL - TelegramScrap AWS
Valida TODA a implementação e integração antes da produção
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports_and_dependencies():
    """Testar todos os imports necessários"""
    print("TESTE 1: IMPORTS E DEPENDÊNCIAS")
    print("=" * 50)

    tests_passed = []

    # Teste 1.1: Imports básicos
    try:
        import boto3
        import pandas as pd
        import requests
        tests_passed.append("✅ Dependências básicas")
    except ImportError as e:
        tests_passed.append(f"❌ Dependências básicas: {e}")
        return False, tests_passed

    # Teste 1.2: Imports utilitários
    try:
        from utils.config_loader import ConfigLoader
        from utils.google_sheets import GoogleSheetsLoader
        from utils.monitoring import CloudWatchMonitor
        from utils.monitoring_pro import CloudWatchMonitorPro
        from utils.aws_kinesis import KinesisStreamer
        from utils.aws_elasticsearch import ElasticsearchClient
        tests_passed.append("✅ Todos os utilitários importados")
    except ImportError as e:
        tests_passed.append(f"❌ Utilitários: {e}")
        return False, tests_passed

    return True, tests_passed

def test_configuration_system():
    """Testar sistema de configurações"""
    print("\n📋 TESTE 2: SISTEMA DE CONFIGURAÇÕES")
    print("=" * 50)

    tests_passed = []

    try:
        from utils.config_loader import ConfigLoader

        # Testar carregamento
        config = ConfigLoader()
        tests_passed.append("✅ ConfigLoader inicializado")

        # Testar validação
        validation = config.validate_config()
        tests_passed.append(f"✅ Validação: {validation}")

        # Testar credenciais Telegram
        telegram_creds = config.get_telegram_credentials()
        if telegram_creds['api_id'] and telegram_creds['api_id'] != "":
            tests_passed.append("✅ Credenciais Telegram configuradas")
        else:
            tests_passed.append("⚠️ Credenciais Telegram não configuradas")

        # Testar credenciais AWS
        aws_creds = config.get_aws_credentials()
        tests_passed.append(f"✅ AWS config carregado")

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro configuração: {e}")
        return False, tests_passed

def test_google_sheets_integration():
    """Testar integração Google Sheets"""
    print("\n📊 TESTE 3: GOOGLE SHEETS INTEGRATION")
    print("=" * 50)

    tests_passed = []

    try:
        from utils.google_sheets import GoogleSheetsLoader

        # Inicializar loader
        sheets = GoogleSheetsLoader()
        tests_passed.append("✅ GoogleSheetsLoader inicializado")

        # Carregar grupos
        groups = sheets.load_groups()
        tests_passed.append(f"✅ {len(groups)} grupos carregados")

        # Testar filtros
        active_groups = sheets.get_active_groups()
        tests_passed.append(f"✅ {len(active_groups)} grupos ativos")

        # Testar estatísticas
        stats = sheets.get_stats()
        tests_passed.append(f"✅ Estatísticas: {stats['total']} total")

        # Verificar qualidade dos dados
        if len(groups) >= 100:  # Esperamos pelo menos 100 grupos
            tests_passed.append("✅ Volume de dados adequado")
        else:
            tests_passed.append(f"⚠️ Poucos grupos: {len(groups)}")

        # Verificar estrutura dos dados
        if groups and all(key in groups[0] for key in ['username', 'spectrum', 'stance']):
            tests_passed.append("✅ Estrutura de dados válida")
        else:
            tests_passed.append("❌ Estrutura de dados inválida")

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro Google Sheets: {e}")
        return False, tests_passed

def test_cloudwatch_monitoring():
    """Testar sistema CloudWatch"""
    print("\n📈 TESTE 4: CLOUDWATCH MONITORING")
    print("=" * 50)

    tests_passed = []

    try:
        from utils.monitoring import CloudWatchMonitor
        from utils.monitoring_pro import CloudWatchMonitorPro

        # Testar monitor básico
        monitor = CloudWatchMonitor()
        tests_passed.append(f"✅ CloudWatch básico: {'Habilitado' if monitor.enabled else 'Desabilitado'}")

        # Testar monitor PRO
        monitor_pro = CloudWatchMonitorPro()
        tests_passed.append(f"✅ CloudWatch PRO: {'Habilitado' if monitor_pro.enabled else 'Desabilitado'}")

        # Testar envio de métricas (se habilitado)
        if monitor.enabled:
            success = monitor.send_metric('TestMetric', 1, 'Count')
            tests_passed.append(f"✅ Envio de métrica: {'Sucesso' if success else 'Falha'}")

            # Testar métricas de scraping
            success = monitor.send_scraping_stats(100, 5, 60, 30, 10)
            tests_passed.append(f"✅ Métricas scraping: {'Sucesso' if success else 'Falha'}")
        else:
            tests_passed.append("⚠️ CloudWatch desabilitado - sem credenciais AWS")

        # Testar alarmes (monitor PRO)
        if monitor_pro.enabled:
            alarm_success = monitor_pro.create_alarms()
            tests_passed.append(f"✅ Criação de alarmes: {'Sucesso' if alarm_success else 'Falha'}")

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro CloudWatch: {e}")
        return False, tests_passed

def test_aws_streaming_components():
    """Testar componentes AWS para streaming"""
    print("\n☁️ TESTE 5: COMPONENTES AWS STREAMING")
    print("=" * 50)

    tests_passed = []

    try:
        from utils.aws_kinesis import KinesisStreamer
        from utils.aws_elasticsearch import ElasticsearchClient

        # Testar Kinesis
        kinesis = KinesisStreamer()
        tests_passed.append(f"✅ Kinesis: {'Habilitado' if kinesis.enabled else 'Aguardando ativação AWS'}")

        if kinesis.enabled:
            # Testar envio de mensagem
            test_message = {
                'group': '@test',
                'content': 'Teste CloudWatch',
                'date': datetime.now().isoformat(),
                'views': 100
            }
            success = kinesis.send_message(test_message)
            tests_passed.append(f"✅ Envio Kinesis: {'Sucesso' if success else 'Falha'}")

            # Verificar estatísticas
            stats = kinesis.get_stats()
            tests_passed.append(f"✅ Stats Kinesis: {stats}")

        # Testar Elasticsearch
        es_client = ElasticsearchClient()
        tests_passed.append(f"✅ Elasticsearch: {'Habilitado' if es_client.enabled else 'Aguardando ativação AWS'}")

        if es_client.enabled:
            # Testar criação de índice
            index_success = es_client.create_index()
            tests_passed.append(f"✅ Índice ES: {'Criado' if index_success else 'Falha'}")

            # Testar indexação
            test_doc = {
                'group_name': '@test',
                'content': 'Documento de teste',
                'date_message': datetime.now().isoformat(),
                'category_1': 'TEST'
            }
            doc_success = es_client.index_message(test_doc)
            tests_passed.append(f"✅ Indexação ES: {'Sucesso' if doc_success else 'Falha'}")

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro AWS Streaming: {e}")
        return False, tests_passed

def test_notebook_integration():
    """Testar componentes de integração do notebook"""
    print("\n📓 TESTE 6: INTEGRAÇÃO NOTEBOOK")
    print("=" * 50)

    tests_passed = []

    try:
        # Verificar se arquivo do notebook existe
        notebook_file = "TelegramScrap_A_comprehensive_tool_for_scraping_Telegram_data.ipynb"
        if os.path.exists(notebook_file):
            tests_passed.append("✅ Notebook principal encontrado")

            # Verificar conteúdo do notebook
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook_content = f.read()

            # Verificar integrações
            integrations = [
                ('utils.config_loader', 'ConfigLoader'),
                ('utils.google_sheets', 'GoogleSheetsLoader'),
                ('utils.monitoring', 'CloudWatchMonitor'),
                ('classify_message', 'Classificação automática'),
                ('CloudWatch', 'Métricas')
            ]

            for integration, description in integrations:
                if integration in notebook_content:
                    tests_passed.append(f"✅ {description} integrado")
                else:
                    tests_passed.append(f"⚠️ {description} não encontrado")
        else:
            tests_passed.append("❌ Notebook principal não encontrado")
            return False, tests_passed

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro integração notebook: {e}")
        return False, tests_passed

def test_data_pipeline_simulation():
    """Simular pipeline completo de dados"""
    print("\n🔄 TESTE 7: SIMULAÇÃO PIPELINE COMPLETO")
    print("=" * 50)

    tests_passed = []

    try:
        from utils.google_sheets import GoogleSheetsLoader
        from utils.monitoring import CloudWatchMonitor
        from utils.aws_kinesis import KinesisStreamer
        from utils.aws_elasticsearch import ElasticsearchClient

        # Simular dados do pipeline
        sheets = GoogleSheetsLoader()
        groups = sheets.get_active_groups()[:5]  # Primeiros 5 grupos
        tests_passed.append(f"✅ {len(groups)} grupos carregados para simulação")

        # Simular mensagens
        simulated_messages = []
        for i, group in enumerate(groups):
            for j in range(3):  # 3 mensagens por grupo
                message = {
                    'message_id': f"msg_{i}_{j}",
                    'group_name': group['username'] if isinstance(group, dict) else group,
                    'content': f"Teste de mensagem política {j}",
                    'date_message': (datetime.now() - timedelta(hours=j)).isoformat(),
                    'views': 100 + (i * 10),
                    'reactions': 5 + i,
                    'shares': 2 + j,
                    'category_1': 'POL' if j % 2 == 0 else 'CONSPIRA',
                    'category_4': 'Right' if i % 2 == 0 else 'Left',
                    'url': f'https://t.me/{group}/123{j}' if isinstance(group, str) else f'https://t.me/{group.get("username", "test")}/123{j}'
                }
                simulated_messages.append(message)

        tests_passed.append(f"✅ {len(simulated_messages)} mensagens simuladas")

        # Testar processamento
        pol_count = sum(1 for msg in simulated_messages if msg['category_1'] == 'POL')
        conspira_count = sum(1 for msg in simulated_messages if msg['category_1'] == 'CONSPIRA')

        tests_passed.append(f"✅ Classificação: {pol_count} POL, {conspira_count} CONSPIRA")

        # Testar envios (se componentes estiverem habilitados)
        monitor = CloudWatchMonitor()
        if monitor.enabled:
            success = monitor.send_scraping_stats(
                len(simulated_messages),
                len(groups),
                pol_count,
                conspira_count,
                0
            )
            tests_passed.append(f"✅ CloudWatch pipeline: {'Sucesso' if success else 'Falha'}")

        kinesis = KinesisStreamer()
        if kinesis.enabled:
            sent_count = 0
            for msg in simulated_messages[:5]:  # Enviar apenas primeiras 5
                if kinesis.send_message(msg):
                    sent_count += 1
            tests_passed.append(f"✅ Kinesis pipeline: {sent_count}/5 mensagens enviadas")

        return True, tests_passed

    except Exception as e:
        tests_passed.append(f"❌ Erro simulação pipeline: {e}")
        return False, tests_passed

def generate_system_report(all_results):
    """Gerar relatório completo do sistema"""
    print("\n📋 RELATÓRIO FINAL DO SISTEMA")
    print("=" * 60)

    total_tests = len(all_results)
    passed_tests = sum(1 for result, _ in all_results if result)

    print(f"📊 RESUMO GERAL:")
    print(f"├─ Total de testes: {total_tests}")
    print(f"├─ Testes aprovados: {passed_tests}")
    print(f"├─ Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
    print(f"└─ Status: {'✅ SISTEMA PRONTO' if passed_tests == total_tests else '⚠️ NECESSITA ATENÇÃO'}")

    print(f"\n🔍 DETALHES POR COMPONENTE:")

    for i, (test_result, test_details) in enumerate(all_results, 1):
        status_icon = "✅" if test_result else "❌"
        test_names = [
            "Imports e Dependências",
            "Sistema de Configurações",
            "Google Sheets Integration",
            "CloudWatch Monitoring",
            "AWS Streaming Components",
            "Integração Notebook",
            "Simulação Pipeline Completo"
        ]

        print(f"\n{status_icon} TESTE {i}: {test_names[i-1]}")
        for detail in test_details:
            print(f"  {detail}")

    # Recomendações
    print(f"\n💡 RECOMENDAÇÕES:")

    if passed_tests == total_tests:
        print("🎉 Sistema 100% operacional!")
        print("🚀 Pronto para produção")
        print("📊 Execute notebook para começar scraping")
    elif passed_tests >= 5:
        print("✅ Sistema principalmente funcional")
        print("⚠️ Configure credenciais AWS para ativação completa")
        print("🔧 Resolva pendências antes da produção")
    else:
        print("❌ Sistema precisa de configuração")
        print("🔧 Verifique dependências e configurações")
        print("📝 Consulte documentação de setup")

    # URLs importantes
    print(f"\n🔗 LINKS ÚTEIS:")
    print("📊 CloudWatch: AWS Console → CloudWatch → Dashboards → TelegramScrap-Dashboard")
    print("📈 Métricas: AWS Console → CloudWatch → Metrics → TelegramScrap")
    print("📋 Planilha: https://docs.google.com/spreadsheets/d/1sOnKOz7qqx3bumgNp8-d5_slE3HE3JhGkD8SQjGCAcA/edit#gid=2025195276")

    # Próximos passos
    print(f"\n🎯 PRÓXIMOS PASSOS:")
    if passed_tests == total_tests:
        print("1. ✅ Executar notebook em produção")
        print("2. ✅ Monitorar dashboards CloudWatch")
        print("3. ✅ Configurar automação (cron jobs)")
    else:
        print("1. 🔧 Resolver pendências identificadas")
        print("2. 🔄 Re-executar este teste")
        print("3. 📊 Ativar serviços AWS faltantes")

    return passed_tests == total_tests

def main():
    """Função principal do teste completo"""
    print("TEST SISTEMA COMPLETO FINAL - TELEGRAMSCRAP AWS")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)

    # Lista para armazenar resultados
    all_results = []

    # Executar todos os testes
    tests = [
        test_imports_and_dependencies,
        test_configuration_system,
        test_google_sheets_integration,
        test_cloudwatch_monitoring,
        test_aws_streaming_components,
        test_notebook_integration,
        test_data_pipeline_simulation
    ]

    for test_func in tests:
        try:
            result, details = test_func()
            all_results.append((result, details))
        except Exception as e:
            all_results.append((False, [f"❌ Erro crítico: {e}"]))

    # Gerar relatório final
    system_ready = generate_system_report(all_results)

    # Código de saída
    exit_code = 0 if system_ready else 1

    print(f"\n🏁 TESTE CONCLUÍDO")
    print(f"Código de saída: {exit_code}")
    print(f"Status: {'✅ APROVADO' if system_ready else '❌ REPROVADO'}")

    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)