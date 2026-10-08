#!/usr/bin/env python3
"""Cria um ZIP portátil do projeto sem ambientes e saídas de build."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/insights-brasil-projeto.zip"
EXCLUDED_DIRS = {
    ".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".ipynb_checkpoints", ".tox",
}
EXCLUDED_FILES = {".DS_Store", OUTPUT.name}


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_FILES or path.name.endswith((".pyc", ".pyo", ".tmp")):
        return False
    return path.is_file()


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in ROOT.rglob("*") if should_include(path))
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=7) as archive:
        for path in files:
            archive.write(path, Path("insights") / path.relative_to(ROOT))
    size_mb = OUTPUT.stat().st_size / (1024 * 1024)
    print(f"ZIP criado: {OUTPUT.relative_to(ROOT)}")
    print(f"Arquivos: {len(files)} · Tamanho: {size_mb:.1f} MB")
    print("Excluídos: .venv, .git, node_modules, dist e caches de execução.")


if __name__ == "__main__":
    main()
