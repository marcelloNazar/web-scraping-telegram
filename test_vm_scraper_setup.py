#!/usr/bin/env python3
"""
Teste de Setup VM Scraper
Verifica se todas as dependências estão funcionando antes de executar o scraper contínuo
"""

import sys
import os
from datetime import datetime

def test_imports():
    """Testar imports das dependências"""
    print("🔧 ==> TESTANDO IMPORTS")
    
    try:
        sys.path.append('./src')
        
        print("📦 Testando boto3...")
        import boto3
        print("✅ boto3 OK")
        
        print("📦 Testando telethon...")
        from telethon.sync import TelegramClient
        print("✅ telethon OK")
        
        print("📦 Testando Google Sheets...")
        from utils.google_sheets import GoogleSheetsLoader
        print("✅ GoogleSheetsLoader OK")
        
        print("📦 Testando OpenSearch...")
        from utils.aws_elasticsearch import ElasticsearchClient
        print("✅ ElasticsearchClient OK")
        
        print("📦 Testando CloudWatch...")
        from utils.monitoring import CloudWatchMonitor
        print("✅ CloudWatchMonitor OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro imports: {e}")
        return False

def test_environment():
    """Testar variáveis de ambiente"""
    print("\n🔑 ==> TESTANDO VARIÁVEIS DE AMBIENTE")
    
    required_vars = [
        'TELEGRAM_API_ID',
        'TELEGRAM_API_HASH',
        'AWS_DEFAULT_REGION'
    ]
    
    all_ok = True
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            if 'HASH' in var:
                print(f"✅ {var}: {value[:8]}...")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Não configurada")
            all_ok = False
    
    return all_ok

def test_session_file():
    """Testar arquivo de sessão Telegram"""
    print("\n📱 ==> TESTANDO ARQUIVO DE SESSÃO")
    
    session_file = 'ergoncugler_cinco.session'
    
    if os.path.exists(session_file):
        size = os.path.getsize(session_file)
        print(f"✅ {session_file}: {size} bytes")
        return True
    else:
        print(f"❌ {session_file}: Arquivo não encontrado")
        return False

def test_google_sheets():
    """Testar carregamento Google Sheets"""
    print("\n📊 ==> TESTANDO GOOGLE SHEETS")
    
    try:
        sys.path.append('./src')
        from utils.google_sheets import GoogleSheetsLoader
        
        loader = GoogleSheetsLoader()
        groups = loader.load_groups()
        
        active_groups = [g for g in groups if g.get('active', True)]
        
        print(f"📋 Total grupos na planilha: {len(groups)}")
        print(f"📈 Grupos ativos: {len(active_groups)}")
        
        if len(active_groups) >= 5:
            print("📱 Primeiros 5 grupos:")
            for i, group in enumerate(active_groups[:5]):
                print(f"  {i+1}. {group.get('username', 'N/A')} ({group.get('spectrum', 'Unknown')})")
            print("✅ Google Sheets funcionando")
            return True
        else:
            print("⚠️ Poucos grupos carregados")
            return False
            
    except Exception as e:
        print(f"❌ Erro Google Sheets: {e}")
        return False

def test_aws_connectivity():
    """Testar conectividade AWS"""
    print("\n☁️ ==> TESTANDO CONECTIVIDADE AWS")
    
    try:
        # Testar STS (identidade)
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Identity: {identity['Account']}")
        
        # Testar Kinesis
        kinesis = boto3.client('kinesis')
        stream_info = kinesis.describe_stream(StreamName='telegram-messages')
        status = stream_info['StreamDescription']['StreamStatus']
        print(f"✅ Kinesis Stream: {status}")
        
        # Testar OpenSearch (basic)
        opensearch = boto3.client('opensearch')
        domain_info = opensearch.describe_domain(DomainName='telegramscrap-search')
        processing = domain_info['DomainStatus']['Processing']
        print(f"✅ OpenSearch Domain: {'Processando' if processing else 'Ativo'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro AWS: {e}")
        return False

def main():
    """Executar todos os testes"""
    print("🚀 TESTE DE SETUP VM SCRAPER")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Variáveis de Ambiente", test_environment),
        ("Arquivo de Sessão", test_session_file),
        ("Google Sheets", test_google_sheets),
        ("AWS Connectivity", test_aws_connectivity)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 TESTE: {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 RESULTADO FINAL: {passed}/{len(tests)} testes passaram")
    
    if passed == len(tests):
        print("\n🚀 ✅ TUDO PRONTO! Pode executar o scraper contínuo:")
        print("python3 telegram_scraper_vm_continuous.py")
    else:
        print(f"\n⚠️ {len(tests) - passed} teste(s) falharam. Corrija os problemas antes de executar o scraper.")
    
    print("\n📚 Para mais detalhes, veja: INSTRUCOES_VM_SCRAPER_CONTINUO.md")

if __name__ == "__main__":
    main()
