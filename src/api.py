#!/usr/bin/env python3
"""
Módulo API principal que expõe as rotas e funcionalidades do robô de trading.
Este módulo deve ser importado pelo run.py.
"""

import os
import sys
import sqlite3
import logging
import threading
import time
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, Response
from flask_login import login_required, current_user
from binance.client import Client
from binance.exceptions import BinanceAPIException
import math

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Obter o caminho da raiz do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

# Adicionar ao path do Python para importação de módulos
sys.path.insert(0, root_dir)
sys.path.insert(0, current_dir)

# Importações de módulos do projeto
from Models.AssetStartModel import AssetStartModel
from Models.CoinModel import CoinModel
from Models.SimulationTradeModel import SimulationTradeModel
from modules.BinanceRobot import BinanceTraderBot

# Configurações globais
VOLATILITY_FACTOR = 0.5
ACCEPTABLE_LOSS_PERCENTAGE = 0
STOP_LOSS_PERCENTAGE = 3
FALLBACK_ACTIVATED = True
CANDLE_PERIOD = Client.KLINE_INTERVAL_5MINUTE
TEMPO_ENTRE_TRADES = 5 * 60
DELAY_ENTRE_ORDENS = 15 * 60

# Dicionários e configurações do robô
running_bots = {}
simulation_bots = {}
bots_lock = threading.Lock()
log_messages = []
log_lock = threading.Lock()

# Criação do blueprint principal da API
api_bp = Blueprint('api', __name__)

def add_log_message(message, type="info"):
    """Adiciona uma mensagem de log ao registro."""
    with log_lock:
        timestamp = datetime.now()
        log_messages.append({
            "message": message,
            "timestamp": timestamp.timestamp() * 1000,
            "type": type
        })
        # Manter apenas as últimas 100 mensagens
        if len(log_messages) > 100:
            log_messages.pop(0)
        logger.info(message)

class SimulationTraderBot(BinanceTraderBot):
    """Classe para simulação de trades."""
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

# Rota principal
@api_bp.route('/')
@login_required
def index():
    return render_template('index.html')

# Rota para a página de diagnóstico
@api_bp.route('/diagnostico-page')
def diagnostico_page():
    return render_template('diagnostico.html')

# Rota de diagnóstico
@api_bp.route('/diagnostico')
def diagnostico():
    # Informar hora atual
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
        "total_routes": "N/A",  # Será preenchido após o registro do blueprint
        "binance_api_key": api_key_status,
        "binance_secret_key": api_secret_status,
        "env_vars": list(os.environ.keys())
    })

# Rota para testar a conexão com a Binance
@api_bp.route('/test_binance')
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

# Rota para visualizar o robô
@api_bp.route('/robot/<robot_id>')
@login_required
def view_robot(robot_id):
    return render_template('robot_view.html', robot_id=robot_id)

# Rota para listar ativos
@api_bp.route('/assets')
@login_required
def assets_list():
    return render_template('assets_list.html')

# Rota para obter status do robô
@api_bp.route('/api/robot/<robot_id>/status', methods=['GET'])
@login_required
def get_robot_status(robot_id):
    if robot_id in running_bots:
        return jsonify({"status": "running"})
    else:
        return jsonify({"status": "stopped"})

# Rota para a página de logs
@api_bp.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')

# Rota para a página de moedas
@api_bp.route('/coins')
@login_required
def coins_page():
    if not current_user.is_admin:
        return redirect('/')
    return render_template('coins.html')

# Rota para o histórico de simulações
@api_bp.route('/simulation/history')
@login_required
def simulation_history_page():
    return render_template('simulation_history.html')

# Rota para a página de dashboard (redirecionamento)
@api_bp.route('/dashboard')
@login_required
def dashboard():
    return redirect('/')

# Rotas da API
# Rota para obter o status da API
@api_bp.route('/api/status', methods=['GET'])
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
        
        # Obter bots ativos
        active_bots = []
        with bots_lock:
            for bot_id, bot in running_bots.items():
                try:
                    active_bots.append({
                        "id": bot_id,
                        "stock_code": bot.stock_code,
                        "operation_code": bot.operation_code,
                        "position": bot.last_operation == "BUY" and "Comprado" or "Vendido",
                        "last_buy_price": bot.last_buy_price if hasattr(bot, 'last_buy_price') else 0,
                        "last_sell_price": bot.last_sell_price if hasattr(bot, 'last_sell_price') else 0,
                        "wallet_balance": bot.last_stock_account_balance if hasattr(bot, 'last_stock_account_balance') else 0
                    })
                except Exception as e:
                    logger.error(f"Erro ao obter detalhes do bot {bot_id}: {str(e)}")
        
        return jsonify({
            "status": "ok",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "binance_connection": binance_status,
            "version": "1.0.0",
            "active_bots": active_bots
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Rota para obter informações da carteira
@api_bp.route('/api/wallet', methods=['GET'])
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
            
            # Obter todos os preços atuais para converter em USDT
            tickers = client.get_ticker()
            price_map = {}
            
            for ticker in tickers:
                symbol = ticker['symbol']
                price = float(ticker['lastPrice'])
                price_map[symbol] = price
                
            # Filtrar apenas saldos não-zero
            balances = []
            total_usdt_value = 0
            
            for asset in account['balances']:
                free = float(asset['free'])
                locked = float(asset['locked'])
                total = free + locked
                
                if total > 0:
                    asset_symbol = asset['asset']
                    price_usdt = 0
                    usdt_value = 0
                    
                    # Calcular valor em USDT
                    if asset_symbol == 'USDT':
                        price_usdt = 1
                        usdt_value = total
                    else:
                        # Tentar obter preço diretamente em USDT
                        symbol_usdt = f"{asset_symbol}USDT"
                        if symbol_usdt in price_map:
                            price_usdt = price_map[symbol_usdt]
                            usdt_value = total * price_usdt
                        else:
                            # Tentar via BTC
                            symbol_btc = f"{asset_symbol}BTC"
                            if symbol_btc in price_map and "BTCUSDT" in price_map:
                                price_btc = price_map[symbol_btc]
                                price_btc_usdt = price_map["BTCUSDT"]
                                price_usdt = price_btc * price_btc_usdt
                                usdt_value = total * price_usdt
                    
                    # Validar valores para evitar NaN ou null
                    if usdt_value is None or math.isnan(usdt_value):
                        usdt_value = 0
                    if price_usdt is None or math.isnan(price_usdt):
                        price_usdt = 0
                        
                    # Adicionar à lista de saldos
                    balances.append({
                        "asset": asset_symbol,
                        "free": free,
                        "locked": locked,
                        "total": total,
                        "price_usdt": price_usdt,
                        "usdt_value": usdt_value
                    })
                    
                    total_usdt_value += usdt_value
            
            # Ordenar por valor em USDT (do maior para o menor)
            balances.sort(key=lambda x: x['usdt_value'], reverse=True)
            
            return jsonify({
                "status": "success",
                "balances": balances,
                "total_usdt_value": total_usdt_value,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except BinanceAPIException as e:
            return jsonify({
                "status": "error",
                "message": f"Erro na API da Binance: {e.message} (Código: {e.code})"
            }), 400
        
    except Exception as e:
        logger.error(f"Erro ao carregar carteira: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Listar robôs em execução
@api_bp.route('/api/bot/list', methods=['GET'])
@login_required
def list_bots():
    with bots_lock:
        bots_info = []
        for bot_id, bot in running_bots.items():
            try:
                bot_info = {
                    "id": bot_id,
                    "stock_code": bot.stock_code,
                    "operation_code": bot.operation_code,
                    "last_operation": bot.last_operation if hasattr(bot, 'last_operation') else "NONE",
                    "last_price": bot.last_price if hasattr(bot, 'last_price') else 0,
                    "is_active": True,
                    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
@api_bp.route('/api/bot/start', methods=['POST'])
@login_required
def start_bot():
    try:
        data = request.get_json()
        
        required_fields = ['symbol', 'operation_mode', 'traded_quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Campo obrigatório ausente: {field}"
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
                        "success": False,
                        "error": f"Já existe um robô em execução para {symbol} com modo {operation_mode}",
                        "code": "bot_already_running"
                    }), 400
        
        # Iniciar o robô
        try:
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_SECRET_KEY')
            
            if not api_key or not api_secret or api_key == 'sua_api_key_aqui' or api_secret == 'sua_secret_key_aqui':
                return jsonify({
                    "success": False,
                    "error": "Chaves da API Binance não configuradas",
                    "code": "api_keys_missing"
                }), 400
            
            # Verificar saldo antes de iniciar
            client = Client(api_key, api_secret)
            account = client.get_account()
            
            # Verificar saldo base para comprar (se precisamos de USDT, BTC, etc.)
            quote_currency = symbol.split('/')[-1] if '/' in symbol else 'USDT'  # parte após a barra ou USDT por padrão
            
            # Encontrar o saldo da moeda de cotação
            available_balance = 0
            for balance in account['balances']:
                if balance['asset'] == quote_currency:
                    available_balance = float(balance['free'])
                    break
            
            # Verificar se tem saldo suficiente
            if available_balance < traded_quantity:
                return jsonify({
                    "success": False,
                    "error": f"Saldo insuficiente. Você tem {available_balance:.8f} {quote_currency}, mas precisa de {traded_quantity:.8f} {quote_currency}",
                    "code": "insufficient_balance",
                    "available_balance": available_balance,
                    "required_balance": traded_quantity,
                    "currency": quote_currency
                }), 400
            
            # Tudo ok, criar e iniciar o bot
            bot = BinanceTraderBot(
                stock_code=operation_mode,
                operation_code=symbol,
                traded_quantity=traded_quantity,
                traded_percentage=100,  # 100% do valor definido pelo usuário
                candle_period=CANDLE_PERIOD,
                volatility_factor=data.get('volatility_factor', VOLATILITY_FACTOR),
                acceptable_loss_percentage=data.get('acceptable_loss', ACCEPTABLE_LOSS_PERCENTAGE),
                stop_loss_percentage=data.get('stop_loss', STOP_LOSS_PERCENTAGE),
                fallback_activated=data.get('fallback_activated', FALLBACK_ACTIVATED)
            )
            
            # Adicionar bot à lista de robôs em execução
            with bots_lock:
                running_bots[bot_id] = bot
            
            # Iniciar a thread do robô
            bot_thread = threading.Thread(target=bot.run)
            bot_thread.daemon = True
            bot_thread.start()
            
            add_log_message(f"Bot iniciado para {symbol} com modo {operation_mode}", "success")
            
            return jsonify({
                "success": True,
                "message": f"Robô iniciado com sucesso para {symbol}",
                "bot_id": bot_id
            })
            
        except BinanceAPIException as e:
            error_msg = f"Erro da API Binance: {e.message}"
            logger.error(f"Erro ao iniciar bot - {error_msg}")
            
            # Verificar se é erro de saldo insuficiente
            if e.code == -2010 and "insufficient balance" in e.message.lower():
                return jsonify({
                    "success": False,
                    "error": "Saldo insuficiente na Binance para realizar esta operação",
                    "code": "insufficient_balance",
                    "details": e.message
                }), 400
                
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": e.code
            }), 400
            
        except Exception as e:
            error_msg = f"Erro ao iniciar robô: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Erro genérico ao iniciar bot: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Parar robô
@api_bp.route('/api/bot/stop/<bot_id>', methods=['POST'])
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

# Endpoints para moedas
@api_bp.route('/api/coins', methods=['GET'])
@login_required
def get_coins():
    coins = CoinModel.get_all()
    return jsonify({'success': True, 'coins': coins})

@api_bp.route('/api/coins/<int:coin_id>', methods=['GET'])
@login_required
def get_coin(coin_id):
    coin = CoinModel.get_by_id(coin_id)
    if coin:
        return jsonify({'success': True, 'coin': coin})
    return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404

@api_bp.route('/api/coins', methods=['POST'])
@login_required
def create_coin():
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    data = request.get_json()
    
    required_fields = ['symbol', 'name', 'is_active']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'Campo obrigatório ausente: {field}'}), 400
    
    base_currency = data.get('base_currency', data['symbol'])
    quote_currency = data.get('quote_currency', 'USDT')
    trading_pair = data.get('trading_pair', f"{base_currency}{quote_currency}")
    description = data.get('description', '')
    
    result = CoinModel.add_coin(
        name=data['name'],
        symbol=data['symbol'],
        base_currency=base_currency,
        quote_currency=quote_currency,
        trading_pair=trading_pair,
        description=description,
        is_active=data['is_active']
    )
    
    if result['success']:
        return jsonify({'success': True, 'coin_id': result['id']})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@api_bp.route('/api/coins/<int:coin_id>', methods=['PUT'])
@login_required
def update_coin(coin_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    data = request.get_json()
    
    coin = CoinModel.get_by_id(coin_id)
    if not coin:
        return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404
    
    base_currency = data.get('base_currency', coin['base_currency'])
    quote_currency = data.get('quote_currency', coin['quote_currency'])
    trading_pair = data.get('trading_pair', coin['trading_pair'])
    description = data.get('description', coin['description'])
    
    result = CoinModel.update_coin(
        coin_id=coin_id,
        name=data.get('name', coin['name']),
        symbol=data.get('symbol', coin['symbol']),
        base_currency=base_currency,
        quote_currency=quote_currency,
        trading_pair=trading_pair,
        description=description,
        is_active=data.get('is_active', coin['is_active'])
    )
    
    if result['success']:
        return jsonify({'success': True, 'coin_id': coin_id})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@api_bp.route('/api/coins/<int:coin_id>', methods=['DELETE'])
@login_required
def delete_coin(coin_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Permissão negada'}), 403
    
    coin = CoinModel.get_by_id(coin_id)
    if not coin:
        return jsonify({'success': False, 'error': 'Moeda não encontrada'}), 404
    
    result = CoinModel.delete_coin(coin_id)
    
    if result['success']:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

# Endpoints para histórico de simulações
@api_bp.route('/api/simulation/start', methods=['POST'])
@login_required
def start_simulation():
    try:
        data = request.get_json()
        
        # Verificar dados necessários
        required_fields = ['stock_code', 'operation_code', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'error': f'Campo obrigatório ausente: {field}'
                }), 400
        
        # Extrair dados
        stock_code = data.get('stock_code')
        operation_code = data.get('operation_code')
        quantity = float(data.get('quantity', 0))
        volatility_factor = float(data.get('volatility_factor', 0.5))
        stop_loss = float(data.get('stop_loss', 3.0))
        acceptable_loss = float(data.get('acceptable_loss', 0))
        fallback_activated = data.get('fallback_activated', True)
        
        # Gerar ID único para a simulação
        simulation_id = f"sim_{stock_code}_{operation_code}_{int(time.time())}"
        
        # Registrar simulação no histórico
        # Por simplicidade, vamos registrar um trade inicial
        trade_id = SimulationTradeModel.register_trade(
            simulation_id=simulation_id,
            operation_code=operation_code,
            trade_type='START',
            price=0,  # preço inicial será obtido na primeira execução
            quantity=quantity,
            total_value=0
        )
        
        # Criar um bot de simulação e armazená-lo
        try:
            # Obter preço atual da moeda
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_SECRET_KEY')
            
            if api_key and api_secret and api_key != 'sua_api_key_aqui' and api_secret != 'sua_secret_key_aqui':
                client = Client(api_key, api_secret)
                ticker = client.get_ticker(symbol=operation_code)
                current_price = float(ticker['lastPrice'])
            else:
                # Valor fictício para teste se não tiver API
                current_price = 1000.0
                
            # Criar bot de simulação
            sim_bot = SimulationTraderBot(
                stock_code=stock_code,
                operation_code=operation_code,
                traded_quantity=quantity,
                traded_percentage=100,  # 100% do valor definido pelo usuário
                candle_period=CANDLE_PERIOD,
                volatility_factor=volatility_factor,
                acceptable_loss_percentage=acceptable_loss,
                stop_loss_percentage=stop_loss,
                fallback_activated=fallback_activated
            )
            
            # Configurar valores iniciais
            sim_bot.simulation_balance = quantity
            sim_bot.simulation_stock_balance = 0
            sim_bot.initial_price = current_price
            
            # Registrar na lista de simulações ativas
            with bots_lock:
                simulation_bots[simulation_id] = sim_bot
                
            # Registrar um log
            add_log_message(f"Simulação iniciada para {operation_code} com modo {stock_code}", "info")
            
            return jsonify({
                'success': True,
                'simulation_id': simulation_id,
                'message': 'Simulação iniciada com sucesso',
                'initial_price': current_price
            })
            
        except Exception as e:
            logger.error(f"Erro ao configurar simulação: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        
    except Exception as e:
        logger.error(f"Erro ao iniciar simulação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/simulation/list', methods=['GET'])
@login_required
def list_simulations():
    try:
        # Retornar simulações ativas
        active_simulations = []
        with bots_lock:
            for sim_id, bot in simulation_bots.items():
                try:
                    active_simulations.append({
                        "id": sim_id,
                        "stock_code": bot.stock_code,
                        "operation_code": bot.operation_code,
                        "initial_price": bot.initial_price,
                        "quantity": bot.traded_quantity
                    })
                except Exception as e:
                    logger.error(f"Erro ao obter detalhes da simulação {sim_id}: {str(e)}")
        
        return jsonify({
            'success': True,
            'simulations': active_simulations
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar simulações: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/simulation/history/list', methods=['GET'])
@login_required
def list_simulation_history():
    try:
        # Obter histórico de simulações usando o modelo
        simulations = SimulationTradeModel.get_all_simulations()
        
        return jsonify({
            'success': True,
            'simulations': simulations
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar histórico de simulações: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/simulation/history/<simulation_id>', methods=['GET'])
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
        logger.error(f"Erro ao obter histórico da simulação {simulation_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Endpoint para logs em tempo real
@api_bp.route('/api/logs/stream')
@login_required
def logs_stream():
    def generate():
        # Cabeçalhos necessários para SSE (Server-Sent Events)
        yield "retry: 10000\n"
        
        # Enviar heartbeat para manter a conexão ativa
        while True:
            timestamp = datetime.now().isoformat()
            yield f"data: {{\"type\": \"heartbeat\", \"message\": \"Conexão ativa\", \"timestamp\": \"{timestamp}\"}}\n\n"
            time.sleep(10)  # Heartbeat a cada 10 segundos
            
    return Response(generate(), mimetype='text/event-stream')

# Função para inicializar o modelo de dados
def init_models():
    """Inicializa os modelos de dados."""
    try:
        # Inicializar modelos
        logger.info("Inicializando modelos de dados...")
        CoinModel.init_db()
        SimulationTradeModel.init_db()
        logger.info("Modelos inicializados com sucesso!")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar modelos: {str(e)}")
        return False

# Função para inicializar a API - usada pelo run.py
def init_api(app):
    """Inicializa a API e registra o blueprint no aplicativo Flask."""
    try:
        # Primeiro inicializamos os modelos
        init_models()
        
        # Função para injetar links de navegação
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
        
        # Registrar blueprint
        app.register_blueprint(api_bp)
        
        # Registrar endpoints para arquivos estáticos se necessário
        # Não precisamos disso pois já configuramos o static_folder no run.py
        
        logger.info(f"API inicializada com sucesso! Rotas registradas: {len(list(app.url_map.iter_rules()))}")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar API: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@api_bp.route('/api/simulation/<simulation_id>/execute', methods=['POST'])
@login_required
def execute_simulation(simulation_id):
    try:
        # Verificar se a simulação existe
        with bots_lock:
            if simulation_id not in simulation_bots:
                return jsonify({
                    'success': False,
                    'error': 'Simulação não encontrada'
                }), 404
            
            sim_bot = simulation_bots[simulation_id]
        
        # Obter preço atual (pode ser o preço real ou simulado)
        try:
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_SECRET_KEY')
            
            if api_key and api_secret and api_key != 'sua_api_key_aqui' and api_secret != 'sua_secret_key_aqui':
                client = Client(api_key, api_secret)
                ticker = client.get_ticker(symbol=sim_bot.operation_code)
                current_price = float(ticker['lastPrice'])
            else:
                # Simular variação de preço para testes
                base_price = sim_bot.initial_price
                variation = (float(time.time() % 100) / 100 - 0.5) * 0.02  # Variação de ±1%
                current_price = base_price * (1 + variation)
        except Exception as e:
            logger.error(f"Erro ao obter preço atual: {str(e)}")
            # Caso falhe, usar um preço com pequena variação baseado no último
            last_price = 1000  # valor padrão
            if hasattr(sim_bot, 'last_price') and sim_bot.last_price:
                last_price = sim_bot.last_price
            variation = (float(time.time() % 100) / 100 - 0.5) * 0.01  # Variação de ±0.5%
            current_price = last_price * (1 + variation)
        
        # Atualizar o preço atual do bot
        sim_bot.last_price = current_price
        
        # Simular decisão de compra ou venda
        current_position = False
        if hasattr(sim_bot, 'last_operation') and sim_bot.last_operation:
            current_position = sim_bot.last_operation == "BUY"  # True se comprado, False se vendido
        
        # Definir uma operação de acordo com regras simples
        decision = None
        trade_type = None
        
        # Se não tivermos uma operação anterior, começar com compra
        if not hasattr(sim_bot, 'last_operation') or not sim_bot.last_operation:
            decision = "BUY"
            trade_type = "BUY"
        else:
            # Alternar entre compra e venda para simular operações
            decision = "SELL" if sim_bot.last_operation == "BUY" else "BUY"
            trade_type = decision
        
        # Aplicar a decisão
        sim_bot.last_operation = decision
        
        # Calcular valores (simplificados para simulação)
        quantity = sim_bot.traded_quantity
        total_value = current_price * quantity
        
        # Registrar operação no histórico
        trade_id = SimulationTradeModel.register_trade(
            simulation_id=simulation_id,
            operation_code=sim_bot.operation_code,
            trade_type=trade_type,
            price=current_price,
            quantity=quantity,
            total_value=total_value
        )
        
        # Atualizar estatísticas do bot
        if trade_type == "BUY":
            sim_bot.simulation_balance -= total_value
            sim_bot.simulation_stock_balance += quantity
            sim_bot.buy_price = current_price
            # Também atualizar last_buy_price para manter consistência
            sim_bot.last_buy_price = current_price
        else:  # SELL
            sim_bot.simulation_balance += total_value
            sim_bot.simulation_stock_balance -= quantity
            sim_bot.sell_price = current_price
            # Também atualizar last_sell_price para manter consistência
            sim_bot.last_sell_price = current_price
        
        # Calcular lucro/prejuízo
        profit_loss = 0
        if hasattr(sim_bot, 'buy_price') and sim_bot.buy_price:
            if hasattr(sim_bot, 'sell_price') and sim_bot.sell_price:
                price_diff = sim_bot.sell_price - sim_bot.buy_price
                profit_loss = price_diff * quantity
        
        return jsonify({
            'success': True,
            'trade_id': trade_id,
            'simulation_id': simulation_id,
            'position': 'Comprado' if sim_bot.last_operation == 'BUY' else 'Vendido',
            'price': current_price,
            'quantity': quantity,
            'total_value': total_value,
            'profit_loss': profit_loss,
            'message': f'Simulação executada com sucesso. Operação: {trade_type}'
        })
        
    except Exception as e:
        logger.error(f"Erro ao executar passo da simulação {simulation_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/api/simulation/<simulation_id>/stop', methods=['POST'])
@login_required
def stop_simulation(simulation_id):
    try:
        # Verificar se a simulação existe
        with bots_lock:
            if simulation_id not in simulation_bots:
                return jsonify({
                    'success': False,
                    'error': 'Simulação não encontrada'
                }), 404
            
            sim_bot = simulation_bots[simulation_id]
        
        # Obter preço atual para finalização
        try:
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_SECRET_KEY')
            
            if api_key and api_secret and api_key != 'sua_api_key_aqui' and api_secret != 'sua_secret_key_aqui':
                client = Client(api_key, api_secret)
                ticker = client.get_ticker(symbol=sim_bot.operation_code)
                current_price = float(ticker['lastPrice'])
            else:
                # Usar preço atual armazenado ou base
                current_price = sim_bot.last_price if hasattr(sim_bot, 'last_price') and sim_bot.last_price else sim_bot.initial_price
        except Exception as e:
            logger.error(f"Erro ao obter preço final: {str(e)}")
            current_price = sim_bot.last_price if hasattr(sim_bot, 'last_price') and sim_bot.last_price else 1000
        
        # Se o bot estiver comprado, realizar venda final para fechar posição
        if hasattr(sim_bot, 'last_operation') and sim_bot.last_operation == "BUY" and sim_bot.simulation_stock_balance > 0:
            quantity = sim_bot.simulation_stock_balance
            total_value = current_price * quantity
            
            # Registrar operação final
            SimulationTradeModel.register_trade(
                simulation_id=simulation_id,
                operation_code=sim_bot.operation_code,
                trade_type='SELL_FINAL',
                price=current_price,
                quantity=quantity,
                total_value=total_value
            )
            
            # Atualizar estatísticas
            sim_bot.simulation_balance += total_value
            sim_bot.simulation_stock_balance = 0
            sim_bot.sell_price = current_price
            sim_bot.last_sell_price = current_price
            sim_bot.last_operation = "SELL"
        
        # Obter todas as operações
        trades = SimulationTradeModel.get_trades_by_simulation(simulation_id)
        
        # Calcular estatísticas
        buy_trades = [t for t in trades if t['trade_type'] in ['BUY', 'BUY_MARKET']]
        sell_trades = [t for t in trades if t['trade_type'] in ['SELL', 'SELL_MARKET', 'SELL_FINAL']]
        
        total_buy_value = sum(float(t['total_value']) for t in buy_trades)
        total_sell_value = sum(float(t['total_value']) for t in sell_trades)
        
        profit_loss = total_sell_value - total_buy_value
        profit_loss_percentage = 0
        
        if total_buy_value > 0:
            profit_loss_percentage = (profit_loss / total_buy_value) * 100
        
        # Registrar resultados finais
        results = {
            'buys': len(buy_trades),
            'sells': len(sell_trades),
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'profit_loss': profit_loss,
            'profit_loss_percentage': profit_loss_percentage,
            'stock_balance': sim_bot.simulation_stock_balance,
            'wallet_balance': sim_bot.simulation_balance,
            'current_price': current_price,
            'initial_price': sim_bot.initial_price
        }
        
        # Remover o bot de simulação da lista
        with bots_lock:
            del simulation_bots[simulation_id]
        
        # Registrar log
        add_log_message(f"Simulação {simulation_id} finalizada com resultado: {profit_loss:.2f} ({profit_loss_percentage:.2f}%)", 
                        "success" if profit_loss >= 0 else "danger")
        
        return jsonify({
            'success': True,
            'simulation_id': simulation_id,
            'message': 'Simulação finalizada com sucesso',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erro ao finalizar simulação {simulation_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Endpoint para listar moedas da Binance
@api_bp.route('/api/binance/coins', methods=['GET'])
@login_required
def get_binance_coins():
    try:
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret or api_key == 'sua_api_key_aqui' or api_secret == 'sua_secret_key_aqui':
            return jsonify({
                "success": False,
                "message": "Chaves da API Binance não configuradas"
            }), 400
        
        # Tipo de moeda solicitado (opcional)
        coin_type = request.args.get('type', None)
        
        # Página e limite para paginação
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100))  # Limitar a 100 moedas por página
        
        client = Client(api_key, api_secret)
        
        # Obter informações de todos os símbolos
        exchange_info = client.get_exchange_info()
        symbols = exchange_info['symbols']
        
        # Obter preços atuais
        tickers = client.get_all_tickers()
        price_map = {ticker['symbol']: ticker['price'] for ticker in tickers}
        
        # Obter lista de moedas de cada tipo
        all_coins = []
        
        # Categorizar moedas
        categories = {
            'USDT': [],    # Stablecoins com USDT
            'BTC': [],     # Criptomoedas cotadas em BTC
            'ETH': [],     # Criptomoedas cotadas em ETH
            'BNB': [],     # Criptomoedas cotadas em BNB
            'BUSD': [],    # Stablecoins com BUSD
            'FIAT': [],    # Moedas fiduciárias
            'OTHER': []    # Outras moedas
        }
        
        # Lista de principais memecoins conhecido (pode atualizar conforme necessário)
        memecoins = ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BABYDOGE', 'ELON', 'SAMO', 'BONK', 'WOJAK']
        
        for symbol_info in symbols:
            if symbol_info['status'] != 'TRADING':
                continue  # Pular símbolos que não estão em negociação
                
            symbol = symbol_info['symbol']
            base_asset = symbol_info['baseAsset']
            quote_asset = symbol_info['quoteAsset']
            
            # Determinar categoria
            category = 'OTHER'
            if quote_asset == 'USDT':
                category = 'USDT'
            elif quote_asset == 'BTC':
                category = 'BTC'
            elif quote_asset == 'ETH':
                category = 'ETH'
            elif quote_asset == 'BNB':
                category = 'BNB'
            elif quote_asset == 'BUSD':
                category = 'BUSD'
            elif quote_asset in ['EUR', 'USD', 'GBP', 'AUD', 'BRL']:
                category = 'FIAT'
            
            # Verificar se é uma memecoin
            is_memecoin = base_asset in memecoins
            
            # Criar objeto de moeda
            coin_data = {
                'symbol': symbol,
                'baseAsset': base_asset,
                'quoteAsset': quote_asset,
                'price': price_map.get(symbol, "0"),
                'category': category,
                'is_memecoin': is_memecoin
            }
            
            # Adicionar à categoria correspondente
            categories[category].append(coin_data)
            
            # Adicionar à lista completa
            all_coins.append(coin_data)
        
        # Filtrar por tipo se solicitado
        if coin_type:
            if coin_type == 'memecoin':
                filtered_coins = [coin for coin in all_coins if coin['is_memecoin']]
            else:
                filtered_coins = categories.get(coin_type.upper(), [])
        else:
            filtered_coins = all_coins
        
        # Aplicar paginação
        total_count = len(filtered_coins)
        total_pages = (total_count + limit - 1) // limit
        
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, total_count)
        
        paginated_coins = filtered_coins[start_idx:end_idx]
        
        return jsonify({
            "success": True,
            "coins": paginated_coins,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_items": total_count,
                "total_pages": total_pages
            },
            "categories": {
                "usdt": len(categories['USDT']),
                "btc": len(categories['BTC']),
                "eth": len(categories['ETH']),
                "bnb": len(categories['BNB']),
                "busd": len(categories['BUSD']),
                "fiat": len(categories['FIAT']),
                "other": len(categories['OTHER']),
                "memecoin": sum(1 for coin in all_coins if coin['is_memecoin'])
            }
        })
    except BinanceAPIException as e:
        return jsonify({
            "success": False,
            "message": f"Erro na API da Binance: {e.message}",
            "code": e.code
        }), 400
    except Exception as e:
        logger.error(f"Erro ao obter moedas: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erro ao obter moedas: {str(e)}"
        }), 500 