"""Testes do MODO DEMONSTRAÇÃO como ele roda na nuvem.

Na nuvem o app recebe só duas variáveis (CGCELL_MODO_DEMO e CGCELL_CAMINHO_BANCO) e o
disco começa vazio: o próprio app precisa gerar os dados SIMULADOS ao abrir.
Tudo aqui usa bancos temporários; o banco principal da aplicação nunca é tocado.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from cgcell import config
from cgcell.dominio import OrigemRegistro
from cgcell.servicos.servico_ordens_servico import listar_ordens_servico
from cgcell.servicos.sessao import abrir_conexao
from scripts import gerar_dados_simulados as gerador

ARQUIVO_APP = Path(__file__).resolve().parents[2] / "app.py"
TEMPO_LIMITE = 60  # a primeira abertura gera ~6 meses de OS simuladas (uns segundos)


@pytest.fixture
def banco_principal_falso(tmp_path, monkeypatch) -> Path:
    """Faz o 'banco principal' apontar para uma pasta temporária durante o teste."""
    falso = tmp_path / "principal" / "cgcell.db"
    monkeypatch.setattr(config, "CAMINHO_BANCO_PADRAO", falso)
    monkeypatch.setattr(gerador, "CAMINHO_BANCO_PADRAO", falso)
    return falso


# --- Função de preparação ---


def test_preparar_gera_dados_quando_banco_nao_existe(tmp_path):
    destino = tmp_path / "pasta_nova" / "demo.db"  # a pasta também ainda não existe

    resumo = gerador.preparar_banco_demonstracao(destino)

    assert resumo is not None and resumo.ordens > 0
    assert destino.exists()
    assert not destino.with_name("demo.db.gerando").exists()
    with abrir_conexao(destino) as conexao:
        ordens = listar_ordens_servico(conexao)
    assert len(ordens) == resumo.ordens
    assert {ordem.origem_registro for ordem in ordens} == {OrigemRegistro.SIMULADO}


def test_preparar_nao_mexe_em_banco_que_ja_existe(tmp_path):
    destino = tmp_path / "demo.db"
    with abrir_conexao(destino):
        pass  # banco existente (vazio)
    conteudo_antes = destino.read_bytes()

    assert gerador.preparar_banco_demonstracao(destino) is None
    assert destino.read_bytes() == conteudo_antes


def test_preparar_recusa_o_banco_principal(banco_principal_falso):
    with pytest.raises(gerador.DestinoProibido):
        gerador.preparar_banco_demonstracao(banco_principal_falso)
    assert not banco_principal_falso.exists()


def test_falha_no_meio_nao_deixa_banco_pela_metade(tmp_path, monkeypatch):
    destino = tmp_path / "demo.db"

    def falhar(*_args, **_kwargs):
        raise RuntimeError("queda simulada")

    monkeypatch.setattr(gerador, "gerar_dados", falhar)
    with pytest.raises(RuntimeError):
        gerador.preparar_banco_demonstracao(destino)
    assert not destino.exists()
    assert not destino.with_name("demo.db.gerando").exists()


# --- App completo, configurado como na nuvem ---


def test_app_na_nuvem_gera_dados_e_abre_o_dashboard(tmp_path, monkeypatch):
    destino = tmp_path / "data" / "demo.db"
    monkeypatch.setenv("CGCELL_MODO_DEMO", "1")
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", str(destino))

    app = AppTest.from_file(str(ARQUIVO_APP), default_timeout=TEMPO_LIMITE).run()

    assert not app.exception
    assert destino.exists()
    assert any("Dashboard gerencial" in cabecalho.value for cabecalho in app.header)
    assert any("MODO DEMONSTRAÇÃO" in aviso.value for aviso in app.warning)
    quantidade = {metrica.label: metrica.value for metrica in app.metric}["Quantidade de OS"]
    assert int(quantidade.replace(".", "")) > 0


def test_app_em_modo_demo_sem_banco_separado_para_com_erro(banco_principal_falso, monkeypatch):
    monkeypatch.setenv("CGCELL_MODO_DEMO", "1")
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", "")  # vazio = banco principal

    app = AppTest.from_file(str(ARQUIVO_APP), default_timeout=TEMPO_LIMITE).run()

    assert not app.exception
    assert any("CGCELL_CAMINHO_BANCO" in erro.value for erro in app.error)
    assert not banco_principal_falso.exists()
