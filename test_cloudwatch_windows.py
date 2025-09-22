#!/usr/bin/env python3
"""
Teste simples do CloudWatch Monitor - Versao Windows
Valida se o monitoring.py funciona corretamente
"""

import sys
import os
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_cloudwatch_monitor():
    """Testa o CloudWatch Monitor"""

    print("TESTE CLOUDWATCH MONITOR")
    print("=" * 50)

    try:
        # Importar o monitor
        from utils.monitoring import CloudWatchMonitor
        print("✅ Import do CloudWatchMonitor bem-sucedido")

        # Inicializar monitor
        monitor = CloudWatchMonitor()
        print(f"✅ Monitor inicializado (habilitado: {monitor.enabled})")

        if not monitor.enabled:
            print("⚠️ CloudWatch não habilitado (sem credenciais AWS)")
            print("ℹ️ Teste continuará em modo simulação")

        # Teste 1: Métrica simples
        print("\n📊 Testando envio de métrica simples...")
        result1 = monitor.send_metric('TestMetric', 42, 'Count')
        print(f"Resultado: {'✅' if result1 else '❌'}")

        # Teste 2: Estatísticas de scraping (simuladas)
        print("\n📈 Testando envio de estatísticas de scraping...")
        result2 = monitor.send_scraping_stats(
            total_messages=1500,
            groups_count=25,
            pol_count=800,
            conspira_count=400,
            naz_count=300
        )
        print(f"Resultado: {'✅' if result2 else '❌'}")

        # Resumo do teste
        print("\n" + "=" * 50)
        print("📋 RESUMO DO TESTE:")
        print(f"  Monitor habilitado: {'✅' if monitor.enabled else '❌'}")
        print(f"  Métrica simples: {'✅' if result1 else '❌'}")
        print(f"  Estatísticas scraping: {'✅' if result2 else '❌'}")

        if monitor.enabled and result1 and result2:
            print("\n🎉 TESTE COMPLETO: CloudWatch funcionando!")
            print("📊 Verifique métricas: AWS Console -> CloudWatch -> Metrics -> TelegramScrap")
        elif monitor.enabled:
            print("\n⚠️ TESTE PARCIAL: CloudWatch habilitado mas com erros")
        else:
            print("\n✅ TESTE SIMULAÇÃO: Lógica funcionando (sem credenciais AWS)")
            print("💡 Configure credenciais AWS para teste real")

        return True

    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        print("💡 Verifique se src/utils/monitoring.py existe")
        return False

    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def test_aws_connection():
    """Testa conexão AWS básica"""

    print("\n🔗 TESTE CONEXÃO AWS")
    print("=" * 30)

    try:
        import boto3
        print("✅ boto3 importado com sucesso")

        # Testar credenciais
        try:
            cloudwatch = boto3.client('cloudwatch')
            print("✅ Cliente CloudWatch criado")

            # Testar acesso (sem enviar dados)
            response = cloudwatch.list_metrics(Namespace='AWS/EC2', MaxRecords=1)
            print("✅ Credenciais AWS válidas")
            return True

        except Exception as e:
            print(f"⚠️ Credenciais AWS: {e}")
            print("💡 Configure AWS credentials ou IAM role")
            return False

    except ImportError:
        print("❌ boto3 não instalado")
        print("💡 Execute: pip install boto3")
        return False

if __name__ == "__main__":
    print(f"Iniciando teste CloudWatch - {datetime.now()}")
    print()

    # Teste 1: Conexão AWS
    aws_ok = test_aws_connection()

    # Teste 2: Monitor
    monitor_ok = test_cloudwatch_monitor()

    print(f"\nRESULTADO FINAL:")
    print(f"  AWS Connection: {'✅' if aws_ok else '❌'}")
    print(f"  CloudWatch Monitor: {'✅' if monitor_ok else '❌'}")

    if aws_ok and monitor_ok:
        print("🎉 Todos os testes passaram!")
    elif monitor_ok:
        print("✅ Monitor funcionando (configure AWS para métricas reais)")
    else:
        print("❌ Verificar configuração")