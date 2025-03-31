#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Adicionar src/ ao PATH do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))

# Exibir o PATH para diagnóstico
print("Python path:", sys.path)

# Criar diretório de logs se não existir
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

try:
    # Importações de bibliotecas padrão
    from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context, render_template, redirect, url_for
    import threading
    import json
    import time
    import datetime
    from dotenv import load_dotenv
    import logging
    import copy
    from flask_cors import CORS
    from flask_login import login_required, current_user
    import decimal
    import sqlite3
    
    # Importações específicas do projeto
    sys.path.insert(0, os.path.join(current_dir, 'src'))
    from src.modules.BinanceRobot import BinanceTraderBot
    from binance.client import Client
    from src.Models.AssetStartModel import AssetStartModel
    from src.Models.CoinModel import CoinModel
    from src.Models.SimulationTradeModel import SimulationTradeModel
    from src.auth import init_auth
    
    # Configuração do logger
    logging.basicConfig(
        filename='src/logs/api.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Carrega as variáveis de ambiente
    load_dotenv()
    
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
    
    # Inicializa o sistema de autenticação
    init_auth(app)
    
    # Inicializa o modelo de moedas
    CoinModel.init_db()
    
    # Inicializa o modelo de simulações
    SimulationTradeModel.init_db()
    
    # Adiciona rota para renderizar a interface web
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')
    
    # Adiciona rota para a página de logs em tempo real
    @app.route('/logs')
    @login_required
    def logs_page():
        return render_template('logs.html')
    
    # Adiciona rota para a página de gerenciamento de moedas
    @app.route('/coins')
    @login_required
    def coins_page():
        # Apenas administradores podem gerenciar moedas
        if not current_user.is_admin:
            return redirect(url_for('index'))
        return render_template('coins.html')
    
    # Rota raiz redireciona para login se não estiver autenticado
    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return redirect(url_for('auth.login'))
    
    print("✅ Aplicação Flask inicializada com sucesso!")
    
    # Ponto de entrada para execução direta
    if __name__ == '__main__':
        print("🤖 API e Interface do Robô de Criptomoedas iniciando...")
        print("🌐 Acesse http://localhost:5000 para abrir a interface")
        app.run(debug=False, host='0.0.0.0', port=5000)
        
except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 