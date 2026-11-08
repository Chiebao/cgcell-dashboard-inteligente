# CG CELL Repair — Dashboard Inteligente

Dashboard para gestão e análise de dados de uma assistência técnica de celulares, desenvolvido em Python
com Streamlit, Pandas, Plotly e SQLite. Projeto acadêmico do curso de Análise e Desenvolvimento de Sistemas.

> **Status:** em desenvolvimento — **Etapa 1 de 8 concluída** (estrutura do projeto).
> Cadastros, dashboard e Machine Learning ainda não estão implementados. Veja o [roadmap](#roadmap).

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

---

## Segurança e privacidade

- O app roda **apenas localmente**. O Streamlit não tem login nativo: se um dia for hospedado online, será preciso
  tratar o acesso público e a persistência do SQLite (hospedagens com disco temporário perdem os dados).
- O banco (`data/*.db`) e o arquivo `.env` ficam **fora do repositório**.
- **LGPD:** o projeto evita dados pessoais por design — não armazena nome, telefone ou documento de clientes,
  apenas dados das ordens de serviço necessários à análise.

---

## Roadmap

- [x] **Etapa 1** — Diagnóstico e estrutura do projeto
- [ ] **Etapa 2** — Banco de dados e regras de negócio
- [ ] **Etapa 3** — Dashboard
- [ ] **Etapa 4** — Engenharia de dados
- [ ] **Etapa 5** — Machine Learning (sobre base SIMULADA até haver histórico real)
- [ ] **Etapa 6** — Testes e CI/CD
- [ ] **Etapa 7** — Validação com a empresa
- [ ] **Etapa 8** — Finalização

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE).
