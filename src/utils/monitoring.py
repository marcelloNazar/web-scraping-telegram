import boto3
from datetime import datetime

class CloudWatchMonitor:
    """Monitor CloudWatch simples para TelegramScrap"""

    def __init__(self):
        try:
            self.cloudwatch = boto3.client('cloudwatch')
            self.enabled = True
            print("✅ CloudWatch habilitado")
        except Exception as e:
            print(f"⚠️ CloudWatch erro: {e}")
            self.enabled = False

    def send_metric(self, metric_name, value, unit='Count'):
        """Enviar métrica para CloudWatch"""
        if not self.enabled:
            return

        try:
            self.cloudwatch.put_metric_data(
                Namespace='TelegramScrap',
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Timestamp': datetime.now()
                }]
            )
            return True
        except Exception as e:
            print(f"❌ Erro enviando métrica: {e}")
            return False

    def send_scraping_stats(self, total_messages, groups_count, pol_count, conspira_count, naz_count):
        """Enviar estatísticas do scraping"""
        if not self.enabled:
            return

        try:
            metrics = [
                {'MetricName': 'MessagesProcessed', 'Value': total_messages, 'Unit': 'Count'},
                {'MetricName': 'GroupsProcessed', 'Value': groups_count, 'Unit': 'Count'},
                {'MetricName': 'POL_Messages', 'Value': pol_count, 'Unit': 'Count'},
                {'MetricName': 'CONSPIRA_Messages', 'Value': conspira_count, 'Unit': 'Count'},
                {'MetricName': 'NAZ_Messages', 'Value': naz_count, 'Unit': 'Count'}
            ]

            # Adicionar timestamp a todos
            for metric in metrics:
                metric['Timestamp'] = datetime.now()

            self.cloudwatch.put_metric_data(
                Namespace='TelegramScrap',
                MetricData=metrics
            )

            print(f"✅ Métricas enviadas: {total_messages} mensagens, {groups_count} grupos")
            return True

        except Exception as e:
            print(f"❌ Erro enviando métricas: {e}")
            return False