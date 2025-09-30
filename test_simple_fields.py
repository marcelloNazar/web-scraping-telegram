#!/usr/bin/env python3
"""
Script simples para verificar se os campos de categorização estão disponíveis.
"""

import sys
sys.path.append('src')
from utils.aws_elasticsearch import ElasticsearchClient
import requests
import json

def test_categorization_fields():
    print("🔍 VERIFICANDO CAMPOS DE CATEGORIZAÇÃO")
    print("="*50)
    
    es_client = ElasticsearchClient()
    
    if not es_client.enabled:
        print("❌ Cliente OpenSearch não habilitado")
        return False
    
    print(f"✅ Cliente conectado: {es_client.domain_endpoint}")
    
    # Campos que precisamos para o dashboard
    required_fields = [
        'group_format',
        'group_spectrum', 
        'group_stance',
        'group_identity',
        'group_basis',
        'group_territory',
        'group_country',
        'group_project'
    ]
    
    try:
        # Verificar mapeamento
        url = f"{es_client.domain_endpoint}/telegram-messages/_mapping"
        response = requests.get(url, timeout=30, verify=False)
        
        if response.status_code == 200:
            mapping_data = response.json()
            
            # Encontrar propriedades
            properties = {}
            for index_name, index_data in mapping_data.items():
                props = index_data.get('mappings', {}).get('properties', {})
                properties.update(props)
            
            print("\n📊 STATUS DOS CAMPOS NECESSÁRIOS:")
            print("-" * 40)
            
            missing_fields = []
            available_fields = []
            
            for field in required_fields:
                if field in properties:
                    field_type = properties[field].get('type', 'unknown')
                    print(f"✅ {field} ({field_type})")
                    
                    # Verificar se tem .keyword
                    if field_type == 'text':
                        if 'fields' in properties[field] and 'keyword' in properties[field]['fields']:
                            print(f"   └── {field}.keyword DISPONÍVEL para agregações")
                            available_fields.append(f"{field}.keyword")
                        else:
                            print(f"   ❌ {field}.keyword NÃO ENCONTRADO")
                            missing_fields.append(f"{field}.keyword")
                    else:
                        available_fields.append(field)
                else:
                    print(f"❌ {field} - NÃO ENCONTRADO")
                    missing_fields.append(field)
            
            print(f"\n📊 RESUMO:")
            print(f"✅ Campos disponíveis: {len(available_fields)}")
            print(f"❌ Campos ausentes: {len(missing_fields)}")
            
            if missing_fields:
                print(f"\n🔧 CAMPOS AUSENTES:")
                for field in missing_fields:
                    print(f"   • {field}")
                print(f"\n💡 SOLUÇÃO: Execute 'python3 fix_opensearch_template.py'")
                return False
            else:
                print(f"\n🎉 TODOS OS CAMPOS ESTÃO DISPONÍVEIS!")
                return True
                
        else:
            print(f"❌ Erro ao verificar mapeamento: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    success = test_categorization_fields()
    
    if success:
        print("\n" + "="*50)
        print("🚀 PRÓXIMO PASSO:")
        print("Os campos estão disponíveis! Você pode criar as tabelas:")
        print("• group_format.keyword")
        print("• group_spectrum.keyword") 
        print("• group_stance.keyword")
        print("="*50)
    else:
        print("\n" + "="*50) 
        print("🔧 EXECUTE ESTE COMANDO PARA CORRIGIR:")
        print("python3 fix_opensearch_template.py")
        print("="*50)
