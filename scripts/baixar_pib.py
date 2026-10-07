"""Baixa e consolida as Contas Nacionais Trimestrais do IBGE via SIDRA."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ibge"
PROCESSED = ROOT / "data" / "processed"
API = "https://apisidra.ibge.gov.br/values"
TABLES = {
    "nominal": ("1846", "585"),
    "volume": ("1620", "583"),
    "rates": ("5932", "6561,6562,6563,6564"),
}

# Códigos publicados pelo IBGE na classificação "Setores e subsetores".
SERIES = {
    "90687": ("agropecuaria", "Agropecuária"),
    "90691": ("industria", "Indústria"),
    "90696": ("servicos", "Serviços"),
    "90707": ("pib", "PIB a preços de mercado"),
    "93404": ("consumo_familias", "Consumo das famílias"),
    "93405": ("consumo_governo", "Consumo da administração pública"),
    "93406": ("formacao_capital", "Formação bruta de capital fixo"),
    "102880": ("variacao_estoques", "Variação de estoques"),
    "93407": ("exportacoes", "Exportações de bens e serviços"),
    "93408": ("importacoes", "Importações de bens e serviços"),
}
RATE_NAMES = {
    "6561": "yoy",
    "6562": "four_quarters",
    "6563": "ytd",
    "6564": "qoq_sa",
}


def fetch(client: httpx.Client, key: str, table: str, variable: str) -> list[dict]:
    url = f"{API}/t/{table}/n1/1/v/{variable}/p/all/c11255/all"
    response = client.get(url)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, list) or not result:
        raise ValueError(f"Resposta vazia/inválida do SIDRA para {key}: {url}")
    header = result[0]
    if "V" not in header or not any("Trimestre" in name for name in header.values()):
        raise ValueError(f"Estrutura inesperada na resposta SIDRA para {key}")
    return result


def observations(raw: list[dict]) -> dict[tuple[str, str], float | None]:
    """Retorna (período YYYYQ, código de série) -> valor, sem depender de D# fixo."""
    header = raw[0]
    dimension_names = {k[:-1]: v for k, v in header.items() if k.endswith("N") and k.startswith("D")}
    period_dim = next((dim for dim, name in dimension_names.items() if "Trimestre" in name), None)
    series_dim = next((dim for dim, name in dimension_names.items() if "Setores e subsetores" in name), None)
    variable_dim = next((dim for dim, name in dimension_names.items() if name == "Variável"), None)
    if not period_dim or not series_dim:
        raise ValueError("SIDRA não informou as dimensões de trimestre e série esperadas")
    output = {}
    for row in raw[1:]:
        period = str(row.get(period_dim + "C", ""))
        code = str(row.get(series_dim + "C", ""))
        if len(period) != 6 or code not in SERIES:
            continue
        value = row.get("V")
        if value in (None, "", "-", "..."):
            parsed_value = None
        else:
            numeric = str(value)
            if "," in numeric and "." in numeric:
                numeric = numeric.replace(".", "").replace(",", ".")
            else:
                numeric = numeric.replace(",", ".")
            parsed_value = float(numeric)
        output[(period, code if variable_dim is None else f"{row[variable_dim + 'C']}:{code}")] = parsed_value
    return output


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    collected = datetime.now(timezone.utc).isoformat(timespec="seconds")
    responses = {}
    with httpx.Client(timeout=90, headers={"User-Agent": "insights-publicos/0.1 (dados abertos)"}) as client:
        for key, (table, variable) in TABLES.items():
            responses[key] = fetch(client, key, table, variable)
            print(f"SIDRA {table}: {len(responses[key]) - 1} observações em {key}")

    raw_snapshot = RAW / f"contas_nacionais_trimestrais_sidra_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    raw_file = RAW / "contas_nacionais_trimestrais_sidra.json"
    raw_content = json.dumps({
        "coletado_em": collected,
        "fonte": "IBGE/SIDRA — Contas Nacionais Trimestrais",
        "urls": {key: f"{API}/t/{table}/n1/1/v/{variable}/p/all/c11255/all" for key, (table, variable) in TABLES.items()},
        "tabelas": {key: table for key, (table, _) in TABLES.items()},
        "respostas": responses,
    }, ensure_ascii=False)
    raw_snapshot.write_text(raw_content, encoding="utf-8")
    shutil.copyfile(raw_snapshot, raw_file)

    nominal, volume, rates = (observations(responses[key]) for key in ("nominal", "volume", "rates"))
    periods = sorted({period for period, _ in nominal})
    rows = []
    for period in periods:
        quarter = int(period[-2:])
        year = int(period[:4])
        row = {"trimestre": f"{year}-T{quarter}", "periodo_sidra": period, "ano": year, "trimestre_numero": quarter, "semestre": 1 if quarter <= 2 else 2}
        for code, (slug, _) in SERIES.items():
            row[f"{slug}_nominal_milhoes"] = nominal.get((period, f"585:{code}"))
            row[f"{slug}_volume_indice"] = volume.get((period, f"583:{code}"))
            for rate_code, rate_slug in RATE_NAMES.items():
                row[f"{slug}_{rate_slug}_percentual"] = rates.get((period, f"{rate_code}:{code}"))
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values("periodo_sidra")
    if frame.empty or frame["pib_nominal_milhoes"].isna().all() or frame["pib_volume_indice"].isna().all():
        raise ValueError("As respostas do SIDRA não contêm PIB nominal e índice de volume")
    frame.to_csv(PROCESSED / "pib_trimestral.csv", index=False)
    print(f"Salvo: {PROCESSED / 'pib_trimestral.csv'} ({len(frame)} trimestres, {frame.trimestre.iloc[0]} a {frame.trimestre.iloc[-1]})")
    print(f"Bruto preservado: {raw_snapshot} · ponteiro mais recente: {raw_file} · coleta UTC {collected}")


if __name__ == "__main__":
    main()
