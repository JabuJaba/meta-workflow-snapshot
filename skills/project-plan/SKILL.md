---
name: project-plan
description: Plans a new project by generating spec.md, constraints.md, and sprint files after a discovery interview. Use when user says "/project-plan", "plan this project", "create sprints for", "let's plan the implementation", or "I want to start a new project". Do NOT use for continuing an existing sprint — use sprint-execute instead.
metadata:
  version: 1.0.0
  category: project-management
---

# Project Plan

When the user invokes /project-plan, follow this protocol exactly.

## 1. Discovery Phase

Ask all questions in a single message — do not drip them one by one:

1. **Objetivo**: O que esse projeto deve entregar? Qual o critério de sucesso quantificável?
2. **Escopo**: O que está IN e o que está OUT? Quais funcionalidades são MVP vs. nice-to-have?
3. **Restrições técnicas**: Ambiente (OS, venv, Docker?), modelos permitidos (local Ollama only? corporate?), autenticação (Azure AD, APIs externas?), encoding, dependências críticas.
4. **Complexidade estimada**: Quantas sprints imagina? `1-2` simples / `3-5` médio / `6+` complexo — ou deixe em aberto.
5. **Contexto existente**: Tem código, schema, CLAUDE.md ou arquivos de referência relevantes? Liste os caminhos.

Aguarde as respostas antes de continuar.

## 2. Context Read (before generating anything)

- Read `CLAUDE.md` if it exists in the working directory
- Read any files referenced by the user in step 1
- Glob `sprints/` to detect sprints existentes e evitar conflito de numeração
- Read `spec.md` e `constraints.md` se já existirem (projeto sendo replanejado)

## 3. Draft & Approval Gate

Gere internamente o plano completo e apresente um **resumo para aprovação**:

```
## Plano gerado — aguardando aprovação

**Spec**: [goal em 1 linha] | Critério: [métrica]
**Fora do escopo**: [lista]
**Sprints**: N sprints planejadas
  - Sprint 1 — [nome]: [phases resumidas]
  - Sprint 2 — [nome]: [phases resumidas]
  ...
**Constraints**: [top 3 restrições críticas]

Quer ajustar algo antes de eu escrever os arquivos?
```

Itere com o usuário até aprovação explícita. Só então escreva os arquivos.

## 4. Generate Artifacts

Após aprovação, escreva os 3 tipos de artefato:

### spec.md (raiz do projeto)

```markdown
# Spec — [Nome do Projeto]

## Objetivo
[O que deve ser entregue e por quê]

## Critério de Sucesso
[Métrica quantificável — ex: "704/704 linhas processadas, 0 erros"]

## Escopo
### IN
- [item]

### OUT
- [item]

## Sprints
| Sprint | Nome | Objetivo |
|--------|------|----------|
| 1 | [nome] | [objetivo] |

_Gerado por /project-plan em [data ISO]_
```

### constraints.md (raiz do projeto)

```markdown
# Constraints — [Nome do Projeto]

## Ambiente
- OS / shell: [...]
- Python / venv: [...]
- Encoding: [...]

## Modelos Permitidos
- [ex: apenas Ollama local — qwen2.5-coder, llama3.1]

## Autenticação & APIs Externas
- [ex: Azure AD — public-client-flow, scope Files.ReadWrite.All]

## Gotchas Conhecidos
- [campo crítico, convenção de pasta, armadilha de encoding, etc.]

_Gerado por /project-plan em [data ISO]_
```

### sprints/sprint_N.md (uma por sprint)

```markdown
# Sprint N — [Nome]

## Objetivo
[O que essa sprint entrega]

## Phases

### Phase 1: [Nome]
**Entregável**: [artefato concreto]
**Acceptance**: [verificação quantitativa — ex: "0 erros, N/N testes"]

### Phase 2: [Nome]
**Entregável**: [...]
**Acceptance**: [...]

## Critérios de Aceite da Sprint
- [ ] [critério 1]
- [ ] [critério 2]

## Dependências
- [ex: Sprint 1 concluída / schema validado / auth configurado]
```

## 5. Scaffold Infrastructure Folders

Após escrever os arquivos de planejamento, criar as pastas de infraestrutura das skills — são agnósticas ao tipo de projeto e sempre necessárias:

```
sprints/                      # já criado ao escrever os sprint docs
handoffs/                     # session-close
.delegation/verdicts/         # fit-evaluator, sprint-generator-unified
.delegation/sprints/          # fit-evaluator, sprint-generator-unified
```

Usar `New-Item -ItemType Directory -Force` (PowerShell) para cada pasta, garantindo idempotência. Criar um `.gitkeep` vazio em cada pasta vazia para que o git as rastreie.

Não criar estrutura canônica de código (`src/`, `data/`, `scripts/`, etc.) — isso é responsabilidade do `/git-prep` que detecta o tipo de projeto.

## 6. Post-Generation Handoff

Após escrever todos os arquivos, exiba:

```
Arquivos gerados:
  spec.md
  constraints.md
  sprints/sprint_1.md
  [sprints/sprint_2.md ...]

Pastas criadas:
  handoffs/
  .delegation/verdicts/
  .delegation/sprints/

Próximos passos:
  1. /git-prep   — organiza estrutura canônica do código e faz git init
  2. /sprint-execute sprints/sprint_1.md   — inicia a Sprint 1
```

Não execute nada além de escrita de arquivos. A execução é responsabilidade do /sprint-execute.
