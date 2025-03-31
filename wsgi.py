import sys
import os
from pathlib import Path

# Adicionar o diretório atual ao path do Python
sys.path.append(os.getcwd())

# Verificar e criar diretório de logs
logs_dir = Path('src/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

try:
    # Importar a aplicação Flask
    from api import app as application
    
    # Para compatibilidade com Gunicorn
    app = application
    
    if __name__ == '__main__':
        print("🤖 API e Interface do Robô de Criptomoedas iniciando...")
        print("🌐 Acesse http://localhost:5000 para abrir a interface")
        app.run(debug=False, host='0.0.0.0', port=5000)
except Exception as e:
    print(f"Erro ao iniciar API: {str(e)}")
    sys.exit(1) 