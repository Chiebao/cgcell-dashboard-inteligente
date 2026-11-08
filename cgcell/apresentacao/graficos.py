"""Gráficos Plotly do dashboard. Funções puras: recebem DataFrames e devolvem figuras.

Distinção visual: barras de dados SIMULADOS têm cor laranja e hachura, e o título
avisa quando há simulados no gráfico.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import CATEGORIA_REAL, CATEGORIA_SIMULADO
from cgcell.apresentacao.formatacao import formatar_moeda

CORES_ORIGEM = {CATEGORIA_REAL: "#2563eb", CATEGORIA_SIMULADO: "#f59e0b"}
HACHURAS_ORIGEM = {CATEGORIA_REAL: "", CATEGORIA_SIMULADO: "/"}
CORES_STATUS = {
    "Aberta": "#64748b",
    "Em andamento": "#0ea5e9",
    "Concluída": "#16a34a",
    "Cancelada": "#dc2626",
}
_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def rotulo_periodo(inicio_periodo: pd.Timestamp, frequencia: Frequencia) -> str:
    """Rótulo do eixo X no padrão brasileiro."""
    if frequencia == Frequencia.MES:
        return f"{_MESES[inicio_periodo.month - 1]}/{inicio_periodo.year}"
    if frequencia == Frequencia.SEMANA:
        return f"sem. {inicio_periodo:%d/%m/%Y}"
    return f"{inicio_periodo:%d/%m/%Y}"


def _layout_padrao(figura: go.Figure, titulo: str) -> go.Figure:
    figura.update_layout(
        title=titulo,
        separators=",.",  # vírgula decimal, ponto de milhar
        xaxis_title=None,
        yaxis_title=None,
        legend_title_text="Origem",
        margin={"t": 60, "b": 10, "l": 10, "r": 10},
    )
    return figura


def _titulo(titulo: str, contem_simulados: bool) -> str:
    """Aviso de simulados numa segunda linha, para o título não ser cortado."""
    return f"{titulo}<br><sup>⚠️ inclui dados SIMULADOS</sup>" if contem_simulados else titulo


def grafico_evolucao_faturamento(evolucao: pd.DataFrame, frequencia: Frequencia) -> go.Figure:
    dados = evolucao.assign(
        rotulo=evolucao["periodo"].map(lambda p: rotulo_periodo(p, frequencia)),
        valor_reais=evolucao["valor_centavos"] / 100,
        valor_formatado=evolucao["valor_centavos"].map(formatar_moeda),
    )
    contem_simulados = bool(dados["categoria"].eq(CATEGORIA_SIMULADO).any())
    figura = px.bar(
        dados,
        x="rotulo",
        y="valor_reais",
        color="categoria",
        pattern_shape="categoria",
        color_discrete_map=CORES_ORIGEM,
        pattern_shape_map=HACHURAS_ORIGEM,
        custom_data=["valor_formatado", "categoria"],
    )
    figura.update_traces(hovertemplate="%{x}<br>%{customdata[1]}: %{customdata[0]}<extra></extra>")
    figura.update_layout(barmode="stack", yaxis_tickprefix="R$ ", showlegend=contem_simulados)
    return _layout_padrao(
        figura,
        _titulo("Evolução do faturamento recebido (por data de pagamento)", contem_simulados),
    )


def grafico_evolucao_volume(evolucao: pd.DataFrame, frequencia: Frequencia) -> go.Figure:
    dados = evolucao.assign(rotulo=evolucao["periodo"].map(lambda p: rotulo_periodo(p, frequencia)))
    contem_simulados = bool(dados["categoria"].eq(CATEGORIA_SIMULADO).any())
    figura = px.bar(
        dados,
        x="rotulo",
        y="quantidade",
        color="categoria",
        pattern_shape="categoria",
        color_discrete_map=CORES_ORIGEM,
        pattern_shape_map=HACHURAS_ORIGEM,
        custom_data=["categoria"],
    )
    figura.update_traces(hovertemplate="%{x}<br>%{customdata[0]}: %{y} OS<extra></extra>")
    figura.update_layout(barmode="stack", showlegend=contem_simulados)
    figura.update_yaxes(rangemode="tozero", tickformat="d")
    return _layout_padrao(
        figura, _titulo("Evolução do volume de OS (por data de abertura)", contem_simulados)
    )


def grafico_status(por_status: pd.DataFrame, contem_simulados: bool) -> go.Figure:
    figura = px.bar(
        por_status,
        x="rotulo",
        y="quantidade",
        color="rotulo",
        color_discrete_map=CORES_STATUS,
        text="quantidade",
    )
    figura.update_traces(hovertemplate="%{x}: %{y} OS<extra></extra>")
    figura.update_layout(showlegend=False)
    figura.update_yaxes(rangemode="tozero", tickformat="d")
    return _layout_padrao(figura, _titulo("Distribuição por status", contem_simulados))


def grafico_servicos_frequentes(servicos: pd.DataFrame, contem_simulados: bool) -> go.Figure:
    figura = px.bar(
        servicos,
        x="quantidade",
        y="nome_servico",
        orientation="h",
        text="quantidade",
        color_discrete_sequence=[CORES_ORIGEM[CATEGORIA_REAL]],
    )
    figura.update_traces(hovertemplate="%{y}: %{x} OS<extra></extra>")
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(rangemode="tozero", tickformat="d")
    return _layout_padrao(
        figura, _titulo("Serviços mais frequentes (sem canceladas)", contem_simulados)
    )
