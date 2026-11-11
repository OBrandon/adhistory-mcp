# adhistory-mcp

<!-- mcp-name: io.github.OBrandon/adhistory-mcp -->

An MCP server that gives AI agents (Claude Desktop, Claude Code, Cursor and any other MCP client)
fifteen data tools for jobs people actually ask an assistant to do:

- **Competitor Google ads**: the Search, YouTube, Shopping and Display ads any company runs, from
  the Google Ads Transparency Center.
- **App reviews**: App Store and Google Play reviews, filterable to 1-2 star complaints.
- **Job postings**: open jobs from Workday career sites, Greenhouse, Lever and Ashby boards, and
  remote jobs from six remote job boards (Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas,
  Arbeitnow) with pay parsed.
- **PDF tables**: tables from PDF links as rows, plus CSV and Excel.
- **Bank statements**: statement PDFs as transactions, balances and a balance check.
- **Invoices**: invoice PDFs as number, dates, vendor, totals, tax and line items.
- **Payslips**: payslip PDFs as gross, tax, deductions, net pay and earnings lines.
- **Table images**: tables in screenshots or photos as rows, via OCR.
- **Email list cleaning**: syntax, MX, disposable, role-account and typo checks.
- **Website screenshots**: full-page or first-screen images of public pages.
- **Broken links**: crawl a site and list broken links, images and scripts.

Each tool runs one public [Apify](https://apify.com/adhistory) Actor on your own Apify account and
returns the results as JSON, trimmed so they fit in an agent's context. You need a free Apify API
token. You pay only the Actor's per-result price, which at the default limits is a few cents or less
per call, and Apify's free monthly platform credits cover your first runs, so you can try every tool
without paying anything.

## Quick start

1. Create a free Apify account at <https://console.apify.com/sign-up>.
2. Copy your API token: **console.apify.com → Settings → API & Integrations**.
3. Add the server to your MCP client (examples below). It runs locally over stdio with
   [`uvx`](https://docs.astral.sh/uv/), so you need `uv` installed
   (`curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux, or `brew install uv`).

### Claude Desktop

Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "adhistory": {
      "command": "uvx",
      "args": ["adhistory-mcp"],
      "env": { "APIFY_TOKEN": "apify_api_your_token_here" }
    }
  }
}
```

Restart Claude Desktop. The tools appear under the tools icon.

### Claude Code

```bash
claude mcp add adhistory --env APIFY_TOKEN=apify_api_your_token_here -- uvx adhistory-mcp
```

### Cursor

Add to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project):

```json
{
  "mcpServers": {
    "adhistory": {
      "command": "uvx",
      "args": ["adhistory-mcp"],
      "env": { "APIFY_TOKEN": "apify_api_your_token_here" }
    }
  }
}
```

### Other clients

Any MCP client that can launch a stdio server works: command `uvx`, argument `adhistory-mcp`,
environment variable `APIFY_TOKEN`. Without `uv`: `pip install adhistory-mcp`, then run
`adhistory-mcp`.

## Tools

| Tool | What it returns | Price per 1,000 results | Default size | Typical time |
|---|---|---|---|---|
| `competitor_google_ads` | Ads a company runs on Google Search, YouTube, Shopping, Maps, Play and Display, from the Google Ads Transparency Center: headline and description of text ads, format, first/last shown, days running, countries, link. Or one summary row per domain (`mode: advertiserCheck`). | $1.00 | 20 ads per advertiser | 20-90 s |
| `app_reviews` | App Store and Google Play reviews: rating, title, text, date, app version, developer reply. Star filter for complaints only. | $0.10 | 20 per app | 10-40 s |
| `workday_jobs` | Open jobs from any `*.myworkdayjobs.com` career site; optional description, pay range, apply link. | $1.00 | 20 jobs | 10-60 s |
| `ats_jobs` | Open jobs from Greenhouse, Lever and Ashby boards: department, location, remote flag, pay when published. | $1.50 | 20 jobs | 5-30 s |
| `remote_jobs` | Remote jobs from Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas and Arbeitnow, deduplicated: company, allowed location, posted date, apply link, pay parsed to min/max/currency/period and a yearly figure. Filters for keywords, location, age and minimum pay. | $1.00 | 20 jobs | 5-30 s |
| `telegram_posts` | Posts from public Telegram channels: text, date, views, reactions, links, hashtags, plus views vs the channel median, view rate and best hour. Filters for keywords, age and minimum views. | $0.35 | 20 posts | 5-30 s |
| `pdf_tables` | Tables from PDF links as rows, plus CSV and Excel links. | $2.00 | 10 tables | 10-60 s |
| `bank_statement` | Bank statement PDFs as balances, totals, a balance check and transactions, plus Excel. | $15.00 | 5 statements | 10-40 s |
| `invoice` | Invoice PDFs as number, dates, vendor, totals, tax and line items, plus Excel. | $5.00 | 10 invoices | 10-30 s |
| `payslip` | Payslip PDFs as employee, pay period, gross, tax, deductions, net pay, earnings and deduction lines, plus Excel. | $5.00 | 10 payslips | 10-30 s |
| `image_tables` | Tables in images (screenshots, photos) as rows and columns via OCR, plus CSV and Excel. | $2.00 | 5 tables | 10-40 s |
| `clean_email_list` | Syntax, MX record, disposable, role account and typo checks per email, with a valid/invalid/risky/unknown result. | $0.20 | up to 1,000 emails | 5-30 s |
| `website_screenshot` | Full-page or first-screen PNG/JPEG of public pages, returned as image URLs. | $1.00 | 1 per URL (max 10) | 10-30 s per page |
| `broken_links` | Crawls a site and reports broken links, images and scripts with status, error and the pages they appear on. | $1.00 | 10 pages, problems only | 20-120 s |
| `read_google_sheet` | Rows from a public Google Sheet tab, keyed by column name. | $0.10 | 200 rows | 10-30 s |

Each Actor also charges $0.00005 per run start. Prices are the Actors' public Apify Store prices
at the time of writing; the Store page of each Actor is the source of truth.

### Example prompts

- "What Google Search ads is hubspot.com running in the US right now? Group them by message."
  → `competitor_google_ads(domains=["hubspot.com"], country="US", platform="search", only_active_ads=true)`
- "Which of these 20 domains advertise on Google?" → `competitor_google_ads(domains=[...], mode="advertiserCheck")`
- "Summarize the last 50 one- and two-star reviews of Notion on iOS and Android."
  → `app_reviews(apps=["notion", "notion.id"], max_reviews_per_app=25, max_rating=2)`
- "List NVIDIA's remote software jobs posted this week."
  → `workday_jobs(career_site_urls=["https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"], search_text="software", location_contains="Remote", posted_within_days=7)`
- "Which data roles are open at Airbnb and Palantir?"
  → `ats_jobs(boards=["https://boards.greenhouse.io/airbnb", "https://jobs.lever.co/palantir"], search_text="data")`
- "Find remote Python jobs posted this week that pay at least $120k."
  → `remote_jobs(search_text="python", posted_within_days=7, min_yearly_salary=120000)`
- "Which of these Telegram channels' posts got the most views this month?"
  → `telegram_posts(channels=["durov", "telegram"], posted_within_days=30, min_views=100000)`
- "Pull the table on pages 1-3 of this PDF into rows." → `pdf_tables(pdf_urls=["https://.../report.pdf"], pages="1-3")`
- "Total the debits in this statement by merchant." → `bank_statement(pdf_urls=["https://.../statement.pdf"])`
- "Turn these payslips into one net-pay-by-month table." → `payslip(pdf_urls=[...])`
- "Get the table out of this screenshot." → `image_tables(image_urls=["https://.../table.png"])`
- "Which of these emails will likely bounce?" → `clean_email_list(emails=[...])`
- "Screenshot our pricing page on mobile." → `website_screenshot(urls=["example.com/pricing"], device="mobile")`
- "Find broken links on example.com." → `broken_links(start_urls=["https://example.com"])`
- "Read the leads tab of this Google Sheet and find rows missing an email." → `read_google_sheet(spreadsheet="https://docs.google.com/spreadsheets/d/.../edit", sheet_name="leads")`

## Cost control

- Defaults are small, so a typical call costs well under $0.10.
- Every run is capped by Apify's `maxTotalChargeUsd`, $0.50 per call by default. Set the
  environment variable `APIFY_MAX_CHARGE_USD` (for example `2`) to allow larger runs.
- Free Apify accounts include monthly platform credit, which covers many small calls.

## Limits

- Calls are synchronous and Apify stops waiting after 300 seconds, so very large requests fail
  with a clear message; ask for fewer results instead.
- Responses are trimmed for the agent: long text fields are shortened, nested lists (table rows,
  transactions) are capped, and at most about 60,000 characters of JSON are returned. Full tables
  and statements are in the CSV/Excel links the PDF tools return.
- `clean_email_list` works at DNS level. It does not connect to the mail server, so it cannot
  tell whether a specific mailbox exists.
- The PDF tools need text-based PDFs at public URLs; scanned images are not read. Local files
  must be uploaded somewhere public first.
- `competitor_google_ads` reads what Google publishes in the Transparency Center. Google does not
  publish ad spend, keywords or click data.
- Pages behind a login are not supported by `website_screenshot` and `broken_links`.
- `remote_jobs` returns what the six remote boards list right now, not every remote job on the
  web. Pay is parsed from the posting where the board has no pay field; currencies are not converted.

## Privacy

The server runs on your machine. Inputs go only to the Apify API under your account, and the
token is sent only in the `Authorization` header to `api.apify.com`. Results are stored in your
Apify account's storage under its normal retention.

## Development

```bash
uv sync --group dev
uv run pytest
uv run adhistory-mcp   # starts the stdio server
```

## License

MIT
