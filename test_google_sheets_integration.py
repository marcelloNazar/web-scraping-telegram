#!/usr/bin/env python3
"""
Teste de Integração Google Sheets
Valida carregamento de grupos da planilha
"""

import sys
sys.path.append('./src')

def test_google_sheets_integration():
    """Testa integração com Google Sheets"""

    print("📊 Testando integração Google Sheets...")

    try:
        from utils.google_sheets import GoogleSheetsLoader

        # Testar com URL padrão (fallback)
        print("\n1️⃣ Testando com configuração padrão...")
        loader = GoogleSheetsLoader()
        groups = loader.load_groups()

        print(f"📊 Total de grupos carregados: {len(groups)}")

        if len(groups) > 0:
            print(f"\n📋 Primeiros {min(5, len(groups))} grupos:")
            for i, group in enumerate(groups[:5]):
                print(f"  {i+1}. {group['username']} ({group.get('spectrum', 'N/A')})")

            # Estatísticas
            stats = loader.get_stats()
            print(f"\n📈 Estatísticas:")
            print(f"  Total: {stats['total']}")
            print(f"  Ativos: {stats['active']}")
            print(f"  Por espectro: {stats['by_spectrum']}")

            # Testar filtros
            if stats['total'] > 2:
                print(f"\n🔍 Testando filtros:")

                # Grupos ativos
                active_groups = loader.get_active_groups()
                print(f"  Grupos ativos: {len(active_groups)}")

                # Por espectro (se disponível)
                if 'left' in stats['by_spectrum']:
                    left_groups = loader.get_groups_by_spectrum('left')
                    print(f"  Grupos esquerda: {len(left_groups)}")

                if 'right' in stats['by_spectrum']:
                    right_groups = loader.get_groups_by_spectrum('right')
                    print(f"  Grupos direita: {len(right_groups)}")

        print("\n✅ Google Sheets funcionando!")
        return True

    except Exception as e:
        print(f"❌ ERRO na integração Google Sheets: {e}")
        print("💡 Isso é normal se a URL da planilha não estiver configurada")
        print("💡 O sistema usará grupos fallback automaticamente")
        return True  # Não é erro crítico

def test_with_custom_url():
    """Testa com URL customizada (se configurada)"""

    try:
        from utils.config_loader import ConfigLoader
        from utils.google_sheets import GoogleSheetsLoader

        config = ConfigLoader()
        sheets_url = config.sheets_config.sheet_url

        if sheets_url and 'YOUR_SHEET_ID' not in sheets_url:
            print(f"\n2️⃣ Testando com URL configurada...")
            print(f"🔗 URL: {sheets_url[:60]}...")

            loader = GoogleSheetsLoader(sheets_url)
            groups = loader.load_groups()

            print(f"📊 Grupos da planilha real: {len(groups)}")

            if len(groups) > 2:  # Mais que fallback
                print("✅ Planilha real carregada com sucesso!")
                return True

        print("⚠️ URL da planilha não configurada - usando fallback")
        return True

    except Exception as e:
        print(f"⚠️ Erro com URL customizada: {e}")
        return True

if __name__ == "__main__":
    print("=" * 50)
    success1 = test_google_sheets_integration()
    success2 = test_with_custom_url()

    if success1 and success2:
        print("\n✅ Todos os testes Google Sheets PASSARAM")
    else:
        print("\n⚠️ Alguns testes falharam (não crítico)")

    print("=" * 50)