FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar o código da aplicação
COPY . .

# Tornar o script de setup executável
RUN chmod +x setup.sh

# Instalar dependências Python
RUN ./setup.sh

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:5000", "src.run_api:app"] 