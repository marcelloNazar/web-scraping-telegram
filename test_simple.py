#!/usr/bin/env python3
"""
Teste CloudWatch Monitor - Sem emojis para Windows
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("TESTE CLOUDWATCH MONITOR")
print("=" * 50)

try:
    # Importar o monitor
    from utils.monitoring import CloudWatchMonitor
    print("OK: Import do CloudWatchMonitor bem-sucedido")

    # Inicializar monitor
    monitor = CloudWatchMonitor()
    print(f"OK: Monitor inicializado (habilitado: {monitor.enabled})")

    if not monitor.enabled:
        print("AVISO: CloudWatch nao habilitado (sem credenciais AWS)")
        print("INFO: Teste continuara em modo simulacao")

    # Teste 1: Métrica simples
    print("\nTestando envio de metrica simples...")
    result1 = monitor.send_metric('TestMetric', 42, 'Count')
    print(f"Resultado: {'OK' if result1 else 'ERRO'}")

    # Teste 2: Estatísticas de scraping
    print("\nTestando envio de estatisticas de scraping...")
    result2 = monitor.send_scraping_stats(
        total_messages=1500,
        groups_count=25,
        pol_count=800,
        conspira_count=400,
        naz_count=300
    )
    print(f"Resultado: {'OK' if result2 else 'ERRO'}")

    # Resumo
    print("\n" + "=" * 50)
    print("RESUMO DO TESTE:")
    print(f"  Monitor habilitado: {'OK' if monitor.enabled else 'NAO'}")
    print(f"  Metrica simples: {'OK' if result1 else 'ERRO'}")
    print(f"  Estatisticas scraping: {'OK' if result2 else 'ERRO'}")

    if monitor.enabled and result1 and result2:
        print("\nSUCESSO: CloudWatch funcionando!")
    elif monitor.enabled:
        print("\nPARCIAL: CloudWatch habilitado mas com erros")
    else:
        print("\nSIMULACAO: Logica funcionando (sem credenciais AWS)")
        print("DICA: Configure credenciais AWS para teste real")

except ImportError as e:
    print(f"ERRO de import: {e}")
    print("DICA: Verifique se src/utils/monitoring.py existe")

except Exception as e:
    print(f"ERRO no teste: {e}")

print("\nFIM DO TESTE")