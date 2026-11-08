# AGENTS.md — CG CELL REPAIR
## Dashboard Inteligente para Gestão e Análise de Dados de Assistência Técnica

> Este arquivo contém as regras permanentes do projeto. Leia-o integralmente antes de qualquer tarefa.
> Cada tarefa enviada no chat indicará qual etapa executar. Execute somente essa etapa.

---

## 0. PAPEL E OBJETIVO

Atue como engenheiro de software sênior, engenheiro de dados e cientista de dados especializado em Machine Learning, arquitetura de aplicações e boas práticas de desenvolvimento.

O projeto faz parte da graduação em Análise e Desenvolvimento de Sistemas. Ele também deve servir de portfólio para estágios em Engenharia de Dados, Ciência de Dados, IA/ML, Desenvolvimento Python, Business Intelligence e Engenharia de Software.

O objetivo é demonstrar conhecimento técnico real, não apenas uma interface bonita. Quem desenvolve precisa conseguir explicar tecnicamente cada parte em uma entrevista de estágio.

---

## 1. CONTEXTO DO AMBIENTE

- Pasta do projeto: `$HOME\Documents\systenRepair` (pasta Documentos do usuário, subpasta `systenRepair`). Se não existir, criar.
- Repositório GitHub: **ainda não existe**. Nome sugerido: `cgcell-dashboard-inteligente`.
- Usuário GitHub: `Chiebao`
- Sistema: **Windows 11 Pro**, terminal **PowerShell**.
- Python 3.12: instalado (confirmar com `python --version` na Etapa 1).
- Git: instalado (confirmar com `git --version` na Etapa 1).
- O Codex roda **localmente no PC do usuário**, que acompanha as mudanças nos arquivos ao vivo. Todos os comandos são executados e explicados em PowerShell.
- O usuário é iniciante em terminal: **todo comando deve vir explicado (o que faz e por quê)**. Não assumir conhecimento prévio nem passos que não foram ensinados.

### O que é publicado e onde
- O **código** será público no GitHub.
- O **app** (Streamlit) roda **localmente** no PC (`streamlit run`). O GitHub não hospeda a aplicação em funcionamento; hospedagem online está fora do escopo por enquanto.

### Permissões do agente no Git/GitHub
- Pode executar comandos Git locais: `init`, criar branches, `add`, `commit`, `push` (se as credenciais já estiverem configuradas).
- Criar o repositório no site do GitHub e abrir/mesclar Pull Requests: **o usuário faz pelo navegador**, com o agente guiando passo a passo.
- Antes de cada comando Git, explicar o que ele faz.

---

## 2. CONTEXTO DO NEGÓCIO

O projeto foi planejado nas Experiências Práticas II e III da disciplina Projeto de Software.

A empresa parceira é a CG CELL Repair, assistência técnica de celulares em Sorocaba-SP.

A empresa já possui um sistema de ordens de serviço. A solução **não substitui** esse sistema: é uma ferramenta complementar de gestão e análise de dados.

**Problema:** facilitar a visualização e interpretação de informações gerenciais, como faturamento recebido, volume de OS, serviços mais frequentes e evolução dos indicadores no tempo.

**Público principal:** gestor ou responsável pela CG CELL Repair.

**Objetivo de longo prazo:** evoluir de um dashboard gerencial para uma solução com Machine Learning que identifique padrões históricos e gere previsões úteis ao planejamento.

**Dados históricos reais:**
- **Não há histórico disponível.** O sistema de OS atual não exporta dados.
- Consequências:
  - Os dados reais entrarão pelo cadastro manual (e, futuramente, por importação de CSV).
  - Desde o início, o módulo de ML será desenvolvido sobre **base SIMULADA**, identificada como tal em todo lugar.
  - A avaliação real do modelo fica condicionada ao acúmulo de histórico suficiente (critério definido na Etapa 5).

**Prazos acadêmicos:**
- **17/11/2026:** o projeto precisa estar no GitHub, em estado funcional e organizado.
- O professor, por enquanto, exige apenas o projeto publicado no GitHub. O desenvolvimento continua depois dessa data.
- Rodadas de validação: datas a definir com o usuário (não antes da Etapa 3 concluída).

**Prioridade até 17/11:** Etapas 1, 2 e 3 concluídas e publicadas, com README apresentável. As Etapas 4 a 8 seguem depois, sem prazo fixo.

**Regra absoluta:** não invente entrevistas, informações da empresa, participantes, datas, resultados, métricas ou integrações que não foram confirmados por mim.

---

## 3. STACK TECNOLÓGICA

### Base (obrigatória)
- Python 3.12: linguagem principal.
- Streamlit: interface web.
- Pandas: manipulação e transformação de dados.
- Plotly: visualizações interativas.
- SQLite: banco relacional inicial.

### Complementares (usar quando justificável)
- Scikit-learn: modelos de ML.
- NumPy: operações numéricas.
- Pytest: testes automatizados.
- Git e GitHub: versionamento.
- GitHub Actions: integração contínua.
- SQL: consultas e análise.
- Ruff: análise estática e padronização.
- Pre-commit: verificações antes dos commits.
- SHAP ou Permutation Importance: somente se houver modelo treinado que supere o baseline. Para modelos de árvore, prefira começar por Permutation Importance.

### Fora do escopo
- MLflow: não utilizar. O tamanho do projeto não justifica.

Não instale bibliotecas só para aumentar a lista do README. Justifique cada ferramenta.

### Gestão de dependências
- Usar `requirements.txt` com versões fixas (ou `pyproject.toml`, se justificado).
- Separar dependências de execução e de desenvolvimento (ex.: `requirements-dev.txt`).

---

## 4. ARQUITETURA

Arquitetura modular em camadas:

1. **Apresentação:** interface Streamlit.
2. **Serviços:** regras de negócio e operações.
3. **Dados:** conexão e persistência SQLite.
4. **Análise:** tratamento de dados e indicadores.
5. **Machine Learning:** treinamento, avaliação e previsão.
6. **Testes:** unitários e de integração.

Requisitos:
- Código organizado, reutilizável, legível e de fácil manutenção.
- Nada de aplicação inteira em um único arquivo.
- Estrutura que permita evolução sem reescrever o sistema.
- Interface não acessa o banco diretamente: passa pela camada de serviços.

### Convenções
- Nomes de variáveis, funções, tabelas e arquivos: **português**, sem acentos (snake_case). Termos técnicos consagrados podem ficar em inglês (ex.: `baseline`, `test_`).
- Mensagens de commit: em português, no padrão semântico.
- Comentários e docstrings: em português.

---

## 5. MODELAGEM DO BANCO DE DADOS

### OrdemServico
- `id_ordem_servico`: chave primária.
- `codigo_os`: texto obrigatório e único.
- `data_abertura`: data obrigatória.
- `data_conclusao`: data opcional.
- `valor_servico`: inteiro em centavos, não negativo.
- `status_os`: aberta, em andamento, concluída ou cancelada.
- `status_pagamento`: pendente ou pago.
- `data_pagamento`: data opcional.
- `id_tipo_servico`: chave estrangeira.
- `origem_registro`: manual, importado ou simulado. Permite separar e rotular dados simulados em todos os indicadores e gráficos.
- `excluida`: booleano (exclusão lógica), padrão falso.
- `excluida_em`: data e hora da exclusão lógica, opcional.
- `criado_em`: data e hora de criação do registro.
- `atualizado_em`: data e hora da última alteração.

### TipoServico
- `id_tipo_servico`: chave primária.
- `nome_servico`: texto obrigatório e único.
- `descricao`: texto opcional.
- `ativo`: booleano obrigatório.

**Relacionamento:** um tipo de serviço pode estar associado a várias OS (1:N).

### Regras gerais
- Identificadores únicos.
- Impedir códigos de OS duplicados.
- Validar campos obrigatórios.
- Consultas SQL sempre parametrizadas.
- Integridade referencial ativa (`PRAGMA foreign_keys = ON`).
- Valores monetários em centavos (inteiros).
- Datas armazenadas em formato ISO (AAAA-MM-DD).
- Não armazenar dados pessoais de clientes desnecessários para a análise.
- Tipo de serviço desativado não aparece para novas OS, mas continua válido nas OS antigas.

### Regras de consistência entre campos
- `status_pagamento = pago` exige `data_pagamento` preenchida.
- `status_pagamento = pendente` exige `data_pagamento` vazia.
- `data_conclusao` só pode ser preenchida quando `status_os = concluída`.
- `data_conclusao` e `data_pagamento` não podem ser anteriores a `data_abertura`.
- OS cancelada **não pode** ter pagamento: `status_os = cancelada` exige `status_pagamento = pendente` e `data_pagamento` vazia.
- `valor_servico = 0` **é permitido** (garantia ou retorno). Essas OS contam no volume, mas não alteram o faturamento.

### Edição de OS
- Permitida enquanto a OS estiver **aberta** ou **em andamento**.
- Com status **concluída** e pagamento **pendente**: só é permitido registrar o pagamento (status e data).
- Com status **concluída e paga** (finalizada e entregue): **bloqueada** para edição.
- Com status **cancelada**: bloqueada para edição.
- Toda edição atualiza `atualizado_em`.

### Exclusão de OS
- Somente **exclusão lógica** (`excluida = verdadeiro`). O registro nunca é apagado do banco.
- Permitida apenas para OS com **mais de 3 meses (90 dias) desde a `data_abertura`**.
- OS excluídas não aparecem nas listagens nem entram em nenhum indicador ou no treinamento do modelo.
- Não há exclusão física pela aplicação.

### Evolução do banco
- Criar uma estratégia simples de migração versionada (scripts numerados), para alterar o esquema sem perder dados.
- Banco persistente, com estratégia de backup e recuperação documentada.

---

## 6. FUNCIONALIDADES DO MVP

### Cadastro de tipos de serviço
Cadastrar, consultar, ativar e desativar.

### Cadastro de ordens de serviço
Registrar manualmente, com validação e associação ao tipo de serviço. Edição e exclusão conforme as regras da seção 5.

### Dashboard gerencial
Exibir:
- Faturamento recebido.
- Quantidade de OS.
- Serviços mais frequentes.
- Distribuição dos status.
- Evolução do faturamento.
- Evolução do volume de atendimentos.
- Filtros por período.

### Regras de cálculo
- Faturamento recebido considera **somente OS pagas**.
- **Faturamento recebido filtra por `data_pagamento`.**
- **Volume de OS filtra por `data_abertura`.**
- OS canceladas não contam como serviços concluídos.
- Todos os indicadores respeitam o período selecionado.
- Não confundir valor de serviços realizados com valor efetivamente recebido.
- Faturamento **não é lucro**: o projeto não registra custo de peças, portanto não calcula margem. Deixar isso explícito na interface e na documentação.
- OS com exclusão lógica nunca entram nos indicadores.
- Dados com `origem_registro = simulado` devem ser identificados visualmente como **SIMULADOS** e poder ser filtrados (mostrar apenas reais / apenas simulados / todos).

### Exibição (padrão brasileiro)
- Datas: DD/MM/AAAA.
- Moeda: R$ 1.234,56.
- Armazenamento continua em ISO e centavos; a conversão acontece só na apresentação.

### Importação de CSV (complementar)
- Implementar somente depois das funcionalidades obrigatórias.
- Validar os dados antes de inserir.
- Impedir duplicidades.
- Gerar relatório de linhas aceitas e rejeitadas, com o motivo.

---

## 7. MACHINE LEARNING — PREVISÃO INTELIGENTE DE DESEMPENHO

Não é um chatbot. É uma funcionalidade de ML demonstrável, treinável e avaliada por métricas.

### O módulo deve estimar, quando houver dados suficientes
- Volume futuro de OS.
- Tendência de faturamento recebido.
- Comportamento da demanda por período.
- Variações na procura por tipo de serviço, se houver histórico suficiente.

### Metodologia (antes de treinar)
1. Análise exploratória.
2. Quantidade de registros.
3. Período histórico disponível.
4. Valores ausentes e inconsistências.
5. Sazonalidade e tendências.
6. Frequência de agregação mais adequada.
7. Avaliação se os dados realmente permitem treinamento.

### Modelos candidatos
- Baseline simples (ex.: média móvel ou valor do período anterior).
- Regressão linear, quando apropriada.
- Random Forest Regressor.
- HistGradientBoostingRegressor.
- Modelos estatísticos de séries temporais, quando fizer sentido.

Não escolha algoritmo por fama. Compare e justifique.

### Validação
- Separação temporal, respeitando a ordem cronológica.
- Proibido usar divisão aleatória para avaliar previsões temporais.
- Métricas: MAE, RMSE e MAPE (este só quando os valores permitirem, sem zeros ou valores muito pequenos).
- Comparar sempre com o baseline, em tabela, com análise escrita.
- Não declarar que o modelo é bom sem demonstrar superioridade ou utilidade frente ao baseline.

### Dados insuficientes (situação atual confirmada)
- Hoje **não existe histórico real**. O módulo começa obrigatoriamente em modo SIMULADO.
- Criar um script de geração de base sintética, reproduzível (semente fixa), que grave registros com `origem_registro = simulado`.
- Definir um critério técnico de quantidade mínima de dados, considerando a frequência e a complexidade do modelo.
- Não inventar desempenho.
- Não apresentar dados sintéticos como reais.
- Permitir base sintética **somente** para demonstração técnica, identificada como **SIMULADA** em todo lugar (interface, gráficos, README).
- Explicar que a avaliação real depende de histórico suficiente.

### Interpretabilidade
- Explicar as variáveis mais relevantes com técnica apropriada, quando houver modelo treinado.
- Importância de variável não é causalidade: deixar isso explícito.
- Não apresentar explicações que os dados não sustentam.

### Interface de IA (seção própria no dashboard)
- Indicador de disponibilidade do modelo.
- Período usado no treinamento.
- Data do último treinamento.
- Modelo selecionado.
- Métricas de avaliação.
- Comparação com o baseline.
- Gráfico de histórico e previsão.
- Avisos de limitação e confiabilidade.
- Distinção visual clara entre dado histórico, previsão e dado simulado.

---

## 8. ENGENHARIA DE DADOS

Fluxo reproduzível:
1. Entrada manual ou importação.
2. Validação.
3. Limpeza.
4. Transformação.
5. Persistência.
6. Análise.
7. Geração de indicadores.
8. Preparação dos dados para ML.

Requisitos:
- Código de preparação separado do código de treinamento.
- Funções reutilizáveis para: tratamento de datas, valores ausentes, validação de registros, agregação por período, agregação por tipo de serviço e preparação de variáveis para o modelo.
- Documentar as regras de transformação.
- Evitar vazamento de dados (data leakage): nenhuma variável pode usar informação do futuro em relação à data prevista.

---

## 9. TESTES E QUALIDADE (Pytest)

### Unitários
Cálculo de faturamento, contagem de OS, serviços mais frequentes, validação de datas, validação de valores, tratamento de pagamentos, regras de cancelamento, regras de consistência entre campos, filtro por data correta (pagamento vs. abertura), preparação dos dados e funções de avaliação dos modelos.

### Integração
Conexão SQLite, criação das tabelas, cadastro e consulta de tipos de serviço, cadastro e consulta de OS, integridade do relacionamento, persistência e fluxos principais.

### Machine Learning
Verificação dos dados de entrada, separação temporal, treinamento, avaliação, comparação com baseline, prevenção de vazamento de dados e comportamento com histórico insuficiente.

### Regras
- Bancos temporários nos testes.
- Nunca alterar o banco da aplicação durante os testes.
- Dados de teste sempre fictícios.

---

## 10. GITHUB E VERSIONAMENTO

- Repositório público e organizado.
- Commits semânticos (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `refactor:`, `chore:`).
- Uma branch por funcionalidade e Pull Request para integrar na principal, mesmo havendo uma única pessoa desenvolvendo.
- Auto-revisão técnica descrita em cada PR.
- Histórico de evolução documentado.
- Licença: **MIT** (arquivo `LICENSE` na raiz, titular: Chiebao).

Exemplos de commits:
- `feat: implementa cadastro de ordens de serviço`
- `feat: adiciona dashboard gerencial`
- `test: adiciona testes dos indicadores`
- `fix: corrige cálculo do faturamento`
- `docs: atualiza documentação do projeto`
- `ci: configura pipeline de testes`

GitHub Actions deve executar: instalação das dependências, Ruff, testes automatizados e verificações básicas de qualidade.

---

## 11. SEGURANÇA E PRIVACIDADE

- Nunca publicar senhas, tokens ou credenciais.
- Configurações sensíveis em variáveis de ambiente (com `.env.example` sem valores reais).
- Nenhum dado real de cliente no GitHub.
- Arquivo do banco SQLite fora do repositório (no `.gitignore`).
- Consultas SQL parametrizadas.
- Validação de todas as entradas.
- Proteção das operações de escrita.
- Documentar as limitações de autenticação (o Streamlit não tem login nativo).
- O app roda apenas localmente. Documentar que, caso venha a ser hospedado online no futuro, será preciso tratar acesso público (sem login nativo) e persistência do SQLite (hospedagens com disco temporário perdem os dados).
- Nota sobre LGPD no README: o projeto evita dados pessoais por design.
- Documentar backup e recuperação.
- Não declarar que o sistema é seguro sem testes e evidências.

---

## 12. DOCUMENTAÇÃO PARA PORTFÓLIO

1. README.md completo.
2. Problema e solução.
3. Arquitetura da aplicação.
4. Diagrama do banco de dados.
5. Diagrama do fluxo de dados.
6. Tecnologias e justificativas.
7. Instalação (Windows/PowerShell).
8. Execução.
9. Como rodar os testes.
10. Documentação do modelo de ML.
11. Resultados reais dos experimentos, quando disponíveis.
12. Limitações conhecidas.
13. Capturas de tela (somente com dados fictícios).
14. Roadmap.

Seção de portfólio: problema resolvido, tecnologias, decisões técnicas, como a IA foi treinada e avaliada, métricas obtidas, limitações e melhorias possíveis.

Não inventar resultados ou experiências profissionais.

---

## 13. VALIDAÇÃO COM A EMPRESA

Mínimo de duas rodadas com representante externo.

**Primeira rodada:** facilidade de acesso, cadastro de OS, consulta dos indicadores, compreensão dos gráficos e utilidade das informações. Registrar dificuldades e feedbacks reais.

**Segunda rodada (após ajustes):** repetir as tarefas principais, verificar se as dificuldades anteriores foram resolvidas, registrar novos comentários e comparar as duas rodadas.

Preparar roteiro e formulário de registro para cada rodada.

Não inventar participantes, datas, resultados ou comentários. Nenhuma rodada é considerada realizada sem minha confirmação.

---

## 14. ETAPAS DE EXECUÇÃO

**ETAPA 1 — Diagnóstico e estrutura:** verificar o que já existe, organizar pastas, configurar Python e dependências, criar README, .gitignore e aplicação inicial, preparar GitHub.

**ETAPA 2 — Banco de dados e regras de negócio:** SQLite, tabelas, migração inicial, CRUD necessário, validações e regras de consistência, testes iniciais.

**ETAPA 3 — Dashboard:** interface Streamlit, integração com serviços, indicadores, gráficos, filtros, cadastro e consulta.

**ETAPA 4 — Engenharia de dados:** pipeline de tratamento, análise exploratória, preparação para análise e treinamento, documentação das transformações.

**ETAPA 5 — Machine Learning:** avaliar disponibilidade e qualidade dos dados, baseline, modelos candidatos, validação temporal, comparação de métricas, previsões na interface (se houver evidência), limitações e interpretabilidade.

**ETAPA 6 — Testes e CI/CD:** completar testes unitários, de integração e de IA, configurar Ruff, pre-commit e GitHub Actions, PRs e revisão técnica.

**ETAPA 7 — Validação externa:** preparar a primeira rodada, registrar feedbacks reais, corrigir, preparar a segunda rodada, comparar.

**ETAPA 8 — Finalização:** revisão de código e de segurança, documentação, organização do repositório, evidências e apresentação para faculdade e portfólio.

### Cronograma
- **Até 17/11/2026:** Etapas 1, 2 e 3 concluídas e publicadas no GitHub, com README apresentável.
- **Depois de 17/11:** Etapas 4 a 8, em sequência, sem prazo fixo.
- Se alguma parte das Etapas 1 a 3 ameaçar o prazo, avisar e propor o que cortar ou adiar, antes de implementar.

### Critério de pronto de cada etapa
Uma etapa só está pronta quando:
- [ ] Tudo o que foi pedido na etapa está implementado.
- [ ] O código roda no Windows seguindo as instruções entregues.
- [ ] Os testes da etapa passam.
- [ ] O Ruff não aponta erros (a partir da Etapa 6, ou antes, se já configurado).
- [ ] O README foi atualizado com o que mudou.
- [ ] Nenhum dado real ou credencial foi incluído.
- [ ] O relatório de entrega (seção 15) foi apresentado.

---

## 15. REGRAS DE TRABALHO E FORMATO DE ENTREGA

Quem desenvolve é estudante de ADS e quer aprender durante o processo. Portanto:

1. Execute **somente** a etapa indicada na tarefa. Ao terminar, **pare**.
2. Não pule etapas nem antecipe funcionalidades de etapas futuras.
3. Não altere decisões já estabelecidas sem explicar o motivo.
4. Não invente dados reais nem apresente métricas fictícias como comprovadas.
5. Se uma funcionalidade for complexa ou desnecessária para o MVP, justifique **antes** de implementar.
6. Verifique imports e dependências antes de entregar.
7. Priorize qualidade, clareza, reprodutibilidade e evidências técnicas.

### Relatório obrigatório ao final de cada etapa
1. **Resumo:** o que foi feito, em poucas linhas.
2. **Arquivos criados e alterados:** caminho de cada um e sua função.
3. **Decisões técnicas:** o que foi escolhido e por quê.
4. **Como executar:** comandos em PowerShell, explicando o que cada comando faz e por que é necessário.
5. **Como testar:** passo a passo, incluindo o que deve aparecer na tela quando der certo.
6. **Erros prováveis:** mensagem de erro, causa e como corrigir.
7. **Commit e PR sugeridos:** nome da branch, mensagens de commit e descrição do PR.
8. **Pendências e decisões que precisam da minha aprovação.**
9. **Checklist do critério de pronto** (seção 14), marcado.
