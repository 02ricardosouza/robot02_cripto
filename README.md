# Robô de Trading de Criptomoedas

## Visão Geral
Este é um robô automatizado para trading de criptomoedas usando a API da Binance.

## Configuração do Ambiente

### Requisitos
- Python 3.9
- Conta na Binance com API Key e Secret Key

### Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```
FLASK_APP=app:app
FLASK_ENV=production
PORT=5000
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_SECRET_KEY=sua_secret_key_aqui
```

## Instalação

### Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar a aplicação
python app.py
```

### Docker
```bash
# Construir a imagem
docker build -t robo-cripto .

# Executar o container
docker run -p 5000:5000 --env-file .env robo-cripto
```

## Deploy no EasyPanel
1. Faça o fork deste repositório
2. No EasyPanel, crie um novo serviço usando o repositório
3. Configure as variáveis de ambiente necessárias
4. Inicie o deploy

## Estrutura do Projeto
- `app.py`: Arquivo principal da aplicação
- `src/`: Diretório com os módulos do projeto
  - `api.py`: API Flask para interação com o robô
  - `modules/`: Módulos do robô de trading
  - `strategies/`: Estratégias de trading
  - `indicators/`: Indicadores técnicos
  - `Models/`: Modelos de dados
  - `auth/`: Sistema de autenticação
  - `templates/`: Templates HTML
  - `static/`: Arquivos estáticos (CSS, JS, imagens)

## Licença
Este projeto é distribuído sob licença privada.

# PARA DÚVIDAS E SUGESTÕES, PARTICIPE DO NOSSO DISCORD

    https://discord.gg/PpmB3DwSSX

    Inscreva-se no meu canal no YouTube https://www.youtube.com/@DescolaDev

# 1. Instale as seguintes bibliotecas:

    Digite no terminal (abra o terminal com ctrl+J):

    pip install pandas python-binance python-dotenv

# 2. Insira suas chaves da Binance no documento .env

    🟡 IMPORTANTE: Elas devem estar entre aspas duplas

# 3. Ative o interpretador no VsCode. Selecione Python -> Conda/Base

    Ctrl + shift + P

    Digitar Interpretador -> Selecionar Interpretador

    Escolher Python -> "Base"

    🟡 IMPORTANTE: Depois de selecionar o interpretador, clique no ícone da LIXEIRA e abra o terminal novamente.

# 4. Configure o bot e suas variáveis

    Agora a configuração é feita no arquivo .\src\main.py

# 5. Código para rodar o bot

    Digite no terminal:

    python .\src\main.py

Atenção: O mercado de ações e criptomoedas é altamente volátil. O uso deste robô é por sua conta e risco. Nossa equipe não se responsabiliza por quaisquer perdas financeiras que possam ocorrer. Este código é apenas para fins educacionais e não constitui aconselhamento financeiro.
