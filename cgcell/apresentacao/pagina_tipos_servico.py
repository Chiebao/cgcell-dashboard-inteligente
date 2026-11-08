"""Página de tipos de serviço: cadastrar, consultar, ativar e desativar."""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from cgcell.apresentacao.componentes import (
    agendar_sucesso,
    chave_formulario,
    exibir_sucesso_pendente,
    mostrar_erro,
    renovar_formulario,
)
from cgcell.dominio import TipoServico
from cgcell.servicos.erros import ErroNegocio
from cgcell.servicos.servico_tipos_servico import (
    TAMANHO_MAXIMO_DESCRICAO,
    TAMANHO_MAXIMO_NOME,
    ativar_tipo_servico,
    cadastrar_tipo_servico,
    desativar_tipo_servico,
    listar_tipos_servico,
)
from cgcell.servicos.sessao import abrir_conexao


def renderizar() -> None:
    st.header("🛠️ Tipos de serviço")
    st.caption("Os serviços que a assistência oferece. Cada OS é associada a um tipo.")
    exibir_sucesso_pendente()

    with abrir_conexao() as conexao:
        _formulario_cadastro(conexao)
        tipos = listar_tipos_servico(conexao)
        st.divider()
        _tabela(tipos)
        if tipos:
            st.divider()
            _ativar_desativar(conexao, tipos)


def _formulario_cadastro(conexao: sqlite3.Connection) -> None:
    st.subheader("Cadastrar novo tipo")
    with st.form(chave_formulario("novo_tipo")):
        nome = st.text_input(
            "Nome do serviço *", max_chars=TAMANHO_MAXIMO_NOME, placeholder="Ex.: Troca de tela"
        )
        descricao = st.text_area(
            "Descrição (opcional)", max_chars=TAMANHO_MAXIMO_DESCRICAO, height=80
        )
        enviado = st.form_submit_button("Cadastrar", type="primary")

    if enviado:
        try:
            tipo = cadastrar_tipo_servico(conexao, nome, descricao)
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            agendar_sucesso(f"Tipo de serviço **{tipo.nome_servico}** cadastrado.")
            renovar_formulario("novo_tipo")
            st.rerun()


def _tabela(tipos: list[TipoServico]) -> None:
    st.subheader("Tipos cadastrados")
    if not tipos:
        st.info("Nenhum tipo de serviço cadastrado ainda. Use o formulário acima.")
        return
    tabela = pd.DataFrame(
        {
            "Serviço": [tipo.nome_servico for tipo in tipos],
            "Descrição": [tipo.descricao or "—" for tipo in tipos],
            "Situação": ["✅ Ativo" if tipo.ativo else "⛔ Desativado" for tipo in tipos],
        }
    )
    st.dataframe(tabela, hide_index=True)


def _ativar_desativar(conexao: sqlite3.Connection, tipos: list[TipoServico]) -> None:
    st.subheader("Ativar ou desativar")
    st.caption(
        "Um tipo desativado não aparece no cadastro de novas OS, "
        "mas continua válido nas OS antigas."
    )
    por_id = {tipo.id_tipo_servico: tipo for tipo in tipos}
    id_escolhido = st.selectbox(
        "Tipo de serviço",
        list(por_id),
        format_func=lambda id_tipo: (
            f"{por_id[id_tipo].nome_servico} ({'ativo' if por_id[id_tipo].ativo else 'desativado'})"
        ),
        key="tipo_para_alterar",
    )
    escolhido = por_id[id_escolhido]
    rotulo = "Desativar" if escolhido.ativo else "Ativar"
    if st.button(rotulo, key="alterar_situacao_tipo"):
        try:
            if escolhido.ativo:
                desativar_tipo_servico(conexao, escolhido.id_tipo_servico)
            else:
                ativar_tipo_servico(conexao, escolhido.id_tipo_servico)
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            situacao = "desativado" if escolhido.ativo else "ativado"
            agendar_sucesso(f"Tipo **{escolhido.nome_servico}** {situacao}.")
            st.rerun()
