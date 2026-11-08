"""Ponto de entrada da aplicação Streamlit.

Execute a partir da raiz do projeto com:  streamlit run app.py
"""

import streamlit as st

from cgcell.config import NOME_PROJETO

st.set_page_config(page_title=NOME_PROJETO, page_icon="📱", layout="wide")

st.title(NOME_PROJETO)
st.caption(
    "Ferramenta complementar de gestão e análise de dados para a assistência técnica. "
    "Não substitui o sistema de ordens de serviço da empresa."
)

st.info(
    "Etapa 1 concluída: estrutura inicial do projeto. "
    "Cadastros, indicadores e gráficos serão adicionados nas próximas etapas."
)
