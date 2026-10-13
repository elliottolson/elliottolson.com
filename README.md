# elliottolson.com

Source for my personal website, [elliottolson.com](https://elliottolson.com).

It's a single static page in plain HTML, CSS and JavaScript, with no build step or dependencies. GitHub Pages serves the `main` branch as is.

## Preview locally

```sh
python3 -m http.server 8000
```

Then open <http://localhost:8000>.

## Files

- `index.html`, `styles.css`, `main.js`: the page, its styles, and its animations
- `404.html`: shown for any URL that doesn't exist
- `og.png`: the preview image used when the site is shared
- `CNAME`: the custom domain for GitHub Pages
- `robots.txt`, `sitemap.xml`, `llms.txt`: files for search engines and other crawlers
