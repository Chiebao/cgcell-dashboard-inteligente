"""Integração: indicadores calculados a partir do banco (temporário)."""

from __future__ import annotations

from datetime import date

import pytest

from cgcell.analise.indicadores import Frequencia
from cgcell.analise.preparacao import FiltroOrigem
from cgcell.dominio import OrigemRegistro, StatusOS, StatusPagamento
from cgcell.servicos.erros import ErroValidacao
from cgcell.servicos.servico_indicadores import calcular_painel
from cgcell.servicos.servico_ordens_servico import (
    cadastrar_ordem_servico,
    excluir_ordem_servico,
)
from tests.conftest import HOJE

INICIO, FIM = date(2026, 1, 1), date(2026, 6, 15)


@pytest.fixture
def banco_com_dados(conexao, fabricar_dados):
    cadastrar_ordem_servico(
        conexao,
        fabricar_dados(
            codigo_os="R1",
            data_abertura=date(2026, 5, 2),
            status_os=StatusOS.CONCLUIDA,
            data_conclusao=date(2026, 5, 3),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 5, 4),
            valor_servico=20000,
        ),
        hoje=HOJE,
    )
    cadastrar_ordem_servico(
        conexao,
        fabricar_dados(codigo_os="R2", data_abertura=date(2026, 5, 10), status_os="cancelada"),
        hoje=HOJE,
    )
    cadastrar_ordem_servico(
        conexao,
        fabricar_dados(
            codigo_os="S1",
            data_abertura=date(2026, 4, 1),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 4, 1),
            valor_servico=7000,
        ),
        origem_registro=OrigemRegistro.SIMULADO,
        hoje=HOJE,
    )
    # OS antiga e excluída: nunca entra nos indicadores.
    antiga = cadastrar_ordem_servico(
        conexao,
        fabricar_dados(
            codigo_os="X1",
            data_abertura=date(2026, 1, 5),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 1, 5),
            valor_servico=99999,
        ),
        hoje=HOJE,
    )
    excluir_ordem_servico(conexao, antiga.id_ordem_servico, hoje=HOJE)
    return conexao


def test_painel_apenas_reais(banco_com_dados):
    painel = calcular_painel(banco_com_dados, INICIO, FIM, FiltroOrigem.REAIS)
    assert painel.faturamento_recebido == 20000
    assert painel.quantidade_os == 2
    assert painel.quantidade_concluidas == 1
    assert painel.quantidade_canceladas == 1
    assert painel.contem_simulados is False
    assert painel.servicos_frequentes["quantidade"].tolist() == [1]


def test_painel_todos_inclui_e_sinaliza_simulados(banco_com_dados):
    painel = calcular_painel(banco_com_dados, INICIO, FIM, FiltroOrigem.TODOS)
    assert painel.faturamento_recebido == 27000
    assert painel.quantidade_os == 3
    assert painel.contem_simulados is True


def test_painel_apenas_simulados(banco_com_dados):
    painel = calcular_painel(banco_com_dados, INICIO, FIM, FiltroOrigem.SIMULADOS)
    assert painel.faturamento_recebido == 7000
    assert painel.quantidade_os == 1


def test_os_excluida_nunca_entra(banco_com_dados):
    painel = calcular_painel(
        banco_com_dados, date(2026, 1, 1), date(2026, 1, 31), FiltroOrigem.TODOS
    )
    assert painel.faturamento_recebido == 0
    assert painel.quantidade_os == 0


def test_evolucao_mensal_do_painel(banco_com_dados):
    painel = calcular_painel(banco_com_dados, INICIO, FIM, FiltroOrigem.REAIS, Frequencia.MES)
    assert len(painel.evolucao_faturamento) == 6  # jan a jun, só categoria Real
    assert painel.evolucao_faturamento["valor_centavos"].sum() == 20000


def test_periodo_invertido_rejeitado(conexao):
    with pytest.raises(ErroValidacao, match="data inicial"):
        calcular_painel(conexao, date(2026, 6, 1), date(2026, 5, 1))
