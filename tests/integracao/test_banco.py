"""Testes de integração do banco: conexão, migrações, restrições e backup."""

from __future__ import annotations

import sqlite3

import pytest

from cgcell.dados.conexao import conectar, fazer_backup, inicializar_banco
from cgcell.dados.migracoes import aplicar_migracoes, listar_migracoes, obter_versao_esquema


def _tabelas(conexao: sqlite3.Connection) -> set[str]:
    linhas = conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {linha[0] for linha in linhas}


def _inserir_os_direto(conexao: sqlite3.Connection, id_tipo: int, **campos) -> None:
    """INSERT sem passar pelos serviços, para testar as restrições do próprio banco."""
    valores = {
        "codigo_os": "OS-1",
        "data_abertura": "2026-06-01",
        "data_conclusao": None,
        "valor_servico": 1000,
        "status_os": "aberta",
        "status_pagamento": "pendente",
        "data_pagamento": None,
        "id_tipo_servico": id_tipo,
        "criado_em": "2026-06-01 10:00:00",
        "atualizado_em": "2026-06-01 10:00:00",
    } | campos
    colunas = ", ".join(valores)
    marcadores = ", ".join(f":{coluna}" for coluna in valores)
    conexao.execute(f"INSERT INTO ordem_servico ({colunas}) VALUES ({marcadores})", valores)


def test_conexao_ativa_chaves_estrangeiras(tmp_path):
    conexao = conectar(tmp_path / "x.db")
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conexao.close()


def test_conectar_cria_pasta_do_banco(tmp_path):
    caminho = tmp_path / "subpasta" / "banco.db"
    conectar(caminho).close()
    assert caminho.exists()


def test_migracao_cria_tabelas(conexao):
    assert {"tipo_servico", "ordem_servico", "versao_esquema"} <= _tabelas(conexao)


def test_versao_registrada_igual_a_ultima_migracao(conexao):
    ultima_versao = listar_migracoes()[-1][0]
    assert obter_versao_esquema(conexao) == ultima_versao


def test_migracoes_sao_idempotentes(tmp_path):
    caminho = tmp_path / "banco.db"
    inicializar_banco(caminho).close()
    conexao = inicializar_banco(caminho)
    assert aplicar_migracoes(conexao) == []
    conexao.close()


def test_migracao_com_erro_nao_deixa_nada_gravado(tmp_path):
    pasta = tmp_path / "migracoes"
    pasta.mkdir()
    (pasta / "0001_ok.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    (pasta / "0002_quebrada.sql").write_text(
        "CREATE TABLE b (x INTEGER);\nISTO NAO E SQL;", encoding="utf-8"
    )
    conexao = conectar(tmp_path / "banco.db")
    with pytest.raises(sqlite3.OperationalError):
        aplicar_migracoes(conexao, pasta)
    assert obter_versao_esquema(conexao) == 1
    assert "a" in _tabelas(conexao)
    assert "b" not in _tabelas(conexao)
    conexao.close()


def test_nome_de_migracao_fora_do_padrao_e_rejeitado(tmp_path):
    (tmp_path / "criar_tabela.sql").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="fora do padrão"):
        listar_migracoes(tmp_path)


def test_banco_rejeita_tipo_servico_inexistente(conexao):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        _inserir_os_direto(conexao, id_tipo=999)


def test_banco_impede_apagar_tipo_em_uso(conexao, tipo_tela):
    _inserir_os_direto(conexao, tipo_tela.id_tipo_servico)
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "DELETE FROM tipo_servico WHERE id_tipo_servico = ?", (tipo_tela.id_tipo_servico,)
        )


@pytest.mark.parametrize(
    "campos",
    [
        {"valor_servico": -1},
        {"valor_servico": 10.5},
        {"data_abertura": "2026-02-30"},
        {"data_abertura": "01/06/2026"},
        {"status_os": "finalizada"},
        {"status_pagamento": "pago"},
        {"data_pagamento": "2026-06-02"},
        {"data_conclusao": "2026-06-02"},
        {"status_os": "concluida", "data_conclusao": "2026-05-01"},
        {"status_os": "cancelada", "status_pagamento": "pago", "data_pagamento": "2026-06-02"},
        {"excluida": 1},
        {"origem_registro": "outro"},
    ],
)
def test_banco_rejeita_registro_inconsistente(conexao, tipo_tela, campos):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _inserir_os_direto(conexao, tipo_tela.id_tipo_servico, **campos)


def test_codigo_os_duplicado_rejeitado_sem_diferenciar_maiusculas(conexao, tipo_tela):
    _inserir_os_direto(conexao, tipo_tela.id_tipo_servico, codigo_os="os-1")
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        _inserir_os_direto(conexao, tipo_tela.id_tipo_servico, codigo_os="OS-1")


def test_backup_copia_os_dados(conexao, tipo_tela, tmp_path):
    destino = fazer_backup(conexao, tmp_path / "backups" / "copia.db")
    copia = sqlite3.connect(destino)
    nomes = [linha[0] for linha in copia.execute("SELECT nome_servico FROM tipo_servico")]
    copia.close()
    assert nomes == ["Troca de tela"]
