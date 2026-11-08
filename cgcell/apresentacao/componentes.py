"""Componentes reutilizados pelas páginas: mensagens, avisos e controle de formulários."""

from __future__ import annotations

from datetime import date

import streamlit as st

from cgcell.servicos.erros import ErroNegocio, ErroValidacao

DATA_MINIMA = date(2000, 1, 1)
"""Data mais antiga aceita nos campos de data da interface."""

_CHAVE_MENSAGEM = "_mensagem_sucesso"


def mostrar_erro(erro: ErroNegocio) -> None:
    """Mostra o erro de negócio de forma amigável (lista quando houver vários itens)."""
    if isinstance(erro, ErroValidacao) and len(erro.erros) > 1:
        itens = "\n".join(f"- {mensagem}" for mensagem in erro.erros)
        st.error(f"Corrija os itens abaixo:\n\n{itens}")
    elif isinstance(erro, ErroValidacao):
        st.error(erro.erros[0])
    else:
        st.error(str(erro))


def agendar_sucesso(mensagem: str) -> None:
    """Guarda uma mensagem para exibir depois do `st.rerun()`."""
    st.session_state[_CHAVE_MENSAGEM] = mensagem


def exibir_sucesso_pendente() -> None:
    mensagem = st.session_state.pop(_CHAVE_MENSAGEM, None)
    if mensagem:
        st.success(mensagem)


def chave_formulario(nome: str) -> str:
    """Chave do formulário. Muda depois de cada envio bem-sucedido, o que limpa os campos."""
    return f"{nome}_{st.session_state.get(f'_versao_{nome}', 0)}"


def renovar_formulario(nome: str) -> None:
    st.session_state[f"_versao_{nome}"] = st.session_state.get(f"_versao_{nome}", 0) + 1


def aviso_simulado() -> None:
    st.warning(
        "⚠️ **Dados SIMULADOS incluídos.** Parte dos registros exibidos foi gerada para "
        "demonstração técnica e **não representa a operação real** da empresa."
    )
