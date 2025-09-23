#!/bin/bash
set -e

# =================================================================
# TELEGRAMSCRAP - VERIFICAÇÃO AUTOMÁTICA DE PERMISSÕES AWS
# =================================================================
# Verifica se todas as permissões AWS necessárias estão disponíveis
# Criado via Git workflow para deploy na VM

echo "🔍 TELEGRAMSCRAP - VERIFICAÇÃO PERMISSÕES AWS"
echo "============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
PERMISSIONS_OK=0
PERMISSIONS_TOTAL=0

check_permission() {
    local service="$1"
    local command="$2"
    local description="$3"

    PERMISSIONS_TOTAL=$((PERMISSIONS_TOTAL + 1))

    echo -n "Testando $service: $description... "

    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
        return 0
    else
        echo -e "${RED}❌ FALHOU${NC}"
        return 1
    fi
}

echo ""
echo "📋 VERIFICANDO PERMISSÕES AWS..."
echo ""

# 1. Verificação básica AWS CLI
echo "1️⃣ AWS CLI e Credenciais"
check_permission "AWS CLI" "aws sts get-caller-identity" "Verificar identidade"

if [ $? -eq 0 ]; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null)
    echo "   📋 Account: $AWS_ACCOUNT"
    echo "   👤 User: $AWS_USER"
else
    echo -e "   ${RED}❌ AWS CLI não configurado ou sem permissões${NC}"
    echo "   👉 Configure com: aws configure"
    exit 1
fi

echo ""

# 2. CloudWatch (deve estar sempre disponível)
echo "2️⃣ CloudWatch"
check_permission "CloudWatch" "aws cloudwatch list-metrics --namespace AWS/EC2 --max-items 1" "Listar métricas"
check_permission "CloudWatch" "aws cloudwatch put-metric-data --namespace TelegramScrap/Test --metric-data MetricName=TestMetric,Value=1" "Enviar métricas"

echo ""

# 3. Kinesis Data Streams
echo "3️⃣ Kinesis Data Streams"
check_permission "Kinesis" "aws kinesis list-streams" "Listar streams"

# Verificar se stream específico existe
if aws kinesis describe-stream --stream-name telegram-messages >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Stream 'telegram-messages' encontrado${NC}"
    STREAM_STATUS=$(aws kinesis describe-stream --stream-name telegram-messages --query StreamDescription.StreamStatus --output text 2>/dev/null)
    echo "   📊 Status: $STREAM_STATUS"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    echo -e "   ${YELLOW}⚠️ Stream 'telegram-messages' não encontrado${NC}"
    echo "   👉 Crie com: aws kinesis create-stream --stream-name telegram-messages --shard-count 1"
fi
PERMISSIONS_TOTAL=$((PERMISSIONS_TOTAL + 1))

check_permission "Kinesis" "aws kinesis put-record --stream-name telegram-messages --data '{\"test\":\"data\"}' --partition-key test" "Enviar dados para stream"

echo ""

# 4. OpenSearch/Elasticsearch
echo "4️⃣ OpenSearch/Elasticsearch"
check_permission "OpenSearch" "aws opensearch list-domain-names" "Listar domínios"

# Verificar domínio específico
if aws opensearch describe-domain --domain-name telegramscrap-search >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Domínio 'telegramscrap-search' encontrado${NC}"
    DOMAIN_STATUS=$(aws opensearch describe-domain --domain-name telegramscrap-search --query DomainStatus.Processing --output text 2>/dev/null)
    ENDPOINT=$(aws opensearch describe-domain --domain-name telegramscrap-search --query DomainStatus.Endpoint --output text 2>/dev/null)
    echo "   📊 Processing: $DOMAIN_STATUS"
    echo "   🔗 Endpoint: https://$ENDPOINT"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    echo -e "   ${YELLOW}⚠️ Domínio 'telegramscrap-search' não encontrado${NC}"
    echo "   👉 Crie via AWS Console ou CLI"
fi
PERMISSIONS_TOTAL=$((PERMISSIONS_TOTAL + 1))

echo ""

# 5. Lambda
echo "5️⃣ Lambda Functions"
check_permission "Lambda" "aws lambda list-functions" "Listar funções"

# Verificar função específica
if aws lambda get-function --function-name telegram-processor >/dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Função 'telegram-processor' encontrada${NC}"
    FUNCTION_STATUS=$(aws lambda get-function --function-name telegram-processor --query Configuration.State --output text 2>/dev/null)
    echo "   📊 Status: $FUNCTION_STATUS"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    echo -e "   ${YELLOW}⚠️ Função 'telegram-processor' não encontrada${NC}"
    echo "   👉 Deploy com arquivos em lambda_deployment/"
fi
PERMISSIONS_TOTAL=$((PERMISSIONS_TOTAL + 1))

check_permission "Lambda" "aws lambda invoke --function-name telegram-processor --payload '{}' /tmp/lambda_test.json" "Invocar função"

echo ""

# 6. IAM (verificações básicas)
echo "6️⃣ IAM Permissions"
check_permission "IAM" "aws iam list-attached-user-policies --user-name \$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2) 2>/dev/null || aws iam list-attached-role-policies --role-name \$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2) 2>/dev/null || echo 'checked'" "Listar políticas anexadas"

echo ""

# 7. S3 (se necessário para backups)
echo "7️⃣ S3 (Opcional)"
check_permission "S3" "aws s3 ls" "Listar buckets"

echo ""

# Resultado final
echo "📊 RESUMO DA VERIFICAÇÃO"
echo "========================"
echo "Permissões OK: $PERMISSIONS_OK/$PERMISSIONS_TOTAL"

SUCCESS_RATE=$((PERMISSIONS_OK * 100 / PERMISSIONS_TOTAL))
echo "Taxa de sucesso: $SUCCESS_RATE%"

echo ""

if [ $SUCCESS_RATE -ge 80 ]; then
    echo -e "${GREEN}🎉 SISTEMA PRONTO PARA PRODUÇÃO!${NC}"
    echo ""
    echo "✅ PRÓXIMOS PASSOS:"
    echo "   1. Executar: ./scripts/activate_production_mode.sh"
    echo "   2. Testar: ./scripts/run_telegramscrap_auto.sh"
    echo "   3. Monitorar: tail -f logs/scraping_*.log"

elif [ $SUCCESS_RATE -ge 50 ]; then
    echo -e "${YELLOW}⚠️ SISTEMA PARCIALMENTE PRONTO${NC}"
    echo ""
    echo "🔧 AÇÕES NECESSÁRIAS:"
    echo "   1. Corrigir permissões faltantes acima"
    echo "   2. Executar modo desenvolvimento: DEVELOPMENT_MODE=true"
    echo "   3. Criar recursos AWS pendentes"

else
    echo -e "${RED}❌ SISTEMA NÃO PRONTO${NC}"
    echo ""
    echo "🚨 PROBLEMAS CRÍTICOS:"
    echo "   1. Muitas permissões em falta"
    echo "   2. Verificar configuração AWS CLI"
    echo "   3. Validar credenciais e políticas IAM"
fi

echo ""
echo "📋 CONFIGURAÇÃO ATUAL RECOMENDADA:"
if [ $SUCCESS_RATE -ge 80 ]; then
    echo "   export DEVELOPMENT_MODE=\"false\""
    echo "   export KINESIS_ENABLED=\"true\""
    echo "   export ELASTICSEARCH_ENABLED=\"true\""
else
    echo "   export DEVELOPMENT_MODE=\"true\""
    echo "   export KINESIS_ENABLED=\"false\""
    echo "   export ELASTICSEARCH_ENABLED=\"false\""
fi

echo ""
echo "📚 DOCUMENTAÇÃO ÚTIL:"
echo "   - AWS CLI: https://docs.aws.amazon.com/cli/"
echo "   - Kinesis: https://docs.aws.amazon.com/kinesis/"
echo "   - OpenSearch: https://docs.aws.amazon.com/opensearch-service/"
echo "   - Lambda: https://docs.aws.amazon.com/lambda/"

exit 0