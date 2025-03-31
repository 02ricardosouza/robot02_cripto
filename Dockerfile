FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar apenas os requisitos primeiro
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para logs
RUN mkdir -p src/logs

# Copiar o restante do código para a pasta correta
COPY . .

# Tornar os scripts executáveis
RUN chmod +x app.py entrypoint.sh

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["./entrypoint.sh"] 