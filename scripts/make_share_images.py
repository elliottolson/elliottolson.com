#!/usr/bin/env python3
"""Make the preview image shown when a post is shared (in iMessage, LinkedIn, Slack and so on).

Each image is the post's cover artwork with its topic and title on top, saved
as site/writing/<post>/og.png. Images are committed, so this only needs running
when a post is added or its title, topic or cover changes.

    python3 scripts/make_share_images.py          make images for posts that have none
    python3 scripts/make_share_images.py --all    remake every image

Needs Playwright (pip install playwright) and Google Chrome.
"""
import html
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from build_writing import CONTENT, OUT, SITE, load_post

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


def main():
    remake = "--all" in sys.argv
    posts = [load_post(path) for path in sorted(CONTENT.glob("*.md"))]
    todo = [post for post in posts if remake or not (OUT / post["slug"] / "og.png").exists()]
    if not todo:
        print("Every post already has a share image. Use --all to remake them.")
        return

    with sync_playwright() as playwright, tempfile.TemporaryDirectory() as folder:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        for post in todo:
            title = post["title"]
            source = Path(folder) / "share.html"
            source.write_text(TEMPLATE.format(
                size=92 if len(title) <= 28 else 78 if len(title) <= 46 else 64,
                cover=post["cover"],
                slug=post["slug"],
                topic=html.escape(post["topic"]),
                title=html.escape(title),
                script=(SITE / "assets" / "writing.js").as_uri(),
            ), encoding="utf-8")
            page.goto(source.as_uri())
            page.wait_for_timeout(500)
            target = OUT / post["slug"] / "og.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(target))
            print(f"Made {target.relative_to(SITE.parent)}")
        browser.close()


if __name__ == "__main__":
    main()
