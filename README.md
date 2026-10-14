# elliottolson.com

Source for my personal website, [elliottolson.com](https://elliottolson.com).

It's a static site in plain HTML, CSS and JavaScript. The home page is written by hand; the Writing section is built from Markdown by a small Python script, and the [Status page](https://elliottolson.com/status/) is drawn from the record of an hourly check of the live site.

## Structure

```
content/writing/       Posts, one Markdown file each
  share/               The link preview image for each post
site/                  The hand-written site
  index.html           The home page
  404.html             Shown for any URL that doesn't exist
  assets/              Styles and scripts
  status/              The Status page
  linkedin/ github/    Short links, e.g. elliottolson.com/linkedin
  patent/ paper/
  og.png               Preview image used when the site is shared
  robots.txt, sitemap.xml, llms.txt
dist/                  The finished site, made by the build (not committed)
scripts/
  build.py             Builds the site into dist/: site/ plus the Writing pages, RSS feed and Status data
  make_share_images.py Makes the link preview image for each post
  serve.py             Local preview server
  check_links.py       Link checker
  uptime.py            Checks the live site and its certificate, and records what it found
.github/workflows/
  deploy.yml           Builds the site and publishes it to GitHub Pages
  checks.yml           Link check and Lighthouse audit
  uptime.yml           Hourly check of the live site, which then publishes the Status page
```

## Development

Install the two build tools once:

```sh
pip install -r requirements.txt
```

Preview the site at <http://localhost:8000>. The preview includes drafts, and rebuilds whenever a file changes, so a browser refresh shows the edit:

```sh
python3 scripts/serve.py
```

Check for broken links:

```sh
python3 scripts/build.py --drafts && python3 scripts/check_links.py
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

`cover` picks the artwork: `waves`, `rings`, `beams` or `cells`. Add `draft: true` to keep a post out of the published site; it still appears in the local preview, marked as a draft.

To schedule a post, give it a `date` that is still to come and commit it as usual. It stays off the published site until that day arrives in Pacific time, then appears by itself, because the site is published again every hour. A time can follow the date, as in `date: 2026-10-20 09:00`, to hold the post until then; it goes out with the next hourly publish, at about 17 minutes past. Until then the preview shows it marked as scheduled.

Until there is at least one published post, the site has no Writing section at all: no nav link, no list on the home page and no Writing page. Publishing the first post turns all three on.

The body is ordinary Markdown, plus a few extras:

- `A sentence.^[A note.]` adds a numbered note that opens in place.
- A fenced code block is coloured by language; ` ```python title="retry.py" ` also names the file.
- `::: table Caption`, `::: chart Caption`, `::: diagram Caption` and `::: aside` blocks, each closed with `:::`, add a captioned table, a chart drawn from JSON, an SVG diagram, or a boxed note. `content/writing/example-post.md`, a draft, shows every one.

Then make the post's share image (drafts don't need one, scheduled posts do) and commit it with the Markdown file:

```sh
python3 scripts/make_share_images.py
```

This needs Playwright (`pip install playwright`) and Google Chrome. The image is drawn with the Mac's system font, which is why it is made locally rather than on GitHub.

## Deployment

Every push to `main` builds the site on GitHub and publishes it to GitHub Pages, as does the hourly uptime check, so adding a post only takes committing its Markdown file and share image. The same push runs the link check and a Lighthouse audit, which fails if accessibility, best practices or SEO score below 90. Both checks also run against a build with drafts included, so the Writing pages are tested even before anything is published.

## Monitoring

An hourly workflow runs `scripts/uptime.py`, which fails if the site is down, stops redirecting to HTTPS, or has a certificate within 14 days of expiry.

Each run also adds a line to `uptime.jsonl` on the repository's `uptime` branch, which keeps the hourly commits out of the site's own history. The workflow then publishes the site again, and the build writes a summary of the last 90 days into the [Status page](https://elliottolson.com/status/). To watch something new, add a check to the list in `scripts/uptime.py`; it appears on the page by itself.

The record isn't on `main`, so the local preview shows made-up checks, marked as a sample. `python3 scripts/serve.py 8000 down` shows the page as it looks during an outage, and `new` as it looks in the first days of checks.

Visits, link clicks and short link use are counted with [GoatCounter](https://www.goatcounter.com), which sets no cookies and collects no personal data.
