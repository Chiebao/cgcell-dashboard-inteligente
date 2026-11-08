"""Integração: pipeline e relatório exploratório a partir do banco temporário."""

from __future__ import annotations

from datetime import date

from cgcell.analise.preparacao import FiltroOrigem
from cgcell.dominio import OrigemRegistro
from cgcell.servicos.servico_dados import (
    executar_pipeline_do_banco,
    gerar_relatorio_exploratorio,
)
from cgcell.servicos.servico_ordens_servico import (
    cadastrar_ordem_servico,
    excluir_ordem_servico,
)
from tests.conftest import HOJE


def test_pipeline_do_banco_ignora_excluidas_e_separa_origem(conexao, fabricar_dados):
    cadastrar_ordem_servico(conexao, fabricar_dados(codigo_os="R1"), hoje=HOJE)
    cadastrar_ordem_servico(
        conexao,
        fabricar_dados(codigo_os="S1"),
        origem_registro=OrigemRegistro.SIMULADO,
        hoje=HOJE,
    )
    antiga = cadastrar_ordem_servico(
        conexao, fabricar_dados(codigo_os="X1", data_abertura=date(2026, 1, 2)), hoje=HOJE
    )
    excluir_ordem_servico(conexao, antiga.id_ordem_servico, hoje=HOJE)

    todos = executar_pipeline_do_banco(conexao)
    assert sorted(todos.base["codigo_os"]) == ["R1", "S1"]
    assert todos.rejeitados.empty  # o banco já garante a consistência

    reais = executar_pipeline_do_banco(conexao, FiltroOrigem.REAIS)
    assert reais.base["codigo_os"].tolist() == ["R1"]


def test_relatorio_do_banco(conexao, fabricar_dados):
    cadastrar_ordem_servico(conexao, fabricar_dados(codigo_os="R1"), hoje=HOJE)
    relatorio = gerar_relatorio_exploratorio(conexao)
    assert relatorio.total_valido == 1
    assert relatorio.por_tipo_servico.loc[0, "nome_servico"] == "Troca de tela"


def test_relatorio_com_banco_vazio(conexao):
    relatorio = gerar_relatorio_exploratorio(conexao)
    assert relatorio.total_valido == 0
