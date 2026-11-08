"""Regras de negócio das ordens de serviço: cadastro, consulta, edição, pagamento e exclusão.

Regras de edição (seção 5 do AGENTS.md):
- aberta ou em andamento: edição livre (com validação);
- concluída com pagamento pendente: só é permitido registrar o pagamento;
- concluída e paga: bloqueada;
- cancelada: bloqueada.

Exclusão: somente lógica e somente para OS com mais de 90 dias desde a abertura.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import date, datetime

from cgcell.dados import repositorio_ordens_servico as repositorio
from cgcell.dados import repositorio_tipos_servico
from cgcell.dominio import (
    DIAS_MINIMOS_PARA_EXCLUSAO,
    DadosOrdemServico,
    OrdemServico,
    OrigemRegistro,
    StatusOS,
    StatusPagamento,
)
from cgcell.servicos.erros import (
    ErroValidacao,
    OperacaoNaoPermitida,
    RegistroNaoEncontrado,
)
from cgcell.servicos.validacoes import validar_dados_ordem_servico


def agora() -> datetime:
    """Momento atual, sem microssegundos. Isolado em função para os testes poderem controlar."""
    return datetime.now().replace(microsecond=0)


def _hoje(hoje: date | None) -> date:
    return hoje if hoje is not None else date.today()


# --- Regras de permissão (funções puras, também úteis para a interface) ---


def motivo_bloqueio_edicao(ordem: OrdemServico) -> str | None:
    """Retorna por que a OS não pode ser editada, ou `None` se a edição é permitida."""
    if ordem.status_os == StatusOS.CANCELADA:
        return "OS cancelada não pode ser editada."
    if ordem.status_os == StatusOS.CONCLUIDA:
        if ordem.status_pagamento == StatusPagamento.PAGO:
            return "OS concluída e paga está finalizada e não pode ser editada."
        return "OS concluída: só é permitido registrar o pagamento."
    return None


def motivo_bloqueio_pagamento(ordem: OrdemServico) -> str | None:
    """Retorna por que não é possível registrar pagamento, ou `None` se é permitido."""
    if ordem.status_os == StatusOS.CANCELADA:
        return "OS cancelada não pode ter pagamento registrado."
    if ordem.status_pagamento == StatusPagamento.PAGO:
        return "O pagamento desta OS já foi registrado."
    return None


def motivo_bloqueio_exclusao(ordem: OrdemServico, hoje: date) -> str | None:
    """Retorna por que a OS não pode ser excluída, ou `None` se a exclusão é permitida."""
    dias = (hoje - ordem.data_abertura).days
    if dias <= DIAS_MINIMOS_PARA_EXCLUSAO:
        return (
            f"A OS só pode ser excluída com mais de {DIAS_MINIMOS_PARA_EXCLUSAO} dias "
            f"desde a abertura (esta tem {dias} dias)."
        )
    return None


# --- Verificações que dependem do banco ---


def _erros_tipo_servico(
    conexao: sqlite3.Connection, id_tipo_servico: int, id_tipo_atual: int | None = None
) -> list[str]:
    """O tipo precisa existir e estar ativo, exceto se for o tipo que a OS já usava."""
    tipo = repositorio_tipos_servico.buscar_por_id(conexao, id_tipo_servico)
    if tipo is None:
        return ["Tipo de serviço não encontrado."]
    if not tipo.ativo and id_tipo_servico != id_tipo_atual:
        return [f"O tipo de serviço '{tipo.nome_servico}' está desativado."]
    return []


def _erros_codigo(
    conexao: sqlite3.Connection, codigo_os: str, ignorar_id: int | None = None
) -> list[str]:
    if repositorio.existe_codigo(conexao, codigo_os, ignorar_id=ignorar_id):
        return [f"Já existe uma OS com o código '{codigo_os}'."]
    return []


def _gravar(conexao: sqlite3.Connection, operacao) -> int | None:
    """Executa a escrita numa transação e traduz violações do banco em erro de validação."""
    try:
        with conexao:
            return operacao()
    except sqlite3.IntegrityError as erro:
        raise ErroValidacao([f"O banco recusou o registro: {erro}"]) from erro


# --- Operações ---


def obter_ordem_servico(conexao: sqlite3.Connection, id_ordem_servico: int) -> OrdemServico:
    """Busca uma OS não excluída."""
    ordem = repositorio.buscar_por_id(conexao, id_ordem_servico)
    if ordem is None:
        raise RegistroNaoEncontrado(f"OS {id_ordem_servico} não encontrada.")
    return ordem


def listar_ordens_servico(conexao: sqlite3.Connection) -> list[OrdemServico]:
    """Lista as OS não excluídas, da abertura mais recente para a mais antiga."""
    return repositorio.listar(conexao)


def cadastrar_ordem_servico(
    conexao: sqlite3.Connection,
    dados: DadosOrdemServico,
    origem_registro: OrigemRegistro = OrigemRegistro.MANUAL,
    hoje: date | None = None,
) -> OrdemServico:
    """Valida e grava uma nova OS."""
    dados = validar_dados_ordem_servico(dados, _hoje(hoje))
    try:
        origem = OrigemRegistro(origem_registro)
    except ValueError as erro:
        raise ErroValidacao(["Origem do registro inválida."]) from erro

    erros = _erros_tipo_servico(conexao, dados.id_tipo_servico)
    erros += _erros_codigo(conexao, dados.codigo_os)
    if erros:
        raise ErroValidacao(erros)

    id_ordem_servico = _gravar(
        conexao, lambda: repositorio.inserir(conexao, dados, origem, agora())
    )
    return obter_ordem_servico(conexao, id_ordem_servico)


def editar_ordem_servico(
    conexao: sqlite3.Connection,
    id_ordem_servico: int,
    novos_dados: DadosOrdemServico,
    hoje: date | None = None,
) -> OrdemServico:
    """Edita uma OS aberta ou em andamento."""
    atual = obter_ordem_servico(conexao, id_ordem_servico)
    motivo = motivo_bloqueio_edicao(atual)
    if motivo:
        raise OperacaoNaoPermitida(motivo)

    dados = validar_dados_ordem_servico(novos_dados, _hoje(hoje))
    erros = _erros_tipo_servico(conexao, dados.id_tipo_servico, atual.id_tipo_servico)
    erros += _erros_codigo(conexao, dados.codigo_os, ignorar_id=id_ordem_servico)
    if erros:
        raise ErroValidacao(erros)

    _gravar(conexao, lambda: repositorio.atualizar(conexao, id_ordem_servico, dados, agora()))
    return obter_ordem_servico(conexao, id_ordem_servico)


def registrar_pagamento(
    conexao: sqlite3.Connection,
    id_ordem_servico: int,
    data_pagamento: date,
    hoje: date | None = None,
) -> OrdemServico:
    """Marca a OS como paga na data informada. Único ajuste aceito em OS concluída."""
    atual = obter_ordem_servico(conexao, id_ordem_servico)
    motivo = motivo_bloqueio_pagamento(atual)
    if motivo:
        raise OperacaoNaoPermitida(motivo)

    dados = replace(
        atual.para_dados(),
        status_pagamento=StatusPagamento.PAGO,
        data_pagamento=data_pagamento,
    )
    dados = validar_dados_ordem_servico(dados, _hoje(hoje))

    _gravar(conexao, lambda: repositorio.atualizar(conexao, id_ordem_servico, dados, agora()))
    return obter_ordem_servico(conexao, id_ordem_servico)


def excluir_ordem_servico(
    conexao: sqlite3.Connection, id_ordem_servico: int, hoje: date | None = None
) -> None:
    """Exclusão lógica. O registro permanece no banco, fora de listagens e indicadores."""
    atual = obter_ordem_servico(conexao, id_ordem_servico)
    motivo = motivo_bloqueio_exclusao(atual, _hoje(hoje))
    if motivo:
        raise OperacaoNaoPermitida(motivo)
    _gravar(conexao, lambda: repositorio.marcar_excluida(conexao, id_ordem_servico, agora()))
