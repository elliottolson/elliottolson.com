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
.github/workflows/
  deploy.yml           Publishes site/ to GitHub Pages
  checks.yml           Link check and Lighthouse audit
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
