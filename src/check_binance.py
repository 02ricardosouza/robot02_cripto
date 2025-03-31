#!/usr/bin/env python3
"""
Script para verificar a conexão com a Binance e exibir informações sobre o status.
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Tentar importar a binance
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    print("❌ ERRO: Módulo binance não encontrado!")
    print("Execute: pip install python-binance")
    sys.exit(1)

def main():
    """Função principal para testar a conexão com a Binance."""
    # Carregar variáveis de ambiente
    load_dotenv()
    
    # Obter as chaves da API da Binance
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_SECRET_KEY')
    
    if not api_key or not api_secret:
        print("❌ ERRO: Chaves da API Binance não encontradas no ambiente!")
        print("Certifique-se de definir BINANCE_API_KEY e BINANCE_SECRET_KEY no arquivo .env")
        sys.exit(1)
    
    # Verificar se as chaves são as padrões do modelo
    if api_key == "sua_api_key_aqui" or api_secret == "sua_secret_key_aqui":
        print("❌ ERRO: Você está usando as chaves padrão do modelo!")
        print("Edite o arquivo .env e insira suas próprias chaves da Binance.")
        sys.exit(1)
    
    print(f"⏳ Conectando à Binance em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        # Criar um cliente Binance
        client = Client(api_key, api_secret)
        
        # Verificar o status do sistema
        status = client.get_system_status()
        
        # Verificar o status da conta
        account = client.get_account()
        
        # Verificar permissões de trading
        perms = "Sim" if "SPOT" in account.get("permissions", []) else "Não"
        
        # Exibir resultados
        print("\n✅ Conexão com a Binance estabelecida com sucesso!")
        print(f"Status do sistema: {status['msg'] if status['status'] == 0 else 'manutenção'}")
        print(f"Permissão para operar: {perms}")
        print(f"\nDetalhes da conta:")
        print(f"- Nível de Maker: {account.get('makerCommission', 'N/A')}")
        print(f"- Nível de Taker: {account.get('takerCommission', 'N/A')}")
        print(f"- Número de ativos: {len(account.get('balances', []))}")
        
        # Mensagem de status completa para uso em outros sistemas
        status_msg = f"Conexão com a Binance estabelecida com sucesso! Status do sistema: {status['msg'] if status['status'] == 0 else 'manutenção'} | Permissão para operar: {perms}"
        print(f"\nMensagem de status: {status_msg}")
        
        return 0  # Sucesso
        
    except BinanceAPIException as e:
        print(f"❌ ERRO Binance API: {e.message} (código: {e.code})")
        return 1  # Erro
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        return 1  # Erro

if __name__ == "__main__":
    sys.exit(main()) 