"""Script auxiliar para gerar o banco de dados efêmero no GitHub Actions."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from reliquary.database import SQLiteStorage
from reliquary.vault import Vault


def main() -> None:
    db_path = Path("ci_dummy.db")
    
    # Remove o banco se já existir (para evitar erros se rodado localmente 2x)
    if db_path.exists():
        db_path.unlink()

    print(f"Criando cofre efêmero para CI/CD em {db_path}...")
    
    storage = SQLiteStorage(db_path=db_path)
    vault = Vault(storage=storage)
    
    # Cria o cofre com a senha fixa da esteira
    master_password = os.environ["MASTER_PASSWORD"]
    vault.create_vault(master_password)
    
    # Insere os exatos caminhos que o manifesto secrets.yml espera
    vault.add_secret("dev/api_key", "ci-test-token-123")
    vault.add_secret("prod/db_pass", "ci-test-db-pass")
    
    print("Banco populado com sucesso e pronto para injeção!")


if __name__ == "__main__":
    main()