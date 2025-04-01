import sqlite3
import json
import datetime
import os

class BotTradeModel:
    @staticmethod
    def init_db():
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        # Criar tabela de operações do bot real se não existir
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT NOT NULL,
            operation_code TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            price REAL NOT NULL,
            quantity REAL NOT NULL,
            total_value REAL NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Criar índice para melhorar performance das buscas
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bot_id ON bot_trades (bot_id)
        ''')
        
        conn.commit()
        conn.close()
        
        print("Tabela de operações de bot real inicializada com sucesso!")
    
    @staticmethod
    def register_trade(bot_id, operation_code, trade_type, price, quantity, total_value, timestamp=None):
        """
        Registra uma operação de bot real no banco de dados
        
        Parameters:
            bot_id (str): ID do bot
            operation_code (str): Código da operação (ex: BTCUSDT)
            trade_type (str): Tipo da operação ('BUY' ou 'SELL')
            price (float): Preço da operação
            quantity (float): Quantidade da operação
            total_value (float): Valor total da operação (preço * quantidade)
            timestamp (str, optional): Timestamp da operação. Se None, usa o timestamp atual.
        
        Returns:
            int: ID da operação registrada
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO bot_trades 
        (bot_id, operation_code, trade_type, price, quantity, total_value, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, operation_code, trade_type, price, quantity, total_value, timestamp))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    @staticmethod
    def get_trades_by_bot(bot_id):
        """
        Retorna todas as operações de um bot específico
        
        Parameters:
            bot_id (str): ID do bot
        
        Returns:
            list: Lista de dicionários com as operações
        """
        conn = sqlite3.connect('src/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM bot_trades 
        WHERE bot_id = ? 
        ORDER BY timestamp ASC
        ''', (bot_id,))
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
        
    @staticmethod
    def get_bot_statistics(bot_id):
        """
        Calcula estatísticas para um bot específico

        Parameters:
            bot_id (str): ID do bot

        Returns:
            dict: Dicionário com estatísticas do bot
        """
        trades = BotTradeModel.get_trades_by_bot(bot_id)

        if not trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_profit": 0,
                "profit_percentage": 0,
                "initial_balance": 0,
                "final_balance": 0,
                "highest_price": 0,
                "lowest_price": 0,
                "total_buy_volume": 0,
                "total_sell_volume": 0
            }

        # Contar operações por tipo
        buy_trades = [t for t in trades if t["trade_type"] == "BUY"]
        sell_trades = [t for t in trades if t["trade_type"] == "SELL"]
        
        # Calcular valores extremos
        all_prices = [t["price"] for t in trades]
        highest_price = max(all_prices) if all_prices else 0
        lowest_price = min(all_prices) if all_prices else 0
        
        # Calcular volumes de compra e venda
        total_buy_volume = sum(t["total_value"] for t in buy_trades)
        total_sell_volume = sum(t["total_value"] for t in sell_trades)
        
        # Calcular lucro ou prejuízo
        total_profit = total_sell_volume - total_buy_volume
        
        # Calcular saldo inicial e final (estimados)
        initial_balance = total_buy_volume if buy_trades else 0
        final_balance = total_sell_volume if sell_trades else total_buy_volume
        
        # Calcular percentual de lucro
        profit_percentage = 0
        if initial_balance > 0:
            profit_percentage = (total_profit / initial_balance) * 100
        
        return {
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_profit": total_profit,
            "profit_percentage": profit_percentage,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "highest_price": highest_price,
            "lowest_price": lowest_price,
            "total_buy_volume": total_buy_volume,
            "total_sell_volume": total_sell_volume
        }
    
    @staticmethod
    def delete_bot_trades(bot_id):
        """
        Exclui todas as operações de um bot específico
        
        Parameters:
            bot_id (str): ID do bot
        
        Returns:
            int: Número de operações excluídas
        """
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM bot_trades WHERE bot_id = ?', (bot_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
        
    @staticmethod
    def get_all_bots():
        """
        Retorna todos os bots únicos que possuem registro de operações, com estatísticas

        Returns:
            list: Lista de dicionários com informações de cada bot
        """
        try:
            conn = sqlite3.connect('src/database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Consulta para obter bots únicos com contagem de operações e datas
            cursor.execute('''
            SELECT 
                bot_id,
                operation_code AS symbol,
                COUNT(*) AS total_operations,
                MIN(timestamp) AS start_date,
                MAX(timestamp) AS end_date
            FROM 
                bot_trades
            GROUP BY 
                bot_id
            ORDER BY 
                MAX(timestamp) DESC
            ''')
            
            bots = []
            for row in cursor.fetchall():
                bot_id = row['bot_id']
                
                # Obter estatísticas para cada bot
                stats = BotTradeModel.get_bot_statistics(bot_id)
                
                # Extrair símbolo (par de moedas) da operação
                symbol = row['symbol']
                
                # Adicionar bot à lista com dados formatados
                bots.append({
                    'id': bot_id,
                    'symbol': symbol,
                    'total_operations': row['total_operations'],
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'profit_percentage': stats.get('profit_percentage', 0),
                    'total_profit': stats.get('total_profit', 0),
                    'initial_balance': stats.get('initial_balance', 0),
                    'final_balance': stats.get('final_balance', 0),
                    'total_buy_volume': stats.get('total_buy_volume', 0),
                    'total_sell_volume': stats.get('total_sell_volume', 0),
                    'highest_price': stats.get('highest_price', 0),
                    'lowest_price': stats.get('lowest_price', 0),
                    'buy_trades': stats.get('buy_trades', 0),
                    'sell_trades': stats.get('sell_trades', 0)
                })
            
            conn.close()
            return bots
            
        except Exception as e:
            print(f"Erro ao obter lista de bots: {str(e)}")
            return [] 