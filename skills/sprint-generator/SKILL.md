---
name: sprint-generator
description: Gera próximo sprint doc (sprints/sprint_N.md) a partir do contexto — lê spec.md/constraints.md/handoff/checkpoint e propõe phases com deliverables e acceptance quantitativa. Use "/sprint-generator", "gerar próxima sprint", "plan sprint N+1", "próxima sprint". Não use para projeto novo (use /project-plan) ou executar sprint (use /sprint-execute).
metadata:
  version: 1.1.0
  category: project-management
---

# Sprint Generator

When the user invokes /sprint-generator, generate the next sprint doc from existing project context.

**Flags:**
- `--ok` — skip approval gate and write the file immediately after drafting.

**Phase cap:** maximum 5 phases per sprint. If the scope requires more, apply the split rule below.

## Phase 1 — Read Project Context

Before asking anything, read the following files from the current working directory:

**Required (abort with clear error if missing):**
- `spec.md` — project goal, success criteria, scope IN/OUT, sprint table
- `constraints.md` — environment, allowed models, known gotchas

**State files (read all that exist, skip gracefully if absent):**
- `.checkpoint.json` — last completed phase, metrics, sprint number
- `handoff_sprint*.md` — read the most recent one (highest N or latest date)
- `sprints/sprint_*.md` — glob all, determine highest N to calculate next sprint number

**Project rules:**
- `CLAUDE.md` — field names, encoding rules, source-of-truth hierarchy

If `spec.md` or `constraints.md` are missing, stop and tell the user:
```
Não encontrei spec.md / constraints.md. Este projeto foi planejado com /project-plan?
Se sim, verifique o diretório. Se não, use /project-plan primeiro.
```

## Phase 2 — Assess Current State

After reading, synthesize:

1. **Sprint atual**: qual sprint foi a última? (do checkpoint ou handoff)
2. **O que foi entregue**: resumo do handoff — fases concluídas, métricas
3. **O que ficou pendente**: itens abertos do handoff "Next Steps" e "Open Decisions"
4. **Blockers conhecidos**: "State Warning" do handoff, se houver
5. **Próximo sprint número**: N+1 (verificar se `sprints/sprint_N+1.md` já existe — se existir, avisar e perguntar se quer sobrescrever)
6. **Escopo restante**: confrontar o que foi feito com o `spec.md` — o que do escopo IN ainda não foi entregue?

## Phase 3 — Draft Sprint

Com base no contexto, gerar internamente o sprint completo.

### Regra de split (cap = 5 phases)

Contar as phases que o escopo exigiria:

- **≤ 5 phases**: incluir todas na sprint N+1.
- **> 5 phases**: incluir apenas as primeiras 5 phases (priorizadas por dependência e valor) na sprint N+1. As phases excedentes vão para a seção "Backlog sprint N+2" no rodapé do arquivo gerado. Na próxima execução de /sprint-generator, esse backlog é incorporado automaticamente como escopo inicial da sprint N+2.

### Modo interativo (sem `--ok`)

Apresentar o draft para aprovação:

```
## Sprint N+1 draft — aguardando aprovação

**Arquivo**: sprints/sprint_<N+1>.md
**Objetivo**: [derivado do escopo restante do spec.md]

**Phases propostas** (<X> de <total proposto> — cap 5):

  Phase 1 — [Nome]
    Entregável: [artefato concreto]
    Acceptance: [verificação quantitativa — ex: "N/N testes, 0 erros"]

  Phase 2 — [Nome]
    Entregável: [...]
    Acceptance: [...]

  [...]

**Critérios de Aceite da Sprint**:
  - [ ] [critério derivado do spec.md]
  - [ ] [critério de qualidade / integridade]

**Dependências**: Sprint <N> concluída — [estado confirmado via handoff]

**Itens pendentes incorporados** (do handoff anterior):
  - [item de "Next Steps" não concluído → alocado em Phase X]

[Se split aplicado:]
**Overflow para sprint N+2** (phases excedentes não incluídas):
  - Phase 6 — [Nome]: [descrição curta]
  - Phase 7 — [Nome]: [descrição curta]

Quer ajustar fases, renomear, adicionar critérios ou mudar ordem?
```

Itere com o usuário até aprovação explícita, depois ir para Phase 4.

### Modo `--ok`

Gerar o draft internamente sem exibir para aprovação. Aplicar split se necessário (silenciosamente). Ir direto para Phase 4.

## Phase 4 — Write File

Escrever `sprints/sprint_<N+1>.md` neste formato exato:

```markdown
# Sprint <N+1> — <Nome>

## Objetivo
<O que essa sprint entrega — derivado do spec.md>

## Phases

### Phase 1: <Nome>
**Entregável**: <artefato concreto>
**Acceptance**: <verificação quantitativa>

### Phase 2: <Nome>
**Entregável**: <artefato concreto>
**Acceptance**: <verificação quantitativa>

## Critérios de Aceite da Sprint
- [ ] <critério 1>
- [ ] <critério 2>

## Dependências
- Sprint <N> concluída
- <qualquer outra dependência identificada>

## Itens Pendentes do Sprint Anterior
- <itens do handoff anterior incorporados nesta sprint, com Phase de destino>

## Backlog Sprint N+2
<!-- Gerado automaticamente por split — incorporar na próxima execução de /sprint-generator -->
- <Phase excedente 1>: <descrição curta>
- <Phase excedente 2>: <descrição curta>

_Gerado por /sprint-generator em <data ISO>_
```

Omitir a seção "Backlog Sprint N+2" se não houve split.

## Phase 5 — Handoff

Após escrever o arquivo, exibir:

```
Sprint <N+1> criada: sprints/sprint_<N+1>.md

Phases: <N>/5 | Critérios de aceite: <N>
[Se split:] Overflow: <M> phases movidas para Backlog sprint N+2

Execute /sprint-execute para iniciar.
```

## Regras

- Sem `--ok`, exigir aprovação explícita antes de escrever o arquivo
- Com `--ok`, escrever diretamente sem pedir aprovação
- Acceptance criteria devem ser sempre quantitativos ("139/139 testes", "0 erros", "N/N rows") — nunca vagos ("funciona corretamente")
- Se o handoff tem "Open Decisions" não resolvidas, incluir como itens de Phase 1 ou bloquear com aviso
- Se o escopo restante do spec.md está vazio (tudo entregue), avisar: "Spec.md não tem itens IN pendentes — o projeto pode estar concluído. Quer criar uma sprint de hardening/docs?"
- Não duplicar conteúdo já entregue nas sprints anteriores
- Incorporar gotchas do CLAUDE.md como notas nas phases relevantes (sem embedar no corpo principal)
- Ao ler contexto de uma sprint anterior, verificar seção "Backlog Sprint N+2" e incorporar como escopo prioritário da nova sprint antes de derivar do spec.md
