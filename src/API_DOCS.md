# Documentação da API do Robô de Criptomoedas

## Introdução

Esta API permite controlar o robô de criptomoedas, oferecendo funcionalidades para iniciar operações reais, além de permitir simulações antes de investir de verdade.

## Como executar a API

```bash
python src/run_api.py
```

A API será executada em http://localhost:5000

## Endpoints

### Status da API

```
GET /api/status
```

Retorna o status da API e informações sobre os bots ativos.

**Exemplo de resposta:**
```json
{
  "status": "online",
  "active_bots": [
    {
      "id": "btc_btcusdt",
      "operation_code": "BTCUSDT",
      "stock_code": "BTC",
      "is_active": true,
      "position": "Comprado",
      "last_buy_price": 42000.0,
      "last_sell_price": 0,
      "wallet_balance": 0.001
    }
  ]
}
```

### Iniciar Bot (Operações Reais)

```
POST /api/bot/start
```

Inicia um bot para operar com criptomoedas reais.

**Parâmetros (JSON):**
```json
{
  "stock_code": "BTC",
  "operation_code": "BTCUSDT",
  "traded_quantity": 0.001,
  "candle_period": "5m",
  "volatility_factor": 0.5,
  "stop_loss_percentage": 3,
  "acceptable_loss_percentage": 0,
  "fallback_activated": true
}
```

**Exemplo de resposta:**
```json
{
  "status": "success",
  "message": "Bot btc_btcusdt iniciado com sucesso",
  "bot_id": "btc_btcusdt"
}
```

### Parar Bot

```
POST /api/bot/stop/<bot_id>
```

Para a execução de um bot ativo.

**Exemplo de resposta:**
```json
{
  "status": "success",
  "message": "Bot btc_btcusdt parado com sucesso"
}
```

### Iniciar Simulação

```
POST /api/simulation/start
```

Inicia uma simulação de operações sem usar dinheiro real.

**Parâmetros (JSON):**
```json
{
  "stock_code": "BTC",
  "operation_code": "BTCUSDT",
  "traded_quantity": 0.001,
  "volatility_factor": 0.5,
  "stop_loss_percentage": 3
}
```

**Exemplo de resposta:**
```json
{
  "status": "success",
  "message": "Simulação sim_btc_btcusdt_1648123456 iniciada com sucesso",
  "simulation_id": "sim_btc_btcusdt_1648123456"
}
```

### Executar Passo de Simulação

```
POST /api/simulation/<sim_id>/execute
```

Executa um passo na simulação para verificar o que o bot faria com base nas condições atuais do mercado.

**Exemplo de resposta:**
```json
{
  "status": "success",
  "simulation_id": "sim_btc_btcusdt_1648123456",
  "results": {
    "status": "success",
    "trades": [
      {
        "type": "BUY",
        "price": 42000,
        "quantity": 0.001,
        "timestamp": 1648123457000,
        "total_value": 42
      }
    ],
    "buys": 1,
    "sells": 0,
    "total_buy_value": 42,
    "total_sell_value": 0,
    "current_holdings_value": 42.1,
    "profit_loss": 0.1,
    "profit_loss_percentage": 0.24,
    "stock_balance": 0.001,
    "current_price": 42100,
    "initial_price": 42000
  }
}
```

### Obter Resultados da Simulação

```
GET /api/simulation/<sim_id>/results
```

Obtém os resultados atuais da simulação.

**Exemplo de resposta:**
```json
{
  "status": "success",
  "simulation_id": "sim_btc_btcusdt_1648123456",
  "operation_code": "BTCUSDT",
  "stock_code": "BTC",
  "results": {
    "status": "success",
    "trades": [
      {
        "type": "BUY",
        "price": 42000,
        "quantity": 0.001,
        "timestamp": 1648123457000,
        "total_value": 42
      },
      {
        "type": "SELL",
        "price": 43000,
        "quantity": 0.001,
        "timestamp": 1648123557000,
        "total_value": 43
      }
    ],
    "buys": 1,
    "sells": 1,
    "total_buy_value": 42,
    "total_sell_value": 43,
    "current_holdings_value": 0,
    "profit_loss": 1,
    "profit_loss_percentage": 2.38,
    "stock_balance": 0,
    "current_price": 43100,
    "initial_price": 42000
  }
}
```

### Parar Simulação

```
POST /api/simulation/<sim_id>/stop
```

Finaliza uma simulação e retorna os resultados finais.

**Exemplo de resposta:**
```json
{
  "status": "success",
  "message": "Simulação sim_btc_btcusdt_1648123456 encerrada com sucesso",
  "final_results": {
    "status": "success",
    "trades": [
      {
        "type": "BUY",
        "price": 42000,
        "quantity": 0.001,
        "timestamp": 1648123457000,
        "total_value": 42
      },
      {
        "type": "SELL",
        "price": 43000,
        "quantity": 0.001,
        "timestamp": 1648123557000,
        "total_value": 43
      }
    ],
    "buys": 1,
    "sells": 1,
    "total_buy_value": 42,
    "total_sell_value": 43,
    "current_holdings_value": 0,
    "profit_loss": 1,
    "profit_loss_percentage": 2.38,
    "stock_balance": 0,
    "current_price": 43100,
    "initial_price": 42000
  }
}
```

## Como usar a simulação

1. Inicie uma simulação usando o endpoint `/api/simulation/start`
2. Anote o ID da simulação retornado na resposta
3. Execute passos da simulação usando `/api/simulation/<sim_id>/execute` quantas vezes desejar
4. Verifique os resultados usando `/api/simulation/<sim_id>/results`
5. Quando terminar, encerre a simulação com `/api/simulation/<sim_id>/stop`

## Como usar o bot real

1. Inicie um bot real usando o endpoint `/api/bot/start`
2. O bot começará a operar automaticamente segundo as estratégias configuradas
3. Verifique o status do bot usando `/api/status`
4. Quando desejar parar, use `/api/bot/stop/<bot_id>`

## Observações importantes

- As simulações não comprometem seu saldo real
- Os parâmetros `volatility_factor`, `stop_loss_percentage` e `acceptable_loss_percentage` podem ser ajustados para controlar o comportamento do robô
- É recomendado realizar simulações antes de iniciar operações reais
- A API utiliza as mesmas estratégias do robô original para que a simulação seja fiel ao comportamento real 