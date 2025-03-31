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
                "total_buy_value": 0,
                "total_sell_value": 0,
                "profit_loss": 0,
                "profit_loss_percentage": 0
            }
        
        buy_trades = [t for t in trades if t["trade_type"] == "BUY"]
        sell_trades = [t for t in trades if t["trade_type"] == "SELL"]
        
        total_buy_value = sum(t["total_value"] for t in buy_trades)
        total_sell_value = sum(t["total_value"] for t in sell_trades)
        
        profit_loss = total_sell_value - total_buy_value
        profit_loss_percentage = 0
        
        if total_buy_value > 0:
            profit_loss_percentage = (profit_loss / total_buy_value) * 100
            
        return {
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "profit_loss": profit_loss,
            "profit_loss_percentage": profit_loss_percentage,
            "first_trade_date": trades[0]["timestamp"] if trades else None,
            "last_trade_date": trades[-1]["timestamp"] if trades else None
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
            
            # Obter todos os IDs de bot únicos
            cursor.execute('''
            SELECT DISTINCT bot_id 
            FROM bot_trades
            ''')
            
            bot_ids = [row[0] for row in cursor.fetchall()]
            
            # Se precisarmos ordenar, podemos fazer isso em uma etapa separada
            if bot_ids:
                # Consulta separada para obter a primeira timestamp de cada bot
                cursor.execute('''
                SELECT bot_id, MIN(timestamp) as first_timestamp
                FROM bot_trades
                GROUP BY bot_id
                ''')
                
                timestamp_map = {row['bot_id']: row['first_timestamp'] for row in cursor.fetchall()}
                # Ordenar IDs com base nos timestamps (do mais recente para o mais antigo)
                bot_ids.sort(key=lambda bot_id: timestamp_map.get(bot_id, ''), reverse=True)
            
            conn.close()
            
            # Construir lista de resultados com estatísticas para cada bot
            bots = []
            for bot_id in bot_ids:
                # Obter primeiro trade para informações básicas
                trades = BotTradeModel.get_trades_by_bot(bot_id)
                if not trades:
                    continue
                    
                first_trade = trades[0]
                stats = BotTradeModel.get_bot_statistics(bot_id)
                
                # Determinar datas de início e fim
                timestamps = [trade["timestamp"] for trade in trades]
                created_at = min(timestamps) if timestamps else ""
                updated_at = max(timestamps) if timestamps else ""
                
                # Extrair códigos de operação e stock do formato bot_id: BTCUSDT_BTC_timestamp
                parts = bot_id.split('_')
                operation_code = parts[0] if len(parts) > 0 else ""
                stock_code = parts[1] if len(parts) > 1 else ""
                
                bots.append({
                    "id": bot_id,
                    "operation_code": operation_code,
                    "stock_code": stock_code,
                    "trades_count": len(trades),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "profit_loss": stats["profit_loss"],
                    "profit_loss_percentage": stats["profit_loss_percentage"]
                })
                
            return bots
            
        except Exception as e:
            print(f"Erro ao listar bots: {str(e)}")
            return [] 