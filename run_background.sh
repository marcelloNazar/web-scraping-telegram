#!/bin/bash

# Script para gerenciar Telegram Scraper em background
# Uso: ./run_background.sh [start|stop|status|logs]

SCRIPT_NAME="telegram_scraper_vm_continuous.py"
PID_FILE="scraper.pid"
LOG_FILE="scraper.log"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            echo "⚠️  Scraper já está rodando (PID: $(cat $PID_FILE))"
            exit 1
        fi
        
        echo "🚀 Iniciando Telegram Scraper em background..."
        nohup python3 "$SCRIPT_NAME" > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        
        sleep 2
        if ps -p $(cat $PID_FILE) > /dev/null; then
            echo "✅ Scraper iniciado com sucesso!"
            echo "📋 PID: $(cat $PID_FILE)"
            echo "📄 Logs: tail -f $LOG_FILE"
        else
            echo "❌ Falha ao iniciar scraper"
            rm -f "$PID_FILE"
            exit 1
        fi
        ;;
        
    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "⚠️  Scraper não está rodando"
            exit 1
        fi
        
        PID=$(cat $PID_FILE)
        echo "🛑 Parando Telegram Scraper (PID: $PID)..."
        
        if kill "$PID" 2>/dev/null; then
            echo "✅ Scraper parado com sucesso"
        else
            echo "⚠️  Forçando parada..."
            kill -9 "$PID" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        ;;
        
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat $PID_FILE)
            if ps -p "$PID" > /dev/null; then
                echo "✅ Scraper rodando (PID: $PID)"
                echo "📊 Uptime: $(ps -o etime= -p $PID | tr -d ' ')"
            else
                echo "❌ Scraper parado (PID file órfão)"
                rm -f "$PID_FILE"
            fi
        else
            echo "⚠️  Scraper não está rodando"
        fi
        ;;
        
    logs)
        echo "📄 Logs em tempo real (Ctrl+C para sair):"
        tail -f "$LOG_FILE"
        ;;
        
    *)
        echo "🔧 Uso: $0 {start|stop|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start  - Iniciar scraper em background"
        echo "  stop   - Parar scraper"
        echo "  status - Ver status atual"
        echo "  logs   - Ver logs em tempo real"
        exit 1
        ;;
esac
