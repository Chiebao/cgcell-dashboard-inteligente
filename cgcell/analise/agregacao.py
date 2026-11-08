"""Agregações reutilizáveis: por período e por tipo de serviço."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import pandas as pd

from cgcell.analise.preparacao import CATEGORIA_REAL


class Frequencia(StrEnum):
    """Agrupamento temporal (códigos de período do pandas)."""

    DIA = "D"
    SEMANA = "W"
    MES = "M"

    @property
    def rotulo(self) -> str:
        return {Frequencia.DIA: "Dia", Frequencia.SEMANA: "Semana", Frequencia.MES: "Mês"}[self]


def agregar_por_periodo(
    linhas: pd.DataFrame,
    coluna_data: str,
    frequencia: Frequencia,
    inicio: date | None = None,
    fim: date | None = None,
    coluna_valor: str | None = None,
    por_origem: bool = False,
    nome_resultado: str = "quantidade",
) -> pd.DataFrame:
    """Conta registros (ou soma `coluna_valor`) por período de `coluna_data`.

    - Períodos sem registro aparecem com zero (importante para gráficos e séries temporais).
    - Sem `inicio`/`fim`, usa do primeiro ao último registro.
    - `por_origem=True` separa as categorias Real e SIMULADO.
    - Colunas do resultado: `periodo` (início do período), [`categoria`], `nome_resultado`.
    """
    frequencia = Frequencia(frequencia)
    com_data = linhas.dropna(subset=[coluna_data])
    colunas = ["periodo", *(["categoria"] if por_origem else []), nome_resultado]

    if inicio is None or fim is None:
        if com_data.empty:
            return pd.DataFrame(columns=colunas)
        inicio = inicio or com_data[coluna_data].min()
        fim = fim or com_data[coluna_data].max()
    periodos = pd.period_range(start=inicio, end=fim, freq=str(frequencia))

    agrupado = com_data.assign(
        periodo=com_data[coluna_data].dt.to_period(str(frequencia)),
        categoria=com_data["categoria_origem"],
    )
    chaves = ["periodo", "categoria"] if por_origem else ["periodo"]
    grupos = agrupado.groupby(chaves)
    serie = grupos[coluna_valor].sum() if coluna_valor else grupos.size()

    if por_origem:
        categorias = sorted(com_data["categoria_origem"].unique()) or [CATEGORIA_REAL]
        indice = pd.MultiIndex.from_product([periodos, categorias], names=chaves)
    else:
        indice = pd.Index(periodos, name="periodo")
    serie = serie.reindex(indice, fill_value=0).astype("int64")

    resultado = serie.rename(nome_resultado).reset_index()
    resultado["periodo"] = resultado["periodo"].dt.start_time
    return resultado[colunas]


def agregar_por_tipo_servico(linhas: pd.DataFrame) -> pd.DataFrame:
    """Quantidade de OS e soma do valor dos serviços (centavos) por tipo.

    Atenção: `valor_servicos_centavos` é o valor dos serviços, NÃO o faturamento recebido.
    """
    agrupado = (
        linhas.groupby("nome_servico")
        .agg(
            quantidade=("id_ordem_servico", "size"),
            valor_servicos_centavos=("valor_servico", "sum"),
        )
        .reset_index()
    )
    agrupado["quantidade"] = agrupado["quantidade"].astype("int64")
    agrupado["valor_servicos_centavos"] = agrupado["valor_servicos_centavos"].astype("int64")
    return agrupado.sort_values(
        ["quantidade", "nome_servico"], ascending=[False, True]
    ).reset_index(drop=True)
