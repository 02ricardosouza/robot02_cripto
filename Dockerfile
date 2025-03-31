FROM python:3.9-slim

# Configurar variáveis de ambiente
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PORT=5000

# Criar diretório da aplicação
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas o requirements.txt primeiro
COPY ./requirements.txt /app/

# Instalar dependências Python
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copiar o resto do código
COPY . /app/

# Criar diretório de logs se não existir
RUN mkdir -p ./src/logs

# Expor porta
EXPOSE $PORT

# Comando para iniciar a aplicação
CMD ["sh", "-c", "gunicorn --workers=2 --bind=0.0.0.0:$PORT src.run_api:app"] 