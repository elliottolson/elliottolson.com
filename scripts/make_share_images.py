#!/usr/bin/env python3
"""Make the preview images shown when a page is shared (in iMessage, LinkedIn, Slack and so on).

A post's image is its cover artwork with its topic and title on top, saved as
content/writing/share/<post>.png. The Status page has three, one for each thing
it can say, saved as site/status/og-<state>.png; each time the site is built,
the page points at the one that matches the latest check. Images are committed,
so this only needs running when a post is added or its title, topic or cover
changes, or when the Status page's wording does.

    python3 scripts/make_share_images.py          make the images that are missing
    python3 scripts/make_share_images.py --all    remake every image

Needs Playwright (pip install playwright) and Google Chrome.
"""
import html
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

import uptime
from build import CONTENT, ROOT, SHARE, SITE, load_post

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {{ --dot: 255, 255, 255; --glow: 127, 178, 255; }}
  html, body {{ margin: 0; }}
  body {{
    position: relative;
    width: 1200px;
    height: 630px;
    overflow: hidden;
    background: #050506;
    color: #f5f5f7;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  .scrim {{
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(5, 5, 6, 0.97) 0%, rgba(5, 5, 6, 0.86) 48%, rgba(5, 5, 6, 0.2) 100%);
  }}
  .site {{ position: absolute; left: 80px; top: 72px; font-size: 26px; font-weight: 600; letter-spacing: -0.015em; }}
  .site span {{ font-weight: 400; color: #8e8e96; }}
  .text {{ position: absolute; left: 80px; right: 260px; bottom: 80px; }}
  .topic {{ font-size: 27px; color: #8e8e96; letter-spacing: -0.01em; }}
  h1 {{ margin: 18px 0 0; font-size: {size}px; font-weight: 600; line-height: 1.04; letter-spacing: -0.045em; text-wrap: balance; }}
</style>
</head>
<body>
  <canvas data-cover="{cover}" data-seed="{slug}"></canvas>
  <div class="scrim"></div>
  <div class="site">Elliott Olson <span>· Writing</span></div>
  <div class="text">
    <div class="topic">{topic}</div>
    <h1>{title}</h1>
  </div>
  <script src="{script}"></script>
</body>
</html>
"""


STATUS_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; }}
  body {{
    position: relative;
    width: 1200px;
    height: 630px;
    overflow: hidden;
    background: #050506;
    color: #f5f5f7;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .dots {{
    position: absolute;
    inset: 0;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 1.5px, transparent 2.1px) 0 0 / 30px 30px;
    -webkit-mask-image: radial-gradient(ellipse 46% 78% at 78% 50%, #000 12%, transparent 78%);
  }}
  .dots--lit {{
    background-image: radial-gradient(circle, rgb({colour}) 2.3px, transparent 2.9px);
    -webkit-mask-image: radial-gradient(ellipse 20% 38% at 76% 52%, #000 5%, transparent 100%);
  }}
  .site {{ position: absolute; left: 80px; top: 72px; font-size: 26px; font-weight: 600; letter-spacing: -0.015em; }}
  .text {{ position: absolute; left: 80px; right: 300px; bottom: 80px; }}
  .label {{ display: flex; align-items: center; gap: 14px; font-size: 27px; color: #8e8e96; letter-spacing: -0.01em; }}
  .label i {{ width: 14px; height: 14px; border-radius: 50%; background: rgb({colour}); box-shadow: 0 0 0 7px rgba({colour}, 0.22); }}
  h1 {{ margin: 20px 0 0; font-size: 96px; font-weight: 600; line-height: 1.02; letter-spacing: -0.045em; text-wrap: balance; }}
  p {{ margin: 26px 0 0; font-size: 31px; color: #d2d2d7; letter-spacing: -0.015em; }}
</style>
</head>
<body>
  <div class="dots"></div>
  <div class="dots dots--lit"></div>
  <div class="site">elliottolson.com</div>
  <div class="text">
    <div class="label"><i></i>Status</div>
    <h1>{headline}</h1>
    <p>Checked every hour.</p>
  </div>
</body>
</html>
"""
# The Status page's colours for each state, as in site/assets/status.css
STATUS_COLOURS = {"ok": "61, 220, 151", "warn": "255, 179, 64", "down": "255, 92, 84"}


def main():
    remake = "--all" in sys.argv
    # Each image to make: where it goes, and the page it is a picture of
    todo = []

    # Drafts are never shared, so they don't need an image
    for post in map(load_post, sorted(CONTENT.glob("*.md"))):
        title = post["title"]
        todo.append((SHARE / f'{post["slug"]}.png', None if post["draft"] else TEMPLATE.format(
            size=92 if len(title) <= 28 else 78 if len(title) <= 46 else 64,
            cover=post["cover"],
            slug=post["slug"],
            topic=html.escape(post["topic"]),
            title=html.escape(title),
            script=(SITE / "assets" / "writing.js").as_uri(),
        )))

    # The Status page has one image for each thing it can say; the build picks the one that is true
    for state, headline in uptime.HEADLINES.items():
        todo.append((SITE / "status" / f"og-{state}.png",
                     STATUS_TEMPLATE.format(colour=STATUS_COLOURS[state], headline=html.escape(headline))))

    todo = [(target, source) for target, source in todo if source and (remake or not target.exists())]
    if not todo:
        print("Every share image is already made. Use --all to remake them.")
        return

    with sync_playwright() as playwright, tempfile.TemporaryDirectory() as folder:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        for target, source in todo:
            file = Path(folder) / "share.html"
            file.write_text(source, encoding="utf-8")
            page.goto(file.as_uri())
            page.wait_for_timeout(500)
            target.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(target))
            print(f"Made {target.relative_to(ROOT)}")
        browser.close()


if __name__ == "__main__":
    main()
