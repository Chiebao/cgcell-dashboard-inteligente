"""Regras de negócio dos tipos de serviço: cadastrar, consultar, ativar e desativar."""

from __future__ import annotations

import sqlite3

from cgcell.dados import repositorio_tipos_servico as repositorio
from cgcell.dominio import TipoServico
from cgcell.servicos.erros import ErroValidacao, RegistroNaoEncontrado
from cgcell.servicos.validacoes import normalizar_texto

TAMANHO_MAXIMO_NOME = 80
TAMANHO_MAXIMO_DESCRICAO = 300


def cadastrar_tipo_servico(
    conexao: sqlite3.Connection, nome_servico: str, descricao: str | None = None
) -> TipoServico:
    """Cadastra um tipo de serviço ativo. O nome é único, sem diferenciar maiúsculas."""
    nome = normalizar_texto(nome_servico)
    texto_descricao = normalizar_texto(descricao) or None

    erros: list[str] = []
    if not nome:
        erros.append("Informe o nome do serviço.")
    elif len(nome) > TAMANHO_MAXIMO_NOME:
        erros.append(f"O nome do serviço deve ter no máximo {TAMANHO_MAXIMO_NOME} caracteres.")
    elif repositorio.buscar_por_nome(conexao, nome) is not None:
        erros.append(f"Já existe um tipo de serviço chamado '{nome}'.")
    if texto_descricao and len(texto_descricao) > TAMANHO_MAXIMO_DESCRICAO:
        erros.append(f"A descrição deve ter no máximo {TAMANHO_MAXIMO_DESCRICAO} caracteres.")
    if erros:
        raise ErroValidacao(erros)

    with conexao:
        id_tipo_servico = repositorio.inserir(conexao, nome, texto_descricao)
    return obter_tipo_servico(conexao, id_tipo_servico)


def obter_tipo_servico(conexao: sqlite3.Connection, id_tipo_servico: int) -> TipoServico:
    tipo = repositorio.buscar_por_id(conexao, id_tipo_servico)
    if tipo is None:
        raise RegistroNaoEncontrado(f"Tipo de serviço {id_tipo_servico} não encontrado.")
    return tipo


def listar_tipos_servico(
    conexao: sqlite3.Connection, somente_ativos: bool = False
) -> list[TipoServico]:
    """Lista em ordem alfabética. Use `somente_ativos=True` no cadastro de novas OS."""
    return repositorio.listar(conexao, somente_ativos=somente_ativos)


def ativar_tipo_servico(conexao: sqlite3.Connection, id_tipo_servico: int) -> TipoServico:
    return _alterar_ativo(conexao, id_tipo_servico, ativo=True)


def desativar_tipo_servico(conexao: sqlite3.Connection, id_tipo_servico: int) -> TipoServico:
    """Tipo desativado some do cadastro de novas OS, mas continua válido nas OS antigas."""
    return _alterar_ativo(conexao, id_tipo_servico, ativo=False)


def _alterar_ativo(conexao: sqlite3.Connection, id_tipo_servico: int, ativo: bool) -> TipoServico:
    obter_tipo_servico(conexao, id_tipo_servico)
    with conexao:
        repositorio.atualizar_ativo(conexao, id_tipo_servico, ativo)
    return obter_tipo_servico(conexao, id_tipo_servico)
