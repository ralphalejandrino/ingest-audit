#!/usr/bin/env python3
"""
ingest_audit.py — what does a site actually cost the thing reading it?

Walks a sitemap, measures every page twice (over the wire vs. after
decompression), and flags the pages that are cheap to deliver but
expensive to ingest. Then, for the worst offender, reads the page's own
declared dates to ask whether the weight is carrying anything current.

Written for ctaio.dev. Works on any sitemap-driven site.
Standard library only — no install step, so you can re-run it yourself.

Usage:
    python3 ingest_audit.py https://ctaio.dev/sitemap.xml
    python3 ingest_audit.py https://ctaio.dev/sitemap.xml --limit 40
"""

import argparse
import collections
import concurrent.futures as futures
import datetime as dt
import gzip
import re
import sys
import urllib.request

UA = "ingest-audit/1.0 (+one-off measurement; contact via application)"
TIMEOUT = 60


def fetch(url, want_body=True):
    """Return (wire_bytes, decoded_bytes, body). Asks for gzip so the two
    numbers are directly comparable — that gap is the whole point."""
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(raw)
        else:
            body = raw
    return len(raw), len(body), (body if want_body else b"")


def sitemap_urls(sitemap_url):
    """Follow a sitemap or sitemapindex one level down."""
    _, _, body = fetch(sitemap_url)
    text = body.decode("utf-8", "replace")
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    if "<sitemapindex" in text:
        out = []
        for child in locs:
            _, _, b = fetch(child)
            out += re.findall(r"<loc>([^<]+)</loc>", b.decode("utf-8", "replace"))
        return out
    return locs


def measure(url):
    try:
        wire, decoded, body = fetch(url)
        rows = body.count(b"<tr")
        return dict(url=url, wire=wire, decoded=decoded, rows=rows, err=None)
    except Exception as exc:                       # noqa: BLE001 — report, never abort the walk
        return dict(url=url, wire=0, decoded=0, rows=0, err=f"{type(exc).__name__}: {exc}")


def freshness(url, today):
    """Read the page's OWN declared dates. We are not inferring staleness —
    `data-posted` sits under a column the site itself labels 'Posted'."""
    _, _, body = fetch(url)
    text = body.decode("utf-8", "replace")
    stamps = re.findall(r'data-posted="(\d{4})-(\d{2})-(\d{2})"', text)
    ages = [(today - dt.date(int(y), int(m), int(d))).days for y, m, d in stamps]
    total_rows = len(re.findall(r"<tr[^>]*>", text))
    return ages, total_rows




def size(n):
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sitemap")
    ap.add_argument("--limit", type=int, default=0, help="audit only the first N URLs")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    args = ap.parse_args()
    today = dt.date(*map(int, args.today.split("-")))

    urls = sitemap_urls(args.sitemap)
    if args.limit:
        urls = urls[: args.limit]
    print(f"# Ingest audit — {args.sitemap}", flush=True)
    print(f"\n{len(urls)} URLs in the sitemap. Measuring…\n", file=sys.stderr, flush=True)

    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(measure, urls))

    ok = [r for r in results if not r["err"] and r["decoded"] > 0]
    failed = [r for r in results if r["err"]]
    if not ok:
        sys.exit("no pages measured successfully")

    sizes = sorted(r["decoded"] for r in ok)
    median = sizes[len(sizes) // 2]
    ok.sort(key=lambda r: r["decoded"], reverse=True)

    print(f"\n## Delivered weight — {len(ok)} pages measured, {len(failed)} failed\n")
    print(f"Median page: **{size(median)}**\n")
    print("| Page | After decompression | Over the wire | Ratio | vs median | `<tr>` |")
    print("|---|---:|---:|---:|---:|---:|")
    for r in ok[:10]:
        path = r["url"].split("//", 1)[-1].split("/", 1)[-1]
        ratio = r["decoded"] / r["wire"] if r["wire"] else 0
        print(
            f"| `/{path}` | {size(r['decoded'])} | {size(r['wire'])} | "
            f"{ratio:.0f}× | {r['decoded']/median:.0f}× | {r['rows']:,} |"
        )

    worst = ok[0]
    print(
        f"\n**The gap is the finding.** `/{worst['url'].split('//',1)[-1].split('/',1)[-1]}` "
        f"costs {size(worst['wire'])} to deliver and {size(worst['decoded'])} to read — "
        f"a {worst['decoded']/worst['wire']:.0f}× difference. Compression hides it from every "
        f"CDN-level check; the parser and the context window still pay full price."
    )

    # ---- is the weight carrying anything current? -------------------------
    ages, total_rows = freshness(worst["url"], today)
    if not ages:
        print("\n_No `data-posted` stamps on the heaviest page; freshness not assessed._")
        return
    n = len(ages)
    ages.sort()
    buckets = collections.Counter()
    for a in ages:
        buckets[
            "≤7 days" if a <= 7 else
            "8–30 days" if a <= 30 else
            "31–90 days" if a <= 90 else
            "91–365 days" if a <= 365 else
            "over a year"
        ] += 1

    print(f"\n## Is that weight carrying anything current?\n")
    print(f"Parsed **{n:,}** `data-posted` stamps from {total_rows:,} rows "
          f"({100*n/max(total_rows-1,1):.1f}% of data rows).\n")
    print("| Age of listing | Count | Share |")
    print("|---|---:|---:|")
    for k in ("≤7 days", "8–30 days", "31–90 days", "91–365 days", "over a year"):
        if buckets[k]:
            print(f"| {k} | {buckets[k]:,} | {100*buckets[k]/n:.1f}% |")

    stale90 = sum(1 for a in ages if a > 90)
    print(
        f"\n- Median listing age: **{ages[n//2]:,} days**\n"
        f"- Older than 30 days: **{100*sum(1 for a in ages if a > 30)/n:.1f}%**\n"
        f"- Older than 90 days: **{100*stale90/n:.1f}%**\n"
        f"- Oldest: **{max(ages):,} days**  ·  Newest: **{min(ages):,} days**\n"
    )
    projected = worst["decoded"] * (1 - stale90 / n)
    print(
        f"**Retiring rows older than 90 days removes {100*stale90/n:.1f}% of them, "
        f"taking the page from {size(worst['decoded'])} to roughly {size(projected)}.** "
        f"The weight problem and the freshness problem are the same problem: nothing expires."
    )

    if failed:
        print(f"\n_{len(failed)} URLs failed to measure:_")
        for r in failed[:5]:
            print(f"- `{r['url']}` — {r['err']}")


if __name__ == "__main__":
    main()
