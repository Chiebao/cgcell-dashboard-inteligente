"""Testes de fumaça da configuração (Etapa 1)."""

from pathlib import Path

from cgcell import config


def test_caminho_banco_padrao_quando_variavel_ausente(monkeypatch):
    monkeypatch.delenv("CGCELL_CAMINHO_BANCO", raising=False)
    assert config.obter_caminho_banco() == config.CAMINHO_BANCO_PADRAO


def test_caminho_banco_relativo_resolvido_pela_raiz(monkeypatch):
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", "data/teste.db")
    assert config.obter_caminho_banco() == config.RAIZ_PROJETO / "data" / "teste.db"


def test_caminho_banco_absoluto_mantido(monkeypatch, tmp_path: Path):
    destino = tmp_path / "outro.db"
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", str(destino))
    assert config.obter_caminho_banco() == destino


def test_caminho_banco_vazio_usa_padrao(monkeypatch):
    monkeypatch.setenv("CGCELL_CAMINHO_BANCO", "   ")
    assert config.obter_caminho_banco() == config.CAMINHO_BANCO_PADRAO
