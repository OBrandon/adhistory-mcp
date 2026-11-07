"""End-to-end: start the real server as a subprocess and talk MCP over stdio."""

from __future__ import annotations

import os
import sys

from mcp import Client, StdioServerParameters

from test_tools import EXPECTED_TOOLS, text_of


def server_params(env_extra: dict[str, str] | None = None) -> StdioServerParameters:
    env = {k: v for k, v in os.environ.items() if k != "APIFY_TOKEN"}
    env.update(env_extra or {})
    return StdioServerParameters(command=sys.executable, args=["-m", "adhistory_mcp"], env=env)


async def test_stdio_initialize_and_list_tools():
    async with Client(server_params()) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == EXPECTED_TOOLS
    by_name = {t.name: t for t in tools}
    schema = by_name["competitor_google_ads"].input_schema
    assert "domains" in schema["properties"]
    assert by_name["app_reviews"].input_schema["required"] == ["apps"]


async def test_stdio_call_without_token_returns_tool_error():
    async with Client(server_params()) as client:
        result = await client.call_tool("website_screenshot", {"urls": ["https://example.com"]})
    assert result.is_error
    assert "console.apify.com" in text_of(result)
