# adhistory-mcp

<!-- mcp-name: io.github.OBrandon/adhistory-mcp -->

An MCP server that gives AI agents (Claude Desktop, Claude Code, Cursor and any other MCP client)
twenty-four data tools: competitor Google ads, App Store and Google Play reviews, open jobs from
Greenhouse, Lever, Ashby, BambooHR, Workable, Personio, Recruitee and six remote job boards, public Telegram channel posts, FDA
recalls, SEC EDGAR filings and key financials, journalist source requests (#JournoRequest), PDF tables,
Word document tables, HTML tables from web pages, bank statements, invoices, payslips, tables in images, email list cleaning, website screenshots,
broken links, SSL certificate checks and public Google Sheets.

## Install

Paste this into Claude Desktop's `claude_desktop_config.json` (Settings → Developer → Edit Config)
or Cursor's `~/.cursor/mcp.json`, with your Apify API token
(**console.apify.com → Settings → API & Integrations**; a free account at
<https://console.apify.com/sign-up> is enough):

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

Apify's free monthly credits cover your first runs, so you can try every tool without paying
anything. Restart the client and the tools appear. `uvx` comes with [uv](https://docs.astral.sh/uv/)
(`curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux, or `brew install uv`).

Claude Code:

```bash
claude mcp add adhistory --env APIFY_TOKEN=apify_api_your_token_here -- uvx adhistory-mcp
```

## What it does

- **Competitor Google ads**: the Search, YouTube, Shopping and Display ads any company runs, from
  the Google Ads Transparency Center.
- **App reviews**: App Store and Google Play reviews, filterable to 1-2 star complaints.
- **Job postings**: open jobs from Greenhouse, Lever, Ashby, BambooHR, Workable,
  Personio and Recruitee careers pages, and remote jobs from six remote job boards (Remotive, Remote OK, We Work Remotely,
  Jobicy, Himalayas, Arbeitnow) with pay parsed.
- **Telegram channels**: posts from public channels with views, reactions and links, and which
  posts beat the channel's usual views.
- **FDA recalls**: food, drug and medical device recalls with class, firm, product, lot codes and
  reason, from openFDA.
- **SEC filings**: 10-K, 10-Q, 8-K, Form 4 and other EDGAR filings by ticker or CIK with document
  links, or XBRL key financials (revenue, net income, EPS, assets) per 10-K/10-Q.
- **Journalist requests**: #JournoRequest-style source requests from Bluesky and Mastodon, with
  deadline, outlet, request type and topics parsed.
- **Google Sheets**: read a tab of a public Google Sheet as rows keyed by column name.
- **PDF tables**: tables from PDF links as rows, plus CSV and Excel.
- **Word tables**: every table in .docx files or shared Google Docs as rows, plus CSV and Excel.
- **Bank statements**: statement PDFs as transactions, balances and a balance check.
- **Invoices**: invoice PDFs as number, dates, vendor, totals, tax and line items.
- **Payslips**: payslip PDFs as gross, tax, deductions, net pay and earnings lines.
- **Table images**: tables in screenshots or photos as rows, via OCR.
- **Email list cleaning**: syntax, MX, disposable, role-account and typo checks.
- **Website screenshots**: a full page screenshot (or first screen) of any public URL, as an image link.
- **Broken links**: crawl a site and list broken links, images and scripts.
- **SSL certificates**: days until expiry, issuer, hostname match and chain trust for a list of domains.

Each tool runs one public [Apify](https://apify.com/adhistory) Actor on your own Apify account and
returns the results as JSON, trimmed so they fit in an agent's context. You pay only the Actor's
per-result price, which at the default limits is a few cents or less per call.

## Other MCP clients

Any MCP client that can launch a stdio server works: command `uvx`, argument `adhistory-mcp`,
environment variable `APIFY_TOKEN`. Without `uv`: `pip install adhistory-mcp`, then run
`adhistory-mcp`.

## Tools

| Tool | What it returns | Price per 1,000 results | Default size | Typical time |
|---|---|---|---|---|
| `competitor_google_ads` | Ads a company runs on Google Search, YouTube, Shopping, Maps, Play and Display, from the Google Ads Transparency Center: headline and description of text ads, format, first/last shown, days running, countries, link. Or one summary row per domain (`mode: advertiserCheck`). | $1.00 | 20 ads per advertiser | 20-90 s |
| `app_reviews` | App Store and Google Play reviews: rating, title, text, date, app version, developer reply. Star filter for complaints only. | $0.10 | 20 per app | 10-40 s |
| `ats_jobs` | Open jobs from Greenhouse, Lever and Ashby boards: department, location, remote flag, pay when published. | $1.50 | 20 jobs | 5-30 s |
| `bamboohr_jobs` | Open jobs from BambooHR careers pages (`company.bamboohr.com/careers`): department, location, on-site/remote/hybrid; optional posted date, pay text and description. Same fields as `ats_jobs`. | $0.80 | 20 jobs | 5-30 s |
| `workable_jobs` | Open jobs from Workable career pages (`apply.workable.com/company`): department, job function, experience level, location, remote/hybrid/on-site, posted date; optional description. Same fields as `ats_jobs`. | $1.00 | 20 jobs | 5-30 s |
| `personio_jobs` | Open jobs from Personio career pages (`company.jobs.personio.de`): department, offices, remote flag, employment type (incl. working student, trainee), seniority, salary with a yearly figure when published; optional description. Same fields as `ats_jobs`. | $0.80 | 20 jobs | 5-20 s |
| `recruitee_jobs` | Open jobs from Recruitee career sites (`company.recruitee.com`, also on the company's own domain): department, category, tags, locations, hybrid/remote/on-site, employment type, experience level, hours per week, salary with a yearly figure when published; optional description and requirements. Same fields as `ats_jobs`. | $0.80 | 20 jobs | 5-20 s |
| `remote_jobs` | Remote jobs from Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas and Arbeitnow, deduplicated: company, allowed location, posted date, apply link, pay parsed to min/max/currency/period and a yearly figure. Filters for keywords, location, age and minimum pay. | $1.00 | 20 jobs | 5-30 s |
| `telegram_posts` | Posts from public Telegram channels: text, date, views, reactions, links, hashtags, plus views vs the channel median, view rate and best hour. Filters for keywords, age and minimum views. | $0.35 | 20 posts | 5-30 s |
| `fda_recalls` | FDA food, drug and medical device recalls from openFDA: class, status, firm, product, lot codes, reason, distribution, dates. Filters for keywords, class, status, firm state and date range. | $1.00 | 20 recalls, last 30 days | 5-30 s |
| `sec_filings` | SEC EDGAR filings by ticker or CIK: form, dates, accession number, 8-K items in plain English, document links. Or XBRL key financials per 10-K/10-Q (`mode: financials`). | $0.40 | 20 rows | 5-30 s |
| `journalist_requests` | Journalist source requests (#JournoRequest, #PRrequest ...) from Bluesky and Mastodon: text, parsed deadline, outlet, request type, topics, how to respond. | $1.00 | 20 requests, last 7 days | 10-60 s |
| `pdf_tables` | Tables from PDF links as rows, plus CSV and Excel links. | $2.00 | 10 tables | 10-60 s |
| `word_tables_to_excel` | Every table in Word (.docx) files or Google Docs shared by link: heading above it, columns, rows keyed by header (merged cells filled in), plus CSV and Excel links. No old .doc files. | $1.50 | 10 tables | 10-30 s |
| `html_tables_to_excel` | Data tables from public web pages: caption or heading above it, columns (two-row headers joined), rows keyed by header (merged cells filled in, footnote marks removed), plus CSV and Excel links. Menus and layout tables skipped; no JavaScript-drawn tables. | $1.50 | 10 tables | 5-30 s |
| `bank_statement` | Bank statement PDFs as balances, totals, a balance check and transactions, plus Excel. | $15.00 | 5 statements | 10-40 s |
| `invoice` | Invoice PDFs as number, dates, vendor, totals, tax and line items, plus Excel. | $5.00 | 10 invoices | 10-30 s |
| `payslip` | Payslip PDFs as employee, pay period, gross, tax, deductions, net pay, earnings and deduction lines, plus Excel. | $5.00 | 10 payslips | 10-30 s |
| `image_tables` | Tables in images (screenshots, photos) as rows and columns via OCR, plus CSV and Excel. | $2.00 | 5 tables | 10-40 s |
| `clean_email_list` | Syntax, MX record, disposable, role account and typo checks per email, with a valid/invalid/risky/unknown result. | $0.20 | up to 1,000 emails | 5-30 s |
| `website_screenshot` | Full-page or first-screen PNG/JPEG of public pages, returned as image URLs. | $1.00 | 1 per URL (max 10) | 10-30 s per page |
| `broken_links` | Crawls a site and reports broken links, images and scripts with status, error and the pages they appear on. | $1.00 | 10 pages, problems only | 20-120 s |
| `ssl_certificates` | SSL/TLS certificate per domain: status (OK, EXPIRING_SOON, EXPIRED, INVALID, UNREACHABLE), days until expiry, issuer, SANs, hostname match, chain trust, TLS version. | $2.00 | 1 per domain (max 100) | 5-30 s |
| `read_google_sheet` | Rows from a public Google Sheet tab, keyed by column name. | $0.10 | 200 rows | 10-30 s |

Each Actor also charges $0.00005 per run start. Prices are the Actors' public Apify Store prices
at the time of writing; the Store page of each Actor is the source of truth.

### Example prompts

- "What Google Search ads is hubspot.com running in the US right now? Group them by message."
  → `competitor_google_ads(domains=["hubspot.com"], country="US", platform="search", only_active_ads=true)`
- "Which of these 20 domains advertise on Google?" → `competitor_google_ads(domains=[...], mode="advertiserCheck")`
- "Summarize the last 50 one- and two-star reviews of Notion on iOS and Android."
  → `app_reviews(apps=["notion", "notion.id"], max_reviews_per_app=25, max_rating=2)`
- "Which data roles are open at Airbnb and Palantir?"
  → `ats_jobs(boards=["https://boards.greenhouse.io/airbnb", "https://jobs.lever.co/palantir"], search_text="data")`
- "What is Kiln hiring for on BambooHR, with posted dates?"
  → `bamboohr_jobs(companies=["https://kiln.bamboohr.com/careers"], include_description=true)`
- "Which remote roles are open at Hack The Box on Workable?"
  → `workable_jobs(accounts=["https://apply.workable.com/hack-the-box-ltd"], workplace_types=["remote"])`
- "Which tado and Chrono24 jobs publish a salary? Show it per year."
  → `personio_jobs(companies=["tado", "chrono24"], with_salary_only=true, language="en")`
- "Which engineering jobs at bunq, Fastned and Channable publish a salary?"
  → `recruitee_jobs(companies=["bunq", "fastned", "channable"], keywords=["engineer"], with_salary_only=true)`
- "Find remote Python jobs posted this week that pay at least $120k."
  → `remote_jobs(search_text="python", posted_within_days=7, min_yearly_salary=120000)`
- "Which of these Telegram channels' posts got the most views this month?"
  → `telegram_posts(channels=["durov", "telegram"], posted_within_days=30, min_views=100000)`
- "Any Class I food recalls for listeria in the last 30 days?"
  → `fda_recalls(categories=["food"], keywords=["listeria"], classifications=["Class I"])`
- "List Apple's 8-K filings this year and what each was about."
  → `sec_filings(companies=["AAPL"], form_types=["8-K"], date_from="2026-01-01")`
- "Find open journalist requests about personal finance I can still answer."
  → `journalist_requests(keywords=["finance", "mortgage"], skip_expired=true)`
- "Pull the table on pages 1-3 of this PDF into rows." → `pdf_tables(pdf_urls=["https://.../report.pdf"], pages="1-3")`
- "Put every table in this Word contract into Excel." → `word_tables_to_excel(doc_urls=["https://.../contract.docx"])`
- "Put the rate tables from this Federal Reserve page into Excel." → `html_tables_to_excel(page_urls=["https://www.federalreserve.gov/releases/h15/"])`
- "Total the debits in this statement by merchant." → `bank_statement(pdf_urls=["https://.../statement.pdf"])`
- "Turn these payslips into one net-pay-by-month table." → `payslip(pdf_urls=[...])`
- "Get the table out of this screenshot." → `image_tables(image_urls=["https://.../table.png"])`
- "Which of these emails will likely bounce?" → `clean_email_list(emails=[...])`
- "Screenshot our pricing page on mobile." → `website_screenshot(urls=["example.com/pricing"], device="mobile")`
- "Find broken links on example.com." → `broken_links(start_urls=["https://example.com"])`
- "Which of our domains have SSL certificates expiring in the next 30 days?"
  → `ssl_certificates(domains=["example.com", "shop.example.com"], only_problems=true)`
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
- `html_tables_to_excel` reads the HTML the server sends; tables drawn by JavaScript after the page
  loads are not read, and sites that answer 401/403 to automated requests are reported as failed.
- `word_tables_to_excel` reads .docx files and Google Docs shared as "Anyone with the link"; old
  Word 97-2003 `.doc`, `.odt` and `.rtf` files must be saved as .docx first.
- `competitor_google_ads` reads what Google publishes in the Transparency Center. Google does not
  publish ad spend, keywords or click data.
- Pages behind a login are not supported by `website_screenshot` and `broken_links`.
- `remote_jobs` returns what the six remote boards list right now, not every remote job on the
  web. Pay is parsed from the posting where the board has no pay field; currencies are not converted.
- `fda_recalls` lists recalls after FDA classifies them (often 1 to a few weeks after the company's
  announcement); USDA meat/poultry and CPSC consumer product recalls are not included.
- `sec_filings` returns filing metadata and links, not the filing text.
- `journalist_requests` reads public Bluesky and Mastodon hashtags only (not X, LinkedIn or paid
  services); deadline, outlet and topics are parsed from free text on a best-effort basis.
- `ssl_certificates` checks public hosts over plain TLS; no STARTTLS, revocation or cipher audit.

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
