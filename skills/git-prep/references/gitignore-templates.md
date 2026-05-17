# Templates de .gitignore por Tipo de Projeto

## Python
```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.env
.env.*
.venv/
venv/
env/
*.log
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

## Python — Data Pipeline
```
__pycache__/
*.py[cod]
.env
.env.*
.venv/
venv/
*.log
.pytest_cache/
data/raw/
data/processed/
*.csv
*.parquet
*.xlsx
*.db
*.sqlite
```

## Node/JS
```
node_modules/
dist/
build/
.env
.env.*
*.log
coverage/
.DS_Store
```

## Mixed / Geral
```
.env
.env.*
*.log
__pycache__/
*.py[cod]
node_modules/
dist/
build/
data/raw/
*.csv
*.parquet
.DS_Store
```

## ai-infra
```
# modelos e binários de inferência: models/, *.gguf, *.ggml (nunca versionar — GBs)
models/
*.gguf
*.ggml
llama_cpp/
*.dll
*.zip

# runtime e logs
logs/
__pycache__/
*.py[cod]

# artefatos de sessão
handoffs/
benchmarks/*.json
benchmark/*.json

# env
.env
.env.*
```

## Delegation framework (incluir em todos os templates)
Sempre anexar ao final do `.gitignore` gerado, independente do tipo de projeto:
```
# Delegation framework — não versionar artefatos volumosos
.delegation/deliveries/

# Versionar verdicts e sprints (auditoria)
!.delegation/verdicts/
!.delegation/sprints/
```
