"""Fixtures compartilhadas pelos testes.

Regras: todo teste usa um banco TEMPORÁRIO e dados fictícios.
O banco da aplicação nunca é aberto durante os testes.
"""

from __future__ import annotations

from datetime import date

import pytest

from cgcell.dados.conexao import inicializar_banco
from cgcell.dominio import DadosOrdemServico, TipoServico
from cgcell.servicos.servico_tipos_servico import cadastrar_tipo_servico

HOJE = date(2026, 6, 15)
"""Data fixa usada como 'hoje' nos testes, para resultados reprodutíveis."""


@pytest.fixture(autouse=True)
def isolar_banco_da_aplicacao(tmp_path_factory, monkeypatch):
    """Se algum código usar o caminho padrão por engano, ele cai numa pasta temporária."""
    pasta = tmp_path_factory.mktemp("banco_padrao")
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", str(pasta / "nao_usar.db"))


@pytest.fixture
def conexao(tmp_path):
    """Banco temporário com todas as migrações aplicadas."""
    con = inicializar_banco(tmp_path / "teste.db")
    yield con
    con.close()


@pytest.fixture
def tipo_tela(conexao) -> TipoServico:
    return cadastrar_tipo_servico(conexao, "Troca de tela", "Substituição do display")


@pytest.fixture
def fabricar_dados(tipo_tela):
    """Cria `DadosOrdemServico` válidos, permitindo sobrescrever qualquer campo."""

    def _fabricar(**campos) -> DadosOrdemServico:
        padrao = {
            "codigo_os": "OS-0001",
            "data_abertura": date(2026, 6, 1),
            "valor_servico": 15000,
            "id_tipo_servico": tipo_tela.id_tipo_servico,
        }
        return DadosOrdemServico(**(padrao | campos))

    return _fabricar
