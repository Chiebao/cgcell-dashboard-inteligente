"""Testes da interface com o AppTest do Streamlit (sem navegador).

Cada teste roda a página de verdade contra um banco temporário
(a fixture automática do conftest aponta CGCELL_CAMINHO_BANCO para uma pasta temporária).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from cgcell.servicos.servico_ordens_servico import listar_ordens_servico
from cgcell.servicos.servico_tipos_servico import listar_tipos_servico
from cgcell.servicos.sessao import abrir_conexao

TEMPO_LIMITE = 30
ARQUIVO_APP = Path(__file__).resolve().parents[2] / "app.py"


def pagina(modulo: str) -> AppTest:
    script = f"from cgcell.apresentacao import {modulo}\n{modulo}.renderizar()\n"
    return AppTest.from_string(script, default_timeout=TEMPO_LIMITE)


def texto_da_tela(app: AppTest) -> str:
    partes = [elemento.value for elemento in app.markdown]
    partes += [elemento.value for elemento in app.info]
    partes += [elemento.value for elemento in app.success]
    partes += [elemento.value for elemento in app.error]
    partes += [elemento.value for elemento in app.warning]
    return "\n".join(str(parte) for parte in partes)


def test_app_completo_abre_no_dashboard():
    app = AppTest.from_file(str(ARQUIVO_APP), default_timeout=TEMPO_LIMITE).run()
    assert not app.exception
    assert any("Dashboard gerencial" in cabecalho.value for cabecalho in app.header)


@pytest.mark.parametrize(
    "modulo",
    ["pagina_dashboard", "pagina_exploracao", "pagina_ordens_servico", "pagina_tipos_servico"],
)
def test_paginas_abrem_com_banco_vazio(modulo):
    app = pagina(modulo).run()
    assert not app.exception


def test_cadastrar_tipo_pela_tela():
    app = pagina("pagina_tipos_servico").run()
    app.text_input[0].input("Troca de tela")
    app.button[0].click().run()
    assert not app.exception
    assert "Troca de tela" in texto_da_tela(app)

    with abrir_conexao() as conexao:
        assert [tipo.nome_servico for tipo in listar_tipos_servico(conexao)] == ["Troca de tela"]


def test_cadastrar_tipo_vazio_mostra_erro():
    app = pagina("pagina_tipos_servico").run()
    app.button[0].click().run()
    assert "Informe o nome do serviço." in texto_da_tela(app)


def test_nova_os_sem_tipo_pede_cadastro_de_tipo():
    app = pagina("pagina_ordens_servico").run()
    assert "Nenhum tipo de serviço ativo" in texto_da_tela(app)


def _app_com_tipo() -> AppTest:
    app = pagina("pagina_tipos_servico").run()
    app.text_input[0].input("Troca de tela")
    app.button[0].click().run()
    return pagina("pagina_ordens_servico").run()


def test_cadastrar_os_pela_tela():
    app = _app_com_tipo()
    app.text_input(key=[k for k in _chaves(app) if k.endswith("_codigo")][0]).input("2026-0001")
    app.text_input(key=[k for k in _chaves(app) if k.endswith("_valor")][0]).input("1.234,56")
    app.button[0].click().run()
    assert not app.exception
    assert "2026-0001" in texto_da_tela(app)

    with abrir_conexao() as conexao:
        ordens = listar_ordens_servico(conexao)
    assert len(ordens) == 1
    assert ordens[0].valor_servico == 123456
    assert ordens[0].data_abertura == date.today()


def test_valor_invalido_mostra_erro_e_nao_grava():
    app = _app_com_tipo()
    app.text_input(key=[k for k in _chaves(app) if k.endswith("_codigo")][0]).input("A1")
    app.text_input(key=[k for k in _chaves(app) if k.endswith("_valor")][0]).input("150.50")
    app.button[0].click().run()
    assert "Valor inválido" in texto_da_tela(app)
    with abrir_conexao() as conexao:
        assert listar_ordens_servico(conexao) == []


def test_dashboard_mostra_indicadores_da_os_paga():
    app = _app_com_tipo()
    chaves = _chaves(app)
    app.text_input(key=[k for k in chaves if k.endswith("_codigo")][0]).input("P1")
    app.text_input(key=[k for k in chaves if k.endswith("_valor")][0]).input("200")
    app.selectbox(key=[k for k in chaves if k.endswith("_pagamento")][0]).select_index(1)  # "Pago"
    app.date_input(key=[k for k in chaves if k.endswith("_data_pagamento")][0]).set_value(
        date.today()
    )
    app.button[0].click().run()
    assert not app.exception

    painel = pagina("pagina_dashboard").run()
    assert not painel.exception
    # O valor usa espaço que não quebra entre "R$" e o número.
    valores = {metrica.label: metrica.value.replace("\xa0", " ") for metrica in painel.metric}
    assert valores["Faturamento recebido"] == "R$ 200,00"
    assert valores["Quantidade de OS"] == "1"


def _chaves(app: AppTest) -> list[str]:
    return [
        str(elemento.key)
        for colecao in (app.text_input, app.selectbox, app.date_input)
        for elemento in colecao
        if elemento.key
    ]


def test_pagina_exploracao_com_dados():
    app = _app_com_tipo()
    chaves = _chaves(app)
    app.text_input(key=[k for k in chaves if k.endswith("_codigo")][0]).input("E1")
    app.text_input(key=[k for k in chaves if k.endswith("_valor")][0]).input("50")
    app.button[0].click().run()

    exploracao = pagina("pagina_exploracao").run()
    assert not exploracao.exception
    metricas = {metrica.label: metrica.value for metrica in exploracao.metric}
    assert metricas["OS válidas"] == "1"
    assert "Nenhuma inconsistência encontrada." in texto_da_tela(exploracao)


def test_script_relatorio_exploratorio(capsys):
    from scripts import relatorio_exploratorio

    assert relatorio_exploratorio.main(["--origem", "reais"]) == 0
    assert "RELATÓRIO EXPLORATÓRIO" in capsys.readouterr().out


def _app_completo() -> AppTest:
    return AppTest.from_file(str(ARQUIVO_APP), default_timeout=TEMPO_LIMITE).run()


def test_painel_de_acessibilidade_aparece_na_barra_lateral():
    app = _app_completo()
    assert not app.exception
    rotulos = [elemento.label for elemento in app.sidebar.toggle]
    assert rotulos == ["Alto contraste", "Resumo em texto dos gráficos"]
    assert app.sidebar.radio(key="acessibilidade_tamanho_fonte").value == "normal"


def test_ligar_alto_contraste_e_trocar_fonte_sem_erro():
    from cgcell.apresentacao.acessibilidade import (
        CHAVE_ALTO_CONTRASTE,
        CHAVE_RESUMO_TEXTO,
        CHAVE_TAMANHO_FONTE,
        TamanhoFonte,
    )

    # Uma OS paga para o dashboard ter gráficos.
    cadastro = _app_com_tipo()
    chaves = _chaves(cadastro)
    cadastro.text_input(key=[k for k in chaves if k.endswith("_codigo")][0]).input("A1")
    cadastro.text_input(key=[k for k in chaves if k.endswith("_valor")][0]).input("349,50")
    cadastro.selectbox(key=[k for k in chaves if k.endswith("_pagamento")][0]).select_index(1)
    cadastro.date_input(key=[k for k in chaves if k.endswith("_data_pagamento")][0]).set_value(
        date.today()
    )
    cadastro.button[0].click().run()

    app = _app_completo()
    app.toggle(key=CHAVE_ALTO_CONTRASTE).set_value(True).run()
    assert not app.exception
    for tamanho in (TamanhoFonte.GRANDE, TamanhoFonte.MUITO_GRANDE, TamanhoFonte.NORMAL):
        app.radio(key=CHAVE_TAMANHO_FONTE).set_value(tamanho).run()
        assert not app.exception
        assert app.session_state[CHAVE_TAMANHO_FONTE] == tamanho

    assert "Resumo do gráfico" not in texto_da_tela(app)
    app.toggle(key=CHAVE_RESUMO_TEXTO).set_value(True).run()
    assert not app.exception
    resumos = [m.value for m in app.markdown if "Resumo do gráfico" in m.value]
    assert len(resumos) == 4  # um para cada gráfico do dashboard
    assert any("R$ 349,50" in resumo for resumo in resumos)
    assert app.session_state[CHAVE_ALTO_CONTRASTE] is True
