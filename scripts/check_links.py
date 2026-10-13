#!/usr/bin/env python3
"""Check every link in the site's HTML files.

Internal links must point at a file (and anchor) that exists. External links
must not be dead: a 404, 410 or failed connection fails the check, while other
errors (rate limits, bot blocking) are reported as warnings.
"""
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse

ROOT = Path(__file__).resolve().parents[1] / "site"
SITE = "https://elliottolson.com"
SKIP_HOSTS = {"www.linkedin.com", "linkedin.com"}  # blocks automated requests
USER_AGENT = "Mozilla/5.0 (compatible; elliottolson.com link check)"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.links.append(attrs.get("content", "").split("url=", 1)[-1])
        if tag == "meta" and attrs.get("property") == "og:image":
            self.links.append(attrs.get("content", ""))


def parse(path):
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def resolve(source, target):
    """Map an internal link to the file GitHub Pages would serve."""
    base = ROOT if target.startswith("/") else source.parent
    path = (base / target.lstrip("/")).resolve() if target else source
    if path.is_dir():
        path = path / "index.html"
    return path


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status


def main():
    pages = {p: parse(p) for p in sorted(ROOT.rglob("*.html"))}
    errors, warnings, external = [], [], {}

    for path, page in pages.items():
        name = path.relative_to(ROOT)
        for link in page.links:
            if link.startswith(("mailto:", "tel:", "data:")):
                continue
            if link.startswith("//"):
                link = "https:" + link
            if link.startswith(SITE):
                link = link[len(SITE):] or "/"
            if link.startswith(("http://", "https://")):
                external.setdefault(link, name)
                continue
            target, anchor = urldefrag(link)
            file = resolve(path, target)
            if not file.exists():
                errors.append(f"{name}: {link} -> file not found")
            elif anchor and file.suffix == ".html":
                ids = pages[file].ids if file in pages else parse(file).ids
                if anchor not in ids:
                    errors.append(f"{name}: {link} -> no element with id '{anchor}'")

    for url, name in external.items():
        if urlparse(url).hostname in SKIP_HOSTS:
            continue
        for attempt in (1, 2):
            try:
                fetch(url)
                break
            except urllib.error.HTTPError as error:
                if error.code in (404, 410):
                    errors.append(f"{name}: {url} -> HTTP {error.code}")
                    break
                if attempt == 2:
                    warnings.append(f"{name}: {url} -> HTTP {error.code}")
            except Exception as error:  # DNS failure, timeout, TLS error
                if attempt == 2:
                    errors.append(f"{name}: {url} -> {error}")

    for line in warnings:
        print(f"warning: {line}")
    for line in errors:
        print(f"error: {line}")
    print(f"Checked {len(pages)} pages and {len(external)} external links: "
          f"{len(errors)} errors, {len(warnings)} warnings.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
