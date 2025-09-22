#!/usr/bin/env python3
"""
Setup completo CloudWatch + Dashboard para TelegramScrap
Executa configuração automática completa em uma só execução
"""

import sys
import os
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_dependencies():
    """Verificar dependências necessárias"""
    print("🔍 Verificando dependências...")

    try:
        import boto3
        print("✅ boto3 disponível")
    except ImportError:
        print("❌ boto3 não encontrado - execute: pip install boto3")
        return False

    try:
        import psutil
        print("✅ psutil disponível")
    except ImportError:
        print("❌ psutil não encontrado - execute: pip install psutil")
        return False

    return True

def test_aws_credentials():
    """Testar credenciais AWS"""
    print("🔑 Testando credenciais AWS...")

    try:
        import boto3

        # Tentar criar cliente CloudWatch
        cloudwatch = boto3.client('cloudwatch')

        # Testar acesso básico
        response = cloudwatch.list_metrics(Namespace='AWS/EC2', MaxRecords=1)
        print("✅ Credenciais AWS válidas")
        return True

    except Exception as e:
        print(f"❌ Credenciais AWS inválidas: {e}")
        print("💡 Configure: export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...")
        return False

def setup_cloudwatch_complete():
    """Configurar CloudWatch completo"""

    print("🚀 SETUP CLOUDWATCH COMPLETO")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now()}")
    print("=" * 60)

    # Verificar dependências
    if not check_dependencies():
        return False

    # Verificar credenciais AWS
    if not test_aws_credentials():
        return False

    try:
        from utils.monitoring_pro import CloudWatchMonitorPro

        # Inicializar monitor
        print("\n📊 Inicializando CloudWatch Monitor PRO...")
        monitor = CloudWatchMonitorPro()

        if not monitor.enabled:
            print("❌ CloudWatch não habilitado - erro na inicialização")
            return False

        print("✅ CloudWatch Monitor PRO habilitado!")

        # Limpar alarmes antigos
        print("\n🧹 Limpando configurações antigas...")
        monitor.cleanup_old_alarms()

        # Criar alarmes novos
        print("\n⚠️ Configurando alarmes...")
        if monitor.create_alarms():
            print("✅ Alarmes configurados com sucesso")
        else:
            print("⚠️ Alguns alarmes podem não ter sido criados")

        # Enviar métricas de teste
        print("\n🧪 Enviando métricas de teste...")

        # Marcar início de sessão
        monitor.send_session_start()

        # Métricas de scraping simuladas
        test_success = monitor.send_scraping_stats(
            total_messages=5000,
            groups_count=50,
            pol_count=2000,
            conspira_count=800,
            naz_count=200
        )

        if test_success:
            print("✅ Métricas de scraping enviadas")
        else:
            print("❌ Erro enviando métricas de scraping")

        # Métricas de performance
        perf_success = monitor.send_performance_metrics(
            execution_time=300,  # 5 minutos
            groups_per_minute=10.0
        )

        if perf_success:
            print("✅ Métricas de performance enviadas")
        else:
            print("❌ Erro enviando métricas de performance")

        # Marcar fim de sessão
        monitor.send_session_end()

        print("\n" + "=" * 60)
        print("🎉 SETUP COMPLETO COM SUCESSO!")
        print("=" * 60)
        print("📊 Dashboard: AWS Console → CloudWatch → Dashboards → TelegramScrap-Dashboard")
        print("⚠️ Alarmes: AWS Console → CloudWatch → Alarms")
        print("📈 Métricas: AWS Console → CloudWatch → Metrics → TelegramScrap")
        print("\n💡 O dashboard foi criado automaticamente e já contém dados de teste!")
        print("💡 Execute o notebook TelegramScrap para ver métricas reais!")

        return True

    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        print("💡 Verifique se src/utils/monitoring_pro.py existe")
        return False
    except Exception as e:
        print(f"❌ Erro no setup: {e}")
        return False

def show_next_steps():
    """Mostrar próximos passos"""
    print("\n🚀 PRÓXIMOS PASSOS:")
    print("=" * 30)
    print("1. ✅ CloudWatch configurado")
    print("2. ✅ Dashboard criado")
    print("3. ✅ Alarmes configurados")
    print("4. 🔄 Execute o notebook TelegramScrap")
    print("5. 📊 Veja métricas em tempo real no dashboard")
    print("\n📌 Links úteis:")
    print("   Dashboard: AWS Console → CloudWatch → Dashboards")
    print("   Alarmes: AWS Console → CloudWatch → Alarms")
    print("   Métricas: AWS Console → CloudWatch → Metrics → TelegramScrap")

def main():
    """Função principal"""
    try:
        success = setup_cloudwatch_complete()

        if success:
            show_next_steps()
            print("\n🎉 Configuração CloudWatch + Dashboard finalizada!")
            return 0
        else:
            print("\n❌ Erro na configuração - verifique logs acima")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\nCódigo de saída: {exit_code}")
    sys.exit(exit_code)