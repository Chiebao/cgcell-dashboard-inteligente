"""Preparação de variáveis para o modelo (feature engineering). NÃO treina nada.

Mantido separado do treinamento (que virá em outro módulo) para que a mesma
preparação sirva a qualquer modelo e possa ser testada isoladamente.

REGRA ANTI-VAZAMENTO (data leakage): a linha do período t usa como variáveis
apenas valores de períodos ANTERIORES a t. O valor do próprio período t é o
`alvo` (o que se quer prever) e nunca aparece entre as variáveis.
Variáveis de calendário (mês, semana, dia da semana) são permitidas porque são
conhecidas com antecedência.
"""

from __future__ import annotations

from enum import StrEnum

import pandas as pd

from cgcell.analise.agregacao import Frequencia, agregar_por_periodo
from cgcell.dominio import StatusPagamento

COLUNAS_FIXAS = ("periodo", "alvo")


class Alvo(StrEnum):
    """O que a série mede."""

    VOLUME = "volume"
    """Quantidade de OS por período de abertura."""
    FATURAMENTO = "faturamento"
    """Faturamento recebido (centavos) por período de pagamento."""


def montar_serie(base: pd.DataFrame, alvo: Alvo, frequencia: Frequencia) -> pd.DataFrame:
    """Série temporal contínua (sem buracos) com colunas `periodo` e `valor`.

    As duas séries cobrem o mesmo intervalo: da primeira abertura até a última data
    registrada (abertura ou pagamento), para serem comparáveis.
    """
    alvo = Alvo(alvo)
    if base.empty:
        return pd.DataFrame(columns=["periodo", "valor"])
    inicio = base["data_abertura"].min()
    fim = base["data_abertura"].max()
    ultimo_pagamento = base["data_pagamento"].max()
    if pd.notna(ultimo_pagamento) and ultimo_pagamento > fim:
        fim = ultimo_pagamento

    if alvo == Alvo.VOLUME:
        return agregar_por_periodo(
            base, "data_abertura", frequencia, inicio=inicio, fim=fim, nome_resultado="valor"
        )
    pagas = base[base["status_pagamento"].eq(str(StatusPagamento.PAGO))]
    return agregar_por_periodo(
        pagas,
        "data_pagamento",
        frequencia,
        inicio=inicio,
        fim=fim,
        coluna_valor="valor_servico",
        nome_resultado="valor",
    )


def verificar_ordem_temporal(serie: pd.DataFrame) -> None:
    """Garante períodos únicos e em ordem crescente (pré-requisito para defasagens corretas)."""
    periodos = serie["periodo"]
    if not periodos.is_monotonic_increasing or periodos.duplicated().any():
        raise ValueError("A série precisa estar em ordem cronológica e sem períodos repetidos.")


def criar_variaveis(
    serie: pd.DataFrame,
    frequencia: Frequencia,
    defasagens: tuple[int, ...] = (1, 2, 3),
    janelas_media: tuple[int, ...] = (3,),
) -> pd.DataFrame:
    """Cria as variáveis explicativas a partir de uma série (`periodo`, `valor`).

    Variáveis criadas (todas usam só o passado):
    - `defasagem_k`: valor de k períodos atrás;
    - `media_movel_j`: média dos j períodos ANTERIORES (não inclui o atual);
    - `indice_tempo`: 0, 1, 2... (captura tendência);
    - calendário: `mes`, e `semana_do_ano` (semanal) ou `dia_semana` (diário).
    """
    if any(k < 1 for k in defasagens):
        raise ValueError("Defasagens precisam ser >= 1: defasagem 0 seria o próprio alvo.")
    if any(j < 1 for j in janelas_media):
        raise ValueError("Janelas de média precisam ser >= 1.")
    verificar_ordem_temporal(serie)

    frequencia = Frequencia(frequencia)
    valores = serie["valor"].astype("float64").reset_index(drop=True)
    periodos = pd.to_datetime(serie["periodo"]).reset_index(drop=True)
    passado = valores.shift(1)  # deslocar 1 período é o que impede o vazamento

    resultado = pd.DataFrame({"periodo": periodos, "alvo": valores})
    for k in defasagens:
        resultado[f"defasagem_{k}"] = valores.shift(k)
    for j in janelas_media:
        resultado[f"media_movel_{j}"] = passado.rolling(window=j, min_periods=j).mean()
    resultado["indice_tempo"] = pd.Series(range(len(resultado)), dtype="int64")
    resultado["mes"] = periodos.dt.month.astype("int64")
    if frequencia == Frequencia.SEMANA:
        resultado["semana_do_ano"] = periodos.dt.isocalendar().week.astype("int64").to_numpy()
    elif frequencia == Frequencia.DIA:
        resultado["dia_semana"] = periodos.dt.day_of_week.astype("int64")
    return resultado


def colunas_variaveis(tabela: pd.DataFrame) -> list[str]:
    """Nomes das variáveis explicativas (tudo, menos período e alvo)."""
    return [coluna for coluna in tabela.columns if coluna not in COLUNAS_FIXAS]


def remover_linhas_sem_historico(tabela: pd.DataFrame) -> pd.DataFrame:
    """Remove os primeiros períodos, que ainda não têm passado suficiente para as defasagens."""
    return tabela.dropna(subset=colunas_variaveis(tabela)).reset_index(drop=True)


def preparar_tabela_modelo(
    base: pd.DataFrame,
    alvo: Alvo,
    frequencia: Frequencia,
    defasagens: tuple[int, ...] = (1, 2, 3),
    janelas_media: tuple[int, ...] = (3,),
) -> pd.DataFrame:
    """Atalho: base do pipeline -> série -> variáveis -> sem linhas incompletas."""
    serie = montar_serie(base, alvo, frequencia)
    if serie.empty:
        return pd.DataFrame(columns=list(COLUNAS_FIXAS))
    tabela = criar_variaveis(serie, frequencia, defasagens, janelas_media)
    return remover_linhas_sem_historico(tabela)
