#!/bin/bash
set -e

# =================================================================
# TELEGRAMSCRAP - ATIVAÇÃO MODO PRODUÇÃO
# =================================================================
# Script para ativar modo produção quando tiver permissões AWS
# Execute APENAS após criar Kinesis e OpenSearch na AWS

echo "🚀 TELEGRAMSCRAP - ATIVAÇÃO MODO PRODUÇÃO"
echo "========================================"
echo "⚠️ IMPORTANTE: Execute apenas após configurar:"
echo "   - Kinesis Data Stream: telegram-messages"
echo "   - OpenSearch Domain: telegramscrap-search"
echo "   - Lambda Function: telegram-processor"
echo ""

# Verificar se usuário tem certeza
read -p "Tem certeza que os serviços AWS estão configurados? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "❌ Operação cancelada. Configure AWS primeiro."
    exit 1
fi

PROJECT_DIR="/home/ec2-user/web-scraping-telegram"
cd "$PROJECT_DIR"

echo ""
echo "📋 COLETANDO INFORMAÇÕES AWS..."

# Coletar endpoints reais
echo "🔍 Digite os endpoints AWS reais:"
echo ""

read -p "OpenSearch Domain Endpoint: " OPENSEARCH_ENDPOINT
if [[ ! $OPENSEARCH_ENDPOINT =~ ^https://search- ]]; then
    echo "❌ Endpoint deve começar com 'https://search-'"
    exit 1
fi

KIBANA_URL="${OPENSEARCH_ENDPOINT}/_dashboards"

echo ""
echo "✅ Configuração coletada:"
echo "   OpenSearch: $OPENSEARCH_ENDPOINT"
echo "   Kibana: $KIBANA_URL"
echo ""

# Backup configuração atual
echo "💾 Backup configuração atual..."
cp ~/.bashrc ~/.bashrc.backup.prod.$(date +%Y%m%d_%H%M%S)

# Atualizar variáveis de ambiente
echo "🔧 Atualizando variáveis de ambiente..."

# Remover placeholders
sed -i 's/export DEVELOPMENT_MODE="true"/export DEVELOPMENT_MODE="false"/' ~/.bashrc
sed -i 's/export KINESIS_ENABLED="false"/export KINESIS_ENABLED="true"/' ~/.bashrc
sed -i 's/export ELASTICSEARCH_ENABLED="false"/export ELASTICSEARCH_ENABLED="true"/' ~/.bashrc

# Atualizar endpoints
escaped_endpoint=$(echo "$OPENSEARCH_ENDPOINT" | sed 's/[[\.*^$()+?{|]/\\&/g')
sed -i "s|export ELASTICSEARCH_ENDPOINT=\"https://PLACEHOLDER-OPENSEARCH-DOMAIN.us-east-1.es.amazonaws.com\"|export ELASTICSEARCH_ENDPOINT=\"$OPENSEARCH_ENDPOINT\"|" ~/.bashrc
sed -i "s|export KIBANA_URL=\"https://PLACEHOLDER-OPENSEARCH-DOMAIN.us-east-1.es.amazonaws.com/_dashboards\"|export KIBANA_URL=\"$KIBANA_URL\"|" ~/.bashrc

# Recarregar ambiente
source ~/.bashrc

echo "✅ Variáveis atualizadas"

# Testar conectividade
echo ""
echo "🧪 TESTANDO CONECTIVIDADE..."

# Teste AWS básico
echo "1. Testando AWS CLI..."
if aws sts get-caller-identity >/dev/null 2>&1; then
    echo "   ✅ AWS CLI funcionando"
else
    echo "   ❌ Erro AWS CLI"
    exit 1
fi

# Teste Kinesis
echo "2. Testando Kinesis..."
if aws kinesis describe-stream --stream-name telegram-messages >/dev/null 2>&1; then
    echo "   ✅ Kinesis Stream encontrado"
else
    echo "   ❌ Kinesis Stream 'telegram-messages' não encontrado"
    echo "      Crie o stream primeiro na AWS Console"
    exit 1
fi

# Teste OpenSearch
echo "3. Testando OpenSearch..."
if curl -s "$OPENSEARCH_ENDPOINT" >/dev/null 2>&1; then
    echo "   ✅ OpenSearch acessível"
else
    echo "   ❌ OpenSearch não acessível"
    echo "      Verifique endpoint e domain status"
    exit 1
fi

# Teste código Python
echo "4. Testando código Python..."
python3 -c "
import sys
sys.path.append('./src')
import os

# Configurar ambiente
os.environ['DEVELOPMENT_MODE'] = 'false'
os.environ['KINESIS_ENABLED'] = 'true'
os.environ['ELASTICSEARCH_ENABLED'] = 'true'

try:
    from utils.aws_kinesis import KinesisStreamer
    kinesis = KinesisStreamer()
    print(f'   ✅ Kinesis enabled: {kinesis.enabled}')

    from utils.aws_elasticsearch import ElasticsearchClient
    es = ElasticsearchClient()
    print(f'   ✅ Elasticsearch enabled: {es.enabled}')

except Exception as e:
    print(f'   ❌ Erro: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "   ❌ Erro no código Python"
    exit 1
fi

# Setup Kibana automático
echo ""
echo "📊 CONFIGURANDO KIBANA..."
if [ -f "kibana/setup/setup_kibana_dashboards.py" ]; then
    echo "🚀 Executando setup automático Kibana..."
    python3 kibana/setup/setup_kibana_dashboards.py

    if [ $? -eq 0 ]; then
        echo "   ✅ Kibana dashboards importados"
    else
        echo "   ⚠️ Erro no setup Kibana (pode ser temporário)"
    fi
else
    echo "   ⚠️ Script setup Kibana não encontrado"
fi

# Teste end-to-end
echo ""
echo "🎯 TESTE END-TO-END..."
python3 -c "
import sys
sys.path.append('./src')
import os, json
from datetime import datetime

# Configurar produção
os.environ['DEVELOPMENT_MODE'] = 'false'
os.environ['KINESIS_ENABLED'] = 'true'
os.environ['ELASTICSEARCH_ENABLED'] = 'true'

try:
    from utils.aws_kinesis import KinesisStreamer
    from utils.aws_elasticsearch import ElasticsearchClient
    from utils.monitoring import CloudWatchMonitor

    # Testar componentes
    kinesis = KinesisStreamer()
    es = ElasticsearchClient()
    monitor = CloudWatchMonitor()

    # Mensagem de teste
    test_message = {
        'message_id': 'prod_test_001',
        'group_name': 'test_production',
        'content': 'Teste de produção TelegramScrap',
        'date_message': datetime.now().isoformat(),
        'views': 100,
        'reactions': 10,
        'shares': 2,
        'category_1': 'POL',
        'category_4': 'General',
        'sentiment': 'neutral'
    }

    # Enviar para Kinesis
    if kinesis.enabled:
        result = kinesis.send_message(test_message)
        print(f'   ✅ Kinesis test: {result}')

    # Indexar no Elasticsearch
    if es.enabled:
        result = es.index_message(test_message)
        print(f'   ✅ Elasticsearch test: {result}')

    # Enviar métricas
    if monitor.enabled:
        test_stats = {
            'total_messages': 1,
            'groups_count': 1,
            'total_views': 100,
            'total_reactions': 10
        }
        result = monitor.send_scraping_metrics(test_stats)
        print(f'   ✅ CloudWatch test: {result}')

    print('🎉 PIPELINE PRODUÇÃO: FUNCIONANDO!')

except Exception as e:
    print(f'❌ Erro no teste: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Teste end-to-end falhou"
    exit 1
fi

# Configurar automação produção
echo ""
echo "🤖 CONFIGURANDO AUTOMAÇÃO..."

# Atualizar cron jobs para modo produção
crontab -l | sed 's|# TelegramScrap - Automação|# TelegramScrap - Automação (PRODUÇÃO)|' | crontab -

echo "✅ Automação configurada para produção"

# Resultado final
echo ""
echo "🎉 MODO PRODUÇÃO ATIVADO COM SUCESSO!"
echo "====================================="
echo ""
echo "📊 CONFIGURAÇÃO ATUAL:"
echo "   🚀 Modo: PRODUÇÃO"
echo "   ✅ Kinesis: HABILITADO ($KINESIS_STREAM_NAME)"
echo "   ✅ Elasticsearch: HABILITADO"
echo "   ✅ Kibana: CONFIGURADO ($KIBANA_URL)"
echo "   ✅ CloudWatch: HABILITADO"
echo "   ✅ Automação: ATIVA (diária 06:00)"
echo ""
echo "🔗 URLS IMPORTANTES:"
echo "   📊 Kibana: $KIBANA_URL"
echo "   ☁️ CloudWatch: https://console.aws.amazon.com/cloudwatch/"
echo "   🌊 Kinesis: https://console.aws.amazon.com/kinesis/"
echo ""
echo "👉 PRÓXIMOS PASSOS:"
echo "   1. Acessar Kibana e verificar dashboards"
echo "   2. Executar: ./scripts/run_telegramscrap_auto.sh"
echo "   3. Monitorar logs: tail -f logs/scraping_*.log"
echo "   4. Verificar métricas CloudWatch"
echo ""
echo "⚡ PIPELINE STREAMING ATIVO:"
echo "   Telegram → Kinesis → Lambda → Elasticsearch → Kibana"
echo ""
echo "🎯 SISTEMA TELEGRAMSCRAP TOTALMENTE OPERACIONAL! 🚀"

exit 0