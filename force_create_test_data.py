#!/usr/bin/env python3
"""
Script para forçar criação de dados de teste no OpenSearch com TODOS os campos de categorização.
Use se o Index Pattern não reconhecer os campos automaticamente.
"""

import sys
sys.path.append('src')
from utils.aws_elasticsearch import ElasticsearchClient
from datetime import datetime
import json

def create_test_documents():
    """Criar documentos de teste com TODOS os campos necessários"""
    
    print("🧪 CRIANDO DOCUMENTOS DE TESTE COM TODOS OS CAMPOS")
    print("="*60)
    
    es_client = ElasticsearchClient()
    
    if not es_client.enabled:
        print("❌ Cliente OpenSearch não habilitado")
        return False
    
    print(f"✅ Conectado: {es_client.domain_endpoint}")
    
    # Documentos de teste com TODOS os campos necessários
    test_docs = [
        {
            "@timestamp": datetime.now().isoformat(),
            "group": "@test_group_1",
            "content": "Mensagem de teste para dashboard - categoria News",
            "date": datetime.now().isoformat(),
            "message_id": "test_001",
            "author_id": "test_user_001", 
            "classification": "POL",
            "views": 1500,
            "reactions": 25,
            "shares": 5,
            # CAMPOS ESSENCIAIS PARA O DASHBOARD
            "group_format": "News",
            "group_spectrum": "Right", 
            "group_stance": "Conservative",
            "group_project": "Pol",
            "group_country": "Brasil",
            "group_identity": "General",
            "group_basis": "Bolsonarista", 
            "group_territory": "National",
            "url": "https://t.me/test_group_1/001",
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram_test"
        },
        {
            "@timestamp": datetime.now().isoformat(),
            "group": "@test_group_2", 
            "content": "Segunda mensagem de teste - categoria Debate",
            "date": datetime.now().isoformat(),
            "message_id": "test_002",
            "author_id": "test_user_002",
            "classification": "CONSPIRA", 
            "views": 800,
            "reactions": 12,
            "shares": 3,
            # VARIAÇÕES DOS CAMPOS PARA TESTAR
            "group_format": "Debate",
            "group_spectrum": "Left",
            "group_stance": "Progressive", 
            "group_project": "Conspira",
            "group_country": "Brasil",
            "group_identity": "Socialist / Communist",
            "group_basis": "Lulista/Petista",
            "group_territory": "National",
            "url": "https://t.me/test_group_2/002",
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram_test"
        },
        {
            "@timestamp": datetime.now().isoformat(),
            "group": "@test_group_3",
            "content": "Terceira mensagem - categoria Personality",
            "date": datetime.now().isoformat(), 
            "message_id": "test_003",
            "author_id": "test_user_003",
            "classification": "OTHER",
            "views": 2100,
            "reactions": 45,
            "shares": 8,
            # MAIS VARIAÇÕES
            "group_format": "Personality",
            "group_spectrum": "General",
            "group_stance": "General",
            "group_project": "OTHER", 
            "group_country": "Global",
            "group_identity": "General",
            "group_basis": "None",
            "group_territory": "Regional",
            "url": "https://t.me/test_group_3/003",
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram_test"
        }
    ]
    
    # Indexar documentos de teste
    success_count = 0
    for i, doc in enumerate(test_docs):
        try:
            success = es_client.index_message(doc)
            if success:
                success_count += 1
                print(f"✅ Documento {i+1}/3 indexado: {doc['group']} - {doc['group_format']}")
            else:
                print(f"❌ Falha ao indexar documento {i+1}")
        except Exception as e:
            print(f"❌ Erro no documento {i+1}: {e}")
    
    print(f"\n📊 RESUMO:")
    print(f"✅ Documentos criados com sucesso: {success_count}/3")
    
    if success_count > 0:
        print(f"\n🔄 PRÓXIMOS PASSOS:")
        print(f"1. Aguarde 1-2 minutos")
        print(f"2. Vá para OpenSearch Dashboards → Index Patterns")
        print(f"3. Clique em 'telegram-messages*'")
        print(f"4. Clique 'Refresh field list' 🔄")
        print(f"5. Procure pelos campos:")
        for field in ["group_format", "group_spectrum", "group_stance"]:
            print(f"   • {field}.keyword")
        
        print(f"\n✅ Campos devem aparecer na interface após o refresh!")
        return True
    else:
        print(f"\n❌ Nenhum documento foi criado com sucesso")
        return False

if __name__ == "__main__":
    success = create_test_documents()
    
    if success:
        print("\n" + "="*60)
        print("🎯 AGORA FAÇA O REFRESH DO INDEX PATTERN:")
        print("OpenSearch Dashboards → Index Patterns → telegram-messages* → Refresh field list")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Falha na criação dos documentos de teste")
        print("Verifique a conectividade com OpenSearch")
        print("="*60)
