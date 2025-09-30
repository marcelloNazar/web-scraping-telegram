#!/usr/bin/env python3
"""
Diagnóstico SIMPLIFICADO: Por que campos de categorização não aparecem
"""

import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.config_loader import load_config
from utils.aws_elasticsearch import ElasticsearchClient

def diagnose():
    """Diagnóstico simplificado"""
    print("\n🔍 DIAGNÓSTICO SIMPLIFICADO")
    print("=" * 80)
    
    config = load_config()
    es_client = ElasticsearchClient()
    
    if not es_client.enabled:
        print("❌ OpenSearch não habilitado")
        return
    
    endpoint = es_client.domain_endpoint
    print(f"\n📍 Endpoint: {endpoint}")
    
    print("\n📊 VERIFICAÇÃO 1: Mensagens de teste (últimos 10 min)")
    print("-" * 80)
    
    try:
        # Buscar mensagens de teste
        query = {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gte": "now-10m"}}},
                    {"prefix": {"group.keyword": "@test_"}}
                ]
            }
        }
        
        results = es_client.search_messages(query, size=10)
        
        if results:
            print(f"   ✅ {len(results)} mensagens de teste encontradas:")
            for msg in results[:3]:
                print(f"\n      Grupo: {msg.get('group')}")
                print(f"      Format: {msg.get('group_format', '❌ AUSENTE')}")
                print(f"      Spectrum: {msg.get('group_spectrum', '❌ AUSENTE')}")
                print(f"      Stance: {msg.get('group_stance', '❌ AUSENTE')}")
        else:
            print("   ❌ Nenhuma mensagem de teste encontrada")
            print("   💡 Execute: python3 force_index_new_template.py")
    
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n📊 VERIFICAÇÃO 2: Contagem total de documentos")
    print("-" * 80)
    
    try:
        url = f"{endpoint}/telegram-messages*/_count"
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('count', 0)
            print(f"   📈 Total de documentos: {total:,}")
        else:
            print(f"   ⚠️  Status: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n📊 VERIFICAÇÃO 3: Documentos COM categorização")
    print("-" * 80)
    
    try:
        # Contar documentos que têm group_format
        url = f"{endpoint}/telegram-messages*/_count"
        query_body = {
            "query": {
                "exists": {"field": "group_format"}
            }
        }
        
        response = requests.post(
            url,
            json=query_body,
            headers={'Content-Type': 'application/json'},
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            count_with = response.json().get('count', 0)
            
            # Total
            response_all = requests.get(f"{endpoint}/telegram-messages*/_count", verify=False, timeout=10)
            count_all = response_all.json().get('count', 0)
            
            percentage = (count_with / count_all * 100) if count_all > 0 else 0
            
            print(f"   📈 COM categorização: {count_with:,}")
            print(f"   📈 Total: {count_all:,}")
            print(f"   📊 Percentual: {percentage:.2f}%")
            
            if percentage < 0.1:
                print(f"\n   🚨 PROBLEMA CONFIRMADO!")
                print(f"   └─ Apenas {percentage:.4f}% dos documentos têm categorização")
                print(f"   └─ OpenSearch Dashboards NÃO mostra campos raros")
                print(f"\n   💡 SOLUÇÃO: Executar força população")
                print(f"      python3 force_populate_categorization.py")
            elif percentage < 5:
                print(f"\n   ⚠️  Baixa cobertura ({percentage:.2f}%)")
                print(f"   💡 Recomendado popular mais documentos")
            else:
                print(f"\n   ✅ Boa cobertura! Campos deveriam aparecer")
                print(f"   💡 Tente: Management → Index Patterns → Refresh")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 PRÓXIMO PASSO:")
    print("=" * 80)
    print("""
Se percentual < 1%:
   python3 force_populate_categorization.py
   
Depois:
   OpenSearch Dashboards → Management → Index Patterns → Refresh
""")

if __name__ == "__main__":
    diagnose()
