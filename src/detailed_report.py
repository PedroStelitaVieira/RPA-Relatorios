import datetime
import json
import time
from collections import defaultdict
from numbers import Number
from typing import Any

import pandas as pd

from src.utils import setup_logger

logger = setup_logger(__name__)

MAX_REPORT_BLOCK_DAYS = 10
REPORT_BLOCK_DELAY_SECONDS = 1

# Backwards-compatible names for callers that still reference detailed reports.
MAX_DETAILED_REPORT_DAYS = MAX_REPORT_BLOCK_DAYS
DETAILED_REPORT_BLOCK_DELAY_SECONDS = REPORT_BLOCK_DELAY_SECONDS


def split_date_range(start_date: str, end_date: str, max_days: int = MAX_REPORT_BLOCK_DAYS) -> list[tuple[str, str]]:
    """Splits an inclusive date range into contiguous blocks."""
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    if start > end:
        raise ValueError(f"Start date {start_date} cannot be after end date {end_date}.")

    blocks = []
    current = start

    while current <= end:
        block_end = min(current + datetime.timedelta(days=max_days - 1), end)
        blocks.append((current.strftime("%Y-%m-%d"), block_end.strftime("%Y-%m-%d")))
        current = block_end + datetime.timedelta(days=1)

    return blocks


def fetch_detailed_report(client: Any, url: str, query_params: dict[str, str]) -> list[dict] | dict | list | None:
    return fetch_report_in_blocks(client, url, query_params, identifier="detalhado")


def fetch_report_in_blocks(
    client: Any,
    url: str,
    query_params: dict[str, str],
    identifier: str,
) -> list[dict] | dict | list | None:
    """
    Fetches report data in smaller date blocks when the period is large.

    The API can return 503 for large ranges, so periods longer than
    MAX_REPORT_BLOCK_DAYS are never requested in a single call. The block
    responses are consolidated before the caller writes a single final file.
    """
    start_date = query_params.get("dtStart")
    end_date = query_params.get("dtEnd")

    if not start_date or not end_date:
        logger.error(f"Report {identifier} requires dtStart and dtEnd parameters.")
        return None

    blocks = split_date_range(start_date, end_date)

    if len(blocks) == 1:
        logger.info(f"Fetching report {identifier} in a single request.")

        try:
            return client.fetch_data(url, params=query_params)
        except Exception as exc:
            logger.error(f"Report {identifier} request failed: {exc}")
            return None

    logger.info(
        f"Fetching report {identifier} in date blocks to reduce API load: "
        f"{len(blocks)} blocks of up to {MAX_REPORT_BLOCK_DAYS} days."
    )

    records = []
    for block_start, block_end in blocks:
        records.extend(_fetch_report_block(client, url, query_params, identifier, block_start, block_end))

    if not records:
        logger.error(f"Report {identifier} slicing finished without any successful records.")
        return None

    consolidated = consolidate_report_records(records, identifier)
    logger.info(
        f"Report {identifier} slicing finished. "
        f"Collected {len(records)} records; consolidated {len(consolidated)} unique records."
    )

    return consolidated


def _fetch_report_block(
    client: Any,
    url: str,
    query_params: dict[str, str],
    identifier: str,
    block_start: str,
    block_end: str,
) -> list[dict]:
    block_params = dict(query_params)
    block_params["dtStart"] = block_start
    block_params["dtEnd"] = block_end

    logger.info(f"Fetching report {identifier} block: {block_start} to {block_end}")

    try:
        block_data = client.fetch_data(url, params=block_params)
    except Exception as exc:
        logger.error(f"Report {identifier} block failed ({block_start} to {block_end}): {exc}")
        block_data = None

    if block_data is None:
        return _retry_smaller_blocks(client, url, query_params, identifier, block_start, block_end)

    block_records = extract_records(block_data)
    logger.info(
        f"Report {identifier} block succeeded ({block_start} to {block_end}): "
        f"{len(block_records)} records."
    )

    delay_seconds = _get_block_delay_seconds()
    if delay_seconds:
        time.sleep(delay_seconds)

    return block_records


def _retry_smaller_blocks(
    client: Any,
    url: str,
    query_params: dict[str, str],
    identifier: str,
    block_start: str,
    block_end: str,
) -> list[dict]:
    start = datetime.datetime.strptime(block_start, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(block_end, "%Y-%m-%d").date()

    if start >= end:
        logger.error(f"Report {identifier} block returned no data ({block_start} to {block_end}).")
        return []

    total_days = (end - start).days + 1
    smaller_max_days = max(1, total_days // 2)
    smaller_blocks = split_date_range(block_start, block_end, smaller_max_days)

    logger.warning(
        f"Report {identifier} block returned no data ({block_start} to {block_end}). "
        f"Retrying as {len(smaller_blocks)} smaller blocks."
    )

    records = []
    for smaller_start, smaller_end in smaller_blocks:
        records.extend(_fetch_report_block(client, url, query_params, identifier, smaller_start, smaller_end))

    return records


def extract_records(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [data]

    logger.warning(f"Unsupported report response type: {type(data).__name__}")
    return []


def consolidate_records(records: list[dict]) -> list[dict]:
    unique_records = _deduplicate_records(records)
    date_column = _find_date_column(unique_records)

    if not date_column:
        logger.warning("No date column found in detailed report. Keeping API order after deduplication.")
        return unique_records

    df = pd.json_normalize(unique_records)
    df["_sort_date"] = pd.to_datetime(df[date_column], errors="coerce", dayfirst=True)
    sorted_indexes = df.sort_values(by=["_sort_date"], na_position="last").index.tolist()

    return [unique_records[index] for index in sorted_indexes]


def consolidate_report_records(records: list[dict], identifier: str) -> list[dict]:
    if identifier == "detalhado":
        return consolidate_records(records)

    return _aggregate_summary_records(records)


def _aggregate_summary_records(records: list[dict]) -> list[dict]:
    groups = {}
    average_values = defaultdict(lambda: defaultdict(list))

    for record in records:
        group_key = _summary_group_key(record)

        if group_key not in groups:
            groups[group_key] = {
                key: value for key, value in record.items() if not _is_numeric_value(value)
            }

        for field, value in record.items():
            if not _is_numeric_value(value):
                continue

            if _is_average_field(field):
                average_values[group_key][field].append(float(value))
                continue

            groups[group_key][field] = groups[group_key].get(field, 0) + value

    for group_key, fields in average_values.items():
        for field, values in fields.items():
            groups[group_key][field] = round(sum(values) / len(values), 2) if values else None

    return list(groups.values())


def _summary_group_key(record: dict) -> tuple:
    key_parts = []

    for field, value in record.items():
        if _is_numeric_value(value):
            continue

        key_parts.append((field, json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)))

    return tuple(key_parts)


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _is_average_field(field: str) -> bool:
    normalized = field.lower()
    return any(token in normalized for token in ("media", "média", "medio", "médio", "average", "avg", "tempo"))


def _get_block_delay_seconds() -> int | float:
    return min(REPORT_BLOCK_DELAY_SECONDS, DETAILED_REPORT_BLOCK_DELAY_SECONDS)


def _deduplicate_records(records: list[dict]) -> list[dict]:
    seen = set()
    unique_records = []

    for record in records:
        marker = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)

        if marker in seen:
            continue

        seen.add(marker)
        unique_records.append(record)

    return unique_records


def _find_date_column(records: list[dict]) -> str | None:
    if not records:
        return None

    df = pd.json_normalize(records)
    preferred_names = [
        "data",
        "date",
        "dt",
        "dataCriacao",
        "data_criacao",
        "dataAbertura",
        "data_abertura",
        "dtCriacao",
        "dt_criacao",
        "dtAbertura",
        "dt_abertura",
        "createdAt",
        "created_at",
    ]

    columns_by_lower = {column.lower(): column for column in df.columns}

    for name in preferred_names:
        column = columns_by_lower.get(name.lower())
        if column and _has_parseable_dates(df[column]):
            return column

    for column in df.columns:
        normalized = column.lower()
        if any(token in normalized for token in ("data", "date", "dt")) and _has_parseable_dates(df[column]):
            return column

    return None


def _has_parseable_dates(series: pd.Series) -> bool:
    parsed = pd.to_datetime(series.dropna(), errors="coerce", dayfirst=True)
    return parsed.notna().any()
