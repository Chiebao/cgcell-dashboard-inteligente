"""Validações e regras de consistência das ordens de serviço.

Funções puras (sem banco): recebem dados e devolvem mensagens de erro em português,
prontas para exibição. As mesmas regras também existem como CHECK no banco.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from enum import StrEnum

from cgcell.dominio import DadosOrdemServico, StatusOS, StatusPagamento
from cgcell.servicos.erros import ErroValidacao

TAMANHO_MAXIMO_CODIGO_OS = 30


def eh_data_valida(valor: object) -> bool:
    """Aceita somente `date` (um `datetime` não serve, pois carrega hora)."""
    return isinstance(valor, date) and not isinstance(valor, datetime)


def eh_inteiro(valor: object) -> bool:
    """Inteiro de verdade (`True`/`False` também são `int` em Python, mas não valem aqui)."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def normalizar_texto(valor: object) -> str:
    """Remove espaços nas pontas e espaços repetidos no meio."""
    return " ".join(valor.split()) if isinstance(valor, str) else ""


def _converter_enum[E: StrEnum](classe: type[E], valor: object) -> E | None:
    try:
        return classe(valor)
    except ValueError:
        return None


def verificar_consistencia(
    status_os: StatusOS | None,
    status_pagamento: StatusPagamento | None,
    data_abertura: date | None,
    data_conclusao: date | None,
    data_pagamento: date | None,
) -> list[str]:
    """Regras de consistência entre campos (seção 5 do AGENTS.md)."""
    erros: list[str] = []

    if status_pagamento == StatusPagamento.PAGO and data_pagamento is None:
        erros.append("Para marcar como pago, informe a data de pagamento.")
    if status_pagamento == StatusPagamento.PENDENTE and data_pagamento is not None:
        erros.append("Com pagamento pendente, a data de pagamento deve ficar vazia.")

    if status_os is not None and status_os != StatusOS.CONCLUIDA and data_conclusao is not None:
        erros.append("A data de conclusão só pode ser preenchida quando a OS está concluída.")

    if status_os == StatusOS.CANCELADA and status_pagamento == StatusPagamento.PAGO:
        erros.append("OS cancelada não pode ter pagamento registrado.")

    if data_abertura is not None:
        if data_conclusao is not None and data_conclusao < data_abertura:
            erros.append("A data de conclusão não pode ser anterior à data de abertura.")
        if data_pagamento is not None and data_pagamento < data_abertura:
            erros.append("A data de pagamento não pode ser anterior à data de abertura.")

    return erros


def validar_dados_ordem_servico(dados: DadosOrdemServico, hoje: date) -> DadosOrdemServico:
    """Valida todos os campos e devolve os dados normalizados.

    Levanta `ErroValidacao` com TODAS as mensagens encontradas, para o usuário
    corrigir tudo de uma vez.
    """
    erros: list[str] = []

    codigo = normalizar_texto(dados.codigo_os)
    if not codigo:
        erros.append("Informe o código da OS.")
    elif len(codigo) > TAMANHO_MAXIMO_CODIGO_OS:
        erros.append(f"O código da OS deve ter no máximo {TAMANHO_MAXIMO_CODIGO_OS} caracteres.")

    if not eh_inteiro(dados.valor_servico):
        erros.append("O valor do serviço deve ser um número inteiro de centavos.")
    elif dados.valor_servico < 0:
        erros.append("O valor do serviço não pode ser negativo.")

    if not eh_inteiro(dados.id_tipo_servico):
        erros.append("Informe o tipo de serviço.")

    status_os = _converter_enum(StatusOS, dados.status_os)
    if status_os is None:
        erros.append("Status da OS inválido.")
    status_pagamento = _converter_enum(StatusPagamento, dados.status_pagamento)
    if status_pagamento is None:
        erros.append("Status de pagamento inválido.")

    datas: dict[str, date | None] = {}
    for campo, rotulo, obrigatoria in (
        ("data_abertura", "abertura", True),
        ("data_conclusao", "conclusão", False),
        ("data_pagamento", "pagamento", False),
    ):
        valor = getattr(dados, campo)
        if valor is None and not obrigatoria:
            datas[campo] = None
        elif not eh_data_valida(valor):
            erros.append(f"Informe uma data de {rotulo} válida.")
            datas[campo] = None
        elif valor > hoje:
            erros.append(f"A data de {rotulo} não pode estar no futuro.")
            datas[campo] = valor
        else:
            datas[campo] = valor

    erros.extend(
        verificar_consistencia(
            status_os,
            status_pagamento,
            datas["data_abertura"],
            datas["data_conclusao"],
            datas["data_pagamento"],
        )
    )

    if erros:
        raise ErroValidacao(erros)

    return replace(
        dados,
        codigo_os=codigo,
        status_os=status_os,
        status_pagamento=status_pagamento,
    )
