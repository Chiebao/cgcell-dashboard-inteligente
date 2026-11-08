"""Migrações versionadas do esquema do banco.

Cada arquivo `NNNN_descricao.sql` desta pasta é uma versão do esquema.
A tabela `versao_esquema` registra quais versões já foram aplicadas, então
cada migração roda uma única vez e na ordem numérica. Para mudar o esquema,
crie um novo arquivo com o próximo número; nunca edite uma migração já aplicada.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

PASTA_MIGRACOES = Path(__file__).resolve().parent
_PADRAO_ARQUIVO = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def listar_migracoes(pasta: Path = PASTA_MIGRACOES) -> list[tuple[int, Path]]:
    """Retorna as migrações da pasta como pares (versão, arquivo), em ordem."""
    migracoes: dict[int, Path] = {}
    for arquivo in pasta.glob("*.sql"):
        encontrado = _PADRAO_ARQUIVO.match(arquivo.name)
        if not encontrado:
            raise ValueError(f"Nome de migração fora do padrão NNNN_descricao.sql: {arquivo.name}")
        versao = int(encontrado.group(1))
        if versao in migracoes:
            raise ValueError(f"Duas migrações com a mesma versão {versao:04d}.")
        migracoes[versao] = arquivo
    return sorted(migracoes.items())


def obter_versao_esquema(conexao: sqlite3.Connection) -> int:
    """Versão mais recente aplicada ao banco (0 se nenhuma)."""
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS versao_esquema (
            versao       INTEGER PRIMARY KEY,
            nome_arquivo TEXT NOT NULL,
            aplicada_em  TEXT NOT NULL
        )
        """
    )
    conexao.commit()
    linha = conexao.execute("SELECT COALESCE(MAX(versao), 0) FROM versao_esquema").fetchone()
    return int(linha[0])


def aplicar_migracoes(conexao: sqlite3.Connection, pasta: Path = PASTA_MIGRACOES) -> list[str]:
    """Aplica, em ordem, as migrações ainda não aplicadas.

    Cada migração roda numa transação própria: se der erro no meio, nada
    daquela migração fica gravado. Retorna os nomes dos arquivos aplicados.
    """
    versao_atual = obter_versao_esquema(conexao)
    aplicadas: list[str] = []
    for versao, arquivo in listar_migracoes(pasta):
        if versao <= versao_atual:
            continue
        sql = arquivo.read_text(encoding="utf-8")
        try:
            # executescript confirma qualquer transação pendente e depois roda o script;
            # o BEGIN no início mantém a migração e o registro da versão juntos.
            conexao.executescript("BEGIN;\n" + sql)
            conexao.execute(
                "INSERT INTO versao_esquema (versao, nome_arquivo, aplicada_em) VALUES (?, ?, ?)",
                (versao, arquivo.name, datetime.now().isoformat(sep=" ", timespec="seconds")),
            )
            conexao.commit()
        except Exception:
            if conexao.in_transaction:
                conexao.rollback()
            raise
        aplicadas.append(arquivo.name)
    return aplicadas
