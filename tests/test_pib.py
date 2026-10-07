from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path

import pandas as pd

from scripts.baixar_pib import observations


ROOT = Path(__file__).resolve().parents[1]


class SidraParsingTest(unittest.TestCase):
    def test_parses_period_series_and_missing_markers(self) -> None:
        rows = [
            {"D1C": "Brasil (Código)", "D1N": "Brasil", "D2C": "Variável (Código)", "D2N": "Variável", "D3C": "Trimestre (Código)", "D3N": "Trimestre", "D4C": "Setores e subsetores (Código)", "D4N": "Setores e subsetores", "V": "Valor"},
            {"D1C": "1", "D2C": "585", "D3C": "202601", "D4C": "90707", "V": "3.200,5"},
            {"D1C": "1", "D2C": "585", "D3C": "202602", "D4C": "90707", "V": "..."},
        ]
        parsed = observations(rows)
        self.assertEqual(parsed[("202601", "585:90707")], 3200.5)
        self.assertIsNone(parsed[("202602", "585:90707")])


class PibDataValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quarters = pd.read_csv(ROOT / "data/processed/pib_trimestral.csv")
        with gzip.open(ROOT / "web/src/assets/data/dashboard.json.gz", "rt", encoding="utf-8") as file:
            cls.dashboard = json.load(file)["pib"]

    def test_quarterly_series_is_unique_ordered_and_complete_for_main_measures(self) -> None:
        rows = self.quarters
        self.assertEqual(len(rows), 122)
        self.assertFalse(rows["periodo_sidra"].duplicated().any())
        self.assertTrue(rows["periodo_sidra"].is_monotonic_increasing)
        self.assertFalse(rows[["pib_nominal_milhoes", "pib_volume_indice", "pib_yoy_percentual"]].isna().any().any())

    def test_latest_official_release_matches_sidra_observation(self) -> None:
        latest = self.quarters.iloc[-1]
        self.assertEqual(latest["trimestre"], "2026-T2")
        self.assertEqual(latest["pib_nominal_milhoes"], 3_425_728)
        self.assertEqual(latest["pib_yoy_percentual"], 2.0)
        self.assertEqual(latest["pib_qoq_sa_percentual"], 0.5)
        self.assertEqual(str(self.dashboard["quarterly"][-1]["periodo_sidra"]), "202602")

    def test_semester_sum_and_derived_growth_match_source_quarters(self) -> None:
        semester = next(row for row in self.dashboard["aggregates"] if row["periodo"] == "2026-S1")
        quarters = self.quarters[self.quarters["periodo_sidra"].astype(str).str.startswith("2026")]
        prior = self.quarters[self.quarters["periodo_sidra"].astype(str).str.startswith("2025")].head(2)
        self.assertTrue(semester["periodo_completo"])
        self.assertEqual(semester["pib_nominal_milhoes"], quarters["pib_nominal_milhoes"].sum())
        expected = (quarters["pib_volume_indice"].mean() / prior["pib_volume_indice"].mean() - 1) * 100
        self.assertAlmostEqual(semester["pib_real_semestre_derived_percentual"], expected)

    def test_open_year_is_marked_partial_and_keeps_official_ytd_rate(self) -> None:
        year = next(row for row in self.dashboard["aggregates"] if row["periodo"] == "2026")
        self.assertFalse(year["periodo_completo"])
        self.assertEqual(year["trimestres_no_periodo"], 2)
        self.assertIsNone(year["pib_nominal_yoy_percentual"])
        self.assertEqual(year["pib_ytd_percentual"], 1.9)

    def test_collection_snapshot_is_preserved(self) -> None:
        snapshots = list((ROOT / "data/raw/ibge").glob("contas_nacionais_trimestrais_sidra_????????T??????Z.json"))
        self.assertTrue(snapshots)
        payload = json.loads(snapshots[-1].read_text(encoding="utf-8"))
        self.assertIn("coletado_em", payload)
        self.assertEqual(set(payload["tabelas"]), {"nominal", "volume", "rates"})


if __name__ == "__main__":
    unittest.main()
