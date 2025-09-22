#!/bin/bash
# Script de instalação automática TelegramScrap
yum update -y
yum install -y python3 python3-pip git

# Instalar dependências Python
pip3 install jupyter pandas telethon openpyxl pyarrow boto3

# Criar usuário jupyter
useradd -m jupyter
mkdir -p /home/jupyter/telegramscrap
chown -R jupyter:jupyter /home/jupyter/

# Configurar Jupyter para acesso web
mkdir -p /home/jupyter/.jupyter
cat > /home/jupyter/.jupyter/jupyter_notebook_config.py << 'EOF'
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = 8888
c.NotebookApp.open_browser = False
c.NotebookApp.token = 'telegramscrap2024'
c.NotebookApp.allow_root = True
EOF

# Criar serviço systemd para iniciar automaticamente
cat > /etc/systemd/system/jupyter.service << 'EOF'
[Unit]
Description=Jupyter Notebook
After=network.target

[Service]
Type=simple
User=jupyter
WorkingDirectory=/home/jupyter/telegramscrap
ExecStart=/usr/local/bin/jupyter notebook
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Habilitar e iniciar serviço
systemctl enable jupyter
systemctl start jupyter

echo "✅ TelegramScrap instalação completa!"
echo "🌐 Acesse: http://IP-DA-INSTANCIA:8888"
echo "🔑 Token: telegramscrap2024"
