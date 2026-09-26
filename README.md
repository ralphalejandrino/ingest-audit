# ingest-audit

**What does a page cost the thing reading it?**

Compression makes that question easy to get wrong. A CDN reports bytes on the wire; a parser, a crawler and a context window all pay for bytes *after* decompression. When those two numbers diverge far enough, a page can look perfectly healthy on every dashboard and still be too large to ingest.

This is a small, dependency-free script that measures both, ranks the gap across a whole sitemap, and then asks a second question about the worst offender: **is that weight carrying anything current?**

Built in a 45-minute window for a Flywheel Motion assessment, against `ctaio.dev`. It works on any sitemap-driven site.

```bash
python3 ingest_audit.py https://ctaio.dev/sitemap.xml
python3 ingest_audit.py https://example.com/sitemap.xml --limit 40 --workers 4
```

No install step, standard library only — so the numbers below can be reproduced rather than taken on trust. Full output: [`report.md`](report.md).

---

## What it found on ctaio.dev

422 URLs measured, 0 failures. **Median page: 59 KB.**

| Page | After decompression | Over the wire | Ratio | vs median | `<tr>` |
|---|---:|---:|---:|---:|---:|
| `/en/jobs/` | **26.6 MB** | 421 KB | 65× | **462×** | 19,379 |
| `/en/salary/h1b-salary-database/` | 6.8 MB | 176 KB | 40× | 118× | 1 |
| `/en/jobs/remote/` | 2.5 MB | 55 KB | 46× | 43× | 1 |
| `/en/jobs/engineering-manager/` | 2.3 MB | 49 KB | 49× | 41× | 1 |
| `/en/jobs/senior-software-engineer/` | 1.6 MB | 37 KB | 43× | 28× | 1 |

Eight of the ten heaviest pages on the site are in the `/en/jobs/` tree, so this is a property of the section, not one bad page.

`/en/jobs/` costs **421 KB to deliver and 26.6 MB to read** — a 65× gap. Cloudflare returns a cache HIT and every wire-level metric looks fine.

## The second question

The heaviest page carries 19,379 rows under a column the site itself labels **Posted**, each with a machine-readable `data-posted` attribute. The script reads that field — staleness here is the site's own declared data, not an inference.

**19,378 stamps parsed from 19,379 rows (100% of data rows; the one miss is the header).**

| Age of listing | Count | Share |
|---|---:|---:|
| ≤ 7 days | 0 | 0.0% |
| 8–30 days | 47 | 0.2% |
| 31–90 days | 1,061 | 5.5% |
| 91–365 days | 17,763 | 91.7% |
| Over a year | 507 | 2.6% |

- Median listing age: **209 days**
- Older than 30 days: **99.8%**
- Older than 90 days: **94.3%**
- Oldest: **1,734 days** (2021-12-27) · Newest: **15 days**
- Largest source: `hn` — 15,073 rows (78%), scraped Hacker News "Who is hiring" threads, which are monthly and ephemeral by design

## So the two findings are one finding

The page is 26.6 MB **because nothing expires.** It isn't a rendering problem sitting next to a content problem.

**Retiring rows older than 90 days removes 94.3% of them and takes the page from 26.6 MB to roughly 1.5 MB.** That is a retention rule, not an engineering project — and the site already has the architecture for it: `/en/jobs/remote/data-engineer/` and its siblings are faceted sub-pages, so the slicing exists. What's missing is an expiry.

### Why it matters beyond page weight

A jobs index where 99.8% of rows are over a month old and none are under a week old is a page that answers a visitor's question wrongly. And at 26.6 MB it is unlikely to be ingested whole by a crawler or a model — so the rows that *are* current may never be retrieved or cited. For a site whose Labs section is currently running an experiment on what moves AI citations, the supply side is worth measuring too.

## Method, and its limits

- Each URL is requested once with `Accept-Encoding: gzip`; the script records the compressed length and the decompressed length from the same response, so the two figures are directly comparable.
- `<tr>` is counted as a proxy for row-level DOM cost. It is a proxy, not a DOM measurement — a headless render would be more accurate and much slower.
- Ages are computed against a fixed `--today` so a run is reproducible after the fact.
- Failures are reported, never swallowed: a page that could not be measured is listed separately rather than dropped from the median.
- 6 concurrent requests against a Cloudflare-cached static site, one pass.

Measured 2026-09-26.

---

## Portfolio-wide run (added after the assessment window)

The submission noted this as unfinished. Running the same script across all three properties, same day, same `--today`:

| Property | Pages | Median page | Heaviest page | Heaviest ÷ median |
|---|---:|---:|---:|---:|
| `ctaio.dev` | 422 | 59 KB | **26.6 MB** (`/en/jobs/`) | **462×** |
| `prommer.net` | 474 | 279 KB | 358 KB | 1× |
| `wetheflywheel.com` | 306 | 56 KB | 208 KB | 4× |

**1,202 pages measured, 0 failures — and `/en/jobs/` is the only page anywhere near pathological.** The other two properties have no outlier: `prommer.net`'s heaviest page is barely above its own median, and `wetheflywheel.com`'s tops out at 208 KB.

That matters more than a list of offenders would. It means the 26.6 MB is not a house pattern or a framework artifact — it is one un-expired table in one tree, and 8 of the 10 heaviest pages on `ctaio.dev` sit in that same tree.

One incidental observation: `prommer.net` carries a **279 KB median**, roughly five times `ctaio.dev`'s and `wetheflywheel.com`'s. Nothing is broken there — it is uniformly heavy rather than spiked, which is a different question (shared page furniture) and a much smaller one.
