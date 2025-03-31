from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context, render_template, redirect
import threading
import json
import os
import time
import datetime
from dotenv import load_dotenv
from modules.BinanceRobot import BinanceTraderBot
from binance.client import Client
from Models.AssetStartModel import AssetStartModel
from Models.CoinModel import CoinModel
from Models.SimulationTradeModel import SimulationTradeModel
import logging
import copy
from flask_cors import CORS
from auth import init_auth
from flask_login import login_required, current_user
import decimal
import sqlite3

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
            static_folder="static",
            template_folder="templates")
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

# Configurações do robô
VOLATILITY_FACTOR = 0.5
ACCEPTABLE_LOSS_PERCENTAGE = 0
STOP_LOSS_PERCENTAGE = 3
FALLBACK_ACTIVATED = True
CANDLE_PERIOD = Client.KLINE_INTERVAL_5MINUTE
TEMPO_ENTRE_TRADES = 5 * 60
DELAY_ENTRE_ORDENS = 15 * 60

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
        if not self.simulation_mode:
            return super().sellMarketOrder()
        
        if self.simulation_stock_balance <= 0:
            return False
            
        current_price = float(self.stock_data["close_price"].iloc[-1])
        quantity_to_sell = min(self.traded_quantity, self.simulation_stock_balance)
        
        trade = {
            "type": "SELL",
            "price": current_price,
            "quantity": quantity_to_sell,
            "timestamp": self.getTimestamp(),
            "total_value": current_price * quantity_to_sell
        }
        
        self.simulation_trades.append(trade)
        self.last_sell_price = current_price
        self.simulation_stock_balance -= quantity_to_sell
        
        if self.simulation_stock_balance <= 0:
            self.actual_trade_position = False
        
        # Registrar a operação no banco de dados
        trade_id = SimulationTradeModel.register_trade(
            simulation_id=self.simulation_id,
            operation_code=self.operation_code,
            trade_type="SELL",
            price=current_price,
            quantity=quantity_to_sell,
            total_value=current_price * quantity_to_sell,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        log_msg = f"[SIMULAÇÃO] Ordem de venda: {self.operation_code} - Preço: {current_price}, Quantidade: {quantity_to_sell}"
        add_log_message(log_msg, "sell")
        logging.info(f"[SIMULAÇÃO] Ordem de venda: {json.dumps(trade)}")
        return True
    
    def buyLimitedOrder(self, price=0):
        if not self.simulation_mode:
            return super().buyLimitedOrder(price)
            
        # Na simulação tratamos como compra a mercado para simplificar
        return self.buyMarketOrder()
    
    def sellLimitedOrder(self, price=0):
        if not self.simulation_mode:
            return super().sellLimitedOrder(price)
            
        # Na simulação tratamos como venda a mercado para simplificar
        return self.sellMarketOrder()
    
    def getActualTradePosition(self):
        if not self.simulation_mode:
            return super().getActualTradePosition()
            
        return self.simulation_stock_balance > 0
    
    def get_simulation_results(self):
        if len(self.simulation_trades) == 0:
            return {
                "status": "no_trades",
                "trades": [],
                "profit_loss": 0,
                "stock_balance": self.simulation_stock_balance
            }
        
        # Buscar operações do banco de dados para resultados mais precisos
        db_trades = SimulationTradeModel.get_trades_by_simulation(self.simulation_id)
        
        if db_trades:
            buys = [t for t in db_trades if t["trade_type"] == "BUY"]
            sells = [t for t in db_trades if t["trade_type"] == "SELL"]
            
            total_buy_value = sum(t["total_value"] for t in buys)
            total_sell_value = sum(t["total_value"] for t in sells)
        else:
            # Fallback para os dados em memória
            buys = [t for t in self.simulation_trades if t["type"] == "BUY"]
            sells = [t for t in self.simulation_trades if t["type"] == "SELL"]
            
            total_buy_value = sum(t["total_value"] for t in buys)
            total_sell_value = sum(t["total_value"] for t in sells)
        
        # Adiciona valor atual das moedas que ainda estão em posse
        current_price = float(self.stock_data["close_price"].iloc[-1])
        current_holdings_value = current_price * self.simulation_stock_balance
        
        profit_loss = total_sell_value + current_holdings_value - total_buy_value
        profit_loss_percentage = 0
        
        if total_buy_value > 0:
            profit_loss_percentage = (profit_loss / total_buy_value) * 100
        
        return {
            "status": "success",
            "trades": db_trades if db_trades else self.simulation_trades,
            "buys": len(buys),
            "sells": len(sells),
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "current_holdings_value": current_holdings_value,
            "profit_loss": profit_loss,
            "profit_loss_percentage": profit_loss_percentage,
            "stock_balance": self.simulation_stock_balance,
            "current_price": current_price,
            "initial_price": self.initial_price
        }

# Função para criar e executar uma instância do robô
def create_and_run_bot(asset_model, is_simulation=False):
    if is_simulation:
        bot = SimulationTraderBot(
            stock_code=asset_model.stockCode,
            operation_code=asset_model.operationCode,
            traded_quantity=asset_model.tradedQuantity,
            traded_percentage=asset_model.tradedPercentage,
            candle_period=asset_model.candlePeriod,
            volatility_factor=asset_model.volatilityFactor,
            time_to_trade=asset_model.tempoEntreTrades,
            delay_after_order=asset_model.delayEntreOrdens,
            acceptable_loss_percentage=asset_model.acceptableLossPercentage,
            stop_loss_percentage=asset_model.stopLossPercentage,
            fallback_activated=asset_model.fallBackActivated
        )
    else:
        bot = BinanceTraderBot(
            stock_code=asset_model.stockCode,
            operation_code=asset_model.operationCode,
            traded_quantity=asset_model.tradedQuantity,
            traded_percentage=asset_model.tradedPercentage,
            candle_period=asset_model.candlePeriod,
            volatility_factor=asset_model.volatilityFactor,
            time_to_trade=asset_model.tempoEntreTrades,
            delay_after_order=asset_model.delayEntreOrdens,
            acceptable_loss_percentage=asset_model.acceptableLossPercentage,
            stop_loss_percentage=asset_model.stopLossPercentage,
            fallback_activated=asset_model.fallBackActivated
        )
    
    return bot

# Rotas da API
@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    with bots_lock:
        active_bots = len(running_bots)
        active_simulations = len(simulation_bots)
    
    return jsonify({
        'status': 'online',
        'active_bots': active_bots,
        'active_simulations': active_simulations,
        'server_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/wallet', methods=['GET'])
@login_required
def get_wallet():
    try:
        # Criar uma instância temporária do cliente Binance
        client = Client(os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_SECRET_KEY'))
        
        # Obter informações da conta
        account_info = client.get_account()
        
        # Obter todas as moedas registradas
        coins = CoinModel.get_all(active_only=True)
        coin_symbols = {coin['trading_pair']: coin for coin in coins}
        
        # Filtrar saldos com valor maior que zero
        balances = []
        total_usdt_value = 0
        
        for balance in account_info['balances']:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                # Tentar obter o valor atual em USDT
                usdt_value = 0
                price = 0
                
                try:
                    if asset != 'USDT':
                        # Tentar obter preço atual do par com USDT
                        ticker = client.get_symbol_ticker(symbol=f"{asset}USDT")
                        if ticker:
                            price = float(ticker['price'])
                            usdt_value = total * price
                    else:
                        # USDT tem valor 1:1
                        price = 1
                        usdt_value = total
                        
                    # Adicionar ao total
                    total_usdt_value += usdt_value
                except:
                    # Se não conseguir obter o preço, mantém como 0
                    pass
                
                # Verificar se é uma moeda registrada no sistema
                is_registered = False
                coin_info = None
                
                for pair, coin in coin_symbols.items():
                    if pair.startswith(asset):
                        is_registered = True
                        coin_info = coin
                        break
                
                # Adicionar à lista de saldos
                balances.append({
                    'asset': asset,
                    'free': free,
                    'locked': locked,
                    'total': total,
                    'price_usdt': price,
                    'usdt_value': usdt_value,
                    'is_registered': is_registered,
                    'coin_info': coin_info
                })
        
        # Ordenar por valor em USDT (maiores primeiro)
        balances.sort(key=lambda x: x['usdt_value'], reverse=True)
        
        return jsonify({
            'balances': balances,
            'total_usdt_value': total_usdt_value,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logging.error(f"Erro ao obter carteira: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/list', methods=['GET'])
@login_required
def list_bots():
    try:
        bots_list = []
        
        with bots_lock:
            for bot_id, bot_data in running_bots.items():
                bot = bot_data['bot']
                
                # Garante que os dados estão atualizados
                bot.updateAllData(verbose=False)
                
                bots_list.append({
                    'id': bot_id,
                    'operation_code': bot.operation_code,
                    'stock_code': bot.stock_code,
                    'actual_trade_position': bot.actual_trade_position,
                    'last_buy_price': bot.last_buy_price,
                    'last_sell_price': bot.last_sell_price,
                    'stock_balance': bot.last_stock_account_balance,
                    'created_at': bot_data['created_at'],
                    'last_execution': bot_data.get('last_execution', 'Nunca')
                })
        
        return jsonify({'success': True, 'bots': bots_list})
        
    except Exception as e:
        logging.error(f"Erro ao listar bots: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/list', methods=['GET'])
@login_required
def list_simulations():
    try:
        sims_list = []
        
        with bots_lock:
            for sim_id, sim_data in simulation_bots.items():
                sims_list.append({
                    'id': sim_id,
                    'operation_code': sim_data['operation_code'],
                    'stock_code': sim_data['stock_code'],
                    'created_at': sim_data['created_at'],
                    'last_executed': sim_data.get('last_executed', 'Nunca')
                })
        
        return jsonify({'success': True, 'simulations': sims_list})
        
    except Exception as e:
        logging.error(f"Erro ao listar simulações: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/start', methods=['POST'])
@login_required
def start_bot():
    try:
        data = request.get_json()
        
        # Verifica se os dados necessários foram fornecidos
        if not all(k in data for k in ['stock_code', 'operation_code', 'quantity']):
            return jsonify({'error': 'Dados incompletos'}), 400
        
        stock_code = data['stock_code']
        operation_code = data['operation_code']
        quantity = float(data['quantity'])
        volatility_factor = float(data.get('volatility_factor', VOLATILITY_FACTOR))
        stop_loss = float(data.get('stop_loss', STOP_LOSS_PERCENTAGE))
        acceptable_loss = float(data.get('acceptable_loss', ACCEPTABLE_LOSS_PERCENTAGE))
        fallback_activated = data.get('fallback_activated', FALLBACK_ACTIVATED)
        
        # Verifica se já existe um bot para este par de moedas
        with bots_lock:
            for bot_id, bot_data in running_bots.items():
                if bot_data['bot'].operation_code == operation_code:
                    return jsonify({'error': f'Já existe um bot em execução para {operation_code}'}), 400
        
        # Verifica saldo disponível antes de iniciar o bot
        try:
            client = Client(os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_SECRET_KEY'))
            account_info = client.get_account()
            
            # Determinar a moeda base (ex: USDT em BTCUSDT)
            base_currency = operation_code.replace(stock_code, '')
            
            # Encontrar o saldo disponível
            base_balance = 0
            for balance in account_info['balances']:
                if balance['asset'] == base_currency:
                    base_balance = float(balance['free'])
                    break
            
            # Obter preço atual para estimar o custo
            ticker = client.get_symbol_ticker(symbol=operation_code)
            current_price = float(ticker['price'])
            estimated_cost = quantity * current_price
            
            if base_balance < estimated_cost:
                error_msg = f"Saldo insuficiente para iniciar o bot. Disponível: {base_balance:.2f} {base_currency}, Necessário: {estimated_cost:.2f} {base_currency}"
                logging.error(error_msg)
                add_log_message(f"ERRO: {error_msg}", "error")
                return jsonify({'success': False, 'error': error_msg}), 400
        except Exception as e:
            logging.error(f"Erro ao verificar saldo: {str(e)}")
            # Continua o processo mesmo se houver erro na verificação
        
        # Cria o modelo de dados do bot com os parâmetros obrigatórios
        asset_model = AssetStartModel(
            stockCode=stock_code,
            operationCode=operation_code,
            tradedQuantity=quantity,
            candlePeriod=CANDLE_PERIOD,
            volatilityFactor=volatility_factor,
            acceptableLossPercentage=acceptable_loss,
            stopLossPercentage=stop_loss,
            fallBackActivated=fallback_activated,
            tempoEntreTrades=TEMPO_ENTRE_TRADES,
            delayEntreOrdens=DELAY_ENTRE_ORDENS,
            tradedPercentage=100
        )
        
        # Cria e inicia o bot
        bot_instance = create_and_run_bot(asset_model)
        bot_id = f"bot_{time.time()}"
        
        with bots_lock:
            running_bots[bot_id] = {
                'id': bot_id,
                'bot': bot_instance,
                'thread': None,
                'active': True,
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Inicia a thread do bot
            bot_thread = threading.Thread(
                target=bot_loop,
                args=(bot_instance, bot_id),
                daemon=True
            )
            running_bots[bot_id]['thread'] = bot_thread
            bot_thread.start()
            
        logging.info(f"Bot iniciado para {operation_code}")
        add_log_message(f"Bot iniciado para {operation_code}", "info")
        return jsonify({'success': True, 'bot_id': bot_id})
    
    except Exception as e:
        logging.error(f"Erro ao iniciar bot: {str(e)}")
        add_log_message(f"ERRO ao iniciar bot: {str(e)}", "error")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/stop/<bot_id>', methods=['POST'])
@login_required
def stop_bot(bot_id):
    try:
        with bots_lock:
            if bot_id not in running_bots:
                return jsonify({'error': 'Bot não encontrado'}), 404
            
            bot_data = running_bots[bot_id]
            bot_data['active'] = False
            operation_code = bot_data['bot'].operation_code
            
            # Aguardar a thread terminar naturalmente
            # Não precisamos join aqui, a thread sairá na próxima verificação
            
            del running_bots[bot_id]
        
        logging.info(f"Bot parado para {operation_code}")
        add_log_message(f"Bot parado para {operation_code}", "info")
        return jsonify({'success': True})
    
    except Exception as e:
        logging.error(f"Erro ao parar bot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/start', methods=['POST'])
@login_required
def start_simulation():
    try:
        data = request.get_json()
        
        # Valida os dados de entrada
        if not data or not 'stock_code' in data or not 'operation_code' in data or not 'quantity' in data:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        stock_code = data['stock_code']
        operation_code = data['operation_code']
        quantity = float(data['quantity'])
        volatility_factor = float(data.get('volatility_factor', VOLATILITY_FACTOR))
        stop_loss = float(data.get('stop_loss', STOP_LOSS_PERCENTAGE))
        acceptable_loss = float(data.get('acceptable_loss', ACCEPTABLE_LOSS_PERCENTAGE))
        fallback_activated = data.get('fallback_activated', FALLBACK_ACTIVATED)
        
        # Cria um ID único para a simulação
        simulation_id = f"sim_{int(time.time())}_{operation_code}"
        
        # Cria uma instância do robô de simulação
        sim_bot = SimulationTraderBot(
            stock_code=stock_code,
            operation_code=operation_code,
            traded_quantity=quantity,
            traded_percentage=100,  # Na simulação, usamos 100% do valor
            candle_period=CANDLE_PERIOD,
            volatility_factor=volatility_factor,
            acceptable_loss_percentage=acceptable_loss,
            stop_loss_percentage=stop_loss,
            fallback_activated=fallback_activated
        )
        
        # Adiciona o ID da simulação ao bot
        sim_bot.simulation_id = simulation_id
        
        # Armazena a simulação no dicionário
        with bots_lock:
            simulation_bots[simulation_id] = {
                'bot': sim_bot,
                'stock_code': stock_code,
                'operation_code': operation_code,
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        log_msg = f"[SIMULAÇÃO] Nova simulação iniciada: {operation_code} (ID: {simulation_id})"
        add_log_message(log_msg, "simulation")
        logging.info(log_msg)
        
        return jsonify({
            'success': True,
            'simulation_id': simulation_id,
            'message': f'Simulação iniciada para {operation_code}'
        })
        
    except Exception as e:
        logging.error(f"Erro ao iniciar simulação: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<sim_id>/execute', methods=['POST'])
@login_required
def execute_simulation_step(sim_id):
    try:
        with bots_lock:
            if sim_id not in simulation_bots:
                return jsonify({'error': 'Simulação não encontrada'}), 404
            
            sim_data = simulation_bots[sim_id]
            sim_bot = sim_data['bot']
            
            # Executa um passo da simulação
            add_log_message(f"Executando passo da simulação {sim_id} para {sim_bot.operation_code}", "simulation")
            result = sim_bot.executeRobotTradeLogic()
            
            # Atualiza dados da simulação
            sim_data['last_executed'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Log dos resultados
            if result:
                if sim_bot.getActualTradePosition():
                    add_log_message(f"[RESULTADO] {sim_bot.operation_code} - Comprado a {sim_bot.last_buy_price}", "result")
                else:
                    add_log_message(f"[RESULTADO] {sim_bot.operation_code} - Vendido a {sim_bot.last_sell_price}", "result")
            
        return jsonify({
            'success': True, 
            'position': 'Comprado' if sim_bot.getActualTradePosition() else 'Vendido',
            'last_price': sim_bot.stock_data["close_price"].iloc[-1] if not sim_bot.stock_data.empty else 0
        })
    
    except Exception as e:
        logging.error(f"Erro ao executar simulação: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/<sim_id>/results', methods=['GET'])
@login_required
def get_simulation_results(sim_id):
    try:
        with bots_lock:
            if sim_id not in simulation_bots:
                return jsonify({'error': 'Simulação não encontrada'}), 404
            
            sim_data = simulation_bots[sim_id]
            sim_bot = sim_data['bot']
            
            results = sim_bot.get_simulation_results()
            
            # Adiciona informações sobre a simulação
            results['simulation_id'] = sim_id
            results['stock_code'] = sim_data['stock_code']
            results['operation_code'] = sim_data['operation_code']
            results['created_at'] = sim_data['created_at']
            results['position'] = 'Comprado' if sim_bot.getActualTradePosition() else 'Vendido'
            
        return jsonify(results)
    
    except Exception as e:
        logging.error(f"Erro ao obter resultados da simulação: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/<sim_id>/stop', methods=['POST'])
@login_required
def stop_simulation(sim_id):
    try:
        with bots_lock:
            if sim_id not in simulation_bots:
                return jsonify({'error': 'Simulação não encontrada'}), 404
            
            sim_data = simulation_bots[sim_id]
            operation_code = sim_data['bot'].operation_code
            
            # Obtém os resultados finais antes de remover
            results = sim_data['bot'].get_simulation_results()
            
            # Remove a simulação
            del simulation_bots[sim_id]
        
        logging.info(f"Simulação finalizada para {operation_code}")
        add_log_message(f"Simulação finalizada para {operation_code}", "info")
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        logging.error(f"Erro ao parar simulação: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Endpoint para streaming de logs em tempo real
@app.route('/api/logs/stream', methods=['GET'])
@login_required
def stream_logs():
    def generate():
        # Envia os logs existentes primeiro
        with log_lock:
            # Cria uma cópia para não bloquear o lock enquanto envia
            existing_logs = copy.deepcopy(log_messages)
        
        for log in existing_logs:
            yield f"data: {json.dumps(log)}\n\n"
        
        # Ponto de início para novos logs
        last_index = len(existing_logs)
        
        # Enviar heartbeat para manter a conexão aberta
        heartbeat_interval = 15  # segundos
        last_heartbeat = time.time()
        
        while True:
            # Verifica se há novos logs
            with log_lock:
                if len(log_messages) > last_index:
                    # Há novos logs para enviar
                    for i in range(last_index, len(log_messages)):
                        yield f"data: {json.dumps(log_messages[i])}\n\n"
                    last_index = len(log_messages)
                    last_heartbeat = time.time()  # Atualiza o tempo do último heartbeat
            
            # Enviar heartbeat periodicamente
            if time.time() - last_heartbeat > heartbeat_interval:
                heartbeat = {
                    "message": "[HEARTBEAT] Conexão ativa",
                    "timestamp": time.time() * 1000,
                    "type": "heartbeat"
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                last_heartbeat = time.time()
            
            time.sleep(0.5)  # Pequena pausa para não sobrecarregar
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    with log_lock:
        return jsonify(log_messages)

# Rotas para gerenciamento de moedas
@app.route('/api/coins', methods=['GET'])
@login_required
def get_coins():
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    coins = CoinModel.get_all(active_only=active_only)
    return jsonify(coins)

@app.route('/api/coins/<int:coin_id>', methods=['GET'])
@login_required
def get_coin(coin_id):
    coin = CoinModel.get_by_id(coin_id)
    if not coin:
        return jsonify({'error': 'Moeda não encontrada'}), 404
    return jsonify(coin)

@app.route('/api/coins', methods=['POST'])
@login_required
def add_coin():
    if not current_user.is_admin:
        return jsonify({'error': 'Apenas administradores podem adicionar moedas'}), 403
        
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'symbol', 'base_currency', 'quote_currency', 'trading_pair']):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    result = CoinModel.add_coin(
        name=data['name'],
        symbol=data['symbol'],
        base_currency=data['base_currency'],
        quote_currency=data['quote_currency'],
        trading_pair=data['trading_pair'],
        description=data.get('description', ''),
        is_active=data.get('is_active', True)
    )
    
    if result['success']:
        return jsonify({'success': True, 'id': result['id']})
    else:
        return jsonify({'error': result['error']}), 400

@app.route('/api/coins/<int:coin_id>', methods=['PUT'])
@login_required
def update_coin(coin_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Apenas administradores podem editar moedas'}), 403
        
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'symbol', 'base_currency', 'quote_currency', 'trading_pair']):
        return jsonify({'error': 'Dados incompletos'}), 400
    
    # Verifica se a moeda existe
    coin = CoinModel.get_by_id(coin_id)
    if not coin:
        return jsonify({'error': 'Moeda não encontrada'}), 404
    
    result = CoinModel.update_coin(
        coin_id=coin_id,
        name=data['name'],
        symbol=data['symbol'],
        base_currency=data['base_currency'],
        quote_currency=data['quote_currency'],
        trading_pair=data['trading_pair'],
        description=data.get('description', ''),
        is_active=data.get('is_active', True)
    )
    
    if result['success']:
        return jsonify({'success': True})
    else:
        return jsonify({'error': result['error']}), 400

@app.route('/api/coins/<int:coin_id>', methods=['DELETE'])
@login_required
def delete_coin(coin_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Apenas administradores podem excluir moedas'}), 403
    
    # Verifica se a moeda existe
    coin = CoinModel.get_by_id(coin_id)
    if not coin:
        return jsonify({'error': 'Moeda não encontrada'}), 404
    
    # Verifica se a moeda está sendo usada em alguma operação
    # Aqui você deveria verificar se há operações com esta moeda
    
    result = CoinModel.delete_coin(coin_id)
    
    if result['success']:
        return jsonify({'success': True})
    else:
        return jsonify({'error': result['error']}), 400

# Rota para servir arquivos estáticos
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Função principal para execução do robô
def bot_loop(bot_instance, bot_id):
    try:
        while True:
            # Verifica se o bot ainda está ativo
            with bots_lock:
                if bot_id not in running_bots or not running_bots[bot_id]['active']:
                    break
            
            # Executa a lógica do bot
            try:
                add_log_message(f"Executando ciclo de negociação para {bot_instance.operation_code}")
                bot_instance.executeRobotTradeLogic()
                
                # Atualiza status na lista de bots ativos
                with bots_lock:
                    if bot_id in running_bots:
                        running_bots[bot_id]['last_execution'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                # Aguarda o tempo configurado para a próxima execução
                time.sleep(bot_instance.time_to_sleep)
                
            except Exception as e:
                logging.error(f"Erro ao executar bot {bot_id}: {str(e)}")
                add_log_message(f"Erro no bot {bot_instance.operation_code}: {str(e)}")
                time.sleep(60)  # Em caso de erro, espera 1 minuto antes de tentar novamente
    except Exception as e:
        logging.error(f"Erro fatal no bot {bot_id}: {str(e)}")
        add_log_message(f"Erro fatal no bot {bot_instance.operation_code}: {str(e)}")
    finally:
        # Garante que o bot seja removido da lista ao encerrar
        with bots_lock:
            if bot_id in running_bots:
                del running_bots[bot_id]
        add_log_message(f"Bot {bot_instance.operation_code} finalizado")

# Rotas da aplicação web
# Estas rotas são definidas em run_api.py e run_api_local.py
# As definições abaixo estão comentadas para evitar conflitos
'''
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/logs')
@login_required
def logs_page():
    return render_template('logs.html')

@app.route('/coins')
@login_required
def coins_page():
    if not current_user.is_admin:
        return redirect('/')
    return render_template('coins.html')
'''

@app.route('/simulation/history')
@login_required
def simulation_history_page():
    return render_template('simulation_history.html')

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

# Adicionar link para o menu de navegação
@app.context_processor
def inject_nav_links():
    return {
        'nav_links': [
            {'title': 'Dashboard', 'url': '/', 'icon': 'dashboard'},
            {'title': 'Logs', 'url': '/logs', 'icon': 'receipt_long'},
            {'title': 'Histórico de Simulações', 'url': '/simulation/history', 'icon': 'insights'},
            {'title': 'Moedas', 'url': '/coins', 'icon': 'currency_bitcoin', 'admin_only': True}
        ]
    }

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000) 