#!/usr/bin/env python3
"""
Script para forçar indexação de dados com novo template de prioridade 9999
"""

import os
import sys
from datetime import datetime, timedelta
import json

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.aws_elasticsearch import ElasticsearchClient
from utils.config_loader import load_config

def force_index_with_new_template():
    """Força indexação de mensagens de teste com novo template"""
    
    print("🚀 FORÇANDO INDEXAÇÃO COM NOVO TEMPLATE")
    print("=" * 60)
    
    # Carregar configurações
    config = load_config()
    
    # Inicializar cliente OpenSearch
    es_client = ElasticsearchClient(
        domain_name=config.opensearch_domain_name,
        region_name=config.aws_region,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key
    )
    if not es_client.enabled:
        print("❌ OpenSearch não habilitado")
        return False
        
    # Dados de teste com TODOS os campos de categorização
    test_messages = [
        {
            "@timestamp": datetime.now().isoformat(),
            "group": "@test_group_1",
            "content": "Mensagem de teste 1 - Template prioridade 9999",
            "date": datetime.now().isoformat(),
            "message_id": f"test_msg_{int(datetime.now().timestamp())}_1",
            "author_id": "test_user_1",
            "classification": "POL",
            "views": 100,
            "reactions": 5,
            "shares": 2,
            "url": "https://t.me/test_group_1/1",
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram",
            
            # CAMPOS DE CATEGORIZAÇÃO - NOVOS DO TEMPLATE 9999
            "group_project": "Pol",
            "group_country": "Brasil", 
            "group_format": "Debate",
            "group_spectrum": "Right",
            "group_stance": "Conservative",
            "group_identity": "General",
            "group_basis": "Bolsonarista",
            "group_territory": "National"
        },
        {
            "@timestamp": (datetime.now() - timedelta(minutes=1)).isoformat(),
            "group": "@test_group_2",
            "content": "Mensagem de teste 2 - Verificação campos .keyword",
            "date": (datetime.now() - timedelta(minutes=1)).isoformat(),
            "message_id": f"test_msg_{int(datetime.now().timestamp())}_2",
            "author_id": "test_user_2", 
            "classification": "OTHER",
            "views": 50,
            "reactions": 3,
            "shares": 1,
            "url": "https://t.me/test_group_2/1",
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram",
            
            # DIFERENTES VALORES PARA TESTAR AGREGAÇÕES
            "group_project": "Naz",
            "group_country": "USA",
            "group_format": "News", 
            "group_spectrum": "Left",
            "group_stance": "Progressive",
            "group_identity": "Socialist / Communist",
            "group_basis": "None",
            "group_territory": "Regional"
        },
        {
            "@timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "group": "@test_group_3",
            "content": "Mensagem de teste 3 - Validação template funcionou",
            "date": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "message_id": f"test_msg_{int(datetime.now().timestamp())}_3",
            "author_id": "test_user_3",
            "classification": "CONSPIRA",
            "views": 200,
            "reactions": 10,
            "shares": 5,
            "url": "https://t.me/test_group_3/1", 
            "indexed_at": datetime.now().isoformat(),
            "source": "telegram",
            
            # TERCEIRO CONJUNTO DE VALORES
            "group_project": "Conspira",
            "group_country": "Global",
            "group_format": "Personality",
            "group_spectrum": "General", 
            "group_stance": "General",
            "group_identity": "Religious",
            "group_basis": "Lulista/Petista",
            "group_territory": "Local"
        }
    ]
    
    print(f"📤 Indexando {len(test_messages)} mensagens de teste...")
    
    success_count = 0
    for i, message in enumerate(test_messages, 1):
        try:
            # Forçar indexação individual para garantir aplicação do template
            success = es_client.index_message(
                message_data=message,
                index_name="telegram-messages-test"  # Usar nome que força aplicação do template
            )
            
            if success:
                success_count += 1
                print(f"✅ Mensagem {i}: {message['group']} - {message['group_format']} | {message['group_spectrum']}")
            else:
                print(f"❌ Mensagem {i}: Falha na indexação")
                
        except Exception as e:
            print(f"❌ Mensagem {i}: Erro - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO: {success_count}/{len(test_messages)} mensagens indexadas")
    
    if success_count > 0:
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("1. Aguarde 30 segundos para processamento")
        print("2. Vá para Stack Management → Index Patterns → telegram-messages*")
        print("3. Clique em 🔄 Refresh field list")
        print("4. Procure por group_format.keyword, group_spectrum.keyword, group_stance.keyword")
        print("5. Se aparecerem: ✅ TEMPLATE FUNCIONOU!")
        
        return True
    else:
        print("❌ Nenhuma mensagem foi indexada - verifique configuração OpenSearch")
        return False

if __name__ == "__main__":
    try:
        force_index_with_new_template()
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
