"""Testes de integração do serviço de tipos de serviço."""

from __future__ import annotations

import pytest

from cgcell.servicos.erros import ErroValidacao, RegistroNaoEncontrado
from cgcell.servicos.servico_tipos_servico import (
    ativar_tipo_servico,
    cadastrar_tipo_servico,
    desativar_tipo_servico,
    listar_tipos_servico,
    obter_tipo_servico,
)


def test_cadastrar_e_consultar(conexao):
    tipo = cadastrar_tipo_servico(conexao, "  Troca   de bateria ", "  ")
    assert tipo.nome_servico == "Troca de bateria"
    assert tipo.descricao is None
    assert tipo.ativo is True
    assert obter_tipo_servico(conexao, tipo.id_tipo_servico) == tipo


def test_nome_obrigatorio(conexao):
    with pytest.raises(ErroValidacao, match="Informe o nome do serviço"):
        cadastrar_tipo_servico(conexao, "   ")


def test_nome_duplicado_sem_diferenciar_maiusculas(conexao, tipo_tela):
    with pytest.raises(ErroValidacao, match="Já existe"):
        cadastrar_tipo_servico(conexao, "TROCA DE TELA")


def test_listar_em_ordem_alfabetica(conexao):
    for nome in ("Troca de tela", "Banho químico", "Conector de carga"):
        cadastrar_tipo_servico(conexao, nome)
    nomes = [tipo.nome_servico for tipo in listar_tipos_servico(conexao)]
    assert nomes == ["Banho químico", "Conector de carga", "Troca de tela"]


def test_desativar_e_ativar(conexao, tipo_tela):
    desativado = desativar_tipo_servico(conexao, tipo_tela.id_tipo_servico)
    assert desativado.ativo is False
    assert listar_tipos_servico(conexao, somente_ativos=True) == []
    assert len(listar_tipos_servico(conexao)) == 1

    reativado = ativar_tipo_servico(conexao, tipo_tela.id_tipo_servico)
    assert reativado.ativo is True


def test_tipo_inexistente(conexao):
    with pytest.raises(RegistroNaoEncontrado):
        desativar_tipo_servico(conexao, 999)
