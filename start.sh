#!/bin/bash

# Ativar ambiente virtual, se existir
if [ -d "/opt/venv" ]; then
  echo "🔄 Ativando ambiente virtual..."
  source /opt/venv/bin/activate
fi

# Mudar para o diretório da aplicação
cd /app

# Verificar se as variáveis de ambiente da Binance estão configuradas
if grep -q "BINANCE_API_KEY.*sua_api_key_aqui" .env || grep -q "BINANCE_SECRET_KEY.*sua_secret_key_aqui" .env; then
  echo "⚠️  AVISO: As chaves da API Binance não foram configuradas no arquivo .env"
  echo "⚠️  O aplicativo iniciará, mas não poderá se conectar à Binance até que as chaves sejam configuradas."
  echo "⚠️  Edite o arquivo .env e reinicie o aplicativo."
else
  # Verificar se as chaves têm aspas ou espaços extras
  if grep -q 'BINANCE_API_KEY[[:space:]]*=[[:space:]]*"' .env || grep -q "BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*\"" .env; then
    echo "⚠️  AVISO: As chaves da API Binance têm aspas que podem causar problemas."
    echo "⚠️  Editando o arquivo .env para remover aspas..."
    
    # Criar um arquivo temporário sem aspas
    sed 's/BINANCE_API_KEY[[:space:]]*=[[:space:]]*"\(.*\)"/BINANCE_API_KEY=\1/g' .env > .env.tmp
    sed 's/BINANCE_SECRET_KEY[[:space:]]*=[[:space:]]*"\(.*\)"/BINANCE_SECRET_KEY=\1/g' .env.tmp > .env
    rm .env.tmp
    
    echo "✅ Arquivo .env editado com sucesso!"
  fi
  
  echo "🔑 Chaves da API Binance configuradas corretamente."
fi

# Configurar o Python Path
export PYTHONPATH=/app:/app/src:$PYTHONPATH

# Verificar se o diretório de logs existe
if [ ! -d "/app/src/logs" ]; then
  mkdir -p /app/src/logs
  echo "📂 Diretório de logs criado em /app/src/logs"
fi

# Verificar a configuração atual
echo "📊 Informações do sistema:"
echo "- Python: $(python --version)"
echo "- Diretório atual: $(pwd)"
echo "- Conteúdo do diretório: $(ls -la)"
echo "- Variáveis de ambiente: PYTHONPATH=$PYTHONPATH"

# Executar o script de verificação da Binance
echo "🧪 Testando conexão com a Binance..."
python src/check_binance.py || echo "⚠️ Não foi possível conectar à Binance. Prosseguindo com o inicialização do servidor..."

# Verificar se o arquivo run.py existe
if [ -f "run.py" ]; then
  # Iniciar a aplicação usando o novo run.py
  echo "🚀 Iniciando a API com o novo arquivo run.py..."
  exec python run.py
else
  # Arquivo run.py não encontrado, tenta usar api.py
  echo "⚠️ Arquivo run.py não encontrado. Tentando iniciar com api.py..."
  if [ -f "api.py" ]; then
    echo "🚀 Iniciando a API com api.py..."
    exec python api.py
  else
    echo "❌ Nenhum arquivo de inicialização (run.py ou api.py) encontrado!"
    exit 1
  fi
fi 