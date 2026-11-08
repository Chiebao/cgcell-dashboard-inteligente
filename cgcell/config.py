"""Configurações da aplicação lidas de variáveis de ambiente.

O arquivo `.env` (opcional, fora do Git) é carregado uma única vez, na importação deste módulo.
Variáveis já definidas no sistema têm prioridade sobre as do `.env`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
NOME_PROJETO = "CG CELL Repair — Dashboard Inteligente"
CAMINHO_BANCO_PADRAO = RAIZ_PROJETO / "data" / "cgcell.db"

load_dotenv(RAIZ_PROJETO / ".env")


def obter_caminho_banco() -> Path:
    """Retorna o caminho do arquivo SQLite.

    Usa a variável `CGCELL_CAMINHO_BANCO` quando definida. Caminhos relativos são
    resolvidos a partir da raiz do projeto, para não depender da pasta onde o
    comando foi executado.
    """
    valor = os.getenv("CGCELL_CAMINHO_BANCO", "").strip()
    if not valor:
        return CAMINHO_BANCO_PADRAO
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho
