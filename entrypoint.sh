#!/bin/bash

echo "🤖 Iniciando a aplicação..."
echo "👉 Diretórios no path do Python:"
python -c "import sys; print('\n'.join(sys.path))"
echo "👉 Verificando módulos..."
python -c "import app; print('✅ Módulo app importado com sucesso!')"
echo "🚀 Iniciando o servidor Gunicorn..."

# Criar diretório de logs se não existir
mkdir -p src/logs

# Iniciar o servidor Gunicorn
exec gunicorn --workers=2 --bind=0.0.0.0:5000 app:app 