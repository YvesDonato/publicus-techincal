from __future__ import annotations

import html
import html.parser
import re
import shutil
import subprocess
import zipfile
from io import BytesIO
from typing import Any
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import httpx


BUSINESS_BENEFITS_DATASET_ID = "4e75337e-70d0-4ed7-92d1-3b85192ec6b1"
CKAN_API_BASE = "https://open.canada.ca/data/api/3/action"
INNOVATION_BASE_URL = "https://innovation.ised-isde.canada.ca"
INNOVATION_LIST_PATH = "/s/list-liste"
BUSINESS_BENEFITS_PAGE = "https://innovation.ised-isde.canada.ca/s/?language=en_CA"
DEFAULT_LANGUAGE = "en_CA"
DEFAULT_TOKEN = "a0BMm0000064uubMAA"
DEFAULT_RENDER_WAIT_MS = 15000
USER_AGENT = "publicus-technical/business-benefits-finder"
SORT_ORDERS = {"asc", "desc"}
CATEGORY_ALIASES = {
    "advice": "advice",
    "expert advice": "advice",
    "funding": "funding",
    "grant": "funding",
    "grants": "funding",
    "grants and funding": "funding",
    "loan": "loans",
    "loans": "loans",
    "loans and capital investments": "loans",
    "other": "other",
    "other support": "other",
    "partnership": "partnerships",
    "partnerships": "partnerships",
    "partnering and collaboration": "partnerships",
    "research": "research",
    "tariff": "urgent",
    "tax credit": "taxcredits",
    "tax credits": "taxcredits",
    "taxcredits": "taxcredits",
    "wage subsidies": "wagesubsidies",
    "wage subsidies and interns": "wagesubsidies",
    "wagesubsidies": "wagesubsidies",
}

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"m": SPREADSHEET_NS}
CELL_REFERENCE_RE = re.compile(r"([A-Z]+)")

HEADER_ALIASES = {
    "title-english": "title",
    "title-french": "title_fr",
    "short-description-english": "program",
    "short-description-french": "program_fr",
    "long-description-english": "description",
    "long-description-french": "description_fr",
    "organization-english": "organization",
    "organization-french": "organization_fr",
    "organization-url-english": "organization_url",
    "organization-url-french": "organization_url_fr",
}


def build_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout, connect=30.0),
        headers={
            "Accept": "application/json, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
            "User-Agent": USER_AGENT,
        },
        follow_redirects=True,
    )


class InnovationCanadaError(RuntimeError):
    pass


class InnovationListParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict[str, Any]] = []
        self.category_counts: dict[str, int] = {}
        self._record: dict[str, Any] | None = None
        self._record_depth = 0
        self._capture: str | None = None
        self._capture_depth = 0
        self._capture_chunks: list[str] = []
        self._hidden_span_depth = 0
        self._hidden_span_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}

        if self._hidden_span_depth:
            self._hidden_span_depth += 1
        elif tag == "span" and "display: none" in values.get("style", ""):
            self._hidden_span_depth = 1
            self._hidden_span_chunks = []

        if self._capture:
            self._capture_depth += 1

        if tag == "div" and values.get("data-dovid") and values.get("data-dovtitle") and self._record is None:
            data_dov = values.get("data-dov", "")
            self._record = {
                "id": values["data-dovid"],
                "dov_id": values["data-dovid"],
                "title": normalize_text(values.get("data-dovtitle", "")),
                "title_en": normalize_text(values.get("data-dovtitleen", "")),
                "status": normalize_text(values.get("data-dovstatus", "")),
                "category": category_from_data_dov(data_dov),
            }
            self._record_depth = 1
            return

        if self._record is None:
            return

        self._record_depth += 1
        node_id = values.get("id", "")
        class_names = set(values.get("class", "").split())

        if tag == "div" and node_id.endswith("-dov-title") and "list-sub-title" in class_names:
            self._capture = "title_text"
            self._capture_depth = 1
            self._capture_chunks = []
        elif tag == "div" and node_id.endswith("-dov-short-description") and "list-item-dov" in class_names:
            self._capture = "short_description"
            self._capture_depth = 1
            self._capture_chunks = []

    def handle_data(self, data: str) -> None:
        if self._hidden_span_depth:
            self._hidden_span_chunks.append(data)
        elif self._capture:
            self._capture_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._hidden_span_depth:
            self._hidden_span_depth -= 1
            if self._hidden_span_depth == 0:
                self._record_category_count()

        if self._capture:
            self._capture_depth -= 1
            if self._capture_depth == 0:
                self._finish_capture()

        if self._record is None:
            return

        self._record_depth -= 1
        if self._record_depth == 0:
            self._finish_record()

    def _record_category_count(self) -> None:
        text = normalize_text("".join(self._hidden_span_chunks))
        self._hidden_span_chunks = []
        match = re.match(r"^(.+?)\s+\((\d+)\)$", text)
        if match:
            self.category_counts[match.group(1)] = int(match.group(2))

    def _finish_capture(self) -> None:
        if self._record is not None and self._capture is not None:
            value = normalize_text("".join(self._capture_chunks))
            if value:
                self._record[self._capture] = value
        self._capture = None
        self._capture_depth = 0
        self._capture_chunks = []

    def _finish_record(self) -> None:
        if self._record is None:
            return

        record = dict(self._record)
        title_text = record.pop("title_text", "")
        if not record.get("title") and title_text:
            record["title"] = title_text
        if record.get("short_description"):
            record["description"] = record["short_description"]

        record["_id"] = len(self.records) + 1
        self.records.append(record)
        self._record = None
        self._record_depth = 0


def get_json(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if payload.get("success") is False:
        raise RuntimeError(f"API returned success=false: {payload}")
    return payload


def package_show(client: httpx.Client) -> dict[str, Any]:
    payload = get_json(client, f"{CKAN_API_BASE}/package_show", {"id": BUSINESS_BENEFITS_DATASET_ID})
    return payload["result"]


def latest_xlsx_resource(package: dict[str, Any]) -> dict[str, Any]:
    resources = [
        resource
        for resource in package.get("resources", [])
        if resource.get("url") and str(resource.get("format", "")).upper() == "XLSX"
    ]
    if not resources:
        raise RuntimeError("No XLSX Business Benefits Finder resource found.")
    return max(resources, key=lambda resource: int(resource.get("position") or 0))


def normalize_header(header: str) -> str:
    key = header.strip().lower()
    key = re.sub(r"\s+", " ", key)
    key = re.sub(r"\s*-\s*", "-", key)
    key = key.replace(" ", "-")
    return HEADER_ALIASES.get(key, key.replace("-", "_"))


def normalize_text(value: str) -> str:
    unescaped = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", unescaped).strip()


def build_list_url(*, token: str = DEFAULT_TOKEN, language: str = DEFAULT_LANGUAGE) -> str:
    query = urlencode({"language": language, "token": token})
    return f"{INNOVATION_BASE_URL}{INNOVATION_LIST_PATH}?{query}"


def category_from_data_dov(data_dov: str) -> str | None:
    if "-dov-" not in data_dov:
        return None
    category = data_dov.split("-dov-", 1)[0]
    return category or None


def normalize_category_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", normalize_text(value).casefold()).strip()
    compact_key = key.replace(" ", "")
    return CATEGORY_ALIASES.get(key) or CATEGORY_ALIASES.get(compact_key) or compact_key


def column_index(cell_reference: str) -> int:
    match = CELL_REFERENCE_RE.match(cell_reference)
    if not match:
        return 0

    index = 0
    for character in match.group(1):
        index = index * 26 + (ord(character) - ord("A") + 1)
    return index - 1


def shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("m:si", NS):
        strings.append("".join(text.text or "" for text in item.findall(".//m:t", NS)))
    return strings


def cell_value(cell: ET.Element, strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//m:t", NS)).strip()

    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""

    if cell_type == "s":
        return strings[int(value.text)].strip()
    return value.text.strip()


def parse_programs_xlsx(content: bytes, limit: int) -> list[dict[str, Any]]:
    with zipfile.ZipFile(BytesIO(content)) as workbook:
        strings = shared_strings(workbook)
        worksheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))

    headers: list[str] = []
    records: list[dict[str, Any]] = []
    sheet_data = worksheet.find("m:sheetData", NS)
    if sheet_data is None:
        return records

    for row in sheet_data.findall("m:row", NS):
        row_number = int(row.get("r") or 0)
        values_by_column: dict[int, str] = {}
        for cell in row.findall("m:c", NS):
            values_by_column[column_index(cell.get("r") or "")] = cell_value(cell, strings)

        if row_number == 1:
            max_column = max(values_by_column.keys(), default=-1)
            headers = [normalize_header(values_by_column.get(index, "")) for index in range(max_column + 1)]
            continue

        if row_number <= 2:
            continue

        if not any(values_by_column.values()):
            continue

        record: dict[str, Any] = {"_id": row_number}
        for index, header in enumerate(headers):
            if header:
                record[header] = values_by_column.get(index, "")

        records.append(record)
        if len(records) >= limit:
            break

    return records


def first_programs(client: httpx.Client, count: int) -> dict[str, Any]:
    package = package_show(client)
    resource = latest_xlsx_resource(package)
    response = client.get(resource["url"])
    response.raise_for_status()
    records = parse_programs_xlsx(response.content, count)

    return {
        "dataset_id": BUSINESS_BENEFITS_DATASET_ID,
        "dataset_title": package.get("title"),
        "resource_id": resource.get("id"),
        "resource_name": resource.get("name"),
        "requested": count,
        "count": len(records),
        "records": records,
        "source": resource.get("url") or BUSINESS_BENEFITS_PAGE,
    }


def find_chromium() -> str:
    for executable in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(executable)
        if path:
            return path
    raise InnovationCanadaError("Could not find a Chromium executable. Install chromium or enter the Nix dev shell.")


def render_list_page(
    *,
    token: str = DEFAULT_TOKEN,
    language: str = DEFAULT_LANGUAGE,
    timeout: float = 45.0,
    render_wait_ms: int = DEFAULT_RENDER_WAIT_MS,
) -> str:
    command = [
        find_chromium(),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--ignore-certificate-errors",
        f"--virtual-time-budget={render_wait_ms}",
        "--dump-dom",
        build_list_url(token=token, language=language),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=max(timeout, (render_wait_ms / 1000) + 10),
    )

    if completed.returncode != 0:
        stderr = completed.stderr.strip()[-1000:]
        raise InnovationCanadaError(f"Chromium could not render the Business Benefits Finder page: {stderr}")
    if "advanced-results" not in completed.stdout:
        raise InnovationCanadaError("The rendered Business Benefits Finder page did not include result records.")

    return completed.stdout


def parse_rendered_records(rendered_html: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    parser = InnovationListParser()
    parser.feed(rendered_html)
    parser.close()
    return parser.records, parser.category_counts


def category_sort_value(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("category") or "").casefold(),
        str(record.get("title") or record.get("title_en") or "").casefold(),
        str(record.get("id") or ""),
    )


def records_by_category(
    *,
    category: str | None = None,
    limit: int,
    offset: int,
    order: str = "asc",
    token: str = DEFAULT_TOKEN,
    language: str = DEFAULT_LANGUAGE,
    timeout: float = 45.0,
    render_wait_ms: int = DEFAULT_RENDER_WAIT_MS,
) -> dict[str, Any]:
    sort_order = order.lower()
    if sort_order not in SORT_ORDERS:
        raise InnovationCanadaError("order must be 'asc' or 'desc'.")

    rendered_html = render_list_page(
        token=token,
        language=language,
        timeout=timeout,
        render_wait_ms=render_wait_ms,
    )
    records, category_counts = parse_rendered_records(rendered_html)
    normalized_category = normalize_text(category or "")
    normalized_category_key = normalize_category_key(normalized_category)
    matching_records = [
        record
        for record in records
        if not normalized_category_key
        or normalize_category_key(str(record.get("category") or "")) == normalized_category_key
    ]
    sorted_records = sorted(matching_records, key=category_sort_value, reverse=sort_order == "desc")
    page_records = sorted_records[offset : offset + limit]

    return {
        "category": normalized_category or None,
        "order": sort_order,
        "limit": limit,
        "offset": offset,
        "count": len(page_records),
        "total": len(matching_records),
        "records": page_records,
        "source": build_list_url(token=token, language=language),
        "category_counts": category_counts,
        "source_meta": {
            "method": "salesforce_experience_cloud_rendered_dom",
            "sort": "category, title, id",
            "note": (
                "The Open Canada XLSX feed does not include the Business Benefits Finder category labels. "
                "This endpoint renders the official Business Benefits Finder page, parses the hydrated result DOM, "
                "then sorts and optionally filters records by category."
            ),
        },
    }
