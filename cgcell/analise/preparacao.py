"""Preparação da base de análise: registros do banco -> DataFrame tipado.

Regras de transformação:
- datas em texto ISO viram `datetime64` (dia, sem hora);
- valores continuam em centavos (`int64`), para somas exatas;
- a coluna `categoria_origem` agrupa `manual` e `importado` como "Real" e
  `simulado` como "SIMULADO", para separar visualmente os dados simulados.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import pandas as pd

from cgcell.analise.tratamento import converter_datas, converter_valores
from cgcell.dominio import OrigemRegistro

COLUNAS_BASE = [
    "id_ordem_servico",
    "codigo_os",
    "data_abertura",
    "data_conclusao",
    "data_pagamento",
    "valor_servico",
    "status_os",
    "status_pagamento",
    "id_tipo_servico",
    "nome_servico",
    "origem_registro",
]
COLUNAS_DATA = ["data_abertura", "data_conclusao", "data_pagamento"]

CATEGORIA_REAL = "Real"
CATEGORIA_SIMULADO = "SIMULADO"


class FiltroOrigem(StrEnum):
    """Quais registros entram na análise."""

    REAIS = "reais"
    SIMULADOS = "simulados"
    TODOS = "todos"

    @property
    def rotulo(self) -> str:
        return {
            FiltroOrigem.REAIS: "Apenas reais",
            FiltroOrigem.SIMULADOS: "Apenas simulados",
            FiltroOrigem.TODOS: "Todos",
        }[self]


def criar_base_analise(registros: list[dict]) -> pd.DataFrame:
    """Cria o DataFrame de análise a partir dos registros (já sem OS excluídas).

    Datas e valores inválidos viram ausentes; a validação do pipeline os aponta depois.
    """
    base = pd.DataFrame.from_records(registros, columns=COLUNAS_BASE)
    base = converter_valores(converter_datas(base, COLUNAS_DATA))
    base["categoria_origem"] = (
        base["origem_registro"]
        .eq(str(OrigemRegistro.SIMULADO))
        .map({True: CATEGORIA_SIMULADO, False: CATEGORIA_REAL})
        .astype(object)
    )
    return base


def filtrar_por_origem(base: pd.DataFrame, filtro: FiltroOrigem) -> pd.DataFrame:
    simulado = base["origem_registro"].eq(str(OrigemRegistro.SIMULADO))
    if filtro == FiltroOrigem.REAIS:
        return base[~simulado]
    if filtro == FiltroOrigem.SIMULADOS:
        return base[simulado]
    return base


def filtrar_periodo(base: pd.DataFrame, coluna: str, inicio: date, fim: date) -> pd.DataFrame:
    """Mantém as linhas com `coluna` entre `inicio` e `fim`, inclusive. Datas vazias saem."""
    datas = base[coluna]
    return base[(datas >= pd.Timestamp(inicio)) & (datas <= pd.Timestamp(fim))]
