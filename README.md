# elliottolson.com

Source for my personal website, [elliottolson.com](https://elliottolson.com).

It's a static site in plain HTML, CSS and JavaScript. The home page is written by hand; the Writing section is built from Markdown by a small Python script.

## Structure

```
content/writing/       Posts, one Markdown file each
site/                  Everything that gets published
  index.html           The home page
  404.html             Shown for any URL that doesn't exist
  assets/              Styles and scripts
  writing/             Built from content/writing/ (don't edit by hand)
  linkedin/ github/    Short links, e.g. elliottolson.com/linkedin
  patent/ paper/
  og.png               Preview image used when the site is shared
  robots.txt, sitemap.xml, llms.txt
scripts/
  build_writing.py     Builds the Writing pages, RSS feed and home page list
  make_share_images.py Makes the link preview image for each post
  serve.py             Local preview server
  check_links.py       Link checker
  check_uptime.sh      Checks the live site and its certificate
.github/workflows/
  deploy.yml           Publishes site/ to GitHub Pages
  checks.yml           Link check and Lighthouse audit
  uptime.yml           Hourly check of the live site
```

## Development

Preview the site at <http://localhost:8000>:

```sh
python3 scripts/serve.py
```

Check for broken links:

```sh
python3 scripts/check_links.py
```

## Writing a post

Add a Markdown file to `content/writing/`; its file name becomes the address. It starts with a short header:

```
---
title: What an evaluation score really tells you
date: 2026-10-06
topic: Evaluation
cover: waves
summary: One or two sentences shown on cards and under the title.
---
```

`cover` picks the artwork: `waves`, `rings`, `beams` or `cells`. Add `sample: true` to mark a placeholder post, which hides it from search engines.

The body is ordinary Markdown, plus a few extras:

- `A sentence.^[A note.]` adds a numbered note that opens in place.
- A fenced code block is coloured by language; ` ```python title="retry.py" ` also names the file.
- `::: table Caption`, `::: chart Caption`, `::: diagram Caption` and `::: aside` blocks, each closed with `:::`, add a captioned table, a chart drawn from JSON, an SVG diagram, or a boxed note. `content/writing/evaluation-scores.md` shows every one.

Then build the pages and make the post's share image:

```sh
pip install -r requirements.txt     # once
python3 scripts/build_writing.py
python3 scripts/make_share_images.py
```

The share images need Playwright (`pip install playwright`) and Google Chrome. Commit the Markdown file together with what the build wrote into `site/`.

## Deployment

Every push to `main` publishes the `site/` folder to GitHub Pages. The same push checks that the Writing pages match their Markdown, runs the link check, and runs a Lighthouse audit, which fails if accessibility, best practices or SEO score below 90.

## Monitoring

An hourly workflow runs `scripts/check_uptime.sh`, which fails if the site is down, stops redirecting to HTTPS, or has a certificate within 14 days of expiry.

Visits, link clicks and short link use are counted with [GoatCounter](https://www.goatcounter.com), which sets no cookies and collects no personal data.
