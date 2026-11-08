"""Acesso à tabela `ordem_servico`. Todas as consultas são parametrizadas.

Conversões feitas aqui (e só aqui):
- `date` <-> texto ISO `AAAA-MM-DD`;
- `datetime` <-> texto ISO `AAAA-MM-DD HH:MM:SS`;
- booleanos <-> 0/1.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from cgcell.dominio import (
    DadosOrdemServico,
    OrdemServico,
    OrigemRegistro,
    StatusOS,
    StatusPagamento,
)

_COLUNAS = (
    "id_ordem_servico, codigo_os, data_abertura, data_conclusao, valor_servico, status_os, "
    "status_pagamento, data_pagamento, id_tipo_servico, origem_registro, excluida, "
    "excluida_em, criado_em, atualizado_em"
)


def _data_para_texto(valor: date | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def _momento_para_texto(valor: datetime) -> str:
    return valor.isoformat(sep=" ", timespec="seconds")


def _texto_para_data(valor: str | None) -> date | None:
    return date.fromisoformat(valor) if valor else None


def _texto_para_momento(valor: str | None) -> datetime | None:
    return datetime.fromisoformat(valor) if valor else None


def _para_ordem_servico(linha: sqlite3.Row) -> OrdemServico:
    return OrdemServico(
        id_ordem_servico=linha["id_ordem_servico"],
        codigo_os=linha["codigo_os"],
        data_abertura=date.fromisoformat(linha["data_abertura"]),
        data_conclusao=_texto_para_data(linha["data_conclusao"]),
        valor_servico=linha["valor_servico"],
        status_os=StatusOS(linha["status_os"]),
        status_pagamento=StatusPagamento(linha["status_pagamento"]),
        data_pagamento=_texto_para_data(linha["data_pagamento"]),
        id_tipo_servico=linha["id_tipo_servico"],
        origem_registro=OrigemRegistro(linha["origem_registro"]),
        excluida=bool(linha["excluida"]),
        excluida_em=_texto_para_momento(linha["excluida_em"]),
        criado_em=datetime.fromisoformat(linha["criado_em"]),
        atualizado_em=datetime.fromisoformat(linha["atualizado_em"]),
    )


def _parametros(dados: DadosOrdemServico) -> dict[str, Any]:
    return {
        "codigo_os": dados.codigo_os,
        "data_abertura": _data_para_texto(dados.data_abertura),
        "data_conclusao": _data_para_texto(dados.data_conclusao),
        "valor_servico": dados.valor_servico,
        "status_os": str(dados.status_os),
        "status_pagamento": str(dados.status_pagamento),
        "data_pagamento": _data_para_texto(dados.data_pagamento),
        "id_tipo_servico": dados.id_tipo_servico,
    }


def inserir(
    conexao: sqlite3.Connection,
    dados: DadosOrdemServico,
    origem_registro: OrigemRegistro,
    momento: datetime,
) -> int:
    """Insere a OS e retorna o id gerado. `criado_em` e `atualizado_em` recebem `momento`."""
    parametros = _parametros(dados) | {
        "origem_registro": str(origem_registro),
        "momento": _momento_para_texto(momento),
    }
    cursor = conexao.execute(
        """
        INSERT INTO ordem_servico (
            codigo_os, data_abertura, data_conclusao, valor_servico, status_os,
            status_pagamento, data_pagamento, id_tipo_servico, origem_registro,
            criado_em, atualizado_em
        ) VALUES (
            :codigo_os, :data_abertura, :data_conclusao, :valor_servico, :status_os,
            :status_pagamento, :data_pagamento, :id_tipo_servico, :origem_registro,
            :momento, :momento
        )
        """,
        parametros,
    )
    return int(cursor.lastrowid)


def buscar_por_id(
    conexao: sqlite3.Connection, id_ordem_servico: int, incluir_excluidas: bool = False
) -> OrdemServico | None:
    sql = f"SELECT {_COLUNAS} FROM ordem_servico WHERE id_ordem_servico = ?"
    if not incluir_excluidas:
        sql += " AND excluida = 0"
    linha = conexao.execute(sql, (id_ordem_servico,)).fetchone()
    return _para_ordem_servico(linha) if linha else None


def existe_codigo(
    conexao: sqlite3.Connection, codigo_os: str, ignorar_id: int | None = None
) -> bool:
    """Verifica se o código já existe, inclusive em OS excluídas (o código nunca é reutilizado)."""
    linha = conexao.execute(
        "SELECT 1 FROM ordem_servico WHERE codigo_os = ? AND id_ordem_servico IS NOT ?",
        (codigo_os, ignorar_id),
    ).fetchone()
    return linha is not None


def listar(conexao: sqlite3.Connection, incluir_excluidas: bool = False) -> list[OrdemServico]:
    """Lista as OS da mais recente para a mais antiga (por data de abertura)."""
    sql = f"SELECT {_COLUNAS} FROM ordem_servico"
    if not incluir_excluidas:
        sql += " WHERE excluida = 0"
    sql += " ORDER BY data_abertura DESC, id_ordem_servico DESC"
    return [_para_ordem_servico(linha) for linha in conexao.execute(sql)]


def listar_para_analise(conexao: sqlite3.Connection) -> list[dict[str, Any]]:
    """Registros para os indicadores: OS não excluídas, com o nome do tipo de serviço.

    Retorna valores crus do banco (datas em texto ISO); a conversão de tipos fica
    na camada de análise.
    """
    linhas = conexao.execute(
        """
        SELECT o.id_ordem_servico, o.codigo_os, o.data_abertura, o.data_conclusao,
               o.data_pagamento, o.valor_servico, o.status_os, o.status_pagamento,
               o.id_tipo_servico, t.nome_servico, o.origem_registro
          FROM ordem_servico AS o
          JOIN tipo_servico AS t ON t.id_tipo_servico = o.id_tipo_servico
         WHERE o.excluida = 0
        """
    )
    return [dict(linha) for linha in linhas]


def atualizar(
    conexao: sqlite3.Connection,
    id_ordem_servico: int,
    dados: DadosOrdemServico,
    momento: datetime,
) -> None:
    """Grava os campos editáveis e atualiza `atualizado_em`."""
    parametros = _parametros(dados) | {
        "id_ordem_servico": id_ordem_servico,
        "momento": _momento_para_texto(momento),
    }
    conexao.execute(
        """
        UPDATE ordem_servico SET
            codigo_os = :codigo_os,
            data_abertura = :data_abertura,
            data_conclusao = :data_conclusao,
            valor_servico = :valor_servico,
            status_os = :status_os,
            status_pagamento = :status_pagamento,
            data_pagamento = :data_pagamento,
            id_tipo_servico = :id_tipo_servico,
            atualizado_em = :momento
        WHERE id_ordem_servico = :id_ordem_servico
        """,
        parametros,
    )


def marcar_excluida(conexao: sqlite3.Connection, id_ordem_servico: int, momento: datetime) -> None:
    """Exclusão lógica: o registro continua no banco, apenas marcado."""
    texto = _momento_para_texto(momento)
    conexao.execute(
        """
        UPDATE ordem_servico
           SET excluida = 1, excluida_em = ?, atualizado_em = ?
         WHERE id_ordem_servico = ?
        """,
        (texto, texto, id_ordem_servico),
    )
