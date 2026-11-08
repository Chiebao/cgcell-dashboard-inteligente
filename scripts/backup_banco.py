"""Cria uma cópia de segurança do banco SQLite da aplicação.

Uso (na raiz do projeto, com o ambiente virtual ativado):

    python -m scripts.backup_banco

A cópia é gravada em `backups/cgcell_AAAAMMDD_HHMMSS.db` (pasta fora do Git).
Para recuperar, veja docs/banco_de_dados.md.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from cgcell.config import RAIZ_PROJETO, obter_caminho_banco
from cgcell.dados.conexao import conectar, fazer_backup

PASTA_BACKUPS = RAIZ_PROJETO / "backups"


def main(pasta_destino: Path = PASTA_BACKUPS) -> int:
    origem = obter_caminho_banco()
    if not origem.exists():
        print(f"Banco não encontrado em {origem}. Nada para copiar.")
        return 1

    destino = pasta_destino / f"cgcell_{datetime.now():%Y%m%d_%H%M%S}.db"
    conexao = conectar(origem)
    try:
        fazer_backup(conexao, destino)
    finally:
        conexao.close()
    print(f"Backup criado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
