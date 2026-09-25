#!/usr/bin/env python3
"""Refresh the three article sections in exoplanetnews.html."""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "exoplanetnews.html"
ZONE = ZoneInfo("America/Chicago")
MAX_CARDS = 6
TIMEOUT = 12
HEADERS = {"User-Agent": "ExoplanetSlackerNews/1.0 (+https://drloot.github.io/exoplanet-slacker/)"}
START = "AUTOMATED NEWS START"

# Feeds are used only for source pages already linked in the corresponding section.
# Pages without a known feed are also checked for feed discovery and dated articles.
FEEDS = {
    "https://www.space.com/astronomy/exoplanets/": "https://www.space.com/feeds/all",
    "https://science.nasa.gov/exoplanets/stories/": "https://science.nasa.gov/feed/",
    "https://science.nasa.gov/mission/hubble/hubble-news/": "https://science.nasa.gov/mission/hubble/feed/",
    "https://science.nasa.gov/mission/webb/latestnews/": "https://science.nasa.gov/mission/webb/feed/",
    "https://www.nasa.gov/news/recently-published/": "https://www.nasa.gov/feed/",
    "https://www.jpl.nasa.gov/news/": "https://www.jpl.nasa.gov/feeds/news/",
    "https://aasnova.org/": "https://aasnova.org/feed/",
    "https://spacenews.com/": "https://spacenews.com/feed/",
    "https://www.astronomy.com/tags/news/": "https://www.astronomy.com/feed/",
    "https://skyandtelescope.org/astronomy-news/": "https://skyandtelescope.org/feed/",
}


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    source: str
    date: dt.date
    published_at: dt.datetime | None = None


def get(url: str) -> requests.Response | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        if len(response.content) > 8_000_000:
            return None
        return response
    except requests.RequestException as exc:
        logging.info("Unavailable: %s (%s)", url, exc)
        return None


def date_of(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
    if parsed.tzinfo is None:
        # A date without a time zone is interpreted as the publisher's calendar date.
        return parsed.date()
    return parsed.astimezone(ZONE).date()


def time_of(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
    return parsed.astimezone(ZONE) if parsed.tzinfo else parsed.replace(tzinfo=ZONE)


def same_site(url: str, source_url: str) -> bool:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    source = (urlparse(source_url).hostname or "").removeprefix("www.")
    return host == source and urlparse(url).scheme in ("http", "https")


def article(title: str, url: str, source_name: str, source_url: str,
            published: str | None, allowed_dates: set[dt.date]) -> Article | None:
    title = re.sub(r"\s+", " ", BeautifulSoup(html.unescape(title or ""), "html.parser").get_text(" ")).strip()
    url = url.split("#", 1)[0]
    day = date_of(published)
    if not (title and len(title) >= 12 and day in allowed_dates and same_site(url, source_url)):
        return None
    # These general feeds must stay on the topic of their linked category page.
    if source_url.endswith("/exoplanets/stories/") or source_url.endswith("/astronomy/exoplanets/"):
        if not re.search(r"exoplanet|planetary system|habitable world|alien planet", title + " " + url, re.I):
            return None
    if "/mission/hubble/" in source_url and "hubble" not in (title + " " + url).lower():
        return None
    if "/mission/webb/" in source_url and not re.search(r"webb|jwst", title + " " + url, re.I):
        return None
    for path, topic in (("/blogs/voyager/", r"voyager"),
                        ("/mission/roman-space-telescope/", r"roman"),
                        ("/exoplanets/", r"exoplanet|planetary system|habitable world|alien planet")):
        if path in source_url and not re.search(topic, title + " " + url, re.I):
            return None
    return Article(title, url, re.sub(r"\s+", " ", source_name).strip(), day, time_of(published))


def page_date(soup: BeautifulSoup) -> str | None:
    for attr in ("article:published_time", "datePublished", "pubdate", "date", "DC.date.issued"):
        tag = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if tag and tag.get("content"):
            return tag["content"]
    tag = soup.find("time", datetime=True)
    if tag:
        return tag["datetime"]
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            stack = data if isinstance(data, list) else [data]
            while stack:
                item = stack.pop()
                if isinstance(item, dict):
                    if item.get("datePublished"):
                        return item["datePublished"]
                    stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
        except (ValueError, TypeError):
            continue
    return None


def collect(source: tuple[str, str], allowed_dates: set[dt.date]) -> list[Article]:
    name, url = source
    result: list[Article] = []
    response = get(url)
    if response is None:
        return result
    soup = BeautifulSoup(response.text, "html.parser")
    feed_urls = [FEEDS[url]] if url in FEEDS else []
    for link in soup.find_all("link", type=re.compile(r"(rss|atom)\+xml", re.I), href=True):
        candidate = urljoin(url, link["href"])
        if same_site(candidate, url) and "/comments/" not in candidate and candidate not in feed_urls:
            feed_urls.append(candidate)

    for feed_url in feed_urls[:3]:
        feed_response = get(feed_url)
        if feed_response is None:
            continue
        feed = feedparser.parse(feed_response.content)
        for entry in feed.entries[:50]:
            found = article(entry.get("title", ""), entry.get("link", ""), name, url,
                            entry.get("published") or entry.get("updated"), allowed_dates)
            if found:
                result.append(found)

    # Some publishers provide no RSS. Inspect recent links and read their article dates.
    if not result:
        candidates = []
        for anchor in soup.select("article a[href], main a[href], a[href]"):
            target = urljoin(url, anchor.get("href", ""))
            title = anchor.get_text(" ", strip=True)
            if (same_site(target, url) and target != url and len(title) >= 12
                    and not re.search(r"(?:favicon|opensearch|\.svg(?:\?|$)|\.xml(?:\?|$)|/login|/account)", target, re.I)
                    and target not in {item.url for item in result} and target not in {v for _, v in candidates}):
                candidates.append((title, target))
            if len(candidates) >= 8:
                break
        for title, target in candidates:
            detail = get(target)
            if detail is None or "html" not in detail.headers.get("Content-Type", "").lower():
                continue
            detail_soup = BeautifulSoup(detail.text, "html.parser")
            headline = detail_soup.find("h1")
            found = article(headline.get_text(" ", strip=True) if headline else title,
                            target, name, url, page_date(detail_soup), allowed_dates)
            if found:
                result.append(found)
    logging.info("%s: %s dated articles", name, len(result))
    return result


def render(items: list[Article], today: dt.date) -> str:
    cards = []
    for item in items:
        title = html.escape(item.title, quote=True)
        source = html.escape(item.source, quote=True)
        url = html.escape(item.url, quote=True)
        label = "Today" if item.date == today else "Yesterday"
        cards.append(f'<a class="news-item" href="{url}" target="_blank" rel="noopener noreferrer">'
                     f'<span class="news-meta">{source} · {label}, {item.date:%b %-d}</span>'
                     f'<span class="news-title">{title}</span><span class="news-read">Read article →</span></a>')
    if not cards:
        return '<p class="news-empty">No articles dated today or yesterday from these sources yet.</p>'
    return '<div class="news-grid">\n' + '\n'.join(cards) + '\n</div>'


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    raw = PAGE.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    sections = soup.select("main > section.card")
    if len(sections) != 3:
        raise ValueError(f"Expected three news sections, found {len(sections)}")
    today = dt.datetime.now(ZONE).date()
    allowed_dates = {today, today - dt.timedelta(days=1)}
    sources_by_section = []
    for section in sections:
        sources_by_section.append([(a.get_text(" ", strip=True), a["href"])
                                   for a in section.select(".list .item a[href]")])
    unique_sources = list(dict.fromkeys(source for group in sources_by_section for source in group))
    articles_by_source = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(collect, source, allowed_dates): source for source in unique_sources}
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                articles_by_source[source] = future.result()
            except Exception:
                logging.exception("Failed to check %s", source[1])
                articles_by_source[source] = []

    for section, sources in zip(sections, sources_by_section):
        candidates = [item for source in sources for item in articles_by_source[source]]
        candidates.sort(key=lambda item: (item.published_at or dt.datetime.combine(item.date, dt.time.min, ZONE),
                                          item.title.casefold()), reverse=True)
        seen = set()
        selected = []
        for item in candidates:
            key = urlparse(item.url)._replace(query="", fragment="").geturl().rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
            if len(selected) == MAX_CARDS:
                break
        marker = section.find(string=lambda value: isinstance(value, str) and START in value)
        if marker is None:
            raise ValueError("Missing automated news marker")
        container = marker.next_sibling
        if not getattr(container, "get", lambda _: None)("class") or "auto-news" not in container.get("class", []):
            raise ValueError("Missing automated news container")
        container.clear()
        fragment = BeautifulSoup(render(selected, today), "html.parser")
        container.append(fragment)
        logging.info("%s: %d cards", section.h2.get_text(" ", strip=True), len(selected))

    output = str(soup)
    if output != raw:
        PAGE.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
