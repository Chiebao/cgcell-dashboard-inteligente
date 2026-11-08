"""Testes unitários dos indicadores (DataFrames montados à mão, sem banco)."""

from __future__ import annotations

from datetime import date

import pytest

from cgcell.analise import indicadores as ind
from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import (
    CATEGORIA_REAL,
    CATEGORIA_SIMULADO,
    FiltroOrigem,
    criar_base_analise,
    filtrar_por_origem,
)

JAN_INICIO, JAN_FIM = date(2026, 1, 1), date(2026, 1, 31)
FEV_INICIO, FEV_FIM = date(2026, 2, 1), date(2026, 2, 28)


def registro(**campos) -> dict:
    padrao = {
        "id_ordem_servico": 1,
        "codigo_os": "OS",
        "data_abertura": "2026-01-10",
        "data_conclusao": None,
        "data_pagamento": None,
        "valor_servico": 10000,
        "status_os": "aberta",
        "status_pagamento": "pendente",
        "id_tipo_servico": 1,
        "nome_servico": "Troca de tela",
        "origem_registro": "manual",
    }
    return padrao | campos


@pytest.fixture
def base():
    return criar_base_analise(
        [
            # Aberta em janeiro, paga em fevereiro.
            registro(
                id_ordem_servico=1,
                status_os="concluida",
                data_conclusao="2026-01-20",
                status_pagamento="pago",
                data_pagamento="2026-02-05",
                valor_servico=15000,
            ),
            # Aberta e paga em janeiro (garantia, valor zero).
            registro(
                id_ordem_servico=2,
                status_pagamento="pago",
                data_pagamento="2026-01-12",
                valor_servico=0,
                nome_servico="Troca de bateria",
            ),
            # Cancelada em janeiro.
            registro(id_ordem_servico=3, status_os="cancelada", nome_servico="Troca de bateria"),
            # Pendente em janeiro: não entra no faturamento.
            registro(id_ordem_servico=4, valor_servico=99999),
            # Simulada, aberta e paga em fevereiro.
            registro(
                id_ordem_servico=5,
                data_abertura="2026-02-10",
                status_pagamento="pago",
                data_pagamento="2026-02-10",
                valor_servico=5000,
                origem_registro="simulado",
            ),
        ]
    )


def test_faturamento_considera_so_pagas_pela_data_de_pagamento(base):
    assert ind.faturamento_recebido(base, JAN_INICIO, JAN_FIM) == 0  # só a garantia (R$ 0)
    assert ind.faturamento_recebido(base, FEV_INICIO, FEV_FIM) == 20000  # OS 1 + simulada


def test_volume_considera_data_de_abertura(base):
    assert ind.quantidade_os(base, JAN_INICIO, JAN_FIM) == 4
    assert ind.quantidade_os(base, FEV_INICIO, FEV_FIM) == 1


def test_periodo_inclui_as_extremidades(base):
    assert ind.quantidade_os(base, date(2026, 1, 10), date(2026, 1, 10)) == 4


def test_distribuicao_por_status_tem_os_quatro_status(base):
    por_status = ind.quantidade_por_status(base, JAN_INICIO, JAN_FIM)
    assert dict(zip(por_status["status_os"], por_status["quantidade"], strict=True)) == {
        "aberta": 2,
        "em_andamento": 0,
        "concluida": 1,
        "cancelada": 1,
    }


def test_servicos_frequentes_ignoram_canceladas(base):
    servicos = ind.servicos_mais_frequentes(base, JAN_INICIO, JAN_FIM)
    assert servicos.to_dict("records") == [
        {"nome_servico": "Troca de tela", "quantidade": 2},
        {"nome_servico": "Troca de bateria", "quantidade": 1},
    ]


def test_servicos_frequentes_respeitam_limite(base):
    assert len(ind.servicos_mais_frequentes(base, JAN_INICIO, JAN_FIM, limite=1)) == 1


def test_filtro_de_origem(base):
    assert len(filtrar_por_origem(base, FiltroOrigem.REAIS)) == 4
    assert len(filtrar_por_origem(base, FiltroOrigem.SIMULADOS)) == 1
    assert len(filtrar_por_origem(base, FiltroOrigem.TODOS)) == 5


def test_evolucao_volume_preenche_periodos_vazios_e_separa_simulados(base):
    evolucao = ind.evolucao_volume(base, JAN_INICIO, date(2026, 3, 31), Frequencia.MES)
    tabela = {
        (linha.periodo.month, linha.categoria): linha.quantidade for linha in evolucao.itertuples()
    }
    assert tabela == {
        (1, CATEGORIA_REAL): 4,
        (1, CATEGORIA_SIMULADO): 0,
        (2, CATEGORIA_REAL): 0,
        (2, CATEGORIA_SIMULADO): 1,
        (3, CATEGORIA_REAL): 0,
        (3, CATEGORIA_SIMULADO): 0,
    }


def test_evolucao_faturamento_por_data_de_pagamento(base):
    reais = filtrar_por_origem(base, FiltroOrigem.REAIS)
    evolucao = ind.evolucao_faturamento(reais, JAN_INICIO, FEV_FIM, Frequencia.MES)
    assert evolucao["valor_centavos"].tolist() == [0, 15000]
    assert set(evolucao["categoria"]) == {CATEGORIA_REAL}


def test_evolucao_diaria_tem_um_ponto_por_dia(base):
    evolucao = ind.evolucao_volume(base, JAN_INICIO, JAN_FIM, Frequencia.DIA)
    assert len(evolucao) == 31  # só categoria Real em janeiro


def test_base_vazia_nao_quebra():
    vazia = criar_base_analise([])
    assert ind.faturamento_recebido(vazia, JAN_INICIO, JAN_FIM) == 0
    assert ind.quantidade_os(vazia, JAN_INICIO, JAN_FIM) == 0
    assert ind.servicos_mais_frequentes(vazia, JAN_INICIO, JAN_FIM).empty
    evolucao = ind.evolucao_faturamento(vazia, JAN_INICIO, FEV_FIM, Frequencia.MES)
    assert evolucao["valor_centavos"].tolist() == [0, 0]
