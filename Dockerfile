# Usar uma imagem base do Python
FROM python:3.9-slim

# Definir diretório de trabalho
WORKDIR /app

# Copiar os arquivos de requisitos
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Dar permissão de execução ao script de inicialização
RUN chmod +x start.sh

# Expor a porta que a aplicação usa
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["./start.sh"] 