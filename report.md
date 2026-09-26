# Ingest audit — https://ctaio.dev/sitemap.xml

## Delivered weight — 422 pages measured, 0 failed

Median page: **59 KB**

| Page | After decompression | Over the wire | Ratio | vs median | `<tr>` |
|---|---:|---:|---:|---:|---:|
| `/en/jobs/` | 26.6 MB | 421 KB | 65× | 462× | 19,379 |
| `/en/salary/h1b-salary-database/` | 6.8 MB | 176 KB | 40× | 118× | 1 |
| `/en/jobs/remote/` | 2.5 MB | 55 KB | 46× | 43× | 1 |
| `/en/jobs/engineering-manager/` | 2.3 MB | 49 KB | 49× | 41× | 1 |
| `/en/jobs/senior-software-engineer/` | 1.6 MB | 37 KB | 43× | 28× | 1 |
| `/en/jobs/hybrid/` | 1.3 MB | 36 KB | 38× | 23× | 1 |
| `/en/jobs/remote/engineering-manager/` | 869 KB | 27 KB | 32× | 15× | 1 |
| `/en/jobs/remote/senior-software-engineer/` | 610 KB | 22 KB | 27× | 10× | 1 |
| `/en/jobs/director-engineering/` | 446 KB | 45 KB | 10× | 8× | 1 |
| `/en/jobs/cto/` | 425 KB | 24 KB | 18× | 7× | 1 |

**The gap is the finding.** `/en/jobs/` costs 421 KB to deliver and 26.6 MB to read — a 65× difference. Compression hides it from every CDN-level check; the parser and the context window still pay full price.

## Is that weight carrying anything current?

Parsed **19,378** `data-posted` stamps from 19,379 rows (100.0% of data rows).

| Age of listing | Count | Share |
|---|---:|---:|
| 8–30 days | 47 | 0.2% |
| 31–90 days | 1,061 | 5.5% |
| 91–365 days | 17,763 | 91.7% |
| over a year | 507 | 2.6% |

- Median listing age: **209 days**
- Older than 30 days: **99.8%**
- Older than 90 days: **94.3%**
- Oldest: **1,734 days**  ·  Newest: **15 days**

**Retiring rows older than 90 days removes 94.3% of them, taking the page from 26.6 MB to roughly 1.5 MB.** The weight problem and the freshness problem are the same problem: nothing expires.
