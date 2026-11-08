"""Ponto único para a interface obter uma conexão pronta para uso.

A interface não importa nada da camada de dados: abre a conexão por aqui e
repassa para as funções de serviço.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cgcell.dados.conexao import inicializar_banco
from cgcell.dados.migracoes import obter_versao_esquema


@contextmanager
def abrir_conexao(caminho: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Abre o banco (aplicando migrações pendentes) e fecha ao final do bloco `with`."""
    conexao = inicializar_banco(caminho)
    try:
        yield conexao
    finally:
        conexao.close()


def obter_versao_banco(conexao: sqlite3.Connection) -> int:
    """Versão do esquema aplicada ao banco."""
    return obter_versao_esquema(conexao)
