"""Recursos de acessibilidade: alto contraste, tamanho da fonte e resumo em texto dos gráficos.

A maior parte do módulo são funções puras (testáveis sem Streamlit):
- cálculo de contraste segundo a WCAG 2.x;
- geração do CSS para cada combinação de preferências;
- ajuste das figuras Plotly;
- resumos em texto dos gráficos, para leitores de tela.

As funções que usam Streamlit (painel na barra lateral e aplicação do CSS) ficam no fim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cgcell.analise.agregacao import Frequencia
from cgcell.analise.preparacao import CATEGORIA_SIMULADO
from cgcell.apresentacao.formatacao import formatar_moeda
from cgcell.apresentacao.graficos import rotulo_periodo

# --- Paleta de alto contraste ---

FUNDO = "#000000"
TEXTO = "#FFFFFF"
DESTAQUE = "#FFD700"  # amarelo
GRADE = "#5C5C5C"  # linhas de grade: não são texto, só apoio visual
CORES_SERIES_ALTO_CONTRASTE = {
    "Real": TEXTO,
    CATEGORIA_SIMULADO: DESTAQUE,  # além da cor, mantém a hachura
    "Aberta": TEXTO,
    "Em andamento": "#00FFFF",
    "Concluída": "#7CFC00",
    "Cancelada": "#FF8080",
}
CONTRASTE_MINIMO_AAA = 7.0
"""WCAG 2.x, critério 1.4.6 (Contraste Aprimorado, nível AAA): 7:1 para texto normal."""

TAMANHO_BASE_PX = 16
FONTE_GRAFICO_PX = 12
TITULO_GRAFICO_PX = 16
ALTURA_GRAFICO_PX = 450  # altura padrão do Plotly


class TamanhoFonte(StrEnum):
    NORMAL = "normal"
    GRANDE = "grande"
    MUITO_GRANDE = "muito_grande"

    @property
    def rotulo(self) -> str:
        return {
            TamanhoFonte.NORMAL: "Normal",
            TamanhoFonte.GRANDE: "Grande",
            TamanhoFonte.MUITO_GRANDE: "Muito grande",
        }[self]

    @property
    def escala(self) -> float:
        return {
            TamanhoFonte.NORMAL: 1.0,
            TamanhoFonte.GRANDE: 1.25,
            TamanhoFonte.MUITO_GRANDE: 1.5,
        }[self]


@dataclass(frozen=True)
class Preferencias:
    alto_contraste: bool = False
    tamanho_fonte: TamanhoFonte = TamanhoFonte.NORMAL
    resumo_texto: bool = False

    @property
    def usa_tabela_html(self) -> bool:
        """Tabelas interativas (canvas) não seguem CSS nem leitores de tela; nesses modos
        a interface usa tabela HTML, que respeita cores, tamanho e leitura em voz alta."""
        return self.alto_contraste or self.tamanho_fonte != TamanhoFonte.NORMAL


# --- Contraste (WCAG 2.x) ---


def _canal_linear(valor_8bits: int) -> float:
    canal = valor_8bits / 255
    return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4


def luminancia_relativa(cor_hex: str) -> float:
    """Luminância relativa da cor, de 0 (preto) a 1 (branco), conforme a WCAG."""
    cor = cor_hex.lstrip("#")
    if len(cor) != 6:
        raise ValueError(f"Cor inválida: {cor_hex}. Use o formato #RRGGBB.")
    vermelho, verde, azul = (int(cor[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _canal_linear(vermelho)
        + 0.7152 * _canal_linear(verde)
        + 0.0722 * _canal_linear(azul)
    )


def razao_contraste(cor_a: str, cor_b: str) -> float:
    """Razão de contraste entre duas cores: de 1 (iguais) a 21 (preto e branco)."""
    clara, escura = sorted((luminancia_relativa(cor_a), luminancia_relativa(cor_b)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


# --- CSS ---

_CSS_ALTO_CONTRASTE = f"""
/* Alto contraste: texto {TEXTO} e destaques {DESTAQUE} sobre {FUNDO} (WCAG 1.4.6, nível AAA). */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"],
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
  background-color: {FUNDO} !important;
}}
.stApp, .stApp * {{ color: {TEXTO} !important; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h1 *, .stApp h2 *, .stApp h3 * {{
  color: {DESTAQUE} !important;
}}
.stApp a {{ color: {DESTAQUE} !important; text-decoration: underline !important; }}
[data-testid="stSidebar"] {{ border-right: 2px solid {TEXTO} !important; }}

/* Campos com borda visível */
.stApp input, .stApp textarea,
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"],
.stApp [data-baseweb="select"] > div {{
  background-color: {FUNDO} !important;
  border: 2px solid {TEXTO} !important;
}}

/* Botões em amarelo com borda (só os botões de ação, não os ícones de ajuda) */
.stApp [data-testid^="stBaseButton"] {{
  background-color: {FUNDO} !important;
  border: 2px solid {DESTAQUE} !important;
}}
.stApp [data-testid^="stBaseButton"], .stApp [data-testid^="stBaseButton"] * {{
  color: {DESTAQUE} !important;
}}

/* Cards de indicadores, avisos, gráficos e tabelas com borda */
.stApp [data-testid="stMetric"] {{
  border: 2px solid {TEXTO} !important;
  border-radius: 0.5rem;
  padding: 0.75rem;
}}
.stApp [data-testid="stAlertContainer"] {{
  background-color: {FUNDO} !important;
  border: 2px solid {DESTAQUE} !important;
}}
.stApp [data-testid="stPlotlyChart"] {{
  border: 2px solid {TEXTO} !important;
  border-radius: 0.5rem;
}}
.stApp [data-testid="stTable"] table,
.stApp [data-testid="stTable"] th,
.stApp [data-testid="stTable"] td {{
  background-color: {FUNDO} !important;
  border: 1px solid {TEXTO} !important;
}}
.stApp [data-testid="stTable"] th {{ color: {DESTAQUE} !important; }}

/* Listas suspensas (abrem fora da área principal da página) */
[data-baseweb="popover"], [data-baseweb="popover"] *, [role="listbox"], [role="option"] {{
  background-color: {FUNDO} !important;
  color: {TEXTO} !important;
}}
[role="option"][aria-selected="true"], [role="option"]:hover {{
  outline: 2px solid {DESTAQUE} !important;
}}

/* Foco do teclado sempre visível (WCAG 2.4.7) */
.stApp *:focus-visible, [data-baseweb="popover"] *:focus-visible {{
  outline: 3px solid {DESTAQUE} !important;
  outline-offset: 2px !important;
}}
"""

_CSS_LAYOUT_FLEXIVEL = """
/* Layout flexível: colunas descem para a linha de baixo em vez de espremer o conteúdo,
   e textos de indicadores quebram linha em vez de serem cortados com "...". */
[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
[data-testid="stColumn"] { min-width: min(100%, 12rem) !important; }
[data-testid="stColumn"]:has([data-testid="stPlotlyChart"]) {
  min-width: min(100%, 26rem) !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
}
/* O valor já é grande por padrão; um pouco menor que o padrão em rem para caber no card. */
[data-testid="stMetricValue"] { font-size: 1.8rem !important; }
"""


def gerar_css(preferencias: Preferencias) -> str:
    """CSS para as preferências. Texto vazio quando tudo está no padrão."""
    partes: list[str] = []
    escala = preferencias.tamanho_fonte.escala
    if escala != 1.0:
        tamanho = round(TAMANHO_BASE_PX * escala)
        partes.append(
            f"/* Tamanho da fonte: {preferencias.tamanho_fonte.rotulo} ({escala:.0%}). "
            "O Streamlit mede quase tudo em rem, então aumentar a fonte da raiz "
            "aumenta a página inteira (WCAG 1.4.4). */\n"
            f"html {{ font-size: {tamanho}px !important; }}"
        )
    if escala != 1.0 or preferencias.alto_contraste:
        partes.append(_CSS_LAYOUT_FLEXIVEL)
    if preferencias.alto_contraste:
        partes.append(_CSS_ALTO_CONTRASTE)
    return "\n".join(partes).strip()


# --- Gráficos ---


def limite_titulo(escala: float) -> int:
    """Caracteres por linha do título.

    Fonte normal: dois gráficos por linha, títulos curtos. Fonte ampliada: cada gráfico ocupa
    a largura toda (ver CSS), então cabem mais caracteres, mas cada um é maior.
    """
    return 48 if escala == 1.0 else int(72 / escala)


def quebrar_titulo(titulo: str, escala: float) -> str:
    """Quebra a linha principal do título em linhas menores (o Plotly não quebra sozinho).

    Partes já separadas por `<br>` (como o aviso de SIMULADOS) são mantidas.
    """
    if not titulo:
        return titulo
    principal, separador, resto = titulo.partition("<br>")
    limite = limite_titulo(escala)
    linhas: list[str] = []
    atual = ""
    for palavra in principal.split():
        candidata = f"{atual} {palavra}".strip()
        if atual and len(candidata) > limite:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidata
    linhas.append(atual)
    return "<br>".join(linhas) + separador + resto


def ajustar_grafico(figura: go.Figure, preferencias: Preferencias) -> go.Figure:
    """Aplica tamanho de fonte e alto contraste a uma figura Plotly (altera e devolve a mesma)."""
    escala = preferencias.tamanho_fonte.escala
    if escala != 1.0 or preferencias.alto_contraste:
        # Título alinhado à esquerda e quebrado em linhas: não é cortado nas bordas.
        titulo = quebrar_titulo(figura.layout.title.text or "", escala)
        linhas_titulo = titulo.count("<br>") + 1
        espaco_legenda = FONTE_GRAFICO_PX * escala * 2 if escala != 1.0 else 0
        figura.update_layout(
            title_text=titulo,
            title_x=0,
            title_xanchor="left",
            # Espaço do topo: linhas do título + legenda (quando fica acima) + folga.
            margin_t=round(linhas_titulo * TITULO_GRAFICO_PX * escala * 1.35 + espaco_legenda + 20),
        )
        # Rótulos maiores ou com borda precisam de espaço: o Plotly calcula as margens sozinho.
        figura.update_xaxes(automargin=True)
        figura.update_yaxes(automargin=True)
    if escala != 1.0:
        figura.update_layout(
            font_size=round(FONTE_GRAFICO_PX * escala),
            title_font_size=round(TITULO_GRAFICO_PX * escala),
            hoverlabel_font_size=round(FONTE_GRAFICO_PX * escala),
            height=round(ALTURA_GRAFICO_PX * escala),
            # Legenda em linha acima do gráfico, para não cobrir as barras.
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        )

    if preferencias.alto_contraste:
        figura.update_layout(
            paper_bgcolor=FUNDO,
            plot_bgcolor=FUNDO,
            font_color=TEXTO,
            title_font_color=DESTAQUE,
            legend={"bgcolor": FUNDO, "bordercolor": TEXTO, "borderwidth": 1, "font_color": TEXTO},
            hoverlabel={"bgcolor": FUNDO, "bordercolor": DESTAQUE, "font_color": TEXTO},
            # Os números ficam fora das barras; a margem direita evita cortar o maior deles.
            margin_r=round(48 * escala),
        )
        for eixo in (figura.update_xaxes, figura.update_yaxes):
            eixo(
                showline=True,
                linecolor=TEXTO,
                linewidth=2,
                tickcolor=TEXTO,
                tickfont_color=TEXTO,
                gridcolor=GRADE,
                zerolinecolor=TEXTO,
            )
        for serie in figura.data:
            if serie.type != "bar":
                continue
            cor = CORES_SERIES_ALTO_CONTRASTE.get(serie.name, TEXTO)
            serie.marker.color = cor
            serie.marker.line = {"color": cor, "width": 2}
            if serie.marker.pattern and serie.marker.pattern.shape:
                # A hachura continua: a informação "simulado" não depende só da cor.
                serie.marker.pattern.fgcolor = cor
                serie.marker.pattern.bgcolor = FUNDO
            serie.textposition = "outside"
            serie.textfont = {"color": TEXTO}
            serie.cliponaxis = False
    return figura


# --- Resumos em texto ---


def _inteiro(valor: int) -> str:
    return f"{int(valor):,}".replace(",", ".")


def _percentual(parte: int, total: int) -> str:
    return f"{100 * parte / total:.1f}%".replace(".", ",")


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _unidade(frequencia: Frequencia, quantidade: int) -> str:
    singular, plural = {
        Frequencia.DIA: ("dia", "dias"),
        Frequencia.SEMANA: ("semana", "semanas"),
        Frequencia.MES: ("mês", "meses"),
    }[Frequencia(frequencia)]
    return singular if quantidade == 1 else plural


def _somar_por_periodo(evolucao: pd.DataFrame, coluna: str) -> pd.Series:
    return evolucao.groupby("periodo", sort=True)[coluna].sum()


def resumo_evolucao_faturamento(evolucao: pd.DataFrame, frequencia: Frequencia) -> str:
    """Descreve o gráfico de evolução do faturamento recebido."""
    if evolucao.empty:
        return "Sem dados de faturamento no período."
    por_periodo = _somar_por_periodo(evolucao, "valor_centavos")
    inicio, fim = (
        rotulo_periodo(p, frequencia) for p in (por_periodo.index[0], por_periodo.index[-1])
    )
    total = int(por_periodo.sum())
    if total == 0:
        return f"Nenhum faturamento recebido entre {inicio} e {fim}."
    maior, menor = por_periodo.idxmax(), por_periodo.idxmin()
    texto = (
        f"Faturamento recebido de {inicio} a {fim} "
        f"({len(por_periodo)} {_unidade(frequencia, len(por_periodo))}): "
        f"total de {formatar_moeda(total)}. "
        f"Maior faturamento em {rotulo_periodo(maior, frequencia)}: "
        f"{formatar_moeda(int(por_periodo[maior]))}; "
        f"menor em {rotulo_periodo(menor, frequencia)}: {formatar_moeda(int(por_periodo[menor]))}."
    )
    simulado = int(
        evolucao.loc[evolucao["categoria"].eq(CATEGORIA_SIMULADO), "valor_centavos"].sum()
    )
    if simulado:
        texto += f" Desse total, {formatar_moeda(simulado)} vêm de dados SIMULADOS."
    return texto


def resumo_evolucao_volume(evolucao: pd.DataFrame, frequencia: Frequencia) -> str:
    """Descreve o gráfico de evolução do volume de OS."""
    if evolucao.empty:
        return "Sem dados de volume no período."
    por_periodo = _somar_por_periodo(evolucao, "quantidade")
    inicio, fim = (
        rotulo_periodo(p, frequencia) for p in (por_periodo.index[0], por_periodo.index[-1])
    )
    total = int(por_periodo.sum())
    if total == 0:
        return f"Nenhuma OS aberta entre {inicio} e {fim}."
    maior, menor = por_periodo.idxmax(), por_periodo.idxmin()
    unidade = _unidade(frequencia, 1)
    texto = (
        f"{_inteiro(total)} OS abertas de {inicio} a {fim}, média de "
        f"{_decimal(total / len(por_periodo))} por {unidade}. "
        f"Maior volume em {rotulo_periodo(maior, frequencia)}: {_inteiro(por_periodo[maior])} OS; "
        f"menor em {rotulo_periodo(menor, frequencia)}: {_inteiro(por_periodo[menor])} OS."
    )
    simulado = int(evolucao.loc[evolucao["categoria"].eq(CATEGORIA_SIMULADO), "quantidade"].sum())
    if simulado:
        texto += f" Dessas, {_inteiro(simulado)} são SIMULADAS."
    return texto


def resumo_status(por_status: pd.DataFrame, contem_simulados: bool = False) -> str:
    """Descreve a distribuição por status, do mais frequente para o menos frequente."""
    total = int(por_status["quantidade"].sum())
    if total == 0:
        return "Nenhuma OS no período."
    ordenado = por_status.sort_values("quantidade", ascending=False, kind="stable")
    partes = [
        f"{linha.rotulo}: {_inteiro(linha.quantidade)} ({_percentual(linha.quantidade, total)})"
        for linha in ordenado.itertuples()
    ]
    texto = f"Distribuição das {_inteiro(total)} OS por status: " + "; ".join(partes) + "."
    return texto + (" Inclui dados SIMULADOS." if contem_simulados else "")


def resumo_servicos_frequentes(servicos: pd.DataFrame, contem_simulados: bool = False) -> str:
    """Descreve o ranking de serviços mais frequentes."""
    if servicos.empty:
        return "Nenhum serviço realizado no período."
    partes = [
        f"{posicao}º {linha.nome_servico}, {_inteiro(linha.quantidade)} OS"
        for posicao, linha in enumerate(servicos.itertuples(), start=1)
    ]
    texto = "Serviços mais frequentes, sem contar canceladas: " + "; ".join(partes) + "."
    return texto + (" Inclui dados SIMULADOS." if contem_simulados else "")


def resumo_barras(dados: pd.DataFrame, coluna_categoria: str, descricao: str) -> str:
    """Resumo genérico de um gráfico de barras de contagem (coluna `quantidade`)."""
    total = int(dados["quantidade"].sum())
    if total == 0:
        return f"{descricao}: nenhuma OS."
    maior = dados.loc[dados["quantidade"].idxmax()]
    menor = dados.loc[dados["quantidade"].idxmin()]
    return (
        f"{descricao}: total de {_inteiro(total)} OS. "
        f"Maior em {maior[coluna_categoria]} ({_inteiro(maior['quantidade'])}); "
        f"menor em {menor[coluna_categoria]} ({_inteiro(menor['quantidade'])})."
    )


# --- Streamlit: painel e aplicação ---

CHAVE_ALTO_CONTRASTE = "acessibilidade_alto_contraste"
CHAVE_TAMANHO_FONTE = "acessibilidade_tamanho_fonte"
CHAVE_RESUMO_TEXTO = "acessibilidade_resumo_texto"


def obter_preferencias() -> Preferencias:
    """Preferências da sessão atual (valem para todas as páginas enquanto o app estiver aberto)."""
    estado = st.session_state
    return Preferencias(
        alto_contraste=bool(estado.get(CHAVE_ALTO_CONTRASTE, False)),
        tamanho_fonte=TamanhoFonte(estado.get(CHAVE_TAMANHO_FONTE, TamanhoFonte.NORMAL)),
        resumo_texto=bool(estado.get(CHAVE_RESUMO_TEXTO, False)),
    )


def renderizar_painel() -> Preferencias:
    """Seção "♿ Acessibilidade" (chamar dentro de `with st.sidebar:`)."""
    st.markdown("### ♿ Acessibilidade")
    st.toggle(
        "Alto contraste",
        key=CHAVE_ALTO_CONTRASTE,
        help="Fundo preto, texto branco e destaques em amarelo (contraste mínimo de 7:1).",
    )
    st.radio(
        "Tamanho da fonte",
        list(TamanhoFonte),
        format_func=lambda tamanho: tamanho.rotulo,
        key=CHAVE_TAMANHO_FONTE,
    )
    st.toggle(
        "Resumo em texto dos gráficos",
        key=CHAVE_RESUMO_TEXTO,
        help="Mostra abaixo de cada gráfico um parágrafo que descreve os dados, "
        "para quem usa leitor de tela.",
    )
    return obter_preferencias()


def aplicar_estilo(preferencias: Preferencias) -> None:
    css = gerar_css(preferencias)
    if css:
        st.html(f"<style>{css}</style>")
