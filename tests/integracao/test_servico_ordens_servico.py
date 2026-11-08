"""Testes de integração do serviço de ordens de serviço (cadastro, edição, pagamento, exclusão)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from cgcell.dominio import OrigemRegistro, StatusOS, StatusPagamento
from cgcell.servicos import servico_ordens_servico as servico
from cgcell.servicos.erros import ErroValidacao, OperacaoNaoPermitida, RegistroNaoEncontrado
from cgcell.servicos.servico_tipos_servico import cadastrar_tipo_servico, desativar_tipo_servico
from tests.conftest import HOJE


@pytest.fixture
def relogio(monkeypatch):
    """Controla o 'agora' do serviço para testar criado_em e atualizado_em."""
    momentos = iter(datetime(2026, 6, 15, 9, minuto) for minuto in range(60))
    monkeypatch.setattr(servico, "agora", lambda: next(momentos))


def cadastrar(conexao, dados, **kwargs):
    return servico.cadastrar_ordem_servico(conexao, dados, hoje=HOJE, **kwargs)


# --- Cadastro e consulta ---


def test_cadastrar_e_consultar(conexao, fabricar_dados, relogio):
    ordem = cadastrar(conexao, fabricar_dados())
    assert ordem.codigo_os == "OS-0001"
    assert ordem.valor_servico == 15000
    assert ordem.status_os is StatusOS.ABERTA
    assert ordem.origem_registro is OrigemRegistro.MANUAL
    assert ordem.excluida is False
    assert ordem.criado_em == ordem.atualizado_em == datetime(2026, 6, 15, 9, 0)
    assert servico.obter_ordem_servico(conexao, ordem.id_ordem_servico) == ordem


def test_cadastrar_com_origem_simulada(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(), origem_registro=OrigemRegistro.SIMULADO)
    assert ordem.origem_registro is OrigemRegistro.SIMULADO


def test_codigo_duplicado_rejeitado(conexao, fabricar_dados):
    cadastrar(conexao, fabricar_dados(codigo_os="OS-10"))
    with pytest.raises(ErroValidacao, match="Já existe uma OS com o código"):
        cadastrar(conexao, fabricar_dados(codigo_os="os-10"))


def test_tipo_inexistente_rejeitado(conexao, fabricar_dados):
    with pytest.raises(ErroValidacao, match="Tipo de serviço não encontrado"):
        cadastrar(conexao, fabricar_dados(id_tipo_servico=999))


def test_tipo_desativado_nao_aceita_nova_os(conexao, fabricar_dados, tipo_tela):
    desativar_tipo_servico(conexao, tipo_tela.id_tipo_servico)
    with pytest.raises(ErroValidacao, match="desativado"):
        cadastrar(conexao, fabricar_dados())


def test_dados_inconsistentes_nao_sao_gravados(conexao, fabricar_dados):
    with pytest.raises(ErroValidacao):
        cadastrar(conexao, fabricar_dados(status_pagamento=StatusPagamento.PAGO))
    assert servico.listar_ordens_servico(conexao) == []


def test_listar_da_mais_recente_para_a_mais_antiga(conexao, fabricar_dados):
    cadastrar(conexao, fabricar_dados(codigo_os="A", data_abertura=date(2026, 5, 1)))
    cadastrar(conexao, fabricar_dados(codigo_os="B", data_abertura=date(2026, 6, 1)))
    assert [o.codigo_os for o in servico.listar_ordens_servico(conexao)] == ["B", "A"]


# --- Edição ---


def test_editar_os_aberta_atualiza_campos_e_data_de_alteracao(conexao, fabricar_dados, relogio):
    ordem = cadastrar(conexao, fabricar_dados())
    editada = servico.editar_ordem_servico(
        conexao,
        ordem.id_ordem_servico,
        replace(ordem.para_dados(), valor_servico=20000, status_os=StatusOS.EM_ANDAMENTO),
        hoje=HOJE,
    )
    assert editada.valor_servico == 20000
    assert editada.status_os is StatusOS.EM_ANDAMENTO
    assert editada.criado_em == ordem.criado_em
    assert editada.atualizado_em > ordem.atualizado_em


def test_editar_para_codigo_de_outra_os_rejeitado(conexao, fabricar_dados):
    cadastrar(conexao, fabricar_dados(codigo_os="A"))
    ordem_b = cadastrar(conexao, fabricar_dados(codigo_os="B"))
    with pytest.raises(ErroValidacao, match="Já existe"):
        servico.editar_ordem_servico(
            conexao,
            ordem_b.id_ordem_servico,
            replace(ordem_b.para_dados(), codigo_os="A"),
            hoje=HOJE,
        )


def test_editar_mantendo_o_proprio_codigo(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados())
    servico.editar_ordem_servico(conexao, ordem.id_ordem_servico, ordem.para_dados(), hoje=HOJE)


def test_os_antiga_mantem_tipo_desativado_na_edicao(conexao, fabricar_dados, tipo_tela):
    ordem = cadastrar(conexao, fabricar_dados())
    desativar_tipo_servico(conexao, tipo_tela.id_tipo_servico)
    editada = servico.editar_ordem_servico(
        conexao,
        ordem.id_ordem_servico,
        replace(ordem.para_dados(), valor_servico=1),
        hoje=HOJE,
    )
    assert editada.id_tipo_servico == tipo_tela.id_tipo_servico


def test_edicao_nao_pode_trocar_para_tipo_desativado(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados())
    bateria = cadastrar_tipo_servico(conexao, "Troca de bateria")
    desativar_tipo_servico(conexao, bateria.id_tipo_servico)
    with pytest.raises(ErroValidacao, match="desativado"):
        servico.editar_ordem_servico(
            conexao,
            ordem.id_ordem_servico,
            replace(ordem.para_dados(), id_tipo_servico=bateria.id_tipo_servico),
            hoje=HOJE,
        )


def test_os_cancelada_bloqueada_para_edicao(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(status_os=StatusOS.CANCELADA))
    with pytest.raises(OperacaoNaoPermitida, match="cancelada"):
        servico.editar_ordem_servico(conexao, ordem.id_ordem_servico, ordem.para_dados(), hoje=HOJE)


def test_os_concluida_pendente_so_permite_pagamento(conexao, fabricar_dados):
    ordem = cadastrar(
        conexao,
        fabricar_dados(status_os=StatusOS.CONCLUIDA, data_conclusao=date(2026, 6, 5)),
    )
    with pytest.raises(OperacaoNaoPermitida, match="registrar o pagamento"):
        servico.editar_ordem_servico(
            conexao,
            ordem.id_ordem_servico,
            replace(ordem.para_dados(), valor_servico=1),
            hoje=HOJE,
        )


def test_os_concluida_e_paga_bloqueada(conexao, fabricar_dados):
    ordem = cadastrar(
        conexao,
        fabricar_dados(
            status_os=StatusOS.CONCLUIDA,
            data_conclusao=date(2026, 6, 5),
            status_pagamento=StatusPagamento.PAGO,
            data_pagamento=date(2026, 6, 5),
        ),
    )
    with pytest.raises(OperacaoNaoPermitida, match="finalizada"):
        servico.editar_ordem_servico(conexao, ordem.id_ordem_servico, ordem.para_dados(), hoje=HOJE)


# --- Pagamento ---


def test_registrar_pagamento_em_os_concluida(conexao, fabricar_dados):
    ordem = cadastrar(
        conexao,
        fabricar_dados(status_os=StatusOS.CONCLUIDA, data_conclusao=date(2026, 6, 5)),
    )
    paga = servico.registrar_pagamento(
        conexao, ordem.id_ordem_servico, date(2026, 6, 10), hoje=HOJE
    )
    assert paga.status_pagamento is StatusPagamento.PAGO
    assert paga.data_pagamento == date(2026, 6, 10)
    assert servico.motivo_bloqueio_edicao(paga) is not None


def test_pagamento_antes_da_abertura_rejeitado(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados())
    with pytest.raises(ErroValidacao, match="anterior à data de abertura"):
        servico.registrar_pagamento(conexao, ordem.id_ordem_servico, date(2026, 5, 1), hoje=HOJE)


def test_pagamento_em_os_cancelada_rejeitado(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(status_os=StatusOS.CANCELADA))
    with pytest.raises(OperacaoNaoPermitida, match="cancelada"):
        servico.registrar_pagamento(conexao, ordem.id_ordem_servico, date(2026, 6, 10), hoje=HOJE)


def test_pagamento_duplicado_rejeitado(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados())
    servico.registrar_pagamento(conexao, ordem.id_ordem_servico, date(2026, 6, 2), hoje=HOJE)
    with pytest.raises(OperacaoNaoPermitida, match="já foi registrado"):
        servico.registrar_pagamento(conexao, ordem.id_ordem_servico, date(2026, 6, 3), hoje=HOJE)


# --- Exclusão lógica ---


def test_exclusao_bloqueada_com_90_dias_ou_menos(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(data_abertura=date(2026, 3, 17)))  # 90 dias
    with pytest.raises(OperacaoNaoPermitida, match="mais de 90 dias"):
        servico.excluir_ordem_servico(conexao, ordem.id_ordem_servico, hoje=HOJE)


def test_exclusao_logica_com_mais_de_90_dias(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(data_abertura=date(2026, 3, 16)))  # 91 dias
    servico.excluir_ordem_servico(conexao, ordem.id_ordem_servico, hoje=HOJE)

    assert servico.listar_ordens_servico(conexao) == []
    with pytest.raises(RegistroNaoEncontrado):
        servico.obter_ordem_servico(conexao, ordem.id_ordem_servico)

    linha = conexao.execute(
        "SELECT excluida, excluida_em FROM ordem_servico WHERE id_ordem_servico = ?",
        (ordem.id_ordem_servico,),
    ).fetchone()
    assert linha["excluida"] == 1
    assert linha["excluida_em"] is not None


def test_os_excluida_nao_pode_ser_editada_nem_excluida_de_novo(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(data_abertura=date(2026, 1, 1)))
    servico.excluir_ordem_servico(conexao, ordem.id_ordem_servico, hoje=HOJE)
    with pytest.raises(RegistroNaoEncontrado):
        servico.editar_ordem_servico(conexao, ordem.id_ordem_servico, ordem.para_dados(), hoje=HOJE)
    with pytest.raises(RegistroNaoEncontrado):
        servico.excluir_ordem_servico(conexao, ordem.id_ordem_servico, hoje=HOJE)


def test_codigo_de_os_excluida_nao_e_reutilizado(conexao, fabricar_dados):
    ordem = cadastrar(conexao, fabricar_dados(data_abertura=date(2026, 1, 1)))
    servico.excluir_ordem_servico(conexao, ordem.id_ordem_servico, hoje=HOJE)
    with pytest.raises(ErroValidacao, match="Já existe"):
        cadastrar(conexao, fabricar_dados())
