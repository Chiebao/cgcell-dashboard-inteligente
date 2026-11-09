"""Testes dos recursos de acessibilidade: contraste, CSS, gráficos e resumos em texto."""

from __future__ import annotations

import itertools
from datetime import date

import pandas as pd
import pytest

from cgcell.analise import indicadores as ind
from cgcell.analise.agregacao import Frequencia
from cgcell.analise.preparacao import criar_base_analise
from cgcell.apresentacao import acessibilidade as ac
from cgcell.apresentacao import graficos
from cgcell.apresentacao.acessibilidade import Preferencias, TamanhoFonte

# --- Contraste (WCAG) ---


def test_contraste_preto_e_branco_e_21_para_1():
    assert ac.razao_contraste("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert ac.razao_contraste("#FFFFFF", "#000000") == pytest.approx(21.0)


def test_contraste_de_cores_iguais_e_1_para_1():
    assert ac.razao_contraste("#FFD700", "#FFD700") == pytest.approx(1.0)


def test_contraste_de_referencia_da_wcag():
    # #767676 sobre branco é o cinza mais claro que ainda passa no nível AA (4,5:1).
    assert ac.razao_contraste("#767676", "#FFFFFF") == pytest.approx(4.54, abs=0.01)


def test_cor_invalida():
    with pytest.raises(ValueError, match="#RRGGBB"):
        ac.luminancia_relativa("#FFF")


@pytest.mark.parametrize(
    ("nome", "cor"),
    [("texto", ac.TEXTO), ("destaque", ac.DESTAQUE)]
    + [(f"série {nome}", cor) for nome, cor in ac.CORES_SERIES_ALTO_CONTRASTE.items()],
)
def test_cores_do_alto_contraste_atingem_7_para_1(nome, cor):
    razao = ac.razao_contraste(cor, ac.FUNDO)
    assert razao >= ac.CONTRASTE_MINIMO_AAA, f"{nome} ({cor}) tem só {razao:.2f}:1"


# --- CSS ---

COMBINACOES = list(itertools.product([False, True], list(TamanhoFonte)))


@pytest.mark.parametrize(("alto_contraste", "tamanho"), COMBINACOES)
def test_css_de_cada_combinacao(alto_contraste, tamanho):
    css = ac.gerar_css(Preferencias(alto_contraste=alto_contraste, tamanho_fonte=tamanho))

    if not alto_contraste and tamanho == TamanhoFonte.NORMAL:
        assert css == ""
        return

    px = round(16 * tamanho.escala)
    if tamanho == TamanhoFonte.NORMAL:
        assert "html { font-size" not in css
    else:
        assert f"html {{ font-size: {px}px !important; }}" in css
    assert "flex-wrap: wrap" in css  # layout não quebra

    if alto_contraste:
        for cor in (ac.FUNDO, ac.TEXTO, ac.DESTAQUE):
            assert cor in css
        assert "focus-visible" in css  # foco do teclado visível
        assert 'data-testid="stMetric"' in css  # cards com borda
        assert "border: 2px solid" in css
    else:
        assert ac.DESTAQUE not in css


def test_tamanhos_de_fonte_crescem():
    escalas = [tamanho.escala for tamanho in TamanhoFonte]
    assert escalas == sorted(escalas) and escalas[0] == 1.0


def test_tabela_html_so_quando_ha_preferencia_ativa():
    assert not Preferencias().usa_tabela_html
    assert Preferencias(alto_contraste=True).usa_tabela_html
    assert Preferencias(tamanho_fonte=TamanhoFonte.GRANDE).usa_tabela_html
    assert not Preferencias(resumo_texto=True).usa_tabela_html


# --- Gráficos ---


def _base_com_simulado():
    registro = {
        "id_ordem_servico": 1,
        "codigo_os": "A",
        "data_abertura": "2026-03-02",
        "data_conclusao": None,
        "data_pagamento": "2026-03-02",
        "valor_servico": 12345,
        "status_os": "aberta",
        "status_pagamento": "pago",
        "id_tipo_servico": 1,
        "nome_servico": "Troca de tela",
        "origem_registro": "manual",
    }
    simulado = registro | {"id_ordem_servico": 2, "codigo_os": "B", "origem_registro": "simulado"}
    return criar_base_analise([registro, simulado])


def _grafico_faturamento():
    evolucao = ind.evolucao_faturamento(
        _base_com_simulado(), date(2026, 3, 1), date(2026, 4, 30), Frequencia.MES
    )
    return graficos.grafico_evolucao_faturamento(evolucao, Frequencia.MES)


def test_grafico_sem_preferencias_nao_muda():
    figura = _grafico_faturamento()
    antes = figura.to_json()
    assert ac.ajustar_grafico(figura, Preferencias()).to_json() == antes


def test_grafico_em_alto_contraste():
    figura = ac.ajustar_grafico(_grafico_faturamento(), Preferencias(alto_contraste=True))
    layout = figura.layout
    assert layout.paper_bgcolor == ac.FUNDO and layout.plot_bgcolor == ac.FUNDO
    assert layout.font.color == ac.TEXTO
    assert layout.xaxis.linecolor == ac.TEXTO

    series = {serie.name: serie for serie in figura.data}
    assert series["Real"].marker.color == ac.TEXTO
    assert series["SIMULADO"].marker.color == ac.DESTAQUE
    # A hachura continua: a informação não depende só da cor.
    assert series["SIMULADO"].marker.pattern.shape == "/"
    assert series["SIMULADO"].marker.pattern.fgcolor == ac.DESTAQUE


@pytest.mark.parametrize("tamanho", [TamanhoFonte.GRANDE, TamanhoFonte.MUITO_GRANDE])
def test_grafico_com_fonte_ampliada(tamanho):
    figura = ac.ajustar_grafico(_grafico_faturamento(), Preferencias(tamanho_fonte=tamanho))
    assert figura.layout.font.size == round(12 * tamanho.escala)
    assert figura.layout.title.font.size == round(16 * tamanho.escala)
    assert figura.layout.height == round(450 * tamanho.escala)
    assert figura.layout.xaxis.automargin is True


def test_quebrar_titulo_mantem_aviso_e_respeita_limite():
    titulo = "Evolução do faturamento recebido (por data de pagamento)<br><sup>⚠️ SIMULADOS</sup>"
    quebrado = ac.quebrar_titulo(titulo, 1.5)
    principal, _, aviso = quebrado.rpartition("<br><sup>")
    assert aviso == "⚠️ SIMULADOS</sup>"
    assert all(len(linha) <= ac.limite_titulo(1.5) for linha in principal.split("<br>"))
    assert (
        principal.replace("<br>", " ") == "Evolução do faturamento recebido (por data de pagamento)"
    )
    assert ac.quebrar_titulo("", 1.5) == ""


# --- Resumos em texto ---


def _evolucao(valores: list[int], coluna: str, simulados: list[int] | None = None):
    periodos = pd.date_range("2026-01-01", periods=len(valores), freq="MS")
    linhas = pd.DataFrame({"periodo": periodos, "categoria": "Real", coluna: valores})
    if simulados:
        linhas = pd.concat(
            [
                linhas,
                pd.DataFrame({"periodo": periodos, "categoria": "SIMULADO", coluna: simulados}),
            ]
        )
    return linhas


def test_resumo_faturamento():
    texto = ac.resumo_evolucao_faturamento(
        _evolucao([100000, 3495000, 0], "valor_centavos"), Frequencia.MES
    )
    assert texto == (
        "Faturamento recebido de jan/2026 a mar/2026 (3 meses): total de R$ 35.950,00. "
        "Maior faturamento em fev/2026: R$ 34.950,00; menor em mar/2026: R$ 0,00."
    )


def test_resumo_faturamento_soma_categorias_e_avisa_simulados():
    texto = ac.resumo_evolucao_faturamento(
        _evolucao([100, 0], "valor_centavos", simulados=[0, 500]), Frequencia.MES
    )
    assert "Maior faturamento em fev/2026: R$ 5,00" in texto
    assert "R$ 5,00 vêm de dados SIMULADOS" in texto


def test_resumo_faturamento_sem_valores():
    texto = ac.resumo_evolucao_faturamento(_evolucao([0, 0], "valor_centavos"), Frequencia.MES)
    assert texto == "Nenhum faturamento recebido entre jan/2026 e fev/2026."
    vazio = pd.DataFrame(columns=["periodo", "categoria", "valor_centavos"])
    assert ac.resumo_evolucao_faturamento(vazio, Frequencia.MES) == (
        "Sem dados de faturamento no período."
    )


def test_resumo_volume():
    texto = ac.resumo_evolucao_volume(_evolucao([2, 3], "quantidade"), Frequencia.MES)
    assert texto == (
        "5 OS abertas de jan/2026 a fev/2026, média de 2,5 por mês. "
        "Maior volume em fev/2026: 3 OS; menor em jan/2026: 2 OS."
    )


def test_resumo_status_em_ordem_e_com_percentual():
    por_status = pd.DataFrame(
        {
            "rotulo": ["Aberta", "Em andamento", "Concluída", "Cancelada"],
            "quantidade": [1, 0, 3, 0],
        }
    )
    texto = ac.resumo_status(por_status, contem_simulados=True)
    assert texto.startswith("Distribuição das 4 OS por status: Concluída: 3 (75,0%); Aberta: 1")
    assert texto.endswith("Inclui dados SIMULADOS.")


def test_resumo_servicos_frequentes():
    servicos = pd.DataFrame({"nome_servico": ["Tela", "Bateria"], "quantidade": [1200, 5]})
    assert ac.resumo_servicos_frequentes(servicos) == (
        "Serviços mais frequentes, sem contar canceladas: 1º Tela, 1.200 OS; 2º Bateria, 5 OS."
    )
    assert ac.resumo_servicos_frequentes(servicos.iloc[0:0]) == (
        "Nenhum serviço realizado no período."
    )


def test_resumo_barras():
    dias = pd.DataFrame({"dia_semana": ["Segunda", "Terça", "Quarta"], "quantidade": [5, 1, 9]})
    assert ac.resumo_barras(dias, "dia_semana", "OS por dia da semana") == (
        "OS por dia da semana: total de 15 OS. Maior em Quarta (9); menor em Terça (1)."
    )


def test_resumos_vem_dos_mesmos_dados_do_grafico():
    base = _base_com_simulado()
    evolucao = ind.evolucao_faturamento(base, date(2026, 3, 1), date(2026, 3, 31), Frequencia.MES)
    texto = ac.resumo_evolucao_faturamento(evolucao, Frequencia.MES)
    assert "total de R$ 246,90" in texto  # 2 x R$ 123,45, igual ao gráfico
