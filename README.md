# CG CELL Repair — Dashboard Inteligente

Dashboard para gestão e análise de dados de uma assistência técnica de celulares, desenvolvido em Python
com Streamlit, Pandas, Plotly e SQLite. Projeto acadêmico do curso de Análise e Desenvolvimento de Sistemas.

> **Status:** em desenvolvimento — **Etapa 3 de 8 concluída**: cadastros e dashboard gerencial funcionando.
> O módulo de Machine Learning ainda não foi implementado. Veja o [roadmap](#roadmap).

---

## Problema e solução

A **CG CELL Repair** (assistência técnica de celulares em Sorocaba-SP) já usa um sistema de ordens de serviço (OS),
mas ele não oferece uma visão gerencial dos dados.

Este projeto é uma **ferramenta complementar** — não substitui o sistema atual — para que o gestor visualize:

- faturamento recebido;
- volume de OS;
- serviços mais frequentes;
- evolução dos indicadores ao longo do tempo.

No longo prazo, o objetivo é adicionar um módulo de **Machine Learning** que identifique padrões históricos e gere
previsões úteis ao planejamento.

### Observações importantes

- **Faturamento não é lucro.** O sistema não registra custo de peças, portanto não calcula margem.
- **Não há histórico real de dados.** O sistema de OS atual não exporta dados. Os dados reais entrarão por cadastro
  manual. Qualquer dado gerado para demonstração será identificado como **SIMULADO** na interface, nos gráficos e
  nesta documentação.

---

## Funcionalidades

| Tela | O que faz |
|---|---|
| **📊 Dashboard** | Faturamento recebido, quantidade de OS, OS concluídas e canceladas; evolução do faturamento e do volume; serviços mais frequentes; distribuição por status. Filtros de período (pré-definidos ou personalizado), de origem (apenas reais / apenas simulados / todos) e de agrupamento (dia, semana, mês). |
| **🧾 Ordens de serviço** | Cadastrar OS; consultar com busca por código e filtros de status e origem; editar, registrar pagamento e excluir (conforme as regras de cada situação). |
| **🛠️ Tipos de serviço** | Cadastrar, consultar, ativar e desativar. |

### Regras de cálculo do dashboard

| Indicador | Regra |
|---|---|
| Faturamento recebido | Soma das OS **pagas**, filtradas pela **data de pagamento**. Não é lucro. |
| Quantidade de OS | OS filtradas pela **data de abertura**, em qualquer situação. |
| OS concluídas | OS abertas no período com status Concluída (canceladas nunca contam). |
| Serviços mais frequentes | OS abertas no período, **sem as canceladas**. |
| Todas | OS excluídas logicamente nunca entram. |

Dados SIMULADOS aparecem com aviso no topo, título de gráfico sinalizado e barras **laranjas com hachura**.
Exibição no padrão brasileiro: `DD/MM/AAAA` e `R$ 1.234,56`.

---

## Arquitetura

Arquitetura modular em camadas. A interface nunca acessa o banco diretamente: passa sempre pela camada de serviços.

```
Apresentação (Streamlit) → Serviços (regras de negócio) → Dados (SQLite)
                                       ↓
                           Análise (indicadores) → Machine Learning
```

```
systenRepair/
├── app.py                 # Ponto de entrada do Streamlit
├── cgcell/                # Pacote principal
│   ├── config.py          # Configurações via variáveis de ambiente
│   ├── apresentacao/      # Páginas e componentes Streamlit
│   ├── servicos/          # Regras de negócio e validações
│   ├── dados/             # Conexão SQLite e migrações
│   ├── analise/           # Indicadores e agregações
│   └── ml/                # Treino, avaliação e previsão
├── scripts/               # Utilitários de linha de comando
├── data/                  # Banco SQLite local (fora do Git)
├── docs/                  # Documentação e diagramas
└── tests/                 # unitarios/, integracao/, ml/
```

A análise completa das decisões está em [docs/analise_inicial.md](docs/analise_inicial.md).

---

## Banco de dados

```mermaid
erDiagram
    tipo_servico ||--o{ ordem_servico : "classifica"
    tipo_servico {
        INTEGER id_tipo_servico PK
        TEXT nome_servico
        INTEGER ativo
    }
    ordem_servico {
        INTEGER id_ordem_servico PK
        TEXT codigo_os
        TEXT data_abertura
        INTEGER valor_servico "centavos"
        TEXT status_os
        TEXT status_pagamento
        TEXT data_pagamento
        INTEGER id_tipo_servico FK
        TEXT origem_registro "manual | importado | simulado"
        INTEGER excluida "exclusão lógica"
    }
```

Destaques:

- Valores em centavos e datas em ISO; a conversão para R$ e DD/MM/AAAA acontece só na tela.
- Regras de consistência validadas na camada de serviços **e** como `CHECK` no próprio banco.
- Migrações versionadas (`cgcell/dados/migracoes/0001_...sql`), aplicadas automaticamente.
- Exclusão somente lógica, permitida após 90 dias da abertura.
- Backup com `python -m scripts.backup_banco`.

Diagrama completo, regras de edição e procedimento de recuperação:
[docs/banco_de_dados.md](docs/banco_de_dados.md).

---

## Tecnologias

| Tecnologia | Uso | Justificativa |
|---|---|---|
| Python 3.12 | Linguagem principal | Ecossistema de dados e ML. |
| Streamlit | Interface web | Interface com Python puro, sem HTML/JS. |
| Pandas | Manipulação de dados | Padrão para dados tabulares. |
| Plotly | Gráficos interativos | Integração nativa com Streamlit. |
| SQLite | Banco de dados | Já vem com o Python; um arquivo local, sem servidor. |
| python-dotenv | Configuração | Lê o arquivo `.env` com as variáveis de ambiente. |
| Pytest | Testes automatizados | Padrão de mercado para testes em Python. |
| Ruff | Qualidade de código | Linter e formatador rápido, uma ferramenta só. |

---

## Instalação (Windows / PowerShell)

Pré-requisitos: **Python 3.12** e **Git** instalados.

```powershell
# 1. Baixar o projeto e entrar na pasta
git clone https://github.com/Chiebao/cgcell-dashboard-inteligente.git
cd cgcell-dashboard-inteligente

# 2. Criar o ambiente virtual (isola as bibliotecas deste projeto)
python -m venv .venv

# 3. Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# 4. Instalar as dependências (execução + desenvolvimento)
python -m pip install -r requirements-dev.txt

# 5. (Opcional) Criar o arquivo de configuração local a partir do modelo
Copy-Item .env.example .env
```

Se o passo 3 mostrar um erro de "execução de scripts desabilitada", libere scripts **só para a janela atual**
e tente de novo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

## Execução

### Jeito mais fácil (dois cliques)

Dê dois cliques no arquivo **`iniciar_dashboard.bat`**, na pasta do projeto. Ele:

1. na primeira vez, cria o ambiente virtual e instala as dependências;
2. inicia o app e abre o navegador em `http://localhost:8501`;
3. se o app já estiver aberto, apenas abre o navegador de novo.

Para fechar o app, feche a janela preta que abriu junto.

### Pelo terminal

Com o ambiente virtual ativado:

```powershell
streamlit run app.py
```

O navegador abre em `http://localhost:8501`. Para encerrar, pressione `Ctrl + C` no terminal.

A página recarrega sozinha quando um arquivo do projeto é salvo (opção `runOnSave` em `.streamlit/config.toml`).

## Testes e qualidade

```powershell
python -m pytest          # roda os testes automatizados
python -m ruff check .    # análise estática
```

Os testes nunca usam o banco da aplicação; usam arquivos temporários e dados fictícios.

| Pasta | O que cobre |
|---|---|
| `tests/unitarios/` | Validações, regras de consistência, indicadores, formatação BR, períodos e gráficos (sem banco). |
| `tests/integracao/` | Conexão, migrações, restrições do banco, cadastros, edição, pagamento, exclusão, backup, indicadores a partir do banco e telas (com o `AppTest` do Streamlit). |

---

## Limitações conhecidas

- Sem histórico real ainda: os indicadores refletem só o que for cadastrado a partir de agora.
- Sem login (limitação do Streamlit); o app foi feito para rodar só no computador da loja.
- Faturamento não é lucro: custos de peças não são registrados.
- Capturas de tela ainda não incluídas (serão feitas apenas com dados fictícios).

---

## Segurança e privacidade

- O app roda **apenas localmente**. O Streamlit não tem login nativo: se um dia for hospedado online, será preciso
  tratar o acesso público e a persistência do SQLite (hospedagens com disco temporário perdem os dados).
- O banco (`data/*.db`), os backups (`backups/`) e o arquivo `.env` ficam **fora do repositório**.
- Todas as consultas SQL são parametrizadas (sem montar SQL com dados do usuário).
- **LGPD:** o projeto evita dados pessoais por design — não armazena nome, telefone ou documento de clientes,
  apenas dados das ordens de serviço necessários à análise.

---

## Roadmap

- [x] **Etapa 1** — Diagnóstico e estrutura do projeto
- [x] **Etapa 2** — Banco de dados e regras de negócio
- [x] **Etapa 3** — Dashboard
- [ ] **Etapa 4** — Engenharia de dados
- [ ] **Etapa 5** — Machine Learning (sobre base SIMULADA até haver histórico real)
- [ ] **Etapa 6** — Testes e CI/CD
- [ ] **Etapa 7** — Validação com a empresa
- [ ] **Etapa 8** — Finalização

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).
