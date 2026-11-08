"""Ponto de entrada da aplicação Streamlit.

Execute a partir da raiz do projeto com:  streamlit run app.py
"""

import streamlit as st

from cgcell.config import NOME_PROJETO
from cgcell.servicos.sessao import abrir_conexao, obter_versao_banco

st.set_page_config(page_title=NOME_PROJETO, page_icon="📱", layout="wide")

st.title(NOME_PROJETO)
st.caption(
    "Ferramenta complementar de gestão e análise de dados para a assistência técnica. "
    "Não substitui o sistema de ordens de serviço da empresa."
)

with abrir_conexao() as conexao:
    versao_banco = obter_versao_banco(conexao)

st.info(
    "Etapa 2 concluída: banco de dados e regras de negócio prontos. "
    "As telas de cadastro e o dashboard chegam na Etapa 3."
)
st.caption(f"Banco de dados conectado · esquema versão {versao_banco}")
