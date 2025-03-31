# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from datetime import datetime
import io

# Configuração explícita de codificação para entrada/saída padrão
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adiciona o diretório src ao path do Python para importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Verifica se a pasta de logs existe, caso contrário, cria
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

# Importa e executa a API
try:
    # Configuração do banco de dados
    from Models.database import setup_db
    
    # Configuração da autenticação
    from auth import setup_auth
    
    # Importa a aplicação Flask
    from api import app
    
    # Configuração do template com contexto para o ano atual
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    # Configuração do banco de dados
    setup_db(app)
    
    # Configuração da autenticação
    setup_auth(app)
    
    # Rotas para renderizar a interface web
    from flask import render_template
    
    @app.route('/')
    def index():
        return render_template('index.html')

    # Adiciona rota para a página de logs em tempo real
    @app.route('/logs')
    def logs_page():
        return render_template('logs.html')
    
    if __name__ == '__main__':
        print("🤖 API e Interface do Robô de Criptomoedas iniciando...")
        print("🌐 Acesse http://localhost:5001 para abrir a interface")
        print("📊 Acesse http://localhost:5001/logs para ver os logs em tempo real")
        app.run(debug=True, host='0.0.0.0', port=5001)
except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    sys.exit(1) 