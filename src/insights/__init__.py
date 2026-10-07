"""Explore and collect official Brazilian public data."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Sequence

from .catalog import DATASETS, get_dataset
from .ingest import download, parse_params
from .storage import database_path, latest_runs


def _catalog(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps([dataset.__dict__ for dataset in DATASETS], ensure_ascii=False, indent=2))
        return 0
    print("Catálogo de dados públicos brasileiros\n")
    for dataset in DATASETS:
        state = "disponível" if dataset.connector else "planejado"
        print(f"{dataset.id} [{state}] — {dataset.title}")
        print(f"  Tema: {dataset.theme} | Órgão: {dataset.publisher}")
        print(f"  Acesso: {dataset.access}")
        print(f"  Formato: {dataset.format} | Versão: {dataset.source_version}")
        print(f"  Licença/termos: {dataset.license_terms}")
        print(f"  Fonte: {dataset.url}")
    return 0


def _fetch(args: argparse.Namespace) -> int:
    try:
        dataset = get_dataset(args.dataset)
    except KeyError:
        print(f"Conjunto desconhecido: {args.dataset}. Use 'insights catalog'.", file=sys.stderr)
        return 2
    try:
        params = parse_params(args.param)
        count, source_url = download(dataset, params, max_pages=args.max_pages)
    except (ValueError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Coleta concluída: {dataset.id} — {count} registros")
    print(f"Fonte: {source_url}")
    print("Os dados foram gravados em DuckDB; cópia bruta e proveniência em .insights/.")
    return 0


def _status(_: argparse.Namespace) -> int:
    runs = latest_runs()
    print(f"Banco local: {database_path()}")
    if not runs:
        print("Nenhuma coleta registrada.")
        return 0
    for dataset_id, finished, state, count, pages, raw_path, start, end, query_params, source_version, error in runs:
        timestamp = finished.isoformat() if isinstance(finished, datetime) else str(finished)
        period = f" | período: {start}–{end}" if start or end else ""
        print(f"{dataset_id}: {state}, {count} registros, {pages} página(s), {timestamp}{period}")
        if query_params:
            print(f"  Filtros: {query_params}")
        if source_version:
            print(f"  Versão da fonte: {source_version}")
        if raw_path:
            print(f"  Cópia bruta: {raw_path}")
        if error:
            print(f"  Erro: {error}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="insights",
        description="Catálogo e coleta local de dados públicos brasileiros.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    catalog = commands.add_parser("catalog", help="lista os conjuntos catalogados")
    catalog.add_argument("--json", action="store_true", help="imprime metadados em JSON")
    catalog.set_defaults(handler=_catalog)

    for name, help_text in (
        ("fetch", "baixa um conjunto de dados"),
        ("update", "baixa novamente um conjunto e atualiza o banco local"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("dataset", help="identificador listado por 'insights catalog'")
        command.add_argument(
            "--param", action="append", default=[], metavar="NOME=VALOR",
            help="filtro da API; pode ser informado mais de uma vez",
        )
        command.add_argument(
            "--max-pages", type=int, default=2,
            help="limite de páginas por coleta (1–100; padrão: 2)",
        )
        command.set_defaults(handler=_fetch)

    status = commands.add_parser("status", help="mostra a última coleta de cada conjunto")
    status.set_defaults(handler=_status)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
