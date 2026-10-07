"""Normalize official Receita Federal and Tesouro tax collection workbooks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "tributos"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

MONTHS = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAIO": 5, "JUN": 6,
          "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}


def monthly_archive() -> pd.DataFrame:
    path = RAW / "arrecadacao_receitas_federais_1994_2025.xlsx"
    rows = []
    for year in range(1994, 2026):
        frame = pd.read_excel(path, sheet_name=str(year), header=None)
        total = frame[frame.iloc[:, 0].astype(str).str.contains("TOTAL GERAL", case=False, na=False)]
        if total.empty:
            raise ValueError(f"Linha TOTAL GERAL ausente na aba {year}")
        values = total.iloc[0, 1:13].tolist()
        for month_number, amount in enumerate(values, 1):
            if pd.notna(amount):
                rows.append({"data": f"{year}-{month_number:02d}", "arrecadacao_total_federal_milhoes": float(amount)})
    return pd.DataFrame(rows)


def latest_monthly() -> pd.DataFrame:
    path = RAW / "arrecadacao_federal_2026_ate_agosto.xlsx"
    frame = pd.read_excel(path, sheet_name="Tabela III", header=None)
    rows = []
    year = 2021
    for _, row in frame.iloc[7:].iterrows():
        label = str(row.iloc[0]).strip().upper()
        if label.startswith("JAN-"):
            digits = "".join(char for char in label if char.isdigit())
            if digits:
                year = int(digits) + 1
            continue
        if label in MONTHS:
            rows.append({
                "data": f"{year}-{MONTHS[label]:02d}",
                "arrecadacao_rfb_administrada_milhoes": float(row.iloc[7]),
                "arrecadacao_outros_orgaos_milhoes": float(row.iloc[8]),
                "arrecadacao_total_federal_milhoes": float(row.iloc[9]),
            })
    if not rows or max(row["data"] for row in rows) < "2026-08":
        raise ValueError("A tabela mensal atual da Receita Federal não chegou a agosto de 2026")
    return pd.DataFrame(rows)


def general_tax_burden() -> pd.DataFrame:
    path = RAW / "carga_tributaria_governo_geral_2025.xlsx"
    frame = pd.read_excel(path, sheet_name="Tabela 1", header=None)
    years = [int(float(value)) for value in frame.iloc[3, 1:17]]
    rows = []
    names = {"Governo Geral": "governo_geral", "Governo Central": "governo_central",
             "Governos Estaduais": "governos_estaduais", "Governos Municipais": "governos_municipais"}
    for idx in range(4, 12):
        label = str(frame.iloc[idx, 0]).strip()
        key = names.get(label)
        if not key:
            continue
        is_ratio = idx >= 8
        for col, year in enumerate(years, 1):
            row = next((item for item in rows if item["ano"] == year), None)
            if row is None:
                row = {"ano": year}
                rows.append(row)
            field = f"{key}_percentual_pib" if is_ratio else f"{key}_milhoes"
            value = frame.iloc[idx, col]
            row[field] = float(value) * (100 if is_ratio else 1) if pd.notna(value) else None
    return pd.DataFrame(rows).sort_values("ano")


def main() -> None:
    historical = monthly_archive()
    latest = latest_monthly()
    monthly = pd.concat([historical[historical["data"] < "2021-01"], latest], ignore_index=True)
    monthly["ano"] = monthly["data"].str[:4].astype(int)
    monthly["mes"] = monthly["data"].str[5:7].astype(int)
    monthly.to_csv(OUT / "arrecadacao_federal_mensal.csv", index=False, float_format="%.6f")
    general_tax_burden().to_csv(OUT / "carga_tributaria_governo_geral_anual.csv", index=False, float_format="%.6f")
    print(f"Arrecadação federal mensal: {len(monthly)} meses, {monthly.data.min()} a {monthly.data.max()}")
    print("Carga tributária geral anual: 2010 a 2025")


if __name__ == "__main__":
    main()
