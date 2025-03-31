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
    
    # Em vez de usar exec() para importar src/api.py, vamos importar os componentes necessários
    print("Importando componentes do aplicativo...")
    
    # Importar módulos e inicializar o sistema de autenticação
    from src.auth import init_auth
    from src.Models.AssetStartModel import AssetStartModel
    from src.Models.CoinModel import CoinModel
    from src.Models.SimulationTradeModel import SimulationTradeModel
    from src.modules.BinanceRobot import BinanceTraderBot
    
    # Inicializar sistema de autenticação
    print("Inicializando autenticação...")
    init_auth(app)
    
    # Inicializar modelos
    print("Inicializando modelos...")
    CoinModel.init_db()
    SimulationTradeModel.init_db()
    
    # Dicionários e configurações do robô
    running_bots = {}
    simulation_bots = {}
    bots_lock = threading.Lock()
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
    
    # Classe para simulação
    class SimulationTraderBot(BinanceTraderBot):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.simulation_mode = True
            self.simulation_trades = []
            self.simulation_balance = 0
            self.simulation_stock_balance = 0
            self.initial_price = 0
        
        # Métodos simplificados para simulação
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
    
    # Importar as rotas principais do arquivo src/api.py
    # Vamos importar as funções específicas que precisamos
    print("Importando as rotas principais...")
    
    # Importar implementações específicas do arquivo src/api.py
    # Isso pode ser expandido conforme necessário
    
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
    
    # Importar as rotas do arquivo original
    print("Implementando rotas personalizadas...")
    # Não importar de src.api, pois as funções estão comentadas

    # Rota principal
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')

    # Menu de navegação
    @app.context_processor
    def inject_nav_links():
        return {
            'nav_links': [
                {'title': 'Dashboard', 'url': '/', 'icon': 'dashboard'},
                {'title': 'Logs', 'url': '/logs', 'icon': 'receipt_long'},
                {'title': 'Histórico de Simulações', 'url': '/simulation/history', 'icon': 'insights'},
                {'title': 'Moedas', 'url': '/coins', 'icon': 'currency_bitcoin', 'admin_only': True},
                {'title': 'Diagnóstico', 'url': '/diagnostico-page', 'icon': 'health_and_safety'}
            ]
        }
    
    # Rota para visualizar o robô
    @app.route('/robot/<robot_id>')
    @login_required
    def view_robot(robot_id):
        return render_template('robot_view.html', robot_id=robot_id)
    
    # Rota para listar ativos
    @app.route('/assets')
    @login_required
    def assets_list():
        return render_template('assets_list.html')
    
    # Rota para obter status do robô
    @app.route('/api/robot/<robot_id>/status', methods=['GET'])
    @login_required
    def get_robot_status(robot_id):
        if robot_id in running_bots:
            return jsonify({"status": "running"})
        else:
            return jsonify({"status": "stopped"})
    
    # Rotas da API
    # Rota para obter o status da API
    @app.route('/api/status', methods=['GET'])
    def api_status():
        try:
            api_key = os.environ.get('BINANCE_API_KEY', 'NÃO DEFINIDA')
            api_secret = os.environ.get('BINANCE_SECRET_KEY', 'NÃO DEFINIDA')
            
            # Verificar conexão com a Binance se as chaves estiverem definidas
            binance_status = "not_configured"
            if api_key != 'NÃO DEFINIDA' and api_secret != 'NÃO DEFINIDA' and api_key != 'sua_api_key_aqui' and api_secret != 'sua_secret_key_aqui':
                try:
                    client = Client(api_key, api_secret)
                    status = client.get_system_status()
                    binance_status = status['status'] == 0 and "normal" or "maintenance"
                except:
                    binance_status = "error"
            
            return jsonify({
                "status": "ok",
                "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "binance_connection": binance_status,
                "version": "1.0.0"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    # Rota para obter informações da carteira
    @app.route('/api/wallet', methods=['GET'])
    @login_required
    def get_wallet():
        try:
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_SECRET_KEY')
            
            if not api_key or not api_secret or api_key == 'sua_api_key_aqui' or api_secret == 'sua_secret_key_aqui':
                return jsonify({
                    "status": "error",
                    "message": "Chaves da API Binance não configuradas"
                }), 400
            
            try:
                client = Client(api_key, api_secret)
                account = client.get_account()
                
                # Filtrar apenas saldos não-zero
                balances = [
                    {
                        "asset": asset['asset'],
                        "free": float(asset['free']),
                        "locked": float(asset['locked'])
                    }
                    for asset in account['balances'] 
                    if float(asset['free']) > 0 or float(asset['locked']) > 0
                ]
                
                return jsonify({
                    "status": "success",
                    "balances": balances
                })
            except BinanceAPIException as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro na API da Binance: {e.message} (Código: {e.code})"
                }), 400
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    # Listar robôs em execução
    @app.route('/api/bot/list', methods=['GET'])
    @login_required
    def list_bots():
        with bots_lock:
            bots_info = []
            for bot_id, bot in running_bots.items():
                try:
                    bot_info = {
                        "id": bot_id,
                        "symbol": bot.symbol,
                        "operation_mode": bot.operation_mode,
                        "last_operation": bot.last_operation,
                        "last_price": bot.last_price,
                        "is_active": bot.is_active,
                        "start_time": bot.start_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(bot, 'start_time') else None
                    }
                    bots_info.append(bot_info)
                except Exception as e:
                    bots_info.append({
                        "id": bot_id,
                        "error": str(e),
                        "is_active": False
                    })
            
            return jsonify({
                "status": "success",
                "bots": bots_info
            })

    # Iniciar robô
    @app.route('/api/bot/start', methods=['POST'])
    @login_required
    def start_bot():
        try:
            data = request.get_json()
            
            required_fields = ['symbol', 'operation_mode', 'traded_quantity']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        "status": "error",
                        "message": f"Campo obrigatório ausente: {field}"
                    }), 400
            
            symbol = data['symbol']
            operation_mode = data['operation_mode']
            traded_quantity = float(data['traded_quantity'])
            
            # Gerar ID para o robô
            bot_id = f"{symbol}_{operation_mode}_{int(time.time())}"
            
            # Verificar se o robô já está em execução
            with bots_lock:
                for existing_bot_id, bot in running_bots.items():
                    if bot.symbol == symbol and bot.operation_mode == operation_mode:
                        return jsonify({
                            "status": "error",
                            "message": f"Já existe um robô em execução para {symbol} com modo {operation_mode}"
                        }), 400
            
            # Iniciar o robô
            try:
                api_key = os.environ.get('BINANCE_API_KEY')
                api_secret = os.environ.get('BINANCE_SECRET_KEY')
                
                if not api_key or not api_secret or api_key == 'sua_api_key_aqui' or api_secret == 'sua_secret_key_aqui':
                    return jsonify({
                        "status": "error",
                        "message": "Chaves da API Binance não configuradas"
                    }), 400
                
                bot = BinanceTraderBot(
                    symbol=symbol,
                    operation_mode=operation_mode,
                    api_key=api_key,
                    api_secret=api_secret,
                    traded_quantity=traded_quantity
                )
                
                # Adicionar bot à lista de robôs em execução
                with bots_lock:
                    running_bots[bot_id] = bot
                
                # Iniciar a thread do robô
                bot_thread = threading.Thread(target=bot.run)
                bot_thread.daemon = True
                bot_thread.start()
                
                return jsonify({
                    "status": "success",
                    "message": f"Robô iniciado com sucesso para {symbol}",
                    "bot_id": bot_id
                })
                
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao iniciar robô: {str(e)}"
                }), 500
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    # Parar robô
    @app.route('/api/bot/stop/<bot_id>', methods=['POST'])
    @login_required
    def stop_bot(bot_id):
        try:
            with bots_lock:
                if bot_id not in running_bots:
                    return jsonify({
                        "status": "error",
                        "message": f"Robô com ID {bot_id} não encontrado"
                    }), 404
                
                # Parar o robô
                bot = running_bots[bot_id]
                bot.stop()
                
                # Remover da lista de robôs em execução
                del running_bots[bot_id]
                
                return jsonify({
                    "status": "success",
                    "message": f"Robô {bot_id} parado com sucesso"
                })
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    
    # Verificar todas as rotas registradas
    print("Rotas registradas na aplicação:")
    for rule in app.url_map.iter_rules():
        print(f"Rota: {rule.endpoint} -> {rule.rule}")
    
    # Rota para a página de logs
    @app.route('/logs')
    @login_required
    def logs_page():
        return render_template('logs.html')

    # Rota para a página de moedas
    @app.route('/coins')
    @login_required
    def coins_page():
        if not current_user.is_admin:
            return redirect('/')
        return render_template('coins.html')

    # Rota para o histórico de simulações
    @app.route('/simulation/history')
    @login_required
    def simulation_history_page():
        return render_template('simulation_history.html')

    # Rota para a página de dashboard (redirecionamento)
    @app.route('/dashboard')
    @login_required
    def dashboard():
        return redirect('/')

    # Endpoints para moedas
    @app.route('/api/coins', methods=['GET'])
    @login_required
    def get_coins():
        coins = CoinModel.get_all()
        return jsonify({'success': True, 'coins': coins})

    @app.route('/api/coins/<int:coin_id>', methods=['GET'])
    @login_required
    def get_coin(coin_id):
        coin = CoinModel.get_by_id(coin_id)
        if coin:
            return jsonify({'success': True, 'coin': coin})
        return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404

    @app.route('/api/coins', methods=['POST'])
    @login_required
    def create_coin():
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        required_fields = ['symbol', 'name', 'is_active']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Campo obrigatório ausente: {field}'}), 400
        
        coin_id = CoinModel.create(
            symbol=data['symbol'],
            name=data['name'],
            is_active=data['is_active']
        )
        
        return jsonify({'success': True, 'coin_id': coin_id})

    @app.route('/api/coins/<int:coin_id>', methods=['PUT'])
    @login_required
    def update_coin(coin_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permissão negada'}), 403
        
        data = request.get_json()
        
        coin = CoinModel.get_by_id(coin_id)
        if not coin:
            return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404
        
        updated = CoinModel.update(
            coin_id=coin_id,
            symbol=data.get('symbol', coin['symbol']),
            name=data.get('name', coin['name']),
            is_active=data.get('is_active', coin['is_active'])
        )
        
        if updated:
            return jsonify({'success': True, 'coin_id': coin_id})
        return jsonify({'success': False, 'error': 'Erro ao atualizar moeda'}), 500

    @app.route('/api/coins/<int:coin_id>', methods=['DELETE'])
    @login_required
    def delete_coin(coin_id):
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permissão negada'}), 403
        
        coin = CoinModel.get_by_id(coin_id)
        if not coin:
            return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404
        
        deleted = CoinModel.delete(coin_id)
        
        if deleted:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Erro ao excluir moeda'}), 500

    # Endpoints para histórico de simulações
    @app.route('/api/simulation/history/list', methods=['GET'])
    @login_required
    def list_simulation_history():
        try:
            # Consultar banco de dados para obter histórico de simulações
            conn = sqlite3.connect('src/database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Agrupar por simulation_id e obter a mais recente de cada
            cursor.execute('''
            SELECT simulation_id as id, operation_code, 
                   MIN(timestamp) as start_date, 
                   MAX(timestamp) as end_date,
                   COUNT(*) as trade_count
            FROM simulation_trades
            GROUP BY simulation_id, operation_code
            ORDER BY MAX(timestamp) DESC
            ''')
            
            simulations = []
            for row in cursor.fetchall():
                sim_data = dict(row)
                
                # Obter estatísticas para cada simulação
                stats = SimulationTradeModel.get_simulation_statistics(sim_data['id'])
                
                simulations.append({
                    'id': sim_data['id'],
                    'operation_code': sim_data['operation_code'],
                    'start_date': sim_data['start_date'],
                    'end_date': sim_data['end_date'],
                    'trade_count': sim_data['trade_count'],
                    'created_at': sim_data['start_date'],
                    'profit_loss': stats['profit_loss'],
                    'profit_loss_percentage': stats['profit_loss_percentage']
                })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'simulations': simulations
            })
            
        except Exception as e:
            logging.error(f"Erro ao listar histórico de simulações: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/simulation/history/<simulation_id>', methods=['GET'])
    @login_required
    def get_simulation_history(simulation_id):
        try:
            # Buscar trades da simulação
            trades = SimulationTradeModel.get_trades_by_simulation(simulation_id)
            
            if not trades:
                return jsonify({
                    'success': False,
                    'error': 'Simulação não encontrada ou sem operações'
                }), 404
            
            # Obter estatísticas
            statistics = SimulationTradeModel.get_simulation_statistics(simulation_id)
            
            # Obter detalhes adicionais da simulação, se disponível
            simulation_details = {}
            for trade in trades:
                simulation_details['operation_code'] = trade['operation_code']
                break
            
            return jsonify({
                'success': True,
                'simulation_id': simulation_id,
                'trades': trades,
                'statistics': statistics,
                'details': simulation_details
            })
            
        except Exception as e:
            logging.error(f"Erro ao obter histórico da simulação {simulation_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Endpoint para servir arquivos estáticos
    @app.route('/static/<path:path>')
    def serve_static(path):
        return send_from_directory('src/static', path)

    # Iniciar o servidor Flask diretamente
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 5000))
        print(f"�� Iniciando servidor na porta {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)

except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 