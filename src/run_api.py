#!/usr/bin/env python3
"""
Este arquivo serve apenas como um wrapper para manter a compatibilidade.
Ele importa e executa o código de run.py, que é a nova implementação
sem problemas de indentação.
"""

import os
import sys

# Obter o caminho da raiz do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

# Caminho para o arquivo run.py na raiz do projeto
run_py_path = os.path.join(root_dir, 'run.py')

# Verificar se run.py existe
if not os.path.isfile(run_py_path):
    print(f"ERRO CRÍTICO: O arquivo run.py não foi encontrado em: {run_py_path}")
    print("Certifique-se de que o arquivo run.py está presente na raiz do projeto")
    sys.exit(1)

# Imprimir informações de diagnóstico
print(f"Current directory: {current_dir}")
print(f"Root directory: {root_dir}")
print(f"run.py path: {run_py_path}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")

# Executar o run.py
print("Redirecionando para run.py para evitar problemas de indentação...")
sys.path.insert(0, root_dir)  # Adicionar a raiz ao path do Python
os.chdir(root_dir)  # Mudar para o diretório raiz
exec(open(run_py_path).read()) 