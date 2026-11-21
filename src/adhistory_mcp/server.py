"""adhistory-mcp: MCP server exposing adhistory's Apify Actors as tools for AI agents.

Each tool runs one public Apify Actor through Apify's run-sync API with the user's own
APIFY_TOKEN and returns the dataset items, trimmed to fit an agent's context.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__
from .apify import run_actor, shape_items

INSTRUCTIONS = (
    "Tools that run adhistory's Apify Actors: Google Ads Transparency Center ads, App Store and "
    "Google Play reviews, Greenhouse/Lever/Ashby, BambooHR, Workable, Personio and Recruitee job exports, remote jobs from six "
    "remote job boards, public Telegram channel posts, FDA recalls, SEC EDGAR filings and key financials, "
    "journalist source requests (#JournoRequest), PDF table, Word (.docx) table, bank "
    "statement, invoice, payslip and table-image extraction, email list cleaning, website screenshots, broken link "
    "and SSL certificate checks, and reading public Google Sheets. Each call runs on the user's Apify account and costs cents at the default limits; "
    "keep limits small unless the user asks for more."
)

mcp = MCPServer(
    name="adhistory-mcp",
    title="adhistory Apify tools",
    instructions=INSTRUCTIONS,
    website_url="https://apify.com/adhistory",
    version=__version__,
)

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

PdfUrls = Annotated[
    list[str],
    Field(
        min_length=1,
        max_length=20,
        description="Direct public links to PDF files (https://...). The file must download without a login.",
    ),
]
PdfPassword = Annotated[
    str | None, Field(description="Optional. Password for protected PDFs. Leave empty otherwise.")
]


def _need_any(**groups: Any) -> None:
    if not any(groups.values()):
        raise ToolError(f"Pass at least one of: {', '.join(groups)}.")


# --------------------------------------------------------------------------------------------
# Competitive intelligence
# --------------------------------------------------------------------------------------------


@mcp.tool(
    title="Competitor Google ads (Ads Transparency Center)",
    annotations=READ_ONLY,
    description=(
        "Get the ads a company or domain runs on Google (Search, YouTube, Shopping, Maps, Play, Display), "
        "read from the public Google Ads Transparency Center. Each item is one ad: advertiser name, format "
        "(text/image/video), headline and description for text ads, first and last shown dates, days running, "
        "per-country regions and platforms, and the Transparency Center link. Newest ads first; long-running ads "
        "are the proven ones. mode='advertiserCheck' returns one row per domain instead (advertises on Google "
        "yes/no, estimated ad count, live now, last ad date), useful to qualify a list of companies. "
        "Google does not publish spend or keywords. "
        "Cost: $1.00 per 1,000 results (an ad, or a checked domain) on the user's Apify account; the default "
        "20 ads cost about $0.02. Latency: usually 20-90 s, up to 5 min for large requests."
    ),
)
async def competitor_google_ads(
    domains: Annotated[
        list[str] | None,
        Field(description="Advertiser websites, e.g. ['hubspot.com']. URLs are fine.", max_length=20),
    ] = None,
    company_names: Annotated[
        list[str] | None,
        Field(description="Company names to look up in the Transparency Center; the best match is used.", max_length=20),
    ] = None,
    advertiser_ids: Annotated[
        list[str] | None,
        Field(description="Transparency Center advertiser IDs (start with AR).", max_length=20),
    ] = None,
    mode: Annotated[
        Literal["ads", "advertiserCheck"],
        Field(description="'ads' lists ads; 'advertiserCheck' returns one summary row per domain."),
    ] = "ads",
    max_ads_per_advertiser: Annotated[
        int, Field(ge=1, le=200, description="Newest ads first. Raise to reach older long-running ads.")
    ] = 20,
    country: Annotated[
        Literal[
            "ANY", "US", "GB", "CA", "AU", "NZ", "IE", "DE", "FR", "ES", "IT", "NL", "BE", "CH", "AT",
            "SE", "NO", "DK", "FI", "PL", "PT", "IN", "SG", "JP", "BR", "MX", "ZA", "AE",
        ],
        Field(description="Only ads shown in this country. ANY = all countries."),
    ] = "ANY",
    platform: Annotated[
        Literal["all", "search", "youtube", "shopping", "maps", "play"],
        Field(description="Only ads shown on this Google platform."),
    ] = "all",
    ad_format: Annotated[
        Literal["all", "text", "image", "video"],
        Field(description="text = Google Search ads; image and video cover Display and YouTube."),
    ] = "all",
    only_active_ads: Annotated[bool, Field(description="Keep only ads shown in the last 3 days.")] = False,
    date_from: Annotated[str | None, Field(description="Optional start date, YYYY-MM-DD.")] = None,
    date_to: Annotated[str | None, Field(description="Optional end date, YYYY-MM-DD.")] = None,
) -> dict[str, Any]:
    _need_any(domains=domains, company_names=company_names, advertiser_ids=advertiser_ids)
    actor = "google-ads-history-actor"
    n_inputs = len(domains or []) + len(company_names or []) + len(advertiser_ids or [])
    max_items = n_inputs if mode == "advertiserCheck" else n_inputs * max_ads_per_advertiser
    items = await run_actor(
        actor,
        {
            "mode": mode,
            "domains": domains,
            "searchTerms": company_names,
            "advertiserIds": advertiser_ids,
            "country": country,
            "platform": platform,
            "adFormat": ad_format,
            "maxAdsPerAdvertiser": max_ads_per_advertiser,
            "onlyActiveAds": only_active_ads,
            "dateFrom": date_from,
            "dateTo": date_to,
            "decodeAds": True,
            "includeCountryHistory": False,
        },
        timeout_s=300,
    )
    return shape_items(items, actor=actor, max_items=max(max_items, 1), max_list=10)


@mcp.tool(
    title="App Store & Google Play reviews",
    annotations=READ_ONLY,
    description=(
        "Get user reviews for iOS App Store and Google Play apps. Each item: store, app id and name, country, "
        "rating (1-5), title, review text, date, app version, helpful votes, developer reply and link. "
        "Filter by star rating (e.g. min 1 / max 2 for complaints only). Apps can be App Store URLs or IDs "
        "(324684580), Google Play URLs or package names (com.spotify.music), or an app name (App Store search). "
        "Cost: $0.10 per 1,000 reviews on the user's Apify account; the default 20 reviews per app cost a "
        "fraction of a cent. Latency: usually 10-40 s."
    ),
)
async def app_reviews(
    apps: Annotated[
        list[str],
        Field(min_length=1, max_length=10, description="App Store / Google Play URLs, IDs, package names or app names."),
    ],
    max_reviews_per_app: Annotated[
        int, Field(ge=1, le=500, description="Per app and country. The App Store returns at most 500.")
    ] = 20,
    countries: Annotated[
        list[str], Field(min_length=1, max_length=5, description="Two-letter country codes, e.g. ['us', 'gb'].")
    ] = ["us"],  # noqa: B006 - pydantic copies defaults
    sort: Annotated[Literal["newest", "relevant"], Field(description="Which reviews come first.")] = "newest",
    language: Annotated[str, Field(description="Google Play review language, e.g. en, es, de.")] = "en",
    min_rating: Annotated[int, Field(ge=1, le=5, description="Keep reviews with at least this many stars.")] = 1,
    max_rating: Annotated[int, Field(ge=1, le=5, description="Keep reviews with at most this many stars.")] = 5,
) -> dict[str, Any]:
    if min_rating > max_rating:
        raise ToolError("min_rating must be less than or equal to max_rating.")
    actor = "app-store-google-play-reviews-scraper"
    items = await run_actor(
        actor,
        {
            "apps": apps,
            "countries": countries,
            "maxReviewsPerApp": max_reviews_per_app,
            "sort": sort,
            "language": language,
            "minRating": min_rating,
            "maxRating": max_rating,
            "includeSummary": False,
        },
        timeout_s=180,
    )
    return shape_items(items, actor=actor, max_items=len(apps) * len(countries) * max_reviews_per_app, max_str=800)


# --------------------------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------------------------


@mcp.tool(
    title="Greenhouse, Lever & Ashby jobs",
    annotations=READ_ONLY,
    description=(
        "List open jobs from company job boards on Greenhouse, Lever or Ashby. Each item: ATS, company, title, "
        "department, team, location, remote flag, employment type, posted/updated dates, pay range when "
        "published, job and apply URLs, optional description text. "
        "Cost: $1.50 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.03. "
        "Latency: usually 5-30 s."
    ),
)
async def ats_jobs(
    boards: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "Job board links, e.g. https://boards.greenhouse.io/airbnb, https://jobs.lever.co/palantir, "
                "https://jobs.ashbyhq.com/openai"
            ),
        ),
    ],
    search_text: Annotated[
        str | None, Field(description="Optional. Keep jobs whose title, department or team contains all these words.")
    ] = None,
    location_contains: Annotated[str | None, Field(description="Optional. Keep jobs whose location contains this.")] = None,
    remote_only: Annotated[bool, Field(description="Keep only remote jobs.")] = False,
    include_description: Annotated[bool, Field(description="Add the job description text. Same price.")] = False,
    max_items_per_board: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per board so one big company does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "ats-jobs-export"
    items = await run_actor(
        actor,
        {
            "boards": boards,
            "searchText": search_text,
            "locationContains": location_contains,
            "remoteOnly": remote_only,
            "includeDescription": include_description,
            "maxItemsPerBoard": max_items_per_board,
            "maxItems": max_items,
        },
        timeout_s=180,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


@mcp.tool(
    title="BambooHR jobs",
    annotations=READ_ONLY,
    description=(
        "List open jobs from company careers pages on BambooHR (company.bamboohr.com/careers). Each item: title, "
        "company, department, employment type, city, state, country, location text, workplace type "
        "(on-site/remote/hybrid), remote flag, job and apply URLs; with include_description also posted date, "
        "minimum experience, pay text when the employer publishes it, and description text. Same field names as "
        "ats_jobs. Honest limits: you supply the companies (it does not discover who uses BambooHR); companies "
        "without a public careers page are skipped; most employers publish no pay. "
        "Cost: $0.80 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.016. "
        "Latency: usually 5-30 s (longer with descriptions, about one request per job)."
    ),
)
async def bamboohr_jobs(
    companies: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "BambooHR careers links (https://kiln.bamboohr.com/careers), a job link from that page, "
                "or just the part before .bamboohr.com (kiln)."
            ),
        ),
    ],
    search_text: Annotated[
        str | None, Field(description="Optional. Keep jobs whose title or department contains all these words.")
    ] = None,
    location_contains: Annotated[
        str | None, Field(description="Optional. Keep jobs whose city, state, country or workplace type contains this.")
    ] = None,
    department_contains: Annotated[
        str | None, Field(description="Optional. Keep jobs whose department contains this, e.g. sales.")
    ] = None,
    remote_only: Annotated[bool, Field(description="Keep only jobs the employer marked as remote.")] = False,
    include_description: Annotated[
        bool, Field(description="Add posted date, pay text, minimum experience and description. Slower, same price.")
    ] = False,
    max_items_per_company: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per company so one big employer does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "bamboohr-jobs-export"
    items = await run_actor(
        actor,
        {
            "companies": companies,
            "searchText": search_text,
            "locationContains": location_contains,
            "departmentContains": department_contains,
            "remoteOnly": remote_only,
            "includeDescription": include_description,
            "maxItemsPerCompany": max_items_per_company,
            "maxItems": max_items,
        },
        timeout_s=240,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


@mcp.tool(
    title="Workable jobs",
    annotations=READ_ONLY,
    description=(
        "List open jobs from company career pages on Workable (apply.workable.com/company). Each item: title, "
        "company, account, department, job function, employment type, experience level, city, region, country, "
        "country code, other locations of the same job, workplace type (remote/hybrid/on_site), remote flag, "
        "posted date (day only), job and apply URLs; with include_description also the description as text. "
        "Same field names as ats_jobs. Honest limits: you supply the companies (it does not discover who uses "
        "Workable); Workable publishes no pay, so pay is always empty; companies with no open jobs return nothing. "
        "Cost: $1.00 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.02. "
        "Latency: usually 5-30 s (one request per company plus one per job)."
    ),
)
async def workable_jobs(
    accounts: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "Workable career page links (https://apply.workable.com/skroutz), a job link from that page, "
                "or just the account name from the address (skroutz)."
            ),
        ),
    ],
    keywords: Annotated[
        list[str] | None,
        Field(description="Optional. Keep jobs whose title, department or job function contains any of these words."),
    ] = None,
    departments: Annotated[
        list[str] | None, Field(description="Optional. Keep jobs whose department contains one of these words.")
    ] = None,
    location_contains: Annotated[
        str | None,
        Field(description="Optional. Keep jobs whose city, region, country or two-letter country code contains this."),
    ] = None,
    remote_only: Annotated[bool, Field(description="Keep only jobs the employer marked as remote.")] = False,
    workplace_types: Annotated[
        list[Literal["remote", "hybrid", "on_site"]] | None,
        Field(description="Optional. Keep only these workplace types."),
    ] = None,
    include_description: Annotated[
        bool, Field(description="Add the full description as text and HTML. Larger output, same price.")
    ] = False,
    max_items_per_company: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per company so one big employer does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "workable-jobs-export"
    items = await run_actor(
        actor,
        {
            "accounts": accounts,
            "keywords": keywords,
            "departments": departments,
            "locationContains": location_contains,
            "remoteOnly": remote_only,
            "workplaceTypes": workplace_types,
            "includeDescription": include_description,
            "maxItemsPerAccount": max_items_per_company,
            "maxItems": max_items,
        },
        timeout_s=240,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


@mcp.tool(
    title="Personio jobs",
    annotations=READ_ONLY,
    description=(
        "List open jobs from company career pages on Personio (company.jobs.personio.de or .com). Each item: "
        "title, company (legal entity), account, department, team, office and additional offices, remote flag, "
        "employment type (permanent, internship, working student, trainee, fixed-term), schedule (full-/part-time), "
        "seniority, years of experience, keyword tags, posted date, salary min/max/currency/period plus a yearly "
        "figure and salaryText when the employer publishes it, job and apply URLs; with include_description also "
        "the description by section and as text. Same field names as ats_jobs. Honest limits: you supply the "
        "companies (it does not discover who uses Personio); most employers publish no salary; remote is read from "
        "the office name; texts are often German unless language='en' and the employer translated them. "
        "Cost: $0.80 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.016. "
        "Latency: usually 5-20 s (one request per company)."
    ),
)
async def personio_jobs(
    companies: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "Personio career page links (https://tado.jobs.personio.de), a job link from that page, "
                "or just the part before .jobs.personio (tado)."
            ),
        ),
    ],
    keywords: Annotated[
        list[str] | None,
        Field(description="Optional. Keep jobs whose title, department, team or keyword tags contain any of these words."),
    ] = None,
    departments: Annotated[
        list[str] | None, Field(description="Optional. Keep jobs whose department contains one of these words.")
    ] = None,
    location_contains: Annotated[
        str | None, Field(description="Optional. Keep jobs whose main or additional office contains this, e.g. Berlin.")
    ] = None,
    remote_only: Annotated[bool, Field(description="Keep only jobs whose office is Remote, Home office or similar.")] = False,
    employment_types: Annotated[
        list[str] | None,
        Field(description="Optional, e.g. permanent, intern, working_student, trainee, fixed_term, part-time."),
    ] = None,
    with_salary_only: Annotated[bool, Field(description="Keep only jobs with a published salary.")] = False,
    language: Annotated[
        str | None,
        Field(pattern=r"^[a-z]{2}$", description="Optional two-letter code, e.g. en, for translated job texts."),
    ] = None,
    include_description: Annotated[
        bool, Field(description="Add the description by section and as text and HTML. Larger output, same price.")
    ] = False,
    max_items_per_company: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per company so one big employer does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "personio-jobs-export"
    items = await run_actor(
        actor,
        {
            "companies": companies,
            "keywords": keywords,
            "departments": departments,
            "locationContains": location_contains,
            "remoteOnly": remote_only,
            "employmentTypes": employment_types,
            "withSalaryOnly": with_salary_only,
            "language": language,
            "includeDescription": include_description,
            "maxItemsPerCompany": max_items_per_company,
            "maxItems": max_items,
        },
        timeout_s=240,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


@mcp.tool(
    title="Recruitee jobs",
    annotations=READ_ONLY,
    description=(
        "List open jobs from company career sites on Recruitee (company.recruitee.com, also when the site runs on "
        "the company's own domain). Each item: title, company, account, department, category, tags, location, "
        "city, country, country code, all locations of a multi-location job, remote flag, work mode "
        "(hybrid/remote/on-site), employment type (permanent, fixed-term, part-time, internship ...), experience "
        "level, education level, hours per week min/max, posted date, closing date when set, salary "
        "min/max/currency/period plus a yearly figure and salaryText when the employer publishes it, job and apply "
        "URLs; with include_description also the description and requirements as text and HTML. Same field names "
        "as ats_jobs. Honest limits: you supply the companies (it does not discover who uses Recruitee, and it "
        "cannot search all Recruitee jobs); for a site on its own domain you need the Recruitee name "
        "(jobs.channable.com is channable); open jobs only; most employers publish no salary, and a range without "
        "a period has no yearly figure; a hybrid job has remote=false; companies with no open jobs return nothing. "
        "Cost: $0.80 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.016. "
        "Latency: usually 5-20 s (one request per company)."
    ),
)
async def recruitee_jobs(
    companies: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description=(
                "Recruitee career site links (https://bunq.recruitee.com), a job link from that site, "
                "or just the part before .recruitee.com (bunq)."
            ),
        ),
    ],
    keywords: Annotated[
        list[str] | None,
        Field(description="Optional. Keep jobs whose title, department, category or tags contain any of these words."),
    ] = None,
    departments: Annotated[
        list[str] | None, Field(description="Optional. Keep jobs whose department contains one of these words.")
    ] = None,
    location_contains: Annotated[
        str | None,
        Field(description="Optional. Keep jobs whose city, region, country or work mode contains this, e.g. Amsterdam."),
    ] = None,
    remote_only: Annotated[bool, Field(description="Keep only jobs the employer marked as remote.")] = False,
    employment_types: Annotated[
        list[str] | None,
        Field(description="Optional, e.g. permanent, fixed-term, part-time, internship, contract, freelance."),
    ] = None,
    with_salary_only: Annotated[bool, Field(description="Keep only jobs with a published salary.")] = False,
    language: Annotated[
        str | None,
        Field(pattern=r"^[a-z]{2}$", description="Optional two-letter code, e.g. en, for translated job texts."),
    ] = None,
    include_description: Annotated[
        bool, Field(description="Add the description and requirements as text and HTML. Larger output, same price.")
    ] = False,
    max_items_per_company: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per company so one big employer does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "recruitee-jobs-export"
    items = await run_actor(
        actor,
        {
            "companies": companies,
            "keywords": keywords,
            "departments": departments,
            "locationContains": location_contains,
            "remoteOnly": remote_only,
            "employmentTypes": employment_types,
            "withSalaryOnly": with_salary_only,
            "language": language,
            "includeDescription": include_description,
            "maxItemsPerCompany": max_items_per_company,
            "maxItems": max_items,
        },
        timeout_s=240,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


RemoteBoard = Literal["remotive", "remoteok", "weworkremotely", "jobicy", "himalayas", "arbeitnow"]


@mcp.tool(
    title="Remote jobs from 6 job boards",
    annotations=READ_ONLY,
    description=(
        "List current remote jobs from Remotive, Remote OK, We Work Remotely, Jobicy, Himalayas and Arbeitnow in "
        "one deduplicated list (same company + title is returned once), newest first. Each item: board "
        "(sourceName, sourceUrl), title, company, allowed location, job type, pay as posted plus parsed "
        "salaryMin/salaryMax/salaryCurrency/salaryPeriod and a yearly figure (salaryYearlyMin/Max), posted date, "
        "job and apply URLs, optional description text. Filter by keywords, location, age and pay. Returns what "
        "those six boards currently list, not the whole web; currencies are not converted. "
        "Cost: $1.00 per 1,000 jobs on the user's Apify account; the default 20 jobs cost $0.02. "
        "Latency: usually 5-30 s."
    ),
)
async def remote_jobs(
    search_text: Annotated[
        str | None,
        Field(description="Optional. Keep jobs whose title, company, category or tags contain all these words, e.g. 'python developer'."),
    ] = None,
    location_contains: Annotated[
        str | None, Field(description="Optional. Keep jobs whose allowed-location text contains this, e.g. Europe, USA, Worldwide.")
    ] = None,
    posted_within_days: Annotated[
        int | None, Field(ge=1, le=365, description="Optional. Only jobs posted in the last N days.")
    ] = None,
    sources: Annotated[
        list[RemoteBoard] | None,
        Field(min_length=1, max_length=6, description="Optional. Boards to read; default all six."),
    ] = None,
    salary_only: Annotated[bool, Field(description="Keep only jobs that show pay.")] = False,
    min_yearly_salary: Annotated[
        int | None,
        Field(ge=1, description="Optional. Keep jobs whose top pay, as a yearly amount in the job's own currency, is at least this."),
    ] = None,
    include_description: Annotated[bool, Field(description="Add the job description text. Same price.")] = False,
    only_new_since_last_run: Annotated[
        bool,
        Field(description="Skip jobs returned by an earlier run on this Apify account (for daily new-job feeds)."),
    ] = False,
    max_items_per_source: Annotated[
        int | None, Field(ge=1, le=200, description="Optional cap per board so one big board does not use the whole limit.")
    ] = None,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many jobs in total.")] = 20,
) -> dict[str, Any]:
    actor = "remote-jobs-aggregator"
    items = await run_actor(
        actor,
        {
            "sources": sources,
            "searchText": search_text,
            "locationContains": location_contains,
            "postedWithinDays": posted_within_days,
            "salaryOnly": salary_only,
            "minYearlySalary": min_yearly_salary,
            "includeDescription": include_description,
            "onlyNewSinceLastRun": only_new_since_last_run,
            "maxItemsPerSource": max_items_per_source,
            "maxItems": max_items,
        },
        timeout_s=180,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


@mcp.tool(
    title="Public Telegram channel posts",
    annotations=READ_ONLY,
    description=(
        "Read recent posts from public Telegram channels (the t.me/s web preview; no login, private channels and "
        "groups cannot be read). Each item: channel, post link and id, text, date, views, reactions, links, "
        "hashtags, mentions, emails, media flags, channel subscribers, plus analysis: views vs the channel's "
        "median (viewsVsMedian), view rank, view and reaction rate, weekday and hour. Filter by keywords, age and "
        "minimum views. Newest posts first; only what Telegram shows publicly. "
        "Cost: $0.35 per 1,000 posts on the user's Apify account; the default 20 posts cost $0.007. "
        "Latency: usually 5-30 s."
    ),
)
async def telegram_posts(
    channels: Annotated[
        list[str],
        Field(min_length=1, max_length=20, description="Public channels: username (durov), @username or https://t.me/name link."),
    ],
    max_posts_per_channel: Annotated[int, Field(ge=1, le=500, description="Newest posts to read per channel.")] = 20,
    posted_within_days: Annotated[
        int | None, Field(ge=1, le=3650, description="Optional. Stop at posts older than this many days.")
    ] = None,
    search_text: Annotated[
        str | None, Field(description="Optional. Keep posts whose text contains all these words.")
    ] = None,
    min_views: Annotated[int | None, Field(ge=0, description="Optional. Keep posts with at least this many views.")] = None,
    only_new_since_last_run: Annotated[
        bool, Field(description="Skip posts returned by an earlier run on this Apify account.")
    ] = False,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many posts in total.")] = 20,
) -> dict[str, Any]:
    actor = "telegram-channel-posts-scraper"
    items = await run_actor(
        actor,
        {
            "channels": channels,
            "maxPostsPerChannel": max_posts_per_channel,
            "postedWithinDays": posted_within_days,
            "searchText": search_text,
            "minViews": min_views,
            "onlyNewSinceLastRun": only_new_since_last_run,
            "maxItems": max_items,
        },
        timeout_s=180,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


# --------------------------------------------------------------------------------------------
# Public records and media requests
# --------------------------------------------------------------------------------------------


FdaCategory = Literal["food", "drug", "device"]


@mcp.tool(
    title="FDA recalls (food, drug, device)",
    annotations=READ_ONLY,
    description=(
        "List FDA recalls of food (incl. cosmetics and supplements), drugs and medical devices from the official "
        "openFDA enforcement data. Each item is one recalled product: category, recall number, classification "
        "(Class I is most serious), status, recalling firm and its address, product description, lot/code info, "
        "reason for recall, distribution pattern, quantity, voluntary or mandated, recall initiation, "
        "classification, report and termination dates, brand/generic/manufacturer names when openFDA links them, "
        "and the openFDA source link. Filter by keywords (whole words in product, firm or reason), class, status, "
        "firm state or country, and date range. Honest limits: recalls appear only after FDA classifies them "
        "(often 1 to a few weeks after the company announcement); meat/poultry (USDA), consumer products (CPSC) and "
        "vehicles (NHTSA) are not included; state/country filters use the firm's address, not where the product "
        "was sold. "
        "Cost: $1.00 per 1,000 recalls on the user's Apify account; the default 20 recalls cost $0.02. "
        "Latency: usually 5-30 s."
    ),
)
async def fda_recalls(
    categories: Annotated[
        list[FdaCategory] | None,
        Field(min_length=1, max_length=3, description="Optional. Recall databases to read; default all three."),
    ] = None,
    keywords: Annotated[
        list[str] | None,
        Field(max_length=20, description="Optional. Keep recalls mentioning any of these, e.g. ['listeria', 'peanut']."),
    ] = None,
    last_days: Annotated[
        int, Field(ge=0, le=36500, description="Recalls from the last N days. 0 = whole history since 2004. Ignored with date_from.")
    ] = 30,
    date_from: Annotated[str | None, Field(description="Optional start date, YYYY-MM-DD. Overrides last_days.")] = None,
    date_to: Annotated[str | None, Field(description="Optional end date, YYYY-MM-DD.")] = None,
    date_field: Annotated[
        Literal["reportDate", "recallInitiationDate", "centerClassificationDate"],
        Field(description="Which date the range applies to. reportDate = FDA weekly Enforcement Report date."),
    ] = "reportDate",
    classifications: Annotated[
        list[Literal["Class I", "Class II", "Class III"]] | None,
        Field(min_length=1, max_length=3, description="Optional. Keep only these classes."),
    ] = None,
    statuses: Annotated[
        list[Literal["Ongoing", "Completed", "Terminated", "Pending"]] | None,
        Field(min_length=1, max_length=4, description="Optional. Keep only these recall statuses."),
    ] = None,
    states: Annotated[
        list[str] | None,
        Field(max_length=60, description="Optional. Two-letter US state codes of the recalling firm, e.g. ['CA']."),
    ] = None,
    countries: Annotated[
        list[str] | None,
        Field(max_length=20, description="Optional. Recalling firm's country as FDA writes it, e.g. ['United States', 'India']."),
    ] = None,
    only_new_since_last_run: Annotated[
        bool, Field(description="Skip recalls returned by an earlier run on this Apify account (for alert feeds).")
    ] = False,
    max_results: Annotated[int, Field(ge=1, le=500, description="Stop after this many recalls.")] = 20,
) -> dict[str, Any]:
    actor = "fda-recalls-export"
    items = await run_actor(
        actor,
        {
            "categories": categories,
            "keywords": keywords,
            "lastDays": last_days,
            "dateFrom": date_from,
            "dateTo": date_to,
            "dateField": date_field,
            "classifications": classifications,
            "statuses": statuses,
            "states": states,
            "countries": countries,
            "onlyNewSinceLastRun": only_new_since_last_run,
            "maxResults": max_results,
        },
        timeout_s=180,
        limit=max_results,
    )
    return shape_items(items, actor=actor, max_items=max_results, max_str=400)


@mcp.tool(
    title="SEC EDGAR filings and key financials",
    annotations=READ_ONLY,
    description=(
        "List SEC EDGAR filings for companies by ticker or CIK, straight from SEC's free APIs. mode='filings': "
        "each item is one filing with company name, CIK, ticker, form (10-K, 10-Q, 8-K, 4, S-1, DEF 14A, 13F-HR "
        "...), filing date, report date, acceptance time, accession number, 8-K item numbers with plain-English "
        "descriptions, links to the main document, filing index and folder, file number, size, XBRL flags, SIC "
        "industry, exchange and state of incorporation. mode='financials': one row per 10-K/10-Q (or 20-F/40-F) "
        "with XBRL key numbers: revenue, gross profit, operating income, net income, EPS basic/diluted, "
        "operating cash flow, total assets and liabilities, equity, cash, long-term debt, shares outstanding, "
        "currency. Newest first. Honest limits: metadata and links only, the filing text is not downloaded or "
        "searched; XBRL fields can be empty when a company uses its own concept; delisted companies and many "
        "funds need a CIK. "
        "Cost: $0.40 per 1,000 rows (a filing, or a reporting period) on the user's Apify account; the default 20 "
        "rows cost under a cent. Latency: usually 5-30 s (longer for old date ranges)."
    ),
)
async def sec_filings(
    companies: Annotated[
        list[str],
        Field(min_length=1, max_length=20, description="Tickers (AAPL, BRK-B), CIKs (320193) or exact SEC company names."),
    ],
    mode: Annotated[
        Literal["filings", "financials"],
        Field(description="'filings' lists filings; 'financials' returns XBRL key numbers per 10-K/10-Q."),
    ] = "filings",
    form_types: Annotated[
        list[str] | None,
        Field(max_length=20, description="Optional. Keep only these forms, e.g. ['10-K', '8-K', '4']. Empty = every form."),
    ] = None,
    include_amendments: Annotated[bool, Field(description="With 10-K also return 10-K/A, and so on.")] = True,
    date_from: Annotated[str | None, Field(description="Optional. Filed on or after, YYYY-MM-DD.")] = None,
    date_to: Annotated[str | None, Field(description="Optional. Filed on or before, YYYY-MM-DD.")] = None,
    max_filings_per_company: Annotated[
        int, Field(ge=1, le=500, description="Newest first. In financials mode, reporting periods per company.")
    ] = 10,
    max_items: Annotated[int, Field(ge=1, le=500, description="Stop after this many rows in total.")] = 20,
) -> dict[str, Any]:
    actor = "sec-edgar-filings-export"
    items = await run_actor(
        actor,
        {
            "companies": companies,
            "mode": mode,
            "formTypes": form_types,
            "includeAmendments": include_amendments,
            "dateFrom": date_from,
            "dateTo": date_to,
            "maxFilingsPerCompany": max_filings_per_company,
            "maxItems": max_items,
        },
        timeout_s=180,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items, max_str=400)


@mcp.tool(
    title="Journalist requests (#JournoRequest feed)",
    annotations=READ_ONLY,
    description=(
        "List recent journalist source requests (#JournoRequest, #PRrequest, #MediaRequest and similar) posted on "
        "Bluesky and Mastodon, newest first, with duplicates merged. Each item: source, post URL, posted date, "
        "text, author handle, hashtags, language, parsed deadline (date and original text) and expired flag, "
        "outlet, request type (expert comment / case study / product / other), topics, how to respond (link, "
        "email or DM), links and emails in the post, the request service that posted it, times posted and other "
        "post links, likes/reposts/replies. Filter by keywords, age and deadline. Honest limits: roughly 3-10 new "
        "requests a day across the default hashtags; X/Twitter, LinkedIn and paid services (HARO/Connectively, "
        "Qwoted, Featured) are not included; deadline, outlet, type and topics are parsed from free text on a "
        "best-effort basis, so read the request before pitching. "
        "Cost: $1.00 per 1,000 requests on the user's Apify account; the default 20 requests cost $0.02. "
        "Latency: usually 10-60 s."
    ),
)
async def journalist_requests(
    keywords: Annotated[
        list[str] | None,
        Field(max_length=20, description="Optional. Keep requests mentioning any of these words, e.g. ['finance', 'startup']."),
    ] = None,
    exclude_keywords: Annotated[
        list[str] | None, Field(max_length=20, description="Optional. Drop requests mentioning any of these words.")
    ] = None,
    posted_within_days: Annotated[
        int, Field(ge=1, le=365, description="Only requests posted in the last N days.")
    ] = 7,
    skip_expired: Annotated[
        bool, Field(description="Drop requests whose deadline has passed (requests with no deadline are kept).")
    ] = False,
    sources: Annotated[
        list[Literal["bluesky", "mastodon"]] | None,
        Field(min_length=1, max_length=2, description="Optional. Networks to read; default both."),
    ] = None,
    hashtags: Annotated[
        list[str] | None,
        Field(max_length=20, description="Optional. Hashtags to read instead of the defaults (journorequest, prrequest, ...)."),
    ] = None,
    languages: Annotated[
        list[str] | None, Field(max_length=10, description="Optional. Two-letter language codes to keep, e.g. ['en'].")
    ] = None,
    only_new_since_last_run: Annotated[
        bool, Field(description="Skip requests returned by an earlier run on this Apify account (for daily alerts).")
    ] = False,
    max_items: Annotated[int, Field(ge=1, le=200, description="Stop after this many requests.")] = 20,
) -> dict[str, Any]:
    actor = "journalist-requests-feed"
    items = await run_actor(
        actor,
        {
            "hashtags": hashtags,
            "postedWithinDays": posted_within_days,
            "keywords": keywords,
            "excludeKeywords": exclude_keywords,
            "skipExpired": skip_expired,
            "onlyNewSinceLastRun": only_new_since_last_run,
            "sources": sources,
            "languages": languages,
            "maxItems": max_items,
        },
        timeout_s=180,
        limit=max_items,
    )
    return shape_items(items, actor=actor, max_items=max_items)


# --------------------------------------------------------------------------------------------
# Documents (public PDF links)
# --------------------------------------------------------------------------------------------


@mcp.tool(
    title="PDF tables to rows",
    annotations=READ_ONLY,
    description=(
        "Extract tables from PDF files at public URLs (text-based PDFs, not scans). Each item is one table: "
        "source PDF, pages, column names, row count, rows as objects (first 50 shown here), and links to the "
        "full table as CSV and Excel. Tables continuing across pages are merged. "
        "Cost: $2.00 per 1,000 tables on the user's Apify account (PDFs with no tables are free). "
        "Latency: usually 10-60 s depending on page count."
    ),
)
async def pdf_tables(
    pdf_urls: PdfUrls,
    pages: Annotated[str | None, Field(description="Optional page range, e.g. '1-3,7'. Empty reads every page.")] = None,
    strategy: Annotated[
        Literal["lines", "text"],
        Field(description="'lines' for tables with ruled borders, 'text' for tables aligned with spaces only."),
    ] = "lines",
    first_row_is_header: Annotated[bool, Field(description="Use the first row as column names.")] = True,
    merge_across_pages: Annotated[bool, Field(description="Join a table that continues on the next page.")] = True,
    min_rows: Annotated[int, Field(ge=1, le=100, description="Ignore tables with fewer data rows than this.")] = 2,
    pdf_password: PdfPassword = None,
    max_tables: Annotated[int, Field(ge=1, le=100, description="Stop after this many tables.")] = 10,
) -> dict[str, Any]:
    actor = "pdf-tables-to-excel"
    items = await run_actor(
        actor,
        {
            "pdfUrls": pdf_urls,
            "pages": pages,
            "strategy": strategy,
            "firstRowIsHeader": first_row_is_header,
            "mergeAcrossPages": merge_across_pages,
            "minRows": min_rows,
            "pdfPassword": pdf_password,
            "maxItems": max_tables,
        },
        timeout_s=240,
        limit=max_tables,
    )
    return shape_items(items, actor=actor, max_items=max_tables, max_list=50, max_str=300)


@mcp.tool(
    title="Bank statement PDF to transactions",
    annotations=READ_ONLY,
    description=(
        "Read bank statement PDFs at public URLs into structured data. Each item is one statement: bank, masked "
        "account number, currency, period, opening/closing balance, total credits/debits, a balance check "
        "(ok or mismatch), and transactions (date, description, debit, credit, amount, balance; first 150 shown "
        "here) plus an Excel link with all rows. Text-based PDFs only, not scans. "
        "Cost: $15.00 per 1,000 statements ($0.015 each) on the user's Apify account. Latency: usually 10-40 s."
    ),
)
async def bank_statement(
    pdf_urls: PdfUrls,
    date_order: Annotated[
        Literal["auto", "dmy", "mdy"],
        Field(description="How to read dates like 03/04/2026: auto-detect, day-first or month-first."),
    ] = "auto",
    pdf_password: PdfPassword = None,
    max_statements: Annotated[int, Field(ge=1, le=20, description="Stop after this many statements.")] = 5,
) -> dict[str, Any]:
    actor = "bank-statement-to-excel"
    items = await run_actor(
        actor,
        {"pdfUrls": pdf_urls, "dateOrder": date_order, "pdfPassword": pdf_password, "maxItems": max_statements},
        timeout_s=240,
        limit=max_statements,
    )
    return shape_items(items, actor=actor, max_items=max_statements, max_list=150, max_str=200)


@mcp.tool(
    title="Invoice PDF to data",
    annotations=READ_ONLY,
    description=(
        "Read invoice PDFs at public URLs into structured data. Each item is one invoice: invoice number, "
        "invoice and due dates, vendor, currency, subtotal, tax, total, line items (description, quantity, unit "
        "price, amount) and an Excel link. Text-based PDFs only, not scans. "
        "Cost: $5.00 per 1,000 invoices ($0.005 each) on the user's Apify account. Latency: usually 10-30 s."
    ),
)
async def invoice(
    pdf_urls: PdfUrls,
    extract_line_items: Annotated[bool, Field(description="Also read item rows. Off = header fields and totals only.")] = True,
    pdf_password: PdfPassword = None,
    max_invoices: Annotated[int, Field(ge=1, le=50, description="Stop after this many invoices.")] = 10,
) -> dict[str, Any]:
    actor = "invoice-pdf-to-excel"
    items = await run_actor(
        actor,
        {
            "pdfUrls": pdf_urls,
            "extractLineItems": extract_line_items,
            "pdfPassword": pdf_password,
            "maxItems": max_invoices,
        },
        timeout_s=240,
        limit=max_invoices,
    )
    return shape_items(items, actor=actor, max_items=max_invoices, max_list=50, max_str=300)


@mcp.tool(
    title="Payslip PDF to data",
    annotations=READ_ONLY,
    description=(
        "Read payslip PDFs at public URLs into structured data. Each item is one payslip: employee, employer, "
        "pay period and pay date, gross pay, tax, deductions, net pay, earnings lines (hours, rate, amount) and "
        "deduction lines, plus an Excel link. Text-based PDFs only, not scans. "
        "Cost: $5.00 per 1,000 payslips ($0.005 each) on the user's Apify account. Latency: usually 10-30 s."
    ),
)
async def payslip(
    pdf_urls: PdfUrls,
    extract_lines: Annotated[bool, Field(description="Also read earnings and deduction rows. Off = header fields and totals only.")] = True,
    pdf_password: PdfPassword = None,
    max_payslips: Annotated[int, Field(ge=1, le=50, description="Stop after this many payslips.")] = 10,
) -> dict[str, Any]:
    actor = "payslip-pdf-to-excel"
    items = await run_actor(
        actor,
        {"pdfUrls": pdf_urls, "extractLines": extract_lines, "pdfPassword": pdf_password, "maxItems": max_payslips},
        timeout_s=240,
        limit=max_payslips,
    )
    return shape_items(items, actor=actor, max_items=max_payslips, max_list=50, max_str=300)


@mcp.tool(
    title="Table in an image to data",
    annotations=READ_ONLY,
    description=(
        "Read tables out of pictures (screenshots, photos of printed tables; PNG, JPG, WEBP, BMP, TIFF) at public "
        "URLs using OCR. Each item is one table: rows and columns as text, the OCR confidence, plus CSV and Excel "
        "links. Honest limit: OCR can misread small or blurry text, so check numbers that matter. "
        "Cost: $2.00 per 1,000 tables ($0.002 each) on the user's Apify account. Latency: usually 10-40 s."
    ),
)
async def image_tables(
    image_urls: Annotated[
        list[str],
        Field(min_length=1, max_length=20, description="Direct public links to table images (https://...)."),
    ],
    first_row_is_header: Annotated[bool, Field(description="Use the first row as column names.")] = True,
    max_tables: Annotated[int, Field(ge=1, le=20, description="Stop after this many tables.")] = 5,
) -> dict[str, Any]:
    actor = "image-tables-to-excel"
    items = await run_actor(
        actor,
        {"imageUrls": image_urls, "firstRowIsHeader": first_row_is_header, "maxItems": max_tables},
        timeout_s=240,
        limit=max_tables,
    )
    return shape_items(items, actor=actor, max_items=max_tables, max_list=100, max_str=200)


@mcp.tool(
    title="Word document tables to rows",
    annotations=READ_ONLY,
    description=(
        "Extract every table from Word documents at public URLs. Each item is one table: source document, table "
        "number, the heading written above it, column names, row count, rows as objects keyed by the header "
        "(first 50 shown here), and links to the table as CSV and to the document's Excel file (one sheet per "
        "table). Merged cells are repeated into every cell they span; numbers like 1,250 come back as numbers. "
        "Honest limits: .docx files and Google Docs shared as 'Anyone with the link' only; old .doc (Word "
        "97-2003), PDF, .odt and .rtf are not read; links must download without a login. Use 'sample' as a "
        "link to try a built-in example. "
        "Cost: $1.50 per 1,000 tables on the user's Apify account (documents that fail or have no tables are free). "
        "Latency: usually 10-30 s."
    ),
)
async def word_tables_to_excel(
    doc_urls: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description="Links to .docx files or shared Google Docs (https://...), reachable without a login.",
        ),
    ],
    first_row_is_header: Annotated[bool, Field(description="Use each table's first row as column names.")] = True,
    repeat_merged_cells: Annotated[
        bool, Field(description="Copy a merged cell's value into every cell it spans.")
    ] = True,
    include_nested_tables: Annotated[bool, Field(description="Also return tables nested inside table cells.")] = True,
    min_rows: Annotated[int, Field(ge=1, le=100, description="Skip tables with fewer data rows than this.")] = 1,
    max_tables: Annotated[int, Field(ge=1, le=100, description="Stop after this many tables.")] = 10,
) -> dict[str, Any]:
    actor = "word-tables-to-excel"
    items = await run_actor(
        actor,
        {
            "docUrls": doc_urls,
            "firstRowIsHeader": first_row_is_header,
            "repeatMergedCells": repeat_merged_cells,
            "includeNestedTables": include_nested_tables,
            "minRows": min_rows,
            "maxItems": max_tables,
        },
        timeout_s=240,
        limit=max_tables,
    )
    return shape_items(items, actor=actor, max_items=max_tables, max_list=50, max_str=300)


@mcp.tool(
    title="Web page HTML tables to rows",
    annotations=READ_ONLY,
    description=(
        "Extract the data tables from public web pages (HTML <table> elements). Each item is one table: page URL, "
        "table number, its caption or the heading above it, column names (two-row headers joined), row count, rows "
        "as objects keyed by the header (first 50 shown here), and links to the table as CSV and to the page's "
        "Excel file (one sheet per table). Merged cells are repeated into every cell they span, footnote marks like "
        "[1] are removed, and 1,250 / $12.99 / 7.5% come back as numbers. Menus and layout tables are skipped. "
        "Honest limits: tables drawn by JavaScript after the page loads are not read; pages behind a login, or "
        "that answer 401/403 to automated requests (some large sites do), are reported as failed. Use 'sample' "
        "as a link to try a built-in example. "
        "Cost: $1.50 per 1,000 tables on the user's Apify account (pages that fail or have no tables are free). "
        "Latency: usually 5-30 s."
    ),
)
async def html_tables_to_excel(
    page_urls: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=20,
            description="Links to public web pages (https://...) that contain HTML tables.",
        ),
    ],
    first_row_is_header: Annotated[bool, Field(description="Use each table's header row as column names.")] = True,
    repeat_merged_cells: Annotated[
        bool, Field(description="Copy a merged cell's value into every cell it spans.")
    ] = True,
    skip_layout_tables: Annotated[
        bool, Field(description="Skip menus, navigation boxes, infoboxes and single-column layout tables.")
    ] = True,
    min_rows: Annotated[int, Field(ge=1, le=100, description="Skip tables with fewer data rows than this.")] = 2,
    max_tables: Annotated[int, Field(ge=1, le=100, description="Stop after this many tables.")] = 10,
) -> dict[str, Any]:
    actor = "html-tables-to-excel"
    items = await run_actor(
        actor,
        {
            "pageUrls": page_urls,
            "firstRowIsHeader": first_row_is_header,
            "repeatMergedCells": repeat_merged_cells,
            "skipLayoutTables": skip_layout_tables,
            "minRows": min_rows,
            "maxItems": max_tables,
        },
        timeout_s=240,
        limit=max_tables,
    )
    return shape_items(items, actor=actor, max_items=max_tables, max_list=50, max_str=300)


# --------------------------------------------------------------------------------------------
# Email and websites
# --------------------------------------------------------------------------------------------


@mcp.tool(
    title="Clean an email list (syntax, MX, disposable)",
    annotations=READ_ONLY,
    description=(
        "Check a list of email addresses at DNS level: valid syntax, whether the domain has mail (MX) records, "
        "disposable/temporary domains, role accounts (info@, sales@), free providers, and typo suggestions "
        "(gmial.com -> gmail.com). Each item: email, result (valid / invalid / risky / unknown), reason, score 0-100 and "
        "the individual checks. Honest limit: the mailbox itself is NOT checked (no SMTP probe), so a "
        "well-formed address on a working domain can still bounce. Duplicates are removed. "
        "Cost: $0.20 per 1,000 unique emails on the user's Apify account. Latency: usually 5-30 s."
    ),
)
async def clean_email_list(
    emails: Annotated[
        list[str] | None, Field(max_length=1000, description="Email addresses to check, up to 1,000 per call.")
    ] = None,
    csv_url: Annotated[
        str | None,
        Field(description="Or a public CSV link (e.g. Google Sheets 'publish to web' CSV) with an email column."),
    ] = None,
    max_results_returned: Annotated[
        int, Field(ge=1, le=500, description="How many result rows to return to the conversation.")
    ] = 200,
) -> dict[str, Any]:
    _need_any(emails=emails, csv_url=csv_url)
    actor = "email-list-cleaner-validator-syntax-mx-disposable"
    items = await run_actor(actor, {"emails": emails, "csvUrl": csv_url}, timeout_s=240)
    summary: dict[str, int] = {}
    for item in items:
        key = str(item.get("result", "unknown"))
        summary[key] = summary.get(key, 0) + 1
    return shape_items(
        items,
        actor=actor,
        max_items=max_results_returned,
        max_str=200,
        extra={"resultCounts": summary, "mailboxChecked": False},
    )


@mcp.tool(
    title="Website screenshot",
    annotations=READ_ONLY,
    description=(
        "Take a screenshot of public web pages and return an image URL for each (PNG or JPEG, hosted in the "
        "user's Apify storage). Each item: url, final URL, HTTP status, page title, screenshotUrl, size and "
        "viewport. Cookie banners and ads are hidden by default. Pages behind a login are not supported. "
        "Cost: $1.00 per 1,000 screenshots ($0.001 each) on the user's Apify account. "
        "Latency: usually 10-30 s per page."
    ),
)
async def website_screenshot(
    urls: Annotated[list[str], Field(min_length=1, max_length=10, description="Public page URLs.")],
    device: Annotated[Literal["desktop", "tablet", "mobile"], Field(description="Window size and browser type.")] = "desktop",
    full_page: Annotated[bool, Field(description="Whole scrollable page (up to 16,000 px) or just the first screen.")] = True,
    image_format: Annotated[Literal["png", "jpeg"], Field(description="PNG is sharper, JPEG is smaller.")] = "png",
    selector: Annotated[
        str | None, Field(description="Optional CSS selector to capture one element, e.g. '#pricing'.")
    ] = None,
    delay_seconds: Annotated[int, Field(ge=0, le=30, description="Extra wait for animations and late content.")] = 0,
    dark_mode: Annotated[bool, Field(description="Ask the page for its dark color scheme.")] = False,
    width: Annotated[int | None, Field(ge=200, le=3840, description="Optional viewport width override.")] = None,
    height: Annotated[int | None, Field(ge=200, le=4000, description="Optional viewport height override.")] = None,
) -> dict[str, Any]:
    actor = "website-screenshot-api"
    items = await run_actor(
        actor,
        {
            "urls": urls,
            "device": device,
            "fullPage": full_page,
            "format": image_format,
            "selector": selector,
            "delaySeconds": delay_seconds,
            "darkMode": dark_mode,
            "width": width,
            "height": height,
            "maxItems": len(urls),
        },
        timeout_s=240,
        limit=len(urls),
    )
    return shape_items(items, actor=actor, max_items=len(urls))


@mcp.tool(
    title="Broken link checker",
    annotations=READ_ONLY,
    description=(
        "Crawl a website from start URLs and check every link, image and script it finds. Each item: link URL, "
        "HTTP status, result (ok / broken / blocked, where blocked means the site refused automated checks), error, final URL after redirects, "
        "response time, internal or external, anchor text and the pages it was found on. By default only "
        "problems are returned. "
        "Cost: $1.00 per 1,000 result rows on the user's Apify account (with only_broken, working links are "
        "not charged). Latency: usually 20-120 s depending on site size."
    ),
)
async def broken_links(
    start_urls: Annotated[list[str], Field(min_length=1, max_length=5, description="Pages to start crawling from.")],
    only_broken: Annotated[bool, Field(description="Return only broken links and problems, not working links.")] = True,
    max_pages: Annotated[int, Field(ge=1, le=200, description="How many pages of the site to open and read for links.")] = 10,
    max_depth: Annotated[int, Field(ge=0, le=10, description="How many links deep to follow. 0 = start pages only.")] = 2,
    max_links: Annotated[int, Field(ge=1, le=2000, description="Upper limit of distinct links checked.")] = 300,
    check_external: Annotated[bool, Field(description="Also check links to other websites (checked, not crawled).")] = True,
    check_images_and_scripts: Annotated[bool, Field(description="Also check images, scripts, stylesheets and icons.")] = True,
) -> dict[str, Any]:
    actor = "broken-link-checker"
    items = await run_actor(
        actor,
        {
            "startUrls": start_urls,
            "onlyBroken": only_broken,
            "maxPages": max_pages,
            "maxDepth": max_depth,
            "maxLinks": max_links,
            "checkExternal": check_external,
            "checkImagesAndScripts": check_images_and_scripts,
        },
        timeout_s=300,
    )
    return shape_items(items, actor=actor, max_items=200, max_list=5, max_str=300)


@mcp.tool(
    title="SSL certificate checker",
    annotations=READ_ONLY,
    description=(
        "Check the SSL/TLS certificate of domains by opening a real TLS connection (port 443 by default). Each item "
        "is one domain: status (OK / EXPIRING_SOON / EXPIRED / INVALID / UNREACHABLE), problems and error text, days "
        "until expiry, valid from/to, issuer, subject, SAN list, hostname match, chain trusted (Mozilla CA bundle) "
        "and verify error, self-signed flag, TLS version, cipher, key type and size, signature algorithm, serial, "
        "SHA-256 fingerprint, IP and handshake time. Honest limits: public hosts only; no STARTTLS (use ports "
        "465/993/995, not 25/587); no revocation (OCSP/CRL) or cipher-suite audit. "
        "Cost: $2.00 per 1,000 domains ($0.002 each) on the user's Apify account; with only_problems, OK domains "
        "are not charged. Latency: usually 5-30 s."
    ),
)
async def ssl_certificates(
    domains: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=100,
            description="Domains, hostnames or URLs, e.g. example.com, https://shop.example.com/cart, mail.example.com:993.",
        ),
    ],
    port: Annotated[int, Field(ge=1, le=65535, description="TLS port for entries without their own :port.")] = 443,
    expiry_warning_days: Annotated[
        int, Field(ge=0, le=3650, description="Certificates expiring within this many days get EXPIRING_SOON.")
    ] = 30,
    only_problems: Annotated[bool, Field(description="Return only domains whose status is not OK.")] = False,
    timeout_secs: Annotated[
        int, Field(ge=1, le=60, description="Connection and handshake timeout per domain before UNREACHABLE.")
    ] = 10,
) -> dict[str, Any]:
    actor = "ssl-certificate-checker"
    items = await run_actor(
        actor,
        {
            "domains": domains,
            "port": port,
            "expiryWarningDays": expiry_warning_days,
            "onlyProblems": only_problems,
            "timeoutSecs": timeout_secs,
        },
        timeout_s=180,
        limit=len(domains),
    )
    summary: dict[str, int] = {}
    for item in items:
        key = str(item.get("status", "UNKNOWN"))
        summary[key] = summary.get(key, 0) + 1
    return shape_items(items, actor=actor, max_items=len(domains), max_list=10, extra={"statusCounts": summary})


@mcp.tool(
    title="Read a public Google Sheet",
    annotations=READ_ONLY,
    description=(
        "Read one tab of a Google Sheet into rows. Each item is one row as an object keyed by the header row's "
        "column names; numbers come back as numbers. Works on sheets shared as 'Anyone with the link can view' "
        "(no Google login or credentials); private sheets fail. Pick the tab by name, or by the #gid in the URL "
        "(default: the first tab). "
        "Cost: $0.10 per 1,000 rows on the user's Apify account; the default 200 rows cost about $0.02. "
        "Latency: usually 10-30 s."
    ),
)
async def read_google_sheet(
    spreadsheet: Annotated[
        str, Field(description="Google Sheets URL (https://docs.google.com/spreadsheets/d/.../edit#gid=...) or the spreadsheet ID.")
    ],
    sheet_name: Annotated[str | None, Field(description="Optional tab name. Empty uses the tab in the URL, else the first tab.")] = None,
    header_row: Annotated[int, Field(ge=1, le=100, description="Row that holds the column names.")] = 1,
    max_rows: Annotated[int, Field(ge=1, le=5000, description="Stop after this many data rows.")] = 200,
) -> dict[str, Any]:
    actor = "google-sheets-export-actor"
    items = await run_actor(
        actor,
        {
            "operation": "import",
            "spreadsheet": spreadsheet,
            "sheetName": sheet_name,
            "headerRow": header_row,
            "maxRows": max_rows,
        },
        timeout_s=180,
        limit=max_rows,
    )
    return shape_items(items, actor=actor, max_items=max_rows, max_str=300)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
