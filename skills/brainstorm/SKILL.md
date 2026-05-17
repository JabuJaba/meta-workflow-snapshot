---
name: brainstorm
description: Lightweight brainstorming skill for fuzzy ideas — asks focused discovery questions, synthesizes a concept brief, and suggests (never auto-runs) external research only when the payoff justifies it. Use when user says "/brainstorm", "me ajuda a pensar em X", "tenho uma ideia sobre Y", "quero explorar Z", or when an idea is too early for /project-plan or /sanity-check.
metadata:
  version: 1.0.0
  category: planning
---

# Brainstorm

Lightweight idea exploration. The goal is clarity, not completeness. No external calls by default — research is suggested only when it would materially change the direction.

## Mindset

- **Clarity before depth.** The concept is fuzzy — that's the point. Force premature detail and you'll anchor on the wrong thing.
- **Questions over assumptions.** Every assumption the user carries is a candidate for the first thing to test.
- **Research is optional, not free.** WebSearch and WebFetch cost tokens and time. Suggest them when a 5-minute search would save an hour of wrong direction. Don't suggest them for pure creative divergence.
- **Output serves the next step.** The concept brief is an input to `/project-plan`, `/sanity-check`, or a conversation — not a deliverable in itself.

---

## Phase 0 — Receive the idea (0 external calls)

Read the user's description carefully. Extract:

- **Topic / domain** (what space is this in?)
- **Trigger** (what made the user think of this now?)
- **First instinct** (what do they think the solution looks like?)
- **Ambiguity level**: rate 1-3 (1 = clear problem fuzzy solution, 2 = fuzzy both, 3 = "I have a vibe")

If the message is < 2 sentences and ambiguity = 3, ask one open question before proceeding: *"Conta mais — o que te fez pensar nisso agora?"*

---

## Phase 1 — Discovery questions (0 external calls, max 1 conversational round)

Ask **4 to 6 questions** in a single message. Never more than 6. Choose from the pool below based on what's most unknown — don't ask what the user already answered:

**Problem axis**
- Qual problema concreto isso resolve? Quem o sente?
- O problema existe hoje ou é antecipatório?
- Como as pessoas resolvem isso agora (mesmo que mal)?

**Solution axis**
- Qual é sua hipótese de solução em uma frase?
- O que te faria dizer "isso funcionou"? (Métrica ou sinal concreto)
- O que poderia matar essa ideia antes de começar?

**Context axis**
- Isso é para você, para um usuário, para vender?
- Quanto tempo você toparia investir para validar?
- Já tentou algo parecido antes?

**Frontier axis** (use only if domain is technical or there's a clear prior art angle)
- Você sabe se alguém já fez isso? (Não pesquise — só pergunte)
- Qual é o risco técnico que mais te preocupa?

Format: numbered list, conversational tone, Portuguese.

---

## Phase 2 — Synthesize concept brief (0 external calls)

After receiving answers, write the brief directly — don't ask for more information unless a critical field is still blank.

### Concept Brief — `<slug>`

```
Problema
  [1-2 frases. Problema real, não solução disfarçada.]

Hipótese de solução
  [O que o usuário acredita que poderia funcionar.]

Quem sente o problema
  [Persona ou contexto. "Eu mesmo" é válido.]

Sinal de sucesso
  [Métrica ou evento concreto que indicaria que funcionou.]

O que poderia matar isso
  [Riscos reais: técnicos, de mercado, de esforço, de timing.]

Incógnitas-chave
  [As 2-3 perguntas mais importantes que ainda não têm resposta.]

Nível de maturidade
  [Vibe / Hipótese / Conceito Claro]
```

---

## Phase 3 — Research gate (conditional, suggest only)

After the brief, evaluate **each incógnita-chave** against this gate:

| Critério | Sim → sugere pesquisa | Não → deixa em aberto |
|---|---|---|
| A resposta mudaria a direção do projeto? | ✓ | — |
| Existe uma fonte clara onde buscar (GitHub, papers, notícias de mercado)? | ✓ | — |
| A pesquisa cabe em < 10 min / ~2k tokens? | ✓ | — |
| É pura especulação criativa sem fonte objetiva? | — | ✓ |

**Se 3 critérios = Sim para alguma incógnita**, sugira:

> "Essa incógnita tem resposta buscável. Posso rodar um `/sanity-check` rápido ou uma busca direta — quer que eu faça agora?"

**Se nenhuma incógnita passa o gate**, encerre sem sugerir pesquisa.

Nunca execute WebSearch ou WebFetch sem confirmação explícita do usuário.

---

## Phase 4 — Next step suggestion

Termine com uma linha de sugestão de próximo passo, escolhendo a mais adequada:

- **Maturidade = Vibe**: "Quando tiver mais clareza, `/brainstorm` de novo ou me conta mais."
- **Maturidade = Hipótese**: "Pronto para `/sanity-check` (existe algo parecido?) ou `/project-plan` (como construir?)."
- **Maturidade = Conceito Claro**: "Pode ir direto para `/project-plan` ou `/sprint-generator`."

---

## Output file

Save the concept brief to `brainstorm_<slug>.md` in the **current working directory**.

Slug: lowercase, hyphens, max 4 words derived from the topic. Example: `brainstorm_agente-監控-precos.md`.

Inform the user of the file path after saving.

---

## Token budget guidance

| Phase | Typical cost | Hard limit |
|---|---|---|
| Phase 0–1 (questions) | ~500 tokens | — |
| Phase 2 (brief synthesis) | ~800 tokens | — |
| Phase 3 (gate evaluation) | ~300 tokens | — |
| WebSearch (if confirmed) | ~1,500 tokens/query | 2 queries max |
| WebFetch (if confirmed) | ~2,000 tokens/page | 1 page max |

Total without research: ~1,600 tokens. With research: ~5,600 tokens max.
