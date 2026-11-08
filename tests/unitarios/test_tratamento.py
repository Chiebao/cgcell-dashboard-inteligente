"""Testes unitários de tratamento, validação, limpeza e agregação (sem banco)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from cgcell.analise.agregacao import Frequencia, agregar_por_periodo, agregar_por_tipo_servico
from cgcell.analise.preparacao import CATEGORIA_REAL, CATEGORIA_SIMULADO, criar_base_analise
from cgcell.analise.tratamento import (
    adicionar_colunas_derivadas,
    remover_duplicados,
    resumo_valores_ausentes,
    validar_registros,
)


def registro(**campos) -> dict:
    padrao = {
        "id_ordem_servico": 1,
        "codigo_os": "OS-1",
        "data_abertura": "2026-01-05",
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


def base_de(*registros: dict) -> pd.DataFrame:
    return criar_base_analise(list(registros))


# --- Tipagem ---


def test_datas_e_valores_invalidos_viram_ausentes_sem_quebrar():
    base = base_de(registro(data_abertura="05/01/2026", valor_servico="abc"))
    assert pd.isna(base.loc[0, "data_abertura"])
    assert pd.isna(base.loc[0, "valor_servico"])


# --- Valores ausentes ---


def test_resumo_de_ausentes_explica_os_casos_esperados():
    base = base_de(registro(), registro(id_ordem_servico=2, codigo_os="OS-2"))
    resumo = resumo_valores_ausentes(base, ["data_pagamento", "codigo_os"]).set_index("coluna")
    assert resumo.loc["data_pagamento", "ausentes"] == 2
    assert resumo.loc["data_pagamento", "percentual"] == 100.0
    assert "Esperado" in resumo.loc["data_pagamento", "observacao"]
    assert resumo.loc["codigo_os", "ausentes"] == 0


def test_resumo_de_ausentes_com_base_vazia():
    resumo = resumo_valores_ausentes(base_de(), ["codigo_os"])
    assert resumo.loc[0, "percentual"] == 0.0


# --- Validação ---


@pytest.mark.parametrize(
    ("campos", "trecho_motivo"),
    [
        ({"codigo_os": "  "}, "Código da OS ausente"),
        ({"valor_servico": -5}, "negativo"),
        ({"valor_servico": None}, "Valor do serviço ausente"),
        ({"data_abertura": "2026-02-30"}, "Data de abertura ausente ou inválida"),
        ({"status_os": "finalizada"}, "Status da OS inválido"),
        ({"status_pagamento": "parcial"}, "Status de pagamento inválido"),
        ({"origem_registro": "planilha"}, "Origem do registro inválida"),
        ({"status_pagamento": "pago"}, "informe a data de pagamento"),
        ({"data_pagamento": "2026-01-06"}, "data de pagamento deve ficar vazia"),
        ({"data_conclusao": "2026-01-06"}, "só pode ser preenchida quando a OS está concluída"),
        (
            {"status_os": "cancelada", "status_pagamento": "pago", "data_pagamento": "2026-01-06"},
            "cancelada não pode ter pagamento",
        ),
        (
            {"status_pagamento": "pago", "data_pagamento": "2026-01-01"},
            "pagamento não pode ser anterior",
        ),
    ],
)
def test_validacao_rejeita_com_motivo(campos, trecho_motivo):
    validos, rejeitados = validar_registros(base_de(registro(**campos)))
    assert validos.empty
    assert trecho_motivo in rejeitados.loc[0, "motivo"]


def test_validacao_mantem_validos_e_junta_motivos():
    base = base_de(
        registro(),
        registro(id_ordem_servico=2, codigo_os="", valor_servico=-1),
    )
    validos, rejeitados = validar_registros(base)
    assert validos["id_ordem_servico"].tolist() == [1]
    assert rejeitados["id_ordem_servico"].tolist() == [2]
    assert rejeitados.loc[0, "motivo"].count(";") == 1  # dois motivos juntos


def test_validacao_com_base_vazia():
    validos, rejeitados = validar_registros(base_de())
    assert validos.empty and rejeitados.empty


# --- Limpeza ---


def test_duplicados_sem_diferenciar_maiusculas_e_espacos():
    base = base_de(
        registro(id_ordem_servico=1, codigo_os="OS-1"),
        registro(id_ordem_servico=2, codigo_os=" os-1 "),
        registro(id_ordem_servico=3, codigo_os="OS-2"),
    )
    limpa, removidos = remover_duplicados(base)
    assert removidos == 1
    assert limpa["id_ordem_servico"].tolist() == [1, 3]


def test_limpeza_nao_altera_o_original():
    base = base_de(registro(), registro(id_ordem_servico=2))
    remover_duplicados(base)
    assert len(base) == 2


# --- Transformação ---


def test_colunas_derivadas():
    base = adicionar_colunas_derivadas(
        base_de(
            registro(
                data_abertura="2026-01-05",  # segunda-feira
                status_os="concluida",
                data_conclusao="2026-01-08",
                status_pagamento="pago",
                data_pagamento="2026-01-10",
            )
        )
    )
    linha = base.loc[0]
    assert linha["dia_semana"] == 0
    assert linha["mes"] == 1
    assert linha["dias_ate_conclusao"] == 3
    assert linha["dias_ate_pagamento"] == 5


# --- Agregação ---


def test_agregacao_por_periodo_preenche_zeros_no_intervalo_automatico():
    base = base_de(
        registro(data_abertura="2026-01-10"),
        registro(id_ordem_servico=2, data_abertura="2026-03-02"),
    )
    serie = agregar_por_periodo(base, "data_abertura", Frequencia.MES)
    assert serie["quantidade"].tolist() == [1, 0, 1]
    assert serie.columns.tolist() == ["periodo", "quantidade"]


def test_agregacao_por_periodo_soma_valor_e_separa_origem():
    base = base_de(
        registro(valor_servico=100),
        registro(id_ordem_servico=2, valor_servico=50, origem_registro="simulado"),
    )
    serie = agregar_por_periodo(
        base,
        "data_abertura",
        Frequencia.MES,
        inicio=date(2026, 1, 1),
        fim=date(2026, 1, 31),
        coluna_valor="valor_servico",
        por_origem=True,
        nome_resultado="valor",
    )
    assert dict(zip(serie["categoria"], serie["valor"], strict=True)) == {
        CATEGORIA_REAL: 100,
        CATEGORIA_SIMULADO: 50,
    }


def test_agregacao_por_periodo_vazia_sem_intervalo():
    assert agregar_por_periodo(base_de(), "data_abertura", Frequencia.DIA).empty


def test_agregacao_por_tipo_de_servico():
    base = base_de(
        registro(nome_servico="Tela", valor_servico=100),
        registro(id_ordem_servico=2, nome_servico="Tela", valor_servico=200),
        registro(id_ordem_servico=3, nome_servico="Bateria", valor_servico=50),
    )
    assert agregar_por_tipo_servico(base).to_dict("records") == [
        {"nome_servico": "Tela", "quantidade": 2, "valor_servicos_centavos": 300},
        {"nome_servico": "Bateria", "quantidade": 1, "valor_servicos_centavos": 50},
    ]
