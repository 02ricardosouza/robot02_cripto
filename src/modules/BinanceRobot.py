#!/usr/bin/env python3
"""
Módulo para operações com a API da Binance.
Implementa um robô de trading para executar estratégias automatizadas.
"""

import os
import time
from datetime import datetime
import logging
import math

from dotenv import load_dotenv
import pandas as pd
from binance.client import Client
from binance.enums import *
from binance.enums import SIDE_SELL, ORDER_TYPE_STOP_LOSS_LIMIT
from binance.exceptions import BinanceAPIException

from modules.BinanceClient import BinanceClient
from modules.TraderOrder import TraderOrder
from modules.Logger import *
from strategies import runStrategies
from indicators import Indicators


load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")




# ------------------------------------------------------------------

# Classe Principal
class BinanceTraderBot():

    # --------------------------------------------------------------
    # Parâmetros da classe sem valor inicial
    last_trade_decision = None # Última decisão de posição (False = Vender | True = Comprar)
    last_buy_price = 0 # Último valor de ordem de COMPRA executado
    last_sell_price = 0 # Ùltimo valor de ordem de VENDA executada
    open_orders = []
    partial_quantity_discount = 0 # Valor que já foi executado e que será descontado da quantidade, caso uma ordem não seja completamente executada
    tick_size : float
    step_size : float

    # Construtor
    def __init__ (self, stock_code, operation_code, traded_quantity, traded_percentage, candle_period, volatility_factor = 0.5, time_to_trade = 30*60, delay_after_order = 60*60, acceptable_loss_percentage = 0.5, stop_loss_percentage = 5, fallback_activated = True):

        print('------------------------------------------------')
        print(f'🤖 Robo Trader iniciando para {stock_code}/{operation_code}...')
        print(f'Parâmetros recebidos:')
        print(f'- stock_code: {stock_code}')
        print(f'- operation_code: {operation_code}')
        print(f'- traded_quantity: {traded_quantity}')
        print(f'- traded_percentage: {traded_percentage}')
        print(f'- candle_period: {candle_period}')
        print(f'- volatility_factor: {volatility_factor}')
        print(f'- time_to_trade: {time_to_trade}')
        print(f'- delay_after_order: {delay_after_order}')
        print(f'- acceptable_loss_percentage: {acceptable_loss_percentage}')
        print(f'- stop_loss_percentage: {stop_loss_percentage}')
        print(f'- fallback_activated: {fallback_activated}')

        self.stock_code = stock_code # Código princial da stock negociada (ex: 'BTC')
        self.operation_code = operation_code # Código negociado/moeda (ex:'BTCBRL')
        self.traded_quantity = traded_quantity # Quantidade incial que será operada
        self.traded_percentage = traded_percentage # Porcentagem do total da carteira, que será negociada
        self.candle_period = candle_period # Período levado em consideração para operação (ex: 15min)
        self.volatility_factor = volatility_factor # Fator de volatilidade usado para antecipar cruzamento
        self.fallback_activated = fallback_activated # Define se a estratégia de Fallback será usada (ela pode entrar comprada em mercados subindo)

        self.acceptable_loss_percentage = acceptable_loss_percentage / 100 # % Máxima que o bot aceita perder quando vender
        self.stop_loss_percentage = stop_loss_percentage / 100 # % Máxima de loss que ele aceita, em caso de não vender na ordem limitada

        # Configurações de tempos de espera
        self.time_to_trade = time_to_trade
        self.delay_after_order = delay_after_order
        self.time_to_sleep = time_to_trade

        print('Inicializando cliente Binance...')
        try:
            self.client_binance = BinanceClient(api_key, secret_key, sync=True, sync_interval=30000, verbose=True) # Inicia o client da Binance
            print('Cliente Binance inicializado com sucesso')
        except Exception as e:
            print(f'ERRO ao inicializar cliente Binance: {str(e)}')
            raise e

        try:
            print('Definindo step size e tick size...')
            self.setStepSizeAndTickSize()
            print('Step size e tick size definidos com sucesso')
        except Exception as e:
            print(f'ERRO ao definir step size e tick size: {str(e)}')
            raise e

        print('Inicialização concluída com sucesso')

        # self.updateAllData() # Pode ser comentado em produção...

    # Atualiza todos os dados da conta
    # Função importante, sempre incrementar ela, em caso de novos gets
    def updateAllData(self, verbose = False):
        try:
            self.account_data = self.getUpdatedAccountData()                        # Dados atualizados do usuário e sua carteira
            self.last_stock_account_balance = self.getLastStockAccountBalance()     # Balanço atual do ativo na carteira
            self.actual_trade_position = self.getActualTradePosition()              # Posição atual (False = Vendido | True = Comprado)
            self.stock_data = self.getStockData_ClosePrice_OpenTime()               # Atualiza dados usados nos modelos
            self.open_orders = self.getOpenOrders()                                 # Retorna uma lista com todas as ordens abertas
            self.last_buy_price = self.getLastBuyPrice(verbose)                            # Salva o último valor de compra executado com sucesso
            self.last_sell_price = self.getLastSellPrice(verbose)                          # Salva o último valor de venda executado com sucesso

        except BinanceAPIException as e:
            print(f"Erro na atualização de dados: {e}")

    # ------------------------------------------------------------------
    # GETS Principais

    # Busca infos atualizada da conta Binance
    def getUpdatedAccountData(self):
        return self.client_binance.get_account() # Busca infos da conta
    
    # Busca o último balanço da conta, na stock escolhida.
    def getLastStockAccountBalance(self):
        for stock in self.account_data['balances']:
            if stock['asset'] == self.stock_code:
                free = float(stock['free'])
                locked = float(stock['locked'])
                in_wallet_amount = free + locked        
        return float(in_wallet_amount);

    # Checa se a posição atual é comprado ou vendido
    # Checa se a posição atual é comprado ou vendido
    def getActualTradePosition(self):
        """
        Determina a posição atual (comprado ou vendido) com base no saldo da moeda.
        Usa o stepSize da Binance para ajustar o limite mínimo.
        """
        # print(f'STEP SIZE: {self.step_size}')
        try:
            # Verifica se o saldo é maior que o step_size
            if self.last_stock_account_balance >= self.step_size:
                return True  # Comprado
            else:
                return False  # Vendido

        except Exception as e:
            print(f"Erro ao determinar a posição atual para {self.operation_code}: {e}")
            return False  # Retorna como vendido por padrão em caso de erro
        

    # Busca os dados do ativo no periodo
    # volatility_window normalmente e mesma janela que slow_window da MA strategy.
    def getStockData_ClosePrice_OpenTime(self, volatility_window=40):

        # Busca dados na binance dos últimos 1000 períodos
        candles = self.client_binance.get_klines(symbol = self.operation_code, interval = self.candle_period, limit = 500)

        # Transforma um um DataFrame Pandas
        prices = pd.DataFrame(candles)

        # Renomea as colunas baseada na Documentação da Binance
        prices.columns = ["open_time", "open_price", "high_price", "low_price", "close_price",
        "volume", "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "-"]

        # Pega apenas os indicadores que queremos para esse modelo
        prices = prices[["close_price", "open_time", "open_price", "high_price", "low_price", "volume"]]

        # Converte as colunas para o tipo numérico
        prices["close_price"] = pd.to_numeric(prices["close_price"], errors="coerce")
        prices["open_price"] = pd.to_numeric(prices["open_price"], errors="coerce")
        prices["high_price"] = pd.to_numeric(prices["high_price"], errors="coerce")
        prices["low_price"] = pd.to_numeric(prices["low_price"], errors="coerce")
        prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")


        # Corrige o tempo de fechamento 
        prices["open_time"] = pd.to_datetime(prices["open_time"], unit = "ms").dt.tz_localize("UTC")

        # Converte para o fuso horário UTC -3
        prices["open_time"] = prices["open_time"].dt.tz_convert("America/Sao_Paulo")


        # CÁLCULOS PRÉVIOS...

        # Calcula a volatilidade (desvio padrão) dos preços
        # self.stock_data["volatility"] = self.stock_data["close_price"].rolling(window=volatility_window).std()
        prices["volatility"] = prices["close_price"].rolling(window=volatility_window).std()


        return prices;


    # Retorna o preço da última ordem de compra executada para o ativo configurado.
    # Retorna 0.0 se nenhuma ordem de compra foi encontrada.
    def getLastBuyPrice(self, verbose=False):
        try:
            # Obtém o histórico de ordens do par configurado
            all_orders = self.client_binance.get_all_orders(symbol=self.operation_code, limit = 100)

            # Filtra apenas as ordens de compra executadas (FILLED)
            executed_buy_orders = [
                order for order in all_orders 
                if order['side'] == 'BUY' and order['status'] == 'FILLED'
            ]

            if executed_buy_orders:
                # Ordena as ordens por tempo (timestamp) para obter a mais recente
                last_executed_order = sorted(executed_buy_orders, key=lambda x: x['time'], reverse=True)[0]

                # print(f'ÚLTIMA EXECUTADA: {last_executed_order}')

                # Retorna o preço da última ordem de compra executada
                last_buy_price = float(last_executed_order['cummulativeQuoteQty']) / float(last_executed_order['executedQty'])
                                # Corrige o timestamp para a chave correta
                datetime_transact = datetime.utcfromtimestamp(last_executed_order['time'] / 1000).strftime('(%H:%M:%S) %d-%m-%Y')
                if verbose:
                    print(f"\nÚltima ordem de COMPRA executada para {self.operation_code}:")
                    print(f" - Data: {datetime_transact} | Preço: {self.adjust_to_step(last_buy_price,self.tick_size, as_string=True)} | Qnt.: {self.adjust_to_step(float(last_executed_order['origQty']), self.step_size, as_string=True)}")

                return last_buy_price
            else:
                if verbose:
                    print(f"Não há ordens de COMPRA executadas para {self.operation_code}.")
                return 0.0

        except Exception as e:
            if verbose:
                print(f"Erro ao verificar a última ordem de COMPRA executada para {self.operation_code}: {e}")
            return 0.0
        
    # Retorna o preço da última ordem de venda executada para o ativo configurado.
    # Retorna 0.0 se nenhuma ordem de venda foi encontrada.
    def getLastSellPrice(self, verbose = False):
        try:
            # Obtém o histórico de ordens do par configurado
            all_orders = self.client_binance.get_all_orders(symbol=self.operation_code, limit=100)

            # Filtra apenas as ordens de venda executadas (FILLED)
            executed_sell_orders = [
                order for order in all_orders 
                if order['side'] == 'SELL' and order['status'] == 'FILLED'
            ]

            if executed_sell_orders:
                # Ordena as ordens por tempo (timestamp) para obter a mais recente
                last_executed_order = sorted(executed_sell_orders, key=lambda x: x['time'], reverse=True)[0]

                # Retorna o preço da última ordem de venda executada
                last_sell_price = float(last_executed_order['cummulativeQuoteQty']) / float(last_executed_order['executedQty'])

                # Corrige o timestamp para a chave correta
                datetime_transact = datetime.utcfromtimestamp(last_executed_order['time'] / 1000).strftime('(%H:%M:%S) %d-%m-%Y')
                
                if verbose:
                    print(f"Última ordem de VENDA executada para {self.operation_code}:")
                    print(f" - Data: {datetime_transact} | Preço: {self.adjust_to_step(last_sell_price,self.tick_size, as_string=True)} | Qnt.: {self.adjust_to_step(float(last_executed_order['origQty']), self.step_size, as_string=True)}")
                return last_sell_price
            else:
                if verbose:
                    print(f"Não há ordens de VENDA executadas para {self.operation_code}.")
                return 0.0

        except Exception as e:
            if verbose:
                print(f"Erro ao verificar a última ordem de VENDA executada para {self.operation_code}: {e}")
            return 0.0

    def getTimestamp(self):
        """
        Retorna o timestamp ajustado com base no desvio de tempo entre o sistema local e o servidor da Binance.
        """
        try:
            # Obtém o tempo do servidor da Binance e calcula o desvio apenas uma vez
            if not hasattr(self, 'time_offset') or self.time_offset is None:
                server_time = self.client_binance.get_server_time()["serverTime"]
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
            
            # Retorna o timestamp ajustado
            adjusted_timestamp = int(time.time() * 1000) + self.time_offset
            return adjusted_timestamp

        except Exception as e:
            print(f"Erro ao ajustar o timestamp: {e}")
            # Retorna o timestamp local em caso de falha, mas não é recomendado para chamadas críticas
            return int(time.time() * 1000)



    # --------------------------------------------------------------
    # SETs

    # Seta o step_size (para quantidade) e tick_size (para preço) do ativo operado, só precisa ser executado 1x        
    def setStepSizeAndTickSize(self):
        # Obter informações do símbolo para respeitar os filtros
        symbol_info = self.client_binance.get_symbol_info(self.operation_code)
        price_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
        self.tick_size = float(price_filter['tickSize'])

        lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
        self.step_size = float(lot_size_filter['stepSize'])


    def adjust_to_step(self, value, step, as_string=False):
        """
        Ajusta o valor para o múltiplo mais próximo do passo definido, lidando com problemas de precisão
        e garantindo que o resultado não seja retornado em notação científica.
        
        Parameters:
            value (float): O valor a ser ajustado.
            step (float): O incremento mínimo permitido.
            as_string (bool): Define se o valor ajustado será retornado como string. Padrão é True.
        
        Returns:
            str|float: O valor ajustado no formato especificado.
        """
        if step <= 0:
            raise ValueError("O valor de 'step' deve ser maior que zero.")
        
        # Descobrir o número de casas decimais do step
        decimal_places = max(0, abs(int(math.floor(math.log10(step))))) if step < 1 else 0
        
        # Ajustar o valor ao step usando floor
        adjusted_value = math.floor(value / step) * step
        
        # Garantir que o resultado tenha a mesma precisão do step
        adjusted_value = round(adjusted_value, decimal_places)
        
        # Retornar no formato especificado
        if as_string:
            return f"{adjusted_value:.{decimal_places}f}"
        else:
            return adjusted_value






    # --------------------------------------------------------------
    # PRINTS

    # Printa toda a carteira
    def printWallet(self):
        for stock in self.account_data["balances"]:
            if float(stock["free"]) > 0:
                print(stock)

    # Printa o ativo definido na classe
    def printStock(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == self.stock_code:
                print(stock)

    def printBrl(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == 'BRL':
                print(stock)

    # Printa todas ordens abertas
    def printOpenOrders(self):
        # Log das ordens abertas
        if self.open_orders:
            print("-------------------------")
            print(f"Ordens abertas para {self.operation_code}:")
            for order in self.open_orders:
                to_print = (
                    f"----"
                    f"\nID {order['orderId']}:"
                    f"\n - Status: {getOrderStatus(order['status'])}"
                    f"\n - Side: {order['side']}"
                    f"\n - Ativo: {order['symbol']}"
                    f"\n - Preço: {order['price']}"
                    f"\n - Quantidade Original: {order['origQty']}"
                    f"\n - Quantidade Executada: {order['executedQty']}"
                    f"\n - Tipo: {order['type']}"
                )
                print(to_print)    
            print("-------------------------")

        else:
            print(f"Não há ordens abertas para {self.operation_code}.")

    # --------------------------------------------------------------
    # GETs auxiliares

    # Retorna toda a carteira
    def getWallet(self):
        for stock in self.account_data["balances"]:
            if float(stock["free"]) > 0:
                return stock

    # Retorna todo o ativo definido na classe
    def getStock(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == self.stock_code:
                return stock


    # --------------------------------------------------------------
    # FUNÇÕES DE COMPRA

    # Compra a ação, a MERCADO
    def buyMarketOrder(self):
        try:
            if not self.actual_trade_position:  # Se a posição não for comprada
                quantity = self.adjust_to_step(self.traded_quantity - self.partial_quantity_discount, self.step_size, as_string=True)
                
                # Verificar se há saldo suficiente na conta
                # Obter saldo em BRL (ou outra moeda base)
                base_currency = self.operation_code.replace(self.stock_code, '')
                base_balance = 0
                
                for stock in self.account_data["balances"]:
                    if stock['asset'] == base_currency:
                        base_balance = float(stock['free'])
                
                # Estimar o valor total necessário para a compra
                current_price = self.stock_data["close_price"].iloc[-1]
                estimated_cost = float(quantity) * current_price
                
                if base_balance < estimated_cost:
                    error_msg = f"Saldo insuficiente para compra. Disponível: {base_balance:.2f} {base_currency}, Necessário: {estimated_cost:.2f} {base_currency}"
                    logging.error(error_msg)
                    print(f"\n❌ ERRO: {error_msg}")
                    # Adicionar a mensagem aos logs da aplicação
                    import api
                    if hasattr(api, 'add_log_message'):
                        api.add_log_message(f"ERRO: {error_msg}", "error")
                    return False

                order_buy = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_BUY,  # Compra
                    type=ORDER_TYPE_MARKET,  # Ordem de Mercado
                    quantity=quantity
                )

                self.actual_trade_position = True  # Define posição como comprada
                self.last_operation = "BUY"  # Atualiza a operação
                createLogOrder(order_buy)  # Cria um log
                print(f"\nOrdem de COMPRA a mercado enviada com sucesso:")
                print(order_buy)
                
                # Adicionar a mensagem de sucesso aos logs da aplicação
                import api
                if hasattr(api, 'add_log_message'):
                    api.add_log_message(f"COMPRA a mercado de {quantity} {self.stock_code} executada com sucesso", "buy")
                
                # Registrar a operação no histórico
                try:
                    from Models.BotTradeModel import BotTradeModel
                    if hasattr(self, 'bot_id'):  # Verificar se o bot tem ID definido
                        # Calcular o preço e valor total real
                        price = float(order_buy['cummulativeQuoteQty']) / float(order_buy['executedQty'])
                        total_value = float(order_buy['cummulativeQuoteQty'])
                        quantity = float(order_buy['executedQty'])
                        
                        # Registrar a operação no histórico
                        BotTradeModel.register_trade(
                            bot_id=self.bot_id,
                            operation_code=self.operation_code,
                            trade_type="BUY",
                            price=price,
                            quantity=quantity,
                            total_value=total_value
                        )
                        print(f"Operação de compra registrada no histórico para o bot {self.bot_id}")
                except Exception as e:
                    print(f"Erro ao registrar operação no histórico: {e}")
                
                return order_buy  # Retorna a ordem

            else:  # Se a posição já está comprada
                logging.warning('Erro ao comprar: Posição já comprada.')
                print('\nErro ao comprar: Posição já comprada.')
                
                # Adicionar aviso aos logs da aplicação
                import api
                if hasattr(api, 'add_log_message'):
                    api.add_log_message(f"Aviso: Tentativa de compra ignorada pois a posição já está comprada", "warning")
                
                return False

        except Exception as e:
            logging.error(f"Erro ao executar ordem de compra a mercado: {e}")
            print(f"\nErro ao executar ordem de compra a mercado: {e}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO na compra: {str(e)}", "error")
            return False

    # Compra por um preço máximo (Ordem Limitada)
    # [NOVA] Define o valor usando RSI e Volume Médio
    def buyLimitedOrder(self, price=0):
        close_price = self.stock_data["close_price"].iloc[-1]
        volume = self.stock_data["volume"].iloc[-1]  # Volume atual do mercado
        avg_volume = self.stock_data["volume"].rolling(window=20).mean().iloc[-1]  # Média de volume
        rsi = Indicators.getRSI(series=self.stock_data["close_price"])  # RSI para ajuste

        if price == 0:
            if rsi < 30:  # Mercado sobrevendido
                limit_price = close_price - (0.002 * close_price)  # Tenta comprar um pouco mais abaixo
            elif volume < avg_volume:  # Volume baixo (mercado lateral)
                limit_price = close_price + (0.002 * close_price)  # Ajuste pequeno acima
            else:  # Volume alto (mercado volátil)
                limit_price = close_price + (0.005 * close_price)  # Ajuste maior acima (caso suba muito rápido)
        else:
            limit_price = price

        # Ajustar o preço limite para o tickSize permitido
        limit_price = self.adjust_to_step(limit_price, self.tick_size, as_string=True)

        # Ajustar a quantidade para o stepSize permitido
        quantity = self.adjust_to_step(self.traded_quantity - self.partial_quantity_discount, self.step_size, as_string=True)

        # Verificar se há saldo suficiente na conta
        # Obter saldo em BRL (ou outra moeda base)
        base_currency = self.operation_code.replace(self.stock_code, '')
        base_balance = 0
        
        for stock in self.account_data["balances"]:
            if stock['asset'] == base_currency:
                base_balance = float(stock['free'])
        
        # Estimar o valor total necessário para a compra
        estimated_cost = float(quantity) * float(limit_price)
        
        if base_balance < estimated_cost:
            error_msg = f"Saldo insuficiente para ordem limitada de compra. Disponível: {base_balance:.2f} {base_currency}, Necessário: {estimated_cost:.2f} {base_currency}"
            logging.error(error_msg)
            print(f"\n❌ ERRO: {error_msg}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO: {error_msg}", "error")
            return False

        # Log de informações
        print(f"Enviando ordem limitada de COMPRA para {self.operation_code}:")
        print(f" - RSI: {rsi}")
        print(f" - Quantidade: {quantity}")
        print(f" - Close Price: {close_price}")
        print(f" - Preço Limite: {limit_price}")

        # Enviar ordem limitada de COMPRA
        try:
            order_buy = self.client_binance.create_order(
                symbol = self.operation_code,
                side = SIDE_BUY,  # Compra
                type = ORDER_TYPE_LIMIT,  # Ordem Limitada
                timeInForce = "GTC",  # Good 'Til Canceled (Ordem válida até ser cancelada)
                quantity = quantity,
                price = limit_price
            )
            self.actual_trade_position = True  # Atualiza a posição para comprada
            self.last_operation = "BUY"  # Atualiza a operação
            print(f"\nOrdem COMPRA limitada enviada com sucesso:")
            # print(order_buy)
            if (order_buy is not None):
                createLogOrder(order_buy) # Cria um log
                
                # Registrar a operação no histórico
                try:
                    from Models.BotTradeModel import BotTradeModel
                    if hasattr(self, 'bot_id'):  # Verificar se o bot tem ID definido
                        # Para ordem limitada, usamos o preço limite
                        # O valor total é calculado com base na quantidade e preço
                        price = float(limit_price)
                        quantity_float = float(quantity)
                        total_value = price * quantity_float
                        
                        # Registrar a operação no histórico
                        BotTradeModel.register_trade(
                            bot_id=self.bot_id,
                            operation_code=self.operation_code,
                            trade_type="BUY",
                            price=price,
                            quantity=quantity_float,
                            total_value=total_value
                        )
                        print(f"Operação de compra limitada registrada no histórico para o bot {self.bot_id}")
                except Exception as e:
                    print(f"Erro ao registrar operação no histórico: {e}")
                
            return order_buy  # Retorna a ordem enviada
        except Exception as e:
            logging.error(f"Erro ao enviar ordem limitada de COMPRA: {e}")
            print(f"\nErro ao enviar ordem limitada de COMPRA: {e}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO na ordem limitada de compra: {str(e)}", "error")
            return False


    # --------------------------------------------------------------
    # FUNÇÕES DE VENDA 

    # Vende a ação a MERCADO
    def sellMarketOrder(self):
        try:
            if self.actual_trade_position:  # Se a posição for comprada
                quantity = self.adjust_to_step(self.last_stock_account_balance, self.step_size, as_string=True)
                
                # Verificar se há saldo suficiente na carteira
                if self.last_stock_account_balance < float(self.step_size):
                    error_msg = f"Saldo insuficiente para venda. Disponível: {self.last_stock_account_balance:.8f} {self.stock_code}, Mínimo necessário: {self.step_size} {self.stock_code}"
                    logging.error(error_msg)
                    print(f"\n❌ ERRO: {error_msg}")
                    # Adicionar a mensagem aos logs da aplicação
                    import api
                    if hasattr(api, 'add_log_message'):
                        api.add_log_message(f"ERRO: {error_msg}", "error")
                    return False

                order_sell = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_SELL,  # Venda
                    type=ORDER_TYPE_MARKET,  # Ordem de Mercado
                    quantity=quantity
                )

                self.actual_trade_position = False  # Define posição como vendida
                self.last_operation = "SELL"  # Atualiza a operação
                createLogOrder(order_sell)  # Cria um log
                print(f"\nOrdem de VENDA a mercado enviada com sucesso:")
                # print(order_sell)
                
                # Adicionar a mensagem de sucesso aos logs da aplicação
                import api
                if hasattr(api, 'add_log_message'):
                    api.add_log_message(f"VENDA a mercado de {quantity} {self.stock_code} executada com sucesso", "sell")
                
                # Registrar a operação no histórico
                try:
                    from Models.BotTradeModel import BotTradeModel
                    if hasattr(self, 'bot_id'):  # Verificar se o bot tem ID definido
                        # Calcular o preço e valor total real
                        price = float(order_sell['cummulativeQuoteQty']) / float(order_sell['executedQty'])
                        total_value = float(order_sell['cummulativeQuoteQty'])
                        quantity = float(order_sell['executedQty'])
                        
                        # Registrar a operação no histórico
                        BotTradeModel.register_trade(
                            bot_id=self.bot_id,
                            operation_code=self.operation_code,
                            trade_type="SELL",
                            price=price,
                            quantity=quantity,
                            total_value=total_value
                        )
                        print(f"Operação de venda registrada no histórico para o bot {self.bot_id}")
                except Exception as e:
                    print(f"Erro ao registrar operação no histórico: {e}")
                
                return order_sell  # Retorna a ordem

            else:  # Se a posição já está vendida
                logging.warning('Erro ao vender: Posição já vendida.')
                print('\nErro ao vender: Posição já vendida.')
                
                # Adicionar aviso aos logs da aplicação
                import api
                if hasattr(api, 'add_log_message'):
                    api.add_log_message(f"Aviso: Tentativa de venda ignorada pois a posição já está vendida", "warning")
                
                return False

        except Exception as e:
            logging.error(f"Erro ao executar ordem de venda a mercado: {e}")
            print(f"\nErro ao executar ordem de venda a mercado: {e}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO na venda: {str(e)}", "error")
            return False


    # Venda por um preço mínimo (Ordem Limitada)
    # [NOVA] Define o valor usando RSI e Volume Médio
    def sellLimitedOrder(self, price=0):
        close_price = self.stock_data["close_price"].iloc[-1]
        volume = self.stock_data["volume"].iloc[-1]  # Volume atual do mercado
        avg_volume = self.stock_data["volume"].rolling(window=20).mean().iloc[-1]  # Média de volume
        rsi = Indicators.getRSI(series=self.stock_data["close_price"])

        if price == 0:
            if rsi > 70:  # Mercado sobrecomprado
                limit_price = close_price + (0.002 * close_price)  # Tenta vender um pouco acima
            elif volume < avg_volume:  # Volume baixo (mercado lateral)
                limit_price = close_price - (0.002 * close_price)  # Ajuste pequeno abaixo
            else:  # Volume alto (mercado volátil)
                limit_price = close_price - (0.005 * close_price)  # Ajuste maior abaixo (caso caia muito rápido)

            # Garantir que o preço limite seja maior que o mínimo aceitável
            # limit_price = max(limit_price, self.getMinimumPriceToSell())
            if(limit_price < (self.last_buy_price*(1-self.acceptable_loss_percentage))):
                print(f'\nAjuste de venda aceitável ({self.acceptable_loss_percentage*100}%):')
                print(f' - De: {limit_price:.4f}')
                # limit_price = (self.last_buy_price*(1-self.acceptable_loss_percentage))
                limit_price = self.getMinimumPriceToSell()
                print(f' - Para: {limit_price}')
        else:
            limit_price = price

        # Ajustar o preço limite para o tickSize permitido
        limit_price = self.adjust_to_step(limit_price, self.tick_size, as_string=True)

        # Ajustar a quantidade para o stepSize permitido
        quantity = self.adjust_to_step(self.last_stock_account_balance, self.step_size, as_string=True)

        # Verificar se há saldo suficiente na carteira
        if self.last_stock_account_balance < float(self.step_size):
            error_msg = f"Saldo insuficiente para ordem limitada de venda. Disponível: {self.last_stock_account_balance:.8f} {self.stock_code}, Mínimo necessário: {self.step_size} {self.stock_code}"
            logging.error(error_msg)
            print(f"\n❌ ERRO: {error_msg}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO: {error_msg}", "error")
            return False

        # Log de informações
        print(f"\nEnviando ordem limitada de VENDA para {self.operation_code}:")
        print(f" - RSI: {rsi}")
        print(f" - Quantidade: {quantity}")
        print(f" - Close Price: {close_price}")
        print(f" - Preço Limite: {limit_price}")


        # Enviar ordem limitada de VENDA
        try:
            # Por algum motivo, fazer direto por aqui resolveu um bug de mudança de preço
            # Depois vou testar novamente.
            order_sell = self.client_binance.create_order(
                symbol = self.operation_code,
                side = SIDE_SELL,  # Venda
                type = ORDER_TYPE_LIMIT,  # Ordem Limitada
                timeInForce = "GTC",  # Good 'Til Canceled (Ordem válida até ser cancelada)
                quantity = str(quantity),
                price = str(limit_price)
            )

            self.actual_trade_position = False  # Atualiza a posição para vendida
            self.last_operation = "SELL"  # Atualiza a operação
            print(f"\nOrdem VENDA limitada enviada com sucesso:")
            # print(order_sell)
            createLogOrder(order_sell) # Cria um log
            
            # Registrar a operação no histórico
            try:
                from Models.BotTradeModel import BotTradeModel
                if hasattr(self, 'bot_id'):  # Verificar se o bot tem ID definido
                    # Para ordem limitada, usamos o preço limite
                    # O valor total é calculado com base na quantidade e preço
                    price = float(limit_price)
                    quantity_float = float(quantity)
                    total_value = price * quantity_float
                    
                    # Registrar a operação no histórico
                    BotTradeModel.register_trade(
                        bot_id=self.bot_id,
                        operation_code=self.operation_code,
                        trade_type="SELL",
                        price=price,
                        quantity=quantity_float,
                        total_value=total_value
                    )
                    print(f"Operação de venda limitada registrada no histórico para o bot {self.bot_id}")
            except Exception as e:
                print(f"Erro ao registrar operação no histórico: {e}")
            
            return order_sell  # Retorna a ordem enviada
        except Exception as e:
            logging.error(f"Erro ao enviar ordem limitada de VENDA: {e}")
            print(f"\nErro ao enviar ordem limitada de VENDA: {e}")
            # Adicionar a mensagem aos logs da aplicação
            import api
            if hasattr(api, 'add_log_message'):
                api.add_log_message(f"ERRO na ordem limitada de venda: {str(e)}", "error")
            return False


    # --------------------------------------------------------------
    # ORDENS E SUAS ATUALIZAÇÕES

    # Verifica as ordens ativas do ativo atual configurado
    def getOpenOrders(self):
        open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)

        return open_orders

    # Cancela uma ordem a partir do seu ID
    def cancelOrderById(self, order_id):
        self.client_binance.cancel_order(symbol=self.operation_code, orderId=order_id)


    # Cancela todas ordens abertas
    def cancelAllOrders(self):
        if self.open_orders:
            for order in self.open_orders:
                try:
                    self.client_binance.cancel_order(symbol=self.operation_code, orderId=order['orderId'])
                    print(f"❌ Ordem {order['orderId']} cancelada.")
                except Exception as e:
                    print(f"Erro ao cancelar ordem {order['orderId']}: {e}")


    # Verifica se há alguma ordem de COMPRA aberta
    # Se a ordem foi parcialmente executada, ele salva o valor
    # executado na variável self.partial_quantity_discount, para que
    # este valor seja descontado nas execuções seguintes.
    # Se foi parcialmente executado, ela também salva o valor que foi executado
    # na variável self.last_buy_price
    def hasOpenBuyOrder(self):
        """
        Verifica se há uma ordem de compra aberta para o ativo configurado.
        Se houver:
            - Salva a quantidade já executada em self.partial_quantity_discount.
            - Salva o maior preço parcialmente executado em self.last_buy_price.
        """
        # Inicializa as variáveis de desconto e maior preço como 0
        self.partial_quantity_discount = 0.0
        try:

            # Obtém todas as ordens abertas para o par
            open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)

            # Filtra as ordens de compra (SIDE_BUY)
            buy_orders = [order for order in open_orders if order['side'] == 'BUY']

            if buy_orders:
                self.last_buy_price = 0.0

                print(f"\nOrdens de compra abertas para {self.operation_code}:")
                for order in buy_orders:
                    executed_qty = float(order['executedQty'])  # Quantidade já executada
                    price = float(order['price'])  # Preço da ordem

                    print(f" - ID da Ordem: {order['orderId']}, Preço: {price}, Qnt.: {order['origQty']}, Qnt. Executada: {executed_qty}")

                    # Atualiza a quantidade parcial executada
                    self.partial_quantity_discount += executed_qty

                    # Atualiza o maior preço parcialmente executado
                    if executed_qty > 0 and price > self.last_buy_price:
                        self.last_buy_price = price

                print(f" - Quantidade parcial executada no total: {self.partial_quantity_discount}")
                print(f" - Maior preço parcialmente executado: {self.last_buy_price}")
                return True
            else:
                print(f" - Não há ordens de compra abertas para {self.operation_code}.")
                return False

        except Exception as e:
            print(f"Erro ao verificar ordens abertas para {self.operation_code}: {e}")
            return False

    # Verifica se há uma ordem de VENDA aberta para o ativo configurado.
    # Se houver, salva a quantidade já executada na variável self.partial_quantity_discount.
    def hasOpenSellOrder(self):
        # Inicializa a variável de desconto como 0
        self.partial_quantity_discount = 0.0        
        try:

            # Obtém todas as ordens abertas para o par
            open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)

            # Filtra as ordens de venda (SIDE_SELL)
            sell_orders = [order for order in open_orders if order['side'] == 'SELL']

            if sell_orders:
                print(f"\nOrdens de venda abertas para {self.operation_code}:")
                for order in sell_orders:
                    executed_qty = float(order['executedQty'])  # Quantidade já executada
                    print(f" - ID da Ordem: {order['orderId']}, Preço: {order['price']}, Qnt.: {order['origQty']}, Qnt. Executada: {executed_qty}")

                    # Atualiza a quantidade parcial executada
                    self.partial_quantity_discount += executed_qty

                print(f" - Quantidade parcial executada no total: {self.partial_quantity_discount}")
                return True
            else:
                print(f" - Não há ordens de venda abertas para {self.operation_code}.")
                return False

        except Exception as e:
            print(f"Erro ao verificar ordens abertas para {self.operation_code}: {e}")
            return False


    # --------------------------------------------------------------
    # ESTRATÉGIAS DE DECISÃO

    # Função que executa estratégias implementadas e retorna a decisão final
    def getFinalDecisionStrategy(self):
        final_decision = runStrategies(self)
        return final_decision
    
    # Define o valor mínimo para vender, baseado no acceptable_loss_percentage
    def getMinimumPriceToSell(self):
        return (self.last_buy_price*(1-self.acceptable_loss_percentage))
    
    # Estratégia de venda por "stop loss"
    def stopLossTrigger(self):
        close_price = self.stock_data["close_price"].iloc[-1]
        weighted_price = self.stock_data["close_price"].iloc[-2]  # Preço ponderado pelo candle anterior
        stop_loss_price = self.last_buy_price * (1 - self.stop_loss_percentage)

        print(f'\n - Preço atual: {self.stock_data["close_price"].iloc[-1]}')
        print(f' - Preço mínimo para vender: {self.getMinimumPriceToSell()}')
        print(f' - Stop Loss em: {stop_loss_price:.4f} (-{self.stop_loss_percentage*100}%)\n')

        if close_price < stop_loss_price and weighted_price < stop_loss_price and self.actual_trade_position == True:
            print("🔴 Ativando STOP LOSS...")
            self.cancelAllOrders()
            time.sleep(2)
            sell_result = self.sellMarketOrder()
            
            # Atualizar last_operation para SELL se a venda for bem-sucedida
            if sell_result:
                self.last_operation = "SELL"
                print(f"Operação atualizada para: {self.last_operation}")
                
            return True
        return False
    

        
    # --------------------------------------------------------------

    # Não usada por enquanto    
    def create_order(self, _symbol, _side, _type, _quantity, _timeInForce = None, _limit_price = None, _stop_price = None):
        order_buy = TraderOrder.create_order(self.client_binance, 
               _symbol = _symbol,
               _side = _side,  # Compra
               _type = _type,  # Ordem Limitada
               _timeInForce = _timeInForce,  # Good 'Til Canceled (Ordem válida até ser cancelada)
               _quantity = _quantity,
               _limit_price = _limit_price,
               _stop_price = _stop_price
           )
         
        return order_buy    
            
    # --------------------------------------------------------------
    # EXECUTE
        
    # Função principal e a única que deve ser execuda em loop, quando o
    # robô estiver funcionando normalmente    
    def execute(self):
        print('------------------------------------------------')
        print(f'🟢 Executado {datetime.now().strftime("(%H:%M:%S) %d-%m-%Y")}\n')  # Adiciona o horário atual formatado

        # Atualiza todos os dados
        self.updateAllData(verbose=True)

        # Atualiza o atributo last_operation com base na posição atual
        if not hasattr(self, 'last_operation') or self.last_operation is None:
            self.last_operation = "BUY" if self.actual_trade_position else "SELL"
            print(f"Definindo operação inicial como: {self.last_operation}")
        
        print('\n-------')
        print('Detalhes:')
        print(f' - Posição atual: {"Comprado" if self.actual_trade_position else "Vendido"}')
        print(f' - Balanço atual: {self.last_stock_account_balance:.4f} ({self.stock_code})')

        # ---------
        # Estratégias sentinelas de saída
        # Se perder mais que o panic sell aceitável, ele sai à mercado, independente.
        if self.stopLossTrigger():
            print("📉 STOP LOSS executado...")
            return
        
        # ---------
        # Calcula a melhor estratégia para a decisão final
        self.last_trade_decision = self.getFinalDecisionStrategy()

        # ---------
        # Verifica ordens anteriores abertas
        if self.last_trade_decision == True: # Se a decisão for COMPRA
            # Existem ordens de compra abertas?
            if(self.hasOpenBuyOrder()): # Sim e salva possíveis quantidades executadas incompletas.
                self.cancelAllOrders() # Cancela todas ordens
                time.sleep(2)

        if self.last_trade_decision == False: # Se a decisão for VENDA
            # Existem ordens de venda abertas?
            if(self.hasOpenSellOrder()): # Sim e salva possíveis quantidades executadas incompletas.
                self.cancelAllOrders() # Cancela todas ordens
                time.sleep(2)
        
        # ---------
        print('\n--------------')    
        print(f'🔎 Decisão Final: {"Comprar" if self.last_trade_decision == True else "Vender" if self.last_trade_decision == False else "Inconclusiva"}')

        # ---------
        # Se a posição for vendida (false) e a decisão for de compra (true), compra o ativo
        # Se a posição for comprada (true) e a decisão for de venda (false), vende o ativo
        if self.actual_trade_position == False and self.last_trade_decision == True:
            print('🏁 Ação final: Comprar')
            print('--------------')   
            print(f'\nCarteira em {self.stock_code} [ANTES]:') 
            self.printStock()          
            order_result = self.buyLimitedOrder()
            
            # Atualizar o atributo last_operation após a ordem
            if order_result:
                self.last_operation = "BUY"
                print(f"Operação atualizada para: {self.last_operation}")
                
            time.sleep(2)
            self.updateAllData()
            print(f'Carteira em {self.stock_code} [DEPOIS]:')            
            self.printStock()
            self.time_to_sleep = self.delay_after_order

        elif self.actual_trade_position == True and self.last_trade_decision == False:
            print('🏁 Ação final: Vender')
            print('--------------') 
            print(f'\nCarteira em {self.stock_code} [ANTES]:') 
            self.printStock()
            order_result = self.sellLimitedOrder()
            
            # Atualizar o atributo last_operation após a ordem
            if order_result:
                self.last_operation = "SELL"
                print(f"Operação atualizada para: {self.last_operation}")
                
            time.sleep(2)
            self.updateAllData()
            print(f'\nCarteira em {self.stock_code} [DEPOIS]:') 
            self.printStock()
            self.time_to_sleep = self.delay_after_order

        else:
            print(f'🏁 Ação final: Manter posição ({"Comprado" if self.actual_trade_position else "Vendido"})')
            print('--------------') 
            self.time_to_sleep = self.time_to_trade

        print('------------------------------------------------')

    # Método para ser usado como ponto de entrada em uma thread
    def run(self):
        """Método para execução contínua do bot em uma thread separada.
        Este método é chamado pela API quando o bot é iniciado."""
        print(f"Bot iniciado para {self.operation_code} com modo {self.stock_code}")
        try:
            # Inicialização do bot
            self.updateAllData(verbose=True)
            
            # Se não tiver last_operation definido, definir baseado na posição atual
            if not hasattr(self, 'last_operation') or not self.last_operation:
                self.last_operation = "BUY" if self.actual_trade_position else "SELL"
                print(f"Operação inicial definida como: {self.last_operation}")
            
            # Loop principal do bot
            while True:
                try:
                    self.execute()
                    time.sleep(self.time_to_sleep)
                except Exception as e:
                    print(f"Erro durante execução do bot: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(60)  # Esperar um minuto antes de tentar novamente
        except Exception as e:
            print(f"Bot encerrado com erro: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Método para parar o bot
    def stop(self):
        """Método para interromper o funcionamento do bot."""
        print(f"Bot {self.operation_code} sendo finalizado")
        # Cancelar todas as ordens abertas ao finalizar
        try:
            self.cancelAllOrders()
            print("Todas as ordens foram canceladas")
            return True
        except Exception as e:
            print(f"Erro ao cancelar ordens: {str(e)}")
            return False





