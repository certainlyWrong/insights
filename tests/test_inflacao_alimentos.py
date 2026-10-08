import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "baixar_inflacao_alimentos.py"
SPEC = importlib.util.spec_from_file_location("baixar_inflacao_alimentos", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FoodInflationParsingTests(unittest.TestCase):
    def test_request_retries_network_failure_and_reports_it(self):
        class OfflineClient:
            calls = 0

            def get(self, url):
                self.calls += 1
                raise httpx.ConnectError("offline")

        client = OfflineClient()
        with patch.object(MODULE.time, "sleep", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "após 4 tentativas"):
                MODULE.request_json(client, "https://example.invalid/data")
        self.assertEqual(client.calls, 4)

    def test_request_rejects_empty_json_response(self):
        class EmptyResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return []

        class EmptyClient:
            def get(self, url):
                return EmptyResponse()

        with patch.object(MODULE.time, "sleep", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Resposta vazia"):
                MODULE.request_json(EmptyClient(), "https://example.invalid/empty")

    def test_sidra_response_parses_month_and_classification(self):
        payload = [
            {"NC": "Nível Territorial (Código)", "NN": "Nível Territorial", "D1C": "Brasil (Código)", "D1N": "Brasil", "D2C": "Variável (Código)", "D2N": "Variável", "D3C": "Mês (Código)", "D3N": "Mês", "D4C": "Geral, grupo (Código)", "D4N": "Geral, grupo"},
            {"D1C": "1", "D1N": "Brasil", "D2C": "63", "D3C": "202401", "D4C": "7170", "D4N": "1. Alimentação e bebidas", "V": "1,25"},
        ]
        row = MODULE.parse_sidra_rows(payload, "7060", level="Brasil")[0]
        self.assertEqual(row["periodo"], "2024-01")
        self.assertEqual(row["classificacao_codigo"], "7170")
        self.assertEqual(row["classificacao"], "Alimentação e bebidas")
        self.assertEqual(row["valor"], 1.25)

    def test_empty_or_malformed_sidra_response_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "sem observações"):
            MODULE.validate_sidra([], "sidra-test")
        with self.assertRaisesRegex(ValueError, "incompatível"):
            MODULE.validate_sidra([{"D1N": "x"}, {"V": "1"}], "sidra-test")

    def test_malformed_bcb_observation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Observação inválida"):
            MODULE.parse_bcb([{"data": "2024-01-01", "valor": "1,0"}], "1635")

    def test_annual_and_rolling_rates_compound_monthly_rates(self):
        rows = []
        for month in range(1, 13):
            rows.append({
                "periodo": f"2024-{month:02d}", "territorio_codigo": "1", "classificacao_codigo": "7170",
                "variavel_codigo": "63", "valor": 1.0,
            })
        normalized = MODULE.aggregate_rows(rows)
        last = normalized[-1]
        expected = ((1.01 ** 12) - 1) * 100
        self.assertAlmostEqual(last["acumulado_ano_percentual"], expected)
        self.assertAlmostEqual(last["variacao_12_meses_percentual"], expected)

    def test_gaps_and_duplicates_do_not_create_fake_observations(self):
        rows = [
            {"periodo": "2024-01", "territorio_codigo": "1", "classificacao_codigo": "7170", "variavel_codigo": "63", "valor": 1.0},
            {"periodo": "2024-01", "territorio_codigo": "1", "classificacao_codigo": "7170", "variavel_codigo": "63", "valor": 2.0},
            {"periodo": "2024-03", "territorio_codigo": "1", "classificacao_codigo": "7170", "variavel_codigo": "63", "valor": 3.0},
        ]
        unique = MODULE.deduplicate_rows(rows)
        self.assertEqual(len(unique), 2)
        result = MODULE.aggregate_rows(unique)
        march = next(row for row in result if row["periodo"] == "2024-03")
        self.assertIsNone(march["acumulado_ano_percentual"])


if __name__ == "__main__":
    unittest.main()
