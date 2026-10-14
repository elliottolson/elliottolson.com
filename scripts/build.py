#!/usr/bin/env python3
"""Build the site into dist/, ready to publish.

Everything in site/ is copied across as it is. The Writing section is then built
from the Markdown files in content/writing/, and the Status page is given the
record of the uptime checks (see uptime.py).

Each post is a Markdown file with a short header:

    ---
    title: What an evaluation score really tells you
    date: 2026-10-06        (a date still to come holds the post back until that day;
                             add a time, as in 2026-10-06 09:00, to hold it until then)
    topic: Evaluation
    cover: waves            (waves, rings, beams or cells)
    summary: One or two sentences shown on cards and under the title.
    draft: true             (optional: keeps the post out of the published site)
    ---

Beyond ordinary Markdown, a post can use:

    A sentence with a note.^[The note text.]

    ::: table A caption for the table.
    | Column | Other |
    | ------ | ----: |
    :::

    ::: chart A caption for the chart.
    {"type": "line", "x": [...], "series": [...]}
    :::

    ::: diagram A caption for the diagram.
    <svg>...</svg>
    :::

    ::: aside
    A boxed note.
    :::

    ```python title="retry.py"
    print("Code blocks are coloured; the title is optional.")
    ```

Running this script writes the finished site into dist/, which is not committed:
GitHub runs the same script when it publishes the site. Drafts, and posts dated
in the future, are left out unless asked for, which is what the local preview
does. The site is published again every hour, so a post dated ahead appears by
itself once its day comes. With no posts to show, the Writing section is left
off the site entirely.

    python3 scripts/build.py             the site as it will be published
    python3 scripts/build.py --drafts    the same, with drafts and scheduled posts included
"""
import html
import json
import re
import shutil
import sys
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

import uptime

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "writing"
SITE = ROOT / "site"
DIST = ROOT / "dist"
OUT = DIST / "writing"
SHARE = CONTENT / "share"
SITE_URL = "https://elliottolson.com"
TIMEZONE = ZoneInfo("America/Los_Angeles")  # the clock a scheduled post's date and time are read by
COVERS = ("waves", "rings", "beams", "cells")
HOME_START, HOME_END = "<!-- writing:start -->", "<!-- writing:end -->"
# Parts of the home page that only make sense once there is something to read
ONLY_WITH_POSTS = re.compile(r"[ \t]*<!-- if-writing -->\n(.*?)[ \t]*<!-- /if-writing -->\n", re.S)
# Where the Status page keeps the record of the uptime checks
STATUS_DATA = 'id="status-data">null<'
FEED_TITLE = "Elliott Olson – Writing"
FEED_DESCRIPTION = "Notes on evaluating models, building infrastructure, and the work around it."


# Reading the posts

def load_post(path):
    match = re.match(r"---\n(.*?)\n---\n(.*)", path.read_text(encoding="utf-8"), re.S)
    if not match:
        sys.exit(f"{path.name}: missing the header between --- lines")
    meta = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    meta = {key.strip(): value.strip() for key, value in meta.items()}
    for key in ("title", "date", "topic", "summary"):
        if not meta.get(key):
            sys.exit(f"{path.name}: the header needs a '{key}'")
    cover = meta.get("cover", COVERS[sum(map(ord, path.stem)) % len(COVERS)])
    if cover not in COVERS:
        sys.exit(f"{path.name}: cover must be one of {', '.join(COVERS)}")
    body = match.group(2)
    try:
        publishes = datetime.fromisoformat(meta["date"]).replace(tzinfo=TIMEZONE)
    except ValueError:
        sys.exit(f"{path.name}: the date should look like 2026-10-06, or 2026-10-06 09:00 to give a time")
    draft = meta.get("draft", "").lower() == "true"
    return {
        "slug": path.stem,
        "title": meta["title"],
        "date": publishes.date(),
        "publishes": publishes,
        "topic": meta["topic"],
        "summary": meta["summary"],
        "cover": cover,
        "draft": draft,
        "scheduled": not draft and publishes > datetime.now(TIMEZONE),
        "minutes": reading_minutes(body),
        "body": render_body(body, path.name),
    }


def held(post):
    """Whether a post is kept off the published site, as a draft or until its date."""
    return post["draft"] or post["scheduled"]


def reading_minutes(text):
    # Chart data and diagram markup are not prose, so they don't count
    prose = re.sub(r"^::: *(chart|diagram).*?^:::[ \t]*$", "", text, flags=re.S | re.M)
    return max(1, round(len(re.findall(r"\w+", prose)) / 220))


def render_markdown(text, extensions=("tables", "smarty")):
    return markdown.markdown(text, extensions=list(extensions))


def render_body(text, name):
    """Turn a post's Markdown, plus the extra syntax described above, into HTML."""
    blocks = []
    numbers = {"Figure": 0, "Table": 0}

    def stash(block):
        blocks.append(block)
        return f"\n\n@@BLOCK{len(blocks) - 1}@@\n\n"

    def caption(kind, text):
        numbers[kind] += 1
        label = f'<span class="figure__label">{kind} {numbers[kind]}</span>'
        return f"<figcaption>{label}{render_inline(text)}</figcaption>" if text else f"<figcaption>{label}</figcaption>"

    def directive(match):
        kind, text, inner = match.group(1), (match.group(2) or "").strip(), match.group(3)
        if kind == "table":
            table = render_markdown(inner).replace(' style="text-align: right;"', ' class="num"')
            return stash(f'<figure class="table">\n<div class="table__scroll">\n{table}\n</div>\n{caption("Table", text)}\n</figure>')
        if kind == "chart":
            try:
                data = json.dumps(json.loads(inner), separators=(",", ":")).replace("</", "<\\/")
            except json.JSONDecodeError as error:
                sys.exit(f"{name}: a chart's data is not valid JSON ({error})")
            return stash(f'<figure class="chart">\n<script type="application/json">{data}</script>\n{caption("Figure", text)}\n</figure>')
        if kind == "diagram":
            return stash(f'<figure class="diagram">\n<div class="diagram__scroll">\n{inner.strip()}\n</div>\n{caption("Figure", text)}\n</figure>')
        if kind == "aside":
            return stash(f'<div class="callout">\n{render_markdown(inner)}\n</div>')
        sys.exit(f"{name}: unknown block ':::{kind}'")

    def code(match):
        language, title, source = match.group(1) or "", match.group(2), match.group(3)
        return stash(render_code(source, language, title))

    def note(match):
        return f'<button class="note-ref" type="button"></button><span class="note">{match.group(1)}</span>'

    text = re.sub(r"^::: *(\w+)(?: +(.*?))?\n(.*?)\n:::[ \t]*$", directive, text, flags=re.S | re.M)
    text = re.sub(r'^```(\w+)?(?: +title="([^"]*)")?\n(.*?)\n```[ \t]*$', code, text, flags=re.S | re.M)
    text = re.sub(r"\^\[(.+?)\]", note, text)

    # Every heading gets an id and a small link for sharing that section
    body = markdown.markdown(text, extensions=["tables", "smarty", "toc"], extension_configs={
        "toc": {"permalink": "#", "permalink_class": "anchor", "permalink_title": "Copy a link to this section"},
    })
    body = body.replace(' title="Copy a link to this section">', ' aria-label="Copy a link to this section">')
    for index, block in enumerate(blocks):
        body = body.replace(f"<p>@@BLOCK{index}@@</p>", block)
    # The opening paragraph is set a little larger
    if body.startswith("<p>"):
        body = body.replace("<p>", '<p class="lead">', 1)
    if "@@BLOCK" in body:
        sys.exit(f"{name}: a block could not be placed; check the blank lines around ':::' and code blocks")
    return body


def render_inline(text):
    return re.sub(r"^<p>|</p>$", "", render_markdown(text, ("smarty",)).strip())


def render_code(source, language, title):
    """A code block, coloured at build time so the page needs no highlighting script."""
    try:
        lexer = get_lexer_by_name(language) if language else TextLexer()
    except ClassNotFound:
        sys.exit(f"Unknown code language '{language}'")
    label = html.escape(title or (lexer.name if language else "Code"))
    coloured = highlight(source, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")
    return (
        '<div class="code">\n'
        f'<div class="code__bar"><span>{label}</span><button class="ghost-button" type="button" data-copy="code">Copy</button></div>\n'
        f"<pre><code>{coloured}</code></pre>\n"
        "</div>"
    )


# Page templates

def format_date(day):
    return f"{day:%b} {day.day}, {day.year}"


def format_moment(moment):
    """A date, with the time of day when one was given."""
    if (moment.hour, moment.minute) == (0, 0):
        return format_date(moment)
    return f"{format_date(moment)} at {moment.hour % 12 or 12}:{moment:%M} {'AM' if moment.hour < 12 else 'PM'}"


def page_head(title, description, noindex, path, image="/og.png", published=None):
    """The top of every page. `path` and `image` describe the page to search engines and link previews."""
    robots = '\n  <meta name="robots" content="noindex">' if noindex else ""
    article = f'\n  <meta property="article:published_time" content="{published.isoformat()}">' if published else ""
    share_title = html.escape(title.removesuffix(" – Elliott Olson"), quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">{robots}
  <link rel="canonical" href="{SITE_URL}{path}">
  <meta property="og:title" content="{share_title}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:type" content="{"article" if published else "website"}">
  <meta property="og:url" content="{SITE_URL}{path}">
  <meta property="og:site_name" content="Elliott Olson">
  <meta property="og:image" content="{SITE_URL}{image}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">{article}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="color-scheme" content="dark light">
  <meta name="theme-color" content="#050506" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#fbfbfd" media="(prefers-color-scheme: light)">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(FEED_TITLE, quote=True)}" href="/writing/feed.xml">
  <link rel="stylesheet" href="/assets/styles.css">
  <link rel="stylesheet" href="/assets/writing.css">
  <script>document.documentElement.classList.add('js');</script>
</head>
<body>
  <header class="nav" id="nav">
    <div class="wrap nav__inner">
      <a class="nav__name" href="/">Elliott Olson</a>
      <nav class="nav__links" aria-label="Sections">
        <a href="/#work">Work</a>
        <a class="nav__optional" href="/#experience">Experience</a>
        <a href="/writing/" aria-current="page">Writing</a>
        <a href="/#contact">Contact</a>
      </nav>
    </div>
    <div class="nav__progress" aria-hidden="true"></div>
  </header>
"""


def preview_note(posts):
    """What the corner badge says when a page shows posts that aren't on the published site."""
    if any(post["draft"] for post in posts):
        return "Draft · not published"
    waiting = [post["publishes"] for post in posts if post["scheduled"]]
    return f"Scheduled · publishes {format_moment(min(waiting))}" if waiting else ""


def page_foot(note):
    badge = f'\n  <div class="proto">{note}</div>\n' if note else ""
    return f"""
  <footer class="footer">
    <div class="wrap footer__inner">
      <span>© 2026 Elliott Olson</span>
      <span>Bellevue, Washington</span>
      <a href="/status/">Status</a>
    </div>
  </footer>
{badge}
  <script src="/assets/main.js" defer></script>
  <script src="/assets/writing.js" defer></script>
  <script data-goatcounter="https://elliottolson.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""


def meta_line(post):
    return (f'<p class="post__meta"><span>{html.escape(post["topic"])}</span><span>{format_date(post["date"])}</span>'
            f'<span>{post["minutes"]} min read</span></p>')


def cover(post, extra=""):
    classes = f"cover {extra}".strip()
    return (f'<div class="{classes}" style="view-transition-name: cover-{post["slug"]}">'
            f'<canvas data-cover="{post["cover"]}" data-seed="{post["slug"]}" aria-hidden="true"></canvas></div>')


def card(post, featured=False):
    classes = "post post--featured reveal" if featured else "post reveal"
    return f"""        <a class="{classes}" href="/writing/{post["slug"]}/" data-topic="{html.escape(post["topic"].lower(), quote=True)}">
          {cover(post)}
          <div class="post__text">
            {'<p class="post__flag">Latest</p>' if featured else ""}
            {meta_line(post)}
            <h2 class="post__title">{html.escape(post["title"])}</h2>
            <p class="post__excerpt">{html.escape(post["summary"])}</p>
            <span class="post__more">Read <span aria-hidden="true">→</span></span>
          </div>
        </a>
"""


def index_page(posts):
    featured, rest = posts[0], posts[1:]
    topics = list(dict.fromkeys(post["topic"] for post in rest))
    chips = '<button class="chip" type="button" data-topic="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" type="button" data-topic="{html.escape(topic.lower(), quote=True)}" aria-pressed="false">{html.escape(topic)}</button>'
        for topic in topics)
    grid = f"""
      <div class="posts-head reveal">
        <p class="posts-head__count">{len(rest)} {"post" if len(rest) == 1 else "posts"}</p>
        <div class="chips" role="group" aria-label="Filter by topic">{chips}</div>
      </div>

      <div class="posts">
{"".join(card(post) for post in rest)}      </div>
""" if rest else '\n      <div class="posts"></div>\n'
    return page_head("Writing – Elliott Olson", FEED_DESCRIPTION, all(map(held, posts)), "/writing/") + f"""
  <main>
    <header class="page-head" data-field>
      <canvas class="field" aria-hidden="true"></canvas>
      <div class="wrap page-head__inner">
        <p class="section__label rise" style="--i:0">Writing</p>
        <h1 aria-label="Notes from the work.">
          <span class="word" style="--i:1" aria-hidden="true">Notes</span>
          <span class="word" style="--i:2" aria-hidden="true">from</span>
          <span class="word" style="--i:3" aria-hidden="true">the</span>
          <span class="word" style="--i:4" aria-hidden="true">work.</span>
        </h1>
        <p class="page-head__sub rise" style="--i:6">On evaluating models, building the infrastructure underneath them, and what I’ve learned along the way.</p>
        <p class="page-head__links rise" style="--i:7"><a class="link" href="/writing/feed.xml">Follow by RSS <span aria-hidden="true">→</span></a></p>
      </div>
    </header>

    <section class="wrap">
{card(featured, featured=True)}{grid}    </section>
  </main>
""" + page_foot(preview_note(posts))


def article_page(post, following):
    title = html.escape(post["title"])
    next_block = f"""
    <div class="wrap">
      <a class="post next" href="/writing/{following["slug"]}/">
        <div class="post__text">
          <p class="next__label">Next</p>
          <p class="next__title">{html.escape(following["title"])}</p>
          <p class="post__excerpt">{html.escape(following["summary"])}</p>
          <span class="post__more">Read <span aria-hidden="true">→</span></span>
        </div>
        {cover(following)}
      </a>
    </div>
""" if following else ""
    path = f'/writing/{post["slug"]}/'
    image = f"{path}og.png" if (SHARE / f'{post["slug"]}.png').exists() else "/og.png"
    return page_head(f'{post["title"]} – Elliott Olson', post["summary"], held(post), path,
                     image=image, published=post["date"]) + f"""
  <main>
    <article>
      <header class="wrap article-head">
        <a class="article-head__back rise" style="--i:0" href="/writing/"><span aria-hidden="true">←</span> Writing</a>
        <div class="rise" style="--i:1">{meta_line(post)}</div>
        <h1 style="view-transition-name: title-{post["slug"]}">{title}</h1>
        <p class="article-head__dek rise" style="--i:3">{html.escape(post["summary"])}</p>
        {cover(post, "article-cover")}
      </header>

      <div class="wrap article-layout">
        <div class="prose">
{post["body"]}

          <footer class="byline">
            <div>
              <p class="byline__name">Elliott Olson</p>
              <p class="byline__meta">Senior Software Engineer, Amazon AGI · Published {format_date(post["date"])}</p>
            </div>
            <div class="byline__actions">
              <a class="link" href="https://www.linkedin.com/in/elliottolson" target="_blank" rel="noopener" data-goatcounter-click="click-linkedin">LinkedIn <span aria-hidden="true">↗</span></a>
              <button class="ghost-button" type="button" data-copy="link">Copy link</button>
            </div>
          </footer>
        </div>

        <nav class="toc" aria-label="Contents">
          <p class="toc__label">Contents</p>
          <ol></ol>
        </nav>
      </div>
    </article>
{next_block}  </main>
""" + page_foot(preview_note([post]))


def home_rows(posts):
    return "".join(f"""          <li class="row reveal">
            <span class="row__when">{format_date(post["date"])}</span>
            <span class="row__what"><a href="/writing/{post["slug"]}/">{html.escape(post["title"])}</a></span>
            <span class="row__where">{html.escape(post["topic"])} · {post["minutes"]} min</span>
          </li>
""" for post in posts[:3])


def feed(posts):
    """An RSS feed of every post, newest first, for people who follow blogs in a reader."""
    def stamp(day):
        return format_datetime(datetime(day.year, day.month, day.day, tzinfo=timezone.utc))

    items = "".join(f"""
    <item>
      <title>{html.escape(post["title"])}</title>
      <link>{SITE_URL}/writing/{post["slug"]}/</link>
      <guid isPermaLink="true">{SITE_URL}/writing/{post["slug"]}/</guid>
      <pubDate>{stamp(post["date"])}</pubDate>
      <category>{html.escape(post["topic"])}</category>
      <description>{html.escape(post["summary"])}</description>
    </item>""" for post in posts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(FEED_TITLE)}</title>
    <link>{SITE_URL}/writing/</link>
    <atom:link href="{SITE_URL}/writing/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{html.escape(FEED_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>{stamp(posts[0]["date"])}</lastBuildDate>{items}
  </channel>
</rss>
"""


# Writing the output

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sitemap(posts):
    """Every published page, for search engines. A post carries its date, which tells them how fresh it is."""
    pages = [("/", None)] + ([("/writing/", None)] + [(f'/writing/{post["slug"]}/', post["date"]) for post in posts] if posts else [])
    pages.append(("/status/", None))
    urls = "".join(
        f"\n  <url>\n    <loc>{SITE_URL}{page}</loc>" + (f"\n    <lastmod>{day.isoformat()}</lastmod>" if day else "") + "\n  </url>"
        for page, day in pages)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}\n</urlset>\n'


def set_meta(text, name, content):
    text, found = re.subn(rf'(<meta property="{name}" content=")[^"]*', lambda match: match.group(1) + html.escape(content, quote=True), text)
    if found != 1:
        sys.exit(f"site/status/index.html should have exactly one {name}")
    return text


def status_page(text, has_posts, records, made_up):
    """The hand-written Status page, with the record of the uptime checks written into it."""
    if STATUS_DATA not in text:
        sys.exit("site/status/index.html is missing the place for its data")
    data = uptime.summary(records)
    if data and made_up:
        data["sample"] = True
    if data:
        # Shared as a link, the page shows what the latest check found
        text = set_meta(text, "og:title", f'Status · {data["headline"].rstrip(".")}')
        text = set_meta(text, "og:image", f'{SITE_URL}/status/og-{data["state"]}.png')
    text = ONLY_WITH_POSTS.sub(lambda block: block.group(1) if has_posts else "", text)
    return text.replace(STATUS_DATA, STATUS_DATA.replace("null", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))


def main(drafts=False, sample=None):
    posts = sorted((load_post(path) for path in CONTENT.glob("*.md")), key=lambda post: post["date"], reverse=True)
    for post in posts:
        if post["scheduled"]:
            print(f'Scheduled for {format_moment(post["publishes"])}: {post["slug"]}')
    if not drafts:
        posts = [post for post in posts if not held(post)]

    # Start from a clean copy of the hand-written site
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST, ignore=shutil.ignore_patterns(".DS_Store"))

    home = DIST / "index.html"
    text = home.read_text(encoding="utf-8")
    if HOME_START not in text or HOME_END not in text or not ONLY_WITH_POSTS.search(text):
        sys.exit("site/index.html is missing its writing markers")
    write(DIST / "sitemap.xml", sitemap([post for post in posts if not held(post)]))

    # The record of the uptime checks is kept on another branch, so a preview shows made-up checks instead
    records = uptime.read_log()
    if sample or (drafts and not records):
        records, sample = uptime.sample(sample or "ok"), True
    status = DIST / "status" / "index.html"
    write(status, status_page(status.read_text(encoding="utf-8"), bool(posts), records, sample))

    if not posts:
        # Nothing to read yet, so the home page makes no mention of Writing
        write(home, ONLY_WITH_POSTS.sub("", text))
        print(f"Built the site into {DIST.relative_to(ROOT)}/. There are no published posts, so Writing is hidden.")
        return

    write(OUT / "index.html", index_page(posts))
    write(OUT / "feed.xml", feed(posts))
    for position, post in enumerate(posts):
        following = posts[(position + 1) % len(posts)] if len(posts) > 1 else None
        write(OUT / post["slug"] / "index.html", article_page(post, following))
        image = SHARE / f'{post["slug"]}.png'
        if image.exists():
            shutil.copyfile(image, OUT / post["slug"] / "og.png")

    text = ONLY_WITH_POSTS.sub(lambda block: block.group(1), text)
    before, rest = text.split(HOME_START, 1)
    after = rest.split(HOME_END, 1)[1]
    write(home, f"{before}{HOME_START}\n{home_rows(posts)}          {HOME_END}{after}")

    print(f"Built the site, with {len(posts)} {'post' if len(posts) == 1 else 'posts'}, into {DIST.relative_to(ROOT)}/")
    missing = [post["slug"] for post in posts if not post["draft"] and not (SHARE / f'{post["slug"]}.png').exists()]
    if missing:
        print(f"No share image yet for: {', '.join(missing)}. Run scripts/make_share_images.py")


if __name__ == "__main__":
    main(drafts="--drafts" in sys.argv)
