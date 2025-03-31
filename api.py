#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Configurar caminhos e adicionar src/ ao PATH do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)
print(f"Python path configurado: {sys.path}")

# Criar diretório de logs se não existir
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

# Configuração do logger
import logging
logging.basicConfig(
    filename='src/logs/api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    # Lógica para evitar conflitos de rota
    # Em vez de definir as rotas diretamente, vamos simplesmente usar a versão
    # que já existe no módulo auth
    
    # Importações básicas
    from flask import Flask, request, jsonify, send_from_directory, Response
    from flask import stream_with_context, render_template, redirect, url_for
    import threading
    import json
    import time
    import datetime
    from dotenv import load_dotenv
    import copy
    from flask_cors import CORS
    from flask_login import login_required, current_user
    import decimal
    import sqlite3
    from binance.client import Client
    
    # Carrega as variáveis de ambiente
    load_dotenv()
    
    # Configurações iniciais
    VOLATILITY_FACTOR = 0.5
    ACCEPTABLE_LOSS_PERCENTAGE = 0
    STOP_LOSS_PERCENTAGE = 3
    FALLBACK_ACTIVATED = True
    CANDLE_PERIOD = Client.KLINE_INTERVAL_5MINUTE
    TEMPO_ENTRE_TRADES = 5 * 60
    DELAY_ENTRE_ORDENS = 15 * 60
    
    # Inicializa a aplicação Flask
    app = Flask(__name__, 
                static_folder="src/static",
                template_folder="src/templates")
    CORS(app)  # Habilita CORS para todas as rotas
    
    # Configuração de segurança
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_secreta_padrao_para_desenvolvimento')
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = os.environ.get('ENV') == 'production'
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    
    # ===== IMPORTANTE =====
    # CORRIGIR PROBLEMA DE CONFLITO DE ROTAS
    # Em vez de definir as funções aqui, vamos obter as do módulo src.auth
    # =====================
    
    # Importações específicas do projeto
    from src.auth import init_auth
    from src.Models.AssetStartModel import AssetStartModel
    from src.Models.CoinModel import CoinModel
    from src.Models.SimulationTradeModel import SimulationTradeModel
    from src.modules.BinanceRobot import BinanceTraderBot
    
    # Inicializa o sistema de autenticação - ISSO REGISTRA AS ROTAS
    print("Inicializando autenticação...")
    init_auth(app)  # Este módulo provavelmente já define a rota index
    
    # Verificar todas as rotas registradas
    print("Rotas registradas após init_auth:")
    for rule in app.url_map.iter_rules():
        print(f"Rota: {rule.endpoint} -> {rule.rule}")
    
    # Inicializa o modelo de moedas
    print("Inicializando modelo de moedas...")
    CoinModel.init_db()
    
    # Inicializa o modelo de simulações
    print("Inicializando modelo de simulações...")
    SimulationTradeModel.init_db()
    
    # Dicionário para armazenar as instâncias do robô em execução
    running_bots = {}
    # Dicionário para armazenar as instâncias de simulação
    simulation_bots = {}
    # Lock para acesso seguro ao dicionário de robôs
    bots_lock = threading.Lock()
    
    # Lista de mensagens de log para streaming
    log_messages = []
    log_lock = threading.Lock()
    
    # Função para adicionar log
    def add_log_message(message, type="info"):
        with log_lock:
            timestamp = datetime.datetime.now()
            log_messages.append({
                "message": message,
                "timestamp": timestamp.timestamp() * 1000,
                "type": type
            })
            # Manter apenas as últimas 100 mensagens
            if len(log_messages) > 100:
                log_messages.pop(0)
            logging.info(message)
    
    # Classe para simulação que herda de BinanceTraderBot
    class SimulationTraderBot(BinanceTraderBot):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.simulation_mode = True
            self.simulation_trades = []
            self.simulation_balance = 0
            self.simulation_stock_balance = 0
            self.initial_price = 0
            
        # Métodos simplificados
        def buyMarketOrder(self):
            return True
            
        def sellMarketOrder(self):
            return True
            
        def buyLimitedOrder(self, price=0):
            return True
        
        def sellLimitedOrder(self, price=0):
            return True
        
        def getActualTradePosition(self):
            return False
    
    # Rota de saúde - sempre adicionar após init_auth
    @app.route('/health')
    def health():
        # Informar hora atual
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return jsonify({
            "status": "ok", 
            "message": "API está funcionando corretamente",
            "timestamp": now,
            "python_version": sys.version,
            "total_routes": len(list(app.url_map.iter_rules()))
        })
    
    # Rota de status para uso sem autenticação
    @app.route('/status')
    def status():
        # Informar hora atual
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"API do Robô de Trading está funcionando! ({now})"
    
    # Iniciar o servidor Flask diretamente
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        print(f"🤖 Iniciando servidor na porta {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)

except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 