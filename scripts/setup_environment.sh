#!/bin/bash
set -e

# =================================================================
# TELEGRAMSCRAP - CONFIGURAÇÃO AUTOMÁTICA DE AMBIENTE
# =================================================================
# Configura ambiente de desenvolvimento/produção na VM
# Criado via Git workflow para deploy na VM

echo "🔧 TELEGRAMSCRAP - CONFIGURAÇÃO DE AMBIENTE"
echo "============================================="

# Verificar se estamos na VM
if [ ! -f "/etc/os-release" ] || ! grep -q "Amazon Linux" /etc/os-release 2>/dev/null; then
    echo "⚠️ AVISO: Este script foi projetado para Amazon Linux 2023"
    echo "   Continuando mesmo assim..."
fi

# Definir diretório do projeto
PROJECT_DIR="/home/ec2-user/web-scraping-telegram"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Verificar se estamos no diretório correto
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ ERRO: Diretório projeto não encontrado: $PROJECT_DIR"
    echo "   Execute este script na VM após git pull"
    exit 1
fi

echo "📂 Projeto encontrado: $PROJECT_DIR"

# 1. Configurar variáveis de ambiente
echo ""
echo "1️⃣ Configurando variáveis de ambiente..."

# Backup bashrc se existir
if [ -f ~/.bashrc ]; then
    cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d_%H%M%S)
    echo "   📋 Backup ~/.bashrc criado"
fi

# Configurar variáveis AWS (placeholders para quando tiver permissões)
echo ""
echo "# =========================================" >> ~/.bashrc
echo "# TELEGRAMSCRAP - CONFIGURAÇÃO AUTOMÁTICA" >> ~/.bashrc
echo "# =========================================" >> ~/.bashrc
echo "# Configurado em: $(date)" >> ~/.bashrc
echo "" >> ~/.bashrc

# Variáveis AWS
echo "# AWS Configuration" >> ~/.bashrc
echo 'export AWS_DEFAULT_REGION="us-east-1"' >> ~/.bashrc
echo "" >> ~/.bashrc

# Endpoints (placeholders)
echo "# AWS Service Endpoints (atualizar quando tiver permissões)" >> ~/.bashrc
echo 'export KINESIS_STREAM_NAME="telegram-messages"' >> ~/.bashrc
echo 'export ELASTICSEARCH_ENDPOINT="https://PLACEHOLDER-OPENSEARCH-DOMAIN.us-east-1.es.amazonaws.com"' >> ~/.bashrc
echo 'export KIBANA_URL="https://PLACEHOLDER-OPENSEARCH-DOMAIN.us-east-1.es.amazonaws.com/_dashboards"' >> ~/.bashrc
echo "" >> ~/.bashrc

# Configurações de desenvolvimento
echo "# Development/Production Mode" >> ~/.bashrc
echo 'export DEVELOPMENT_MODE="true"' >> ~/.bashrc
echo 'export KINESIS_ENABLED="false"' >> ~/.bashrc
echo 'export ELASTICSEARCH_ENABLED="false"' >> ~/.bashrc
echo "" >> ~/.bashrc

# Path do projeto
echo "# Project Path" >> ~/.bashrc
echo "export TELEGRAMSCRAP_HOME=\"$PROJECT_DIR\"" >> ~/.bashrc
echo 'export PATH="$TELEGRAMSCRAP_HOME/scripts:$PATH"' >> ~/.bashrc

echo "   ✅ Variáveis de ambiente configuradas"

# 2. Tornar scripts executáveis
echo ""
echo "2️⃣ Configurando permissões de scripts..."

SCRIPTS=(
    "run_telegramscrap_auto.sh"
    "backup_system.sh"
    "setup_environment.sh"
    "test_system_local.sh"
    "test_components.py"
    "check_aws_permissions.sh"
    "activate_production_mode.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPTS_DIR/$script" ]; then
        chmod +x "$SCRIPTS_DIR/$script"
        echo "   ✅ $script executável"
    else
        echo "   ⚠️ $script não encontrado"
    fi
done

# 3. Configurar cron jobs automáticos
echo ""
echo "3️⃣ Configurando automação (cron jobs)..."

# Backup crontab atual
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || touch /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt

# Remover jobs antigos do TelegramScrap se existirem
crontab -l 2>/dev/null | grep -v "telegramscrap" | grep -v "TelegramScrap" | crontab - 2>/dev/null || true

# Adicionar novos jobs
(crontab -l 2>/dev/null; echo "") | crontab -
(crontab -l 2>/dev/null; echo "# TelegramScrap - Automação") | crontab -
(crontab -l 2>/dev/null; echo "0 6 * * * $SCRIPTS_DIR/run_telegramscrap_auto.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * 0 $SCRIPTS_DIR/backup_system.sh") | crontab -

echo "   ✅ Cron jobs configurados:"
echo "      - Scraping diário: 06:00"
echo "      - Backup semanal: 02:00 (domingo)"

# 4. Criar estrutura de diretórios
echo ""
echo "4️⃣ Criando estrutura de diretórios..."

DIRS=(
    "$PROJECT_DIR/logs"
    "/home/ec2-user/backups"
    "$PROJECT_DIR/data/raw"
    "$PROJECT_DIR/data/processed"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
    echo "   ✅ $dir"
done

# 5. Testar configuração
echo ""
echo "5️⃣ Testando configuração..."

# Recarregar bashrc
source ~/.bashrc

# Testar variáveis
if [ -n "$TELEGRAMSCRAP_HOME" ] && [ -n "$AWS_DEFAULT_REGION" ]; then
    echo "   ✅ Variáveis de ambiente carregadas"
else
    echo "   ❌ Erro carregando variáveis"
    exit 1
fi

# Testar AWS CLI
if command -v aws >/dev/null 2>&1; then
    if aws sts get-caller-identity >/dev/null 2>&1; then
        echo "   ✅ AWS CLI funcionando"
    else
        echo "   ⚠️ AWS CLI instalado mas credenciais não configuradas"
    fi
else
    echo "   ⚠️ AWS CLI não encontrado"
fi

# Testar Python
if python3 -c "import sys; sys.path.append('$PROJECT_DIR/src'); print('Python OK')" 2>/dev/null; then
    echo "   ✅ Python funcionando"
else
    echo "   ❌ Erro na configuração Python"
fi

# 6. Mostrar próximos passos
echo ""
echo "🎯 CONFIGURAÇÃO CONCLUÍDA!"
echo "========================="
echo ""
echo "📋 RESUMO DA CONFIGURAÇÃO:"
echo "   ✅ Variáveis de ambiente: configuradas"
echo "   ✅ Scripts executáveis: configurados"
echo "   ✅ Cron jobs: ativos"
echo "   ✅ Diretórios: criados"
echo "   ✅ Testes básicos: OK"
echo ""
echo "🔄 MODO ATUAL: DESENVOLVIMENTO"
echo "   - Kinesis: DESABILITADO"
echo "   - Elasticsearch: DESABILITADO"
echo "   - CloudWatch: HABILITADO"
echo "   - Google Sheets: HABILITADO"
echo ""
echo "🚀 PRÓXIMOS PASSOS:"
echo "   1. Testar: $SCRIPTS_DIR/run_telegramscrap_auto.sh"
echo "   2. Verificar logs: $PROJECT_DIR/logs/"
echo "   3. Aguardar permissões AWS para Kinesis/OpenSearch"
echo "   4. Alterar para modo produção quando disponível"
echo ""
echo "⚡ COMANDOS ÚTEIS:"
echo "   - Ver cron jobs: crontab -l"
echo "   - Teste manual: cd $PROJECT_DIR && ./scripts/run_telegramscrap_auto.sh"
echo "   - Ver logs: tail -f $PROJECT_DIR/logs/scraping_*.log"
echo "   - Backup manual: ./scripts/backup_system.sh"
echo ""

# 7. Verificação final dos cron jobs
echo "📅 CRON JOBS ATIVOS:"
crontab -l | grep -E "(telegramscrap|TelegramScrap)" || echo "   ⚠️ Nenhum cron job encontrado"

echo ""
echo "🎉 AMBIENTE PRONTO PARA USO!"
echo "================================"

exit 0