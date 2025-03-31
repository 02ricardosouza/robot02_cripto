import sqlite3
import datetime

class CoinModel:
    def __init__(self, id=None, name=None, symbol=None, base_currency=None, quote_currency=None, 
                 trading_pair=None, description=None, is_active=True, created_at=None):
        self.id = id
        self.name = name  # Nome completo da moeda (ex: Bitcoin)
        self.symbol = symbol  # Símbolo da moeda (ex: BTC)
        self.base_currency = base_currency  # Moeda base (ex: BTC)
        self.quote_currency = quote_currency  # Moeda de cotação (ex: USDT)
        self.trading_pair = trading_pair  # Par de negociação (ex: BTCUSDT)
        self.description = description  # Descrição opcional
        self.is_active = is_active  # Indica se a moeda está ativa para operações
        self.created_at = created_at or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def get_db_connection():
        conn = sqlite3.connect('src/database.db')
        return conn
    
    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
    
    @staticmethod
    def init_db():
        conn = CoinModel.get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se a tabela já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coins'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            cursor.execute('''
                CREATE TABLE coins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    base_currency TEXT NOT NULL,
                    quote_currency TEXT NOT NULL,
                    trading_pair TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.commit()
            
            # Adiciona algumas moedas padrão
            default_coins = [
                ('Bitcoin', 'BTC', 'BTC', 'USDT', 'BTCUSDT', 'A maior criptomoeda do mundo', 1),
                ('Ethereum', 'ETH', 'ETH', 'USDT', 'ETHUSDT', 'Plataforma de contratos inteligentes', 1),
                ('Binance Coin', 'BNB', 'BNB', 'USDT', 'BNBUSDT', 'Token nativo da Binance', 1),
                ('XRP', 'XRP', 'XRP', 'USDT', 'XRPUSDT', 'Soluções de pagamento digital', 1),
                ('Cardano', 'ADA', 'ADA', 'USDT', 'ADAUSDT', 'Plataforma de terceira geração', 1)
            ]
            
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for coin in default_coins:
                cursor.execute('''
                    INSERT INTO coins (name, symbol, base_currency, quote_currency, trading_pair, description, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (coin[0], coin[1], coin[2], coin[3], coin[4], coin[5], coin[6], now))
            
            conn.commit()
        
        conn.close()
    
    @staticmethod
    def get_all(active_only=False):
        conn = CoinModel.get_db_connection()
        conn.row_factory = CoinModel.dict_factory
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM coins WHERE is_active = 1 ORDER BY name')
        else:
            cursor.execute('SELECT * FROM coins ORDER BY name')
            
        coins = cursor.fetchall()
        conn.close()
        
        return coins
    
    @staticmethod
    def get_by_id(coin_id):
        conn = CoinModel.get_db_connection()
        conn.row_factory = CoinModel.dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM coins WHERE id = ?', (coin_id,))
        coin = cursor.fetchone()
        
        conn.close()
        
        return coin
    
    @staticmethod
    def get_by_trading_pair(trading_pair):
        conn = CoinModel.get_db_connection()
        conn.row_factory = CoinModel.dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM coins WHERE trading_pair = ?', (trading_pair,))
        coin = cursor.fetchone()
        
        conn.close()
        
        return coin
    
    @staticmethod
    def add_coin(name, symbol, base_currency, quote_currency, trading_pair, description='', is_active=True):
        conn = CoinModel.get_db_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO coins (name, symbol, base_currency, quote_currency, trading_pair, description, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, symbol, base_currency, quote_currency, trading_pair, description, is_active, now))
            
            conn.commit()
            coin_id = cursor.lastrowid
            conn.close()
            
            return {'success': True, 'id': coin_id}
        except sqlite3.IntegrityError as e:
            conn.close()
            if 'UNIQUE constraint failed: coins.trading_pair' in str(e):
                return {'success': False, 'error': 'Par de negociação já cadastrado'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            conn.close()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def update_coin(coin_id, name, symbol, base_currency, quote_currency, trading_pair, description, is_active):
        conn = CoinModel.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verifica se o trading_pair já existe em outro registro
            cursor.execute('SELECT id FROM coins WHERE trading_pair = ? AND id != ?', (trading_pair, coin_id))
            existing = cursor.fetchone()
            
            if existing:
                conn.close()
                return {'success': False, 'error': 'Par de negociação já existe em outra moeda'}
            
            cursor.execute('''
                UPDATE coins 
                SET name = ?, symbol = ?, base_currency = ?, quote_currency = ?, 
                    trading_pair = ?, description = ?, is_active = ?
                WHERE id = ?
            ''', (name, symbol, base_currency, quote_currency, trading_pair, description, is_active, coin_id))
            
            conn.commit()
            conn.close()
            
            return {'success': True}
        except Exception as e:
            conn.close()
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def delete_coin(coin_id):
        conn = CoinModel.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verifica se existem operações usando esta moeda
            # Se existir uma tabela de operações, você deve adicionar esta verificação
            
            cursor.execute('DELETE FROM coins WHERE id = ?', (coin_id,))
            conn.commit()
            conn.close()
            
            return {'success': True}
        except Exception as e:
            conn.close()
            return {'success': False, 'error': str(e)} 