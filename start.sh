#!/bin/bash

# Script de inicialização simplificado que usa DIRETAMENTE run.py
# sem qualquer dependência de api.py para evitar problemas de indentação

echo "🔍 Verificando ambiente..."
echo "- Python: $(python --version)"
echo "- Diretório atual: $(pwd)"
echo "- Conteúdo do diretório: $(ls -la | grep -E '(run\.py|api\.py|Procfile)')"

# Ativar ambiente virtual, se existir
if [ -d "/opt/venv" ]; then
  echo "🔄 Ativando ambiente virtual..."
  source /opt/venv/bin/activate
fi

# Verificar se o arquivo run.py existe
if [ ! -f "run.py" ]; then
  echo "❌ ERRO CRÍTICO: O arquivo run.py não foi encontrado!"
  echo "Arquivos disponíveis:"
  ls -la
  exit 1
fi

# Configurar o Python Path
export PYTHONPATH=/app:/app/src:$PYTHONPATH
echo "✅ PYTHONPATH configurado: $PYTHONPATH"

# Verificar se o diretório de logs existe
if [ ! -d "src/logs" ]; then
  mkdir -p src/logs
  echo "✅ Diretório de logs criado em src/logs"
fi

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
  echo "⚠️ Arquivo .env não encontrado. Criando um modelo..."
  echo "FLASK_ENV=production
FLASK_APP=run.py
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
SECRET_KEY=chave_secreta_padrao_para_desenvolvimento
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET_KEY=sua_secret_key_aqui" > .env
  echo "✅ Arquivo .env criado!"
else
  # Verificar se as chaves da Binance estão configuradas
  if grep -q "BINANCE_API_KEY.*sua_api_key_aqui" .env || grep -q "BINANCE_SECRET_KEY.*sua_secret_key_aqui" .env; then
    echo "⚠️ AVISO: As chaves da API Binance não foram configuradas no arquivo .env"
    echo "⚠️ O aplicativo iniciará, mas não poderá se conectar à Binance até que as chaves sejam configuradas."
  else
    # Verificar e remover aspas das chaves se necessário
    if grep -q 'BINANCE_API_KEY[[:space:]]*=[[:space:]]*"' .env || grep -q "BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*\"" .env; then
      echo "⚠️ AVISO: Removendo aspas das chaves da API Binance..."
      sed -i 's/BINANCE_API_KEY[[:space:]]*=[[:space:]]*"\(.*\)"/BINANCE_API_KEY=\1/g' .env
      sed -i 's/BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*"\(.*\)"/BINANCE_SECRET_KEY=\1/g' .env
      echo "✅ Aspas removidas!"
    fi
    echo "✅ Chaves da API Binance configuradas no arquivo .env"
  fi
fi

echo "🚀 Iniciando aplicação DIRETAMENTE com run.py..."
echo "===================================================="
# Executar diretamente o run.py para evitar qualquer problema de indentação
exec python run.py 