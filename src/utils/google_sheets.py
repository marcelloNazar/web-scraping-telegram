#!/usr/bin/env python3
"""
Google Sheets Loader para TelegramScrap
Carrega grupos da planilha Google Sheets automaticamente
"""

import pandas as pd
import requests
from io import StringIO
import time
from typing import List, Dict, Optional

class GoogleSheetsLoader:
    """Carrega grupos da planilha Google Sheets automaticamente"""

    def __init__(self, sheet_url: Optional[str] = None):
        """
        Inicializa o loader

        Args:
            sheet_url: URL pública da planilha (formato CSV)
                      Formato: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
        """
        # URL padrão da planilha (substitua pela URL real da sua planilha)
        self.sheet_url = sheet_url or "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv&gid=0"
        self.cache_duration = 300  # Cache por 5 minutos
        self._cached_groups = None
        self._cache_time = 0

    def load_groups(self, use_cache: bool = True) -> List[Dict]:
        """
        Carrega lista de grupos da planilha Google Sheets

        Args:
            use_cache: Se deve usar cache para evitar requests desnecessários

        Returns:
            List[Dict] com informações dos grupos:
            [
                {
                    'username': '@canal',
                    'spectrum': 'left/right/center',
                    'stance': 'progressive/conservative',
                    'identity': 'political/media/...',
                    'active': True/False
                },
                ...
            ]
        """

        # Verificar cache
        if use_cache and self._is_cache_valid():
            print(f"✅ Usando cache: {len(self._cached_groups)} grupos")
            return self._cached_groups

        try:
            print("📊 Carregando grupos da planilha Google Sheets...")

            # Baixar CSV da planilha
            response = requests.get(self.sheet_url, timeout=30)
            response.raise_for_status()

            # Processar CSV
            df = pd.read_csv(StringIO(response.text))

            # Limpar e processar dados
            groups = self._process_dataframe(df)

            # Atualizar cache
            self._cached_groups = groups
            self._cache_time = time.time()

            print(f"✅ Carregados {len(groups)} grupos da planilha")
            return groups

        except Exception as e:
            print(f"❌ Erro ao carregar planilha: {e}")
            print("🔄 Usando grupos fallback...")
            return self._get_fallback_groups()

    def _process_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Processa DataFrame da planilha e retorna lista de grupos"""
        groups = []

        for _, row in df.iterrows():
            try:
                # Extrair username e limpar
                username = str(row.get('To Scrape', '')).replace("'", "").strip()
                if not username or username.lower() in ['nan', 'none', '']:
                    continue

                # Garantir que username começa com @
                if not username.startswith('@'):
                    username = f"@{username}"

                # Extrair outras informações
                group_info = {
                    'username': username,
                    'spectrum': str(row.get('Spectrum', '')).lower().strip(),
                    'stance': str(row.get('Stance', '')).lower().strip(),
                    'identity': str(row.get('Identity', '')).lower().strip(),
                    'active': True  # Por padrão, todos os grupos são ativos
                }

                # Filtrar grupos inválidos
                if self._is_valid_group(group_info):
                    groups.append(group_info)

            except Exception as e:
                print(f"⚠️ Erro ao processar linha: {e}")
                continue

        return groups

    def _is_valid_group(self, group: Dict) -> bool:
        """Valida se um grupo é válido"""
        username = group.get('username', '')

        # Verificações básicas
        if not username or len(username) < 2:
            return False

        # Filtrar usernames inválidos
        invalid_patterns = ['nan', 'none', 'null', 'undefined', '@nan', '@none']
        if username.lower() in invalid_patterns:
            return False

        return True

    def _is_cache_valid(self) -> bool:
        """Verifica se o cache ainda é válido"""
        if not self._cached_groups:
            return False
        return (time.time() - self._cache_time) < self.cache_duration

    def _get_fallback_groups(self) -> List[Dict]:
        """Lista de grupos fallback caso a planilha não funcione"""
        return [
            {
                'username': '@LulanoTelegram',
                'spectrum': 'left',
                'stance': 'progressive',
                'identity': 'political',
                'active': True
            },
            {
                'username': '@jairbolsonarobrasil',
                'spectrum': 'right',
                'stance': 'conservative',
                'identity': 'political',
                'active': True
            }
        ]

    def get_groups_by_spectrum(self, spectrum: str) -> List[Dict]:
        """
        Filtra grupos por espectro político

        Args:
            spectrum: 'left', 'right', 'center'

        Returns:
            Lista filtrada de grupos
        """
        groups = self.load_groups()
        return [g for g in groups if g.get('spectrum', '').lower() == spectrum.lower()]

    def get_active_groups(self) -> List[Dict]:
        """Retorna apenas grupos marcados como ativos"""
        groups = self.load_groups()
        return [g for g in groups if g.get('active', True)]

    def update_sheet_url(self, new_url: str):
        """Atualiza URL da planilha e limpa cache"""
        self.sheet_url = new_url
        self._cached_groups = None
        self._cache_time = 0

    def get_stats(self) -> Dict:
        """Retorna estatísticas dos grupos carregados"""
        groups = self.load_groups()

        stats = {
            'total': len(groups),
            'active': len([g for g in groups if g.get('active', True)]),
            'by_spectrum': {},
            'by_stance': {},
            'by_identity': {}
        }

        for group in groups:
            # Contar por espectro
            spectrum = group.get('spectrum', 'unknown')
            stats['by_spectrum'][spectrum] = stats['by_spectrum'].get(spectrum, 0) + 1

            # Contar por stance
            stance = group.get('stance', 'unknown')
            stats['by_stance'][stance] = stats['by_stance'].get(stance, 0) + 1

            # Contar por identity
            identity = group.get('identity', 'unknown')
            stats['by_identity'][identity] = stats['by_identity'].get(identity, 0) + 1

        return stats


# Função de conveniência para uso direto
def load_telegram_groups(sheet_url: Optional[str] = None) -> List[Dict]:
    """
    Função simples para carregar grupos

    Args:
        sheet_url: URL da planilha (opcional)

    Returns:
        Lista de grupos
    """
    loader = GoogleSheetsLoader(sheet_url)
    return loader.load_groups()


# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade
    loader = GoogleSheetsLoader()

    print("🧪 Testando GoogleSheetsLoader...")
    groups = loader.load_groups()

    print(f"📊 Total de grupos: {len(groups)}")

    # Mostrar estatísticas
    stats = loader.get_stats()
    print(f"📈 Estatísticas: {stats}")

    # Mostrar primeiros 5 grupos
    print("📋 Primeiros grupos:")
    for i, group in enumerate(groups[:5]):
        print(f"  {i+1}. {group['username']} ({group.get('spectrum', 'N/A')})")