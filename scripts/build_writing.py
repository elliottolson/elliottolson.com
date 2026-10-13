#!/usr/bin/env python3
"""Build the Writing section from the Markdown files in content/writing/.

Each post is a Markdown file with a short header:

    ---
    title: What an evaluation score really tells you
    date: 2026-10-06
    topic: Evaluation
    cover: waves            (waves, rings, beams or cells)
    summary: One or two sentences shown on cards and under the title.
    sample: true            (optional: marks a placeholder post and hides it from search engines)
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

Running this script writes the pages into site/writing/ and updates the list of
latest posts on the home page. The output is committed alongside the source.

    python3 scripts/build_writing.py
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "writing"
SITE = ROOT / "site"
OUT = SITE / "writing"
SITE_URL = "https://elliottolson.com"
COVERS = ("waves", "rings", "beams", "cells")
HOME_START, HOME_END = "<!-- writing:start -->", "<!-- writing:end -->"


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
    return {
        "slug": path.stem,
        "title": meta["title"],
        "date": date.fromisoformat(meta["date"]),
        "topic": meta["topic"],
        "summary": meta["summary"],
        "cover": cover,
        "sample": meta.get("sample", "").lower() == "true",
        "minutes": reading_minutes(body),
        "body": render_body(body, path.name),
    }


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
        label = f"{kind} {numbers[kind]}."
        return f"<figcaption>{label} {render_inline(text)}</figcaption>" if text else f"<figcaption>{label}</figcaption>"

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


def page_head(title, description, noindex):
    robots = '\n  <meta name="robots" content="noindex">' if noindex else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">{robots}
  <meta name="color-scheme" content="dark light">
  <meta name="theme-color" content="#050506" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#fbfbfd" media="(prefers-color-scheme: light)">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
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


def page_foot(sample):
    badge = '\n  <div class="proto">Sample content</div>\n' if sample else ""
    return f"""
  <footer class="footer">
    <div class="wrap footer__inner">
      <span>© 2026 Elliott Olson</span>
      <span>Bellevue, Washington</span>
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
    sample = any(post["sample"] for post in posts)
    return page_head("Writing – Elliott Olson",
                     "Notes on evaluating models, building infrastructure, and the work around it.", sample) + f"""
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
      </div>
    </header>

    <section class="wrap">
{card(featured, featured=True)}{grid}    </section>
  </main>
""" + page_foot(sample)


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
    return page_head(f'{post["title"]} – Elliott Olson', post["summary"], post["sample"]) + f"""
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

          <div class="article-end">
            <span>Published {format_date(post["date"])}</span>
            <button class="ghost-button" type="button" data-copy="link">Copy link</button>
          </div>
        </div>

        <nav class="toc" aria-label="Contents">
          <p class="toc__label">Contents</p>
          <ol></ol>
        </nav>
      </div>
    </article>
{next_block}  </main>
""" + page_foot(post["sample"])


def home_rows(posts):
    return "".join(f"""          <li class="row reveal">
            <span class="row__when">{format_date(post["date"])}</span>
            <span class="row__what"><a href="/writing/{post["slug"]}/">{html.escape(post["title"])}</a></span>
            <span class="row__where">{html.escape(post["topic"])} · {post["minutes"]} min</span>
          </li>
""" for post in posts[:3])


# Writing the output

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    posts = sorted((load_post(path) for path in CONTENT.glob("*.md")), key=lambda post: post["date"], reverse=True)
    if not posts:
        sys.exit("No posts found in content/writing/")

    # Drop pages for posts that no longer exist
    slugs = {post["slug"] for post in posts}
    if OUT.exists():
        for folder in OUT.iterdir():
            if folder.is_dir() and folder.name not in slugs:
                shutil.rmtree(folder)

    write(OUT / "index.html", index_page(posts))
    for position, post in enumerate(posts):
        following = posts[(position + 1) % len(posts)] if len(posts) > 1 else None
        write(OUT / post["slug"] / "index.html", article_page(post, following))

    home = SITE / "index.html"
    text = home.read_text(encoding="utf-8")
    if HOME_START not in text or HOME_END not in text:
        sys.exit("site/index.html is missing the writing:start / writing:end markers")
    before, rest = text.split(HOME_START, 1)
    after = rest.split(HOME_END, 1)[1]
    write(home, f"{before}{HOME_START}\n{home_rows(posts)}          {HOME_END}{after}")

    print(f"Built {len(posts)} posts into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
