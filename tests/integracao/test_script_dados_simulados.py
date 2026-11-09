"""Testes do gerador de dados simulados. Sempre em bancos temporários."""

from __future__ import annotations

from collections import Counter
from datetime import date

import pytest

from cgcell.config import CAMINHO_BANCO_PADRAO
from cgcell.dados import repositorio_ordens_servico
from cgcell.dominio import OrigemRegistro, StatusOS, StatusPagamento
from cgcell.servicos.servico_dados import executar_pipeline_do_banco
from cgcell.servicos.servico_ordens_servico import listar_ordens_servico
from cgcell.servicos.servico_tipos_servico import listar_tipos_servico
from cgcell.servicos.sessao import abrir_conexao
from scripts import gerar_dados_simulados as gerador

HOJE = date(2026, 6, 15)  # segunda-feira
MESES = 1  # período curto para os testes serem rápidos


def gerar_em(caminho, semente: int = 7):
    with abrir_conexao(caminho) as conexao:
        resumo = gerador.gerar_dados(conexao, semente=semente, hoje=HOJE, meses=MESES)
        registros = repositorio_ordens_servico.listar_para_analise(conexao)
    return resumo, registros


@pytest.fixture(scope="module")
def base_gerada(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("simulado") / "demo.db"
    resumo, registros = gerar_em(caminho)
    return caminho, resumo, registros


# --- Reprodutibilidade ---


def test_mesma_semente_gera_os_mesmos_dados(tmp_path, base_gerada):
    _, _, registros_originais = base_gerada
    _, registros = gerar_em(tmp_path / "outro.db")
    assert registros == registros_originais


def test_semente_diferente_gera_dados_diferentes(tmp_path, base_gerada):
    _, _, registros_originais = base_gerada
    _, registros = gerar_em(tmp_path / "outro.db", semente=8)
    assert registros != registros_originais


# --- Conteúdo ---


def test_todos_os_registros_sao_simulados(base_gerada):
    caminho, _, _ = base_gerada
    with abrir_conexao(caminho) as conexao:
        ordens = listar_ordens_servico(conexao)
    assert ordens
    assert {ordem.origem_registro for ordem in ordens} == {OrigemRegistro.SIMULADO}
    assert all(ordem.codigo_os.startswith("SIM-") for ordem in ordens)


def test_nenhuma_regra_de_consistencia_violada(base_gerada):
    caminho, resumo, _ = base_gerada
    with abrir_conexao(caminho) as conexao:
        resultado = executar_pipeline_do_banco(conexao)
    assert resultado.rejeitados.empty
    assert resultado.duplicados_removidos == 0
    assert len(resultado.base) == resumo.ordens


def test_cinco_tipos_de_servico(base_gerada):
    caminho, resumo, _ = base_gerada
    with abrir_conexao(caminho) as conexao:
        nomes = {tipo.nome_servico for tipo in listar_tipos_servico(conexao)}
    assert resumo.tipos == 5
    assert nomes == {perfil.nome for perfil in gerador.PERFIS}


def test_entre_3_e_8_os_por_dia_util_sem_fim_de_semana(base_gerada):
    _, resumo, registros = base_gerada
    por_dia = Counter(registro["data_abertura"] for registro in registros)
    assert all(date.fromisoformat(dia).weekday() < 5 for dia in por_dia)
    assert all(3 <= quantidade <= 8 for quantidade in por_dia.values())
    assert set(por_dia) == {dia.isoformat() for dia in gerador.dias_uteis(resumo.inicio, HOJE)}


def test_datas_dentro_do_periodo(base_gerada):
    _, resumo, registros = base_gerada
    assert resumo.inicio == date(2026, 5, 15)
    for registro in registros:
        for coluna in ("data_abertura", "data_conclusao", "data_pagamento"):
            if registro[coluna]:
                assert resumo.inicio <= date.fromisoformat(registro[coluna]) <= HOJE


def test_mistura_realista_de_status(base_gerada):
    caminho, resumo, _ = base_gerada
    with abrir_conexao(caminho) as conexao:
        ordens = listar_ordens_servico(conexao)
    concluidas_pagas = [
        o
        for o in ordens
        if o.status_os == StatusOS.CONCLUIDA and o.status_pagamento == StatusPagamento.PAGO
    ]
    concluidas_pendentes = [
        o
        for o in ordens
        if o.status_os == StatusOS.CONCLUIDA and o.status_pagamento == StatusPagamento.PENDENTE
    ]
    status = {o.status_os for o in ordens}
    assert len(concluidas_pagas) > len(ordens) / 2  # a maioria é concluída e paga
    assert concluidas_pendentes
    assert {StatusOS.EM_ANDAMENTO, StatusOS.CANCELADA} <= status
    assert sum(resumo.por_status.values()) == resumo.ordens


def test_valores_dentro_da_faixa_de_cada_tipo(base_gerada):
    _, _, registros = base_gerada
    faixas = {
        p.nome: (p.valor_minimo_reais * 100, p.valor_maximo_reais * 100) for p in gerador.PERFIS
    }
    for registro in registros:
        minimo, maximo = faixas[registro["nome_servico"]]
        valor = registro["valor_servico"]
        assert valor == 0 or minimo <= valor <= maximo


# --- Segurança e linha de comando ---


def test_recusa_gravar_no_banco_principal(capsys):
    assert gerador.main(["--destino", str(CAMINHO_BANCO_PADRAO)]) == 2
    assert "Recusado" in capsys.readouterr().out


def test_recusa_banco_principal_mesmo_com_caminho_relativo():
    with pytest.raises(gerador.DestinoProibido):
        gerador.resolver_destino("data/cgcell.db")
    with pytest.raises(gerador.DestinoProibido):
        gerador.resolver_destino("data/../data/CGCELL.db")


def test_linha_de_comando_gera_e_nao_duplica_sem_recriar(tmp_path, capsys):
    destino = tmp_path / "demo.db"
    assert gerador.main(["--destino", str(destino), "--meses", "1"]) == 0
    saida = capsys.readouterr().out
    assert "Tipos de serviço criados: 5" in saida
    assert "OS criadas:" in saida

    assert gerador.main(["--destino", str(destino), "--meses", "1"]) == 1
    assert "--recriar" in capsys.readouterr().out


def test_recriar_apaga_e_gera_de_novo(tmp_path):
    destino = tmp_path / "demo.db"
    assert gerador.main(["--destino", str(destino), "--meses", "1"]) == 0
    with abrir_conexao(destino) as conexao:
        quantidade = len(listar_ordens_servico(conexao))

    assert gerador.main(["--destino", str(destino), "--meses", "1", "--recriar"]) == 0
    with abrir_conexao(destino) as conexao:
        assert len(listar_ordens_servico(conexao)) == quantidade
        assert len(listar_tipos_servico(conexao)) == 5


def test_subtrair_meses_ajusta_fim_de_mes():
    assert gerador.subtrair_meses(date(2026, 8, 31), 6) == date(2026, 2, 28)
    assert gerador.subtrair_meses(date(2026, 3, 15), 6) == date(2025, 9, 15)
