# Estruturas Canônicas por Tipo de Projeto

## Python (geral)
```
src/              código fonte principal (.py)
scripts/          CLIs e scripts utilitários
tests/            testes (pytest)
data/             dados (adicionar ao .gitignore se arquivo grande)
docs/             documentação
requirements.txt
README.md
```

## Python (data pipeline)
```
src/              código de pipeline e transformações
data/raw/         dados brutos (geralmente no .gitignore)
data/processed/   outputs do pipeline
notebooks/        Jupyter notebooks exploratórios
scripts/          scripts de ingestão/ETL
tests/
requirements.txt
README.md
```

## Node/JS
```
src/              código fonte
public/           assets estáticos
tests/
scripts/          utilitários
package.json
README.md
```

## Mixed / Geral
```
src/              código fonte
scripts/          scripts variados
data/             dados
docs/             documentação
tests/
README.md
```

## ai-infra
```
orchestrator/     núcleo de roteamento e delegação (versionar)
scripts/          CLIs utilitários (versionar)
benchmark/        suítes de benchmark — código (versionar)
tests/            testes automatizados (versionar)
sprints/          sprint docs (versionar)
backlog/          backlog.yaml e artefatos (versionar)
docs/             documentação (versionar)
models/           pesos GGUF — no .gitignore (NÃO versionar)
llama_cpp/        binários de inferência — no .gitignore (NÃO versionar)
handoffs/         artefatos de handoff — no .gitignore (NÃO versionar)
logs/             logs de execução — no .gitignore (NÃO versionar)
```
