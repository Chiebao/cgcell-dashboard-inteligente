"""Serviço de dados: executa o pipeline sobre o banco e gera o relatório exploratório."""

from __future__ import annotations

import sqlite3

from cgcell.analise.exploracao import RelatorioExploratorio, gerar_relatorio
from cgcell.analise.pipeline import ResultadoPipeline, executar_pipeline
from cgcell.analise.preparacao import FiltroOrigem
from cgcell.dados import repositorio_ordens_servico


def executar_pipeline_do_banco(
    conexao: sqlite3.Connection, filtro_origem: FiltroOrigem = FiltroOrigem.TODOS
) -> ResultadoPipeline:
    """Lê as OS não excluídas e as passa pelo pipeline."""
    registros = repositorio_ordens_servico.listar_para_analise(conexao)
    return executar_pipeline(registros, filtro_origem)


def gerar_relatorio_exploratorio(
    conexao: sqlite3.Connection, filtro_origem: FiltroOrigem = FiltroOrigem.TODOS
) -> RelatorioExploratorio:
    return gerar_relatorio(executar_pipeline_do_banco(conexao, filtro_origem))
