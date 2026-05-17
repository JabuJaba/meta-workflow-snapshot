#!/usr/bin/env python3
# Last verified: 2026-04-30
import sys
import shutil
import argparse
from pathlib import Path

CANONICAL_STRUCTURES = {
    'python': {
        'src':     'código fonte principal (.py)',
        'scripts': 'CLIs e scripts utilitários',
        'tests':   'testes (pytest)',
        'data':    'dados (adicionar ao .gitignore se grande)',
        'docs':    'documentação',
    },
    'node': {
        'src':     'código fonte',
        'public':  'assets estáticos',
        'tests':   'testes',
        'scripts': 'scripts utilitários',
    },
    'data': {
        'src':             'código de pipeline',
        'data/raw':        'dados brutos (não modificar)',
        'data/processed':  'outputs do pipeline',
        'notebooks':       'Jupyter notebooks exploratórios',
        'scripts':         'scripts de ingestão/ETL',
        'tests':           'testes',
    },
    'mixed': {
        'src':     'código fonte',
        'scripts': 'scripts variados',
        'data':    'dados',
        'docs':    'documentação',
        'tests':   'testes',
    },
    'ai-infra': {
        'orchestrator': 'núcleo de roteamento e delegação',
        'scripts':      'CLIs utilitários',
        'benchmark':    'suítes de benchmark',
        'tests':        'testes automatizados',
        'sprints':      'sprint docs',
        'backlog':      'backlog e artefatos',
        'docs':         'documentação',
    },
}


def compute_moves(target: Path, ptype: str) -> list[tuple[Path, Path, str]]:
    moves = []

    # Loose .py files in root → src/ (skip for ai-infra: CLIs live at root by design)
    if ptype != 'ai-infra':
        skip_root_py = {'setup.py', 'conftest.py', 'manage.py'}
        for f in target.glob('*.py'):
            if f.name not in skip_root_py:
                dst = target / 'src' / f.name
                if f != dst:
                    moves.append((f, dst, 'arquivo Python solto -> src/'))

    # Test files not already in tests/
    for f in target.rglob('test_*.py'):
        if 'tests' not in f.relative_to(target).parts:
            moves.append((f, target / 'tests' / f.name, 'arquivo de teste -> tests/'))

    # Notebooks not already in notebooks/
    for f in target.rglob('*.ipynb'):
        if 'notebooks' not in f.relative_to(target).parts:
            moves.append((f, target / 'notebooks' / f.name, 'notebook -> notebooks/'))

    # Data files in root -> data/raw/
    if ptype in ('data', 'mixed', 'python'):
        for ext in ('*.csv', '*.parquet', '*.xlsx', '*.db', '*.sqlite'):
            for f in target.glob(ext):
                moves.append((f, target / 'data' / 'raw' / f.name, 'arquivo de dados -> data/raw/'))

    # Deduplicate: skip if src == dst
    return [(s, d, r) for s, d, r in moves if s != d]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--type', required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("ERRO: informe --dry-run ou --execute", file=sys.stderr)
        sys.exit(1)

    target = Path(args.target)
    if not target.exists():
        print(f"ERRO: Pasta não encontrada: {target}", file=sys.stderr)
        sys.exit(1)

    ptype = args.type
    structure = CANONICAL_STRUCTURES.get(ptype, CANONICAL_STRUCTURES['mixed'])

    print("=== ESTRUTURA CANÔNICA PROPOSTA ===")
    for folder, desc in structure.items():
        print(f"  {folder}/ — {desc}")

    moves = compute_moves(target, ptype)

    print(f"\n=== MOVES PROPOSTOS ({len(moves)}) ===")
    if not moves:
        print("  Nenhum arquivo precisa ser movido.")
    for src, dst, reason in moves:
        print(f"  {src.relative_to(target)} -> {dst.relative_to(target)}  ({reason})")

    if args.dry_run:
        print("\n[DRY-RUN] Nenhuma alteração feita.")
        sys.exit(0)

    if args.execute:
        print("\n=== EXECUTANDO REORGANIZAÇÃO ===")
        # Create canonical dirs
        for folder in structure:
            (target / folder).mkdir(parents=True, exist_ok=True)

        moved_log: list[tuple[Path, Path]] = []  # (dst, src) for rollback
        try:
            for src, dst, reason in moves:
                if not src.exists():
                    print(f"  AVISO: arquivo não encontrado (pulando): {src.name}")
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                moved_log.append((dst, src))
                print(f"  Movido: {src.relative_to(target)} -> {dst.relative_to(target)}")
        except Exception as exc:
            print(f"\n  ERRO durante reorganização: {exc}", file=sys.stderr)
            print("  Revertendo moves executados...", file=sys.stderr)
            for dst_f, src_f in reversed(moved_log):
                if dst_f.exists():
                    shutil.move(str(dst_f), str(src_f))
                    print(f"  Revertido: {dst_f.name}", file=sys.stderr)
            sys.exit(1)

        print(f"\nReorganizacao concluida. {len(moved_log)} arquivo(s) movido(s).")


if __name__ == '__main__':
    main()
