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

    def _apply_range_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica filtro de range de linhas baseado na configuração SHEETS_RANGE"""
        try:
            # Obter configuração de range
            from .config_loader import load_config
            config = load_config()
            sheets_config = config.get_sheets_config()
            sheets_range = sheets_config.get('sheets_range')
            
            if not sheets_range:
                # Sem filtro configurado, retorna DataFrame completo
                return df
            
            # Parse do range no formato "linha_inicial:linha_final"
            if ':' in sheets_range:
                range_parts = sheets_range.split(':')
                if len(range_parts) == 2:
                    try:
                        start_line = int(range_parts[0]) - 1  # Converter para índice 0-based
                        end_line = int(range_parts[1])  # End é exclusivo no slicing
                        
                        # Validar limites
                        start_line = max(0, start_line)
                        end_line = min(len(df), end_line)
                        
                        if start_line < end_line:
                            print(f"📍 Aplicando range: linhas {start_line+1} a {end_line} (de {len(df)} total)")
                            return df.iloc[start_line:end_line]
                        else:
                            print(f"⚠️ Range inválido: {sheets_range}, usando DataFrame completo")
                            return df
                            
                    except ValueError as e:
                        print(f"⚠️ Erro ao parsear range '{sheets_range}': {e}")
                        return df
                else:
                    print(f"⚠️ Formato de range inválido: '{sheets_range}' (use 'inicio:fim')")
                    return df
            else:
                print(f"⚠️ Formato de range inválido: '{sheets_range}' (use 'inicio:fim')")
                return df
                
        except Exception as e:
            print(f"⚠️ Erro ao aplicar filtro de range: {e}")
            return df

    def _process_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Processa DataFrame da planilha e retorna lista de grupos"""
        groups = []

        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📊 Colunas encontradas: {list(df.columns)}")

        # Aplicar filtro de range se configurado
        df_filtered = self._apply_range_filter(df)
        
        print(f"📍 Após filtro de range: {df_filtered.shape[0]} linhas")

        # Usar nomes de colunas reais encontrados:
        # 'To Scrape', 'Url', 'Group', 'Project', 'Country', 'Format', 'Spectrum', 'Stance', 'Identity', 'Basis', 'Territory', 'Name', 'Description', 'Users', 'To Categorize', 'Chip', '2025-07'

        for index, row in df_filtered.iterrows():
            try:
                # Filtrar grupos baseado na configuração de chip (CHIP_ID)
                chip = str(row.get('Chip', '')).strip()
                
                # Obter filtro de chip das configurações
                from .config_loader import load_config
                config = load_config()
                sheets_config = config.get_sheets_config()
                chip_filter = sheets_config.get('chip_filter', '02')  # Default para chip 2
                
                # Verificar se o chip corresponde ao filtro configurado
                if chip not in [chip_filter, chip_filter.zfill(2), chip_filter.lstrip('0')]:
                    continue

                # Extrair username do campo 'Group'
                username = str(row.get('Group', '')).strip()
                if not username:
                    continue

                # Limpar username (remover aspas se houver)
                username = username.replace("'", "").replace('"', "").strip()

                # Garantir que começa com @
                if not username.startswith('@'):
                    if username and not username.lower() in ['nan', 'none', '']:
                        username = f"@{username}"
                    else:
                        continue

                # Extrair outras informações usando os nomes de coluna reais
                url = str(row.get('Url', '')).strip()
                project = str(row.get('Project', 'Pol')).strip()
                country = str(row.get('Country', 'Brasil')).strip()
                channel_format = str(row.get('Format', '')).strip()  # News, Debate, etc
                spectrum = str(row.get('Spectrum', '')).strip()  # Right, Left, General
                stance = str(row.get('Stance', '')).strip()  # Conservative, Progressive
                identity = str(row.get('Identity', '')).strip()  # Red Pill, Religious, etc
                basis = str(row.get('Basis', '')).strip()  # Bolsonarista, Lulista/Petista, None
                territory = str(row.get('Territory', '')).strip()  # National, State-level
                name = str(row.get('Name', '')).strip()
                description = str(row.get('Description', '')).strip()

                # Processar usuários/membros
                users_str = str(row.get('Users', '0')).strip()
                try:
                    members = int(users_str.replace('.', '').replace(',', '').replace(' ', '')) if users_str and users_str not in ['-', 'nan', ''] else 0
                except:
                    members = 0

                # Processar views da última coluna
                views_str = str(row.get('2025-07', '0')).strip()
                try:
                    views = int(views_str.replace('.', '').replace(',', '').replace(' ', '')) if views_str and views_str not in ['-', 'nan', ''] else 0
                except:
                    views = 0

                # Criar info do grupo
                group_info = {
                    'username': username,
                    'url': url,
                    'project': project,
                    'country': country,
                    'format': channel_format,
                    'spectrum': spectrum,
                    'stance': stance,
                    'identity': identity,
                    'basis': basis,
                    'territory': territory,
                    'name': name,
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

        # Por formato/tipo de canal
        formats = {}
        for group in groups:
            channel_format = group.get('format', 'Unknown')
            formats[channel_format] = formats.get(channel_format, 0) + 1
        print(f"Por formato: {formats}")

        # Por stance
        stances = {}
        for group in groups:
            stance = group.get('stance', 'Unknown')
            stances[stance] = stances.get(stance, 0) + 1
        print(f"Por stance: {stances}")

        # Por basis (afiliação política)
        bases = {}
        for group in groups:
            basis = group.get('basis', 'None')
            bases[basis] = bases.get(basis, 0) + 1
        print(f"Por basis: {bases}")

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
            basis = group.get('basis', 'None')
            print(f"  {i+1}. {group['username']} ({members:,} membros - {spectrum}/{basis})")

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

        # Estatísticas por stance
        print(f"\n📍 Distribuição por stance:")
        for stance in ['Conservative', 'Progressive', 'General']:
            stance_groups = [g for g in groups if g.get('stance') == stance]
            stance_members = sum(g.get('members', 0) for g in stance_groups)
            print(f"  {stance}: {len(stance_groups)} grupos, {stance_members:,} membros")


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