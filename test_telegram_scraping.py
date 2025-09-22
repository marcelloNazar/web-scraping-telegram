#!/usr/bin/env python3
"""
Teste de Scraping Telegram
Executa scraping real com poucos dados para validar funcionamento
"""

import sys
sys.path.append('./src')

import pandas as pd
from datetime import datetime, timezone, timedelta

def test_telegram_scraping():
    """Executa scraping de teste com poucos dados"""

    print("🧪 Testando scraping Telegram com dados reais...")

    try:
        from utils.config_loader import ConfigLoader
        from utils.google_sheets import GoogleSheetsLoader
        from telethon.sync import TelegramClient

        # Configurações
        config = ConfigLoader()
        telegram_creds = config.get_telegram_credentials()

        # Carregar grupos (limitado para teste)
        try:
            sheets_loader = GoogleSheetsLoader()
            groups_data = sheets_loader.load_groups()
            # Usar só 2 primeiros grupos ativos para teste
            test_groups = [g['username'] for g in groups_data if g.get('active', True)][:2]
            print(f"📊 Grupos da planilha: {len(groups_data)} total, testando {len(test_groups)}")
        except:
            test_groups = ['@LulanoTelegram']
            print(f"📊 Usando grupos fallback: {test_groups}")

        # Configurações de teste (últimos 3 dias)
        date_max = datetime.now(timezone.utc)
        date_min = date_max - timedelta(days=3)
        max_messages_per_group = 5  # Apenas 5 mensagens por grupo

        print(f"📅 Período: {date_min.strftime('%Y-%m-%d')} até {date_max.strftime('%Y-%m-%d')}")
        print(f"📊 Limite: {max_messages_per_group} mensagens por grupo")

        data = []
        total_groups_processed = 0
        total_messages_collected = 0

        # Conectar e fazer scraping
        with TelegramClient(telegram_creds['username'], telegram_creds['api_id'], telegram_creds['api_hash']) as client:
            print(f"\n🔗 Conectado como: {client.get_me().first_name}")

            for group_username in test_groups:
                print(f"\n📺 Processando: {group_username}")

                try:
                    entity = client.get_entity(group_username)
                    print(f"  ✅ Canal encontrado: {entity.title}")

                    message_count = 0

                    # Iterar mensagens recentes
                    for message in client.iter_messages(entity, limit=max_messages_per_group):
                        if message.date and date_min <= message.date <= date_max:
                            # Coletar dados da mensagem
                            message_data = {
                                'Group': group_username,
                                'Group_Title': entity.title,
                                'Message_ID': message.id,
                                'Content': (message.text or '')[:200],  # Primeiros 200 chars
                                'Date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                                'Views': message.views or 0,
                                'Reactions': len(message.reactions.results) if message.reactions else 0,
                                'Forwards': message.forwards or 0,
                                'Has_Media': bool(message.media),
                                'Author_ID': message.from_id.user_id if message.from_id else None,
                                'URL': f'https://t.me/{group_username.replace("@", "")}/{message.id}',
                                'Collected_At': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }

                            data.append(message_data)
                            message_count += 1

                        if message_count >= max_messages_per_group:
                            break

                    print(f"  📊 Coletadas: {message_count} mensagens")
                    total_messages_collected += message_count
                    total_groups_processed += 1

                except Exception as e:
                    print(f"  ❌ Erro em {group_username}: {e}")

        # Salvar resultados
        if data:
            df = pd.DataFrame(data)
            output_file = f'test_scraping_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            df.to_excel(output_file, index=False)

            print(f"\n📊 RESULTADOS DO TESTE:")
            print(f"  ✅ Grupos processados: {total_groups_processed}")
            print(f"  ✅ Mensagens coletadas: {total_messages_collected}")
            print(f"  💾 Arquivo salvo: {output_file}")

            # Preview dos dados
            print(f"\n📋 Preview dos dados (primeiras 3 linhas):")
            for i, row in df.head(3).iterrows():
                print(f"  {i+1}. {row['Group']} | {row['Date']} | Views: {row['Views']}")
                print(f"     Content: {row['Content'][:100]}...")

            print(f"\n📈 Estatísticas:")
            print(f"  Grupos únicos: {df['Group'].nunique()}")
            print(f"  Total de views: {df['Views'].sum()}")
            print(f"  Mensagens com mídia: {df['Has_Media'].sum()}")
            print(f"  Período: {df['Date'].min()} até {df['Date'].max()}")

            return True

        else:
            print("\n⚠️ Nenhuma mensagem coletada no período especificado")
            print("💡 Tente aumentar o período ou verificar se os canais têm mensagens recentes")
            return False

    except Exception as e:
        print(f"\n❌ ERRO no scraping: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    success = test_telegram_scraping()

    if success:
        print("\n✅ TESTE DE SCRAPING PASSOU")
        print("🎯 Sistema está funcionando corretamente!")
    else:
        print("\n❌ TESTE DE SCRAPING FALHOU")
        print("💡 Verifique as configurações ou conectividade")

    print("=" * 60)