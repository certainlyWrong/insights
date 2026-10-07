"""Normalize official debt source files into analysis-ready monthly tables."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def month_label(value: object) -> pd.Timestamp | None:
    match = re.fullmatch(r"\s*([A-Za-z]{3})/(\d{2,4})\s*", str(value))
    if not match:
        return None
    month = MONTHS.get(match.group(1).lower())
    year = int(match.group(2))
    if year < 100:
        year += 2000
    return pd.Timestamp(year=year, month=month, day=1) if month else None


def pivot_sheet(path: Path, sheet: str, header_row: int, unit: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    dates = [(col, month_label(raw.iloc[header_row, col])) for col in range(1, raw.shape[1])]
    dates = [(col, date) for col, date in dates if date is not None]
    rows = []
    for index, label in enumerate(raw.iloc[:, 0]):
        if pd.isna(label) or not str(label).strip():
            continue
        name = str(label).strip()
        if name.startswith(("ANEXO", "Obs", "¹", "2 ")):
            continue
        for col, date in dates:
            value = pd.to_numeric(raw.iloc[index, col], errors="coerce")
            if pd.notna(value):
                rows.append((date, name, float(value)))
    result = pd.DataFrame(rows, columns=["data", "indicador", "valor"])
    result["valor_r_bilhoes"] = result["valor"] if unit == "R$ bilhões" else result["valor"] / 1000
    return result[["data", "indicador", "valor_r_bilhoes"]].sort_values(["data", "indicador"])


stock = pivot_sheet(RAW / "tesouro" / "estoque-dpf-resumo.xlsx", "2.1", 4, "R$ bilhões")
stock.to_csv(OUT / "dpf_estoque_mensal.csv", index=False, date_format="%Y-%m-%d")

factors = pivot_sheet(RAW / "tesouro" / "fatores-variacao-dpf.xlsx", "2.9", 6, "R$ milhões")
factors.to_csv(OUT / "dpf_fatores_mensais.csv", index=False, date_format="%Y-%m-%d")

flows = pivot_sheet(RAW / "tesouro" / "emissoes-resgates-dpf.xlsx", "1.1", 4, "R$ milhões")
flows.to_csv(OUT / "dpf_emissoes_resgates_mensal.csv", index=False, date_format="%Y-%m-%d")

detail = pd.read_csv(
    RAW / "tesouro" / "estoquedpf.csv",
    sep=";",
    encoding="utf-8-sig",
    decimal=",",
    thousands=".",
)
detail["data"] = pd.to_datetime(detail["Mes do Estoque"], format="%m/%Y")
detail["valor_r_bilhoes"] = detail["Valor do Estoque"] / 1_000_000_000
detail["vencimento"] = pd.to_datetime(
    detail["Vencimento do Titulo/Contrato"], format="%d/%m/%Y", errors="coerce"
)
detail["ano_vencimento"] = detail["vencimento"].dt.year.astype("Int64")
detail.to_csv(
    OUT / "dpf_posicoes_por_titulo.csv.gz",
    index=False,
    compression="gzip",
    date_format="%Y-%m-%d",
)
holdings = (
    detail.groupby(["data", "Classe da Carteira", "Tipo de Divida"], as_index=False)["valor_r_bilhoes"]
    .sum()
    .rename(columns={"Classe da Carteira": "classe_carteira", "Tipo de Divida": "tipo_divida"})
)
holdings.to_csv(OUT / "dpf_estoque_detalhado.csv", index=False, date_format="%Y-%m-%d")

def bcb_series(filename: str, name: str) -> pd.DataFrame:
    records = json.loads((RAW / "bcb" / filename).read_text(encoding="utf-8"))
    frame = pd.DataFrame(records)
    return pd.DataFrame(
        {
            "data": pd.to_datetime(frame["data"], format="%d/%m/%Y"),
            name: pd.to_numeric(frame["valor"], errors="coerce"),
        }
    )


bcb = bcb_series("dbgg_pib.json", "dbgg_percentual_pib")
bcb = bcb.merge(bcb_series("divida_liquida_gg_pib.json", "dlgg_percentual_pib"), on="data", how="outer")
bcb = bcb.merge(bcb_series("ipca_mensal.json", "ipca_variacao_mensal_percentual"), on="data", how="outer")
bcb.sort_values("data").to_csv(OUT / "bcb_divida_ipca_mensal.csv", index=False, date_format="%Y-%m-%d")

print(
    f"DPF: {stock['data'].min():%Y-%m} a {stock['data'].max():%Y-%m} "
    f"({stock['data'].nunique()} meses); detalhes: {detail['data'].min():%Y-%m} "
    f"a {detail['data'].max():%Y-%m} ({detail['data'].nunique()} meses)"
)
print(f"Fatores: {factors['data'].min():%Y-%m} a {factors['data'].max():%Y-%m}")
print(f"Emissões/resgates: {flows['data'].min():%Y-%m} a {flows['data'].max():%Y-%m}")
print(f"BCB DBGG/PIB: {bcb['data'].min():%Y-%m} a {bcb['data'].max():%Y-%m}")
