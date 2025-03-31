#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Configurar caminhos e adicionar src/ ao PATH do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Importações básicas
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context, render_template, redirect, url_for
import threading
import json
import time
import datetime
from dotenv import load_dotenv
import logging
import copy
from flask_cors import CORS
from flask_login import login_required, current_user, login_user, logout_user
import decimal
import sqlite3

# Configuração do logger
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

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

# Rotas mínimas para verificar se o servidor está funcionando
@app.route('/')
def index():
    return "API do Robô de Trading está funcionando! Acesse /login para entrar."

@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "API está funcionando corretamente"})

# Iniciar o servidor Flask diretamente
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🤖 Iniciando servidor na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=False) 