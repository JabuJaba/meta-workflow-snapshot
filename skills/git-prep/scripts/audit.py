#!/usr/bin/env python3
# Last verified: 2026-04-19
import sys
import re
import hashlib
import shutil
import argparse
from pathlib import Path
from datetime import datetime

SENSITIVE_PATTERNS = [
    r'password\s*=\s*["\'][^"\']{3,}["\']',
    r'secret\s*=\s*["\'][^"\']{3,}["\']',
    r'api_key\s*=\s*["\'][^"\']{3,}["\']',
    r'token\s*=\s*["\'][^"\']{8,}["\']',
    r'AKIA[0-9A-Z]{16}',
    r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
]

SENSITIVE_FILENAMES = [
    '.env', 'secrets.json', 'secrets.yaml', 'secrets.yml',
    'credentials.json', 'credentials.yaml', 'credentials.yml',
]

SENSITIVE_SUFFIXES = ['.pem', '.key', '.p12', '.pfx']

LARGE_FILE_MB = 10

SCAN_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.yaml', '.yml',
                   '.env', '.cfg', '.ini', '.conf', '.txt', '.toml'}

DEFAULT_BACKUP_EXCLUDES = ['models', 'llama_cpp', '__pycache__', 'logs', '.git', '.delegation']

PROJECT_INDICATORS = {
    'python':   ['*.py', 'requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
    'node':     ['package.json', 'package-lock.json', 'yarn.lock'],
    'data':     ['*.csv', '*.parquet', '*.xlsx', '*.db', '*.sqlite'],
    'ai-infra': ['orchestrator', 'delegation_rules.yaml', '*.gguf', 'llama_cpp'],
}


def backup(target: Path, exclude_dirs=None) -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = target.parent / f"{target.name}_backup_{ts}"
    ignore = shutil.ignore_patterns(*exclude_dirs) if exclude_dirs else None
    shutil.copytree(str(target), str(dst), ignore=ignore)
    return dst


def scan_sensitive(target: Path) -> list[tuple]:
    found = []
    for f in target.rglob('*'):
        if not f.is_file():
            continue
        if f.name.lower() in SENSITIVE_FILENAMES or f.suffix.lower() in SENSITIVE_SUFFIXES:
            found.append(('NOME', str(f.relative_to(target))))
            continue
        if f.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
            for pat in SENSITIVE_PATTERNS:
                if re.search(pat, content, re.IGNORECASE):
                    found.append(('CONTEUDO', str(f.relative_to(target)), pat))
                    break
        except Exception:
            pass
    return found


def scan_large(target: Path) -> list[tuple]:
    found = []
    for f in target.rglob('*'):
        if f.is_file():
            mb = f.stat().st_size / (1024 * 1024)
            if mb > LARGE_FILE_MB:
                found.append((str(f.relative_to(target)), round(mb, 1)))
    return found


def scan_duplicates(target: Path) -> dict:
    hashes: dict[str, list] = {}
    for f in target.rglob('*'):
        if not f.is_file():
            continue
        if f.stat().st_size / (1024 * 1024) > LARGE_FILE_MB:
            continue  # already reported by scan_large; skip to avoid reading GBs into memory
        h = hashlib.md5(f.read_bytes()).hexdigest()
        hashes.setdefault(h, []).append(str(f.relative_to(target)))
    return {h: paths for h, paths in hashes.items() if len(paths) > 1}


def detect_type(target: Path) -> str:
    scores = {k: 0 for k in PROJECT_INDICATORS}
    for ptype, indicators in PROJECT_INDICATORS.items():
        for ind in indicators:
            if list(target.rglob(ind)):
                scores[ptype] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'mixed'


def print_tree(path: Path, prefix='', depth=0, max_depth=3):
    if depth > max_depth:
        return
    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
    for i, item in enumerate(items):
        conn = '+--' if i == len(items) - 1 else '+--'
        print(f"{prefix}{conn} {item.name}")
        if item.is_dir():
            ext = '   ' if i == len(items) - 1 else '|  '
            print_tree(item, prefix + ext, depth + 1, max_depth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--backup-only', action='store_true')
    parser.add_argument('--audit-only', action='store_true',
                        help='Skip backup and .git check — for use on existing git repos')
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"ERRO: Pasta não encontrada: {target}", file=sys.stderr)
        sys.exit(1)

    if not args.audit_only and (target / '.git').exists():
        print("ERRO: Pasta já contém .git — git-prep não deve ser usado aqui.", file=sys.stderr)
        sys.exit(1)

    if not args.audit_only:
        print("=== FASE 1 — BACKUP ===")
        backup_path = backup(target, exclude_dirs=DEFAULT_BACKUP_EXCLUDES)
        print(f"Backup criado em: {backup_path}\n")

        if args.backup_only:
            sys.exit(0)

    print("=== FASE 2 — AUDIT ===\n")

    print("--- Arquivos Sensíveis ---")
    sensitives = scan_sensitive(target)
    if sensitives:
        for item in sensitives:
            if item[0] == 'NOME':
                print(f"  [NOME]     {item[1]}")
            else:
                print(f"  [CONTEUDO] {item[1]}")
    else:
        print("  Nenhum encontrado.")

    print("\n--- Arquivos Grandes (>10MB) ---")
    large = scan_large(target)
    if large:
        for path, mb in large:
            print(f"  {path} ({mb} MB)")
    else:
        print("  Nenhum encontrado.")

    print("\n--- Duplicatas ---")
    dupes = scan_duplicates(target)
    if dupes:
        for h, paths in dupes.items():
            print(f"  [{h[:8]}] {' | '.join(paths)}")
    else:
        print("  Nenhuma encontrada.")

    ptype = detect_type(target)
    print(f"\n--- Tipo de Projeto Detectado ---")
    print(f"  {ptype.upper()}")

    print("\n--- Estrutura Atual ---")
    print_tree(target)

    print(f"\nTIPO_DETECTADO={ptype}")


if __name__ == '__main__':
    main()
