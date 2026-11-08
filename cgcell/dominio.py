"""Tipos do domínio compartilhados entre as camadas.

Este módulo não depende de banco de dados nem de interface: só descreve os dados do negócio.
Os valores dos status são gravados sem acento no banco; os rótulos com acento servem para exibição.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

DIAS_MINIMOS_PARA_EXCLUSAO = 90
"""Uma OS só pode ser excluída (logicamente) depois de mais de 90 dias da abertura."""


class StatusOS(StrEnum):
    """Situação da ordem de serviço."""

    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"

    @property
    def rotulo(self) -> str:
        """Texto para exibição na interface."""
        return _ROTULOS_STATUS_OS[self]


class StatusPagamento(StrEnum):
    """Situação do pagamento da ordem de serviço."""

    PENDENTE = "pendente"
    PAGO = "pago"

    @property
    def rotulo(self) -> str:
        """Texto para exibição na interface."""
        return _ROTULOS_STATUS_PAGAMENTO[self]


class OrigemRegistro(StrEnum):
    """De onde veio o registro. Permite separar e rotular dados simulados."""

    MANUAL = "manual"
    IMPORTADO = "importado"
    SIMULADO = "simulado"


_ROTULOS_STATUS_OS = {
    StatusOS.ABERTA: "Aberta",
    StatusOS.EM_ANDAMENTO: "Em andamento",
    StatusOS.CONCLUIDA: "Concluída",
    StatusOS.CANCELADA: "Cancelada",
}

_ROTULOS_STATUS_PAGAMENTO = {
    StatusPagamento.PENDENTE: "Pendente",
    StatusPagamento.PAGO: "Pago",
}


@dataclass(frozen=True, slots=True)
class TipoServico:
    """Tipo de serviço oferecido (ex.: troca de tela)."""

    id_tipo_servico: int
    nome_servico: str
    descricao: str | None
    ativo: bool


@dataclass(frozen=True, slots=True)
class DadosOrdemServico:
    """Campos informados pelo usuário ao cadastrar ou editar uma OS.

    `valor_servico` é sempre um inteiro em centavos (R$ 150,00 -> 15000).
    """

    codigo_os: str
    data_abertura: date
    valor_servico: int
    id_tipo_servico: int
    status_os: StatusOS = StatusOS.ABERTA
    status_pagamento: StatusPagamento = StatusPagamento.PENDENTE
    data_conclusao: date | None = None
    data_pagamento: date | None = None


@dataclass(frozen=True, slots=True)
class OrdemServico:
    """Ordem de serviço como está gravada no banco."""

    id_ordem_servico: int
    codigo_os: str
    data_abertura: date
    data_conclusao: date | None
    valor_servico: int
    status_os: StatusOS
    status_pagamento: StatusPagamento
    data_pagamento: date | None
    id_tipo_servico: int
    origem_registro: OrigemRegistro
    excluida: bool
    excluida_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime

    def para_dados(self) -> DadosOrdemServico:
        """Extrai os campos editáveis, úteis como ponto de partida de uma edição."""
        return DadosOrdemServico(
            codigo_os=self.codigo_os,
            data_abertura=self.data_abertura,
            valor_servico=self.valor_servico,
            id_tipo_servico=self.id_tipo_servico,
            status_os=self.status_os,
            status_pagamento=self.status_pagamento,
            data_conclusao=self.data_conclusao,
            data_pagamento=self.data_pagamento,
        )
