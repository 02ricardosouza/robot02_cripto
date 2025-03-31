FROM python:3.9-slim

WORKDIR /app

# Instalar dependências básicas
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar apenas o requirements primeiro
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para logs
RUN mkdir -p src/logs

# Copiar todos os arquivos
COPY . .

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "api.py"] 