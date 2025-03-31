import os
import sys
from pathlib import Path

# Verifica se a pasta de logs existe, caso contrário, cria
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

# Importa e executa a API
try:
    from api import app
    from flask import render_template, redirect, url_for
    from flask_login import login_required, current_user
    
    # Adiciona rota para renderizar a interface web
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')

    # Adiciona rota para a página de logs em tempo real
    @app.route('/logs')
    @login_required
    def logs_page():
        return render_template('logs.html')
    
    # Adiciona rota para a página de gerenciamento de moedas
    @app.route('/coins')
    @login_required
    def coins_page():
        # Apenas administradores podem gerenciar moedas
        if not current_user.is_admin:
            return redirect(url_for('index'))
        return render_template('coins.html')
    
    # Rota raiz redireciona para login se não estiver autenticado
    @app.route('/home')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return redirect(url_for('auth.login'))
    
    if __name__ == '__main__':
        print("🤖 API e Interface do Robô de Criptomoedas iniciando...")
        print("🌐 Acesse http://localhost:5000 para abrir a interface")
        print("📊 Acesse http://localhost:5000/logs para ver os logs em tempo real")
        app.run(debug=True, host='127.0.0.1', port=5000)
except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    sys.exit(1) 