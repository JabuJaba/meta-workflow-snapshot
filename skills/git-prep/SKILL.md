---
name: git-prep
description: Prepara pasta sem versionamento para git em 5 fases com gates — backup, audit (sensíveis/grandes/duplicatas), reorganização dry-run, verificação, git init. Use "preparar para virar git", "transformar essa pasta em git", "inicializar git". Flag --audit-only roda só audit em projeto já git. Não use em pasta já git sem --audit-only.
metadata:
  version: 1.1.0
  category: project-management
---

# git-prep

Prepara uma pasta não-versionada para virar um repositório git em 5 fases com gates de aprovação explícita entre elas. Nunca pule um gate — cada aprovação é obrigatória.

**Idempotente**: re-execução em pasta já git é segura — a skill detecta `.git` e sai com exit 0 sem efeito colateral (ou roda só audit com `--audit-only`).

## Como usar

```
/git-prep                                # skill asks for the path
/git-prep ~/projects/my-project
/git-prep ~/projects/my-project --audit-only   # audit-only, even in an already-git project
```

Se o usuário não fornecer o caminho, perguntar: "Qual o caminho completo da pasta?"

---

## Early-return — Pasta já versionada

**Antes de qualquer fase**, verificar se a pasta já tem `.git`:

```bash
git -C "{target_path}" rev-parse --git-dir 2>/dev/null
```

**Se retornar exit code 0 (já é repositório git):**

- Se o usuário passou `--audit-only`: pular para a **Fase 2 (Audit)** diretamente — não rodar Fase 1 (backup) nem Fase 5 (git init). Avisar: "Projeto já versionado. Rodando apenas audit (--audit-only)." Chamar o script **com flag adicional**: `python ~/.claude/skills/git-prep/scripts/audit.py "{target_path}" --audit-only`
- Caso contrário: informar "Pasta já contém um repositório git (.git detectado). Use --audit-only para rodar apenas o audit, ou /git-publish para publicar no GitHub." e **sair — exit 0, sem nenhuma modificação**.

**Se retornar exit code diferente de 0 (não é repositório git):**
Continuar normalmente pelas 5 fases abaixo.

---

## Fase 1 — Backup

Antes de qualquer ação, criar backup timestamped:

```bash
python ~/.claude/skills/git-prep/scripts/audit.py --backup-only "{target_path}"
```

Confirmar ao usuário: `Backup criado em: {backup_path}` e só então continuar.

---

## Fase 2 — Audit (read-only, nada é movido)

```bash
python ~/.claude/skills/git-prep/scripts/audit.py "{target_path}"
```

Apresentar o relatório completo retornado pelo script, incluindo:
- Arquivos sensíveis detectados (por nome e por conteúdo)
- Arquivos grandes (>10MB)
- Duplicatas (hash MD5 idêntico)
- Tipo de projeto detectado (python/node/data/mixed)
- Árvore de estrutura atual

### GATE 1 — Aprovação obrigatória
Perguntar: "Relatório acima. Confirma que posso prosseguir para a reorganização?"
**Aguardar confirmação explícita antes de continuar. Não assumir aprovação.**

*Se rodando com `--audit-only`: após apresentar o relatório, encerrar aqui — não prosseguir para Fase 3.*

---

## Fase 3 — Reorganização

### 3a — Dry-run (nada é movido)

```bash
python ~/.claude/skills/git-prep/scripts/reorganize.py --dry-run "{target_path}" --type "{detected_type}"
```

Apresentar ao usuário:
- Estrutura canônica proposta para o tipo detectado
- Lista exata de moves/renames que serão feitos

### GATE 2 — Aprovação obrigatória
Perguntar: "Dry-run acima. Confirma que posso executar a reorganização?"
**Aguardar confirmação explícita antes de continuar. Não assumir aprovação.**

### 3b — Execução

```bash
python ~/.claude/skills/git-prep/scripts/reorganize.py --execute "{target_path}" --type "{detected_type}"
```

Após execução, gerar `.gitignore` na raiz da pasta usando o template correspondente ao tipo detectado (ver `~/.claude/skills/git-prep/references/gitignore-templates.md`).

O template gerado deve **sempre incluir** as regras do delegation framework ao final:

```
# Delegation framework — não versionar artefatos volumosos
.delegation/deliveries/

# Versionar verdicts e sprints (auditoria)
!.delegation/verdicts/
!.delegation/sprints/
```

---

## Fase 4 — Verificação pós-reorganização

```bash
python ~/.claude/skills/git-prep/scripts/verify.py "{target_path}" --type "{detected_type}"
```

O script verifica:
- **Python/mixed**: `py_compile` em todos os `.py` para checar sintaxe
- **Re-scan de sensíveis**: garantia que nenhum arquivo sensível ficou exposto após moves
- **Árvore final**: estrutura resultante

**Se o script retornar exit code 1 (erros encontrados): parar imediatamente e reportar os erros. Não continuar para o git init.**

---

## Fase 5 — Git Init

Somente após Fase 4 com exit code 0:

```bash
git -C "{target_path}" init
git -C "{target_path}" add --dry-run .
```

Apresentar a lista de arquivos que entrariam no staging. Confirmar visualmente que nenhum sensível está incluso.

### GATE 3 — Aprovação obrigatória
Perguntar: "Arquivos acima entrarão no commit inicial. Confirma o git init e primeiro commit?"
**Aguardar confirmação explícita.**

Após confirmação:

```bash
git -C "{target_path}" add .
git -C "{target_path}" commit -m "chore: initial commit — estrutura organizada via git-prep"
```

Reportar sucesso com o hash do commit.

---

## Troubleshooting

- **`python` não encontrado**: tentar `python3`; se falhar, pedir ao usuário para verificar o PATH
- **Permissão negada ao mover arquivos**: fechar IDEs/editores que possam ter os arquivos abertos
- **py_compile falha**: erro legítimo de sintaxe — reportar o arquivo e linha, não ignorar
- **Backup falha por espaço em disco**: backup é obrigatório; informar ao usuário e interromper
- **git não encontrado**: instalar Git e verificar PATH antes de continuar
- **Script retorna exit 1 na Fase 4**: não continuar para git init — corrigir os erros primeiro

---

## Exemplos de uso

```
/git-prep ~/projects/scraper-a
/git-prep ~/projects/pipeline-b
/git-prep ~/projects/already-git-project --audit-only   ← already a git repo; audit only
/git-prep                                                ← skill asks for the path
```

---

## Referências

- Estruturas canônicas: `~/.claude/skills/git-prep/references/canonical-structures.md`
- Templates .gitignore: `~/.claude/skills/git-prep/references/gitignore-templates.md`
