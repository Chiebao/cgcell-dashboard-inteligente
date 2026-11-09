"""Gera uma base de dados SIMULADA e reproduzível, para demonstração do software.

Uso (na raiz do projeto, com o ambiente virtual ativado):

    python -m scripts.gerar_dados_simulados             # cria data/demo.db (se estiver vazio)
    python -m scripts.gerar_dados_simulados --recriar   # apaga e recria data/demo.db do zero
    python -m scripts.gerar_dados_simulados --semente 7 --meses 3

Regras:
- todos os registros são gravados com origem_registro = simulado;
- os dados passam pela camada de serviços (mesmas validações do app), nunca por SQL solto;
- o script RECUSA gravar no banco principal (data/cgcell.db);
- mesma semente + mesmo dia de execução = exatamente os mesmos dados.

Os dados são fictícios: valores, volumes e proporções foram escolhidos para parecer
plausíveis, NÃO representam a operação real da CG CELL Repair.
"""

from __future__ import annotations

import argparse
import calendar
import os
import random
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from cgcell.config import CAMINHO_BANCO_PADRAO, RAIZ_PROJETO
from cgcell.dominio import DadosOrdemServico, OrigemRegistro, StatusOS, StatusPagamento
from cgcell.servicos.servico_ordens_servico import (
    cadastrar_ordem_servico,
    listar_ordens_servico,
)
from cgcell.servicos.servico_tipos_servico import cadastrar_tipo_servico
from cgcell.servicos.sessao import abrir_conexao

CAMINHO_DEMO = RAIZ_PROJETO / "data" / "demo.db"
SEMENTE_PADRAO = 2026
MESES_PADRAO = 6
OS_POR_DIA_UTIL = (3, 8)
PROBABILIDADE_GARANTIA = 0.02  # OS de valor zero (garantia ou retorno)


@dataclass(frozen=True)
class PerfilServico:
    """Tipo de serviço simulado: peso na demanda e faixa de preço (em reais)."""

    nome: str
    peso: int
    valor_minimo_reais: int
    valor_maximo_reais: int


PERFIS = (
    PerfilServico("Troca de tela", 35, 250, 900),
    PerfilServico("Troca de bateria", 25, 120, 300),
    PerfilServico("Conector de carga", 15, 80, 200),
    PerfilServico("Software e formatação", 15, 50, 150),
    PerfilServico("Limpeza e oxidação", 10, 100, 350),
)
DESCRICAO_TIPO = "Tipo criado pelo gerador de dados SIMULADOS (demonstração)."


@dataclass
class ResumoGeracao:
    tipos: int
    ordens: int
    inicio: date
    fim: date
    por_status: Counter = field(default_factory=Counter)
    pagas: int = 0


class DestinoProibido(Exception):
    """O destino é o banco principal da aplicação."""


# --- Regras de segurança ---


def eh_banco_principal(destino: Path) -> bool:
    """Compara caminhos já resolvidos (no Windows, sem diferenciar maiúsculas)."""
    return os.path.normcase(str(Path(destino).resolve())) == os.path.normcase(
        str(CAMINHO_BANCO_PADRAO.resolve())
    )


def resolver_destino(destino: Path | str) -> Path:
    caminho = Path(destino)
    caminho = caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho
    if eh_banco_principal(caminho):
        raise DestinoProibido(
            f"Recusado: {caminho} é o banco PRINCIPAL. Dados simulados só podem ir para um "
            "banco separado (padrão: data/demo.db)."
        )
    return caminho


# --- Calendário ---


def subtrair_meses(dia: date, meses: int) -> date:
    """Mesmo dia, `meses` antes (ajustado para o último dia do mês, se preciso)."""
    mes, ano = dia.month - meses, dia.year
    while mes <= 0:
        mes += 12
        ano -= 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def dias_uteis(inicio: date, fim: date) -> list[date]:
    """Segunda a sexta, de `inicio` a `fim` (inclusive)."""
    total = (fim - inicio).days + 1
    dias = (inicio + timedelta(days=i) for i in range(total))
    return [dia for dia in dias if dia.weekday() < 5]


# --- Geração ---


def _sortear_status(rng: random.Random, idade_dias: int) -> StatusOS:
    """OS recentes tendem a estar abertas ou em andamento; antigas, concluídas."""
    if idade_dias <= 2:
        pesos = {StatusOS.ABERTA: 45, StatusOS.EM_ANDAMENTO: 40, StatusOS.CONCLUIDA: 15}
    elif idade_dias <= 10:
        pesos = {
            StatusOS.ABERTA: 5,
            StatusOS.EM_ANDAMENTO: 25,
            StatusOS.CONCLUIDA: 65,
            StatusOS.CANCELADA: 5,
        }
    else:
        pesos = {StatusOS.EM_ANDAMENTO: 2, StatusOS.CONCLUIDA: 92, StatusOS.CANCELADA: 6}
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def montar_ordem(
    rng: random.Random,
    dia: date,
    sequencia: int,
    id_tipo_servico: int,
    perfil: PerfilServico,
    hoje: date,
) -> DadosOrdemServico:
    idade = (hoje - dia).days
    status = _sortear_status(rng, idade)

    if rng.random() < PROBABILIDADE_GARANTIA:
        valor = 0
    else:
        valor = rng.randrange(perfil.valor_minimo_reais, perfil.valor_maximo_reais + 1, 10) * 100

    data_conclusao = data_pagamento = None
    status_pagamento = StatusPagamento.PENDENTE
    if status == StatusOS.CONCLUIDA:
        data_conclusao = min(dia + timedelta(days=rng.randint(0, 3)), hoje)
        probabilidade_pago = 0.9 if idade > 10 else 0.6
        if rng.random() < probabilidade_pago:
            atraso = rng.choice([0, 0, 0, 1, 2])
            data_pagamento = min(data_conclusao + timedelta(days=atraso), hoje)
            status_pagamento = StatusPagamento.PAGO

    return DadosOrdemServico(
        codigo_os=f"SIM-{dia:%Y%m%d}-{sequencia:02d}",
        data_abertura=dia,
        valor_servico=valor,
        id_tipo_servico=id_tipo_servico,
        status_os=status,
        status_pagamento=status_pagamento,
        data_conclusao=data_conclusao,
        data_pagamento=data_pagamento,
    )


def gerar_dados(
    conexao: sqlite3.Connection,
    semente: int = SEMENTE_PADRAO,
    hoje: date | None = None,
    meses: int = MESES_PADRAO,
) -> ResumoGeracao:
    """Cadastra os tipos e as OS simuladas pela camada de serviços."""
    hoje = hoje or date.today()
    rng = random.Random(semente)
    inicio = subtrair_meses(hoje, meses)

    tipos = [
        (perfil, cadastrar_tipo_servico(conexao, perfil.nome, DESCRICAO_TIPO)) for perfil in PERFIS
    ]
    pesos = [perfil.peso for perfil, _ in tipos]
    resumo = ResumoGeracao(tipos=len(tipos), ordens=0, inicio=inicio, fim=hoje)

    for dia in dias_uteis(inicio, hoje):
        for sequencia in range(1, rng.randint(*OS_POR_DIA_UTIL) + 1):
            perfil, tipo = rng.choices(tipos, weights=pesos)[0]
            dados = montar_ordem(rng, dia, sequencia, tipo.id_tipo_servico, perfil, hoje)
            ordem = cadastrar_ordem_servico(
                conexao, dados, origem_registro=OrigemRegistro.SIMULADO, hoje=hoje
            )
            resumo.ordens += 1
            resumo.por_status[ordem.status_os.rotulo] += 1
            resumo.pagas += ordem.status_pagamento == StatusPagamento.PAGO
    return resumo


# --- Linha de comando ---


def _apagar_banco(caminho: Path) -> None:
    for arquivo in (caminho, *(Path(f"{caminho}{s}") for s in ("-wal", "-shm", "-journal"))):
        arquivo.unlink(missing_ok=True)


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(description="Gera dados SIMULADOS para demonstração.")
    leitor.add_argument("--destino", default=str(CAMINHO_DEMO), help="Padrão: data/demo.db")
    leitor.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    leitor.add_argument("--meses", type=int, default=MESES_PADRAO)
    leitor.add_argument(
        "--recriar", action="store_true", help="Apaga o banco de destino e gera do zero."
    )
    opcoes = leitor.parse_args(argumentos)

    try:
        destino = resolver_destino(opcoes.destino)
    except DestinoProibido as erro:
        print(f"ERRO: {erro}")
        return 2

    if destino.exists():
        if opcoes.recriar:
            try:
                _apagar_banco(destino)
            except PermissionError:
                print("ERRO: o banco de demonstração está em uso. Feche o app e tente de novo.")
                return 1
        else:
            with abrir_conexao(destino) as conexao:
                if listar_ordens_servico(conexao):
                    print(f"O banco {destino} já tem dados.")
                    print("Use --recriar para apagar e gerar de novo.")
                    return 1

    print(f"Gerando dados SIMULADOS em {destino} (semente {opcoes.semente})...")
    with abrir_conexao(destino) as conexao:
        resumo = gerar_dados(conexao, semente=opcoes.semente, meses=opcoes.meses)

    print("Concluído. Todos os registros têm origem SIMULADO.")
    print(f"  Período: {resumo.inicio:%d/%m/%Y} a {resumo.fim:%d/%m/%Y} (dias úteis)")
    print(f"  Tipos de serviço criados: {resumo.tipos}")
    print(f"  OS criadas: {resumo.ordens} (pagas: {resumo.pagas})")
    for status, quantidade in sorted(resumo.por_status.items()):
        print(f"    {status}: {quantidade}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
