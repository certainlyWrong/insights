"""Download official SIOP annual execution totals for selected functions."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import httpx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "siop"
PROCESSED = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

ENDPOINT = "https://www1.siop.planejamento.gov.br/sparql/"
LOA = "http://vocab.e.gov.br/2013/09/loa#"
FUNCTIONS = {"06": "Segurança Pública", "10": "Saúde", "12": "Educação"}
PREFIXES = (
    f"PREFIX loa: <{LOA}> "
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
)


def query_for(year: int) -> str:
    return PREFIXES + f"""
SELECT ?codigo ?funcao
       (SUM(?pago) AS ?valor_pago)
       (SUM(?liquidado) AS ?valor_liquidado)
       (SUM(IF(?codigo_gnd = "4", ?pago, 0)) AS ?gnd4_pago)
       (SUM(IF(?codigo_gnd = "4", ?liquidado, 0)) AS ?gnd4_liquidado)
WHERE {{
  GRAPH <http://orcamento.dados.gov.br/{year}/> {{
    ?item a loa:ItemDespesa;
          loa:temFuncao ?funcao_ref;
          loa:valorPago ?pago;
          loa:valorLiquidado ?liquidado;
          loa:temGND ?gnd.
    ?funcao_ref loa:codigo ?codigo; rdfs:label ?funcao.
    ?gnd loa:codigo ?codigo_gnd.
    FILTER(?codigo IN ("06", "10", "12"))
  }}
}}
GROUP BY ?codigo ?funcao
"""


def fetch_year(year: int) -> tuple[int, dict]:
    query = query_for(year)
    params = {"query": query, "format": "application/sparql-results+json"}
    headers = {"Accept": "application/sparql-results+json"}
    for attempt in range(4):
        try:
            response = httpx.get(ENDPOINT, params=params, headers=headers, timeout=180)
            response.raise_for_status()
            return year, response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"Falha ao consultar SIOP para {year}")


def field(binding: dict, key: str) -> str | None:
    value = binding.get(key)
    return value.get("value") if value else None


years = list(range(2001, 2026))
responses: dict[int, dict] = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(fetch_year, year): year for year in years}
    for future in as_completed(futures):
        year, result = future.result()
        responses[year] = result
        print(f"Obtido {year}: {len(result.get('results', {}).get('bindings', []))} funções")

records = []
for year in years:
    bindings = responses[year].get("results", {}).get("bindings", [])
    returned = set()
    for item in bindings:
        code = field(item, "codigo")
        if code not in FUNCTIONS:
            continue
        returned.add(code)
        records.append(
            {
                "ano": year,
                "codigo_funcao": code,
                "funcao": (field(item, "funcao") or FUNCTIONS[code]).strip(),
                "despesa_paga_r$": float(field(item, "valor_pago") or 0),
                "despesa_liquidada_r$": float(field(item, "valor_liquidado") or 0),
                "gnd4_investimento_pago_r$": float(field(item, "gnd4_pago") or 0),
                "gnd4_investimento_liquidado_r$": float(field(item, "gnd4_liquidado") or 0),
            }
        )
    if returned != set(FUNCTIONS):
        raise RuntimeError(f"{year}: funções esperadas {set(FUNCTIONS)}, recebidas {returned}")

raw_file = RAW / "execucao_por_funcao_2001_2025.json"
raw_file.write_text(
    json.dumps(
        {
            "coletado_em": date.today().isoformat(),
            "fonte": ENDPOINT,
            "grafo": "http://orcamento.dados.gov.br/{ano}/",
            "anos": years,
            "codigos_funcao": FUNCTIONS,
            "unidade_original": "R$ correntes",
            "consultas_por_ano": {str(year): query_for(year) for year in years},
            "respostas": responses,
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
pd.DataFrame(records).sort_values(["ano", "codigo_funcao"]).to_csv(
    PROCESSED / "orcamento_saude_seguranca_educacao.csv", index=False
)
print(f"Salvo: {PROCESSED / 'orcamento_saude_seguranca_educacao.csv'} ({len(records)} linhas)")
