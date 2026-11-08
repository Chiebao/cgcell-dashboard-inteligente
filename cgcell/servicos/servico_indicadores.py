"""Serviço do dashboard: busca os dados e calcula todos os indicadores de uma vez."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

import pandas as pd

from cgcell.analise import indicadores
from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import (
    CATEGORIA_SIMULADO,
    FiltroOrigem,
    criar_base_analise,
    filtrar_periodo,
    filtrar_por_origem,
)
from cgcell.dados import repositorio_ordens_servico
from cgcell.dominio import StatusOS
from cgcell.servicos.erros import ErroValidacao


@dataclass(frozen=True)
class PainelIndicadores:
    """Tudo o que o dashboard exibe para um período e um filtro de origem."""

    inicio: date
    fim: date
    filtro_origem: FiltroOrigem
    frequencia: Frequencia
    faturamento_recebido: int
    quantidade_os: int
    quantidade_concluidas: int
    quantidade_canceladas: int
    contem_simulados: bool
    por_status: pd.DataFrame
    servicos_frequentes: pd.DataFrame
    evolucao_faturamento: pd.DataFrame
    evolucao_volume: pd.DataFrame


def calcular_painel(
    conexao: sqlite3.Connection,
    inicio: date,
    fim: date,
    filtro_origem: FiltroOrigem = FiltroOrigem.REAIS,
    frequencia: Frequencia = Frequencia.MES,
) -> PainelIndicadores:
    """Calcula os indicadores do período. OS excluídas nunca entram."""
    if inicio > fim:
        raise ErroValidacao(["A data inicial do período não pode ser depois da data final."])

    base = criar_base_analise(repositorio_ordens_servico.listar_para_analise(conexao))
    base = filtrar_por_origem(base, FiltroOrigem(filtro_origem))

    por_status = indicadores.quantidade_por_status(base, inicio, fim)
    quantidade = dict(zip(por_status["status_os"], por_status["quantidade"], strict=True))

    no_periodo = pd.concat(
        [
            filtrar_periodo(base, "data_abertura", inicio, fim),
            filtrar_periodo(base, "data_pagamento", inicio, fim),
        ]
    )

    return PainelIndicadores(
        inicio=inicio,
        fim=fim,
        filtro_origem=FiltroOrigem(filtro_origem),
        frequencia=Frequencia(frequencia),
        faturamento_recebido=indicadores.faturamento_recebido(base, inicio, fim),
        quantidade_os=indicadores.quantidade_os(base, inicio, fim),
        quantidade_concluidas=int(quantidade[str(StatusOS.CONCLUIDA)]),
        quantidade_canceladas=int(quantidade[str(StatusOS.CANCELADA)]),
        contem_simulados=bool(no_periodo["categoria_origem"].eq(CATEGORIA_SIMULADO).any()),
        por_status=por_status,
        servicos_frequentes=indicadores.servicos_mais_frequentes(base, inicio, fim),
        evolucao_faturamento=indicadores.evolucao_faturamento(base, inicio, fim, frequencia),
        evolucao_volume=indicadores.evolucao_volume(base, inicio, fim, frequencia),
    )
