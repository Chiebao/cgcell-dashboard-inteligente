"""Componentes reutilizados pelas páginas: mensagens, avisos, formulários, gráficos e tabelas."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cgcell.apresentacao.acessibilidade import ajustar_grafico, obter_preferencias
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


# --- Exibição acessível (respeita as preferências do painel de acessibilidade) ---


def exibir_grafico(figura: go.Figure, resumo: str | None = None, area=st) -> None:
    """Mostra o gráfico ajustado às preferências e, se ligado, o resumo em texto abaixo dele."""
    preferencias = obter_preferencias()
    area.plotly_chart(
        ajustar_grafico(figura, preferencias),
        # No alto contraste o tema do Streamlit é desligado para não sobrepor as cores escolhidas.
        theme=None if preferencias.alto_contraste else "streamlit",
    )
    if resumo and preferencias.resumo_texto:
        area.markdown(f"📝 **Resumo do gráfico:** {resumo}")


def exibir_tabela(tabela: pd.DataFrame, area=st) -> None:
    """Tabela interativa no modo padrão; tabela HTML no alto contraste ou com fonte ampliada.

    A tabela interativa do Streamlit é desenhada como imagem (canvas) e não segue CSS nem
    leitores de tela; a tabela HTML segue as duas coisas.
    """
    if obter_preferencias().usa_tabela_html:
        area.table(tabela, hide_index=True)
    else:
        area.dataframe(tabela, hide_index=True)
