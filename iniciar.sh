#!/bin/bash

# Este é um script de início rápido que executa diretamente o run.py
# para evitar problemas com outros arquivos de inicialização.

echo "🔍 Verificando a existência do run.py..."
if [ ! -f "run.py" ]; then
  echo "❌ ERRO: O arquivo run.py não foi encontrado no diretório atual!"
  echo "Certifique-se de estar no diretório raiz do projeto."
  exit 1
fi

echo "✅ run.py encontrado!"
echo "🔧 Verificando ambiente Python..."
python --version

# Verificar se o diretório de logs existe
if [ ! -d "src/logs" ]; then
  echo "📁 Criando diretório de logs..."
  mkdir -p src/logs
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
  echo "⚠️ Arquivo .env não encontrado. Criando modelo..."
  echo "FLASK_ENV=production
FLASK_APP=run.py
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
SECRET_KEY=chave_secreta_padrao_para_desenvolvimento
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET_KEY=sua_secret_key_aqui" > .env
  echo "✅ Arquivo .env criado! Edite-o para configurar suas chaves da Binance."
fi

echo "🚀 Iniciando aplicação diretamente usando run.py..."
python run.py 