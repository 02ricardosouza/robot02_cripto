#!/usr/bin/env python3
"""
Este arquivo serve apenas como um wrapper para manter a compatibilidade.
Ele importa e executa o código de run.py, que é a nova implementação
sem problemas de indentação.
"""

import os
import sys

# Verificar se run.py existe
run_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run.py')
if not os.path.isfile(run_py_path):
    print(f"ERRO CRÍTICO: O arquivo run.py não foi encontrado em: {run_py_path}")
    print("Certifique-se de que o arquivo run.py está presente no mesmo diretório que api.py")
    sys.exit(1)

# Executar o run.py
print("Redirecionando para run.py para evitar problemas de indentação...")
exec(open(run_py_path).read()) 