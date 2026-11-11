"""Ponto de entrada da aplicação Streamlit.

Execute a partir da raiz do projeto com:  streamlit run app.py
Este arquivo só monta o menu; cada página fica em cgcell/apresentacao/.
"""

import streamlit as st

from cgcell.apresentacao import (
    acessibilidade,
    pagina_dashboard,
    pagina_exploracao,
    pagina_ordens_servico,
    pagina_tipos_servico,
)
from cgcell.config import NOME_PROJETO, modo_demonstracao

st.set_page_config(page_title=NOME_PROJETO, page_icon="📱", layout="wide")

navegacao = st.navigation(
    {
        "Gestão": [
            st.Page(pagina_dashboard.renderizar, title="Dashboard", icon="📊", default=True),
            st.Page(
                pagina_exploracao.renderizar,
                title="Exploração dos dados",
                icon="🔎",
                url_path="exploracao-dos-dados",
            ),
        ],
        "Cadastros": [
            st.Page(
                pagina_ordens_servico.renderizar,
                title="Ordens de serviço",
                icon="🧾",
                url_path="ordens-de-servico",
            ),
            st.Page(
                pagina_tipos_servico.renderizar,
                title="Tipos de serviço",
                icon="🛠️",
                url_path="tipos-de-servico",
            ),
        ],
    }
)

with st.sidebar:
    st.markdown(f"**{NOME_PROJETO}**")
    st.caption(
        "Ferramenta complementar de gestão e análise de dados. "
        "Não substitui o sistema de ordens de serviço da empresa."
    )

if modo_demonstracao():
    st.sidebar.warning("🧪 **MODO DEMONSTRAÇÃO**\n\nBanco separado, só com dados SIMULADOS.")
    st.warning(
        "🧪 **MODO DEMONSTRAÇÃO** — todos os dados desta tela são **SIMULADOS** "
        "(gerados para demonstração técnica) e não representam a operação real da empresa."
    )

# Painel de acessibilidade em todas as páginas; as escolhas ficam na sessão (st.session_state).
with st.sidebar:
    st.divider()
    preferencias = acessibilidade.renderizar_painel()
acessibilidade.aplicar_estilo(preferencias)

navegacao.run()
