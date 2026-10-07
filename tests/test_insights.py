from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from insights import main
from insights.catalog import get_dataset
from insights.ingest import _federal, _result_rows, download, parse_params
from insights.storage import connect, latest_runs


class HelpersTest(unittest.TestCase):
    def test_parameter_parser(self) -> None:
        self.assertEqual(parse_params(["ano=2025", "orgaoSuperior=26000"]), {
            "ano": "2025", "orgaoSuperior": "26000",
        })
        with self.assertRaises(ValueError):
            parse_params(["ano"])

    def test_result_rows_and_federal_filter(self) -> None:
        federal = {"orgaoEntidade": {"esferaId": "F"}}
        local = {"orgaoEntidade": {"esferaId": "M"}}
        rows, pages = _result_rows({"data": [federal, local], "totalPaginas": 4})
        self.assertEqual(rows, [federal, local])
        self.assertEqual(pages, 4)
        self.assertTrue(_federal(federal))
        self.assertFalse(_federal(local))
        self.assertFalse(_federal({"nome": "sem esfera"}))


class CliTest(unittest.TestCase):
    def test_catalog_lists_supported_and_planned_sets(self) -> None:
        from io import StringIO
        output = StringIO()
        with patch("sys.stdout", output):
            self.assertEqual(main(["catalog"]), 0)
        self.assertIn("cgu_despesas_orgao [disponível]", output.getvalue())
        self.assertIn("tesouro_divida_publica [planejado]", output.getvalue())

    def test_unknown_dataset_is_an_error(self) -> None:
        from io import StringIO
        errors = StringIO()
        with patch("sys.stderr", errors):
            self.assertEqual(main(["fetch", "nao_existe"]), 2)
        self.assertIn("Conjunto desconhecido", errors.getvalue())


class StorageAndDownloadTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("INSIGHTS_HOME")
        os.environ["INSIGHTS_HOME"] = self.temp_dir.name

    def tearDown(self) -> None:
        if self.old_home is None:
            os.environ.pop("INSIGHTS_HOME", None)
        else:
            os.environ["INSIGHTS_HOME"] = self.old_home
        self.temp_dir.cleanup()

    def test_pncp_download_keeps_raw_page_and_only_stores_federal_records(self) -> None:
        federal = {"numeroControlePNCP": "1", "orgaoEntidade": {"esferaId": "F"}}
        state = {"numeroControlePNCP": "2", "orgaoEntidade": {"esferaId": "E"}}

        class Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"data": [federal, state], "totalPaginas": 1}

        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, params=None, headers=None):
                self.params = params
                return Response()

        with patch("insights.ingest.httpx.Client", Client), patch("insights.ingest.time.sleep"):
            count, _ = download(get_dataset("pncp_contratacoes"), {}, max_pages=1)
            download(get_dataset("pncp_contratacoes"), {}, max_pages=1)

        self.assertEqual(count, 1)
        connection = connect()
        try:
            stored = connection.execute("SELECT count(*) FROM records WHERE dataset_id='pncp_contratacoes'").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(stored, 1)
        run = latest_runs()[0]
        self.assertEqual(run[2], "success")
        raw_path = Path(run[5])
        raw_page = json.loads(raw_path.read_text(encoding="utf-8"))[0]
        self.assertEqual(len(raw_page["data"]), 2)

    def test_compras_api_filters_to_federal_sphere(self) -> None:
        federal = {"idCompra": "1", "orgaoEntidadeEsferaId": "F"}
        state = {"idCompra": "2", "orgaoEntidadeEsferaId": "E"}

        class Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {"resultado": [federal, state], "totalPaginas": 1}

        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, params=None, headers=None):
                self.params = params
                return Response()

        with patch("insights.ingest.httpx.Client", Client), patch("insights.ingest.time.sleep"):
            count, _ = download(get_dataset("compras_contratacoes"), {}, max_pages=1)
        self.assertEqual(count, 1)
        filters = json.loads(latest_runs()[0][8])
        self.assertIn("dataPublicacaoPncpFinal", filters)

    def test_pagination_stops_on_empty_response_page(self) -> None:
        calls: list[dict[str, str]] = []

        class Response:
            status_code = 200

            def __init__(self, page: int):
                self.page = page

            def raise_for_status(self) -> None:
                return None

            def json(self):
                if self.page == 1:
                    return [{"orgao": "MEC", "valor": 12}]
                return []

        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, params=None, headers=None):
                calls.append(dict(params))
                return Response(int(params["pagina"]))

        with (
            patch("insights.ingest.httpx.Client", Client),
            patch("insights.ingest.time.sleep"),
            patch.dict(os.environ, {"PORTAL_TRANSPARENCIA_TOKEN": "test-token"}),
        ):
            count, _ = download(
                get_dataset("cgu_despesas_orgao"),
                {"orgaoSuperior": "26000", "ano": "2025"},
                max_pages=3,
            )
        self.assertEqual(count, 1)
        self.assertEqual([params["pagina"] for params in calls], ["1", "2"])

    def test_cgu_token_is_sent_as_header_and_not_persisted(self) -> None:
        class Response:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self):
                return [{"orgao": "Ministério da Educação", "valor": 12}]

        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, url, params=None, headers=None):
                self.headers = headers
                self.params = params
                self.__class__.last_headers = headers
                return Response()

        with (
            patch("insights.ingest.httpx.Client", Client),
            patch("insights.ingest.time.sleep"),
            patch.dict(os.environ, {"PORTAL_TRANSPARENCIA_TOKEN": "test-secret-token"}),
        ):
            count, _ = download(
                get_dataset("cgu_despesas_orgao"),
                {"orgaoSuperior": "26000", "ano": "2025"},
                max_pages=1,
            )
        self.assertEqual(count, 1)
        self.assertEqual(Client.last_headers["chave-api-dados"], "test-secret-token")
        self.assertNotIn("token", json.dumps(latest_runs(), default=str))

    def test_api_failure_is_recorded(self) -> None:
        class Response:
            status_code = 503

            def raise_for_status(self) -> None:
                import httpx
                request = httpx.Request("GET", "https://example.invalid")
                response = httpx.Response(503, request=request)
                raise httpx.HTTPStatusError("unavailable", request=request, response=response)

        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def get(self, *args, **kwargs):
                return Response()

        with patch("insights.ingest.httpx.Client", Client), patch("insights.ingest.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                download(get_dataset("pncp_contratacoes"), {}, max_pages=1)
        self.assertEqual(latest_runs()[0][2], "failed")


if __name__ == "__main__":
    unittest.main()
