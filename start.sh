#!/bin/bash

# Ativar ambiente virtual
source /opt/venv/bin/activate

# Mudar para o diretório da aplicação
cd /app

# Iniciar a aplicação
python src/run_api.py 