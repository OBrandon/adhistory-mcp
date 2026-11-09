"""Unit tests: every tool against a mocked Apify API (no network, no real token)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp import Client

from adhistory_mcp.apify import API_BASE, shape_items
from adhistory_mcp.server import mcp

FAKE_TOKEN = "apify_api_FAKE_TEST_TOKEN_123"

EXPECTED_TOOLS = {
    "competitor_google_ads",
    "app_reviews",
    "workday_jobs",
    "ats_jobs",
    "remote_jobs",
    "telegram_posts",
    "pdf_tables",
    "bank_statement",
    "invoice",
    "payslip",
    "image_tables",
    "clean_email_list",
    "website_screenshot",
    "broken_links",
}


def url(actor: str) -> str:
    return f"{API_BASE}/acts/adhistory~{actor}/run-sync-get-dataset-items"


def text_of(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


def payload(result) -> dict:
    if result.structured_content:
        sc = result.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
    return json.loads(text_of(result))


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", FAKE_TOKEN)
    monkeypatch.delenv("APIFY_MAX_CHARGE_USD", raising=False)


async def test_lists_all_tools():
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS
    for t in tools:
        assert "per 1,000" in t.description, t.name
        assert "Latency" in t.description, t.name


async def test_missing_token_gives_clear_error(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    async with Client(mcp) as client:
        result = await client.call_tool("app_reviews", {"apps": ["com.spotify.music"]})
    assert result.is_error
    msg = text_of(result)
    assert "APIFY_TOKEN" in msg
    assert "Settings -> API & Integrations" in msg


CASES = [
    (
        "competitor_google_ads",
        {"domains": ["booqable.com"], "max_ads_per_advertiser": 5, "country": "US", "platform": "search"},
        "google-ads-history-actor",
        {
            "mode": "ads",
            "domains": ["booqable.com"],
            "country": "US",
            "platform": "search",
            "adFormat": "all",
            "maxAdsPerAdvertiser": 5,
            "decodeAds": True,
        },
    ),
    (
        "app_reviews",
        {"apps": ["com.spotify.music"], "max_reviews_per_app": 5, "max_rating": 2},
        "app-store-google-play-reviews-scraper",
        {"apps": ["com.spotify.music"], "countries": ["us"], "maxReviewsPerApp": 5, "minRating": 1, "maxRating": 2},
    ),
    (
        "workday_jobs",
        {"career_site_urls": ["https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"], "search_text": "rust"},
        "workday-jobs-export",
        {
            "careerSiteUrls": ["https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"],
            "searchText": "rust",
            "includeDescription": False,
            "maxItems": 20,
        },
    ),
    (
        "ats_jobs",
        {"boards": ["https://boards.greenhouse.io/airbnb"], "remote_only": True, "max_items": 7},
        "ats-jobs-export",
        {"boards": ["https://boards.greenhouse.io/airbnb"], "remoteOnly": True, "maxItems": 7},
    ),
    (
        "remote_jobs",
        {"search_text": "python", "posted_within_days": 7, "sources": ["remoteok", "himalayas"], "min_yearly_salary": 100000},
        "remote-jobs-aggregator",
        {
            "sources": ["remoteok", "himalayas"],
            "searchText": "python",
            "postedWithinDays": 7,
            "salaryOnly": False,
            "minYearlySalary": 100000,
            "includeDescription": False,
            "onlyNewSinceLastRun": False,
            "maxItems": 20,
        },
    ),
    (
        "telegram_posts",
        {"channels": ["durov"], "min_views": 1000, "max_items": 5},
        "telegram-channel-posts-scraper",
        {
            "channels": ["durov"],
            "maxPostsPerChannel": 20,
            "minViews": 1000,
            "onlyNewSinceLastRun": False,
            "maxItems": 5,
        },
    ),
    (
        "pdf_tables",
        {"pdf_urls": ["https://example.com/a.pdf"], "pages": "1-3", "strategy": "text"},
        "pdf-tables-to-excel",
        {"pdfUrls": ["https://example.com/a.pdf"], "pages": "1-3", "strategy": "text", "maxItems": 10},
    ),
    (
        "bank_statement",
        {"pdf_urls": ["https://example.com/s.pdf"], "date_order": "dmy"},
        "bank-statement-to-excel",
        {"pdfUrls": ["https://example.com/s.pdf"], "dateOrder": "dmy", "maxItems": 5},
    ),
    (
        "invoice",
        {"pdf_urls": ["https://example.com/i.pdf"], "extract_line_items": False},
        "invoice-pdf-to-excel",
        {"pdfUrls": ["https://example.com/i.pdf"], "extractLineItems": False, "maxItems": 10},
    ),
    (
        "payslip",
        {"pdf_urls": ["https://example.com/p.pdf"], "extract_lines": False},
        "payslip-pdf-to-excel",
        {"pdfUrls": ["https://example.com/p.pdf"], "extractLines": False, "maxItems": 10},
    ),
    (
        "image_tables",
        {"image_urls": ["https://example.com/t.png"]},
        "image-tables-to-excel",
        {"imageUrls": ["https://example.com/t.png"], "firstRowIsHeader": True, "maxItems": 5},
    ),
    (
        "clean_email_list",
        {"emails": ["a@example.com", "b@gmial.com"]},
        "email-list-cleaner-validator-syntax-mx-disposable",
        {"emails": ["a@example.com", "b@gmial.com"]},
    ),
    (
        "website_screenshot",
        {"urls": ["https://example.com"], "device": "mobile", "image_format": "jpeg"},
        "website-screenshot-api",
        {"urls": ["https://example.com"], "device": "mobile", "format": "jpeg", "maxItems": 1},
    ),
    (
        "broken_links",
        {"start_urls": ["https://example.com"]},
        "broken-link-checker",
        {"startUrls": ["https://example.com"], "onlyBroken": True, "maxPages": 10, "maxDepth": 2},
    ),
]


@pytest.mark.parametrize("tool,args,actor,expected_input", CASES, ids=[c[0] for c in CASES])
@respx.mock
async def test_tool_calls_right_actor_with_mapped_input(token, tool, args, actor, expected_input):
    route = respx.post(url(actor)).mock(return_value=httpx.Response(201, json=[{"ok": 1}, {"ok": 2}]))
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert not result.is_error, text_of(result)
    assert route.called
    req = route.calls.last.request
    assert req.headers["Authorization"] == f"Bearer {FAKE_TOKEN}"
    assert FAKE_TOKEN not in str(req.url)  # token only in the header
    assert req.url.params["clean"] == "true"
    assert req.url.params["maxTotalChargeUsd"] == "0.50"
    assert int(req.url.params["timeout"]) <= 300
    sent = json.loads(req.content)
    for key, value in expected_input.items():
        assert sent[key] == value, key
    assert all(v is not None for v in sent.values())  # None values are not sent
    data = payload(result)
    assert data["actor"] == f"adhistory/{actor}"
    assert data["totalItemsFromRun"] == 2 and data["itemCount"] >= 1


@respx.mock
async def test_max_charge_env_override(token, monkeypatch):
    monkeypatch.setenv("APIFY_MAX_CHARGE_USD", "2")
    route = respx.post(url("broken-link-checker")).mock(return_value=httpx.Response(201, json=[]))
    async with Client(mcp) as client:
        await client.call_tool("broken_links", {"start_urls": ["https://example.com"]})
    assert route.calls.last.request.url.params["maxTotalChargeUsd"] == "2.00"


@pytest.mark.parametrize(
    "status,needle",
    [
        (401, "rejected the API token"),
        (402, "cannot pay"),
        (404, "not found"),
        (408, "longer than"),
        (429, "rate limit"),
        (400, "Input is not valid"),
        (500, "HTTP 500"),
    ],
)
@respx.mock
async def test_http_errors_are_readable_and_never_leak_token(token, status, needle):
    respx.post(url("ats-jobs-export")).mock(
        return_value=httpx.Response(status, json={"error": {"type": "x", "message": "Input is not valid"}})
    )
    async with Client(mcp) as client:
        result = await client.call_tool("ats_jobs", {"boards": ["https://jobs.lever.co/palantir"]})
    assert result.is_error
    msg = text_of(result)
    assert needle in msg
    assert FAKE_TOKEN not in msg


@respx.mock
async def test_network_error(token):
    respx.post(url("ats-jobs-export")).mock(side_effect=httpx.ConnectError("boom"))
    async with Client(mcp) as client:
        result = await client.call_tool("ats_jobs", {"boards": ["https://jobs.lever.co/palantir"]})
    assert result.is_error
    assert "Could not reach the Apify API" in text_of(result)


async def test_google_ads_needs_an_advertiser(token):
    async with Client(mcp) as client:
        result = await client.call_tool("competitor_google_ads", {})
    assert result.is_error
    assert "domains" in text_of(result)


async def test_email_needs_input(token):
    async with Client(mcp) as client:
        result = await client.call_tool("clean_email_list", {})
    assert result.is_error


async def test_rating_range_validated(token):
    async with Client(mcp) as client:
        result = await client.call_tool("app_reviews", {"apps": ["x"], "min_rating": 4, "max_rating": 2})
    assert result.is_error


async def test_limit_out_of_range_rejected(token):
    async with Client(mcp) as client:
        result = await client.call_tool("ats_jobs", {"boards": ["https://jobs.lever.co/x"], "max_items": 100000})
    assert result.is_error


@respx.mock
async def test_email_summary_counts(token):
    items = [{"email": "a@x.com", "result": "valid"}, {"email": "b@x", "result": "invalid"}, {"email": "c@x.com", "result": "valid"}]
    respx.post(url("email-list-cleaner-validator-syntax-mx-disposable")).mock(return_value=httpx.Response(201, json=items))
    async with Client(mcp) as client:
        result = await client.call_tool("clean_email_list", {"emails": ["a@x.com", "b@x", "c@x.com"]})
    data = payload(result)
    assert data["resultCounts"] == {"valid": 2, "invalid": 1}
    assert data["mailboxChecked"] is False


def test_shape_items_trims_text_lists_html_and_size():
    items = [
        {
            "title": "t",
            "descriptionText": "x" * 5000,
            "descriptionHtml": "<p>big</p>",
            "rows": list(range(100)),
        }
        for _ in range(30)
    ]
    out = shape_items(items, actor="a", max_items=20, max_str=100, max_list=10, max_chars=3000)
    assert out["totalItemsFromRun"] == 30
    assert 1 <= out["itemCount"] < 20  # cut by the character budget
    first = out["items"][0]
    assert "descriptionHtml" not in first
    assert first["descriptionText"].startswith("x" * 100) and "+4900 chars" in first["descriptionText"]
    assert len(first["rows"]) == 11 and "+90 more" in first["rows"][-1]
    assert "note" in out
    assert len(json.dumps(out["items"])) <= 3000 + 500


def test_shape_items_caps_item_count():
    out = shape_items([{"i": i} for i in range(50)], actor="a", max_items=5)
    assert out["itemCount"] == 5 and out["totalItemsFromRun"] == 50


@respx.mock
async def test_remote_jobs_defaults_read_all_boards(token):
    route = respx.post(url("remote-jobs-aggregator")).mock(return_value=httpx.Response(201, json=[]))
    async with Client(mcp) as client:
        result = await client.call_tool("remote_jobs", {})
    assert not result.is_error, text_of(result)
    req = route.calls.last.request
    sent = json.loads(req.content)
    assert "sources" not in sent  # Actor default: all six boards
    assert sent["maxItems"] == 20 and req.url.params["limit"] == "20"


async def test_remote_jobs_rejects_unknown_board(token):
    async with Client(mcp) as client:
        result = await client.call_tool("remote_jobs", {"sources": ["linkedin"]})
    assert result.is_error
