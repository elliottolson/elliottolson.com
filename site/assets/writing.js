(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const root = document.documentElement;

  // Covers: halftone artwork generated per post, in the same dot language as the home page
  let dot = '255,255,255', glow = '127,178,255';
  const readColors = () => {
    const styles = getComputedStyle(root);
    dot = styles.getPropertyValue('--dot').trim() || dot;
    glow = styles.getPropertyValue('--glow').trim() || glow;
  };
  readColors();

  const hash = (text) => {
    let h = 2166136261;
    for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
    return (h >>> 0) / 4294967295;
  };
  const noise = (x, y, seed) => {
    const n = Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453;
    return n - Math.floor(n);
  };

  // Each pattern maps a point (u, v in 0..1, aspect-corrected x) and time to a brightness in 0..1
  const patterns = {
    waves: (u, v, x, t) => 0.5 + 0.25 * Math.sin(x * 7 + t * 1.3) * Math.cos(v * 6 - t) + 0.25 * Math.sin((x + v) * 4.5 + t * 0.7),
    rings: (u, v, x, t, s) => 0.5 + 0.5 * Math.sin(Math.hypot(x - (0.4 + s * 0.9), v - (0.25 + s * 0.5)) * 17 - t * 1.8),
    beams: (u, v, x, t) => 0.5 + 0.5 * Math.sin((x * 1.3 + v) * 8 - t * 1.5) * Math.cos(v * 2.2 + t * 0.3),
    cells: (u, v, x, t, s, cx, cy) => {
      const h = noise(Math.floor(cx / 3), Math.floor(cy / 3), s);
      return 0.5 + 0.5 * Math.sin(h * 6.283 + t * (0.6 + h * 1.4));
    },
  };

  function createCover(canvas) {
    const ctx = canvas.getContext('2d');
    const pattern = patterns[canvas.dataset.cover] || patterns.waves;
    const seed = hash(canvas.dataset.seed || canvas.dataset.cover || 'cover');
    let width = 0, height = 0, gap = 14, cols = 0, rows = 0, running = false, frame = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      if (!rect.width) return;
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      gap = Math.min(18, Math.max(9, width / 52));
      cols = Math.ceil(width / gap) + 1;
      rows = Math.ceil(height / gap) + 1;
    };

    const draw = (time) => {
      const t = time * 0.00045 + seed * 40;
      const aspect = width / height;
      ctx.clearRect(0, 0, width, height);
      for (let cy = 0; cy < rows; cy++) {
        for (let cx = 0; cx < cols; cx++) {
          const u = cx / (cols - 1);
          const v = cy / (rows - 1);
          const value = Math.min(1, Math.max(0, pattern(u, v, u * aspect, t, seed, cx, cy)));
          const shaped = value * value;
          ctx.fillStyle = value > 0.95 ? `rgba(${glow},${0.2 + shaped * 0.8})` : `rgba(${dot},${0.08 + shaped * 0.62})`;
          ctx.beginPath();
          ctx.arc(cx * gap, cy * gap, gap * (0.07 + shaped * 0.36), 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    const loop = (time) => {
      draw(time);
      if (running) frame = requestAnimationFrame(loop);
    };
    const start = () => {
      if (running || reduceMotion || document.hidden) return;
      running = true;
      frame = requestAnimationFrame(loop);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(frame);
    };

    let visible = false;
    new ResizeObserver(() => { resize(); if (!running) draw(0); }).observe(canvas);
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      visible ? start() : stop();
    }).observe(canvas);
    document.addEventListener('visibilitychange', () => (document.hidden || !visible ? stop() : start()));

    resize();
    draw(0);
    return () => { if (!running) draw(0); };
  }

  const redraws = [...document.querySelectorAll('canvas[data-cover]')].map(createCover);
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    readColors();
    redraws.forEach((redraw) => redraw());
  });

  // Index: filter posts by topic
  const chips = [...document.querySelectorAll('.chip')];
  const posts = [...document.querySelectorAll('.posts .post')];
  const count = document.querySelector('.posts-head__count');
  if (chips.length) {
    const apply = (topic) => {
      let shown = 0;
      posts.forEach((post) => {
        post.hidden = topic !== 'all' && post.dataset.topic !== topic;
        if (!post.hidden) shown++;
      });
      chips.forEach((chip) => chip.setAttribute('aria-pressed', String(chip.dataset.topic === topic)));
      if (count) count.textContent = `${shown} ${shown === 1 ? 'post' : 'posts'}`;
    };
    chips.forEach((chip) => chip.addEventListener('click', () => {
      const run = () => apply(chip.dataset.topic);
      if (document.startViewTransition && !reduceMotion) document.startViewTransition(run);
      else run();
    }));
  }

  // Article: build the contents list from the headings and highlight the current one
  const toc = document.querySelector('.toc ol');
  const headings = [...document.querySelectorAll('.prose h2')];
  if (toc && headings.length) {
    const links = headings.map((heading) => {
      if (!heading.id) heading.id = heading.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      const link = document.createElement('a');
      link.href = `#${heading.id}`;
      link.textContent = [...heading.childNodes]
        .filter((node) => !(node.classList && node.classList.contains('anchor')))
        .map((node) => node.textContent).join('').trim();
      const item = document.createElement('li');
      item.append(link);
      toc.append(item);
      return link;
    });
    let ticking = false;
    const update = () => {
      ticking = false;
      let current = 0;
      headings.forEach((heading, i) => {
        if (heading.getBoundingClientRect().top <= window.innerHeight * 0.3) current = i;
      });
      links.forEach((link, i) => link.classList.toggle('is-active', i === current));
    };
    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    }, { passive: true });
    update();
  }

  // Notes: a numbered reference in the text that opens its note in place
  document.querySelectorAll('.note-ref').forEach((ref, i) => {
    const note = ref.nextElementSibling;
    if (!note || !note.classList.contains('note')) return;
    note.id = note.id || `note-${i + 1}`;
    ref.setAttribute('aria-label', `Note ${i + 1}`);
    ref.setAttribute('aria-controls', note.id);
    ref.setAttribute('aria-expanded', 'false');
    ref.addEventListener('click', () => {
      const open = note.classList.toggle('is-open');
      ref.setAttribute('aria-expanded', String(open));
    });
  });

  // Charts: line and column charts drawn as SVG from JSON embedded in the figure
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const svgEl = (name, attrs = {}, text) => {
    const node = document.createElementNS(SVG_NS, name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const htmlEl = (name, className, text) => {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const niceMax = (max) => {
    const pow = 10 ** Math.floor(Math.log10(max));
    const n = max / pow;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * pow;
  };
  const compact = (value) => (value >= 1000 ? `${+(value / 1000).toFixed(1)}K` : String(+value.toFixed(1)));

  function createChart(figure) {
    const data = JSON.parse(figure.querySelector('script[type="application/json"]').textContent);
    const unit = data.unit ? ` ${data.unit}` : '';
    const isLine = data.type === 'line';
    const count = data.x.length;

    const body = htmlEl('div', 'chart__body');
    if (data.title) body.append(htmlEl('p', 'chart__title', data.title));
    if (data.subtitle) body.append(htmlEl('p', 'chart__subtitle', data.subtitle));
    if (data.series.length > 1) {
      const legend = htmlEl('div', 'chart__legend');
      data.series.forEach((series, k) => {
        const item = htmlEl('span');
        const key = htmlEl('span', 'chart__key');
        key.style.setProperty('--c', `var(--series-${k + 1})`);
        item.append(key, series.name);
        legend.append(item);
      });
      body.append(legend);
    }

    const plot = htmlEl('div', 'chart__plot');
    const svg = svgEl('svg', { role: 'img', tabindex: '0', 'aria-label': `${data.title || 'Chart'}. Use the arrow keys to read values.` });
    const tip = htmlEl('div', 'chart__tip');
    plot.append(svg, tip);
    body.append(plot);

    // The same numbers as a table, so nothing is only reachable by hovering
    const details = htmlEl('details', 'chart__data');
    details.append(htmlEl('summary', '', 'View data as a table'));
    const table = htmlEl('table');
    const headRow = htmlEl('tr');
    headRow.append(htmlEl('th', '', data.xLabel || ''));
    data.series.forEach((series) => headRow.append(htmlEl('th', 'num', `${series.name}${data.unit ? ` (${data.unit})` : ''}`)));
    const thead = htmlEl('thead');
    thead.append(headRow);
    const tbody = htmlEl('tbody');
    data.x.forEach((label, i) => {
      const row = htmlEl('tr');
      row.append(htmlEl('td', '', label));
      data.series.forEach((series) => row.append(htmlEl('td', 'num', String(series.values[i]))));
      tbody.append(row);
    });
    table.append(thead, tbody);
    const scroll = htmlEl('div', 'table__scroll');
    scroll.append(table);
    details.append(scroll);
    body.append(details);
    figure.prepend(body);

    let show = () => {};
    let hide = () => {};
    let active = -1;

    const render = () => {
      const width = plot.clientWidth;
      if (!width) return;
      const height = width < 480 ? 230 : width > 800 ? 400 : 290;
      const m = { top: 18, right: isLine ? 46 : 8, bottom: 28, left: 40 };
      const iw = width - m.left - m.right;
      const ih = height - m.top - m.bottom;
      const max = niceMax(Math.max(...data.series.flatMap((series) => series.values)));
      const xAt = (i) => (isLine ? m.left + (count === 1 ? iw / 2 : (i * iw) / (count - 1)) : m.left + ((i + 0.5) * iw) / count);
      const yAt = (value) => m.top + ih - (value / max) * ih;

      svg.replaceChildren();
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      svg.setAttribute('height', height);

      for (let i = 0; i <= 4; i++) {
        const value = (max * i) / 4;
        svg.append(
          svgEl('line', { class: 'chart__grid', x1: m.left, x2: m.left + iw, y1: yAt(value), y2: yAt(value) }),
          svgEl('text', { class: 'chart__tick', x: m.left - 8, y: yAt(value), 'text-anchor': 'end', 'dominant-baseline': 'central' }, compact(value)),
        );
      }
      const every = Math.max(1, Math.ceil(count / Math.max(1, Math.floor(iw / 58))));
      data.x.forEach((label, i) => {
        if (i % every) return;
        svg.append(svgEl('text', { class: 'chart__tick', x: xAt(i), y: height - 6, 'text-anchor': 'middle' }, label));
      });

      const cross = svgEl('line', { class: 'chart__cross', y1: m.top, y2: m.top + ih, visibility: 'hidden' });
      const bars = [];
      const hoverDots = [];

      if (isLine) {
        svg.append(cross);
        let lastLabelY = -Infinity;
        data.series.forEach((series, k) => {
          const color = `var(--series-${k + 1})`;
          const d = series.values.map((value, i) => `${i ? 'L' : 'M'}${xAt(i).toFixed(1)} ${yAt(value).toFixed(1)}`).join(' ');
          svg.append(svgEl('path', { class: 'chart__line', d, pathLength: 1, stroke: color }));
          const lastValue = series.values[count - 1];
          const end = svgEl('g', { class: 'chart__end' });
          end.append(svgEl('circle', { class: 'chart__dot', cx: xAt(count - 1), cy: yAt(lastValue), r: 5, fill: color }));
          // Label the end of each line unless it would sit on top of another label
          if (Math.abs(yAt(lastValue) - lastLabelY) > 15) {
            end.append(svgEl('text', { class: 'chart__value', x: xAt(count - 1) + 10, y: yAt(lastValue), 'dominant-baseline': 'central' }, compact(lastValue)));
            lastLabelY = yAt(lastValue);
          }
          svg.append(end);
          const dot = svgEl('circle', { class: 'chart__dot', r: 5, fill: color, visibility: 'hidden' });
          hoverDots.push(dot);
        });
        hoverDots.forEach((dot) => svg.append(dot));
      } else {
        const barWidth = Math.min(24, (iw / count) * 0.6);
        data.series[0].values.forEach((value, i) => {
          const x = xAt(i) - barWidth / 2;
          const y = yAt(value);
          const base = m.top + ih;
          const r = Math.min(4, (base - y) / 2);
          const d = `M${x} ${base} V${y + r} Q${x} ${y} ${x + r} ${y} H${x + barWidth - r} Q${x + barWidth} ${y} ${x + barWidth} ${y + r} V${base} Z`;
          const bar = svgEl('path', { class: 'chart__bar', d });
          bar.style.setProperty('--n', i);
          bars.push(bar);
          const label = svgEl('g', { class: 'chart__end' });
          label.append(svgEl('text', { class: 'chart__value', x: xAt(i), y: y - 8, 'text-anchor': 'middle' }, compact(value)));
          svg.append(bar, label);
        });
      }

      const hit = svgEl('rect', { class: 'chart__hit', x: m.left, y: m.top, width: iw, height: ih + m.bottom });
      svg.append(hit);

      show = (i) => {
        active = i;
        tip.replaceChildren(htmlEl('div', 'chart__tip-title', data.x[i]));
        data.series.forEach((series, k) => {
          const row = htmlEl('div', 'chart__tip-row');
          const name = htmlEl('span');
          const key = htmlEl('span', 'chart__key');
          key.style.setProperty('--c', `var(--series-${k + 1})`);
          name.append(key, series.name);
          row.append(name, htmlEl('strong', '', `${series.values[i]}${unit}`));
          tip.append(row);
        });
        if (isLine) {
          cross.setAttribute('x1', xAt(i));
          cross.setAttribute('x2', xAt(i));
          cross.setAttribute('visibility', 'visible');
          hoverDots.forEach((dot, k) => {
            dot.setAttribute('cx', xAt(i));
            dot.setAttribute('cy', yAt(data.series[k].values[i]));
            dot.setAttribute('visibility', 'visible');
          });
        } else {
          bars.forEach((bar, b) => bar.classList.toggle('is-dim', b !== i));
        }
        tip.classList.add('is-on');
        const left = xAt(i) + 14 + tip.offsetWidth > width ? xAt(i) - 14 - tip.offsetWidth : xAt(i) + 14;
        tip.style.transform = `translate(${Math.max(0, left)}px, ${m.top}px)`;
      };
      hide = () => {
        active = -1;
        tip.classList.remove('is-on');
        cross.setAttribute('visibility', 'hidden');
        hoverDots.forEach((dot) => dot.setAttribute('visibility', 'hidden'));
        bars.forEach((bar) => bar.classList.remove('is-dim'));
      };

      hit.addEventListener('pointermove', (event) => {
        const x = event.clientX - svg.getBoundingClientRect().left;
        const i = isLine
          ? Math.round(((x - m.left) / iw) * (count - 1))
          : Math.floor(((x - m.left) / iw) * count);
        const index = Math.min(count - 1, Math.max(0, i));
        if (index !== active) show(index);
      });
      hit.addEventListener('pointerleave', () => hide());
    };

    svg.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      const start = active < 0 ? (event.key === 'ArrowRight' ? -1 : count) : active;
      show(Math.min(count - 1, Math.max(0, start + (event.key === 'ArrowRight' ? 1 : -1))));
    });
    svg.addEventListener('blur', () => hide());

    new ResizeObserver(render).observe(plot);
    render();
    if (reduceMotion) figure.classList.add('is-in');
    else {
      const io = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) return;
        figure.classList.add('is-in');
        io.disconnect();
      }, { threshold: 0.35 });
      io.observe(figure);
    }
  }
  // Click to enlarge: tables, charts and diagrams open large over a dimmed page
  const figures = [...document.querySelectorAll('.prose figure.table, .prose figure.chart, .prose figure.diagram')];
  if (figures.length && window.HTMLDialogElement) {
    const dialog = htmlEl('dialog', 'lightbox');
    dialog.setAttribute('aria-label', 'Enlarged figure');
    const close = htmlEl('button', 'ghost-button lightbox__close', 'Close');
    close.type = 'button';
    const stage = htmlEl('div', 'lightbox__stage prose');
    dialog.append(close, stage);
    document.body.append(dialog);
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => stage.replaceChildren());

    figures.forEach((figure) => {
      // Keep an untouched copy, taken before a chart is drawn into the figure
      const source = figure.cloneNode(true);
      const button = htmlEl('button', 'figure__expand');
      button.type = 'button';
      button.setAttribute('aria-label', 'Enlarge');
      const icon = svgEl('svg', { viewBox: '0 0 16 16', 'aria-hidden': 'true' });
      icon.append(svgEl('path', { d: 'M9.5 2.5h4v4M13.5 2.5 9 7M6.5 13.5h-4v-4M2.5 13.5 7 9' }));
      button.append(icon);
      button.addEventListener('click', () => {
        const copy = source.cloneNode(true);
        stage.replaceChildren(copy);
        dialog.showModal();
        if (copy.classList.contains('chart')) createChart(copy);
      });
      figure.append(button);
    });
  }

  document.querySelectorAll('.article-layout figure.chart').forEach(createChart);

  // Section links: clicking the # beside a heading also copies a link to it
  document.querySelectorAll('.prose .anchor').forEach((anchor) => {
    anchor.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(`${location.origin}${location.pathname}${anchor.getAttribute('href')}`);
        anchor.classList.add('is-copied');
        setTimeout(() => anchor.classList.remove('is-copied'), 1600);
      } catch (error) {
        // The link still works as a normal jump if copying isn't allowed
      }
    });
  });

  // Copy buttons, for the page link and for code blocks
  document.querySelectorAll('[data-copy]').forEach((button) => {
    const label = button.textContent;
    button.addEventListener('click', async () => {
      const text = button.dataset.copy === 'link'
        ? location.href.split('#')[0]
        : button.closest('.code').querySelector('pre').textContent;
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = 'Copied';
      } catch (error) {
        button.textContent = 'Copy failed';
      }
      setTimeout(() => { button.textContent = label; }, 1600);
    });
  });
})();
