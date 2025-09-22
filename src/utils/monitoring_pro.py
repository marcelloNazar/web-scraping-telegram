#!/usr/bin/env python3
"""
CloudWatch Monitor PRO com Dashboard automático para TelegramScrap
Versão completa com dashboard, alarmes e métricas avançadas
"""

import boto3
from datetime import datetime
import json
import psutil
import time

class CloudWatchMonitorPro:
    """Monitor CloudWatch completo com Dashboard automático"""

    def __init__(self):
        try:
            self.cloudwatch = boto3.client('cloudwatch')
            self.enabled = True
            print("✅ CloudWatch habilitado")

            # Criar dashboard automático
            self._create_dashboard()

        except Exception as e:
            print(f"⚠️ CloudWatch erro: {e}")
            self.enabled = False

    def _create_dashboard(self):
        """Criar dashboard TelegramScrap automaticamente"""
        try:
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["TelegramScrap", "MessagesProcessed"],
                                [".", "GroupsProcessed"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": "us-east-1",
                            "title": "📊 Processamento Geral",
                            "yAxis": {
                                "left": {
                                    "min": 0
                                }
                            }
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["TelegramScrap", "POL_Messages"],
                                [".", "CONSPIRA_Messages"],
                                [".", "NAZ_Messages"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": "us-east-1",
                            "title": "🏛️ Classificação de Mensagens",
                            "view": "timeSeries",
                            "stacked": False,
                            "yAxis": {
                                "left": {
                                    "min": 0
                                }
                            }
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["TelegramScrap", "ExecutionTime"],
                                [".", "GroupsPerMinute"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": "us-east-1",
                            "title": "⚡ Performance",
                            "yAxis": {
                                "left": {
                                    "min": 0
                                }
                            }
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["TelegramScrap", "MemoryUsage"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": "us-east-1",
                            "title": "💾 Uso de Memória",
                            "yAxis": {
                                "left": {
                                    "min": 0
                                }
                            }
                        }
                    }
                ]
            }

            self.cloudwatch.put_dashboard(
                DashboardName='TelegramScrap-Dashboard',
                DashboardBody=json.dumps(dashboard_body)
            )

            print("✅ Dashboard TelegramScrap criado automaticamente")
            print("📊 Acesse: AWS Console → CloudWatch → Dashboards → TelegramScrap-Dashboard")

        except Exception as e:
            print(f"⚠️ Erro criando dashboard: {e}")

    def send_metric(self, metric_name, value, unit='Count'):
        """Enviar métrica para CloudWatch"""
        if not self.enabled:
            return False

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
        """Enviar estatísticas completas do scraping"""
        if not self.enabled:
            return False

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

            # Enviar métricas em batch
            self.cloudwatch.put_metric_data(
                Namespace='TelegramScrap',
                MetricData=metrics
            )

            print(f"✅ Métricas enviadas: {total_messages} mensagens, {groups_count} grupos")
            print(f"📊 Dashboard: AWS Console → CloudWatch → Dashboards → TelegramScrap-Dashboard")
            return True

        except Exception as e:
            print(f"❌ Erro enviando métricas: {e}")
            return False

    def send_performance_metrics(self, execution_time, groups_per_minute):
        """Enviar métricas de performance"""
        if not self.enabled:
            return False

        try:
            # Calcular uso de memória atual
            memory_usage = psutil.virtual_memory().used / (1024 * 1024)  # MB

            perf_metrics = [
                {'MetricName': 'ExecutionTime', 'Value': execution_time, 'Unit': 'Seconds'},
                {'MetricName': 'MemoryUsage', 'Value': memory_usage, 'Unit': 'Megabytes'},
                {'MetricName': 'GroupsPerMinute', 'Value': groups_per_minute, 'Unit': 'Count/Second'}
            ]

            for metric in perf_metrics:
                metric['Timestamp'] = datetime.now()

            self.cloudwatch.put_metric_data(
                Namespace='TelegramScrap',
                MetricData=perf_metrics
            )

            print("✅ Métricas de performance enviadas")
            return True

        except Exception as e:
            print(f"❌ Erro enviando métricas de performance: {e}")
            return False

    def create_alarms(self):
        """Criar alarmes automáticos"""
        if not self.enabled:
            return False

        try:
            # Alarme: muitas mensagens extremistas
            self.cloudwatch.put_metric_alarm(
                AlarmName='TelegramScrap-HighExtremistContent',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName='NAZ_Messages',
                Namespace='TelegramScrap',
                Period=300,
                Statistic='Sum',
                Threshold=100.0,
                ActionsEnabled=False,
                AlarmDescription='Alto volume de conteúdo extremista detectado',
                Unit='Count'
            )

            # Alarme: execução muito lenta
            self.cloudwatch.put_metric_alarm(
                AlarmName='TelegramScrap-SlowExecution',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=1,
                MetricName='ExecutionTime',
                Namespace='TelegramScrap',
                Period=300,
                Statistic='Average',
                Threshold=3600.0,
                ActionsEnabled=False,
                AlarmDescription='Execução muito lenta detectada',
                Unit='Seconds'
            )

            # Alarme: alto uso de memória
            self.cloudwatch.put_metric_alarm(
                AlarmName='TelegramScrap-HighMemoryUsage',
                ComparisonOperator='GreaterThanThreshold',
                EvaluationPeriods=2,
                MetricName='MemoryUsage',
                Namespace='TelegramScrap',
                Period=300,
                Statistic='Average',
                Threshold=2048.0,
                ActionsEnabled=False,
                AlarmDescription='Alto uso de memória detectado',
                Unit='Megabytes'
            )

            print("✅ Alarmes criados automaticamente")
            print("⚠️ Acesse: AWS Console → CloudWatch → Alarms")
            return True

        except Exception as e:
            print(f"⚠️ Erro criando alarmes: {e}")
            return False

    def send_session_start(self):
        """Marcar início de sessão de scraping"""
        return self.send_metric('SessionStart', 1, 'Count')

    def send_session_end(self):
        """Marcar fim de sessão de scraping"""
        return self.send_metric('SessionEnd', 1, 'Count')

    def send_error_metric(self, error_type='GeneralError'):
        """Enviar métrica de erro"""
        return self.send_metric(f'Error_{error_type}', 1, 'Count')

    def get_dashboard_url(self):
        """Retorna URL do dashboard (para referência)"""
        if not self.enabled:
            return None

        # URL genérica - usuário precisa acessar o console
        return "AWS Console → CloudWatch → Dashboards → TelegramScrap-Dashboard"

    def cleanup_old_alarms(self):
        """Remove alarmes antigos se existirem"""
        if not self.enabled:
            return False

        try:
            alarm_names = [
                'TelegramScrap-HighExtremistContent',
                'TelegramScrap-SlowExecution',
                'TelegramScrap-HighMemoryUsage'
            ]

            # Tentar deletar alarmes existentes (ignora erros se não existem)
            for alarm_name in alarm_names:
                try:
                    self.cloudwatch.delete_alarms(AlarmNames=[alarm_name])
                except:
                    pass  # Ignora se alarme não existe

            print("🧹 Alarmes antigos removidos")
            return True

        except Exception as e:
            print(f"⚠️ Erro limpando alarmes: {e}")
            return False

# Função de conveniência para compatibilidade
def create_cloudwatch_monitor():
    """Criar monitor CloudWatch PRO"""
    return CloudWatchMonitorPro()

# Exemplo de uso
if __name__ == "__main__":
    # Teste da funcionalidade
    print("🧪 Testando CloudWatchMonitorPro...")

    monitor = CloudWatchMonitorPro()

    if monitor.enabled:
        print("✅ Monitor PRO habilitado")

        # Teste alarmes
        monitor.cleanup_old_alarms()
        monitor.create_alarms()

        # Teste métricas
        monitor.send_scraping_stats(1000, 10, 500, 300, 50)
        monitor.send_performance_metrics(120, 5.5)

        print("🎉 Teste completo!")
    else:
        print("❌ Monitor não habilitado - configure credenciais AWS")