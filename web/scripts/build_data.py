"""Export processed project data for the static Vue dashboard."""

from __future__ import annotations

import gzip
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
ASSETS = Path(__file__).resolve().parents[1] / "src" / "assets" / "data"
ASSETS.mkdir(parents=True, exist_ok=True)


def records(path: Path) -> list[dict]:
    frame = pd.read_csv(path)
    frame = frame.astype(object).where(pd.notna(frame), None)
    return frame.to_dict(orient="records")


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


stock_rows = records(PROCESSED / "dpf_estoque_mensal.csv")
stock = pd.DataFrame(stock_rows)
key_indicators = ["DPF EM PODER DO PÚBLICO", "DPMFi", "DPFe ¹"]
stock_main = (
    stock[stock["indicador"].isin(key_indicators)]
    .pivot(index="data", columns="indicador", values="valor_r_bilhoes")
    .reset_index()
    .rename(
        columns={
            "DPF EM PODER DO PÚBLICO": "dpf_bilhoes",
            "DPMFi": "dpmfi_bilhoes",
            "DPFe ¹": "dpfe_bilhoes",
        }
    )
    .sort_values("data")
)

# The Treasury's "Juros Apropriados" is an accrual measure, not cash interest
# paid in the same month. Keep the total and its domestic/external components.
factor_rows = records(PROCESSED / "dpf_fatores_mensais.csv")
factor_frame = pd.DataFrame(factor_rows)
interest_names = {
    "I.2 - Juros  Apropriados": "juros_dpf_bilhoes",
    "- Juros Apropriados da DPMFi 9": "juros_dpmfi_bilhoes",
    "- Juros Apropriados da DPFe 10": "juros_dpfe_bilhoes",
}
interest_monthly = (
    factor_frame[factor_frame["indicador"].isin(interest_names)]
    .pivot(index="data", columns="indicador", values="valor_r_bilhoes")
    .rename(columns=interest_names)
    .reset_index()
    .sort_values("data")
)
interest_monthly["ano"] = pd.to_datetime(interest_monthly["data"]).dt.year
interest_annual = (
    interest_monthly.groupby("ano", as_index=False)[list(interest_names.values())]
    .sum(min_count=1)
)
stock_monthly = stock_main[["data", "dpf_bilhoes"]].copy()
stock_monthly["ano"] = pd.to_datetime(stock_monthly["data"]).dt.year
annual_average_stock = stock_monthly.groupby("ano", as_index=False)["dpf_bilhoes"].mean().rename(
    columns={"dpf_bilhoes": "estoque_medio_dpf_bilhoes"}
)
interest_annual = interest_annual.merge(annual_average_stock, on="ano", how="left")
interest_annual["custo_implicito_aproximado_percentual"] = (
    100 * interest_annual["juros_dpf_bilhoes"] / interest_annual["estoque_medio_dpf_bilhoes"]
)
# Annual rates are comparable only for closed calendar years. Keep the partial
# year's accrued-interest total, but leave its annual rate blank.
last_interest_date = pd.to_datetime(interest_monthly["data"]).max()
if last_interest_date.month != 12:
    interest_annual.loc[interest_annual["ano"] == last_interest_date.year, "custo_implicito_aproximado_percentual"] = None

# IBGE quarterly national accounts. Keep all periods and source series in the
# bundle; the shorter aggregates are explicitly marked when the year is open.
pib_quarterly = pd.read_csv(PROCESSED / "pib_trimestral.csv")
pib_quarterly = pib_quarterly.where(pd.notna(pib_quarterly), None)
pib_raw = pd.read_csv(PROCESSED / "pib_trimestral.csv")
pib_aggregates = []
for kind in ("semestre", "ano"):
    grouping = ["ano", "semestre"] if kind == "semestre" else ["ano"]
    for keys, group in pd.read_csv(PROCESSED / "pib_trimestral.csv").groupby(grouping, sort=True):
        if kind == "semestre":
            year, half = keys
            label = f"{year}-S{half}"
            expected = 2
            group_name = "semestre"
        else:
            year = keys[0]
            half = None
            label = str(year)
            expected = 4
            group_name = "ano"
        count = len(group)
        aggregate = {
            "periodo": label,
            "tipo_periodo": group_name,
            "ano": int(year),
            "semestre": int(half) if half is not None else None,
            "trimestres_no_periodo": int(count),
            "periodo_completo": count == expected,
            "data_coleta": datetime.now(timezone.utc).date().isoformat(),
        }
        for column in [c for c in group.columns if c.endswith("_nominal_milhoes")]:
            aggregate[column] = group[column].sum(min_count=1)
        for column in [c for c in group.columns if c.endswith("_volume_indice")]:
            # The chained volume index is non-additive; the mean over equal
            # quarter counts is a period-level comparison proxy, not a level.
            aggregate[column] = group[column].mean()
        previous = pib_raw[pib_raw["ano"] == int(year) - 1]
        if kind == "semestre":
            previous = previous[previous["semestre"] == int(half)]
        previous = previous.head(count)
        comparable = len(previous) == count and count == expected
        for slug, _ in {
            "pib": "", "agropecuaria": "", "industria": "", "servicos": "",
            "consumo_familias": "", "consumo_governo": "", "formacao_capital": "",
            "variacao_estoques": "", "exportacoes": "", "importacoes": "",
        }.items():
            current_vol = group[f"{slug}_volume_indice"].dropna()
            prior_vol = previous[f"{slug}_volume_indice"].dropna()
            current_nom = group[f"{slug}_nominal_milhoes"].dropna()
            prior_nom = previous[f"{slug}_nominal_milhoes"].dropna()
            aggregate[f"{slug}_real_semestre_derived_percentual"] = (
                (current_vol.mean() / prior_vol.mean() - 1) * 100
                if kind == "semestre" and comparable and len(current_vol) == count and len(prior_vol) == count else None
            )
            aggregate[f"{slug}_nominal_yoy_percentual"] = (
                (current_nom.sum() / prior_nom.sum() - 1) * 100
                if comparable and len(current_nom) == count and len(prior_nom) == count else None
            )
            if kind == "ano":
                # The accumulated rates are IBGE series. For an open year,
                # this is the official year-to-date rate through its latest quarter.
                latest = group.sort_values("trimestre_numero").iloc[-1]
                aggregate[f"{slug}_ytd_percentual"] = latest.get(f"{slug}_ytd_percentual")
                aggregate[f"{slug}_four_quarters_percentual"] = latest.get(f"{slug}_four_quarters_percentual")
        pib_aggregates.append(aggregate)

tax_monthly = records(PROCESSED / "arrecadacao_federal_mensal.csv")
tax_monthly_frame = pd.DataFrame(tax_monthly).sort_values("data")
tax_monthly_frame["acumulado_ano_milhoes"] = tax_monthly_frame.groupby("ano")["arrecadacao_total_federal_milhoes"].cumsum()
tax_monthly_frame["variacao_nominal_12_meses_percentual"] = tax_monthly_frame["arrecadacao_total_federal_milhoes"].pct_change(12) * 100
tax_annual = (
    tax_monthly_frame.groupby("ano", as_index=False)
    .agg(arrecadacao_total_federal_milhoes=("arrecadacao_total_federal_milhoes", "sum"), meses_publicados=("mes", "count"))
)
tax_annual["ano_completo"] = tax_annual["meses_publicados"] == 12
tax_annual["variacao_nominal_percentual"] = None
for index, row in tax_annual.iterrows():
    prior = tax_monthly_frame[(tax_monthly_frame["ano"] == row["ano"] - 1) & (tax_monthly_frame["mes"] <= row["meses_publicados"])]
    if len(prior) == row["meses_publicados"]:
        tax_annual.loc[index, "variacao_nominal_percentual"] = (
            row["arrecadacao_total_federal_milhoes"] / prior["arrecadacao_total_federal_milhoes"].sum() - 1
        ) * 100
tax_ctb = records(PROCESSED / "carga_tributaria_governo_geral_anual.csv")

# Purchasing power of the Real. July 1994 is the price-level reference; the
# first compounded monthly change is August 1994, so July's inflation is not
# incorrectly counted as though the new currency were in circulation all month.
ipca_source = json.loads((ROOT / "data/raw/bcb/ipca_mensal.json").read_text(encoding="utf-8"))
ipca_rows = []
price_index = 100.0
for observation in ipca_source:
    date = datetime.strptime(observation["data"], "%d/%m/%Y")
    period = date.strftime("%Y-%m")
    if period < "1994-07":
        continue
    monthly_rate = float(str(observation["valor"]).replace(",", "."))
    if period > "1994-07":
        price_index *= 1 + monthly_rate / 100
    remaining = 10000 / price_index
    ipca_rows.append({
        "data": period,
        "ipca_mensal_percentual": monthly_rate,
        "variacao_incluida_no_acumulado": period > "1994-07",
        "indice_precos_jul_1994_100": price_index,
        "inflacao_acumulada_desde_jul_1994_percentual": (price_index / 100 - 1) * 100,
        "perda_poder_compra_percentual": 100 - remaining,
        "poder_compra_remanescente_percentual": remaining,
        "preco_cesta_r_100_jul_1994": price_index,
    })
ipca_latest = ipca_rows[-1]

payload = clean(
    {
        "updated": "2026-10-06",
        "sources": [
            {"name": "Tesouro Nacional — Estoque da DPF", "url": "https://www.tesourotransparente.gov.br/ckan/dataset/0998f610-bc25-4ce3-b32c-a873447500c2"},
            {"name": "Tesouro Nacional — Fatores de variação da DPF", "url": "https://www.tesourotransparente.gov.br/ckan/dataset/fatores-de-variacao-da-divida-publica-federal"},
            {"name": "Tesouro Nacional — Emissões e resgates", "url": "https://www.tesourotransparente.gov.br/ckan/dataset/emissoes-e-resgates-divida-publica-federal"},
            {"name": "Banco Central — Séries SGS", "url": "https://dadosabertos.bcb.gov.br/"},
            {"name": "Banco Central/IBGE — IPCA mensal (SGS 433)", "url": "https://dadosabertos.bcb.gov.br/dataset/433-indice-nacional-de-precos-ao-consumidor-amplo-ipca"},
            {"name": "SIOP — Dados Abertos do Orçamento", "url": "https://orcamento.dados.gov.br/siopdoc/doku.php/acesso_publico:dados_abertos/"},
            {"name": "MDS/SAGICAD — VIS DATA, benefícios sociais", "url": "https://aplicacoes.cidadania.gov.br/vis/data3/"},
            {"name": "MDS — Balanço do Bolsa Família 2024", "url": "https://www.gov.br/mds/pt-br/noticias-e-conteudos/desenvolvimento-social/noticias-desenvolvimento-social/governo-federal-repassa-r-168-3-bilhoes-pelo-bolsa-familia-em-2024"},
            {"name": "MDS — Relatório de Gestão 2024", "url": "https://www.gov.br/mds/pt-br/acesso-a-informacao/auditorias/2024/mds-relatorio-de-gestao.pdf"},
            {"name": "IBGE/SIDRA — Contas Nacionais Trimestrais", "url": "https://sidra.ibge.gov.br/pesquisa/cnt/tabelas"},
            {"name": "Receita Federal — Arrecadação federal", "url": "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/serie-historica"},
            {"name": "Receita Federal — Análise mensal da arrecadação", "url": "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/arrecadacao-federal"},
            {"name": "Tesouro Nacional — Carga Tributária do Governo Geral", "url": "https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/carga-tributaria-do-governo-geral"},
        ],
        "debt": {
            "monthly": stock_main.to_dict(orient="records"),
            "composition": stock_rows,
            "macro": records(PROCESSED / "bcb_divida_ipca_mensal.csv"),
            "factors": records(PROCESSED / "dpf_fatores_mensais.csv"),
            "flows": records(PROCESSED / "dpf_emissoes_resgates_mensal.csv"),
            "holdings": records(PROCESSED / "dpf_estoque_detalhado.csv"),
            "interest": {
                "monthly": interest_monthly.to_dict(orient="records"),
                "annual": interest_annual.to_dict(orient="records"),
            },
        },
        "spending": records(PROCESSED / "orcamento_saude_seguranca_educacao.csv"),
        "social": {
            "bpc_annual": records(PROCESSED / "bpc_historico_anual.csv"),
            "comparison_2024": [
                {"programa": "Bolsa Família", "repasses_brl": 168300000000, "cobertura": 20860000, "unidade": "famílias contempladas ao longo de 2024", "fonte": "MDS — balanço 2024"},
                {"programa": "BPC", "repasses_brl": 102269367070.43, "cobertura": 6292449, "unidade": "beneficiários em 2024", "fonte": "VIS DATA/MDS — série anual BPC"},
            ],
            "auxilio_gas_2024": {"cobertura_media_ciclo": 5700000, "periodo": "fevereiro a dezembro de 2024", "periodicidade": "bimestral", "fonte": "Relatório de Gestão MDS 2024"},
        },
        "pib": {
            "quarterly": pib_quarterly.to_dict(orient="records"),
            "aggregates": pib_aggregates,
            "source": {
                "name": "IBGE — Contas Nacionais Trimestrais",
                "collected_at": json.loads((ROOT / "data/raw/ibge/contas_nacionais_trimestrais_sidra.json").read_text(encoding="utf-8"))["coletado_em"],
                "period_start": str(pib_quarterly.iloc[0]["trimestre"]),
                "period_end": str(pib_quarterly.iloc[-1]["trimestre"]),
                "tables": {"1846": "Valores correntes", "1620": "Índice de volume trimestral", "5932": "Taxas de variação"},
            },
        },
        "taxes": {
            "monthly": tax_monthly_frame.to_dict(orient="records"),
            "annual": tax_annual.to_dict(orient="records"),
            "general_annual": tax_ctb,
            "source": {
                "name": "Receita Federal — Arrecadação das Receitas Federais",
                "collected_at": "2026-10-07",
                "period_start": str(tax_monthly_frame.iloc[0]["data"]),
                "period_end": str(tax_monthly_frame.iloc[-1]["data"]),
                "unit": "R$ milhões correntes",
                "scope": "Total federal: receitas administradas pela RFB e por outros órgãos",
                "history_url": "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/serie-historica",
                "latest_url": "https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/relatorios/arrecadacao-federal",
                "general_tax_burden_url": "https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/carga-tributaria-do-governo-geral",
                "raw_files": ["data/raw/tributos/arrecadacao_receitas_federais_1994_2025.xlsx", "data/raw/tributos/arrecadacao_federal_2026_ate_agosto.xlsx", "data/raw/tributos/carga_tributaria_governo_geral_2025.xlsx"],
            },
        },
        "purchasing_power": {
            "monthly": ipca_rows,
            "source": {
                "name": "IPCA mensal — Banco Central do Brasil / IBGE (SGS 433)",
                "collected_at": "2026-10-06",
                "base_period": "1994-07",
                "period_start": ipca_rows[0]["data"],
                "period_end": ipca_latest["data"],
                "reference_index": 100,
                "unit": "Variação mensal do IPCA (%)",
                "method": "Índice de preços relativo a julho de 1994, composto pelas variações mensais de agosto de 1994 até o último período disponível",
                "url": "https://dadosabertos.bcb.gov.br/dataset/433-indice-nacional-de-precos-ao-consumidor-amplo-ipca",
            },
        },
    }
)

with gzip.open(ASSETS / "dashboard.json.gz", "wt", encoding="utf-8", compresslevel=8) as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
shutil.copy2(PROCESSED / "dpf_posicoes_por_titulo.csv.gz", ASSETS / "posicoes_por_titulo.csv.gz")
print(f"Dashboard bundle: {ASSETS / 'dashboard.json.gz'}")
print(f"Debt months: {len(payload['debt']['monthly'])}; budget rows: {len(payload['spending'])}")
