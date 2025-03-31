import sqlite3
import os
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, password, is_admin=False):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin

    @staticmethod
    def get_db_connection():
        conn = sqlite3.connect('src/database.db')
        return conn
        
    @staticmethod
    def dict_factory(cursor, row):
        """Converter rows do SQLite para dicionário"""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    @staticmethod
    def get_by_id(user_id):
        conn = sqlite3.connect('src/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                is_admin=bool(user_data['is_admin'])
            )
        return None

    @staticmethod
    def get_by_username(username):
        conn = sqlite3.connect('src/database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                is_admin=bool(user_data['is_admin'])
            )
        return None

    @staticmethod
    def create_user(username, password_hash, is_admin=False):
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                (username, password_hash, is_admin)
            )
            conn.commit()
            
            # Obter o ID do usuário recém-criado
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            user_id = cursor.fetchone()[0]
            
            conn.close()
            return User(id=user_id, username=username, password=password_hash, is_admin=is_admin)
        except sqlite3.IntegrityError:
            # Usuário já existe
            conn.close()
            return None

    @staticmethod
    def init_db():
        conn = sqlite3.connect('src/database.db')
        cursor = conn.cursor()
        
        # Verificar se a tabela já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT 0
                )
            ''')
            conn.commit()
        
        conn.close() 