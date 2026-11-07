"""Thin client for Apify's run-sync-get-dataset-items endpoint, plus output trimming.

The API token is read from the APIFY_TOKEN environment variable and only ever sent in the
Authorization header. It is never put in a URL, an error message or a log line.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from mcp.server.mcpserver.exceptions import ToolError

API_BASE = "https://api.apify.com/v2"
ACTOR_OWNER = "adhistory"
TOKEN_ENV = "APIFY_TOKEN"
MAX_CHARGE_ENV = "APIFY_MAX_CHARGE_USD"
DEFAULT_MAX_CHARGE_USD = 0.50
SYNC_WAIT_LIMIT_S = 300  # Apify answers run-sync calls with 408 after 300 s.

# httpx logs every request URL at INFO; keep stderr quiet (the token is never in the URL anyway).
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN_HELP = (
    "APIFY_TOKEN is not set. This server runs Apify Actors with your own Apify account. "
    "Create a free account at https://console.apify.com/sign-up, copy your token from "
    "console.apify.com -> Settings -> API & Integrations, and add it to this server's "
    'config as an environment variable, e.g. "env": {"APIFY_TOKEN": "apify_api_..."}.'
)

# Response shaping, so one call fits comfortably in an agent's context window.
MAX_STRING_CHARS = 600
MAX_NESTED_LIST = 25
MAX_RESPONSE_CHARS = 60_000


def get_token() -> str:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if not token:
        raise ToolError(TOKEN_HELP)
    return token


def max_charge_usd() -> float:
    raw = os.environ.get(MAX_CHARGE_ENV, "").strip()
    if not raw:
        return DEFAULT_MAX_CHARGE_USD
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MAX_CHARGE_USD
    return value if value > 0 else DEFAULT_MAX_CHARGE_USD


def actor_url(actor: str) -> str:
    return f"{API_BASE}/acts/{ACTOR_OWNER}~{actor}/run-sync-get-dataset-items"


def _api_error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            return str(err.get("message") or err.get("type") or "")[:500]
    except (ValueError, json.JSONDecodeError):
        pass
    return resp.text[:300]


def _raise_for_status(resp: httpx.Response, actor: str, timeout_s: int) -> None:
    if resp.status_code < 400:
        return
    detail = _api_error_message(resp)
    code = resp.status_code
    if code == 401:
        msg = (
            "Apify rejected the API token (401). Check APIFY_TOKEN: copy it again from "
            "console.apify.com -> Settings -> API & Integrations."
        )
    elif code == 402:
        msg = (
            "Apify says the account cannot pay for this run (402). Free accounts get monthly "
            "platform credit; check usage at console.apify.com -> Billing."
        )
    elif code == 403:
        msg = f"Apify refused the run (403): {detail}"
    elif code == 404:
        msg = f"Actor {ACTOR_OWNER}/{actor} was not found on Apify (404): {detail}"
    elif code == 408:
        msg = (
            f"The Actor run took longer than {timeout_s} s and was stopped. Ask for fewer "
            "results (lower the limit or pass fewer inputs) and try again."
        )
    elif code == 429:
        msg = "Apify rate limit reached (429). Wait a few seconds and retry."
    elif code == 400:
        msg = f"Apify rejected the input or the run failed (400): {detail}"
    else:
        msg = f"Apify returned HTTP {code}: {detail}"
    raise ToolError(msg)


async def run_actor(
    actor: str,
    actor_input: dict[str, Any],
    *,
    timeout_s: int = 120,
    limit: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Run an Actor synchronously and return its dataset items."""
    token = get_token()
    timeout_s = max(10, min(int(timeout_s), SYNC_WAIT_LIMIT_S))
    params: dict[str, Any] = {
        "timeout": timeout_s,
        "clean": "true",
        "maxTotalChargeUsd": f"{max_charge_usd():.2f}",
    }
    if limit is not None:
        params["limit"] = int(limit)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "adhistory-mcp",
    }
    body = {k: v for k, v in actor_input.items() if v is not None}

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_s + 30, connect=15))
    try:
        resp = await client.post(actor_url(actor), params=params, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise ToolError(
            f"No answer from Apify within {timeout_s + 30} s. Ask for fewer results and try again."
        ) from exc
    except httpx.HTTPError as exc:
        raise ToolError(f"Could not reach the Apify API: {type(exc).__name__}") from exc
    finally:
        if owns_client:
            await client.aclose()

    _raise_for_status(resp, actor, timeout_s)
    try:
        data = resp.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise ToolError("Apify returned a response that is not JSON.") from exc
    if not isinstance(data, list):
        raise ToolError("Apify returned an unexpected response (expected a list of items).")
    return [item for item in data if isinstance(item, dict)]


def _trim(value: Any, max_str: int, max_list: int) -> Any:
    if isinstance(value, str):
        if len(value) > max_str:
            return value[:max_str] + f"... [+{len(value) - max_str} chars]"
        return value
    if isinstance(value, list):
        out = [_trim(v, max_str, max_list) for v in value[:max_list]]
        if len(value) > max_list:
            out.append(f"... [+{len(value) - max_list} more, see the Excel/CSV link if present]")
        return out
    if isinstance(value, dict):
        return {
            k: _trim(v, max_str, max_list)
            for k, v in value.items()
            if not (isinstance(k, str) and k.lower().endswith("html"))
        }
    return value


def shape_items(
    items: list[dict[str, Any]],
    *,
    actor: str,
    max_items: int,
    max_str: int = MAX_STRING_CHARS,
    max_list: int = MAX_NESTED_LIST,
    max_chars: int = MAX_RESPONSE_CHARS,
    drop_keys: tuple[str, ...] = (),
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trim long text, cap nested lists and the item count, and keep the JSON under max_chars."""
    total = len(items)
    kept: list[Any] = []
    size = 0
    for item in items[:max_items]:
        slim = _trim({k: v for k, v in item.items() if k not in drop_keys}, max_str, max_list)
        n = len(json.dumps(slim, ensure_ascii=False, default=str))
        if kept and size + n > max_chars:
            break
        kept.append(slim)
        size += n
    result: dict[str, Any] = {
        "actor": f"{ACTOR_OWNER}/{actor}",
        "itemCount": len(kept),
        "totalItemsFromRun": total,
    }
    if extra:
        result.update(extra)
    if len(kept) < total:
        result["note"] = (
            f"Showing {len(kept)} of {total} items to fit the context window. "
            "Long text fields and nested lists are shortened."
        )
    result["items"] = kept
    return result
