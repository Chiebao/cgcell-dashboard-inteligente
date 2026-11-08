"""Mostra no terminal o relatório exploratório do banco da aplicação.

Uso (na raiz do projeto, com o ambiente virtual ativado):

    python -m scripts.relatorio_exploratorio                 # todos os dados
    python -m scripts.relatorio_exploratorio --origem reais  # reais | simulados | todos

O relatório só é exibido na tela (não é salvo), porque pode conter dados reais da empresa.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from cgcell.analise.exploracao import RelatorioExploratorio
from cgcell.analise.preparacao import FiltroOrigem
from cgcell.servicos.servico_dados import gerar_relatorio_exploratorio
from cgcell.servicos.sessao import abrir_conexao


def formatar_relatorio(relatorio: RelatorioExploratorio) -> str:
    def tabela(dados: pd.DataFrame) -> str:
        return "(vazio)" if dados.empty else dados.to_string(index=False)

    cobertura = relatorio.cobertura.drop(columns=["frequencia"])
    partes = [
        "RELATÓRIO EXPLORATÓRIO — CG CELL Repair",
        "=" * 60,
        *[f"- {observacao}" for observacao in relatorio.observacoes],
        "",
        f"Registros lidos: {relatorio.total_entrada} | válidos: {relatorio.total_valido} | "
        f"inconsistentes: {relatorio.quantidade_rejeitados} | "
        f"duplicados: {relatorio.duplicados_removidos}",
        f"Por origem: {relatorio.quantidade_por_origem}",
        "",
        "VALORES AUSENTES",
        tabela(relatorio.valores_ausentes[["coluna", "ausentes", "percentual"]]),
        "",
        "REGISTROS INCONSISTENTES",
        tabela(relatorio.rejeitados[["codigo_os", "motivo"]]),
        "",
        "OS POR DIA DA SEMANA",
        tabela(relatorio.por_dia_semana),
        "",
        "OS POR TIPO DE SERVIÇO",
        tabela(relatorio.por_tipo_servico),
        "",
        "TEMPO ENTRE ETAPAS (dias)",
        tabela(relatorio.tempos),
        "",
        "AGRUPAMENTO NO TEMPO",
        tabela(cobertura),
    ]
    return "\n".join(partes)


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument(
        "--origem",
        choices=[str(filtro) for filtro in FiltroOrigem],
        default=str(FiltroOrigem.TODOS),
        help="Quais registros analisar (padrão: todos).",
    )
    opcoes = leitor.parse_args(argumentos)

    with abrir_conexao() as conexao:
        relatorio = gerar_relatorio_exploratorio(conexao, FiltroOrigem(opcoes.origem))
    print(formatar_relatorio(relatorio))
    return 0


if __name__ == "__main__":
    # O terminal do Windows nem sempre usa UTF-8; isso evita erro com acentos e setas.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
