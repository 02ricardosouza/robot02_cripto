#!/usr/bin/env python3
"""
Script de diagnóstico para verificar a configuração do ambiente
e garantir que o run.py está funcionando corretamente.
"""

import os
import sys
import subprocess
import platform

def print_header(title):
    """Imprime um cabeçalho formatado."""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def check_python_version():
    """Verifica a versão do Python."""
    print_header("VERSÃO DO PYTHON")
    print(f"Python: {sys.version}")
    print(f"Executável: {sys.executable}")
    print(f"Platform: {platform.platform()}")

def check_environment_variables():
    """Verifica as variáveis de ambiente."""
    print_header("VARIÁVEIS DE AMBIENTE")
    
    # Verificar PYTHONPATH
    python_path = os.environ.get('PYTHONPATH', '')
    print(f"PYTHONPATH: {python_path}")
    
    # Verificar outras variáveis importantes
    env_vars = ['FLASK_APP', 'FLASK_ENV', 'PYTHONUNBUFFERED', 'PYTHONDONTWRITEBYTECODE']
    for var in env_vars:
        value = os.environ.get(var, 'NÃO DEFINIDA')
        print(f"{var}: {value}")

def check_required_files():
    """Verifica a existência de arquivos importantes."""
    print_header("ARQUIVOS REQUERIDOS")
    
    files_to_check = ['run.py', 'api.py', 'Procfile', 'Dockerfile', 'start.sh', '.env']
    for file in files_to_check:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file}: ENCONTRADO ({size} bytes)")
            
            # Verificar o conteúdo de arquivos críticos
            if file == 'run.py':
                with open(file, 'r') as f:
                    first_line = f.readline().strip()
                    print(f"   Primeira linha: {first_line}")
            
            elif file == 'api.py':
                with open(file, 'r') as f:
                    content = f.read(200)  # Primeiros 200 caracteres
                    print(f"   Primeiros caracteres: {content[:50]}...")
                    if 'exec(open(run_py_path).read())' in content:
                        print("   ✅ api.py redirecionando para run.py: SIM")
                    else:
                        print("   ❌ api.py redirecionando para run.py: NÃO")
            
            elif file == 'Procfile':
                with open(file, 'r') as f:
                    content = f.read().strip()
                    print(f"   Conteúdo: {content}")
                    if 'run.py' in content:
                        print("   ✅ Procfile usando run.py: SIM")
                    else:
                        print("   ❌ Procfile usando run.py: NÃO")
        else:
            print(f"❌ {file}: NÃO ENCONTRADO")

def check_python_packages():
    """Verifica os pacotes Python instalados."""
    print_header("PACOTES PYTHON")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                                capture_output=True, text=True, check=True)
        packages = result.stdout.strip().split('\n')
        
        # Mostrar apenas alguns pacotes importantes
        important_packages = ['flask', 'python-binance', 'gunicorn', 'python-dotenv']
        for package in important_packages:
            found = False
            for line in packages:
                if package.lower() in line.lower():
                    print(f"✅ {line.strip()}")
                    found = True
                    break
            if not found:
                print(f"❌ {package}: NÃO INSTALADO")
        
        print(f"\nTotal de pacotes instalados: {len(packages) - 2}")  # -2 para o cabeçalho
    except subprocess.CalledProcessError as e:
        print(f"Erro ao verificar pacotes: {e}")

def check_directory_structure():
    """Verifica a estrutura de diretórios."""
    print_header("ESTRUTURA DE DIRETÓRIOS")
    
    # Verificar src/ e seus subdiretórios
    if os.path.isdir('src'):
        print("✅ src/: ENCONTRADO")
        subdirs = [d for d in os.listdir('src') 
                  if os.path.isdir(os.path.join('src', d))]
        print(f"   Subdiretórios: {', '.join(subdirs)}")
        
        # Verificar diretório de logs
        if os.path.isdir('src/logs'):
            print("✅ src/logs/: ENCONTRADO")
        else:
            print("❌ src/logs/: NÃO ENCONTRADO")
    else:
        print("❌ src/: NÃO ENCONTRADO")

def check_env_file():
    """Verifica o arquivo .env."""
    print_header("ARQUIVO .ENV")
    
    if os.path.exists('.env'):
        print("✅ .env: ENCONTRADO")
        
        # Verificar as chaves da Binance (sem mostrar o valor completo)
        try:
            with open('.env', 'r') as f:
                content = f.read()
                
                # Verificar chave da API
                if 'BINANCE_API_KEY' in content:
                    value = content.split('BINANCE_API_KEY=')[1].split('\n')[0]
                    safe_value = value[:4] + '...' + value[-4:] if len(value) > 8 else value
                    print(f"   BINANCE_API_KEY: {safe_value}")
                    if value == 'sua_api_key_aqui':
                        print("   ❌ ATENÇÃO: Chave padrão detectada!")
                else:
                    print("   ❌ BINANCE_API_KEY: NÃO ENCONTRADA")
                
                # Verificar chave secreta
                if 'BINANCE_SECRET_KEY' in content:
                    value = content.split('BINANCE_SECRET_KEY=')[1].split('\n')[0]
                    safe_value = value[:4] + '...' + value[-4:] if len(value) > 8 else value
                    print(f"   BINANCE_SECRET_KEY: {safe_value}")
                    if value == 'sua_secret_key_aqui':
                        print("   ❌ ATENÇÃO: Chave padrão detectada!")
                else:
                    print("   ❌ BINANCE_SECRET_KEY: NÃO ENCONTRADA")
        except Exception as e:
            print(f"   Erro ao ler .env: {e}")
    else:
        print("❌ .env: NÃO ENCONTRADO")

def check_run_py():
    """Verifica se run.py pode ser importado corretamente."""
    print_header("TESTE DE IMPORTAÇÃO DE RUN.PY")
    
    if os.path.exists('run.py'):
        try:
            import run
            print("✅ Importação de run.py: SUCESSO")
        except Exception as e:
            print(f"❌ Erro ao importar run.py: {e}")
    else:
        print("❌ run.py: NÃO ENCONTRADO")

def main():
    """Função principal."""
    print("\n🔍 DIAGNÓSTICO DO AMBIENTE\n")
    print(f"Data/Hora: {subprocess.check_output('date', text=True).strip()}")
    print(f"Diretório atual: {os.getcwd()}")
    
    # Executar verificações
    check_python_version()
    check_environment_variables()
    check_required_files()
    check_directory_structure()
    check_env_file()
    
    print("\n🚀 DIAGNÓSTICO CONCLUÍDO!\n")
    print("Para iniciar a aplicação, execute:")
    print("  python run.py")
    print("\nSe encontrar problemas, execute:")
    print("  bash iniciar.sh")

if __name__ == "__main__":
    main() 