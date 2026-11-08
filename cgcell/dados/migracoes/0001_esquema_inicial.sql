-- Migração 0001: esquema inicial (tipos de serviço e ordens de serviço).
--
-- As restrições CHECK repetem as regras de negócio da camada de serviços.
-- É uma defesa em profundidade: mesmo um INSERT feito por fora da aplicação
-- não consegue gravar um registro inconsistente.
--
-- Convenções:
--   * datas em texto ISO (AAAA-MM-DD); date(x) IS x garante formato e data existente
--     (com "=" um texto fora do formato passaria, pois date() devolve NULL);
--   * data e hora em texto ISO (AAAA-MM-DD HH:MM:SS);
--   * valores monetários em centavos (inteiros);
--   * booleanos como 0/1.

CREATE TABLE tipo_servico (
    id_tipo_servico INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_servico    TEXT    NOT NULL UNIQUE COLLATE NOCASE
                            CHECK (length(trim(nome_servico)) > 0),
    descricao       TEXT,
    ativo           INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE ordem_servico (
    id_ordem_servico INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_os        TEXT    NOT NULL UNIQUE COLLATE NOCASE
                             CHECK (length(trim(codigo_os)) > 0),
    data_abertura    TEXT    NOT NULL CHECK (date(data_abertura) IS data_abertura),
    data_conclusao   TEXT             CHECK (data_conclusao IS NULL
                                             OR date(data_conclusao) IS data_conclusao),
    valor_servico    INTEGER NOT NULL CHECK (typeof(valor_servico) = 'integer'
                                             AND valor_servico >= 0),
    status_os        TEXT    NOT NULL CHECK (status_os IN
                                 ('aberta', 'em_andamento', 'concluida', 'cancelada')),
    status_pagamento TEXT    NOT NULL CHECK (status_pagamento IN ('pendente', 'pago')),
    data_pagamento   TEXT             CHECK (data_pagamento IS NULL
                                             OR date(data_pagamento) IS data_pagamento),
    id_tipo_servico  INTEGER NOT NULL
                             REFERENCES tipo_servico (id_tipo_servico) ON DELETE RESTRICT,
    origem_registro  TEXT    NOT NULL DEFAULT 'manual'
                             CHECK (origem_registro IN ('manual', 'importado', 'simulado')),
    excluida         INTEGER NOT NULL DEFAULT 0 CHECK (excluida IN (0, 1)),
    excluida_em      TEXT,
    criado_em        TEXT    NOT NULL,
    atualizado_em    TEXT    NOT NULL,

    -- Pago exige data de pagamento; pendente exige data vazia.
    CHECK ((status_pagamento = 'pago') = (data_pagamento IS NOT NULL)),
    -- Data de conclusão só com status concluída.
    CHECK (data_conclusao IS NULL OR status_os = 'concluida'),
    -- Conclusão e pagamento não podem ser anteriores à abertura.
    CHECK (data_conclusao IS NULL OR data_conclusao >= data_abertura),
    CHECK (data_pagamento IS NULL OR data_pagamento >= data_abertura),
    -- OS cancelada não pode ter pagamento.
    CHECK (status_os <> 'cancelada' OR status_pagamento = 'pendente'),
    -- Exclusão lógica sempre registra quando aconteceu.
    CHECK ((excluida = 1) = (excluida_em IS NOT NULL))
);

-- Índices para os filtros do dashboard (abertura, pagamento) e para a junção com o tipo.
CREATE INDEX idx_ordem_servico_data_abertura  ON ordem_servico (data_abertura);
CREATE INDEX idx_ordem_servico_data_pagamento ON ordem_servico (data_pagamento);
CREATE INDEX idx_ordem_servico_tipo           ON ordem_servico (id_tipo_servico);
