#!/usr/bin/env python3
"""
Script para forçar a recriação do template do OpenSearch com os campos de categorização.
"""

import sys
sys.path.append('src')
from utils.aws_elasticsearch import ElasticsearchClient

def force_recreate_template():
    print("🔨 FORÇANDO RECRIAÇÃO DO TEMPLATE")
    print("="*50)
    
    es_client = ElasticsearchClient()
    
    if not es_client.enabled:
        print("❌ Cliente não habilitado")
        return
    
    print(f"🔗 Conectado ao: {es_client.domain_endpoint}")
    
    # Deletar template existente
    try:
        import requests
        url = f"{es_client.domain_endpoint}/_index_template/telegram-messages-template"
        response = requests.delete(url, timeout=30, verify=False)
        print(f"🗑️ Template deletado: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Erro ao deletar (pode não existir): {e}")
    
    # Recriar template
    print("🔨 Criando novo template...")
    success = es_client.create_index_template()
    
    if success:
        print("✅ Template recriado com sucesso!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Aguarde 5-10 minutos para novos dados chegarem")
        print("2. Execute: python3 test_opensearch_template.py")
        print("3. Verifique se campos aparecem na interface do OpenSearch")
    else:
        print("❌ Falha ao recriar template")
        print("\n🔧 SOLUÇÃO:")
        print("1. Verifique as credenciais AWS")
        print("2. Confirme que o domínio OpenSearch está acessível")
        print("3. Revise as permissões do IAM Role")

if __name__ == "__main__":
    force_recreate_template()
