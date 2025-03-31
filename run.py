#!/usr/bin/env python3
"""
Ponto de entrada principal para o Robô Cripto.
Este arquivo configura e inicia a aplicação Flask para API.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

# Configurar logging
log_dir = os.path.join('src', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'api.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

def create_app():
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__, 
                template_folder=os.path.join('src', 'templates'),
                static_folder=os.path.join('src', 'static'))
    
    # Configurar chave secreta
    app.secret_key = os.environ.get('SECRET_KEY', 'chave_secreta_padrao')
    
    # Registrar rotas principais
    
    @app.route('/health')
    def health():
        """Rota para verificar a saúde da aplicação."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'environment': os.environ.get('FLASK_ENV', 'development')
        })
    
    @app.route('/status')
    def status():
        """Verifica o status completo do sistema."""
        try:
            from src.check_binance import check_binance_connection
            binance_status = check_binance_connection()
            db_status = os.path.exists(os.path.join('src', 'database.db'))
            
            return jsonify({
                'api_status': 'online',
                'binance_connected': binance_status,
                'database_exists': db_status,
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return jsonify({
                'api_status': 'online',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    # Importar e registrar blueprint da API principal
    try:
        from src.api import init_api
        logger.info("Inicializando API principal...")
        init_api(app)
        logger.info("API principal inicializada com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao inicializar API principal: {str(e)}")
        
        # Registrar página de erro caso a API principal falhe
        @app.route('/')
        def error_page():
            return render_template('error.html', error=str(e))
    
    # Importar e registrar autenticação
    try:
        from src.auth import init_auth
        logger.info("Inicializando autenticação...")
        init_auth(app)
        logger.info("Autenticação inicializada com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao inicializar autenticação: {str(e)}")
    
    return app

def main():
    """Função principal para iniciar a aplicação."""
    try:
        app = create_app()
        port = int(os.environ.get("PORT", 5000))
        debug = os.environ.get("FLASK_ENV", "production") == "development"
        
        # Log de inicialização
        logger.info(f"Iniciando aplicação na porta {port}, debug={debug}")
        logger.info(f"Ambiente: {os.environ.get('FLASK_ENV', 'production')}")
        logger.info(f"Diretório de trabalho: {os.getcwd()}")
        
        # Iniciar servidor
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        logger.critical(f"Falha ao iniciar aplicação: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 