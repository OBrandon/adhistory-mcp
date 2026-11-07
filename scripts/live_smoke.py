"""Live smoke test: start the server over stdio and make two small real tool calls.

Costs about $0.01 on the Apify account behind the token. The token is read from APIFY_TOKEN or
~/.apify_token, passed to the server process via its environment, and never printed.

    python scripts/live_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


def load_token() -> str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        path = Path.home() / ".apify_token"
        if path.exists():
            token = path.read_text().strip()
    if not token:
        sys.exit("No token: set APIFY_TOKEN or create ~/.apify_token")
    return token


CALLS = [
    ("app_reviews", {"apps": ["com.spotify.music"], "max_reviews_per_app": 5}, ["store", "appName", "rating", "date"]),
    (
        "competitor_google_ads",
        {"domains": ["booqable.com"], "max_ads_per_advertiser": 3},
        ["advertiserName", "format", "headline", "daysShown"],
    ),
]


def data_of(result) -> dict:
    if result.structured_content:
        return result.structured_content
    return json.loads("".join(getattr(c, "text", "") for c in result.content))


async def main() -> None:
    token = load_token()
    env = dict(os.environ, APIFY_TOKEN=token)
    params = StdioServerParameters(command=sys.executable, args=["-m", "adhistory_mcp"], env=env)
    async with Client(params, read_timeout_seconds=400) as client:
        tools = (await client.list_tools()).tools
        print(f"tools listed: {len(tools)}")
        for name, args, fields in CALLS:
            result = await client.call_tool(name, args)
            if result.is_error:
                text = "".join(getattr(c, "text", "") for c in result.content).replace(token, "***")
                print(f"{name}: ERROR {text[:300]}")
                continue
            data = data_of(result)
            print(f"{name}: itemCount={data['itemCount']} totalItemsFromRun={data['totalItemsFromRun']}")
            for item in data["items"][:5]:
                print("   ", {k: item.get(k) for k in fields})


if __name__ == "__main__":
    asyncio.run(main())
