"""Testes unitários das validações e regras de consistência (sem banco)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from cgcell.dominio import DadosOrdemServico, StatusOS, StatusPagamento
from cgcell.servicos.erros import ErroValidacao
from cgcell.servicos.validacoes import (
    TAMANHO_MAXIMO_CODIGO_OS,
    validar_dados_ordem_servico,
    verificar_consistencia,
)

HOJE = date(2026, 6, 15)


def dados(**campos) -> DadosOrdemServico:
    padrao = {
        "codigo_os": "OS-0001",
        "data_abertura": date(2026, 6, 1),
        "valor_servico": 15000,
        "id_tipo_servico": 1,
    }
    return DadosOrdemServico(**(padrao | campos))


def erros_de(dados_os: DadosOrdemServico) -> list[str]:
    with pytest.raises(ErroValidacao) as info:
        validar_dados_ordem_servico(dados_os, HOJE)
    return info.value.erros


# --- Casos válidos ---


def test_dados_validos_sao_normalizados():
    resultado = validar_dados_ordem_servico(dados(codigo_os="  OS   0001 "), HOJE)
    assert resultado.codigo_os == "OS 0001"
    assert resultado.status_os is StatusOS.ABERTA


def test_status_em_texto_e_convertido_para_enum():
    resultado = validar_dados_ordem_servico(
        dados(status_os="em_andamento", status_pagamento="pendente"), HOJE
    )
    assert resultado.status_os is StatusOS.EM_ANDAMENTO
    assert resultado.status_pagamento is StatusPagamento.PENDENTE


def test_valor_zero_e_permitido_para_garantia():
    assert validar_dados_ordem_servico(dados(valor_servico=0), HOJE).valor_servico == 0


def test_os_concluida_e_paga_com_datas_validas():
    resultado = validar_dados_ordem_servico(
        dados(
            status_os=StatusOS.CONCLUIDA,
            data_conclusao=date(2026, 6, 3),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 6, 3),
        ),
        HOJE,
    )
    assert resultado.data_pagamento == date(2026, 6, 3)


def test_datas_iguais_a_abertura_sao_aceitas():
    validar_dados_ordem_servico(
        dados(
            status_os=StatusOS.CONCLUIDA,
            data_conclusao=date(2026, 6, 1),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 6, 1),
        ),
        HOJE,
    )


# --- Campos obrigatórios e valores ---


@pytest.mark.parametrize("codigo", ["", "   ", None])
def test_codigo_obrigatorio(codigo):
    assert "Informe o código da OS." in erros_de(dados(codigo_os=codigo))


def test_codigo_muito_longo():
    erros = erros_de(dados(codigo_os="X" * (TAMANHO_MAXIMO_CODIGO_OS + 1)))
    assert any("no máximo" in erro for erro in erros)


def test_valor_negativo_rejeitado():
    assert "O valor do serviço não pode ser negativo." in erros_de(dados(valor_servico=-1))


@pytest.mark.parametrize("valor", [150.0, "15000", True, None])
def test_valor_precisa_ser_inteiro_em_centavos(valor):
    erros = erros_de(dados(valor_servico=valor))
    assert "O valor do serviço deve ser um número inteiro de centavos." in erros


def test_status_invalidos():
    erros = erros_de(dados(status_os="finalizada", status_pagamento="parcial"))
    assert "Status da OS inválido." in erros
    assert "Status de pagamento inválido." in erros


# --- Datas ---


@pytest.mark.parametrize("valor", [None, "2026-06-01", datetime(2026, 6, 1, 10, 0)])
def test_data_abertura_invalida(valor):
    assert "Informe uma data de abertura válida." in erros_de(dados(data_abertura=valor))


def test_data_abertura_no_futuro_rejeitada():
    erros = erros_de(dados(data_abertura=date(2026, 6, 16)))
    assert "A data de abertura não pode estar no futuro." in erros


def test_data_pagamento_no_futuro_rejeitada():
    erros = erros_de(dados(status_pagamento=StatusPagamento.PAGO, data_pagamento=date(2026, 7, 1)))
    assert "A data de pagamento não pode estar no futuro." in erros


def test_varios_erros_sao_reportados_juntos():
    erros = erros_de(dados(codigo_os="", valor_servico=-5, data_abertura=None))
    assert len(erros) == 3


# --- Regras de consistência entre campos ---


def test_pago_exige_data_pagamento():
    erros = verificar_consistencia(
        StatusOS.ABERTA, StatusPagamento.PAGO, date(2026, 6, 1), None, None
    )
    assert erros == ["Para marcar como pago, informe a data de pagamento."]


def test_pendente_exige_data_pagamento_vazia():
    erros = verificar_consistencia(
        StatusOS.ABERTA, StatusPagamento.PENDENTE, date(2026, 6, 1), None, date(2026, 6, 2)
    )
    assert erros == ["Com pagamento pendente, a data de pagamento deve ficar vazia."]


@pytest.mark.parametrize("status", [StatusOS.ABERTA, StatusOS.EM_ANDAMENTO, StatusOS.CANCELADA])
def test_data_conclusao_so_com_status_concluida(status):
    erros = verificar_consistencia(
        status, StatusPagamento.PENDENTE, date(2026, 6, 1), date(2026, 6, 2), None
    )
    assert "A data de conclusão só pode ser preenchida quando a OS está concluída." in erros


def test_conclusao_anterior_a_abertura():
    erros = verificar_consistencia(
        StatusOS.CONCLUIDA, StatusPagamento.PENDENTE, date(2026, 6, 10), date(2026, 6, 9), None
    )
    assert erros == ["A data de conclusão não pode ser anterior à data de abertura."]


def test_pagamento_anterior_a_abertura():
    erros = verificar_consistencia(
        StatusOS.ABERTA, StatusPagamento.PAGO, date(2026, 6, 10), None, date(2026, 6, 9)
    )
    assert erros == ["A data de pagamento não pode ser anterior à data de abertura."]


def test_os_cancelada_nao_pode_ser_paga():
    erros = verificar_consistencia(
        StatusOS.CANCELADA, StatusPagamento.PAGO, date(2026, 6, 1), None, date(2026, 6, 2)
    )
    assert erros == ["OS cancelada não pode ter pagamento registrado."]


def test_os_cancelada_pendente_e_valida():
    assert (
        verificar_consistencia(
            StatusOS.CANCELADA, StatusPagamento.PENDENTE, date(2026, 6, 1), None, None
        )
        == []
    )


def test_os_aberta_pode_ser_paga_antecipadamente():
    assert (
        verificar_consistencia(
            StatusOS.ABERTA, StatusPagamento.PAGO, date(2026, 6, 1), None, date(2026, 6, 1)
        )
        == []
    )
