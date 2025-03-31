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

# Copiar todos os arquivos
COPY . .

# Adicionar um script para verificar a estrutura de diretórios no contêiner
RUN echo "#!/bin/bash\necho '📂 Estrutura de diretórios:'\nls -la\necho '📂 Conteúdo da pasta src:'\nls -la src/\necho '🔍 Python path:'\npython -c 'import sys; print(sys.path)'\necho '🚀 Iniciando aplicação...'\nexec python api.py" > start.sh && \
    chmod +x start.sh

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["./start.sh"] 