"""Testes do pipeline e do relatório exploratório (sem banco)."""

from __future__ import annotations

from datetime import date

from cgcell.analise.agregacao import Frequencia
from cgcell.analise.exploracao import gerar_relatorio, sugerir_frequencia
from cgcell.analise.pipeline import executar_pipeline
from cgcell.analise.preparacao import CATEGORIA_REAL, CATEGORIA_SIMULADO, FiltroOrigem


def registro(id_os: int, abertura: str, **campos) -> dict:
    padrao = {
        "id_ordem_servico": id_os,
        "codigo_os": f"OS-{id_os}",
        "data_abertura": abertura,
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


REGISTROS = [
    registro(1, "2026-01-05", status_os="concluida", data_conclusao="2026-01-07"),
    registro(2, "2026-01-06", codigo_os="os-1"),  # duplicado do código OS-1
    registro(3, "2026-01-12", valor_servico=-1),  # inconsistente
    registro(4, "2026-02-02", origem_registro="simulado"),
    registro(5, "2026-02-09"),
]


def test_pipeline_valida_limpa_e_transforma():
    resultado = executar_pipeline(REGISTROS)
    assert resultado.total_entrada == 5
    assert resultado.rejeitados["id_ordem_servico"].tolist() == [3]
    assert resultado.duplicados_removidos == 1
    assert resultado.base["id_ordem_servico"].tolist() == [1, 4, 5]
    assert {"dia_semana", "mes", "dias_ate_conclusao"} <= set(resultado.base.columns)


def test_pipeline_e_reprodutivel():
    primeiro = executar_pipeline(REGISTROS)
    segundo = executar_pipeline(REGISTROS)
    assert primeiro.base.equals(segundo.base)
    assert primeiro.rejeitados.equals(segundo.rejeitados)


def test_pipeline_recorta_por_origem_antes_de_validar():
    resultado = executar_pipeline(REGISTROS, FiltroOrigem.SIMULADOS)
    assert resultado.total_entrada == 1
    assert resultado.base["id_ordem_servico"].tolist() == [4]
    assert resultado.rejeitados.empty


def test_relatorio_descreve_os_dados():
    relatorio = gerar_relatorio(executar_pipeline(REGISTROS))
    assert relatorio.total_valido == 3
    assert relatorio.quantidade_rejeitados == 1
    assert relatorio.duplicados_removidos == 1
    assert relatorio.quantidade_por_origem == {CATEGORIA_REAL: 2, CATEGORIA_SIMULADO: 1}
    assert relatorio.primeira_abertura == date(2026, 1, 5)
    assert relatorio.ultima_abertura == date(2026, 2, 9)
    assert relatorio.dias_de_historico == 36
    assert relatorio.por_dia_semana.set_index("dia_semana").loc["Segunda", "quantidade"] == 3
    assert relatorio.tempos.loc[0, "mediana_dias"] == 2.0
    texto = " ".join(relatorio.observacoes)
    assert "SIMULADAS" in texto
    assert "inconsistente" in texto


def test_relatorio_com_base_vazia():
    relatorio = gerar_relatorio(executar_pipeline([]))
    assert relatorio.total_valido == 0
    assert relatorio.primeira_abertura is None
    assert relatorio.frequencia_sugerida is None
    assert "Nenhum registro" in relatorio.observacoes[0]


def test_frequencia_sugerida_e_a_mais_detalhada_com_poucos_periodos_vazios():
    # Uma OS por dia durante 3 semanas: o agrupamento diário já não tem buracos.
    diario = [registro(i, f"2026-03-{i:02d}") for i in range(1, 22)]
    relatorio = gerar_relatorio(executar_pipeline(diario))
    assert relatorio.frequencia_sugerida == Frequencia.DIA

    # Uma OS por mês: dia e semana ficam quase vazios; sugere mês.
    mensal = [registro(i, f"2026-{i:02d}-10") for i in range(1, 7)]
    assert gerar_relatorio(executar_pipeline(mensal)).frequencia_sugerida == Frequencia.MES


def test_cobertura_tem_rotulo_legivel():
    relatorio = gerar_relatorio(executar_pipeline(REGISTROS))
    assert relatorio.cobertura["agrupamento"].tolist() == ["Dia", "Semana", "Mês"]
    assert sugerir_frequencia(relatorio.cobertura) in set(Frequencia)
