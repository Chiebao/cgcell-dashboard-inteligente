"""Análise exploratória: descreve o que existe nos dados antes de qualquer modelo.

Responde: quantos registros, de que período, quantos ausentes e inconsistências,
como a demanda se distribui (dia da semana, mês, tipo) e qual agrupamento temporal
deixa a série menos vazia.

Este módulo DESCREVE os dados. A decisão sobre se eles bastam para treinar um
modelo pertence ao módulo de Machine Learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from cgcell.analise.agregacao import Frequencia, agregar_por_periodo, agregar_por_tipo_servico
from cgcell.analise.pipeline import ResultadoPipeline
from cgcell.analise.preparacao import CATEGORIA_REAL, CATEGORIA_SIMULADO

NOMES_DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
NOMES_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]  # fmt: skip

LIMITE_PERCENTUAL_PERIODOS_VAZIOS = 20.0
"""Critério da frequência sugerida: a mais detalhada com no máximo 20% de períodos sem OS."""


@dataclass(frozen=True)
class RelatorioExploratorio:
    total_entrada: int
    total_valido: int
    quantidade_rejeitados: int
    duplicados_removidos: int
    quantidade_por_origem: dict[str, int]
    primeira_abertura: date | None
    ultima_abertura: date | None
    dias_de_historico: int
    valores_ausentes: pd.DataFrame
    rejeitados: pd.DataFrame
    por_dia_semana: pd.DataFrame
    por_mes_do_ano: pd.DataFrame
    por_tipo_servico: pd.DataFrame
    tempos: pd.DataFrame
    cobertura: pd.DataFrame
    frequencia_sugerida: Frequencia | None
    observacoes: list[str]


def distribuicao_por_dia_semana(base: pd.DataFrame) -> pd.DataFrame:
    contagem = base["dia_semana"].value_counts()
    return pd.DataFrame(
        {
            "dia_semana": NOMES_DIAS,
            "quantidade": [int(contagem.get(indice, 0)) for indice in range(7)],
        }
    )


def distribuicao_por_mes_do_ano(base: pd.DataFrame) -> pd.DataFrame:
    contagem = base["mes"].value_counts()
    return pd.DataFrame(
        {
            "mes": NOMES_MESES,
            "quantidade": [int(contagem.get(indice, 0)) for indice in range(1, 13)],
        }
    )


def resumo_tempos(base: pd.DataFrame) -> pd.DataFrame:
    """Mediana e média de dias da abertura até a conclusão e até o pagamento."""
    linhas = []
    for coluna, medida in (
        ("dias_ate_conclusao", "Abertura → conclusão"),
        ("dias_ate_pagamento", "Abertura → pagamento"),
    ):
        valores = base[coluna].dropna()
        linhas.append(
            {
                "medida": medida,
                "registros": len(valores),
                "mediana_dias": float(valores.median()) if len(valores) else None,
                "media_dias": round(float(valores.mean()), 1) if len(valores) else None,
            }
        )
    return pd.DataFrame(linhas)


def cobertura_por_frequencia(base: pd.DataFrame) -> pd.DataFrame:
    """Para cada agrupamento (dia, semana, mês): quantos períodos, quantos sem OS e variação."""
    linhas = []
    for frequencia in Frequencia:
        serie = agregar_por_periodo(base, "data_abertura", frequencia)["quantidade"]
        periodos = len(serie)
        media = float(serie.mean()) if periodos else 0.0
        desvio = float(serie.std(ddof=1)) if periodos > 1 else 0.0
        sem_os = int((serie == 0).sum())
        linhas.append(
            {
                "frequencia": str(frequencia),
                "agrupamento": frequencia.rotulo,
                "periodos": periodos,
                "periodos_sem_os": sem_os,
                "percentual_sem_os": round(100 * sem_os / periodos, 1) if periodos else 0.0,
                "media_por_periodo": round(media, 2),
                "coeficiente_variacao": round(desvio / media, 2) if media else None,
            }
        )
    return pd.DataFrame(linhas)


def sugerir_frequencia(cobertura: pd.DataFrame) -> Frequencia | None:
    """A frequência mais detalhada com até 20% de períodos vazios (e ao menos 2 períodos).
    Sem dados, não há sugestão; se nenhuma atende, sugere mês."""
    if cobertura["periodos"].sum() == 0:
        return None
    for linha in cobertura.itertuples():  # ordem: dia, semana, mês
        if linha.periodos >= 2 and linha.percentual_sem_os <= LIMITE_PERCENTUAL_PERIODOS_VAZIOS:
            return Frequencia(linha.frequencia)
    return Frequencia.MES


def _observacoes(relatorio_parcial: dict) -> list[str]:
    observacoes: list[str] = []
    total = relatorio_parcial["total_valido"]
    if total == 0:
        observacoes.append("Nenhum registro válido para analisar com o filtro escolhido.")
    else:
        primeira, ultima = (
            relatorio_parcial["primeira_abertura"],
            relatorio_parcial["ultima_abertura"],
        )
        observacoes.append(
            f"Histórico de {relatorio_parcial['dias_de_historico']} dia(s): "
            f"de {primeira:%d/%m/%Y} a {ultima:%d/%m/%Y}, com {total} OS válida(s)."
        )
        simulados = relatorio_parcial["quantidade_por_origem"].get(CATEGORIA_SIMULADO, 0)
        if simulados:
            percentual = round(100 * simulados / total, 1)
            observacoes.append(
                f"{percentual}% das OS são SIMULADAS: servem só para demonstração técnica "
                "e não representam a operação real."
            )
    if relatorio_parcial["quantidade_rejeitados"]:
        observacoes.append(
            f"{relatorio_parcial['quantidade_rejeitados']} registro(s) inconsistente(s) foram "
            "separados e não entram nas análises."
        )
    if relatorio_parcial["duplicados_removidos"]:
        observacoes.append(
            f"{relatorio_parcial['duplicados_removidos']} registro(s) duplicado(s) removido(s)."
        )
    sugerida = relatorio_parcial["frequencia_sugerida"]
    if sugerida is not None:
        observacoes.append(
            f"Agrupamento sugerido para séries temporais: {sugerida.rotulo.lower()} "
            f"(o mais detalhado com até {LIMITE_PERCENTUAL_PERIODOS_VAZIOS:.0f}% de períodos "
            "sem OS)."
        )
    observacoes.append(
        "Se os dados bastam para previsões é decidido no módulo de Machine Learning, "
        "com critério próprio."
    )
    return observacoes


def gerar_relatorio(resultado: ResultadoPipeline) -> RelatorioExploratorio:
    base = resultado.base
    tem_dados = not base.empty
    primeira = base["data_abertura"].min().date() if tem_dados else None
    ultima = base["data_abertura"].max().date() if tem_dados else None
    contagem_origem = base["categoria_origem"].value_counts()
    cobertura = cobertura_por_frequencia(base)

    parcial = {
        "total_entrada": resultado.total_entrada,
        "total_valido": len(base),
        "quantidade_rejeitados": len(resultado.rejeitados),
        "duplicados_removidos": resultado.duplicados_removidos,
        "quantidade_por_origem": {
            categoria: int(contagem_origem.get(categoria, 0))
            for categoria in (CATEGORIA_REAL, CATEGORIA_SIMULADO)
        },
        "primeira_abertura": primeira,
        "ultima_abertura": ultima,
        "dias_de_historico": (ultima - primeira).days + 1 if tem_dados else 0,
        "frequencia_sugerida": sugerir_frequencia(cobertura),
    }
    return RelatorioExploratorio(
        **parcial,
        valores_ausentes=resultado.valores_ausentes,
        rejeitados=resultado.rejeitados,
        por_dia_semana=distribuicao_por_dia_semana(base),
        por_mes_do_ano=distribuicao_por_mes_do_ano(base),
        por_tipo_servico=agregar_por_tipo_servico(base),
        tempos=resumo_tempos(base),
        cobertura=cobertura,
        observacoes=_observacoes(parcial),
    )
