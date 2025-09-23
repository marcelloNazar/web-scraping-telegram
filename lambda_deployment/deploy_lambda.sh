#!/bin/bash
set -e

echo "🚀 Preparando deployment da Lambda..."

# Verificar se estamos no diretório correto
if [ ! -f "telegram_processor.py" ]; then
    echo "❌ Erro: telegram_processor.py não encontrado"
    echo "   Execute este script no diretório lambda_deployment/"
    exit 1
fi

# Criar diretório temporário para build
BUILD_DIR="lambda_build_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BUILD_DIR"

echo "📦 Copiando arquivos para build..."
cp telegram_processor.py "$BUILD_DIR/"
cp requirements.txt "$BUILD_DIR/"

cd "$BUILD_DIR"

echo "📥 Instalando dependências..."
pip install -r requirements.txt -t . --quiet

echo "🗜️ Criando package ZIP..."
zip -r ../telegram-processor-lambda.zip . -x "*.txt" "*.sh" "*.md" --quiet

cd ..
rm -rf "$BUILD_DIR"

echo "✅ Deployment package criado: telegram-processor-lambda.zip"
echo "📊 Tamanho do arquivo:"
ls -lh telegram-processor-lambda.zip

echo ""
echo "👉 PRÓXIMOS PASSOS:"
echo "   1. Acesse AWS Console → Lambda"
echo "   2. Create Function → 'telegram-processor'"
echo "   3. Upload ZIP: telegram-processor-lambda.zip"
echo "   4. Configure environment variables"
echo "   5. Add Kinesis trigger quando disponível"
echo ""
echo "⚠️ IMPORTANTE: Execute apenas quando tiver permissões Lambda na AWS!"