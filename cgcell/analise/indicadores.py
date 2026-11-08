"""Indicadores gerenciais calculados sobre a base de análise.

Regras de cálculo (seção 6 do AGENTS.md):
- faturamento recebido: somente OS PAGAS, filtradas pela DATA DE PAGAMENTO;
- volume de OS: filtrado pela DATA DE ABERTURA;
- OS canceladas não contam como concluídas nem entram nos serviços mais frequentes;
- faturamento não é lucro (o sistema não registra custo de peças).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import pandas as pd

from cgcell.analise.preparacao import CATEGORIA_REAL, filtrar_periodo
from cgcell.dominio import StatusOS, StatusPagamento


class Frequencia(StrEnum):
    """Agrupamento temporal dos gráficos de evolução (códigos de período do pandas)."""

    DIA = "D"
    SEMANA = "W"
    MES = "M"

    @property
    def rotulo(self) -> str:
        return {Frequencia.DIA: "Dia", Frequencia.SEMANA: "Semana", Frequencia.MES: "Mês"}[self]


def _pagas_no_periodo(base: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    pagas = base[base["status_pagamento"].eq(str(StatusPagamento.PAGO))]
    return filtrar_periodo(pagas, "data_pagamento", inicio, fim)


def _abertas_no_periodo(base: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    return filtrar_periodo(base, "data_abertura", inicio, fim)


def faturamento_recebido(base: pd.DataFrame, inicio: date, fim: date) -> int:
    """Soma, em centavos, das OS pagas com data de pagamento no período."""
    return int(_pagas_no_periodo(base, inicio, fim)["valor_servico"].sum())


def quantidade_os(base: pd.DataFrame, inicio: date, fim: date) -> int:
    """Quantidade de OS abertas no período (todas as situações)."""
    return len(_abertas_no_periodo(base, inicio, fim))


def quantidade_por_status(base: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    """Distribuição das OS abertas no período por status, sempre com os 4 status."""
    contagem = _abertas_no_periodo(base, inicio, fim)["status_os"].value_counts()
    return pd.DataFrame(
        {
            "status_os": [str(status) for status in StatusOS],
            "rotulo": [status.rotulo for status in StatusOS],
            "quantidade": [int(contagem.get(str(status), 0)) for status in StatusOS],
        }
    )


def servicos_mais_frequentes(
    base: pd.DataFrame, inicio: date, fim: date, limite: int = 10
) -> pd.DataFrame:
    """Tipos de serviço mais pedidos no período, sem contar OS canceladas."""
    abertas = _abertas_no_periodo(base, inicio, fim)
    validas = abertas[abertas["status_os"].ne(str(StatusOS.CANCELADA))]
    contagem = (
        validas.groupby("nome_servico", as_index=False)
        .size()
        .rename(columns={"size": "quantidade"})
    )
    contagem["quantidade"] = contagem["quantidade"].astype("int64")
    return (
        contagem.sort_values(["quantidade", "nome_servico"], ascending=[False, True])
        .head(limite)
        .reset_index(drop=True)
    )


def _evolucao(
    linhas: pd.DataFrame,
    coluna_data: str,
    inicio: date,
    fim: date,
    frequencia: Frequencia,
    coluna_valor: str | None,
    nome_resultado: str,
) -> pd.DataFrame:
    """Agrega por período e categoria de origem, preenchendo períodos vazios com zero."""
    periodos = pd.period_range(start=inicio, end=fim, freq=str(frequencia))
    categorias = sorted(linhas["categoria_origem"].unique()) or [CATEGORIA_REAL]

    agrupado = linhas.assign(periodo=linhas[coluna_data].dt.to_period(str(frequencia)))
    grupos = agrupado.groupby(["periodo", "categoria_origem"])
    serie = grupos[coluna_valor].sum() if coluna_valor else grupos.size()

    indice = pd.MultiIndex.from_product([periodos, categorias], names=["periodo", "categoria"])
    serie = serie.reindex(indice, fill_value=0).astype("int64")

    resultado = serie.rename(nome_resultado).reset_index()
    resultado["periodo"] = resultado["periodo"].dt.start_time
    return resultado


def evolucao_faturamento(
    base: pd.DataFrame, inicio: date, fim: date, frequencia: Frequencia
) -> pd.DataFrame:
    """Faturamento recebido (centavos) por período de pagamento. Colunas: periodo, categoria,
    valor_centavos."""
    return _evolucao(
        _pagas_no_periodo(base, inicio, fim),
        "data_pagamento",
        inicio,
        fim,
        frequencia,
        "valor_servico",
        "valor_centavos",
    )


def evolucao_volume(
    base: pd.DataFrame, inicio: date, fim: date, frequencia: Frequencia
) -> pd.DataFrame:
    """Quantidade de OS por período de abertura. Colunas: periodo, categoria, quantidade."""
    return _evolucao(
        _abertas_no_periodo(base, inicio, fim),
        "data_abertura",
        inicio,
        fim,
        frequencia,
        None,
        "quantidade",
    )
