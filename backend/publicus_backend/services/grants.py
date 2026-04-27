#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html.parser
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin

import httpx


SEARCH_BASE_URL = "https://search.open.canada.ca"
SEARCH_URL = f"{SEARCH_BASE_URL}/grants/"
DATASET_ID = "432527ab-7aac-45b5-81d6-7597107a7013"
CKAN_API_BASE = "https://open.canada.ca/data/api/3/action"
GRANTS_RESOURCE_ID = "1d15a62f-5656-49ad-8c88-f40ce689d831"
NIL_RESOURCE_ID = "4e4db232-f5e8-43c7-b8b2-439eb7d55475"
USER_AGENT = "publicus-technical/open-canada-grants-scraper"


class SearchPageParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.export_form: dict[str, Any] | None = None
        self._current_form: dict[str, Any] | None = None
        self.record_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "form":
            self._current_form = {
                "action": values.get("action", ""),
                "method": values.get("method", "get").lower(),
                "inputs": {},
            }

        if tag == "input" and self._current_form is not None:
            name = values.get("name")
            if name:
                self._current_form["inputs"][name] = values.get("value", "")

        if tag == "a":
            href = values.get("href", "")
            if href.startswith("/grants/record/"):
                self.record_links.append(urljoin(SEARCH_BASE_URL, href))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            if "/grants/export/" in self._current_form.get("action", ""):
                self.export_form = self._current_form
            self._current_form = None


@dataclass(frozen=True)
class ExportTask:
    task_id: str
    download_page_url: str
    status_url: str


def build_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout, connect=30.0),
        headers={
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "User-Agent": USER_AGENT,
        },
        follow_redirects=False,
    )


def get_json(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is False:
        raise RuntimeError(f"API returned success=false: {payload}")
    return payload


def package_show(client: httpx.Client) -> dict[str, Any]:
    payload = get_json(client, f"{CKAN_API_BASE}/package_show", {"id": DATASET_ID})
    return payload["result"]


def resource_by_id(package: dict[str, Any], resource_id: str) -> dict[str, Any]:
    for resource in package.get("resources", []):
        if resource.get("id") == resource_id:
            return resource
    raise KeyError(f"Resource not found: {resource_id}")


def resolve_resource_id(resource: str) -> str:
    if resource == "grants":
        return GRANTS_RESOURCE_ID
    if resource == "nil":
        return NIL_RESOURCE_ID
    return resource


def parse_filters(values: list[str]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(f"Expected KEY=VALUE filter, got {value!r}")
        key, item = value.split("=", 1)
        filters[key] = item
    return filters


def fetch_search_page(client: httpx.Client, query_string: str = "") -> tuple[httpx.Response, SearchPageParser]:
    url = SEARCH_URL
    if query_string:
        url = f"{SEARCH_URL}?{query_string.lstrip('?')}"
    response = client.get(url, headers={"Accept": "text/html"})
    response.raise_for_status()
    parser = SearchPageParser()
    parser.feed(response.text)
    return response, parser


def start_export(client: httpx.Client, query_string: str = "") -> ExportTask:
    response, parser = fetch_search_page(client, query_string)
    if not parser.export_form:
        raise RuntimeError("Could not find the grants export form on the search page.")

    form = parser.export_form
    data = dict(form["inputs"])
    csrf_token = data.get("csrfmiddlewaretoken")
    if csrf_token and "csrftoken" not in client.cookies:
        client.cookies.set("csrftoken", csrf_token, domain="search.open.canada.ca")

    export_url = urljoin(SEARCH_BASE_URL, form["action"])
    submit_response = client.post(
        export_url,
        data=data,
        headers={
            "Accept": "text/html, application/json;q=0.9, */*;q=0.8",
            "Origin": SEARCH_BASE_URL,
            "Referer": str(response.url),
        },
    )

    if submit_response.status_code not in {302, 303}:
        submit_response.raise_for_status()
        raise RuntimeError(
            "Expected the export endpoint to redirect to a download task page, "
            f"got HTTP {submit_response.status_code}."
        )

    location = submit_response.headers.get("location")
    if not location:
        raise RuntimeError("Export response did not include a Location header.")

    download_page_url = urljoin(SEARCH_BASE_URL, location)
    task_id = download_page_url.rstrip("/").rsplit("/", 1)[-1]
    return ExportTask(
        task_id=task_id,
        download_page_url=download_page_url,
        status_url=f"{SEARCH_BASE_URL}/search-results/en/grants/{task_id}",
    )


def poll_export(
    client: httpx.Client,
    task: ExportTask,
    poll_interval: float,
    timeout: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        response = client.get(
            task.status_url,
            headers={
                "Accept": "application/json",
                "Referer": task.download_page_url,
            },
        )
        if response.status_code not in {200, 202}:
            response.raise_for_status()

        payload = response.json()
        status = payload.get("task_status")
        if status == "SUCCESS":
            return payload
        if status in {"FAILURE", "REVOKED"}:
            raise RuntimeError(f"Export task failed: {payload}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for export task {task.task_id}: {payload}")

        print(payload.get("message", "Waiting for export task ..."), file=sys.stderr)
        time.sleep(poll_interval)


def download_url(client: httpx.Client, url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        with output.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def datastore_page(
    client: httpx.Client,
    resource_id: str,
    *,
    limit: int,
    offset: int,
    q: str | dict[str, str] | None,
    filters: dict[str, str] | None,
    sort: str | None = None,
    include_total: bool | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "resource_id": resource_id,
        "limit": limit,
        "offset": offset,
    }
    if isinstance(q, dict):
        params["q"] = json.dumps(q, ensure_ascii=False)
    elif q:
        params["q"] = q
    if filters:
        params["filters"] = json.dumps(filters, ensure_ascii=False)
    if sort:
        params["sort"] = sort
    if include_total is not None:
        params["include_total"] = "true" if include_total else "false"

    payload = get_json(client, f"{CKAN_API_BASE}/datastore_search", params)
    return payload["result"]


def iter_datastore_pages(
    client: httpx.Client,
    resource_id: str,
    *,
    page_size: int,
    start_offset: int,
    max_records: int | None,
    q: str | None,
    filters: dict[str, str] | None,
):
    emitted = 0
    offset = start_offset

    while True:
        remaining = None if max_records is None else max_records - emitted
        if remaining is not None and remaining <= 0:
            return

        limit = page_size if remaining is None else min(page_size, remaining)
        result = datastore_page(
            client,
            resource_id,
            limit=limit,
            offset=offset,
            q=q,
            filters=filters,
        )
        records = result.get("records", [])
        if not records:
            return

        yield result

        emitted += len(records)
        offset += len(records)
        total = result.get("total")
        if total is not None and offset >= int(total):
            return


def dump_datastore(
    client: httpx.Client,
    *,
    resource_id: str,
    output: Path,
    output_format: str,
    page_size: int,
    start_offset: int,
    max_records: int | None,
    q: str | None,
    filters: dict[str, str] | None,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    writer: csv.DictWriter[str] | None = None

    with output.open("w", encoding="utf-8", newline="") as handle:
        for result in iter_datastore_pages(
            client,
            resource_id,
            page_size=page_size,
            start_offset=start_offset,
            max_records=max_records,
            q=q,
            filters=filters,
        ):
            records = result["records"]
            if output_format == "jsonl":
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                    handle.write("\n")
            else:
                if writer is None:
                    fieldnames = [field["id"] for field in result.get("fields", [])]
                    if not fieldnames:
                        fieldnames = sorted({key for record in records for key in record})
                    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                writer.writerows(records)

            count += len(records)
            total = result.get("total")
            if total is None:
                print(f"Wrote {count} records", file=sys.stderr)
            else:
                print(f"Wrote {count} of {total} records", file=sys.stderr)

    return count


def discover(client: httpx.Client, query_string: str = "") -> dict[str, Any]:
    search_response, parser = fetch_search_page(client, query_string)
    package = package_show(client)
    grants = resource_by_id(package, GRANTS_RESOURCE_ID)
    nil = resource_by_id(package, NIL_RESOURCE_ID)
    export_form = parser.export_form or {}
    export_action = export_form.get("action", "/grants/export/")

    return {
        "source_page": str(search_response.url),
        "dataset": {
            "id": package["id"],
            "title": package.get("title"),
            "metadata_modified": package.get("metadata_modified"),
            "package_show_api": f"{CKAN_API_BASE}/package_show?id={DATASET_ID}",
            "schema_url": "https://open.canada.ca/data/recombinant-published-schema/grants.json",
        },
        "site_network_endpoints": {
            "search_page": SEARCH_URL,
            "search_query_params": {
                "page": "1-based page number",
                "sort": "agreement_start_date desc | agreement_value desc | score desc",
                "search_text": "free text search",
                "facets": [
                    "format",
                    "owner_org",
                    "year",
                    "agreement_type",
                    "agreement_value_range_en",
                    "has_amendments",
                ],
            },
            "record_url_example": parser.record_links[0] if parser.record_links else None,
            "export_submit": {
                "method": "POST",
                "url": urljoin(SEARCH_BASE_URL, export_action),
                "form_fields": sorted((export_form.get("inputs") or {}).keys()),
                "notes": "Requires the CSRF token from the page. The scraper mirrors the token into a csrftoken cookie.",
            },
            "export_status_template": f"{SEARCH_BASE_URL}/search-results/en/grants/{{task_id}}",
        },
        "ckan_raw_apis": {
            "datastore_search": {
                "url": f"{CKAN_API_BASE}/datastore_search",
                "grants_resource_id": GRANTS_RESOURCE_ID,
                "nil_resource_id": NIL_RESOURCE_ID,
                "pagination": "Use limit and offset. Example: ?resource_id=...&limit=5000&offset=0",
            },
            "direct_csv": {
                "grants": {
                    "url": grants.get("url"),
                    "size": grants.get("size"),
                    "last_modified": grants.get("last_modified"),
                    "hash": grants.get("hash"),
                },
                "nothing_to_report": {
                    "url": nil.get("url"),
                    "size": nil.get("size"),
                    "last_modified": nil.get("last_modified"),
                    "hash": nil.get("hash"),
                },
            },
        },
    }


def command_discover(args: argparse.Namespace) -> int:
    with build_client(args.timeout) as client:
        payload = discover(client, args.query_string)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_dump(args: argparse.Namespace) -> int:
    filters = parse_filters(args.filter)
    resource_id = resolve_resource_id(args.resource)
    with build_client(args.timeout) as client:
        count = dump_datastore(
            client,
            resource_id=resource_id,
            output=args.output,
            output_format=args.format,
            page_size=args.page_size,
            start_offset=args.offset,
            max_records=args.max_records,
            q=args.q,
            filters=filters or None,
        )
    print(f"Done: wrote {count} records to {args.output}")
    return 0


def command_download_csv(args: argparse.Namespace) -> int:
    resource_id = resolve_resource_id(args.resource)
    with build_client(args.timeout) as client:
        package = package_show(client)
        resource = resource_by_id(package, resource_id)
        csv_url = resource["url"]
        print(f"Downloading {csv_url} to {args.output}", file=sys.stderr)
        download_url(client, csv_url, args.output)
    print(f"Done: wrote {args.output}")
    return 0


def command_start_export(args: argparse.Namespace) -> int:
    with build_client(args.timeout) as client:
        task = start_export(client, args.query_string)
        payload: dict[str, Any] = {
            "task_id": task.task_id,
            "download_page_url": task.download_page_url,
            "status_url": task.status_url,
        }

        if args.wait:
            status = poll_export(client, task, args.poll_interval, args.timeout)
            payload["result"] = status
            file_url = status.get("file_url")
            if file_url and args.download_to:
                download_url(client, urljoin(SEARCH_BASE_URL, file_url), args.download_to)
                payload["downloaded_to"] = str(args.download_to)

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape Open Canada Grants and Contributions data through the raw APIs behind the search page.",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Print discovered raw API endpoints.")
    discover_parser.add_argument(
        "--query-string",
        default="",
        help="Optional search page query string, for example 'year=2025&owner_org=nrc-cnrc'.",
    )
    discover_parser.set_defaults(func=command_discover)

    dump_parser = subparsers.add_parser("dump", help="Stream records from CKAN datastore_search.")
    dump_parser.add_argument(
        "--resource",
        default="grants",
        help="Resource to dump: 'grants', 'nil', or an explicit CKAN resource id.",
    )
    dump_parser.add_argument("--output", type=Path, default=Path("backend/data/grants.jsonl"))
    dump_parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    dump_parser.add_argument("--page-size", type=int, default=5000)
    dump_parser.add_argument("--offset", type=int, default=0)
    dump_parser.add_argument("--max-records", type=int)
    dump_parser.add_argument("--q", help="Full-text query for CKAN datastore_search.")
    dump_parser.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Exact CKAN datastore filter as KEY=VALUE. Can be repeated.",
    )
    dump_parser.set_defaults(func=command_dump)

    csv_parser = subparsers.add_parser("download-csv", help="Download the direct raw CSV resource.")
    csv_parser.add_argument(
        "--resource",
        default="grants",
        help="Resource to download: 'grants', 'nil', or an explicit CKAN resource id.",
    )
    csv_parser.add_argument("--output", type=Path, default=Path("backend/data/grants.csv"))
    csv_parser.set_defaults(func=command_download_csv)

    export_parser = subparsers.add_parser("start-export", help="Start the website export task workflow.")
    export_parser.add_argument(
        "--query-string",
        default="",
        help="Optional website query string, for example 'year=2025&sort=agreement_value+desc'.",
    )
    export_parser.add_argument("--wait", action="store_true", help="Poll until the export task finishes.")
    export_parser.add_argument("--poll-interval", type=float, default=1.0)
    export_parser.add_argument("--download-to", type=Path, help="Download the export file after --wait succeeds.")
    export_parser.set_defaults(func=command_start_export)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "query_string", ""):
        # Normalize and validate without changing the user-specified query semantics.
        args.query_string = urlencode(parse_qsl(args.query_string, keep_blank_values=True))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
