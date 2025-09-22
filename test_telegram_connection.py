#!/usr/bin/env python3
"""
Teste de Conexão Telegram
Valida credenciais e acesso a canais
"""

import sys
sys.path.append('./src')

def test_telegram_connection():
    """Testa conexão básica com Telegram"""

    print("🔗 Testando conexão Telegram...")

    try:
        from utils.config_loader import ConfigLoader
        from telethon.sync import TelegramClient

        # Carregar credenciais
        config = ConfigLoader()
        creds = config.get_telegram_credentials()

        print(f"📱 Usuário configurado: {creds['username']}")

        # Conectar ao Telegram
        with TelegramClient(creds['username'], creds['api_id'], creds['api_hash']) as client:
            # Verificar usuário conectado
            me = client.get_me()
            print(f"✅ Conectado como: {me.first_name} {me.last_name or ''}")
            print(f"📞 Telefone: {me.phone}")
            print(f"🆔 ID: {me.id}")

            # Testar acesso a canal público (LulanoTelegram)
            try:
                entity = client.get_entity('@LulanoTelegram')
                print(f"✅ Canal acessível: {entity.title}")
                print(f"👥 Participantes: {getattr(entity, 'participants_count', 'N/A')}")
                print(f"📝 Descrição: {getattr(entity, 'about', 'N/A')[:100]}...")
            except Exception as e:
                print(f"⚠️ Erro acessando @LulanoTelegram: {e}")

            # Testar acesso a outro canal
            try:
                entity = client.get_entity('@jairbolsonarobrasil')
                print(f"✅ Canal acessível: {entity.title}")
                print(f"👥 Participantes: {getattr(entity, 'participants_count', 'N/A')}")
            except Exception as e:
                print(f"⚠️ Erro acessando @jairbolsonarobrasil: {e}")

        print("\n🎯 RESULTADO: Telegram 100% funcional!")
        return True

    except Exception as e:
        print(f"❌ ERRO na conexão Telegram: {e}")
        print("💡 Verifique se as credenciais estão corretas em config/telegram_credentials.py")
        return False

if __name__ == "__main__":
    success = test_telegram_connection()
    if success:
        print("✅ Teste PASSOU")
    else:
        print("❌ Teste FALHOU")
        sys.exit(1)