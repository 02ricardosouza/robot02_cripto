# Robô Cripto

Sistema automatizado para negociação de criptomoedas utilizando a API da Binance.

## Requisitos

- Python 3.9 ou superior
- Pip (gerenciador de pacotes Python)
- Conta na Binance com chaves de API configuradas

## Configuração Inicial

1. Clone este repositório:
   ```
   git clone https://github.com/seu-usuario/robo_cripto_02.git
   cd robo_cripto_02
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure o arquivo `.env` na raiz do projeto:
   ```
   FLASK_ENV=development
   FLASK_APP=src.run_api
   PYTHONUNBUFFERED=1
   PYTHONDONTWRITEBYTECODE=1
   SECRET_KEY=chave_secreta_para_flask
   BINANCE_API_KEY=sua_api_key_aqui
   BINANCE_SECRET_KEY=sua_secret_key_aqui
   ```

4. Crie a pasta de logs:
   ```
   mkdir -p src/logs
   ```

## Executando a Aplicação

### Método 1: Usando run.py (Recomendado)

Execute o script principal:
```
python run.py
```

### Método 2: Usando o script iniciar.sh

No Linux ou macOS:
```
bash iniciar.sh
```

### Método 3: Usando Docker

1. Construa a imagem Docker:
   ```
   docker build -t robo_cripto .
   ```

2. Execute o container:
   ```
   docker run -p 5000:5000 robo_cripto
   ```

## Diagnóstico

Se você estiver enfrentando problemas, execute o script de diagnóstico:

```
python diagnostico.py
```

Este script verificará:
- Versão do Python
- Variáveis de ambiente
- Arquivos necessários
- Estrutura de diretórios
- Configuração das chaves da Binance

## Estrutura do Projeto

```
robo_cripto_02/
├── .env                     # Variáveis de ambiente
├── run.py                   # Script principal para iniciar a aplicação
├── api.py                   # Wrapper para executar run.py
├── diagnostico.py           # Script de diagnóstico do ambiente
├── iniciar.sh               # Script de inicialização para Linux/macOS
├── Dockerfile               # Configuração para Docker
├── requirements.txt         # Dependências Python
├── Procfile                 # Configuração para deploy
└── src/                     # Código-fonte principal
    ├── auth/                # Autenticação e rotas
    ├── crypto/              # Integração com criptomoedas
    ├── indicators/          # Indicadores técnicos
    ├── Models/              # Modelos de dados
    ├── modules/             # Módulos auxiliares
    ├── strategies/          # Estratégias de negociação
    ├── static/              # Arquivos estáticos
    ├── templates/           # Templates HTML
    ├── user/                # Gerenciamento de usuários
    └── logs/                # Logs da aplicação
```

## Resolução de Problemas Comuns

### 1. Erro ao conectar com a API da Binance

Verifique:
- Se suas chaves de API estão configuradas corretamente no arquivo `.env`
- Se as permissões das chaves incluem "Leitura" e "Trading" na plataforma da Binance
- Se sua conexão com a internet está funcionando

### 2. Erro ao iniciar a aplicação

Verifique:
- Se o arquivo `run.py` existe na raiz do projeto
- Se todas as dependências foram instaladas corretamente
- Execute o script de diagnóstico para identificar o problema

### 3. Problemas com Docker

Se o container não iniciar corretamente:
- Verifique os logs do Docker: `docker logs [container_id]`
- Certifique-se de que o Dockerfile está correto
- Verifique se as portas estão mapeadas corretamente

## Contato e Suporte

Para suporte ou mais informações, entre em contato:
- Email: seu-email@exemplo.com
- GitHub: https://github.com/seu-usuario
