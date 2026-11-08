"""Formatação no padrão brasileiro. Usada só na apresentação.

O banco continua guardando datas ISO e valores em centavos; a conversão acontece aqui.
"""

from __future__ import annotations

import re
from datetime import date

from cgcell.dominio import OrigemRegistro

_VALOR_COM_MILHAR = re.compile(r"^\d{1,3}(\.\d{3})+(,\d{1,2})?$")
_VALOR_SIMPLES = re.compile(r"^\d+(,\d{1,2})?$")


def formatar_moeda(centavos: int) -> str:
    """15000 -> 'R$ 150,00'; 123456789 -> 'R$ 1.234.567,89'."""
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(int(centavos)), 100)
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{resto:02d}"


def formatar_data(valor: date | None, vazio: str = "—") -> str:
    """date(2026, 6, 1) -> '01/06/2026'."""
    return valor.strftime("%d/%m/%Y") if valor is not None else vazio


def converter_texto_para_centavos(texto: str) -> int:
    """Converte o valor digitado pelo usuário em centavos.

    Aceita '150', '150,5', '150,50', '1.234,56' e 'R$ 1.234,56'.
    Rejeita ponto como separador decimal ('150.50'), que é ambíguo no padrão brasileiro.
    """
    limpo = (texto or "").replace("R$", "").replace(" ", "").strip()
    if not limpo:
        raise ValueError("Informe o valor do serviço.")
    if limpo.startswith("-"):
        raise ValueError("O valor do serviço não pode ser negativo.")
    if not (_VALOR_SIMPLES.match(limpo) or _VALOR_COM_MILHAR.match(limpo)):
        raise ValueError("Valor inválido. Use o formato 1.234,56 (vírgula para os centavos).")
    inteiro, _, decimal = limpo.replace(".", "").partition(",")
    return int(inteiro) * 100 + int(decimal.ljust(2, "0") or "0")


def centavos_para_texto(centavos: int) -> str:
    """15000 -> '150,00' (para preencher o campo de valor numa edição)."""
    return formatar_moeda(centavos).removeprefix("R$ ")


def rotulo_origem(origem: OrigemRegistro) -> str:
    """Rótulo de exibição; dados simulados sempre em destaque."""
    return {
        OrigemRegistro.MANUAL: "Manual",
        OrigemRegistro.IMPORTADO: "Importado",
        OrigemRegistro.SIMULADO: "⚠️ SIMULADO",
    }[OrigemRegistro(origem)]
