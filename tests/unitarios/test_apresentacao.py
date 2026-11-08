"""Testes das funções puras da apresentação: períodos do dashboard e gráficos."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from cgcell.analise import indicadores as ind
from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import criar_base_analise
from cgcell.apresentacao import graficos
from cgcell.apresentacao.pagina_dashboard import PERIODOS, calcular_intervalo

HOJE = date(2026, 3, 15)


@pytest.mark.parametrize(
    ("periodo", "esperado"),
    [
        ("Este mês", (date(2026, 3, 1), HOJE)),
        ("Últimos 30 dias", (date(2026, 2, 14), HOJE)),
        ("Últimos 90 dias", (date(2025, 12, 16), HOJE)),
        ("Este ano", (date(2026, 1, 1), HOJE)),
        ("Últimos 12 meses", (date(2025, 4, 1), HOJE)),
    ],
)
def test_calcular_intervalo(periodo, esperado):
    assert calcular_intervalo(periodo, HOJE) == esperado


def test_ultimos_12_meses_em_dezembro_fica_no_mesmo_ano():
    assert calcular_intervalo("Últimos 12 meses", date(2026, 12, 5))[0] == date(2026, 1, 1)


def test_todos_os_periodos_pre_definidos_sao_tratados():
    for periodo in PERIODOS:
        if periodo != "Personalizado":
            calcular_intervalo(periodo, HOJE)


@pytest.mark.parametrize(
    ("frequencia", "esperado"),
    [
        (Frequencia.MES, "mar/2026"),
        (Frequencia.SEMANA, "sem. 02/03/2026"),
        (Frequencia.DIA, "02/03/2026"),
    ],
)
def test_rotulo_periodo(frequencia, esperado):
    assert graficos.rotulo_periodo(pd.Timestamp("2026-03-02"), frequencia) == esperado


def test_graficos_sao_montados_e_avisam_simulados():
    base = criar_base_analise(
        [
            {
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
                "origem_registro": "simulado",
            }
        ]
    )
    inicio, fim = date(2026, 3, 1), date(2026, 3, 31)
    faturamento = graficos.grafico_evolucao_faturamento(
        ind.evolucao_faturamento(base, inicio, fim, Frequencia.MES), Frequencia.MES
    )
    assert "SIMULADOS" in faturamento.layout.title.text
    assert faturamento.layout.separators == ",."

    volume = graficos.grafico_evolucao_volume(
        ind.evolucao_volume(base, inicio, fim, Frequencia.MES), Frequencia.MES
    )
    assert "SIMULADOS" in volume.layout.title.text

    status = graficos.grafico_status(ind.quantidade_por_status(base, inicio, fim), True)
    assert len(status.data) == 4  # uma barra (traço) por status

    servicos = graficos.grafico_servicos_frequentes(
        ind.servicos_mais_frequentes(base, inicio, fim), False
    )
    assert "SIMULADOS" not in servicos.layout.title.text
