# elliottolson.com

Source for my personal website, [elliottolson.com](https://elliottolson.com).

It's a static site in plain HTML, CSS and JavaScript. The home page is written by hand; the Writing section is built from Markdown by a small Python script.

## Structure

```
content/writing/       Posts, one Markdown file each
  share/               The link preview image for each post
site/                  The hand-written site
  index.html           The home page
  404.html             Shown for any URL that doesn't exist
  assets/              Styles and scripts
  linkedin/ github/    Short links, e.g. elliottolson.com/linkedin
  patent/ paper/
  og.png               Preview image used when the site is shared
  robots.txt, sitemap.xml, llms.txt
dist/                  The finished site, made by the build (not committed)
scripts/
  build.py             Builds the site into dist/: site/ plus the Writing pages and RSS feed
  make_share_images.py Makes the link preview image for each post
  serve.py             Local preview server
  check_links.py       Link checker
  check_uptime.sh      Checks the live site and its certificate
.github/workflows/
  deploy.yml           Builds the site and publishes it to GitHub Pages
  checks.yml           Link check and Lighthouse audit
  uptime.yml           Hourly check of the live site
```

## Development

Install the two build tools once:

```sh
pip install -r requirements.txt
```

Preview the site at <http://localhost:8000>. It rebuilds whenever a file changes, so a browser refresh shows the edit:

```sh
python3 scripts/serve.py
```

Check for broken links:

```sh
python3 scripts/build.py && python3 scripts/check_links.py
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

Then make the post's share image and commit it with the Markdown file:

```sh
python3 scripts/make_share_images.py
```

This needs Playwright (`pip install playwright`) and Google Chrome. The image is drawn with the Mac's system font, which is why it is made locally rather than on GitHub.

## Deployment

Every push to `main` builds the site on GitHub and publishes it to GitHub Pages, so adding a post only takes committing its Markdown file and share image. The same push runs the link check and a Lighthouse audit, which fails if accessibility, best practices or SEO score below 90.

## Monitoring

An hourly workflow runs `scripts/check_uptime.sh`, which fails if the site is down, stops redirecting to HTTPS, or has a certificate within 14 days of expiry.

Visits, link clicks and short link use are counted with [GoatCounter](https://www.goatcounter.com), which sets no cookies and collects no personal data.
