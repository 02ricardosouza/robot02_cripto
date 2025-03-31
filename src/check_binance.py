#!/usr/bin/env python3
import os
import sys
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def check_binance_connection():
    """Verifica a conexão com a Binance usando as credenciais do arquivo .env"""
    print("Verificando conexão com a Binance...")
    
    # Obter as chaves de API da Binance
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_SECRET_KEY')
    
    # Verificar se as chaves estão definidas
    if not api_key or api_key == 'sua_api_key_aqui' or not api_secret or api_secret == 'sua_secret_key_aqui':
        print("❌ ERRO: Chaves da API Binance não configuradas corretamente!")
        print("   Verifique se você configurou as variáveis BINANCE_API_KEY e BINANCE_SECRET_KEY no arquivo .env")
        return False
    
    try:
        # Tentar criar um cliente Binance
        client = Client(api_key, api_secret)
        
        # Verificar a conexão obtendo informações da conta
        status = client.get_system_status()
        account = client.get_account()
        
        print("✅ Conexão com a Binance estabelecida com sucesso!")
        print(f"Status do sistema Binance: {status['msg']}")
        print(f"Status da conta: {'Ativo' if account['canTrade'] else 'Inativo'}")
        
        # Mostrar o saldo de algumas moedas comuns
        print("\nSaldo disponível:")
        for asset in account['balances']:
            free_balance = float(asset['free'])
            if free_balance > 0:
                print(f"  {asset['asset']}: {free_balance}")
        
        return True
    
    except BinanceAPIException as e:
        print(f"❌ ERRO na API da Binance: {e.message}")
        print(f"   Código de erro: {e.code}")
        print(f"   Verifique se as chaves de API estão corretas e têm as permissões necessárias.")
        return False
    
    except Exception as e:
        print(f"❌ ERRO desconhecido: {str(e)}")
        return False

if __name__ == "__main__":
    # Executar a verificação
    success = check_binance_connection()
    
    # Sair com código de erro se a verificação falhar
    if not success:
        sys.exit(1)
    
    sys.exit(0) 