"""Small, bounded downloaders for the initial official sources."""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from .catalog import Dataset
from .storage import persist_failure, persist_run


class DownloadError(RuntimeError):
    pass


def parse_params(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Parâmetro inválido {value!r}; use nome=valor.")
        key, item = value.split("=", 1)
        if not key or not item:
            raise ValueError(f"Parâmetro inválido {value!r}; nome e valor são obrigatórios.")
        parsed[key] = item
    return parsed


def _result_rows(payload: Any) -> tuple[list[dict[str, Any]], int | None]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    if isinstance(payload, dict):
        for key in ("data", "items", "content", "resultado", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                total = payload.get("totalPaginas") or payload.get("totalPages")
                try:
                    total_pages = int(total) if total is not None else None
                except (TypeError, ValueError):
                    total_pages = None
                return [row for row in value if isinstance(row, dict)], total_pages
        return [payload], None
    raise DownloadError("A fonte retornou JSON em um formato não reconhecido.")


def _federal(record: dict[str, Any]) -> bool:
    entity = record.get("orgaoEntidade")
    if isinstance(entity, dict) and entity.get("esferaId") is not None:
        value = entity["esferaId"]
    else:
        value = record.get("orgaoEntidadeEsferaId")
        if value is None:
            value = record.get("esferaId", record.get("esfera"))
    if value is not None:
        normalized = str(value).strip().lower()
        return normalized in {"f", "federal", "união", "uniao", "1"}
    return False


def _request_json(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.get(url, params=params, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(0.5 * (2**attempt))
                    continue
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                raise DownloadError("A fonte não retornou JSON válido.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise DownloadError(f"A fonte respondeu HTTP {status} para {url}.") from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (2**attempt))
    raise DownloadError(f"Não foi possível acessar {url}: {last_error}") from last_error


def _prepare_params(dataset: Dataset, extra: dict[str, str]) -> dict[str, Any]:
    params: dict[str, Any] = dict(dataset.default_params)
    params.update(extra)
    if dataset.connector == "cgu":
        params.setdefault("ano", str(date.today().year))
    if dataset.connector == "pncp":
        start = date.today() - timedelta(days=1)
        end = date.today()
        params.setdefault("dataInicial", start.strftime("%Y%m%d"))
        params.setdefault("dataFinal", end.strftime("%Y%m%d"))
        params.setdefault("codigoModalidadeContratacao", "6")
        params.setdefault("pagina", "1")
        params.setdefault("tamanhoPagina", "10")
    if dataset.id == "compras_contratacoes":
        start = date.today() - timedelta(days=1)
        end = date.today()
        params.setdefault("dataPublicacaoPncpInicial", start.isoformat())
        params.setdefault("dataPublicacaoPncpFinal", end.isoformat())
        params.setdefault("tamanhoPagina", "10")
    missing = [key for key in dataset.required_params if not params.get(key)]
    if missing:
        rendered = ", ".join(f"--param {name}=VALOR" for name in missing)
        raise ValueError(f"Informe os filtros obrigatórios: {rendered}.")
    return params


def download(
    dataset: Dataset,
    extra_params: dict[str, str],
    max_pages: int = 2,
) -> tuple[int, str]:
    if not dataset.connector or not dataset.endpoint:
        raise ValueError(f"{dataset.id} está catalogado, mas ainda não tem conector de download.")
    if not 1 <= max_pages <= 100:
        raise ValueError("--max-pages deve ficar entre 1 e 100.")

    params = _prepare_params(dataset, extra_params)
    private_terms = ("favorecido", "document", "email", "token", "chave", "senha", "password")
    audit_params = {
        key: value for key, value in params.items()
        if not (
            key.lower() in {"cpf", "cnpj", "nis"}
            or key.lower().startswith(("cpf", "cnpj", "nis"))
            or any(term in key.lower() for term in private_terms)
        )
    }
    headers: dict[str, str] = {"User-Agent": "insights-gov-data/0.1"}
    if dataset.connector == "cgu":
        token = os.environ.get("PORTAL_TRANSPARENCIA_TOKEN")
        if not token:
            raise ValueError(
                "A API da CGU exige token. Cadastre um e-mail em "
                "https://portaldatransparencia.gov.br/api-de-dados e defina "
                "PORTAL_TRANSPARENCIA_TOKEN no ambiente."
            )
        headers["chave-api-dados"] = token
    if dataset.connector == "pncp":
        params.setdefault("pagina", "1")

    started_at = datetime.now(timezone.utc)
    collected: list[dict[str, Any]] = []
    raw_pages: list[Any] = []
    page_count = 0
    try:
        with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0), follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                page_params = dict(params)
                page_params[dataset.page_param] = str(page)
                payload = _request_json(client, dataset.endpoint, page_params, headers)
                rows, total_pages = _result_rows(payload)
                raw_pages.append(payload)
                page_count += 1
                source_row_count = len(rows)
                if dataset.federal_filter:
                    rows = [row for row in rows if _federal(row)]
                collected.extend(rows)
                if source_row_count == 0 or (total_pages is not None and page >= total_pages):
                    break
                # API clients are capped to one request per second by default.
                if page < max_pages:
                    time.sleep(1.0)
        period_start = str(
            params.get("dataInicial") or params.get("dataPublicacaoPncpInicial") or params.get("ano") or ""
        ) or None
        period_end = str(
            params.get("dataFinal") or params.get("dataPublicacaoPncpFinal") or params.get("ano") or ""
        ) or None
        persist_run(
            dataset.id, dataset.endpoint, collected, page_count, started_at,
            period_start, period_end, raw_payload=raw_pages, query_params=audit_params,
            source_version=dataset.source_version,
        )
        return len(collected), str(dataset.endpoint)
    except Exception as exc:
        persist_failure(
            dataset.id, dataset.endpoint, started_at, str(exc), page_count,
            query_params=audit_params, source_version=dataset.source_version,
        )
        raise
