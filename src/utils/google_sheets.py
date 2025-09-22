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
        # URL real da planilha (CHIP 2 com 204 grupos brasileiros)
        self.sheet_url = sheet_url or "https://docs.google.com/spreadsheets/d/1sOnKOz7qqx3bumgNp8-d5_slE3HE3JhGkD8SQjGCAcA/export?format=csv&gid=2025195276"
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

        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📊 Colunas encontradas: {list(df.columns)}")

        # A planilha pode não ter cabeçalhos, vamos usar índices de coluna
        # Baseado na estrutura dos dados fornecidos:
        # Col 0: Username com aspas, Col 1: URL, Col 2: Username limpo, Col 3: Category, etc.

        for index, row in df.iterrows():
            try:
                # Converter row para lista para acessar por índice
                row_values = row.tolist()

                # Verificar se temos colunas suficientes
                if len(row_values) < 16:
                    continue

                # Extrair valores por posição (baseado na estrutura fornecida)
                username_quoted = str(row_values[0]).strip() if len(row_values) > 0 else ''
                url = str(row_values[1]).strip() if len(row_values) > 1 else ''
                username_clean = str(row_values[2]).strip() if len(row_values) > 2 else ''
                category = str(row_values[3]).strip() if len(row_values) > 3 else 'Pol'
                country = str(row_values[4]).strip() if len(row_values) > 4 else 'Brasil'
                channel_type = str(row_values[5]).strip() if len(row_values) > 5 else ''
                spectrum = str(row_values[6]).strip() if len(row_values) > 6 else ''
                orientation = str(row_values[7]).strip() if len(row_values) > 7 else ''
                sub_category = str(row_values[8]).strip() if len(row_values) > 8 else ''
                affiliation = str(row_values[9]).strip() if len(row_values) > 9 else ''
                territory = str(row_values[10]).strip() if len(row_values) > 10 else ''
                description = str(row_values[11]).strip() if len(row_values) > 11 else ''
                # row_values[12] parece ser sempre '-'
                members_str = str(row_values[13]).strip() if len(row_values) > 13 else '0'
                # row_values[14] parece ser metadados
                chip = str(row_values[15]).strip() if len(row_values) > 15 else ''
                views_str = str(row_values[16]).strip() if len(row_values) > 16 else '0'

                # Filtrar apenas grupos do chip 2 ('02')
                if chip != '02':
                    continue

                # Limpar username (remover aspas e espaços)
                username = username_clean.replace("'", "").strip()
                if not username.startswith('@'):
                    continue

                # Processar membros (converter '55.680' para 55680)
                try:
                    members = int(members_str.replace('.', '').replace(',', '').replace(' ', '')) if members_str and members_str != '-' else 0
                except:
                    members = 0

                # Processar views
                try:
                    views = int(views_str.replace('.', '').replace(',', '').replace(' ', '')) if views_str and views_str != '-' else 0
                except:
                    views = 0

                # Criar info do grupo
                group_info = {
                    'username': username,
                    'url': url,
                    'category': category,
                    'country': country,
                    'type': channel_type,
                    'spectrum': spectrum,
                    'orientation': orientation,
                    'sub_category': sub_category,
                    'affiliation': affiliation,
                    'territory': territory,
                    'description': description,
                    'members': members,
                    'chip': chip,
                    'views': views,
                    'active': True
                }

                # Filtrar grupos inválidos
                if self._is_valid_group(group_info):
                    groups.append(group_info)

            except Exception as e:
                print(f"⚠️ Erro ao processar linha {index}: {e}")
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
            {'username': '@SputnikBrasil', 'spectrum': 'Left', 'orientation': 'Progressive', 'members': 55680, 'active': True},
            {'username': '@mblivre', 'spectrum': 'Right', 'orientation': 'Conservative', 'members': 28215, 'active': True},
            {'username': '@plenonews', 'spectrum': 'General', 'orientation': 'General', 'members': 13220, 'active': True}
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

    def print_stats(self):
        """Imprimir estatísticas dos grupos"""
        groups = self.load_groups()

        print(f"\n📊 ESTATÍSTICAS DOS GRUPOS CHIP 2:")
        print(f"Total de grupos: {len(groups)}")

        # Por espectro político
        spectrums = {}
        for group in groups:
            spectrum = group.get('spectrum', 'Unknown')
            spectrums[spectrum] = spectrums.get(spectrum, 0) + 1
        print(f"Por espectro político: {spectrums}")

        # Por tipo de canal
        types = {}
        for group in groups:
            channel_type = group.get('type', 'Unknown')
            types[channel_type] = types.get(channel_type, 0) + 1
        print(f"Por tipo: {types}")

        # Por orientação
        orientations = {}
        for group in groups:
            orientation = group.get('orientation', 'Unknown')
            orientations[orientation] = orientations.get(orientation, 0) + 1
        print(f"Por orientação: {orientations}")

        # Por afiliação política
        affiliations = {}
        for group in groups:
            affiliation = group.get('affiliation', 'None')
            affiliations[affiliation] = affiliations.get(affiliation, 0) + 1
        print(f"Por afiliação: {affiliations}")

        # Por território
        territories = {}
        for group in groups:
            territory = group.get('territory', 'Unknown')
            territories[territory] = territories.get(territory, 0) + 1
        print(f"Por território: {territories}")

        # Primeiros 10 grupos mais populares
        sorted_groups = sorted(groups, key=lambda x: x.get('members', 0), reverse=True)
        print(f"\n📋 Top 10 grupos por membros:")
        for i, group in enumerate(sorted_groups[:10]):
            members = group.get('members', 0)
            spectrum = group.get('spectrum', 'N/A')
            affiliation = group.get('affiliation', 'None')
            print(f"  {i+1}. {group['username']} ({members:,} membros - {spectrum}/{affiliation})")

        # Estatísticas de membros
        total_members = sum(group.get('members', 0) for group in groups)
        avg_members = total_members / len(groups) if groups else 0
        print(f"\n📈 Estatísticas de audiência:")
        print(f"Total de membros: {total_members:,}")
        print(f"Média por grupo: {avg_members:,.0f}")

        # Estatísticas por espectro
        print(f"\n🏛️ Distribuição política:")
        for spectrum in ['Left', 'Right', 'General']:
            spectrum_groups = [g for g in groups if g.get('spectrum') == spectrum]
            spectrum_members = sum(g.get('members', 0) for g in spectrum_groups)
            print(f"  {spectrum}: {len(spectrum_groups)} grupos, {spectrum_members:,} membros")


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