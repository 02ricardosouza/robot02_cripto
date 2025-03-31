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

# Copiar run.py primeiro (solução sem exec)
COPY run.py .
RUN chmod +x run.py

# Copiar start.sh
COPY start.sh .
RUN chmod +x start.sh

# Copiar o wrapper api.py
COPY api.py .
RUN chmod +x api.py

# Copiar todos os outros arquivos
COPY . .

# Verificar se o arquivo .env existe e criar um modelo se não existir
RUN if [ ! -f .env ]; then \
    echo "AVISO: Arquivo .env não encontrado. Configure-o antes de executar o container."; \
    echo "FLASK_ENV=production\nFLASK_APP=run.py\nPYTHONUNBUFFERED=1\nPYTHONDONTWRITEBYTECODE=1" > .env; \
    fi

# Imprimir versões e informações do sistema para diagnóstico
RUN python --version && \
    pip --version && \
    ls -la && \
    echo "Verificando se run.py existe:" && \
    ls -la | grep run.py

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação (diretamente com run.py para evitar qualquer problema)
CMD ["python", "run.py"] 