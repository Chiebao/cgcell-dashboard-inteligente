# Análise inicial do projeto

> Documento produzido no início da Etapa 1 (08/11/2026), antes de qualquer código.
> Serve de referência para as decisões de arquitetura e de cronograma.

---

## 1. Diagnóstico do que já existe

Pasta `C:\Users\Elias\Documents\systenRepair` (já existia):

| Item | Situação |
|---|---|
| `AGENTS.md` | Regras permanentes do projeto. |
| `prompt-etapa-1.md` | Tarefa da Etapa 1. |
| Código, testes, banco | **Nada.** O projeto começa do zero. |
| Repositório Git local | **Não existe.** |
| Repositório no GitHub | **Não existe** (`Chiebao/cgcell-dashboard-inteligente` ainda precisa ser criado). |

Ferramentas verificadas no PC:

| Ferramenta | Versão | Observação |
|---|---|---|
| Python | 3.12.10 | Única versão instalada. Atende ao requisito (3.12). |
| Git | 2.56.0.windows.3 | Configurado com nome `Elias Henrique` e e-mail `eliashenr@outlook.com`. |
| GitHub CLI (`gh`) | 2.103.3 | Logado em três contas; a **ativa é `eliashenr`**, não `Chiebao` (ver riscos). |

---

## 2. Arquitetura recomendada

Arquitetura **modular em camadas**, num único pacote Python chamado `cgcell`.
Cada camada só conversa com a camada imediatamente abaixo:

```
┌──────────────────────────────────────────────┐
│ Apresentação (Streamlit)   cgcell/apresentacao│  telas, formulários, gráficos
└───────────────┬──────────────────────────────┘
                │ chama funções de serviço (nunca SQL direto)
┌───────────────▼──────────────────────────────┐
│ Serviços                    cgcell/servicos   │  regras de negócio e validações
└───────┬───────────────────────────┬──────────┘
        │                           │
┌───────▼──────────┐      ┌─────────▼──────────┐
│ Dados            │      │ Análise            │  indicadores e agregações (Pandas)
│ cgcell/dados     │      │ cgcell/analise     │
│ SQLite, migrações│      └─────────┬──────────┘
└──────────────────┘                │
                          ┌─────────▼──────────┐
                          │ Machine Learning   │  treino, avaliação, previsão
                          │ cgcell/ml          │
                          └────────────────────┘
Testes (tests/) cobrem cada camada isoladamente e os fluxos completos.
```

Por que assim:

- **Interface sem SQL:** se um dia a interface mudar (ex.: uma API), as regras de negócio continuam as mesmas.
- **Regras de negócio testáveis sem Streamlit:** os testes chamam os serviços direto, com banco temporário.
- **Análise separada de ML:** a preparação dos dados não se mistura com o treinamento (exigência da seção 8 do AGENTS.md e proteção contra vazamento de dados).

### Layout do pacote: plano (pasta `cgcell/` na raiz)

Alternativa considerada: layout `src/` (`src/cgcell/`), que exige instalar o próprio projeto com `pip install -e .`.
Escolhido o **layout plano** porque:

- `streamlit run app.py` já encontra o pacote `cgcell` sem passo extra (o Streamlit coloca a pasta do `app.py` no caminho de importação).
- Menos um comando para quem está começando no terminal.
- O Pytest encontra o pacote pela configuração `pythonpath = ["."]` no `pyproject.toml`.

---

## 3. Árvore de pastas

```
systenRepair/
├── app.py                    # Ponto de entrada do Streamlit (fino: só monta a página)
├── cgcell/                   # Pacote principal da aplicação
│   ├── __init__.py
│   ├── config.py             # Lê variáveis de ambiente (.env) — caminho do banco etc.
│   ├── apresentacao/         # Camada de apresentação: páginas e componentes Streamlit, formatação BR
│   ├── servicos/             # Camada de serviços: regras de negócio, validações, consistência
│   ├── dados/                # Camada de dados: conexão SQLite, consultas parametrizadas
│   │   └── migracoes/        # Scripts SQL numerados (0001_..., 0002_...) — Etapa 2
│   ├── analise/              # Indicadores, agregações por período e por tipo de serviço
│   └── ml/                   # Preparação de variáveis, baseline, modelos, avaliação — Etapa 5
├── scripts/                  # Utilitários de linha de comando (backup, base simulada)
├── data/                     # Banco SQLite local. Fora do Git (só o .gitkeep é versionado)
├── docs/                     # Documentação, diagramas, capturas de tela (dados fictícios)
├── tests/
│   ├── unitarios/            # Testes de funções isoladas (cálculos, validações)
│   ├── integracao/           # Testes com SQLite temporário e fluxos completos
│   └── ml/                   # Testes do módulo de ML (separação temporal, baseline, vazamento)
├── .streamlit/config.toml    # Configuração do Streamlit (desliga envio de estatísticas de uso)
├── requirements.txt          # Dependências de execução (versões fixas)
├── requirements-dev.txt      # Dependências de desenvolvimento (testes, Ruff)
├── pyproject.toml            # Configuração do Ruff e do Pytest
├── .env.example              # Modelo de variáveis de ambiente, sem valores reais
├── .gitignore                # O que o Git deve ignorar (banco, .env, venv, caches)
├── .gitattributes            # Padroniza fim de linha entre Windows e Linux (CI)
├── LICENSE                   # MIT, titular Chiebao
├── README.md                 # Apresentação do projeto
└── AGENTS.md                 # Regras permanentes do projeto
```

`.github/workflows/` (GitHub Actions) só será criada na Etapa 6.

---

## 4. Dependências

Versões exatas ficam fixadas nos arquivos `requirements*.txt` (ver README).
Só entram agora as bibliotecas usadas nas Etapas 1 a 3.

### Execução (`requirements.txt`)

| Biblioteca | Para quê | Por que ela |
|---|---|---|
| `streamlit` | Interface web | Exigida pela stack. Gera interface com Python puro, sem HTML/JS. |
| `pandas` | Transformação e agregação de dados | Exigida pela stack. Padrão de mercado para dados tabulares. |
| `plotly` | Gráficos interativos | Exigida pela stack. Integra nativamente com Streamlit (`st.plotly_chart`). |
| `python-dotenv` | Ler o arquivo `.env` | O AGENTS.md pede configurações em variáveis de ambiente com `.env.example`. Sem esta biblioteca, o `.env` não seria lido automaticamente no Windows. É pequena e sem dependências. |

`sqlite3` já vem com o Python: nenhuma instalação. `numpy` chega junto com o Pandas e só será listada
explicitamente quando o código usá-la diretamente.

### Desenvolvimento (`requirements-dev.txt`)

| Biblioteca | Para quê | Por que agora |
|---|---|---|
| `pytest` | Testes automatizados | A Etapa 2 já exige testes; a Etapa 1 tem um teste de fumaça. |
| `ruff` | Análise estática e formatação | Um único binário rápido. Configurado desde já evita acumular problemas até a Etapa 6. |

### Ficam para depois (não instaladas agora)

| Biblioteca | Quando | Motivo de esperar |
|---|---|---|
| `scikit-learn` | Etapa 5 | Só faz sentido com o módulo de ML. |
| `pre-commit` | Etapa 6 | Junto com a configuração de CI. |
| SHAP | Talvez nunca | Só se um modelo superar o baseline; Permutation Importance (já no scikit-learn) vem antes. |
| MLflow | Nunca | Fora do escopo (AGENTS.md, seção 3). |

---

## 5. MVP x diferenciais de portfólio

### MVP (obrigatório para a disciplina)

- Cadastro de tipos de serviço (cadastrar, consultar, ativar, desativar).
- Cadastro de OS com validações, regras de consistência, edição e exclusão lógica (seção 5 do AGENTS.md).
- Banco SQLite com integridade referencial e migração inicial.
- Dashboard: faturamento recebido (por data de pagamento), quantidade de OS (por data de abertura),
  serviços mais frequentes, distribuição de status, evolução de faturamento e de volume, filtros por período.
- Filtro real / simulado e rótulo **SIMULADO**.
- Exibição no padrão brasileiro (DD/MM/AAAA, R$ 1.234,56).
- Testes das regras de negócio e dos indicadores.
- README apresentável e repositório organizado.

### Diferenciais de portfólio (depois de 17/11)

- Pipeline de engenharia de dados documentado e reutilizável (Etapa 4).
- Módulo de ML com validação temporal, comparação com baseline e métricas honestas (Etapa 5).
- Interpretabilidade com Permutation Importance, se houver modelo que supere o baseline.
- CI no GitHub Actions (Ruff + Pytest) e pre-commit (Etapa 6).
- Importação de CSV com relatório de linhas aceitas e rejeitadas.
- Script de backup e procedimento de recuperação.
- Validação real com a empresa, em duas rodadas documentadas (Etapa 7).

---

## 6. Cronograma técnico

Hoje é **08/11/2026**. O prazo de **17/11/2026** deixa **9 dias** para as Etapas 1 a 3.

| Data | Entrega |
|---|---|
| 08/11 | Etapa 1 — estrutura, ambiente, README inicial, Git, GitHub. |
| 09/11 a 12/11 | Etapa 2 — banco, migração, serviços, regras de consistência, testes. |
| 13/11 a 15/11 | Etapa 3 — dashboard, cadastros na interface, filtros, gráficos. |
| 16/11 | README final, capturas com dados fictícios, revisão, merge dos PRs. |
| 17/11 | Margem de segurança. Projeto publicado. |
| Depois de 17/11 | Etapas 4 a 8, em sequência, sem prazo fixo. |

### O que cortar se o prazo apertar (nesta ordem)

1. Importação de CSV — já é complementar; fica para depois de 17/11.
2. Script de backup — documentar o procedimento manual (copiar o arquivo `.db`) e automatizar depois.
3. Acabamento visual do dashboard — manter os gráficos exigidos, sem personalização além do necessário.

Nada disso será cortado sem avisar e pedir aprovação antes.

---

## 7. Riscos, limitações e decisões pendentes

### Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Prazo curto (9 dias para 3 etapas) | Alto | Cronograma acima, lista de cortes pré-aprovável, uma etapa por vez. |
| Conta do GitHub: o `gh` está com a conta `eliashenr` ativa e o Git assina commits como `Elias Henrique <eliashenr@outlook.com>` | Médio | Os commits podem aparecer no GitHub como de outra conta, e o `git push` pode ser recusado no repositório de `Chiebao`. Precisa de decisão (abaixo). |
| Sem histórico real de dados | Alto para o ML | Base SIMULADA rotulada em todo lugar; avaliação real só com histórico suficiente (critério na Etapa 5). |
| Streamlit sem login nativo | Médio | App roda só localmente; limitação documentada no README. |
| Política de execução do PowerShell pode bloquear a ativação do venv | Baixo | Solução documentada no README (válida só para a janela atual). |

### Limitações conhecidas

- O app não é hospedado online; roda no PC com `streamlit run`.
- Faturamento não é lucro: o sistema não registra custo de peças.
- Nenhum resultado de ML pode ser apresentado como real enquanto não houver histórico real.

### Decisões que precisam de aprovação

1. **Identidade dos commits:** manter `Elias Henrique <eliashenr@outlook.com>` ou usar a conta `Chiebao` neste repositório.
2. **Publicar o `AGENTS.md`?** Proposta: sim (documenta as regras e mostra o processo). Os arquivos `prompt-etapa-*.md` ficam só no PC (ignorados pelo Git).
3. **Dados fictícios para capturas de tela antes da Etapa 5:** o gerador de base simulada está previsto para a Etapa 5,
   mas o README de 17/11 precisa de capturas. Opções: cadastrar algumas OS fictícias à mão na Etapa 3, ou antecipar
   um gerador simples (gravando `origem_registro = simulado`) para a Etapa 3.
4. **CI mínima antes de 17/11?** O GitHub Actions está na Etapa 6. Antecipar uma verificação simples (Ruff + Pytest)
   deixaria o repositório mais profissional na entrega, ao custo de algumas horas.
5. **`python-dotenv`** como dependência de execução (justificativa na seção 4).
