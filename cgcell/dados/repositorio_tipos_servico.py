"""Acesso à tabela `tipo_servico`. Todas as consultas são parametrizadas."""

from __future__ import annotations

import sqlite3

from cgcell.dominio import TipoServico

_COLUNAS = "id_tipo_servico, nome_servico, descricao, ativo"


def _para_tipo_servico(linha: sqlite3.Row) -> TipoServico:
    return TipoServico(
        id_tipo_servico=linha["id_tipo_servico"],
        nome_servico=linha["nome_servico"],
        descricao=linha["descricao"],
        ativo=bool(linha["ativo"]),
    )


def inserir(conexao: sqlite3.Connection, nome_servico: str, descricao: str | None) -> int:
    """Insere um tipo de serviço ativo e retorna o id gerado."""
    cursor = conexao.execute(
        "INSERT INTO tipo_servico (nome_servico, descricao, ativo) VALUES (?, ?, 1)",
        (nome_servico, descricao),
    )
    return int(cursor.lastrowid)


def buscar_por_id(conexao: sqlite3.Connection, id_tipo_servico: int) -> TipoServico | None:
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM tipo_servico WHERE id_tipo_servico = ?",
        (id_tipo_servico,),
    ).fetchone()
    return _para_tipo_servico(linha) if linha else None


def buscar_por_nome(conexao: sqlite3.Connection, nome_servico: str) -> TipoServico | None:
    """Busca pelo nome sem diferenciar maiúsculas de minúsculas (COLLATE NOCASE)."""
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM tipo_servico WHERE nome_servico = ?",
        (nome_servico,),
    ).fetchone()
    return _para_tipo_servico(linha) if linha else None


def listar(conexao: sqlite3.Connection, somente_ativos: bool = False) -> list[TipoServico]:
    sql = f"SELECT {_COLUNAS} FROM tipo_servico"
    if somente_ativos:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome_servico COLLATE NOCASE"
    return [_para_tipo_servico(linha) for linha in conexao.execute(sql)]


def atualizar_ativo(conexao: sqlite3.Connection, id_tipo_servico: int, ativo: bool) -> None:
    conexao.execute(
        "UPDATE tipo_servico SET ativo = ? WHERE id_tipo_servico = ?",
        (int(ativo), id_tipo_servico),
    )
