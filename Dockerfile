FROM python:3.9-slim

WORKDIR /app

# Instalar dependências básicas
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar apenas os arquivos de requisitos primeiro
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para logs
RUN mkdir -p src/logs

# Copiar arquivo run.py (nova abordagem sem exec)
COPY run.py .
RUN chmod +x run.py

# Copiar todos os arquivos
COPY . .

# Verificar se o arquivo .env existe e imprimir uma mensagem se não existir
RUN if [ ! -f .env ]; then \
    echo "AVISO: Arquivo .env não encontrado. Configure-o antes de executar o container."; \
    echo "FLASK_ENV=production\nFLASK_APP=run.py\nPYTHONUNBUFFERED=1\nPYTHONDONTWRITEBYTECODE=1" > .env; \
    fi

# Adicionar um script para verificar a estrutura de diretórios e iniciar a aplicação
RUN echo '#!/bin/bash\necho "📂 Estrutura de diretórios:"\nls -la\necho "📂 Conteúdo da pasta src:"\nls -la src/\necho "🔍 Python path:"\npython -c "import sys; print(sys.path)"\necho "🔑 Verificando variáveis de ambiente da Binance:"\nif grep -q "BINANCE_API_KEY=sua_api_key_aqui" .env; then\n  echo "⚠️ AVISO: As chaves da API da Binance não foram configuradas no arquivo .env"\n  echo "⚠️ Por favor, atualize o arquivo .env com suas chaves reais da Binance"\nelse\n  echo "✅ Arquivo .env configurado corretamente"\nfi\necho "🚀 Iniciando aplicação..."\nexec python run.py' > start.sh && \
    chmod +x start.sh

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["./start.sh"] 