"""Página de exploração dos dados: qualidade, período, distribuição e agrupamento sugerido."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from cgcell.analise.preparacao import CATEGORIA_REAL, CATEGORIA_SIMULADO, FiltroOrigem
from cgcell.apresentacao.acessibilidade import resumo_barras
from cgcell.apresentacao.componentes import aviso_simulado, exibir_grafico, exibir_tabela
from cgcell.apresentacao.formatacao import formatar_data, formatar_moeda
from cgcell.apresentacao.graficos import CORES_ORIGEM
from cgcell.servicos.servico_dados import gerar_relatorio_exploratorio
from cgcell.servicos.sessao import abrir_conexao


def renderizar() -> None:
    st.header("🔎 Exploração dos dados")
    st.caption(
        "Raio-x dos dados cadastrados: quantidade, período, problemas encontrados e "
        "como a demanda se distribui. Base para o futuro módulo de previsão."
    )

    filtro = st.radio(
        "Dados",
        list(FiltroOrigem),
        index=list(FiltroOrigem).index(FiltroOrigem.TODOS),
        format_func=lambda f: f.rotulo,
        horizontal=True,
        key="exploracao_origem",
    )
    with abrir_conexao() as conexao:
        relatorio = gerar_relatorio_exploratorio(conexao, filtro)

    if relatorio.quantidade_por_origem.get(CATEGORIA_SIMULADO, 0):
        aviso_simulado()

    registros, primeira, ultima, problemas = st.columns(4)
    registros.metric("OS válidas", relatorio.total_valido)
    primeira.metric("Primeira OS", formatar_data(relatorio.primeira_abertura))
    ultima.metric(
        "Última OS",
        formatar_data(relatorio.ultima_abertura),
        help=f"{relatorio.dias_de_historico} dia(s) de histórico.",
    )
    problemas.metric(
        "Registros com problema",
        relatorio.quantidade_rejeitados + relatorio.duplicados_removidos,
        help="Inconsistentes (separados) + duplicados (removidos).",
    )

    st.subheader("Resumo")
    st.markdown("\n".join(f"- {observacao}" for observacao in relatorio.observacoes))

    if relatorio.total_valido == 0:
        st.info("Cadastre OS em **Ordens de serviço** para ver a análise completa.")
        return

    _qualidade(relatorio)
    _distribuicoes(relatorio)
    _cobertura(relatorio)


def _qualidade(relatorio) -> None:
    st.subheader("Qualidade dos dados")
    esquerda, direita = st.columns(2)
    with esquerda:
        st.markdown("**Valores ausentes por coluna**")
        ausentes = relatorio.valores_ausentes.rename(
            columns={
                "coluna": "Coluna",
                "ausentes": "Ausentes",
                "percentual": "%",
                "observacao": "Observação",
            }
        )
        exibir_tabela(ausentes)
    with direita:
        st.markdown("**Registros inconsistentes**")
        if relatorio.rejeitados.empty:
            st.success("Nenhuma inconsistência encontrada.")
        else:
            exibir_tabela(
                relatorio.rejeitados.rename(columns={"codigo_os": "Código", "motivo": "Motivo"})[
                    ["Código", "Motivo"]
                ]
            )
        st.markdown("**Tempo entre etapas (dias)**")
        exibir_tabela(
            relatorio.tempos.rename(
                columns={
                    "medida": "Medida",
                    "registros": "OS",
                    "mediana_dias": "Mediana",
                    "media_dias": "Média",
                }
            )
        )


def _barras(dados, x: str, y: str, titulo: str):
    figura = px.bar(dados, x=x, y=y, text=y, color_discrete_sequence=[CORES_ORIGEM[CATEGORIA_REAL]])
    figura.update_layout(title=titulo, xaxis_title=None, yaxis_title=None, separators=",.")
    figura.update_yaxes(rangemode="tozero", tickformat="d")
    return figura


def _distribuicoes(relatorio) -> None:
    st.subheader("Como a demanda se distribui")
    st.caption("Contagem de OS pela data de abertura. Padrões aqui são descritivos, não causais.")
    esquerda, direita = st.columns(2)
    exibir_grafico(
        _barras(relatorio.por_dia_semana, "dia_semana", "quantidade", "OS por dia da semana"),
        resumo_barras(relatorio.por_dia_semana, "dia_semana", "OS por dia da semana"),
        area=esquerda,
    )
    exibir_grafico(
        _barras(
            relatorio.por_mes_do_ano.assign(mes=relatorio.por_mes_do_ano["mes"].str[:3]),
            "mes",
            "quantidade",
            "OS por mês do ano",
        ),
        resumo_barras(relatorio.por_mes_do_ano, "mes", "OS por mês do ano"),
        area=direita,
    )

    tipos = relatorio.por_tipo_servico.assign(
        valor=relatorio.por_tipo_servico["valor_servicos_centavos"].map(formatar_moeda)
    ).rename(
        columns={
            "nome_servico": "Tipo de serviço",
            "quantidade": "OS",
            "valor": "Valor dos serviços",
        }
    )
    st.markdown("**Por tipo de serviço**")
    st.caption("Valor dos serviços = soma do valor das OS, pagas ou não. Não é faturamento.")
    exibir_tabela(tipos[["Tipo de serviço", "OS", "Valor dos serviços"]])


def _cobertura(relatorio) -> None:
    st.subheader("Agrupamento no tempo")
    st.caption(
        "Para séries temporais, períodos sem nenhuma OS atrapalham a análise. "
        "A tabela mostra, para cada agrupamento, quantos períodos ficariam vazios."
    )
    cobertura = relatorio.cobertura.drop(columns=["frequencia"]).rename(
        columns={
            "agrupamento": "Agrupar por",
            "periodos": "Períodos",
            "periodos_sem_os": "Sem OS",
            "percentual_sem_os": "% sem OS",
            "media_por_periodo": "Média de OS",
            "coeficiente_variacao": "Variação (CV)",
        }
    )
    exibir_tabela(cobertura)
    if relatorio.frequencia_sugerida is not None:
        st.info(f"Agrupamento sugerido: **{relatorio.frequencia_sugerida.rotulo}**.")
