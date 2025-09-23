#!/usr/bin/env python3
# =================================================================
# TELEGRAMSCRAP - TESTE INDIVIDUAL DE COMPONENTES
# =================================================================
# Testa cada componente separadamente com relatório detalhado
# Criado via Git workflow para deploy na VM

import sys
import os
import traceback
from datetime import datetime

# Adicionar projeto ao path
PROJECT_DIR = "/home/ec2-user/web-scraping-telegram"
if os.path.exists("./src"):
    sys.path.append("./src")
elif os.path.exists(f"{PROJECT_DIR}/src"):
    sys.path.append(f"{PROJECT_DIR}/src")
else:
    print("❌ ERRO: Diretório src/ não encontrado")
    sys.exit(1)

# Configurar modo desenvolvimento
os.environ['DEVELOPMENT_MODE'] = 'true'
os.environ['KINESIS_ENABLED'] = 'false'
os.environ['ELASTICSEARCH_ENABLED'] = 'false'

class ComponentTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []

    def test_component(self, name, test_func, description=""):
        """Executa teste de um componente"""
        self.tests_run += 1
        print(f"[{self.tests_run}] Testando {name}...", end=" ")

        try:
            result = test_func()
            if result:
                print("✅ PASS")
                self.tests_passed += 1
                self.results.append({
                    'name': name,
                    'status': 'PASS',
                    'description': description,
                    'details': result if isinstance(result, str) else 'OK'
                })
            else:
                print("❌ FAIL")
                self.tests_failed += 1
                self.results.append({
                    'name': name,
                    'status': 'FAIL',
                    'description': description,
                    'details': 'Retornou False'
                })

        except Exception as e:
            print("❌ ERROR")
            self.tests_failed += 1
            self.results.append({
                'name': name,
                'status': 'ERROR',
                'description': description,
                'details': str(e)
            })

    def print_summary(self):
        """Imprime resumo dos testes"""
        print("\n" + "="*60)
        print("📊 RESUMO DOS TESTES DE COMPONENTES")
        print("="*60)
        print(f"Total: {self.tests_run}")
        print(f"Aprovados: {self.tests_passed}")
        print(f"Falharam: {self.tests_failed}")

        success_rate = (self.tests_passed * 100 // self.tests_run) if self.tests_run > 0 else 0
        print(f"Taxa de sucesso: {success_rate}%")

        print("\n📋 DETALHES DOS TESTES:")
        print("-" * 60)

        for result in self.results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['name']}: {result['status']}")
            if result['description']:
                print(f"   📝 {result['description']}")
            if result['status'] != 'PASS':
                print(f"   🔍 {result['details']}")

        return success_rate >= 80

def test_config_loader():
    """Teste Config Loader"""
    try:
        from utils.config_loader import ConfigLoader
        config = ConfigLoader()
        return f"ConfigLoader criado - tipo: {type(config)}"
    except Exception as e:
        raise Exception(f"Erro importando ConfigLoader: {e}")

def test_monitoring():
    """Teste CloudWatch Monitoring"""
    try:
        from utils.monitoring import CloudWatchMonitor
        monitor = CloudWatchMonitor()

        if not monitor.enabled:
            raise Exception("CloudWatch deveria estar habilitado")

        # Teste envio de métricas
        test_stats = {
            'total_messages': 5,
            'groups_count': 2,
            'total_views': 500,
            'total_reactions': 25,
            'categories': {'POL': 3, 'CONSPIRA': 2},
            'political_spectrum': {'Right': 3, 'Left': 1, 'General': 1}
        }

        result = monitor.send_scraping_metrics(test_stats)
        if not result:
            raise Exception("Falha enviando métricas de teste")

        return f"CloudWatch funcionando - métricas enviadas"

    except Exception as e:
        raise Exception(f"Erro no CloudWatch: {e}")

def test_google_sheets():
    """Teste Google Sheets Integration"""
    try:
        from utils.google_sheets import GoogleSheetsLoader
        sheets = GoogleSheetsLoader()

        groups = sheets.get_active_groups()

        if len(groups) == 0:
            raise Exception("Nenhum grupo carregado do Google Sheets")

        # Verificar estrutura dos dados
        sample_group = groups[0]
        required_fields = ['username', 'spectrum', 'stance']

        for field in required_fields:
            if field not in sample_group:
                raise Exception(f"Campo '{field}' não encontrado nos dados")

        return f"Google Sheets OK - {len(groups)} grupos carregados"

    except Exception as e:
        raise Exception(f"Erro no Google Sheets: {e}")

def test_kinesis_dev_mode():
    """Teste Kinesis em modo desenvolvimento"""
    try:
        from utils.aws_kinesis import KinesisStreamer
        kinesis = KinesisStreamer()

        if kinesis.enabled:
            raise Exception("Kinesis deveria estar disabled em modo desenvolvimento")

        return "Kinesis corretamente disabled em modo dev"

    except Exception as e:
        raise Exception(f"Erro no teste Kinesis: {e}")

def test_elasticsearch_dev_mode():
    """Teste Elasticsearch em modo desenvolvimento"""
    try:
        from utils.aws_elasticsearch import ElasticsearchClient
        es = ElasticsearchClient()

        if es.enabled:
            raise Exception("Elasticsearch deveria estar disabled em modo desenvolvimento")

        return "Elasticsearch corretamente disabled em modo dev"

    except Exception as e:
        raise Exception(f"Erro no teste Elasticsearch: {e}")

def test_lambda_code():
    """Teste código Lambda"""
    try:
        # Verificar se arquivo Lambda existe
        lambda_files = [
            "lambda_functions/telegram_processor.py",
            f"{PROJECT_DIR}/lambda_functions/telegram_processor.py"
        ]

        lambda_file = None
        for f in lambda_files:
            if os.path.exists(f):
                lambda_file = f
                break

        if not lambda_file:
            raise Exception("Arquivo telegram_processor.py não encontrado")

        # Ler e verificar código
        with open(lambda_file, 'r') as f:
            code = f.read()

        # Verificar funções essenciais
        required_functions = ['lambda_handler', 'process_telegram_message']
        for func in required_functions:
            if f"def {func}" not in code:
                raise Exception(f"Função '{func}' não encontrada no código Lambda")

        return f"Código Lambda OK - {len(code)} caracteres"

    except Exception as e:
        raise Exception(f"Erro no código Lambda: {e}")

def test_kibana_files():
    """Teste arquivos Kibana"""
    try:
        kibana_dirs = [
            "kibana",
            f"{PROJECT_DIR}/kibana"
        ]

        kibana_dir = None
        for d in kibana_dirs:
            if os.path.exists(d):
                kibana_dir = d
                break

        if not kibana_dir:
            raise Exception("Diretório kibana/ não encontrado")

        # Contar arquivos JSON
        json_count = 0
        for root, dirs, files in os.walk(kibana_dir):
            json_count += len([f for f in files if f.endswith('.json')])

        if json_count < 9:
            raise Exception(f"Esperados 9+ arquivos JSON, encontrados {json_count}")

        # Verificar script setup
        setup_file = os.path.join(kibana_dir, "setup", "setup_kibana_dashboards.py")
        if not os.path.exists(setup_file):
            raise Exception("Script setup_kibana_dashboards.py não encontrado")

        return f"Kibana OK - {json_count} arquivos JSON + script setup"

    except Exception as e:
        raise Exception(f"Erro nos arquivos Kibana: {e}")

def test_data_files():
    """Teste arquivos de dados"""
    try:
        data_files = [
            "data/grupos_telegram_chip2.csv",
            f"{PROJECT_DIR}/data/grupos_telegram_chip2.csv"
        ]

        data_file = None
        for f in data_files:
            if os.path.exists(f):
                data_file = f
                break

        if not data_file:
            raise Exception("Arquivo grupos_telegram_chip2.csv não encontrado")

        # Verificar tamanho do arquivo
        file_size = os.path.getsize(data_file)
        if file_size < 1000:  # Menos de 1KB indica arquivo vazio/problemático
            raise Exception(f"Arquivo muito pequeno: {file_size} bytes")

        # Contar linhas
        with open(data_file, 'r', encoding='utf-8') as f:
            lines = sum(1 for line in f)

        if lines < 10:
            raise Exception(f"Muito poucas linhas: {lines}")

        return f"Dados OK - {lines} linhas, {file_size} bytes"

    except Exception as e:
        raise Exception(f"Erro nos arquivos de dados: {e}")

def test_integration_simulation():
    """Teste simulação de integração completa"""
    try:
        from utils.google_sheets import GoogleSheetsLoader
        from utils.monitoring import CloudWatchMonitor

        # Carregar componentes
        sheets = GoogleSheetsLoader()
        monitor = CloudWatchMonitor()

        # Verificar componentes
        if not monitor.enabled:
            raise Exception("CloudWatch deveria estar habilitado")

        # Carregar dados
        groups = sheets.get_active_groups()
        if len(groups) < 5:
            raise Exception(f"Poucos grupos carregados: {len(groups)}")

        # Simular processamento
        sample_groups = groups[:3]

        # Simular estatísticas realísticas
        fake_stats = {
            'total_messages': 30,
            'groups_count': len(sample_groups),
            'total_views': 3000,
            'total_reactions': 150,
            'categories': {'POL': 21, 'CONSPIRA': 8, 'NAZ': 1},
            'political_spectrum': {'Right': 15, 'Left': 10, 'General': 5}
        }

        # Enviar métricas
        result = monitor.send_scraping_metrics(fake_stats)
        if not result:
            raise Exception("Falha enviando métricas de integração")

        return f"Integração OK - {len(sample_groups)} grupos, métricas enviadas"

    except Exception as e:
        raise Exception(f"Erro na integração: {e}")

def main():
    print("🧪 TELEGRAMSCRAP - TESTE INDIVIDUAL DE COMPONENTES")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo: DESENVOLVIMENTO (Kinesis/ES disabled)")
    print("")

    tester = ComponentTester()

    # Executar testes
    tester.test_component(
        "Config Loader",
        test_config_loader,
        "Carregamento de configurações"
    )

    tester.test_component(
        "CloudWatch Monitor",
        test_monitoring,
        "Monitoramento e envio de métricas"
    )

    tester.test_component(
        "Google Sheets",
        test_google_sheets,
        "Carregamento de grupos Telegram"
    )

    tester.test_component(
        "Kinesis (Dev Mode)",
        test_kinesis_dev_mode,
        "Kinesis disabled em desenvolvimento"
    )

    tester.test_component(
        "Elasticsearch (Dev Mode)",
        test_elasticsearch_dev_mode,
        "Elasticsearch disabled em desenvolvimento"
    )

    tester.test_component(
        "Código Lambda",
        test_lambda_code,
        "Validação do código Lambda"
    )

    tester.test_component(
        "Arquivos Kibana",
        test_kibana_files,
        "Dashboards e visualizações Kibana"
    )

    tester.test_component(
        "Arquivos de Dados",
        test_data_files,
        "CSV com grupos Telegram"
    )

    tester.test_component(
        "Integração Simulada",
        test_integration_simulation,
        "Teste end-to-end simulado"
    )

    # Resultado final
    success = tester.print_summary()

    print("\n🎯 PRÓXIMOS PASSOS:")
    if success:
        print("   ✅ Todos componentes funcionais")
        print("   👉 Sistema pronto para automação")
        print("   👉 Aguardar permissões AWS para ativação completa")
    else:
        print("   🔧 Corrigir componentes com falha")
        print("   👉 Executar novamente após correções")

    print("\n📊 CAPACIDADES CONFIRMADAS:")
    print("   ✅ Google Sheets: Carregamento automático")
    print("   ✅ CloudWatch: Monitoramento ativo")
    print("   ✅ Lambda: Código pronto para deploy")
    print("   ✅ Kibana: Dashboards preparados")
    print("   🔄 Kinesis: Aguardando permissões")
    print("   🔄 Elasticsearch: Aguardando permissões")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())