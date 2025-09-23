# 🔧 Scripts TelegramScrap - Automação e Testes

## 📋 **Visão Geral**

Este diretório contém todos os scripts necessários para operação, automação e testes do sistema TelegramScrap na VM EC2.

### **🎯 Criados via Git Workflow:**
- ✅ Desenvolvimento local
- ✅ Commit no repositório
- ✅ Deploy via `git pull` na VM
- ✅ Execução na EC2

---

## 📁 **Arquivos Disponíveis**

### **🚀 Scripts de Automação (FASE 2)**

#### **1. `run_telegramscrap_auto.sh`**
```bash
# Script principal de execução automática
📍 Uso: ./scripts/run_telegramscrap_auto.sh
🎯 Função: Executa scraping com suporte a modo desenvolvimento/produção
⏰ Cron: Diário às 06:00
```

**Características:**
- ✅ Suporte modo desenvolvimento (sem Kinesis/OpenSearch)
- ✅ Suporte modo produção (com streaming completo)
- ✅ Logging automático
- ✅ Validação de dependências
- ✅ Envio métricas CloudWatch
- ✅ Commit automático dos resultados

#### **2. `backup_system.sh`**
```bash
# Sistema completo de backup
📍 Uso: ./scripts/backup_system.sh
🎯 Função: Backup código, dados e configurações
⏰ Cron: Semanal (domingo 02:00)
```

**Características:**
- ✅ Backup código completo (tar.gz)
- ✅ Backup configurações sistema
- ✅ Backup dados recentes (7 dias)
- ✅ Backup logs importantes (3 dias)
- ✅ Índice detalhado
- ✅ Cleanup automático (30 dias)

#### **3. `setup_environment.sh`**
```bash
# Configuração automática ambiente VM
📍 Uso: ./scripts/setup_environment.sh
🎯 Função: Configurar variáveis, cron jobs e estrutura
⚡ Executar: Uma vez após git pull
```

**Características:**
- ✅ Configuração variáveis ambiente
- ✅ Permissões scripts executáveis
- ✅ Cron jobs automáticos
- ✅ Estrutura diretórios
- ✅ Testes básicos

---

### **🧪 Scripts de Teste (FASE 3)**

#### **4. `test_system_local.sh`**
```bash
# Teste completo sistema local
📍 Uso: ./scripts/test_system_local.sh
🎯 Função: Validar todos componentes sem AWS streaming
📊 Output: Relatório detalhado + taxa sucesso
```

**Testes Incluídos:**
- ✅ Infraestrutura básica (Python, AWS CLI, Git)
- ✅ Conectividade AWS
- ✅ Código Python (importações)
- ✅ Serviços funcionais (CloudWatch, Google Sheets)
- ✅ Integração simulada
- ✅ Arquivos e estrutura

#### **5. `test_components.py`**
```bash
# Teste individual componentes
📍 Uso: ./scripts/test_components.py
🎯 Função: Teste detalhado cada componente
📊 Output: Relatório por componente
```

**Componentes Testados:**
- ✅ Config Loader
- ✅ CloudWatch Monitor
- ✅ Google Sheets Integration
- ✅ Kinesis (modo dev)
- ✅ Elasticsearch (modo dev)
- ✅ Código Lambda
- ✅ Arquivos Kibana
- ✅ Arquivos de dados
- ✅ Integração simulada

---

### **🚀 Scripts de Produção**

#### **6. `activate_production_mode.sh`**
```bash
# Ativação modo produção
📍 Uso: ./scripts/activate_production_mode.sh
🎯 Função: Ativar modo produção quando tiver permissões AWS
⚠️ IMPORTANTE: Executar apenas após criar Kinesis/OpenSearch
```

**Funcionalidades:**
- ✅ Coleta endpoints AWS reais
- ✅ Atualiza variáveis ambiente
- ✅ Testa conectividade completa
- ✅ Setup automático Kibana
- ✅ Teste end-to-end
- ✅ Ativa pipeline streaming

---

## 🎯 **Fluxo de Execução Recomendado**

### **1️⃣ Setup Inicial (uma vez):**
```bash
cd /home/ec2-user/web-scraping-telegram
git pull origin main
./scripts/setup_environment.sh
```

### **2️⃣ Validação Sistema:**
```bash
./scripts/test_system_local.sh
./scripts/test_components.py
```

### **3️⃣ Execução Desenvolvimento:**
```bash
# Manual
./scripts/run_telegramscrap_auto.sh

# Automático (já configurado)
# Cron: 0 6 * * * (diário 06:00)
```

### **4️⃣ Quando Tiver Permissões AWS:**
```bash
# Primeiro: criar Kinesis + OpenSearch na AWS Console
# Depois:
./scripts/activate_production_mode.sh
```

### **5️⃣ Backup (automático):**
```bash
# Manual
./scripts/backup_system.sh

# Automático (já configurado)
# Cron: 0 2 * * 0 (semanal domingo 02:00)
```

---

## 📊 **Modos de Operação**

### **🔧 Modo Desenvolvimento (Atual)**
```bash
DEVELOPMENT_MODE="true"
KINESIS_ENABLED="false"
ELASTICSEARCH_ENABLED="false"
```

**Comportamento:**
- ✅ Google Sheets: Ativo
- ✅ CloudWatch: Ativo
- ✅ Simulação dados
- ❌ Kinesis: Disabled
- ❌ Elasticsearch: Disabled

### **🚀 Modo Produção (Futuro)**
```bash
DEVELOPMENT_MODE="false"
KINESIS_ENABLED="true"
ELASTICSEARCH_ENABLED="true"
```

**Comportamento:**
- ✅ Google Sheets: Ativo
- ✅ CloudWatch: Ativo
- ✅ Kinesis: Streaming real-time
- ✅ Elasticsearch: Indexação
- ✅ Kibana: Dashboards ativos

---

## 📋 **Logs e Monitoramento**

### **📁 Localização Logs:**
```bash
/home/ec2-user/web-scraping-telegram/logs/
├── scraping_YYYYMMDD_HHMMSS.log
├── backup_YYYYMMDD_HHMMSS.log
└── test_YYYYMMDD_HHMMSS.log
```

### **👀 Monitoramento:**
```bash
# Logs em tempo real
tail -f logs/scraping_*.log

# Status cron jobs
crontab -l

# Últimos backups
ls -la /home/ec2-user/backups/

# Teste rápido
./scripts/test_components.py
```

---

## 🔧 **Configuração Cron Jobs**

```bash
# Configurado automaticamente por setup_environment.sh

# Scraping diário
0 6 * * * /home/ec2-user/web-scraping-telegram/scripts/run_telegramscrap_auto.sh

# Backup semanal
0 2 * * 0 /home/ec2-user/web-scraping-telegram/scripts/backup_system.sh
```

---

## ⚠️ **Dependências AWS**

### **✅ Funciona Agora (sem permissões especiais):**
- CloudWatch (métricas)
- EC2 (básico)
- IAM (get-caller-identity)

### **❌ Requer Permissões (aguardando):**
- Kinesis Data Streams
- OpenSearch Service
- Lambda Functions

---

## 🎉 **Status dos Scripts**

| Script | Status | Funcional | Testado |
|--------|--------|-----------|---------|
| `run_telegramscrap_auto.sh` | ✅ Pronto | ✅ Sim | ✅ Modo dev |
| `backup_system.sh` | ✅ Pronto | ✅ Sim | ✅ Completo |
| `setup_environment.sh` | ✅ Pronto | ✅ Sim | ✅ Completo |
| `test_system_local.sh` | ✅ Pronto | ✅ Sim | ✅ Completo |
| `test_components.py` | ✅ Pronto | ✅ Sim | ✅ Completo |
| `activate_production_mode.sh` | ✅ Pronto | ⏳ Aguarda AWS | ⏳ Quando tiver permissões |

---

## 📞 **Troubleshooting**

### **❓ Script não executa?**
```bash
# Verificar permissões
ls -la scripts/
chmod +x scripts/*.sh scripts/*.py
```

### **❓ Erro de dependências?**
```bash
# Reconfigurar ambiente
./scripts/setup_environment.sh
source ~/.bashrc
```

### **❓ Erro AWS?**
```bash
# Testar credenciais
aws sts get-caller-identity
aws configure list
```

### **❓ Erro Python?**
```bash
# Testar imports
cd /home/ec2-user/web-scraping-telegram
python3 -c "import sys; sys.path.append('./src'); print('OK')"
```

---

## 🚀 **Próximos Passos**

1. **Agora:** Executar setup e testes na VM
2. **Breve:** Aguardar permissões Kinesis/OpenSearch
3. **Futuro:** Ativar modo produção completo

**🎯 Objetivo:** Sistema TelegramScrap 24/7 com pipeline streaming Telegram → Kinesis → Lambda → Elasticsearch → Kibana**