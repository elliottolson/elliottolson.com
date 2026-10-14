#!/usr/bin/env python3
"""Tell search engines about pages that are new to the site, so they are found within hours.

This uses IndexNow, which Bing, Yandex, Naver, Seznam and Yep listen to. Google does not take
part; it finds new pages through the sitemap, which is why each post there carries its date.

It runs in two steps around publishing, because a page can only be announced once it is live:

    python3 scripts/tell_search_engines.py --find FILE   Before: list pages in dist/ that the live site lacks
    python3 scripts/tell_search_engines.py --send FILE   After: announce the pages in that list

Nothing here stops the site being published. If a step fails it says so and carries on.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "elliottolson.com"
SITEMAP = "sitemap.xml"
# IndexNow trusts an announcement when the site serves a file named after this key.
# It is meant to be public: site/<key>.txt holds the same text.
KEY = "0d32387d06504fd58b75381a74c45254"
ENDPOINT = "https://api.indexnow.org/indexnow"
USER_AGENT = f"Mozilla/5.0 (compatible; {HOST} build)"


def pages(sitemap):
    return re.findall(r"<loc>(.*?)</loc>", sitemap)


def find(target):
    built = pages((ROOT / "dist" / SITEMAP).read_text(encoding="utf-8"))
    try:
        request = urllib.request.Request(f"https://{HOST}/{SITEMAP}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=20) as response:
            live = set(pages(response.read().decode("utf-8")))
    except OSError as error:
        # Without the live sitemap there is no telling what is new, and announcing everything would be noise
        print(f"Could not read the live sitemap ({error}), so nothing will be announced")
        built = []
    new = [page for page in built if page not in live]
    target.write_text("".join(f"{page}\n" for page in new), encoding="utf-8")
    print(f"New pages: {', '.join(new) if new else 'none'}")


def send(source):
    new = source.read_text(encoding="utf-8").split() if source.exists() else []
    if not new:
        print("No new pages to announce")
        return
    if not (ROOT / "site" / f"{KEY}.txt").exists():
        print(f"site/{KEY}.txt is missing, so search engines would not trust the announcement")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": new})
    request = urllib.request.Request(ENDPOINT, data=body.encode("utf-8"), headers={
        "Content-Type": "application/json; charset=utf-8", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"Announced {len(new)} new {'page' if len(new) == 1 else 'pages'} (HTTP {response.status}): {', '.join(new)}")
    except OSError as error:
        print(f"The announcement failed ({error}); the pages will still be found through the sitemap")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("--find", "--send"):
        sys.exit(__doc__)
    (find if sys.argv[1] == "--find" else send)(Path(sys.argv[2]))
