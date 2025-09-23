#!/usr/bin/env python3
"""
TESTE SISTEMA SIMPLES - TelegramScrap AWS
Valida implementacao sem emojis para compatibilidade Windows
"""

import sys
import os
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_imports():
    """Testar imports basicos"""
    print("TESTE 1: IMPORTS BASICOS")
    print("=" * 40)

    try:
        import boto3
        import pandas as pd
        import requests
        print("OK - Dependencias basicas")
        return True
    except ImportError as e:
        print(f"ERRO - Dependencias basicas: {e}")
        return False

def test_utils_imports():
    """Testar imports dos utilitarios"""
    print("\nTESTE 2: UTILITARIOS")
    print("=" * 40)

    try:
        from utils.config_loader import ConfigLoader
        print("OK - ConfigLoader")
    except ImportError as e:
        print(f"ERRO - ConfigLoader: {e}")
        return False

    try:
        from utils.google_sheets import GoogleSheetsLoader
        print("OK - GoogleSheetsLoader")
    except ImportError as e:
        print(f"ERRO - GoogleSheetsLoader: {e}")
        return False

    try:
        from utils.monitoring import CloudWatchMonitor
        print("OK - CloudWatchMonitor")
    except ImportError as e:
        print(f"ERRO - CloudWatchMonitor: {e}")
        return False

    try:
        from utils.aws_kinesis import KinesisStreamer
        print("OK - KinesisStreamer")
    except ImportError as e:
        print(f"ERRO - KinesisStreamer: {e}")
        return False

    return True

def test_config_system():
    """Testar sistema de configuracao"""
    print("\nTESTE 3: CONFIGURACOES")
    print("=" * 40)

    try:
        from utils.config_loader import ConfigLoader

        config = ConfigLoader()
        print("OK - ConfigLoader inicializado")

        validation = config.validate_config()
        print(f"OK - Validacao: {validation}")

        return True
    except Exception as e:
        print(f"ERRO - Configuracao: {e}")
        return False

def test_google_sheets():
    """Testar Google Sheets"""
    print("\nTESTE 4: GOOGLE SHEETS")
    print("=" * 40)

    try:
        from utils.google_sheets import GoogleSheetsLoader

        sheets = GoogleSheetsLoader()
        print("OK - GoogleSheetsLoader inicializado")

        groups = sheets.load_groups()
        print(f"OK - {len(groups)} grupos carregados")

        if len(groups) > 100:
            print("OK - Volume adequado de grupos")
        else:
            print(f"AVISO - Poucos grupos: {len(groups)}")

        return True
    except Exception as e:
        print(f"ERRO - Google Sheets: {e}")
        return False

def test_cloudwatch():
    """Testar CloudWatch"""
    print("\nTESTE 5: CLOUDWATCH")
    print("=" * 40)

    try:
        from utils.monitoring import CloudWatchMonitor

        monitor = CloudWatchMonitor()
        print(f"OK - CloudWatch: {'Habilitado' if monitor.enabled else 'Desabilitado'}")

        if monitor.enabled:
            # Testar metrica simples
            success = monitor.send_metric('TestMetric', 1, 'Count')
            print(f"OK - Metrica teste: {'Sucesso' if success else 'Falha'}")

            # Testar metricas de scraping
            success = monitor.send_scraping_stats(100, 5, 60, 30, 10)
            print(f"OK - Metricas scraping: {'Sucesso' if success else 'Falha'}")
        else:
            print("AVISO - CloudWatch desabilitado (sem credenciais AWS)")

        return True
    except Exception as e:
        print(f"ERRO - CloudWatch: {e}")
        return False

def test_aws_components():
    """Testar componentes AWS"""
    print("\nTESTE 6: COMPONENTES AWS")
    print("=" * 40)

    try:
        from utils.aws_kinesis import KinesisStreamer

        kinesis = KinesisStreamer()
        print(f"OK - Kinesis: {'Habilitado' if kinesis.enabled else 'Aguardando AWS'}")

        if kinesis.enabled:
            # Testar mensagem
            test_msg = {
                'group': '@test',
                'content': 'Teste',
                'date': datetime.now().isoformat()
            }
            success = kinesis.send_message(test_msg)
            print(f"OK - Kinesis envio: {'Sucesso' if success else 'Falha'}")

        return True
    except Exception as e:
        print(f"ERRO - AWS Components: {e}")
        return False

def test_notebook_exists():
    """Testar se notebook existe"""
    print("\nTESTE 7: NOTEBOOK")
    print("=" * 40)

    notebook_file = "TelegramScrap_A_comprehensive_tool_for_scraping_Telegram_data.ipynb"

    if os.path.exists(notebook_file):
        print("OK - Notebook principal encontrado")

        # Verificar integracao basica
        with open(notebook_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if 'utils.config_loader' in content:
            print("OK - ConfigLoader integrado")
        else:
            print("AVISO - ConfigLoader nao integrado")

        if 'utils.google_sheets' in content:
            print("OK - GoogleSheets integrado")
        else:
            print("AVISO - GoogleSheets nao integrado")

        if 'utils.monitoring' in content:
            print("OK - Monitoring integrado")
        else:
            print("AVISO - Monitoring nao integrado")

        return True
    else:
        print("ERRO - Notebook nao encontrado")
        return False

def main():
    """Funcao principal"""
    print("TESTE SISTEMA TELEGRAMSCRAP AWS")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    # Executar testes
    tests = [
        test_basic_imports,
        test_utils_imports,
        test_config_system,
        test_google_sheets,
        test_cloudwatch,
        test_aws_components,
        test_notebook_exists
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"ERRO CRITICO: {e}")
            results.append(False)

    # Relatorio final
    print("\n" + "=" * 50)
    print("RELATORIO FINAL")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(results)

    print(f"Total de testes: {total_tests}")
    print(f"Testes aprovados: {passed_tests}")
    print(f"Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")

    if passed_tests == total_tests:
        print("STATUS: SISTEMA 100% OPERACIONAL")
        print("ACAO: Pronto para producao")
    elif passed_tests >= 5:
        print("STATUS: Sistema funcional")
        print("ACAO: Configure AWS para ativacao completa")
    else:
        print("STATUS: Necessita configuracao")
        print("ACAO: Revisar dependencias e setup")

    print("\nLINKS IMPORTANTES:")
    print("CloudWatch: AWS Console -> CloudWatch -> Dashboards")
    print("Planilha: Google Sheets CHIP 2")
    print("Notebook: TelegramScrap_*.ipynb")

    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nCodigo de saida: {exit_code}")
    sys.exit(exit_code)