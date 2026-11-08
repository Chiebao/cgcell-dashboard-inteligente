"""Funções reutilizáveis de tratamento: datas, valores, ausentes, validação, limpeza e derivação.

Pensadas para qualquer fonte de dados (banco hoje; importação de CSV no futuro).
Nenhuma função altera o DataFrame recebido: todas devolvem uma cópia.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import pandas as pd

from cgcell.dominio import OrigemRegistro, StatusOS, StatusPagamento
from cgcell.servicos.validacoes import verificar_consistencia

OBSERVACOES_AUSENTES = {
    "data_conclusao": "Esperado: OS que ainda não foram concluídas não têm data de conclusão.",
    "data_pagamento": "Esperado: OS com pagamento pendente não têm data de pagamento.",
}
_OBSERVACAO_PADRAO = "Não deveria haver ausentes nesta coluna."


# --- Tipagem ---


def converter_datas(base: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Converte texto ISO (AAAA-MM-DD) em data. Texto inválido vira ausente (NaT),
    para ser apontado depois pela validação, em vez de interromper o fluxo."""
    resultado = base.copy()
    for coluna in colunas:
        resultado[coluna] = pd.to_datetime(resultado[coluna], format="%Y-%m-%d", errors="coerce")
    return resultado


def converter_valores(base: pd.DataFrame, coluna: str = "valor_servico") -> pd.DataFrame:
    """Converte para inteiro (centavos). Valor não numérico vira ausente (<NA>)."""
    resultado = base.copy()
    resultado[coluna] = pd.to_numeric(resultado[coluna], errors="coerce").astype("Int64")
    return resultado


# --- Valores ausentes ---


def resumo_valores_ausentes(base: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Quantidade e percentual de ausentes por coluna, com a explicação de cada caso."""
    total = len(base)
    linhas = []
    for coluna in colunas:
        ausentes = int(base[coluna].isna().sum())
        linhas.append(
            {
                "coluna": coluna,
                "ausentes": ausentes,
                "percentual": round(100 * ausentes / total, 1) if total else 0.0,
                "observacao": OBSERVACOES_AUSENTES.get(coluna, _OBSERVACAO_PADRAO),
            }
        )
    return pd.DataFrame(linhas, columns=["coluna", "ausentes", "percentual", "observacao"])


# --- Validação ---


def _para_enum[E: StrEnum](classe: type[E], valor: object) -> E | None:
    try:
        return classe(valor)
    except ValueError:
        return None


def _para_data(valor: object) -> date | None:
    return None if pd.isna(valor) else pd.Timestamp(valor).date()


def motivos_rejeicao(linha: pd.Series) -> list[str]:
    """Todos os problemas de um registro. Lista vazia = registro válido.

    As regras de consistência vêm de `verificar_consistencia`, a MESMA função usada
    no cadastro: a regra existe num único lugar.
    """
    motivos: list[str] = []
    codigo = linha["codigo_os"]
    if not isinstance(codigo, str) or not codigo.strip():
        motivos.append("Código da OS ausente.")

    valor = linha["valor_servico"]
    if pd.isna(valor):
        motivos.append("Valor do serviço ausente ou inválido.")
    elif valor < 0:
        motivos.append("Valor do serviço negativo.")

    if pd.isna(linha["data_abertura"]):
        motivos.append("Data de abertura ausente ou inválida.")

    status_os = _para_enum(StatusOS, linha["status_os"])
    if status_os is None:
        motivos.append("Status da OS inválido.")
    status_pagamento = _para_enum(StatusPagamento, linha["status_pagamento"])
    if status_pagamento is None:
        motivos.append("Status de pagamento inválido.")
    if _para_enum(OrigemRegistro, linha["origem_registro"]) is None:
        motivos.append("Origem do registro inválida.")

    motivos += verificar_consistencia(
        status_os,
        status_pagamento,
        _para_data(linha["data_abertura"]),
        _para_data(linha["data_conclusao"]),
        _para_data(linha["data_pagamento"]),
    )
    return motivos


def validar_registros(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa registros válidos e rejeitados. Rejeitados vêm com o motivo."""
    motivos = base.apply(motivos_rejeicao, axis=1, result_type="reduce")
    if base.empty:
        motivos = pd.Series([], dtype=object)
    invalido = motivos.map(bool).astype(bool)
    rejeitados = pd.DataFrame(
        {
            "id_ordem_servico": base.loc[invalido, "id_ordem_servico"],
            "codigo_os": base.loc[invalido, "codigo_os"],
            "motivo": motivos[invalido].map("; ".join),
        }
    ).reset_index(drop=True)
    return base.loc[~invalido].copy(), rejeitados


# --- Limpeza ---


def remover_duplicados(base: pd.DataFrame, chave: str = "codigo_os") -> tuple[pd.DataFrame, int]:
    """Remove registros repetidos pela chave (sem diferenciar maiúsculas e espaços),
    mantendo o primeiro. Retorna a base limpa e quantos foram removidos."""
    normalizada = base[chave].astype("string").str.strip().str.lower()
    repetido = normalizada.duplicated(keep="first") & normalizada.notna()
    return base.loc[~repetido].copy(), int(repetido.sum())


# --- Transformação ---


def adicionar_colunas_derivadas(base: pd.DataFrame) -> pd.DataFrame:
    """Colunas calculadas a partir da própria linha (nenhuma usa outras linhas):
    - `dia_semana`: 0 = segunda ... 6 = domingo (da data de abertura);
    - `mes`: 1 a 12 (da data de abertura);
    - `dias_ate_conclusao` e `dias_ate_pagamento`: dias desde a abertura (vazio se não houver).
    """
    resultado = base.copy()
    resultado["dia_semana"] = resultado["data_abertura"].dt.day_of_week
    resultado["mes"] = resultado["data_abertura"].dt.month
    resultado["dias_ate_conclusao"] = (
        resultado["data_conclusao"] - resultado["data_abertura"]
    ).dt.days
    resultado["dias_ate_pagamento"] = (
        resultado["data_pagamento"] - resultado["data_abertura"]
    ).dt.days
    return resultado
