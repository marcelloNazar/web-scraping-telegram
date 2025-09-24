#!/usr/bin/env python3
"""
Configuration Loader para TelegramScrap
Carrega configurações de diferentes fontes (arquivos, variáveis de ambiente, etc.)
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class TelegramConfig:
    """Configurações do Telegram"""
    api_id: str
    api_hash: str
    phone: str
    username: str
    session_file: str = "telegram_session"

@dataclass
class AWSConfig:
    """Configurações AWS"""
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str = "us-east-1"
    kinesis_stream: str = "telegram-messages"
    elasticsearch_domain: str = "telegramscrap-search"

@dataclass
class ScrapingConfig:
    """Configurações de scraping"""
    message_limit: int = 1000
    delay_between_groups: int = 60
    max_execution_time: int = 21600  # 6 horas
    backup_interval: int = 1000
    output_format: str = "parquet"  # parquet ou excel

@dataclass
class SheetsConfig:
    """Configurações Google Sheets"""
    sheet_url: Optional[str] = None
    cache_duration: int = 300  # 5 minutos

class ConfigLoader:
    """Carregador central de configurações"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Inicializa carregador de configurações

        Args:
            config_dir: Diretório de configurações (padrão: ./config)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Detectar diretório do projeto
            current_dir = Path(__file__).parent.parent.parent
            self.config_dir = current_dir / "config"

        self.telegram_config = None
        self.aws_config = None
        self.scraping_config = None
        self.sheets_config = None

        # Carregar configurações
        self._load_all_configs()

    def _load_all_configs(self):
        """Carrega todas as configurações"""
        try:
            self.telegram_config = self._load_telegram_config()
            self.aws_config = self._load_aws_config()
            self.scraping_config = self._load_scraping_config()
            self.sheets_config = self._load_sheets_config()

            print("✅ Configurações carregadas com sucesso")

        except Exception as e:
            print(f"⚠️ Erro ao carregar configurações: {e}")
            print("🔄 Usando configurações padrão")
            self._load_default_configs()

    def _load_telegram_config(self) -> TelegramConfig:
        """Carrega configurações do Telegram"""
        # Tentar carregar do arquivo Python
        try:
            sys.path.insert(0, str(self.config_dir))
            import telegram_credentials as telegram_creds

            return TelegramConfig(
                api_id=telegram_creds.api_id,
                api_hash=telegram_creds.api_hash,
                phone=telegram_creds.phone,
                username=telegram_creds.username
            )

        except ImportError:
            print("⚠️ Arquivo telegram_credentials.py não encontrado")

        # Tentar variáveis de ambiente
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        phone = os.getenv('TELEGRAM_PHONE')
        username = os.getenv('TELEGRAM_USERNAME')

        if all([api_id, api_hash, phone, username]):
            return TelegramConfig(
                api_id=api_id,
                api_hash=api_hash,
                phone=phone,
                username=username
            )

        # Configuração padrão (vazia)
        print("❌ Configurações do Telegram não encontradas")
        return TelegramConfig(
            api_id="",
            api_hash="",
            phone="",
            username=""
        )

    def _load_aws_config(self) -> AWSConfig:
        """Carrega configurações AWS"""
        config = AWSConfig()

        # Tentar arquivo YAML
        aws_file = self.config_dir / "aws_config.yaml"
        if aws_file.exists():
            try:
                with open(aws_file, 'r') as f:
                    aws_data = yaml.safe_load(f)

                config.access_key_id = aws_data.get('access_key_id')
                config.secret_access_key = aws_data.get('secret_access_key')
                config.region = aws_data.get('region', 'us-east-1')
                config.kinesis_stream = aws_data.get('kinesis_stream', 'telegram-messages')
                config.elasticsearch_domain = aws_data.get('elasticsearch_domain', 'telegram-analytics')

            except Exception as e:
                print(f"⚠️ Erro ao carregar aws_config.yaml: {e}")

        # Tentar variáveis de ambiente (sobrescrevem arquivo)
        config.access_key_id = os.getenv('AWS_ACCESS_KEY_ID', config.access_key_id)
        config.secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', config.secret_access_key)
        config.region = os.getenv('AWS_DEFAULT_REGION', config.region)
        config.kinesis_stream = os.getenv('KINESIS_STREAM_NAME', config.kinesis_stream)
        config.elasticsearch_domain = os.getenv('OPENSEARCH_DOMAIN', os.getenv('ELASTICSEARCH_DOMAIN', config.elasticsearch_domain))

        return config

    def _load_scraping_config(self) -> ScrapingConfig:
        """Carrega configurações de scraping"""
        config = ScrapingConfig()

        # Tentar arquivo JSON
        scraping_file = self.config_dir / "scraping_config.json"
        if scraping_file.exists():
            try:
                with open(scraping_file, 'r') as f:
                    scraping_data = json.load(f)

                config.message_limit = scraping_data.get('message_limit', 1000)
                config.delay_between_groups = scraping_data.get('delay_between_groups', 60)
                config.max_execution_time = scraping_data.get('max_execution_time', 21600)
                config.backup_interval = scraping_data.get('backup_interval', 1000)
                config.output_format = scraping_data.get('output_format', 'parquet')

            except Exception as e:
                print(f"⚠️ Erro ao carregar scraping_config.json: {e}")

        # Tentar variáveis de ambiente
        config.message_limit = int(os.getenv('SCRAPING_MESSAGE_LIMIT', config.message_limit))
        config.delay_between_groups = int(os.getenv('SCRAPING_DELAY', config.delay_between_groups))
        config.max_execution_time = int(os.getenv('SCRAPING_MAX_TIME', config.max_execution_time))
        config.backup_interval = int(os.getenv('SCRAPING_BACKUP_INTERVAL', config.backup_interval))
        config.output_format = os.getenv('SCRAPING_OUTPUT_FORMAT', config.output_format)

        return config

    def _load_sheets_config(self) -> SheetsConfig:
        """Carrega configurações Google Sheets"""
        config = SheetsConfig()

        # Tentar arquivo de configuração
        sheets_file = self.config_dir / "sheets_config.json"
        if sheets_file.exists():
            try:
                with open(sheets_file, 'r') as f:
                    sheets_data = json.load(f)

                config.sheet_url = sheets_data.get('sheet_url')
                config.cache_duration = sheets_data.get('cache_duration', 300)

            except Exception as e:
                print(f"⚠️ Erro ao carregar sheets_config.json: {e}")

        # Tentar variáveis de ambiente
        config.sheet_url = os.getenv('GOOGLE_SHEETS_URL', config.sheet_url)
        config.cache_duration = int(os.getenv('SHEETS_CACHE_DURATION', config.cache_duration))

        return config

    def _load_default_configs(self):
        """Carrega configurações padrão"""
        self.telegram_config = TelegramConfig("", "", "", "")
        self.aws_config = AWSConfig()
        self.scraping_config = ScrapingConfig()
        self.sheets_config = SheetsConfig()

    def get_telegram_credentials(self) -> Dict[str, str]:
        """Retorna credenciais do Telegram como dict"""
        return {
            'api_id': self.telegram_config.api_id,
            'api_hash': self.telegram_config.api_hash,
            'phone': self.telegram_config.phone,
            'username': self.telegram_config.username
        }

    def get_aws_credentials(self) -> Dict[str, Optional[str]]:
        """Retorna credenciais AWS como dict"""
        return {
            'aws_access_key_id': self.aws_config.access_key_id,
            'aws_secret_access_key': self.aws_config.secret_access_key,
            'region_name': self.aws_config.region
        }

    def create_aws_config_file(self):
        """Cria arquivo de configuração AWS de exemplo"""
        aws_config_example = {
            'access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
            'secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY',
            'region': 'us-east-1',
            'kinesis_stream': 'telegram-messages',
            'elasticsearch_domain': 'telegram-analytics'
        }

        aws_file = self.config_dir / "aws_config.yaml.example"
        self.config_dir.mkdir(exist_ok=True)

        with open(aws_file, 'w') as f:
            yaml.dump(aws_config_example, f, default_flow_style=False)

        print(f"✅ Arquivo de exemplo criado: {aws_file}")
        print("📝 Renomeie para 'aws_config.yaml' e configure suas credenciais")

    def create_scraping_config_file(self):
        """Cria arquivo de configuração de scraping de exemplo"""
        scraping_config_example = {
            'message_limit': 1000,
            'delay_between_groups': 60,
            'max_execution_time': 21600,
            'backup_interval': 1000,
            'output_format': 'parquet'
        }

        scraping_file = self.config_dir / "scraping_config.json.example"
        self.config_dir.mkdir(exist_ok=True)

        with open(scraping_file, 'w') as f:
            json.dump(scraping_config_example, f, indent=2)

        print(f"✅ Arquivo de exemplo criado: {scraping_file}")
        print("📝 Renomeie para 'scraping_config.json' e ajuste conforme necessário")

    def create_sheets_config_file(self):
        """Cria arquivo de configuração Google Sheets de exemplo"""
        sheets_config_example = {
            'sheet_url': 'https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv&gid=0',
            'cache_duration': 300
        }

        sheets_file = self.config_dir / "sheets_config.json.example"
        self.config_dir.mkdir(exist_ok=True)

        with open(sheets_file, 'w') as f:
            json.dump(sheets_config_example, f, indent=2)

        print(f"✅ Arquivo de exemplo criado: {sheets_file}")
        print("📝 Renomeie para 'sheets_config.json' e configure a URL da sua planilha")

    def validate_config(self) -> Dict[str, bool]:
        """Valida todas as configurações"""
        validation = {
            'telegram': bool(
                self.telegram_config.api_id and
                self.telegram_config.api_hash and
                self.telegram_config.phone and
                self.telegram_config.username
            ),
            'aws': bool(
                self.aws_config.access_key_id and
                self.aws_config.secret_access_key
            ) or self._check_aws_role(),
            'scraping': True,  # Sempre válido (tem padrões)
            'sheets': bool(self.sheets_config.sheet_url)
        }

        return validation

    def _check_aws_role(self) -> bool:
        """Verifica se tem IAM role configurada"""
        try:
            import boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            return credentials is not None
        except Exception:
            return False

    def print_status(self):
        """Imprime status das configurações"""
        validation = self.validate_config()

        print("\n📋 Status das Configurações:")
        print(f"  🔑 Telegram: {'✅' if validation['telegram'] else '❌'}")
        print(f"  ☁️  AWS: {'✅' if validation['aws'] else '❌'}")
        print(f"  🔧 Scraping: {'✅' if validation['scraping'] else '❌'}")
        print(f"  📊 Google Sheets: {'✅' if validation['sheets'] else '❌'}")

        if not validation['telegram']:
            print("  ⚠️  Configure telegram_credentials.py ou variáveis de ambiente")
        if not validation['aws']:
            print("  ⚠️  Configure credenciais AWS ou IAM role")
        if not validation['sheets']:
            print("  ⚠️  Configure URL da planilha Google Sheets")


# Função de conveniência
def load_config(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Carrega configurações com diretório personalizado

    Args:
        config_dir: Diretório de configurações

    Returns:
        ConfigLoader configurado
    """
    return ConfigLoader(config_dir)


# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade
    print("🧪 Testando ConfigLoader...")

    config = ConfigLoader()
    config.print_status()

    # Criar arquivos de exemplo se não existirem
    print("\n📁 Criando arquivos de exemplo...")
    config.create_aws_config_file()
    config.create_scraping_config_file()
    config.create_sheets_config_file()

    print(f"\n📂 Diretório de configurações: {config.config_dir}")
    print("✅ ConfigLoader testado com sucesso!")