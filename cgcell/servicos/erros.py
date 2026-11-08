"""Erros de negócio levantados pela camada de serviços.

A interface captura estes erros e mostra as mensagens ao usuário.
"""

from __future__ import annotations


class ErroNegocio(Exception):
    """Base de todos os erros de regra de negócio."""


class ErroValidacao(ErroNegocio):
    """Um ou mais campos são inválidos. Guarda todas as mensagens de uma vez."""

    def __init__(self, erros: list[str]) -> None:
        self.erros = list(erros)
        super().__init__("; ".join(self.erros))


class RegistroNaoEncontrado(ErroNegocio):
    """O registro não existe (ou foi excluído logicamente)."""


class OperacaoNaoPermitida(ErroNegocio):
    """A operação viola uma regra de negócio (ex.: editar OS cancelada)."""
