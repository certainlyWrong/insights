"""Baixa e normaliza séries do IPCA relacionadas a alimentos (IBGE/SIDRA e BCB)."""

from __future__ import annotations

import json
import gzip
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ibge"
PROCESSED = ROOT / "data" / "processed"
SIDRA = "https://apisidra.ibge.gov.br/values"
BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
SIDRA_TABLES = ("655", "2938", "1419", "7060")
REGIONAL_AGGREGATES = ("7169", "7170", "7171", "7432", "7433")
REGIONAL_LEVELS = ("n6", "n7")  # municípios e regiões metropolitanas
BCB_SERIES = {
    "ipca_geral": "433",
    "ipca_alimentacao": "1635",
}
FIELD_NAMES = {
    "7169": "Índice geral",
    "7170": "Alimentação e bebidas",
    "7171": "Alimentação no domicílio",
    "7432": "Alimentação fora do domicílio",
    "7433": "Alimentação fora do domicílio (subgrupo)",
}


def parse_number(value: Any) -> float | None:
    if value in (None, "", "..", "...", "-", "X"):
        return None
    return float(str(value).replace(",", "."))


def request_json(client: httpx.Client, url: str, *, sleep_seconds: float = 0.12) -> Any:
    """GET JSON with bounded retries, modest pacing, and clear malformed-response errors."""
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = client.get(url)
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise ValueError(f"Resposta não é JSON válido: {url}") from exc
            time.sleep(sleep_seconds)
            if not isinstance(payload, (list, dict)) or not payload:
                raise ValueError(f"Resposta vazia ou inesperada: {url}")
            return payload
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(0.35 * (2**attempt))
    raise RuntimeError(f"Falha ao consultar a fonte após 4 tentativas: {last_error}") from last_error


def sidra_url(table: str, *, level: str, variables: str, periods: str, categories: str) -> str:
    return f"{SIDRA}/t/{table}/{level}/v/{variables}/p/{periods}/c315/{categories}"


def validate_sidra(payload: Any, url: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[0], dict):
        raise ValueError(f"Resposta SIDRA sem observações ou cabeçalho inválido: {url}")
    header = " ".join(str(value) for value in payload[0].values()).lower()
    if "variável" not in header or "mês" not in header or "geral, grupo" not in header:
        raise ValueError(f"Cabeçalho SIDRA incompatível com séries mensais: {url}")
    return payload


def variable_map(payload: list[dict[str, Any]]) -> dict[str, str]:
    return {
        key[:-1]: str(value)
        for key, value in payload[0].items()
        if key.startswith("D") and key.endswith("N")
    }


def parse_sidra_rows(payload: list[dict[str, Any]], table: str, *, level: str) -> list[dict[str, Any]]:
    dims = variable_map(payload)
    header = payload[0]
    geo_code_key = next((key for key, name in header.items() if key.startswith("D") and key.endswith("C") and name.endswith("(Código)") and "Mês" not in name and "Variável" not in name and "Geral, grupo" not in name), None)
    geo_name_key = geo_code_key[:-1] + "N" if geo_code_key else None
    period_dim = next((key[:-1] for key, name in header.items() if key.endswith("N") and name.lower() == "mês"), None)
    variable_dim = next((key[:-1] for key, name in header.items() if key.endswith("N") and name.lower() == "variável"), None)
    category_dim = next((key[:-1] for key, name in header.items() if key.endswith("N") and "geral, grupo" in name.lower()), None)
    if not all((geo_code_key, geo_name_key, period_dim, variable_dim, category_dim)):
        raise ValueError(f"Dimensões SIDRA não identificadas para tabela {table}: {header}")

    records: list[dict[str, Any]] = []
    for source_row in payload[1:]:
        period_code = str(source_row.get(period_dim + "C", ""))
        if not re.fullmatch(r"\d{6}", period_code):
            continue
        period = f"{period_code[:4]}-{period_code[4:]}"
        category_code = str(source_row.get(category_dim + "C", ""))
        category_label = str(source_row.get(category_dim + "N", "")).strip()
        category_path, _, category_name = category_label.partition(".")
        category_name = category_name.strip()
        if not category_name:
            category_name = category_label
            category_path = ""
        variable_code = str(source_row.get(variable_dim + "C", ""))
        value = parse_number(source_row.get("V"))
        records.append({
            "periodo": period,
            "territorio_codigo": str(source_row.get(geo_code_key, "")),
            "territorio": str(source_row.get(geo_name_key, "")),
            "nivel_territorial": level,
            "classificacao_codigo": category_code,
            "classificacao_caminho": category_path,
            "classificacao": category_name,
            "variavel_codigo": variable_code,
            "valor": value,
            "tabela_sidra": table,
        })
    return records


def parse_bcb(payload: Any, series_code: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Série SGS {series_code} vazia ou malformada")
    result = []
    for row in payload:
        try:
            period = datetime.strptime(row["data"], "%d/%m/%Y").strftime("%Y-%m")
            value = parse_number(row["valor"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"Observação inválida na série SGS {series_code}: {row}") from exc
        result.append({"periodo": period, "valor": value, "serie_sgs": series_code})
    return result


def is_food_category(row: dict[str, Any]) -> bool:
    path = str(row.get("classificacao_caminho", ""))
    label = str(row.get("classificacao", "")).lower()
    return path.startswith("1") or label.startswith("alimentação")


def is_food_leaf(row: dict[str, Any]) -> bool:
    path = str(row.get("classificacao_caminho", ""))
    return is_food_category(row) and len(path) >= 7 and path[:2] in {"11", "12"}


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Index source observations by series and calculate rolling/annual rates from monthly values."""
    keys = ("territorio_codigo", "classificacao_codigo")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if row["variavel_codigo"] != "63":
            continue
        grouped.setdefault(tuple(row[key] for key in keys), []).append(row)

    result: list[dict[str, Any]] = []
    for series_rows in grouped.values():
        series_rows.sort(key=lambda row: row["periodo"])
        for index, row in enumerate(series_rows):
            current = row["valor"]
            year = int(row["periodo"][:4])
            month = int(row["periodo"][5:7])
            year_rows = [candidate for candidate in series_rows[:index + 1] if candidate["periodo"][:4] == row["periodo"][:4]]
            prev12 = series_rows[index - 12:index] if index >= 12 else []
            last12 = series_rows[index - 11:index + 1] if index >= 11 else []
            contiguous12 = len(last12) == 12 and all(
                (pd.Period(last12[pos]["periodo"], freq="M") - pd.Period(last12[pos - 1]["periodo"], freq="M")).n == 1
                for pos in range(1, 12)
            )
            prior_contiguous = len(prev12) == 12 and all(
                (pd.Period(prev12[pos]["periodo"], freq="M") - pd.Period(prev12[pos - 1]["periodo"], freq="M")).n == 1
                for pos in range(1, 12)
            )
            row["acumulado_ano_percentual"] = (
                ((pd.Series([1 + r["valor"] / 100 for r in year_rows if r["valor"] is not None]).prod() - 1) * 100)
                if len(year_rows) == month and year_rows[-1] is row and all(r["valor"] is not None for r in year_rows) else None
            )
            row["variacao_12_meses_percentual"] = (
                ((pd.Series([1 + r["valor"] / 100 for r in last12 if r["valor"] is not None]).prod() - 1) * 100)
                if contiguous12 and all(r["valor"] is not None for r in last12) else None
            )
            row["variacao_mes_ano_anterior_percentual"] = row["variacao_12_meses_percentual"]
            result.append(row)
    return result


def deduplicate_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one revised observation for each published series and month."""
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in items:
        identity = (row["periodo"], row["territorio_codigo"], row["classificacao_codigo"], row["variavel_codigo"])
        unique[identity] = row
    return list(unique.values())


def normalize_all(raw_responses: dict[str, list[dict[str, Any]]], bcb_responses: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    national_rows: list[dict[str, Any]] = []
    regional_rows: list[dict[str, Any]] = []
    leaf_codes: set[str] = set()
    for table in SIDRA_TABLES:
        national = parse_sidra_rows(raw_responses[f"{table}_national"], table, level="Brasil")
        national_rows.extend(row for row in national if is_food_category(row) or row["classificacao_codigo"] == "7169")
        if table == "7060":
            leaf_codes = {row["classificacao_codigo"] for row in national if is_food_leaf(row)}
        regional = parse_sidra_rows(raw_responses[f"{table}_regions"], table, level="área IPCA")
        regional_rows.extend(row for row in regional if row["classificacao_codigo"] in REGIONAL_AGGREGATES)
        if table == "7060" and leaf_codes:
            for key in ("7060_n6_items", "7060_n7_items"):
                regional_rows.extend(
                    row for row in parse_sidra_rows(raw_responses[key], table, level="área IPCA")
                    if row["classificacao_codigo"] in leaf_codes
                )

    # The BCB maintains the long group series; join it with the headline IPCA by month.
    bcb_food = {row["periodo"]: row["valor"] for row in parse_bcb(bcb_responses["ipca_alimentacao"], BCB_SERIES["ipca_alimentacao"])}
    bcb_headline = {row["periodo"]: row["valor"] for row in parse_bcb(bcb_responses["ipca_geral"], BCB_SERIES["ipca_geral"])}
    sidra_periods = {
        code: {row["periodo"] for row in national_rows if row["classificacao_codigo"] == code}
        for code in ("7169", "7170")
    }
    for period, value in bcb_food.items():
        if period not in sidra_periods["7170"]:
            national_rows.append({"periodo": period, "territorio_codigo": "1", "territorio": "Brasil", "nivel_territorial": "Brasil", "classificacao_codigo": "7170", "classificacao_caminho": "1", "classificacao": "Alimentação e bebidas", "variavel_codigo": "63", "valor": value, "tabela_sidra": f"BCB-SGS-{BCB_SERIES['ipca_alimentacao']}"})
    for period, value in bcb_headline.items():
        if period not in sidra_periods["7169"]:
            national_rows.append({"periodo": period, "territorio_codigo": "1", "territorio": "Brasil", "nivel_territorial": "Brasil", "classificacao_codigo": "7169", "classificacao_caminho": "", "classificacao": "Índice geral", "variavel_codigo": "63", "valor": value, "tabela_sidra": f"BCB-SGS-{BCB_SERIES['ipca_geral']}"})

    national = aggregate_rows(deduplicate_rows(national_rows))
    regional = aggregate_rows(deduplicate_rows(regional_rows))

    # Add observed weights from SIDRA table 7060. They are published only from 2020.
    weights = {}
    for source_row in raw_responses["7060_weights"][1:]:
        dims = raw_responses["7060_weights"][0]
        period_key = next((key[:-1] for key, name in dims.items() if key.endswith("N") and name == "Mês"), "")
        category_key = next((key[:-1] for key, name in dims.items() if key.endswith("N") and "Geral, grupo" in name), "")
        period = str(source_row.get(period_key + "C", ""))
        category = str(source_row.get(category_key + "C", ""))
        if re.fullmatch(r"\d{6}", period):
            weights[(f"{period[:4]}-{period[4:]}", category)] = parse_number(source_row.get("V"))
    for row in national:
        row["peso_mensal_percentual"] = weights.get((row["periodo"], row["classificacao_codigo"]))
        row["impacto_aproximado_pontos_percentuais"] = (
            row["peso_mensal_percentual"] * row["valor"] / 100
            if row["peso_mensal_percentual"] is not None and row["valor"] is not None else None
        )
    for row in regional:
        row["peso_mensal_percentual"] = None
        row["impacto_aproximado_pontos_percentuais"] = None

    return {"nacional": national, "regional": regional}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    collected = datetime.now(timezone.utc).isoformat(timespec="seconds")
    responses: dict[str, Any] = {}
    headers = {"User-Agent": "insights-brasil/1.0 (public data; project repository)"}
    with httpx.Client(timeout=100, headers=headers, follow_redirects=True) as client:
        for table in SIDRA_TABLES:
            # Keep requests below SIDRA's response-size limit: monthly changes and weights are separate.
            url = sidra_url(table, level="n1/1", variables="63", periods="all", categories="all")
            responses[f"{table}_national"] = validate_sidra(request_json(client, url), url)
            if table == "7060":
                weight_url = sidra_url(table, level="n1/1", variables="66", periods="all", categories="all")
                responses["7060_weights"] = validate_sidra(request_json(client, weight_url), weight_url)
            for level in REGIONAL_LEVELS:
                url = sidra_url(table, level=f"{level}/all", variables="63", periods="all", categories=",".join(REGIONAL_AGGREGATES))
                responses[f"{table}_regions_{level}"] = validate_sidra(request_json(client, url), url)
                # Combine municipality and metropolitan-area observations for a shared regional table.
            responses[f"{table}_regions"] = [responses[f"{table}_regions_n6"][0]] + responses[f"{table}_regions_n6"][1:] + responses[f"{table}_regions_n7"][1:]

        # Product detail by IPCA area starts in 2020. Keep only observed food subitems,
        # split by year to stay comfortably under the API response-size limit.
        national_latest = parse_sidra_rows(responses["7060_national"], "7060", level="Brasil")
        food_codes = sorted({row["classificacao_codigo"] for row in national_latest if is_food_leaf(row)})
        if not food_codes:
            raise ValueError("SIDRA 7060 não retornou subitens alimentares para montar o detalhe regional")
        categories = ",".join(food_codes)
        for level in REGIONAL_LEVELS:
            all_period_rows: list[dict[str, Any]] = []
            for year in range(2020, datetime.now(timezone.utc).year + 1):
                start = f"{year}01"
                end = f"{year}12"
                period = f"{start}-{end}"
                url = sidra_url("7060", level=f"{level}/all", variables="63", periods=period, categories=categories)
                payload = validate_sidra(request_json(client, url), url)
                all_period_rows.extend(payload[1:])
            responses[f"7060_{level}_items"] = [responses[f"7060_national"][0]] + all_period_rows

        for key, code in BCB_SERIES.items():
            url = BCB.format(code=code)
            responses[key] = request_json(client, url)

    raw_payload = {
        "coletado_em": collected,
        "fontes": {
            "sidra": "IBGE — IPCA, tabelas 655, 2938, 1419 e 7060",
            "bcb": "Banco Central do Brasil — SGS 433 (IPCA geral) e SGS 1635 (Alimentação e bebidas)",
        },
        "urls": {
            **{f"sidra_{table}": f"{SIDRA}/t/{table}" for table in SIDRA_TABLES},
            **{f"bcb_{key}": BCB.format(code=code) for key, code in BCB_SERIES.items()},
        },
        "respostas": responses,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = RAW / f"ipca_alimentos_sidra_{stamp}.json.gz"
    raw_text = json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":"))
    with gzip.open(snapshot, "wt", encoding="utf-8", compresslevel=8) as stream:
        stream.write(raw_text)
    shutil.copyfile(snapshot, RAW / "ipca_alimentos_sidra.json")

    tables = normalize_all(responses, {key: responses[key] for key in BCB_SERIES})
    for key, table in tables.items():
        frame = pd.DataFrame(table).sort_values(["territorio_codigo", "classificacao_codigo", "periodo"])
        frame.to_csv(PROCESSED / f"ipca_alimentos_{key}.csv", index=False)
        print(f"Salvo {key}: {len(frame):,} registros, {frame.periodo.min()}–{frame.periodo.max()}")
    print(f"Bruto preservado: {snapshot} · coleta UTC {collected}")


if __name__ == "__main__":
    main()
