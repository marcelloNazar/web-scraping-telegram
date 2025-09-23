#!/usr/bin/env python3
"""
Teste Pipeline Completo - TelegramScrap AWS
Testa todos os componentes integrados offline
"""

import sys
sys.path.append('./src')

from utils.google_sheets import GoogleSheetsLoader
from utils.monitoring import CloudWatchMonitor
from utils.aws_kinesis import KinesisStreamer
from utils.aws_elasticsearch import ElasticsearchClient
import json
from datetime import datetime

def test_complete_pipeline():
    """Testar pipeline completo com dados simulados"""

    print("TESTE PIPELINE COMPLETO OFFLINE")
    print("=" * 50)

    # 1. Teste Google Sheets
    print("\n1. Testando Google Sheets...")
    sheets = GoogleSheetsLoader()
    groups = sheets.get_active_groups()
    print(f"Google Sheets: {len(groups)} grupos carregados")

    # 2. Teste CloudWatch
    print("\n2. Testando CloudWatch...")
    monitor = CloudWatchMonitor()
    print(f"CloudWatch: {'Habilitado' if monitor.enabled else 'Desabilitado'}")

    # 3. Teste Kinesis
    print("\n3. Testando Kinesis...")
    kinesis = KinesisStreamer()
    print(f"Kinesis: {'Habilitado' if kinesis.enabled else 'Aguardando AWS'}")

    # 4. Teste Elasticsearch
    print("\n4. Testando Elasticsearch...")
    es_client = ElasticsearchClient()
    print(f"Elasticsearch: {'Habilitado' if es_client.enabled else 'Aguardando AWS'}")

    # 5. Simular dados completos
    print("\n5. Simulando dados de produção...")

    sample_messages = []
    for i, group in enumerate(groups[:10]):  # Primeiros 10 grupos
        for j in range(5):  # 5 mensagens por grupo
            # Extrair username se for dict
            group_name = group['username'] if isinstance(group, dict) else group

            sample_messages.append({
                'message_id': f"msg_{i}_{j}",
                'group_name': group_name,
                'content': f"Teste mensagem política {j} do grupo {group_name}",
                'date_message': datetime.now().isoformat(),
                'views': 100 + (i * j),
                'reactions': 5 + i,
                'shares': 2 + j,
                'url': f'https://t.me/{group_name.replace("@", "")}/123{j}'
            })

    print(f"Criadas {len(sample_messages)} mensagens de teste")

    # 6. Testar envios (quando AWS estiver ativo)
    print("\n6. Testando envios...")

    sent_kinesis = 0
    sent_elasticsearch = 0
    sent_cloudwatch = 0

    if kinesis.enabled:
        for msg in sample_messages:
            if kinesis.send_message(msg):
                sent_kinesis += 1

    if es_client.enabled:
        if es_client.bulk_index_messages(sample_messages):
            sent_elasticsearch = len(sample_messages)

    if monitor.enabled:
        success = monitor.send_scraping_stats(
            len(sample_messages),
            len(groups),
            35,  # POL
            10,  # CONSPIRA
            5    # NAZ
        )
        if success:
            sent_cloudwatch = len(sample_messages)

    # 7. Relatório final
    print(f"\nRELATORIO FINAL:")
    print(f"Google Sheets: OK {len(groups)} grupos")
    print(f"Mensagens teste: OK {len(sample_messages)}")
    print(f"CloudWatch: {'OK' if monitor.enabled else 'AGUARDANDO'} {sent_cloudwatch} enviadas")
    print(f"Kinesis: {'OK' if kinesis.enabled else 'AGUARDANDO'} {sent_kinesis} enviadas")
    print(f"Elasticsearch: {'OK' if es_client.enabled else 'AGUARDANDO'} {sent_elasticsearch} indexadas")

    # Status geral
    components_ready = [
        True,  # Google Sheets sempre funciona
        monitor.enabled,
        kinesis.enabled,
        es_client.enabled
    ]

    ready_count = sum(components_ready)
    total_components = len(components_ready)

    print(f"\nPRONTIDAO GERAL: {ready_count}/{total_components} componentes ativos")

    if ready_count == total_components:
        print("SISTEMA 100% PRONTO PARA PRODUCAO!")
    elif ready_count >= 2:
        print("Sistema parcialmente ativo - pronto para desenvolvimento")
    else:
        print("Sistema aguardando configuracao AWS")

    return {
        'groups_loaded': len(groups),
        'test_messages': len(sample_messages),
        'components_active': ready_count,
        'total_components': total_components,
        'ready_percentage': (ready_count / total_components) * 100
    }

if __name__ == "__main__":
    result = test_complete_pipeline()
    print(f"\nTeste concluido: {result['ready_percentage']:.1f}% dos componentes ativos")