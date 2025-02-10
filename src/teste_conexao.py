from binance.client import Client
import os
from dotenv import load_dotenv
load_dotenv()  # Carrega as variáveis de ambiente
# api_key = "rz16Qb4BI7YGMYEf84jYnlqGlcvF4hfNORbpl0TbfcO5mgmljGM7eq7LtTR8R9qb"
# secret_key = "xjBG7ftZJX2rr0JC93bj7aY9K3UUop4Pz94wmMBqOXlrXEfjA9XPvf88AzCFunTB"
api_key = "dVU8MxpDULBMOtPHaaRmWOrRuIfl5C61xdKDxqttJB6nF8Xx55tuliUrq2LmE7zy"
secret_key = "Ve3PM7v1GMyk1inV7QZ2NF2AMd6aP5UwHIgnRXvnGYk9F0hnVw7phiv01Wuv0zzy"

client = Client(api_key, secret_key)   # Cria o cliente Binance

try:   # Testa a conexão
    account_info = client.get_account()
    balances = [  # Filtra e organiza os ativos com saldo maior que zero
        f"{balance['asset']}: {float(balance['free']):,.6f}"
        for balance in account_info['balances']
        if float(balance['free']) > 0
    ]

    if balances:   # Exibe cada ativo em uma nova linha
        print("\nSaldos disponíveis:")
        print("\n".join(balances))
    else:
        print("Nenhum saldo disponível.")

except Exception as e:
    print("Erro ao conectar à API Binance:", e)