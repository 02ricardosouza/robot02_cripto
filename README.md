# Robô de Trading para Binance

Este projeto implementa um robô de trading automatizado para a corretora Binance, permitindo operações de compra e venda de criptomoedas baseadas em estratégias predefinidas.

## Resolução de Problema de Indentação

Foi corrigido um problema de indentação no código que causava o erro:
```
IndentationError: unexpected indent (<string>, line 33)
```

A solução foi reescrever o arquivo `api.py` para não usar `exec()` na importação do arquivo `src/api.py` e, em vez disso, reimplementar as principais rotas diretamente.

## Requisitos

- Python 3.9 ou superior
- Conta na Binance com chaves de API configuradas

## Configuração

1. Clone este repositório:
```
git clone https://github.com/seu-usuario/robo_cripto_02.git
cd robo_cripto_02
```

2. Instale as dependências:
```
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
   
   Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   ```
   FLASK_ENV=production
   FLASK_APP=src.run_api
   PYTHONUNBUFFERED=1
   PYTHONDONTWRITEBYTECODE=1
   SECRET_KEY=sua_chave_secreta_aqui
   BINANCE_API_KEY=sua_api_key_aqui
   BINANCE_SECRET_KEY=sua_secret_key_aqui
   ```

   **IMPORTANTE**: Substitua `sua_api_key_aqui` e `sua_secret_key_aqui` pelas suas chaves reais da Binance.

### Obtendo chaves da API da Binance

1. Acesse sua conta na Binance (https://www.binance.com)
2. Vá para "Gerenciamento de Conta" > "API Management"
3. Clique em "Create API" e siga as instruções de segurança
4. Configure as restrições de IP se necessário (recomendado)
5. Habilite as permissões "Enable Reading" e "Enable Spot & Margin Trading"
6. Copie a API Key e a Secret Key para o arquivo `.env`

## Execução Local

Para iniciar a aplicação localmente:

```
python api.py
```

Acesse a interface web em: http://localhost:5000

## Diagnóstico

Para verificar se tudo está configurado corretamente, acesse:

- http://localhost:5000/diagnostico-page - Interface web para diagnóstico
- http://localhost:5000/diagnostico - Informações em formato JSON
- http://localhost:5000/test_binance - Teste da conexão com a Binance

## Implantação no Docker

1. Construa a imagem Docker:
```
docker build -t robo-trading .
```

2. Execute o container:
```
docker run -p 5000:5000 --env-file .env robo-trading
```

## Implantação no EasyPanel

1. Adicione todos os arquivos ao repositório Git (incluindo os arquivos atualizados)
2. Configure o EasyPanel para usar o seu repositório
3. Configure as variáveis de ambiente (especialmente as chaves da Binance)
4. Defina a porta externa 5000
5. Configure o volume persistente para o banco de dados

## Logs e Monitoramento

- Os logs da aplicação são armazenados em `src/logs/api.log`
- A página de diagnóstico fornece informações em tempo real sobre a conexão com a Binance

## Solução de Problemas

Se você encontrar problemas com a comunicação com a Binance:

1. Verifique se as chaves da API estão corretas no arquivo `.env` (certifique-se de que não há espaços ou aspas extras)
2. Acesse a página de diagnóstico em `/diagnostico-page`
3. Clique em "Testar conexão" para verificar a comunicação com a Binance
4. Verifique os logs em `src/logs/api.log` para mais detalhes

Se você continuar enfrentando problemas, tente executar o script de verificação:
```
python src/check_binance.py
```

## Suporte

Para suporte ou dúvidas, entre em contato através das issues do GitHub ou pelo email: [seu-email@exemplo.com]
