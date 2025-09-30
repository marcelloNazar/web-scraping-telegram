#!/usr/bin/env python3
"""
Google Sheets Loader para TelegramScrap
Carrega grupos da planilha Google Sheets automaticamente
"""

import pandas as pd
import requests
from io import StringIO
import time
import ast
import re
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

    def parse_categorization_column(self, categorization_text: str) -> tuple:
        """
        Parse da coluna 'To Categorize' do Google Sheets
        
        Input: '@BolsonaroBR': ['Pol', 'Brasil', 'Debate', 'Right', 'Conservative', 'General', 'Bolsonarista', 'National']
        Output: (username, dict com categorizações estruturadas)
        """
        try:
            # Limpar string de entrada
            categorization_text = categorization_text.strip()
            
            if not categorization_text or categorization_text.lower() in ['nan', 'none', '']:
                return None, None
            
            # Extrair username e lista de categorias
            if ':' in categorization_text:
                username_part, categories_part = categorization_text.split(':', 1)
                username = username_part.strip().strip("'\"")
                
                # Remove @ se presente no username
                if username.startswith('@'):
                    username = username[1:]
                
                # Parse da lista de categorias
                try:
                    categories_list = ast.literal_eval(categories_part.strip())
                    
                    if not isinstance(categories_list, list):
                        print(f"⚠️ Categorias não são uma lista para {username}: {categories_part}")
                        return None, None
                        
                except (ValueError, SyntaxError) as e:
                    print(f"⚠️ Erro ao fazer parse de lista para {username}: {e}")
                    return None, None
                
                # Mapear para estrutura padronizada (8 campos)
                categorization = {
                    'group_project': categories_list[0] if len(categories_list) > 0 else 'OTHER',
                    'group_country': categories_list[1] if len(categories_list) > 1 else 'Unknown',
                    'group_format': categories_list[2] if len(categories_list) > 2 else 'General',
                    'group_spectrum': categories_list[3] if len(categories_list) > 3 else 'General',
                    'group_stance': categories_list[4] if len(categories_list) > 4 else 'General',
                    'group_identity': categories_list[5] if len(categories_list) > 5 else 'General',
                    'group_basis': categories_list[6] if len(categories_list) > 6 else 'None',
                    'group_territory': categories_list[7] if len(categories_list) > 7 else 'Unknown'
                }
                
                return username, categorization
            else:
                print(f"⚠️ Formato inválido para categorização (sem ':'): {categorization_text}")
                return None, None
                
        except Exception as e:
            print(f"❌ Erro ao fazer parse de categorização: {e}")
            return None, None

    def load_groups_with_categorizations(self, include_uncategorized: bool = True) -> Dict[str, Dict]:
        """
        Carrega grupos com categorizações completas do Google Sheets
        
        Args:
            include_uncategorized: Se deve incluir grupos sem categorização na coluna "To Categorize"
            
        Returns:
            Dict com username como chave e dados completos como valor
        """
        try:
            print("📊 Carregando grupos com categorizações do Google Sheets...")
            
            # Carregar dados da planilha
            response = requests.get(self.sheet_url, timeout=30)
            response.raise_for_status()
            
            # Processar CSV
            df = pd.read_csv(StringIO(response.text))
            
            # Aplicar filtro de range se configurado
            df_filtered = self._apply_range_filter(df)
            
            print(f"📊 DataFrame filtrado shape: {df_filtered.shape}")
            print(f"📊 Colunas disponíveis: {list(df_filtered.columns)}")
            
            groups_categorized = {}
            grupos_com_categorization = 0
            grupos_sem_categorization = 0
            
            for index, row in df_filtered.iterrows():
                try:
                    # Filtrar por chip (mesmo filtro da função original)
                    chip = str(row.get('Chip', '')).strip()
                    
                    # Obter filtro de chip das configurações
                    from .config_loader import load_config
                    config = load_config()
                    sheets_config = config.get_sheets_config()
                    chip_filter = sheets_config.get('chip_filter', '02')
                    
                    # Verificar se o chip corresponde ao filtro configurado
                    if chip not in [chip_filter, chip_filter.zfill(2), chip_filter.lstrip('0')]:
                        continue
                    
                    # Extrair username básico
                    username = str(row.get('Group', '')).strip()
                    if not username:
                        continue
                    
                    # Limpar username
                    username = username.replace("'", "").replace('"', "").strip()
                    
                    # Garantir que começa com @
                    if not username.startswith('@'):
                        if username and not username.lower() in ['nan', 'none', '']:
                            username = f"@{username}"
                        else:
                            continue
                    
                    # Tentar fazer parse da coluna "To Categorize"
                    categorization_text = str(row.get('To Categorize', '')).strip()
                    parsed_username, categorization = self.parse_categorization_column(categorization_text)
                    
                    # Se temos categorização, usar ela
                    if parsed_username and categorization:
                        grupos_com_categorization += 1
                        
                        # Criar estrutura completa do grupo
                        group_data = {
                            'username': username,
                            'url': str(row.get('Url', '')).strip(),
                            'name': str(row.get('Name', '')).strip(),
                            'description': str(row.get('Description', '')).strip(),
                            'users': self._safe_int_conversion(str(row.get('Users', '0')).strip()),
                            'chip': chip,
                            
                            # Categorizações originais da planilha (para compatibilidade)
                            'project': str(row.get('Project', 'Pol')).strip(),
                            'country': str(row.get('Country', 'Brasil')).strip(),
                            'format': str(row.get('Format', '')).strip(),
                            'spectrum': str(row.get('Spectrum', '')).strip(),
                            'stance': str(row.get('Stance', '')).strip(),
                            'identity': str(row.get('Identity', '')).strip(),
                            'basis': str(row.get('Basis', '')).strip(),
                            'territory': str(row.get('Territory', '')).strip(),
                            
                            # NOVAS categorizações estruturadas da coluna "To Categorize"
                            **categorization
                        }
                        
                        groups_categorized[username] = group_data
                        
                    elif include_uncategorized:
                        # Grupo sem categorização na coluna "To Categorize"
                        grupos_sem_categorization += 1
                        
                        # Usar categorizações das colunas individuais como fallback
                        fallback_categorization = {
                            'group_project': str(row.get('Project', 'OTHER')).strip(),
                            'group_country': str(row.get('Country', 'Unknown')).strip(),
                            'group_format': str(row.get('Format', 'General')).strip(),
                            'group_spectrum': str(row.get('Spectrum', 'General')).strip(),
                            'group_stance': str(row.get('Stance', 'General')).strip(),
                            'group_identity': str(row.get('Identity', 'General')).strip(),
                            'group_basis': str(row.get('Basis', 'None')).strip(),
                            'group_territory': str(row.get('Territory', 'Unknown')).strip()
                        }
                        
                        group_data = {
                            'username': username,
                            'url': str(row.get('Url', '')).strip(),
                            'name': str(row.get('Name', '')).strip(),
                            'description': str(row.get('Description', '')).strip(),
                            'users': self._safe_int_conversion(str(row.get('Users', '0')).strip()),
                            'chip': chip,
                            
                            # Categorizações originais da planilha
                            'project': str(row.get('Project', 'Pol')).strip(),
                            'country': str(row.get('Country', 'Brasil')).strip(),
                            'format': str(row.get('Format', '')).strip(),
                            'spectrum': str(row.get('Spectrum', '')).strip(),
                            'stance': str(row.get('Stance', '')).strip(),
                            'identity': str(row.get('Identity', '')).strip(),
                            'basis': str(row.get('Basis', '')).strip(),
                            'territory': str(row.get('Territory', '')).strip(),
                            
                            # Categorizações estruturadas (fallback das colunas individuais)
                            **fallback_categorization
                        }
                        
                        groups_categorized[username] = group_data
                    
                except Exception as e:
                    print(f"⚠️ Erro ao processar linha {index}: {e}")
                    continue
            
            print(f"✅ Carregadas categorizações:")
            print(f"   📊 {grupos_com_categorization} grupos COM categorização estruturada")
            print(f"   📊 {grupos_sem_categorization} grupos com categorização fallback")
            print(f"   📊 {len(groups_categorized)} grupos TOTAL processados")
            
            return groups_categorized
            
        except Exception as e:
            print(f"❌ Erro ao carregar categorizações: {e}")
            return {}

    def _safe_int_conversion(self, value_str: str) -> int:
        """Converte string para int de forma segura"""
        try:
            return int(value_str.replace('.', '').replace(',', '').replace(' ', '')) if value_str and value_str not in ['-', 'nan', ''] else 0
        except:
            return 0

    def test_categorizations(self, limit: int = 5):
        """
        Testa o sistema de categorizações
        """
        print("🧪 TESTANDO SISTEMA DE CATEGORIZAÇÕES:")
        print("="*60)
        
        groups_categorizations = self.load_groups_with_categorizations()
        
        print(f"\n📊 Total de grupos carregados: {len(groups_categorizations)}")
        
        # Mostrar primeiros grupos como exemplo
        print(f"\n📋 Exemplos de categorizações (primeiros {limit}):")
        for i, (username, data) in enumerate(list(groups_categorizations.items())[:limit]):
            print(f"\n{i+1}. Grupo: {username}")
            print(f"   Nome: {data.get('name', 'N/A')}")
            print(f"   Usuários: {data.get('users', 0):,}")
            print(f"   📊 CATEGORIZAÇÕES:")
            print(f"      Project: {data.get('group_project', 'N/A')}")
            print(f"      Country: {data.get('group_country', 'N/A')}")
            print(f"      Format: {data.get('group_format', 'N/A')}")
            print(f"      Spectrum: {data.get('group_spectrum', 'N/A')}")
            print(f"      Stance: {data.get('group_stance', 'N/A')}")
            print(f"      Identity: {data.get('group_identity', 'N/A')}")
            print(f"      Basis: {data.get('group_basis', 'N/A')}")
            print(f"      Territory: {data.get('group_territory', 'N/A')}")
            print("-" * 40)
        
        # Estatísticas de categorização
        print(f"\n📈 ESTATÍSTICAS DE CATEGORIZAÇÃO:")
        
        # Por project
        projects = {}
        for data in groups_categorizations.values():
            project = data.get('group_project', 'Unknown')
            projects[project] = projects.get(project, 0) + 1
        print(f"   Por Project: {projects}")
        
        # Por spectrum
        spectrums = {}
        for data in groups_categorizations.values():
            spectrum = data.get('group_spectrum', 'Unknown')
            spectrums[spectrum] = spectrums.get(spectrum, 0) + 1
        print(f"   Por Spectrum: {spectrums}")
        
        # Por stance
        stances = {}
        for data in groups_categorizations.values():
            stance = data.get('group_stance', 'Unknown')
            stances[stance] = stances.get(stance, 0) + 1
        print(f"   Por Stance: {stances}")
        
        return groups_categorizations


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


def load_groups_with_categorizations(sheet_url: Optional[str] = None, include_uncategorized: bool = True) -> Dict[str, Dict]:
    """
    Função de conveniência para carregar grupos com categorizações

    Args:
        sheet_url: URL da planilha (opcional)
        include_uncategorized: Se deve incluir grupos sem categorização estruturada

    Returns:
        Dict com username como chave e dados completos (incluindo categorizações) como valor
    """
    loader = GoogleSheetsLoader(sheet_url)
    return loader.load_groups_with_categorizations(include_uncategorized)


def get_group_categorization(group_username: str, groups_categorizations: Dict[str, Dict]) -> Dict:
    """
    Busca categorização de um grupo específico
    
    Args:
        group_username: Username do grupo (com ou sem @)
        groups_categorizations: Dict de categorizações carregado

    Returns:
        Dict com categorizações do grupo ou fallback padrão
    """
    # Normalizar username
    if not group_username.startswith('@'):
        group_username = f"@{group_username}"
    
    # Tentar buscar com @
    categorization = groups_categorizations.get(group_username)
    
    # Tentar buscar sem @
    if not categorization:
        username_no_at = group_username[1:] if group_username.startswith('@') else group_username
        categorization = groups_categorizations.get(username_no_at)
    
    # Fallback para categorização padrão se não encontrar
    if not categorization:
        categorization = {
            'username': group_username,
            'group_project': 'OTHER',
            'group_country': 'Unknown',
            'group_format': 'General',
            'group_spectrum': 'General',
            'group_stance': 'General',
            'group_identity': 'General',
            'group_basis': 'None',
            'group_territory': 'Unknown'
        }
    
    return categorization


def test_categorization_system(sheet_url: Optional[str] = None, limit: int = 5):
    """
    Função de conveniência para testar o sistema de categorização
    """
    loader = GoogleSheetsLoader(sheet_url)
    return loader.test_categorizations(limit)


# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade original
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

    print("\n" + "="*60)
    
    # Teste da nova funcionalidade de categorização
    print("🧪 Testando novo sistema de categorizações...")
    test_categorization_system(limit=3)