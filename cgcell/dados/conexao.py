"""Abertura de conexões SQLite e cópia de segurança (backup)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cgcell.config import obter_caminho_banco
from cgcell.dados.migracoes import aplicar_migracoes


def conectar(caminho: Path | str) -> sqlite3.Connection:
    """Abre uma conexão com integridade referencial ativada.

    O SQLite vem com as chaves estrangeiras DESLIGADAS por padrão; por isso o
    `PRAGMA foreign_keys = ON` precisa ser executado em toda nova conexão.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco(caminho: Path | str | None = None) -> sqlite3.Connection:
    """Conecta ao banco e aplica as migrações pendentes.

    Sem `caminho`, usa o banco configurado em `CGCELL_CAMINHO_BANCO` (ou o padrão).
    """
    conexao = conectar(caminho if caminho is not None else obter_caminho_banco())
    try:
        aplicar_migracoes(conexao)
    except Exception:
        conexao.close()
        raise
    return conexao


def fazer_backup(conexao: sqlite3.Connection, destino: Path | str) -> Path:
    """Copia o banco aberto para `destino` usando a API de backup do SQLite.

    A API de backup gera uma cópia consistente mesmo com a conexão aberta,
    o que é mais seguro do que copiar o arquivo `.db` manualmente.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    copia = sqlite3.connect(destino)
    try:
        conexao.backup(copia)
    finally:
        copia.close()
    return destino
