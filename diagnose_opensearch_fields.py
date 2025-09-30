#!/usr/bin/env python3
"""
Diagnóstico: Por que campos de categorização não aparecem no OpenSearch Dashboards
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.config_loader import load_config
from utils.aws_elasticsearch import ElasticsearchClient

def diagnose_opensearch():
    """Diagnosticar problema de campos não aparecendo"""
    print("\n🔍 DIAGNÓSTICO: CAMPOS DE CATEGORIZAÇÃO")
    print("=" * 80)
    
    config = load_config()
    es_client = ElasticsearchClient()
    
    if not es_client.enabled:
        print("❌ OpenSearch não habilitado")
        return
    
    print("\n📊 VERIFICAÇÃO 1: Índices existentes")
    print("-" * 80)
    
    try:
        response = es_client.es.cat.indices(index="telegram-messages*", format="json")
        
        total_docs = 0
        for idx in response:
            idx_name = idx['index']
            doc_count = int(idx.get('docs.count', 0))
            total_docs += doc_count
            print(f"   📁 {idx_name}: {doc_count:,} documentos")
        
        print(f"\n   📈 TOTAL: {total_docs:,} documentos em todos os índices")
        
    except Exception as e:
        print(f"   ❌ Erro ao listar índices: {e}")
    
    print("\n📊 VERIFICAÇÃO 2: Mensagens de teste (últimos 5 min)")
    print("-" * 80)
    
    try:
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-5m"
                                }
                            }
                        },
                        {
                            "prefix": {
                                "group.keyword": "@test_group"
                            }
                        }
                    ]
                }
            },
            "size": 10,
            "_source": [
                "group", "group_format", "group_spectrum", "group_stance",
                "@timestamp", "content"
            ]
        }
        
        result = es_client.es.search(index="telegram-messages*", body=query)
        hits = result.get('hits', {}).get('hits', [])
        
        if hits:
            print(f"   ✅ {len(hits)} mensagens de teste encontradas:")
            for hit in hits:
                source = hit['_source']
                idx_name = hit['_index']
                print(f"\n   📍 Índice: {idx_name}")
                print(f"      Grupo: {source.get('group')}")
                print(f"      Format: {source.get('group_format', '❌ AUSENTE')}")
                print(f"      Spectrum: {source.get('group_spectrum', '❌ AUSENTE')}")
                print(f"      Stance: {source.get('group_stance', '❌ AUSENTE')}")
        else:
            print("   ❌ Nenhuma mensagem de teste encontrada")
            print("   💡 Execute: python3 force_index_new_template.py")
    
    except Exception as e:
        print(f"   ❌ Erro na busca: {e}")
    
    print("\n📊 VERIFICAÇÃO 3: Documentos COM campos de categorização")
    print("-" * 80)
    
    try:
        query_with_fields = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "group_format"}},
                        {"exists": {"field": "group_spectrum"}},
                        {"exists": {"field": "group_stance"}}
                    ]
                }
            },
            "size": 0
        }
        
        result = es_client.es.search(index="telegram-messages*", body=query_with_fields)
        count_with = result['hits']['total']['value']
        
        query_all = {"query": {"match_all": {}}, "size": 0}
        result_all = es_client.es.search(index="telegram-messages*", body=query_all)
        count_all = result_all['hits']['total']['value']
        
        percentage = (count_with / count_all * 100) if count_all > 0 else 0
        
        print(f"   📈 Documentos COM categorização: {count_with:,}")
        print(f"   📈 Documentos TOTAL: {count_all:,}")
        print(f"   📊 Percentual: {percentage:.2f}%")
        
        if percentage < 1:
            print("\n   ⚠️  PROBLEMA IDENTIFICADO:")
            print("   └─ Menos de 1% dos documentos têm campos de categorização")
            print("   └─ OpenSearch Dashboards pode não mostrar campos raros")
        
    except Exception as e:
        print(f"   ❌ Erro ao contar documentos: {e}")
    
    print("\n📊 VERIFICAÇÃO 4: Mapping do índice atual")
    print("-" * 80)
    
    try:
        today_index = f"telegram-messages-{datetime.now().strftime('%Y.%m.%d')}"
        mapping = es_client.es.indices.get_mapping(index=today_index)
        
        if today_index in mapping:
            props = mapping[today_index]['mappings'].get('properties', {})
            
            categorization_fields = [
                'group_format', 'group_spectrum', 'group_stance',
                'group_project', 'group_country', 'group_identity',
                'group_basis', 'group_territory'
            ]
            
            print(f"   📁 Índice: {today_index}")
            print(f"   📋 Campos de categorização no mapping:")
            
            for field in categorization_fields:
                if field in props:
                    field_type = props[field].get('type', 'unknown')
                    has_keyword = 'fields' in props[field] and 'keyword' in props[field]['fields']
                    status = "✅" if has_keyword else "⚠️"
                    print(f"      {status} {field}: {field_type} (keyword: {has_keyword})")
                else:
                    print(f"      ❌ {field}: AUSENTE NO MAPPING")
        
    except Exception as e:
        print(f"   ℹ️  Índice de hoje ainda não existe: {e}")
    
    print("\n" + "=" * 80)
    print("🎯 CONCLUSÃO E SOLUÇÃO:")
    print("=" * 80)
    
    print("""
Se POUCOS documentos têm os campos de categorização:

📍 SOLUÇÃO RECOMENDADA:
   1. Aguardar scraper popular dados (próximas 24-48h)
   2. À medida que mais mensagens COM categorização forem indexadas
   3. Os campos aparecerão automaticamente no Dashboards

📍 SOLUÇÃO IMEDIATA (criar índice novo):
   python3 create_clean_index.py
   
   ⚠️  ATENÇÃO: Isso cria um NOVO índice limpo
   └─ Não afeta dados existentes
   └─ Permite testar visualizações imediatamente

📍 WORKAROUND TEMPORÁRIO (usar campos existentes):
   - Criar visualizações usando 'classification.keyword'
   - Criar visualizações usando 'group_name.keyword'
   - Criar visualizações usando 'content.keyword'
   - Adicionar categorização depois que aparecer
""")

if __name__ == "__main__":
    diagnose_opensearch()
