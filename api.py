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
    
    # Importações específicas do projeto
    from src.auth import init_auth
    from src.Models.AssetStartModel import AssetStartModel
    from src.Models.CoinModel import CoinModel
    from src.Models.SimulationTradeModel import SimulationTradeModel
    from src.modules.BinanceRobot import BinanceTraderBot
    
    # Inicializa o sistema de autenticação
    init_auth(app)
    
    # Inicializa o modelo de moedas
    CoinModel.init_db()
    
    # Inicializa o modelo de simulações
    SimulationTradeModel.init_db()
    
    # Rota de diagnóstico
    @app.route('/health')
    def health():
        return jsonify({
            "status": "ok", 
            "message": "API está funcionando corretamente",
            "python_version": sys.version,
            "paths": sys.path
        })
    
    # Rota alternativa de homepage (sem autenticação)
    @app.route('/status')
    def status():
        return "API do Robô de Trading está funcionando! Acesse /login para entrar."
    
    # Rota para página inicial
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')
    
    # Rota para a página de logs em tempo real
    @app.route('/logs')
    @login_required
    def logs_page():
        return render_template('logs.html')
    
    # Rota para a página de gerenciamento de moedas
    @app.route('/coins')
    @login_required
    def coins_page():
        # Apenas administradores podem gerenciar moedas
        if not current_user.is_admin:
            return redirect(url_for('index'))
        return render_template('coins.html')
    
    # Rota raiz para login
    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return redirect(url_for('auth.login'))
        
    # Agora precisamos importar e processar todas as outras rotas de src/api.py
    # de maneira que não cause conflito
    print("Importando APIs e classes adicionais do arquivo original...")
    
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
    
    # Classe para simulação que herda de BinanceTraderBot (copiada do arquivo original)
    class SimulationTraderBot(BinanceTraderBot):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.simulation_mode = True
            self.simulation_trades = []
            self.simulation_balance = 0
            self.simulation_stock_balance = 0
            self.initial_price = 0
            
        # Sobrescreve métodos de ordem para não executar de verdade
        def buyMarketOrder(self):
            if not self.simulation_mode:
                return super().buyMarketOrder()
            
            current_price = float(self.stock_data["close_price"].iloc[-1])
            if self.initial_price == 0:
                self.initial_price = current_price
                
            trade = {
                "type": "BUY",
                "price": current_price,
                "quantity": self.traded_quantity,
                "timestamp": self.getTimestamp(),
                "total_value": current_price * self.traded_quantity
            }
            
            self.simulation_trades.append(trade)
            self.last_buy_price = current_price
            self.simulation_stock_balance += self.traded_quantity
            self.actual_trade_position = True
            
            # Registrar a operação no banco de dados
            trade_id = SimulationTradeModel.register_trade(
                simulation_id=self.simulation_id,
                operation_code=self.operation_code,
                trade_type="BUY",
                price=current_price,
                quantity=self.traded_quantity,
                total_value=current_price * self.traded_quantity,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            log_msg = f"[SIMULAÇÃO] Ordem de compra: {self.operation_code} - Preço: {current_price}, Quantidade: {self.traded_quantity}"
            add_log_message(log_msg, "buy")
            logging.info(f"[SIMULAÇÃO] Ordem de compra: {json.dumps(trade)}")
            return True
        
        def sellMarketOrder(self):
            # (resto da implementação omitida por brevidade)
            return True
            
        def buyLimitedOrder(self, price=0):
            # Na simulação tratamos como compra a mercado para simplificar
            return self.buyMarketOrder()
        
        def sellLimitedOrder(self, price=0):
            # Na simulação tratamos como venda a mercado para simplificar
            return self.sellMarketOrder()
        
        def getActualTradePosition(self):
            if not self.simulation_mode:
                return super().getActualTradePosition()
                
            return self.simulation_stock_balance > 0
    
    # Importar as rotas do arquivo original será feito gradualmente
    # conforme necessário, para evitar conflitos
    
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