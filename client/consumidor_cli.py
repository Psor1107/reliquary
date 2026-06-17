import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from reliquary.vault import Vault, VaultError
from reliquary.database import SQLiteStorage

def main():
    if len(sys.argv) != 3:
        print("Uso: python consumidor_cli.py <MASTER_PASSWORD> <PATH_DO_SEGREDO>")
        sys.exit(1)

    senha_mestra = sys.argv[1]
    caminho_segredo = sys.argv[2]

    storage = SQLiteStorage()
    cofre = Vault(storage=storage)

    try:
        cofre.unlock(senha_mestra)
        texto_plano = cofre.get_secret(caminho_segredo)
        print(texto_plano) 
        
    except VaultError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()