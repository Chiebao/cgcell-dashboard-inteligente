"""Indicadores gerenciais calculados sobre a base de análise.

Regras de cálculo (seção 6 do AGENTS.md):
- faturamento recebido: somente OS PAGAS, filtradas pela DATA DE PAGAMENTO;
- volume de OS: filtrado pela DATA DE ABERTURA;
- OS canceladas não contam como concluídas nem entram nos serviços mais frequentes;
- faturamento não é lucro (o sistema não registra custo de peças).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from cgcell.analise.agregacao import Frequencia, agregar_por_periodo, agregar_por_tipo_servico
from cgcell.analise.preparacao import filtrar_periodo
from cgcell.dominio import StatusOS, StatusPagamento

__all__ = [
    "Frequencia",
    "evolucao_faturamento",
    "evolucao_volume",
    "faturamento_recebido",
    "quantidade_os",
    "quantidade_por_status",
    "servicos_mais_frequentes",
]


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
    por_tipo = agregar_por_tipo_servico(validas)[["nome_servico", "quantidade"]]
    return por_tipo.head(limite).reset_index(drop=True)


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
    return agregar_por_periodo(
        linhas,
        coluna_data,
        frequencia,
        inicio=inicio,
        fim=fim,
        coluna_valor=coluna_valor,
        por_origem=True,
        nome_resultado=nome_resultado,
    )


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
