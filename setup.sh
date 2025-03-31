#!/bin/bash

echo ">>> Instalando dependências do Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Criando diretório de logs..."
mkdir -p src/logs

echo ">>> Configuração concluída!" 