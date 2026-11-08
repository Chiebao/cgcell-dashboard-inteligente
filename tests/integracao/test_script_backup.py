"""Teste do script de backup, sempre com banco e pasta temporários."""

from __future__ import annotations

import sqlite3

from cgcell.dados.conexao import inicializar_banco
from cgcell.servicos.servico_tipos_servico import cadastrar_tipo_servico
from scripts import backup_banco


def test_script_cria_backup(tmp_path, monkeypatch):
    banco = tmp_path / "app.db"
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", str(banco))
    conexao = inicializar_banco(banco)
    cadastrar_tipo_servico(conexao, "Troca de tela")
    conexao.close()

    assert backup_banco.main(pasta_destino=tmp_path / "backups") == 0

    copias = list((tmp_path / "backups").glob("cgcell_*.db"))
    assert len(copias) == 1
    copia = sqlite3.connect(copias[0])
    assert copia.execute("SELECT COUNT(*) FROM tipo_servico").fetchone()[0] == 1
    copia.close()


def test_script_sem_banco_retorna_erro(tmp_path, monkeypatch):
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", str(tmp_path / "inexistente.db"))
    assert backup_banco.main(pasta_destino=tmp_path / "backups") == 1
    assert not (tmp_path / "backups").exists()
