import os
import sys

print("\n[BACKEND - Python] Booting up...")
api_key = os.getenv("API_KEY")
db_url = os.getenv("DB_MOCK_URL")

if api_key and db_url:
    print(f"   [+] Conectado à API com token: {api_key}")
    print(f"   [+] Senha do Banco de dados: {db_url}")
else:
    print("   [-] ERRO: Variáveis de ambiente não encontradas!")
    sys.exit(1)