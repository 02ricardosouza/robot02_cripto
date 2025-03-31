import sqlite3
import json
import datetime
import os

class SimulationTradeModel:
    @staticmethod
    def init_db():
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        # Criar tabela de operações de simulação se não existir
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulation_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulation_id TEXT NOT NULL,
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
        CREATE INDEX IF NOT EXISTS idx_simulation_id ON simulation_trades (simulation_id)
        ''')
        
        conn.commit()
        conn.close()
        
        print("Tabela de operações de simulação inicializada com sucesso!")
    
    @staticmethod
    def register_trade(simulation_id, operation_code, trade_type, price, quantity, total_value, timestamp=None):
        """
        Registra uma operação de simulação no banco de dados
        
        Parameters:
            simulation_id (str): ID da simulação
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
        INSERT INTO simulation_trades 
        (simulation_id, operation_code, trade_type, price, quantity, total_value, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (simulation_id, operation_code, trade_type, price, quantity, total_value, timestamp))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    @staticmethod
    def get_trades_by_simulation(simulation_id):
        """
        Retorna todas as operações de uma simulação específica
        
        Parameters:
            simulation_id (str): ID da simulação
        
        Returns:
            list: Lista de dicionários com as operações
        """
        conn = sqlite3.connect('src/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM simulation_trades 
        WHERE simulation_id = ? 
        ORDER BY timestamp ASC
        ''', (simulation_id,))
        
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return trades
        
    @staticmethod
    def get_simulation_statistics(simulation_id):
        """
        Calcula estatísticas para uma simulação específica
        
        Parameters:
            simulation_id (str): ID da simulação
        
        Returns:
            dict: Dicionário com estatísticas da simulação
        """
        trades = SimulationTradeModel.get_trades_by_simulation(simulation_id)
        
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
    def delete_simulation_trades(simulation_id):
        """
        Exclui todas as operações de uma simulação específica
        
        Parameters:
            simulation_id (str): ID da simulação
        
        Returns:
            int: Número de operações excluídas
        """
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM simulation_trades WHERE simulation_id = ?', (simulation_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
        
    @staticmethod
    def get_all_simulations():
        """
        Retorna todas as simulações agrupadas por ID com estatísticas
        
        Returns:
            list: Lista de dicionários com informações de cada simulação
        """
        try:
            conn = sqlite3.connect('src/database.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Obter todos os IDs de simulação únicos sem usar funções de agregação
            cursor.execute('''
            SELECT DISTINCT simulation_id 
            FROM simulation_trades
            ''')
            
            simulation_ids = [row[0] for row in cursor.fetchall()]
            
            # Se precisarmos ordenar, podemos fazer isso em uma etapa separada
            if simulation_ids:
                # Consulta separada para obter a primeira timestamp de cada simulação
                cursor.execute('''
                SELECT simulation_id, MIN(timestamp) as first_timestamp
                FROM simulation_trades
                GROUP BY simulation_id
                ''')
                
                timestamp_map = {row['simulation_id']: row['first_timestamp'] for row in cursor.fetchall()}
                # Ordenar IDs com base nos timestamps (do mais recente para o mais antigo)
                simulation_ids.sort(key=lambda sim_id: timestamp_map.get(sim_id, ''), reverse=True)
            
            conn.close()
            
            # Construir lista de resultados com estatísticas para cada simulação
            simulations = []
            for sim_id in simulation_ids:
                # Obter primeiro trade para informações básicas
                trades = SimulationTradeModel.get_trades_by_simulation(sim_id)
                if not trades:
                    continue
                    
                first_trade = trades[0]
                stats = SimulationTradeModel.get_simulation_statistics(sim_id)
                
                # Determinar datas de início e fim
                timestamps = [trade["timestamp"] for trade in trades]
                created_at = min(timestamps) if timestamps else ""
                updated_at = max(timestamps) if timestamps else ""
                
                simulations.append({
                    "id": sim_id,
                    "operation_code": first_trade["operation_code"],
                    "trades_count": len(trades),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "profit_loss": stats["profit_loss"],
                    "profit_loss_percentage": stats["profit_loss_percentage"]
                })
                
            return simulations
            
        except Exception as e:
            print(f"Erro ao listar simulações: {str(e)}")
            return [] 