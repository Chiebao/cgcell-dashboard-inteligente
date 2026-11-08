"""Testes da preparação de variáveis para o modelo, com foco em vazamento de dados."""

from __future__ import annotations

import pandas as pd
import pytest

from cgcell.analise.agregacao import Frequencia
from cgcell.analise.pipeline import executar_pipeline
from cgcell.ml.preparacao import (
    Alvo,
    colunas_variaveis,
    criar_variaveis,
    montar_serie,
    preparar_tabela_modelo,
    remover_linhas_sem_historico,
)


def serie_mensal(valores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "periodo": pd.date_range("2026-01-01", periods=len(valores), freq="MS"),
            "valor": valores,
        }
    )


def test_defasagens_e_media_movel_usam_os_periodos_anteriores():
    tabela = criar_variaveis(serie_mensal([10, 20, 30, 40, 50]), Frequencia.MES)
    linha = tabela.iloc[4]  # período de maio, alvo = 50
    assert linha["alvo"] == 50
    assert linha["defasagem_1"] == 40
    assert linha["defasagem_2"] == 30
    assert linha["defasagem_3"] == 20
    assert linha["media_movel_3"] == pytest.approx((40 + 30 + 20) / 3)


def test_sem_vazamento_mudar_o_alvo_nao_muda_as_variaveis_da_mesma_linha():
    original = criar_variaveis(serie_mensal([10, 20, 30, 40, 50]), Frequencia.MES)
    alterada = criar_variaveis(serie_mensal([10, 20, 30, 40, 9999]), Frequencia.MES)
    variaveis = colunas_variaveis(original)
    pd.testing.assert_frame_equal(original[variaveis], alterada[variaveis])


def test_sem_vazamento_o_futuro_nao_afeta_o_passado():
    curta = criar_variaveis(serie_mensal([10, 20, 30, 40]), Frequencia.MES)
    longa = criar_variaveis(serie_mensal([10, 20, 30, 40, 500, 600]), Frequencia.MES)
    pd.testing.assert_frame_equal(curta, longa.iloc[:4].reset_index(drop=True))


def test_defasagem_zero_e_proibida():
    with pytest.raises(ValueError, match="defasagem 0"):
        criar_variaveis(serie_mensal([1, 2, 3]), Frequencia.MES, defasagens=(0, 1))


def test_serie_fora_de_ordem_e_rejeitada():
    serie = serie_mensal([1, 2, 3]).iloc[::-1]
    with pytest.raises(ValueError, match="ordem cronológica"):
        criar_variaveis(serie, Frequencia.MES)


def test_variaveis_de_calendario_por_frequencia():
    semanal = pd.DataFrame(
        {"periodo": pd.date_range("2026-01-05", periods=3, freq="7D"), "valor": [1, 2, 3]}
    )
    assert criar_variaveis(semanal, Frequencia.SEMANA)["semana_do_ano"].tolist() == [2, 3, 4]

    diaria = pd.DataFrame(
        {"periodo": pd.date_range("2026-01-05", periods=3, freq="D"), "valor": [1, 2, 3]}
    )
    assert criar_variaveis(diaria, Frequencia.DIA)["dia_semana"].tolist() == [0, 1, 2]


def test_remove_linhas_sem_historico_suficiente():
    tabela = criar_variaveis(serie_mensal([10, 20, 30, 40, 50]), Frequencia.MES)
    completa = remover_linhas_sem_historico(tabela)
    assert completa["alvo"].tolist() == [40, 50]  # as 3 primeiras não têm 3 meses de passado
    assert not completa[colunas_variaveis(completa)].isna().any().any()


def _registro(id_os: int, abertura: str, **campos) -> dict:
    return {
        "id_ordem_servico": id_os,
        "codigo_os": f"OS-{id_os}",
        "data_abertura": abertura,
        "data_conclusao": None,
        "data_pagamento": None,
        "valor_servico": 1000,
        "status_os": "aberta",
        "status_pagamento": "pendente",
        "id_tipo_servico": 1,
        "nome_servico": "Tela",
        "origem_registro": "manual",
    } | campos


def test_series_de_volume_e_faturamento_cobrem_o_mesmo_intervalo():
    base = executar_pipeline(
        [
            _registro(1, "2026-01-10"),
            _registro(
                2,
                "2026-01-20",
                status_pagamento="pago",
                data_pagamento="2026-03-05",
                valor_servico=500,
            ),
        ]
    ).base
    volume = montar_serie(base, Alvo.VOLUME, Frequencia.MES)
    faturamento = montar_serie(base, Alvo.FATURAMENTO, Frequencia.MES)
    assert volume["valor"].tolist() == [2, 0, 0]
    assert faturamento["valor"].tolist() == [0, 0, 500]
    assert volume["periodo"].tolist() == faturamento["periodo"].tolist()


def test_tabela_do_modelo_com_base_vazia():
    tabela = preparar_tabela_modelo(executar_pipeline([]).base, Alvo.VOLUME, Frequencia.MES)
    assert tabela.empty
