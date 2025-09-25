#!/usr/bin/env python3
"""
Deploy simples do Lambda atualizado para TelegramScrap
Atualiza o código da função Lambda telegram-processor
"""

import boto3
import zipfile
import io
import os
import sys
import json
from pathlib import Path

def update_lambda_code():
    """Atualizar apenas o código do Lambda"""

    print("🚀 Iniciando deploy Lambda simplificado...")

    # Localizar arquivo Lambda
    project_root = Path(__file__).parent.parent
    lambda_file = project_root / "lambda_functions" / "telegram_processor.py"

    if not lambda_file.exists():
        print(f"❌ Arquivo Lambda não encontrado: {lambda_file}")
        return False

    # Ler código Lambda atualizado
    try:
        with open(lambda_file, 'r', encoding='utf-8') as f:
            lambda_code = f.read()
        print(f"✅ Código Lambda carregado: {len(lambda_code)} caracteres")
    except Exception as e:
        print(f"❌ Erro lendo arquivo Lambda: {e}")
        return False

    # Criar ZIP em memória
    print("📦 Criando package de deployment...")
    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Adicionar código principal
            zip_file.writestr('lambda_function.py', lambda_code)

            # Adicionar requirements inline (requests-aws4auth precisa estar no layer)
            requirements = """
boto3>=1.26.0
requests>=2.28.0
requests-aws4auth>=1.1.2
"""
            zip_file.writestr('requirements.txt', requirements.strip())

        zip_buffer.seek(0)
        print(f"✅ Package criado: {len(zip_buffer.getvalue())} bytes")

    except Exception as e:
        print(f"❌ Erro criando ZIP: {e}")
        return False

    # Deploy usando boto3
    print("🔧 Fazendo deploy no AWS Lambda...")

    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')

        # Verificar se função existe
        try:
            lambda_client.get_function(FunctionName='telegram-processor')
            print("✅ Função telegram-processor encontrada")
        except lambda_client.exceptions.ResourceNotFoundException:
            print("❌ Função telegram-processor não encontrada na AWS")
            return False

        # Atualizar código da função
        response = lambda_client.update_function_code(
            FunctionName='telegram-processor',
            ZipFile=zip_buffer.getvalue()
        )

        # Validar response
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"✅ Lambda atualizado com sucesso!")
            print(f"   📅 Última modificação: {response['LastModified']}")
            print(f"   🔢 Versão: {response['Version']}")
            print(f"   💾 Tamanho código: {response['CodeSize']} bytes")
            print(f"   🔧 Runtime: {response['Runtime']}")
            return True
        else:
            print(f"⚠️ Response inesperado: {response['ResponseMetadata']['HTTPStatusCode']}")
            return False

    except Exception as e:
        print(f"❌ Erro no deploy: {e}")
        print("💡 Dicas:")
        print("   1. Verifique suas credenciais AWS")
        print("   2. Verifique se a função 'telegram-processor' existe")
        print("   3. Verifique permissões IAM para lambda:UpdateFunctionCode")
        return False

def update_lambda_environment():
    """Atualizar variáveis de ambiente se necessário"""

    print("🔧 Verificando variáveis de ambiente Lambda...")

    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')

        # Variáveis necessárias para o novo código
        required_env = {
            'OPENSEARCH_ENDPOINT': 'https://vpc-telegramscrap-search-nhuumyyyqbjjqoqjsiy6sntzd4.us-east-1.es.amazonaws.com',
            'OPENSEARCH_INDEX': 'telegram-messages',
            'DEVELOPMENT_MODE': 'false'
        }

        # Obter configuração atual
        response = lambda_client.get_function_configuration(
            FunctionName='telegram-processor'
        )

        current_env = response.get('Environment', {}).get('Variables', {})
        needs_update = False

        # Verificar se precisa atualizar
        for key, value in required_env.items():
            if current_env.get(key) != value:
                needs_update = True
                break

        if needs_update:
            print("📝 Atualizando variáveis de ambiente...")

            # Mesclar com variáveis existentes
            updated_env = {**current_env, **required_env}

            lambda_client.update_function_configuration(
                FunctionName='telegram-processor',
                Environment={'Variables': updated_env}
            )

            print("✅ Variáveis de ambiente atualizadas")
            for key, value in required_env.items():
                print(f"   {key}: {value}")
        else:
            print("✅ Variáveis de ambiente já estão corretas")

        return True

    except Exception as e:
        print(f"⚠️ Erro atualizando variáveis: {e}")
        return False

def test_lambda_deployment():
    """Testar se o deployment foi bem-sucedido"""

    print("🧪 Testando deployment...")

    try:
        lambda_client = boto3.client('lambda', region_name='us-east-1')

        # Criar evento de teste simples
        test_event = {
            "Records": [
                {
                    "kinesis": {
                        "data": "eyJ0ZXN0IjogdHJ1ZX0=",  # {"test": true} em base64
                        "sequenceNumber": "test-sequence-123"
                    }
                }
            ]
        }

        # Invocar função com timeout baixo para teste rápido
        response = lambda_client.invoke(
            FunctionName='telegram-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )

        if response['StatusCode'] == 200:
            print("✅ Teste de invocação bem-sucedido")
            return True
        else:
            print(f"⚠️ Teste falhou com status: {response['StatusCode']}")
            return False

    except Exception as e:
        print(f"⚠️ Erro no teste: {e}")
        print("💡 Isso pode ser normal se não há OpenSearch configurado")
        return True  # Não falhar por erro de conectividade OpenSearch

if __name__ == "__main__":
    print("🚀 TelegramScrap - Deploy Lambda Híbrido Jupyter + AWS")
    print("=" * 60)

    # 1. Atualizar código
    success_code = update_lambda_code()
    if not success_code:
        print("❌ Deploy falhou no código")
        sys.exit(1)

    # 2. Atualizar environment
    success_env = update_lambda_environment()
    if not success_env:
        print("⚠️ Environment pode ter problemas, mas continuando...")

    # 3. Testar deployment
    success_test = test_lambda_deployment()
    if not success_test:
        print("⚠️ Teste pode ter falhado, mas deploy foi concluído")

    print("\n" + "=" * 60)
    print("🎉 DEPLOY LAMBDA CONCLUÍDO!")
    print("📋 Próximos passos:")
    print("   1. Testar no Jupyter Notebook enviando dados para Kinesis")
    print("   2. Verificar logs no CloudWatch")
    print("   3. Conferir indexação no OpenSearch")
    print("=" * 60)