"""Testes da formatação no padrão brasileiro."""

from __future__ import annotations

from datetime import date

import pytest

from cgcell.apresentacao.formatacao import (
    centavos_para_texto,
    converter_texto_para_centavos,
    formatar_data,
    formatar_moeda,
    rotulo_origem,
)
from cgcell.dominio import OrigemRegistro


@pytest.mark.parametrize(
    ("centavos", "esperado"),
    [
        (0, "R$ 0,00"),
        (5, "R$ 0,05"),
        (15000, "R$ 150,00"),
        (123456, "R$ 1.234,56"),
        (123456789, "R$ 1.234.567,89"),
        (-15050, "-R$ 150,50"),
    ],
)
def test_formatar_moeda(centavos, esperado):
    assert formatar_moeda(centavos) == esperado


def test_formatar_data():
    assert formatar_data(date(2026, 6, 1)) == "01/06/2026"
    assert formatar_data(None) == "—"


@pytest.mark.parametrize(
    ("texto", "centavos"),
    [
        ("150", 15000),
        ("150,5", 15050),
        ("150,50", 15050),
        ("0", 0),
        ("1.234,56", 123456),
        ("R$ 1.234,56", 123456),
        (" 12.345.678 ", 1234567800),
    ],
)
def test_converter_texto_para_centavos(texto, centavos):
    assert converter_texto_para_centavos(texto) == centavos


@pytest.mark.parametrize("texto", ["150.50", "1,234", "abc", "12,345", "1.23,00", "1.2345"])
def test_converter_rejeita_formato_invalido(texto):
    with pytest.raises(ValueError, match="Valor inválido"):
        converter_texto_para_centavos(texto)


def test_converter_rejeita_vazio_e_negativo():
    with pytest.raises(ValueError, match="Informe o valor"):
        converter_texto_para_centavos("  ")
    with pytest.raises(ValueError, match="negativo"):
        converter_texto_para_centavos("-10")


def test_centavos_para_texto_faz_ida_e_volta():
    assert centavos_para_texto(123456) == "1.234,56"
    assert converter_texto_para_centavos(centavos_para_texto(123456)) == 123456


def test_rotulo_de_simulado_em_destaque():
    assert "SIMULADO" in rotulo_origem(OrigemRegistro.SIMULADO)
    assert rotulo_origem(OrigemRegistro.MANUAL) == "Manual"
