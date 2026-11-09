"""Página de ordens de serviço: cadastrar, consultar, editar, registrar pagamento e excluir.

As permissões (o que pode ser editado, pago ou excluído) vêm da camada de serviços;
esta página só decide o que mostrar.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from cgcell.apresentacao.componentes import (
    DATA_MINIMA,
    agendar_sucesso,
    aviso_simulado,
    chave_formulario,
    exibir_sucesso_pendente,
    exibir_tabela,
    mostrar_erro,
    renovar_formulario,
)
from cgcell.apresentacao.formatacao import (
    centavos_para_texto,
    converter_texto_para_centavos,
    formatar_data,
    formatar_moeda,
    rotulo_origem,
)
from cgcell.dominio import (
    DadosOrdemServico,
    OrdemServico,
    OrigemRegistro,
    StatusOS,
    StatusPagamento,
    TipoServico,
)
from cgcell.servicos.erros import ErroNegocio, ErroValidacao
from cgcell.servicos.servico_ordens_servico import (
    cadastrar_ordem_servico,
    editar_ordem_servico,
    excluir_ordem_servico,
    listar_ordens_servico,
    motivo_bloqueio_edicao,
    motivo_bloqueio_exclusao,
    motivo_bloqueio_pagamento,
    registrar_pagamento,
)
from cgcell.servicos.servico_tipos_servico import listar_tipos_servico
from cgcell.servicos.sessao import abrir_conexao
from cgcell.servicos.validacoes import TAMANHO_MAXIMO_CODIGO_OS

SECOES = ["➕ Nova OS", "🔎 Consultar", "✏️ Editar, pagar ou excluir"]


@dataclass(frozen=True)
class _CamposFormulario:
    """Valores crus digitados no formulário (o valor ainda é texto)."""

    codigo_os: str
    data_abertura: date | None
    id_tipo_servico: int | None
    valor_texto: str
    status_os: StatusOS
    data_conclusao: date | None
    status_pagamento: StatusPagamento
    data_pagamento: date | None

    def para_dados(self) -> DadosOrdemServico:
        try:
            valor = converter_texto_para_centavos(self.valor_texto)
        except ValueError as erro:
            raise ErroValidacao([str(erro)]) from erro
        return DadosOrdemServico(
            codigo_os=self.codigo_os,
            data_abertura=self.data_abertura,
            valor_servico=valor,
            id_tipo_servico=self.id_tipo_servico,
            status_os=self.status_os,
            status_pagamento=self.status_pagamento,
            data_conclusao=self.data_conclusao,
            data_pagamento=self.data_pagamento,
        )


def renderizar() -> None:
    st.header("🧾 Ordens de serviço")
    exibir_sucesso_pendente()
    secao = st.radio("Seção", SECOES, horizontal=True, label_visibility="collapsed", key="secao_os")

    with abrir_conexao() as conexao:
        tipos = listar_tipos_servico(conexao)
        if secao == SECOES[0]:
            _nova_os(conexao, tipos)
        elif secao == SECOES[1]:
            _consultar(listar_ordens_servico(conexao), tipos)
        else:
            _gerenciar(conexao, listar_ordens_servico(conexao), tipos)


# --- Formulário compartilhado (cadastro e edição) ---


def _campos_os(
    chave: str, opcoes_tipo: dict[int, str], inicial: OrdemServico | None
) -> _CamposFormulario:
    hoje = date.today()
    ids_tipo = list(opcoes_tipo)
    esquerda, direita = st.columns(2)

    codigo = esquerda.text_input(
        "Código da OS *",
        value=inicial.codigo_os if inicial else "",
        max_chars=TAMANHO_MAXIMO_CODIGO_OS,
        placeholder="Ex.: 2026-0001",
        key=f"{chave}_codigo",
    )
    data_abertura = direita.date_input(
        "Data de abertura *",
        value=inicial.data_abertura if inicial else hoje,
        min_value=DATA_MINIMA,
        max_value=hoje,
        format="DD/MM/YYYY",
        key=f"{chave}_abertura",
    )
    id_tipo = esquerda.selectbox(
        "Tipo de serviço *",
        ids_tipo,
        index=ids_tipo.index(inicial.id_tipo_servico) if inicial else 0,
        format_func=opcoes_tipo.get,
        key=f"{chave}_tipo",
    )
    valor_texto = direita.text_input(
        "Valor do serviço (R$) *",
        value=centavos_para_texto(inicial.valor_servico) if inicial else "",
        placeholder="Ex.: 150,00",
        help="Use vírgula para os centavos. Valor 0 é permitido (garantia ou retorno).",
        key=f"{chave}_valor",
    )
    status_os = esquerda.selectbox(
        "Status da OS *",
        list(StatusOS),
        index=list(StatusOS).index(inicial.status_os) if inicial else 0,
        format_func=lambda status: status.rotulo,
        key=f"{chave}_status",
    )
    data_conclusao = direita.date_input(
        "Data de conclusão",
        value=inicial.data_conclusao if inicial else None,
        min_value=DATA_MINIMA,
        max_value=hoje,
        format="DD/MM/YYYY",
        help="Preencha somente quando o status for Concluída.",
        key=f"{chave}_conclusao",
    )
    status_pagamento = esquerda.selectbox(
        "Pagamento *",
        list(StatusPagamento),
        index=list(StatusPagamento).index(inicial.status_pagamento) if inicial else 0,
        format_func=lambda status: status.rotulo,
        key=f"{chave}_pagamento",
    )
    data_pagamento = direita.date_input(
        "Data de pagamento",
        value=inicial.data_pagamento if inicial else None,
        min_value=DATA_MINIMA,
        max_value=hoje,
        format="DD/MM/YYYY",
        help="Obrigatória quando o pagamento é Pago; deixe vazia quando Pendente.",
        key=f"{chave}_data_pagamento",
    )
    return _CamposFormulario(
        codigo_os=codigo,
        data_abertura=data_abertura,
        id_tipo_servico=id_tipo,
        valor_texto=valor_texto,
        status_os=status_os,
        data_conclusao=data_conclusao,
        status_pagamento=status_pagamento,
        data_pagamento=data_pagamento,
    )


# --- Seções ---


def _nova_os(conexao: sqlite3.Connection, tipos: list[TipoServico]) -> None:
    ativos = {tipo.id_tipo_servico: tipo.nome_servico for tipo in tipos if tipo.ativo}
    if not ativos:
        st.warning(
            "Nenhum tipo de serviço ativo. Cadastre um em **Tipos de serviço** (menu ao lado) "
            "antes de registrar OS."
        )
        return

    st.caption("Campos com * são obrigatórios.")
    nome_formulario = "nova_os"
    chave = chave_formulario(nome_formulario)
    with st.form(chave):
        campos = _campos_os(chave, ativos, inicial=None)
        enviado = st.form_submit_button("Cadastrar OS", type="primary")

    if enviado:
        try:
            ordem = cadastrar_ordem_servico(conexao, campos.para_dados())
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            agendar_sucesso(f"OS **{ordem.codigo_os}** cadastrada.")
            renovar_formulario(nome_formulario)
            st.rerun()


def _tabela_ordens(ordens: list[OrdemServico], nomes_tipo: dict[int, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Código": [o.codigo_os for o in ordens],
            "Abertura": [formatar_data(o.data_abertura) for o in ordens],
            "Tipo de serviço": [nomes_tipo.get(o.id_tipo_servico, "?") for o in ordens],
            "Valor": [formatar_moeda(o.valor_servico) for o in ordens],
            "Status": [o.status_os.rotulo for o in ordens],
            "Conclusão": [formatar_data(o.data_conclusao) for o in ordens],
            "Pagamento": [o.status_pagamento.rotulo for o in ordens],
            "Data pagamento": [formatar_data(o.data_pagamento) for o in ordens],
            "Origem": [rotulo_origem(o.origem_registro) for o in ordens],
        }
    )


def _consultar(ordens: list[OrdemServico], tipos: list[TipoServico]) -> None:
    if not ordens:
        st.info("Nenhuma OS cadastrada ainda. Use a seção **Nova OS**.")
        return

    nomes_tipo = {tipo.id_tipo_servico: tipo.nome_servico for tipo in tipos}
    filtro_busca, filtro_status, filtro_origem = st.columns([2, 2, 1])
    busca = filtro_busca.text_input("Buscar pelo código", key="consulta_busca")
    status = filtro_status.multiselect(
        "Status",
        list(StatusOS),
        format_func=lambda s: s.rotulo,
        placeholder="Todos os status",
        key="consulta_status",
    )
    origem = filtro_origem.selectbox(
        "Origem", ["Todas", "Reais", "Simuladas"], key="consulta_origem"
    )

    filtradas = [
        o
        for o in ordens
        if busca.strip().lower() in o.codigo_os.lower()
        and (not status or o.status_os in status)
        and (
            origem == "Todas"
            or (origem == "Simuladas") == (o.origem_registro == OrigemRegistro.SIMULADO)
        )
    ]
    if any(o.origem_registro == OrigemRegistro.SIMULADO for o in filtradas):
        aviso_simulado()
    st.caption(f"{len(filtradas)} de {len(ordens)} OS")
    exibir_tabela(_tabela_ordens(filtradas, nomes_tipo))


def _gerenciar(
    conexao: sqlite3.Connection, ordens: list[OrdemServico], tipos: list[TipoServico]
) -> None:
    if not ordens:
        st.info("Nenhuma OS cadastrada ainda. Use a seção **Nova OS**.")
        return

    nomes_tipo = {tipo.id_tipo_servico: tipo.nome_servico for tipo in tipos}
    por_id = {o.id_ordem_servico: o for o in ordens}
    if st.session_state.get("os_escolhida") not in por_id:
        st.session_state.pop("os_escolhida", None)

    id_escolhido = st.selectbox(
        "Escolha a OS (digite para buscar)",
        list(por_id),
        format_func=lambda i: (
            f"{por_id[i].codigo_os} · aberta em {formatar_data(por_id[i].data_abertura)} · "
            f"{nomes_tipo.get(por_id[i].id_tipo_servico, '?')}"
        ),
        key="os_escolhida",
    )
    ordem = por_id[id_escolhido]

    if ordem.origem_registro == OrigemRegistro.SIMULADO:
        aviso_simulado()
    exibir_tabela(_tabela_ordens([ordem], nomes_tipo))

    _secao_editar(conexao, ordem, tipos)
    _secao_pagamento(conexao, ordem)
    _secao_excluir(conexao, ordem)


def _secao_editar(
    conexao: sqlite3.Connection, ordem: OrdemServico, tipos: list[TipoServico]
) -> None:
    st.subheader("Editar")
    motivo = motivo_bloqueio_edicao(ordem)
    if motivo:
        st.info(f"🔒 {motivo}")
        return

    # Tipos ativos + o tipo atual da OS (mesmo que tenha sido desativado depois).
    opcoes = {
        tipo.id_tipo_servico: tipo.nome_servico + ("" if tipo.ativo else " (desativado)")
        for tipo in tipos
        if tipo.ativo or tipo.id_tipo_servico == ordem.id_tipo_servico
    }
    nome_formulario = f"editar_{ordem.id_ordem_servico}"
    chave = chave_formulario(nome_formulario)
    with st.form(chave):
        campos = _campos_os(chave, opcoes, inicial=ordem)
        enviado = st.form_submit_button("Salvar alterações", type="primary")

    if enviado:
        try:
            editada = editar_ordem_servico(conexao, ordem.id_ordem_servico, campos.para_dados())
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            agendar_sucesso(f"OS **{editada.codigo_os}** atualizada.")
            renovar_formulario(nome_formulario)
            st.rerun()


def _secao_pagamento(conexao: sqlite3.Connection, ordem: OrdemServico) -> None:
    if motivo_bloqueio_pagamento(ordem):
        return
    st.subheader("Registrar pagamento")
    hoje = date.today()
    with st.form(f"pagar_{ordem.id_ordem_servico}"):
        data_pagamento = st.date_input(
            "Data do pagamento",
            value=hoje,
            min_value=ordem.data_abertura,
            max_value=hoje,
            format="DD/MM/YYYY",
        )
        enviado = st.form_submit_button("Registrar pagamento")

    if enviado:
        try:
            registrar_pagamento(conexao, ordem.id_ordem_servico, data_pagamento)
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            agendar_sucesso(
                f"Pagamento da OS **{ordem.codigo_os}** registrado em "
                f"{formatar_data(data_pagamento)}."
            )
            st.rerun()


def _secao_excluir(conexao: sqlite3.Connection, ordem: OrdemServico) -> None:
    st.subheader("Excluir")
    motivo = motivo_bloqueio_exclusao(ordem, date.today())
    if motivo:
        st.caption(f"🔒 {motivo}")
        return

    st.caption(
        "A exclusão é lógica: a OS sai das listagens e dos indicadores, "
        "mas o registro continua guardado no banco."
    )
    confirmar = st.checkbox(
        f"Confirmo que quero excluir a OS {ordem.codigo_os}",
        key=f"confirmar_exclusao_{ordem.id_ordem_servico}",
    )
    if st.button("Excluir OS", disabled=not confirmar, key=f"excluir_{ordem.id_ordem_servico}"):
        try:
            excluir_ordem_servico(conexao, ordem.id_ordem_servico)
        except ErroNegocio as erro:
            mostrar_erro(erro)
        else:
            agendar_sucesso(f"OS **{ordem.codigo_os}** excluída.")
            st.rerun()
