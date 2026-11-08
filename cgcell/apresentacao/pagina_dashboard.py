"""Página do dashboard gerencial: indicadores, gráficos e filtros."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import FiltroOrigem
from cgcell.apresentacao import graficos
from cgcell.apresentacao.componentes import DATA_MINIMA, aviso_simulado, mostrar_erro
from cgcell.apresentacao.formatacao import formatar_data, formatar_moeda
from cgcell.servicos.erros import ErroNegocio
from cgcell.servicos.servico_indicadores import calcular_painel
from cgcell.servicos.sessao import abrir_conexao

PERIODOS = [
    "Últimos 12 meses",
    "Este ano",
    "Este mês",
    "Últimos 90 dias",
    "Últimos 30 dias",
    "Personalizado",
]
FREQUENCIA_SUGERIDA = {
    "Este mês": Frequencia.DIA,
    "Últimos 30 dias": Frequencia.DIA,
    "Últimos 90 dias": Frequencia.SEMANA,
}


def calcular_intervalo(periodo: str, hoje: date) -> tuple[date, date]:
    """Converte um período pré-definido em (início, fim), ambos inclusivos."""
    if periodo == "Este mês":
        return hoje.replace(day=1), hoje
    if periodo == "Últimos 30 dias":
        return hoje - timedelta(days=29), hoje
    if periodo == "Últimos 90 dias":
        return hoje - timedelta(days=89), hoje
    if periodo == "Este ano":
        return date(hoje.year, 1, 1), hoje
    if periodo == "Últimos 12 meses":
        mes = hoje.month - 11
        ano = hoje.year
        if mes <= 0:
            mes += 12
            ano -= 1
        return date(ano, mes, 1), hoje
    raise ValueError(f"Período desconhecido: {periodo}")


def renderizar() -> None:
    st.header("📊 Dashboard gerencial")
    hoje = date.today()

    coluna_periodo, coluna_origem, coluna_frequencia = st.columns([2, 2, 1])
    periodo = coluna_periodo.selectbox("Período", PERIODOS, key="dashboard_periodo")
    if periodo == "Personalizado":
        intervalo = coluna_periodo.date_input(
            "De / até",
            value=(hoje.replace(day=1), hoje),
            min_value=DATA_MINIMA,
            max_value=hoje,
            format="DD/MM/YYYY",
            key="dashboard_intervalo",
        )
        if len(intervalo) != 2:
            st.info("Escolha a data final do período.")
            return
        inicio, fim = intervalo
    else:
        inicio, fim = calcular_intervalo(periodo, hoje)

    filtro_origem = coluna_origem.radio(
        "Dados",
        list(FiltroOrigem),
        format_func=lambda filtro: filtro.rotulo,
        horizontal=True,
        key="dashboard_origem",
    )
    sugerida = FREQUENCIA_SUGERIDA.get(periodo, Frequencia.MES)
    frequencia = coluna_frequencia.selectbox(
        "Agrupar por",
        list(Frequencia),
        index=list(Frequencia).index(sugerida),
        format_func=lambda f: f.rotulo,
        key=f"dashboard_frequencia_{periodo}",
    )

    with abrir_conexao() as conexao:
        try:
            painel = calcular_painel(conexao, inicio, fim, filtro_origem, frequencia)
        except ErroNegocio as erro:
            mostrar_erro(erro)
            return

    st.caption(f"Período: **{formatar_data(inicio)}** a **{formatar_data(fim)}**")
    if painel.contem_simulados:
        aviso_simulado()

    _indicadores(painel)

    if painel.quantidade_os == 0 and painel.faturamento_recebido == 0:
        st.info(
            "Nenhuma OS neste período e filtro. Cadastre OS em **Ordens de serviço** "
            "ou escolha outro período."
        )
        return

    esquerda, direita = st.columns(2)
    esquerda.plotly_chart(
        graficos.grafico_evolucao_faturamento(painel.evolucao_faturamento, frequencia)
    )
    direita.plotly_chart(graficos.grafico_evolucao_volume(painel.evolucao_volume, frequencia))

    esquerda, direita = st.columns(2)
    if painel.servicos_frequentes.empty:
        esquerda.info("Nenhum serviço realizado no período (OS canceladas não contam).")
    else:
        esquerda.plotly_chart(
            graficos.grafico_servicos_frequentes(
                painel.servicos_frequentes, painel.contem_simulados
            )
        )
    direita.plotly_chart(graficos.grafico_status(painel.por_status, painel.contem_simulados))


def _indicadores(painel) -> None:
    faturamento, quantidade, concluidas, canceladas = st.columns(4)
    faturamento.metric(
        "Faturamento recebido",
        formatar_moeda(painel.faturamento_recebido),
        help="Soma das OS pagas com data de pagamento dentro do período.",
    )
    quantidade.metric(
        "Quantidade de OS",
        painel.quantidade_os,
        help="OS abertas no período (pela data de abertura), em qualquer situação.",
    )
    concluidas.metric(
        "OS concluídas",
        painel.quantidade_concluidas,
        help="OS abertas no período que estão com status Concluída.",
    )
    canceladas.metric(
        "OS canceladas",
        painel.quantidade_canceladas,
        help="Não contam como serviços concluídos.",
    )
    st.caption(
        "ℹ️ **Faturamento não é lucro.** O sistema não registra custo de peças, "
        "por isso não calcula margem. Faturamento considera a data de pagamento; "
        "quantidade de OS considera a data de abertura."
    )
