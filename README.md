# elliottolson.com

Source for my personal website, [elliottolson.com](https://elliottolson.com).

It's a single static page in plain HTML, CSS and JavaScript, with no build step and no dependencies.

## Structure

```
site/                  Everything that gets published
  index.html           The page
  404.html             Shown for any URL that doesn't exist
  assets/              Styles and scripts
  linkedin/ github/    Short links, e.g. elliottolson.com/linkedin
  patent/ paper/
  og.png               Preview image used when the site is shared
  robots.txt, sitemap.xml, llms.txt
scripts/
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

## Deployment

Every push to `main` publishes the `site/` folder to GitHub Pages. The same push runs the link check and a Lighthouse audit, which fails if accessibility, best practices or SEO score below 90.

## Monitoring

An hourly workflow runs `scripts/check_uptime.sh`, which fails if the site is down, stops redirecting to HTTPS, or has a certificate within 14 days of expiry.

Visits, link clicks and short link use are counted with [GoatCounter](https://www.goatcounter.com), which sets no cookies and collects no personal data.
