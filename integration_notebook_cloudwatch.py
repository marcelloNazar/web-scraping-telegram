# 📊 INTEGRAÇÃO CLOUDWATCH NO NOTEBOOK TELEGRAMSCRAP
# Código para adicionar no notebook existente

print("=" * 60)
print("🔧 CONFIGURANDO TELEGRAMSCRAP COM CLOUDWATCH MONITORING")
print("=" * 60)

# ===== CÉLULA 1: IMPORTS E INICIALIZAÇÃO =====
# Adicionar no início do notebook, após os imports existentes

import sys
sys.path.append('./src')

# Imports para monitoramento
from utils.monitoring import CloudWatchMonitor
from datetime import datetime
import time

# Inicializar CloudWatch Monitor
print("📊 Inicializando CloudWatch Monitor...")
monitor = CloudWatchMonitor()
print(f"✅ CloudWatch habilitado: {monitor.enabled}")

# ===== CÉLULA 2: VARIÁVEIS DE ESTATÍSTICAS =====
# Adicionar antes do loop principal de scraping

print("📋 Inicializando contadores de estatísticas...")

# Contadores globais para estatísticas
scraping_stats = {
    'total_messages': 0,
    'groups_count': 0,
    'pol_count': 0,
    'conspira_count': 0, 
    'naz_count': 0,
    'total_views': 0,
    'total_reactions': 0,
    'start_time': datetime.now(),
    'processed_groups': []
}

print("✅ Contadores inicializados")

# ===== CÉLULA 3: FUNÇÃO DE CLASSIFICAÇÃO =====
# Função melhorada para classificar mensagens

def classify_message_category(content):
    """Classificar mensagem em POL/CONSPIRA/NAZ"""
    if not content:
        return 'OTHER'
        
    content_lower = content.lower()
    
    # Palavras-chave NAZ (prioridade alta)
    naz_keywords = [
        'supremacia', 'raça superior', 'holocausto', 'terceiro reich', 
        'nazi', 'nazista', 'fascista', 'hitler', 'ariano'
    ]
    if any(keyword in content_lower for keyword in naz_keywords):
        return 'NAZ'
    
    # Palavras-chave CONSPIRA
    conspira_keywords = [
        'conspiração', 'illuminati', 'nova ordem', 'deep state', 
        'maçonaria', 'globalista', 'reptiliano', 'teoria da conspiração',
        'governo mundial', 'controle mental'
    ]
    if any(keyword in content_lower for keyword in conspira_keywords):
        return 'CONSPIRA'
    
    # Palavras-chave POL (política geral)
    pol_keywords = [
        'governo', 'eleição', 'político', 'votação', 'presidente',
        'congresso', 'senado', 'deputado', 'ministro', 'política',
        'bolsonaro', 'lula', 'pt', 'psl', 'direita', 'esquerda'
    ]
    if any(keyword in content_lower for keyword in pol_keywords):
        return 'POL'
    
    return 'POL'  # Default para grupos políticos

print("✅ Função de classificação definida")

# ===== CÉLULA 4: FUNÇÃO DE ATUALIZAÇÃO DE STATS =====
# Função para atualizar estatísticas durante o scraping

def update_scraping_stats(message, group_name):
    """Atualizar estatísticas durante o scraping"""
    global scraping_stats
    
    # Incrementar contador total
    scraping_stats['total_messages'] += 1
    
    # Adicionar views e reactions
    views = getattr(message, 'views', 0) or 0
    reactions = len(getattr(message, 'reactions', {}).get('results', [])) if hasattr(message, 'reactions') and message.reactions else 0
    
    scraping_stats['total_views'] += views
    scraping_stats['total_reactions'] += reactions
    
    # Classificar mensagem
    content = getattr(message, 'text', '') or ''
    category = classify_message_category(content)
    
    # Incrementar contadores por categoria
    if category == 'POL':
        scraping_stats['pol_count'] += 1
    elif category == 'CONSPIRA':
        scraping_stats['conspira_count'] += 1
    elif category == 'NAZ':
        scraping_stats['naz_count'] += 1
    
    # Adicionar grupo processado (sem duplicatas)
    if group_name not in scraping_stats['processed_groups']:
        scraping_stats['processed_groups'].append(group_name)
        scraping_stats['groups_count'] = len(scraping_stats['processed_groups'])
    
    # Enviar métricas a cada 100 mensagens
    if scraping_stats['total_messages'] % 100 == 0:
        send_interim_metrics()
        
    return category

def send_interim_metrics():
    """Enviar métricas intermediárias para CloudWatch"""
    if monitor.enabled:
        success = monitor.send_scraping_stats(
            scraping_stats['total_messages'],
            scraping_stats['groups_count'],
            scraping_stats['pol_count'],
            scraping_stats['conspira_count'],
            scraping_stats['naz_count']
        )
        
        if success:
            print(f"📊 CloudWatch: {scraping_stats['total_messages']} mensagens processadas")

print("✅ Funções de estatísticas definidas")

# ===== CÉLULA 5: CÓDIGO PARA LOOP PRINCIPAL =====
# Substituir/modificar o loop principal de scraping

print("📝 Instruções para o loop principal:")
print("1. No loop de processamento de mensagens, adicione:")
print("   category = update_scraping_stats(message, group_name)")
print("2. Use 'category' para salvar a classificação na planilha")

# Exemplo de como usar no loop:
"""
# No loop principal, para cada mensagem:
for message in messages:
    # Processar mensagem normalmente...
    
    # ADICIONAR ESTA LINHA:
    category = update_scraping_stats(message, group_name)
    
    # Usar category ao salvar os dados:
    message_data = {
        'message_id': str(message.id),
        'group_name': group_name.replace('@', ''),
        'content': message.text or '',
        'date_message': message.date.isoformat(),
        'views': message.views or 0,
        'reactions': len(message.reactions.results) if message.reactions else 0,
        'category_1': category,  # ← USAR A CLASSIFICAÇÃO AUTOMÁTICA
        'url': f"https://t.me/{group_name.replace('@', '')}/{message.id}"
    }
    
    # Adicionar à lista de dados...
"""

# ===== CÉLULA 6: FINALIZAÇÃO E MÉTRICAS FINAIS =====
# Adicionar no final do notebook, após todo o scraping

def finalize_cloudwatch_monitoring():
    """Finalizar monitoramento e enviar métricas finais"""
    
    print("\n🎯 FINALIZANDO SCRAPING COM CLOUDWATCH...")
    print("=" * 50)
    
    # Calcular tempo total
    scraping_stats['end_time'] = datetime.now()
    duration = scraping_stats['end_time'] - scraping_stats['start_time']
    duration_minutes = duration.total_seconds() / 60
    
    # Enviar métricas finais
    if monitor.enabled:
        final_success = monitor.send_scraping_stats(
            scraping_stats['total_messages'],
            scraping_stats['groups_count'],
            scraping_stats['pol_count'],
            scraping_stats['conspira_count'],
            scraping_stats['naz_count']
        )
        
        print(f"✅ Métricas finais enviadas: {final_success}")
    
    # Calcular percentuais
    total = scraping_stats['total_messages']
    pol_pct = (scraping_stats['pol_count'] / total * 100) if total > 0 else 0
    conspira_pct = (scraping_stats['conspira_count'] / total * 100) if total > 0 else 0
    naz_pct = (scraping_stats['naz_count'] / total * 100) if total > 0 else 0
    
    # Relatório final
    print(f"""
🎉 SCRAPING COMPLETO COM CLOUDWATCH!

📊 Estatísticas Finais:
────────────────────────────────────────────
📈 Total de mensagens: {scraping_stats['total_messages']:,}
👥 Grupos processados: {scraping_stats['groups_count']}
📱 Total de views: {scraping_stats['total_views']:,}
❤️ Total de reações: {scraping_stats['total_reactions']:,}
⏱️ Duração: {duration_minutes:.1f} minutos

📋 Distribuição por Categoria:
────────────────────────────────────────────
🏛️ POL (Político): {scraping_stats['pol_count']:,} ({pol_pct:.1f}%)
🔍 CONSPIRA (Conspiração): {scraping_stats['conspira_count']:,} ({conspira_pct:.1f}%)
⚠️ NAZ (Extremismo): {scraping_stats['naz_count']:,} ({naz_pct:.1f}%)

🌐 CloudWatch Dashboard:
────────────────────────────────────────────
👉 https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=TelegramScrap-Dashboard

📊 Métricas TelegramScrap:
👉 https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#metricsV2:query=TelegramScrap
    """)
    
    return scraping_stats

print("✅ Integração CloudWatch configurada!")
print("📊 Execute o notebook normalmente - métricas serão enviadas automaticamente!")

# ===== CÉLULA 7: COMMIT AUTOMÁTICO (OPCIONAL) =====
# Adicionar no final para commit automático dos resultados

def auto_commit_results():
    """Commit automático dos resultados no Git"""
    import subprocess
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Git add
        subprocess.run(['git', 'add', '.'], check=True, cwd='/home/ec2-user/web-scraping-telegram')
        
        # Git commit
        commit_msg = f"TelegramScrap results {timestamp} - {scraping_stats['total_messages']} messages"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd='/home/ec2-user/web-scraping-telegram')
        
        print(f"✅ Resultados commitados automaticamente: {commit_msg}")
        
    except Exception as e:
        print(f"⚠️ Erro no commit automático: {e}")

print("=" * 60)
print("🎉 CONFIGURAÇÃO CLOUDWATCH COMPLETA!")
print("📝 Copie e cole as células acima no notebook TelegramScrap")
print("=" * 60)
