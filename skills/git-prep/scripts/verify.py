#!/usr/bin/env python3
# Last verified: 2026-04-19
import sys
import re
import py_compile
import argparse
from pathlib import Path

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
SENSITIVE_SUFFIXES  = ['.pem', '.key', '.p12', '.pfx']
SCAN_EXTENSIONS     = {'.py', '.js', '.ts', '.json', '.yaml', '.yml',
                       '.env', '.cfg', '.ini', '.conf', '.txt', '.toml'}


def check_python_syntax(target: Path) -> list[tuple[str, str]]:
    errors = []
    for f in target.rglob('*.py'):
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((str(f.relative_to(target)), str(e)))
    return errors


def rescan_sensitive(target: Path) -> list[str]:
    found = []
    for f in target.rglob('*'):
        if not f.is_file():
            continue
        if f.name.lower() in SENSITIVE_FILENAMES or f.suffix.lower() in SENSITIVE_SUFFIXES:
            found.append(str(f.relative_to(target)))
            continue
        if f.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
            for pat in SENSITIVE_PATTERNS:
                if re.search(pat, content, re.IGNORECASE):
                    found.append(str(f.relative_to(target)))
                    break
        except Exception:
            pass
    return found


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
    parser.add_argument('--type', default='mixed')
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"ERRO: Pasta não encontrada: {target}", file=sys.stderr)
        sys.exit(1)

    print("=== FASE 4 — VERIFICAÇÃO PÓS-REORGANIZAÇÃO ===\n")
    errors_found = False

    if args.type in ('python', 'mixed', 'data'):
        print("--- Verificação de Sintaxe Python ---")
        py_errors = check_python_syntax(target)
        if py_errors:
            errors_found = True
            for path, err in py_errors:
                print(f"  ERRO: {path}")
                print(f"        {err}")
        else:
            print("  OK — todos os .py compilam sem erro de sintaxe.")

    print("\n--- Re-scan de Arquivos Sensíveis ---")
    sensitives = rescan_sensitive(target)
    if sensitives:
        errors_found = True
        for path in sensitives:
            print(f"  ALERTA: {path}")
    else:
        print("  OK — nenhum arquivo sensível encontrado.")

    print("\n--- Estrutura Final ---")
    print_tree(target)

    print()
    if errors_found:
        print("RESULTADO: FALHA — corrigir os erros acima antes do git init.")
        sys.exit(1)
    else:
        print("RESULTADO: OK — pronto para git init.")
        sys.exit(0)


if __name__ == '__main__':
    main()
