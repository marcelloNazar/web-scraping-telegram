# ===============================================================
# TELEGRAMSCRAP - INTEGRAÇÃO GOOGLE SHEETS → JUPYTER
# ===============================================================
# Código para carregar grupos do Google Sheets no Jupyter Notebook
# Substitui listas hardcoded por dados dinâmicos da planilha

import pandas as pd
import requests
from io import StringIO

# ===============================================================
# CONFIGURAÇÕES GOOGLE SHEETS
# ===============================================================

# URL da planilha (mesma que funciona na EC2)
SHEETS_URL = "https://docs.google.com/spreadsheets/d/1sOnKOz7qqx3bumgNp8-d5_slE3HE3JhGkD8SQjGCAcA/export?format=csv&gid=2025195276"

def load_groups_from_sheets(chip_filter=None, max_groups=None):
    """
    Carregar grupos do Google Sheets para usar no Jupyter

    Args:
        chip_filter (list): Lista de chips para filtrar (ex: ['02', '2'])
        max_groups (int): Máximo de grupos para retornar (None = todos)

    Returns:
        tuple: (groups_data, channels_string)
    """

    print("📊 Carregando grupos da planilha Google Sheets...")

    try:
        # Fazer requisição para Google Sheets
        response = requests.get(SHEETS_URL, timeout=30)
        response.raise_for_status()

        # Converter para DataFrame
        df = pd.read_csv(StringIO(response.text))
        print(f"✅ Planilha carregada: {len(df)} linhas encontradas")

        # Filtrar grupos por chip se especificado
        if chip_filter:
            original_count = len(df)
            df = df[df['Chip'].astype(str).str.strip().isin([str(c) for c in chip_filter])]
            print(f"🔍 Filtro CHIP {chip_filter}: {len(df)} de {original_count} grupos")

        # Processar grupos
        groups_data = []
        for index, row in df.iterrows():
            # Processar username
            username = str(row.get('Group', '')).strip()
            if username and not username.startswith('@'):
                username = f"@{username}"

            # Pular se username inválido
            if not username or username == '@':
                continue

            # Criar dados do grupo
            group_info = {
                'username': username,
                'spectrum': row.get('Spectrum', 'General'),
                'stance': row.get('Stance', 'General'),
                'identity': row.get('Identity', 'General'),
                'basis': row.get('Basis', 'None'),
                'members': int(row.get('Users', 0)) if str(row.get('Users', 0)).isdigit() else 0,
                'name': str(row.get('Name', '')).strip(),
                'chip': str(row.get('Chip', '')).strip(),
                'territory': str(row.get('Territory', 'National')).strip(),
                'active': str(row.get('Active', 'True')).strip().lower() in ['true', '1', 'yes', 'sim']
            }

            groups_data.append(group_info)

        # Aplicar limite se especificado
        if max_groups and max_groups < len(groups_data):
            groups_data = groups_data[:max_groups]
            print(f"🎯 Limitado a primeiros {max_groups} grupos")

        # Criar string channels para compatibilidade com Jupyter existente
        active_usernames = [g['username'] for g in groups_data]
        channels = ", ".join(active_usernames)

        print(f"✅ {len(groups_data)} grupos processados com sucesso")
        print(f"📋 Primeiros grupos: {channels[:100]}...")

        return groups_data, channels

    except Exception as e:
        print(f"❌ Erro carregando planilha: {e}")
        print("🔄 Retornando lista de emergência...")

        # Fallback para grupos de emergência
        emergency_groups = [
            {'username': '@SputnikBrasil', 'spectrum': 'Right', 'stance': 'Conservative'},
            {'username': '@plenonews', 'spectrum': 'Right', 'stance': 'Conservative'},
            {'username': '@mblivre', 'spectrum': 'Right', 'stance': 'Conservative'}
        ]

        emergency_channels = ", ".join([g['username'] for g in emergency_groups])
        return emergency_groups, emergency_channels

def get_chip2_groups(max_groups=20):
    """
    Carregar especificamente grupos do CHIP 2 (valores '02' ou '2')

    Args:
        max_groups (int): Máximo de grupos para teste (padrão: 20)

    Returns:
        tuple: (groups_data, channels_string)
    """
    return load_groups_from_sheets(
        chip_filter=['02', '2'],
        max_groups=max_groups
    )

def get_all_groups():
    """
    Carregar todos os grupos da planilha (sem filtros)

    Returns:
        tuple: (groups_data, channels_string)
    """
    return load_groups_from_sheets()

def print_groups_summary(groups_data):
    """
    Imprimir resumo dos grupos carregados

    Args:
        groups_data (list): Lista de dados dos grupos
    """

    if not groups_data:
        print("❌ Nenhum grupo encontrado")
        return

    print(f"\n📊 RESUMO DOS GRUPOS ({len(groups_data)} total):")
    print("=" * 50)

    # Contadores
    spectrum_count = {}
    stance_count = {}
    total_members = 0

    for group in groups_data:
        # Contar por espectro
        spectrum = group.get('spectrum', 'General')
        spectrum_count[spectrum] = spectrum_count.get(spectrum, 0) + 1

        # Contar por stance
        stance = group.get('stance', 'General')
        stance_count[stance] = stance_count.get(stance, 0) + 1

        # Somar membros
        total_members += group.get('members', 0)

    print(f"👥 Total de membros: {total_members:,}")
    print(f"📈 Média de membros por grupo: {total_members // len(groups_data):,}")

    print("\n🏛️ Por Espectro Político:")
    for spectrum, count in spectrum_count.items():
        percent = (count / len(groups_data)) * 100
        print(f"  {spectrum}: {count} grupos ({percent:.1f}%)")

    print("\n🎯 Por Stance:")
    for stance, count in stance_count.items():
        percent = (count / len(groups_data)) * 100
        print(f"  {stance}: {count} grupos ({percent:.1f}%)")

    print("=" * 50)

# ===============================================================
# CÓDIGO DE EXEMPLO PARA JUPYTER NOTEBOOK
# ===============================================================

def example_jupyter_integration():
    """
    Exemplo de como usar no Jupyter Notebook
    """

    example_code = '''
# ===== ADICIONAR ESTA CÉLULA NO JUPYTER NOTEBOOK =====

# Importar integração Google Sheets
import sys
sys.path.append('.')  # Se o arquivo estiver na mesma pasta
from jupyter_sheets_integration import get_chip2_groups, print_groups_summary

# Carregar grupos do CHIP 2 (primeiros 20 para teste)
print("🔧 Carregando grupos CHIP 2 da planilha...")
groups_data, channels = get_chip2_groups(max_groups=20)

# Imprimir resumo
print_groups_summary(groups_data)

# Usar variável 'channels' no lugar da lista hardcoded
print(f"\\n📱 Variável 'channels' pronta para usar:")
print(f"channels = '{channels[:100]}...'")

# ===== MODIFICAR A CÉLULA DE SCRAPING =====

# ANTES (hardcoded):
# channels = "@SputnikBrasil, @plenonews, @mblivre"

# DEPOIS (dinâmico da planilha):
# channels = channels  # Já carregado acima

print("✅ Integração Google Sheets configurada!")
print("💡 Agora o Jupyter usa os mesmos dados da EC2 AWS")
    '''

    print("📝 CÓDIGO DE EXEMPLO PARA JUPYTER:")
    print("=" * 60)
    print(example_code)
    print("=" * 60)

# ===============================================================
# FUNCIONALIDADES AVANÇADAS
# ===============================================================

def filter_groups_by_criteria(groups_data, **criteria):
    """
    Filtrar grupos por critérios específicos

    Args:
        groups_data (list): Lista de grupos
        **criteria: Critérios de filtro (spectrum='Right', stance='Conservative', etc.)

    Returns:
        list: Grupos filtrados
    """

    filtered = groups_data

    for field, value in criteria.items():
        if isinstance(value, list):
            filtered = [g for g in filtered if g.get(field) in value]
        else:
            filtered = [g for g in filtered if g.get(field) == value]

    return filtered

def create_channels_string(groups_data, max_groups=None):
    """
    Criar string de canais formatada para o Jupyter

    Args:
        groups_data (list): Lista de grupos
        max_groups (int): Máximo de grupos (None = todos)

    Returns:
        str: String formatada para usar no Jupyter
    """

    if max_groups:
        groups_data = groups_data[:max_groups]

    usernames = [g['username'] for g in groups_data]
    return ", ".join(usernames)

def export_groups_for_colab():
    """
    Exportar grupos em formato otimizado para Google Colab

    Returns:
        dict: Dados formatados para Colab
    """

    groups_data, channels = get_chip2_groups()

    return {
        'channels_string': channels,
        'total_groups': len(groups_data),
        'groups_by_spectrum': {},
        'sample_groups': groups_data[:5],  # 5 primeiros para inspeção
        'ready_to_use': True
    }

# ===============================================================
# TESTE E VALIDAÇÃO
# ===============================================================

if __name__ == "__main__":
    print("🧪 Testando integração Google Sheets → Jupyter...")
    print("=" * 60)

    # Testar carregamento CHIP 2
    print("1. 📊 Testando carregamento CHIP 2:")
    groups_data, channels = get_chip2_groups(max_groups=5)
    print_groups_summary(groups_data)

    print("\n2. 🔍 Testando filtros:")
    right_groups = filter_groups_by_criteria(groups_data, spectrum='Right')
    print(f"   Grupos Right: {len(right_groups)}")

    print("\n3. 📱 Testando string channels:")
    test_channels = create_channels_string(groups_data, max_groups=3)
    print(f"   Channels: {test_channels}")

    print("\n4. 📝 Exemplo de integração:")
    example_jupyter_integration()

    print("✅ Teste concluído!")
    print("💡 Arquivo pronto para usar no Jupyter Notebook")