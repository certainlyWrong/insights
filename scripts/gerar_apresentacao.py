#!/usr/bin/env python3
"""Executa o notebook de gráficos e gera a apresentação PDF sem código."""

from __future__ import annotations

import base64
import contextlib
import io
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import nbformat


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/estudo_graficos_politicas_publicas.ipynb"


def main() -> None:
    if not NOTEBOOK.exists():
        raise SystemExit(f"Notebook de apresentação não encontrado: {NOTEBOOK}")

    notebook = nbformat.read(NOTEBOOK, as_version=4)
    namespace: dict[str, object] = {"__name__": "__main__"}
    execution_count = 0

    for index, cell in enumerate(notebook.cells, start=1):
        if cell.cell_type != "code":
            continue
        execution_count += 1
        outputs = []

        def display_figure(figure) -> None:
            image = io.BytesIO()
            figure.savefig(image, format="png", dpi=85, facecolor=figure.get_facecolor())
            png = base64.b64encode(image.getvalue()).decode("ascii")
            outputs.append(nbf_output(png))

        namespace["display"] = display_figure
        source = "\n".join(
            line for line in cell.source.splitlines()
            if line.strip() != "%matplotlib inline"
        )
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(source, f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
        except Exception as exc:
            raise SystemExit(
                f"Falha ao executar a célula {index} de {NOTEBOOK.name}: {exc}"
            ) from exc
        if stdout.getvalue():
            outputs.insert(0, nbformat.v4.new_output("stream", name="stdout", text=stdout.getvalue()))
        if stderr.getvalue():
            outputs.append(nbformat.v4.new_output("stream", name="stderr", text=stderr.getvalue()))
        cell.outputs = outputs
        cell.execution_count = execution_count

    # Mantém as figuras no notebook para leitura direta no Jupyter.
    nbformat.write(notebook, NOTEBOOK)
    pdf = ROOT / "artifacts/apresentacao_insights_brasil.pdf"
    if not pdf.exists() or pdf.stat().st_size < 10_000:
        raise SystemExit("O notebook terminou sem produzir o PDF esperado.")
    print(f"Notebook executado: {NOTEBOOK.relative_to(ROOT)}")
    print(f"PDF completo: {pdf.relative_to(ROOT)} ({pdf.stat().st_size / 1024:.0f} KB)")


def nbf_output(png: str) -> dict:
    return nbformat.v4.new_output(
        "display_data", data={"image/png": png, "text/plain": "<Figura matplotlib>"}, metadata={}
    )


if __name__ == "__main__":
    main()
