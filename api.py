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
    from binance.exceptions import BinanceAPIException
    
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
    
    print("Carregando arquivo src/api.py para importar funcionalidades...")
    
    # Este método evita que tenhamos que reimplementar todas as rotas
    # Importa o código de src/api.py, mas substitui a variável 'app' pelo nosso app
    with open(os.path.join(src_dir, 'api.py'), 'r') as f:
        src_api_code = f.read()
        
    # Remova a criação da aplicação Flask no src/api.py
    src_api_code = src_api_code.replace("app = Flask(__name__", 
                                      "# app já definido acima #")
    
    # Remova a inicialização do CORS
    src_api_code = src_api_code.replace("CORS(app)", 
                                      "# CORS já habilitado acima #")
    
    print("Executando o código modificado de src/api.py...")
    # Executa o código modificado com o 'app' já definido
    exec(src_api_code)
    
    # Verificar todas as rotas registradas
    print("Rotas registradas na aplicação:")
    for rule in app.url_map.iter_rules():
        print(f"Rota: {rule.endpoint} -> {rule.rule}")
    
    # Rota para a página de diagnóstico
    @app.route('/diagnostico-page')
    def diagnostico_page():
        return render_template('diagnostico.html')
    
    # Rota de diagnóstico adicionada no final
    @app.route('/diagnostico')
    def diagnostico():
        # Informar hora atual
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar chaves da Binance
        api_key = os.environ.get('BINANCE_API_KEY', 'NÃO DEFINIDA')
        api_secret = os.environ.get('BINANCE_SECRET_KEY', 'NÃO DEFINIDA')
        
        # Verificar se as chaves estão presentes (truncando para segurança)
        api_key_status = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "NÃO DEFINIDA"
        api_secret_status = f"{api_secret[:4]}...{api_secret[-4:]}" if len(api_secret) > 8 else "NÃO DEFINIDA"
        
        return jsonify({
            "status": "ok", 
            "message": "Diagnóstico do sistema",
            "timestamp": now,
            "python_version": sys.version,
            "total_routes": len(list(app.url_map.iter_rules())),
            "binance_api_key": api_key_status,
            "binance_secret_key": api_secret_status,
            "env_vars": list(os.environ.keys())
        })
    
    # Rota para testar a conexão com a Binance
    @app.route('/test_binance')
    def test_binance():
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_SECRET_KEY')
        
        # Verificar se as chaves estão definidas
        if not api_key or api_key == 'sua_api_key_aqui' or not api_secret or api_secret == 'sua_secret_key_aqui':
            return jsonify({
                "success": False,
                "message": "Chaves da API Binance não configuradas corretamente no arquivo .env"
            })
        
        try:
            # Tentar criar um cliente Binance
            client = Client(api_key, api_secret)
            
            # Verificar a conexão obtendo informações da conta
            status = client.get_system_status()
            account = client.get_account()
            
            # Construir mensagem de resposta
            message = f"Status do sistema: {status['msg']} | "
            message += f"Permissão para operar: {'Sim' if account['canTrade'] else 'Não'}"
            
            # Obter saldos não-zero
            balances = [f"{asset['asset']}: {asset['free']}" for asset in account['balances'] 
                       if float(asset['free']) > 0]
            
            return jsonify({
                "success": True,
                "message": message,
                "balances": balances[:5]  # Limitar a 5 moedas
            })
        
        except BinanceAPIException as e:
            return jsonify({
                "success": False,
                "message": f"Erro na API da Binance: {e.message} (Código: {e.code})",
                "error_code": e.code
            })
        
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Erro desconhecido: {str(e)}"
            })
    
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