"""Pipeline de dados: o caminho único e reproduzível pelo qual os registros passam.

    registros crus
      -> 1. tipagem      (datas e valores; inválidos viram ausentes)
      -> 2. recorte      (reais / simulados / todos)
      -> 3. validação    (regras de negócio; inválidos vão para `rejeitados` com o motivo)
      -> 4. limpeza      (duplicados por código da OS)
      -> 5. transformação (colunas derivadas)
      -> base pronta para indicadores, exploração e preparação do modelo

Rodar o pipeline duas vezes com os mesmos registros dá exatamente o mesmo resultado.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cgcell.analise.preparacao import (
    COLUNAS_BASE,
    FiltroOrigem,
    criar_base_analise,
    filtrar_por_origem,
)
from cgcell.analise.tratamento import (
    adicionar_colunas_derivadas,
    remover_duplicados,
    resumo_valores_ausentes,
    validar_registros,
)


@dataclass(frozen=True)
class ResultadoPipeline:
    base: pd.DataFrame
    """Registros válidos, limpos e transformados."""
    rejeitados: pd.DataFrame
    """Registros que não passaram na validação, com o motivo."""
    valores_ausentes: pd.DataFrame
    """Ausentes por coluna, medidos logo após a tipagem (antes da validação)."""
    total_entrada: int
    duplicados_removidos: int
    filtro_origem: FiltroOrigem


def executar_pipeline(
    registros: list[dict], filtro_origem: FiltroOrigem = FiltroOrigem.TODOS
) -> ResultadoPipeline:
    filtro_origem = FiltroOrigem(filtro_origem)
    tipada = filtrar_por_origem(criar_base_analise(registros), filtro_origem)
    ausentes = resumo_valores_ausentes(tipada, COLUNAS_BASE)
    validos, rejeitados = validar_registros(tipada)
    limpos, duplicados = remover_duplicados(validos)
    base = adicionar_colunas_derivadas(limpos).reset_index(drop=True)
    return ResultadoPipeline(
        base=base,
        rejeitados=rejeitados,
        valores_ausentes=ausentes,
        total_entrada=len(tipada),
        duplicados_removidos=duplicados,
        filtro_origem=filtro_origem,
    )
