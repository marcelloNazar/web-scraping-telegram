# 🚀 Lambda Deployment Package - TelegramScrap

## 📋 **Conteúdo**

Este diretório contém todos os arquivos necessários para deploy da Lambda Function que processa mensagens do Kinesis e indexa no Elasticsearch.

### **📁 Arquivos:**

- `telegram_processor.py` - Código principal da Lambda
- `requirements.txt` - Dependências Python
- `deploy_lambda.sh` - Script para criar package ZIP
- `README.md` - Esta documentação

## 🎯 **Funcionalidade da Lambda**

### **📥 Input:**
- Mensagens do Kinesis Data Stream `telegram-messages`
- Formato: JSON com dados do Telegram

### **🔄 Processamento:**
1. **Decodifica** mensagens do Kinesis
2. **Classifica** automaticamente:
   - Categoria: POL/CONSPIRA/NAZ/OTHER
   - Espectro: Right/Left/General
   - Sentimento: positive/negative/neutral
3. **Enriquece** com tokens para word cloud
4. **Indexa** no Elasticsearch

### **📤 Output:**
- Documentos indexados no Elasticsearch
- Métricas enviadas para CloudWatch

## 🚀 **Como Fazer Deploy**

### **1. Preparar Package:**
```bash
cd lambda_deployment
chmod +x deploy_lambda.sh
./deploy_lambda.sh
```

### **2. Deploy na AWS (quando tiver permissões):**
1. **AWS Console → Lambda**
2. **Create Function:**
   - Function name: `telegram-processor`
   - Runtime: `Python 3.9`
   - Architecture: `x86_64`
3. **Upload ZIP:** `telegram-processor-lambda.zip`
4. **Configure Environment Variables:**
   ```
   ELASTICSEARCH_ENDPOINT=https://search-telegramscrap-XXX.us-east-1.es.amazonaws.com
   AWS_DEFAULT_REGION=us-east-1
   ```
5. **Configure Settings:**
   - Memory: 512 MB
   - Timeout: 5 minutes
6. **Add Kinesis Trigger:**
   - Source: Kinesis
   - Stream: `telegram-messages`
   - Batch size: 10

## 📊 **Métricas CloudWatch**

A Lambda envia automaticamente:
- `TelegramScrap/Lambda/ProcessedMessages` - Total processadas
- `TelegramScrap/Lambda/IndexedMessages` - Total indexadas

## 🔧 **Classificação Automática**

### **Categoria Principal:**
- **POL:** governo, presidente, política, eleição
- **CONSPIRA:** conspiração, illuminati, deep state
- **NAZ:** supremacia, hitler, nazismo
- **OTHER:** demais mensagens

### **Espectro Político:**
- **Right:** bolsonaro, direita, conservador
- **Left:** lula, esquerda, progressista
- **General:** demais

### **Sentimento:**
- **Positive:** bom, ótimo, excelente, sucesso, vitória
- **Negative:** ruim, péssimo, terrível, fracasso, derrota
- **Neutral:** balance ou sem palavras-chave

## ⚠️ **Dependências AWS**

### **Serviços Requeridos:**
- ✅ **Lambda** (criar function)
- ❌ **Kinesis** (aguardar permissões)
- ❌ **OpenSearch** (aguardar permissões)
- ✅ **CloudWatch** (já disponível)

### **IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "kinesis:DescribeStream",
        "kinesis:ListStreams"
      ],
      "Resource": "arn:aws:kinesis:us-east-1:*:stream/telegram-messages"
    },
    {
      "Effect": "Allow",
      "Action": [
        "es:ESHttpGet",
        "es:ESHttpPost",
        "es:ESHttpPut"
      ],
      "Resource": "arn:aws:es:us-east-1:*:domain/telegramscrap-search/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🎉 **Status**

- ✅ **Código:** 100% pronto
- ✅ **Package:** Preparado
- ❌ **Deploy:** Aguarda permissões Lambda
- ❌ **Teste:** Aguarda Kinesis + OpenSearch

**🚀 Pronto para deploy quando tiver permissões AWS!**