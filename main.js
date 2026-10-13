(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
  const root = document.documentElement;

  // Evaluation matrix: cells fill in a sweep, column by column
  const matrix = document.querySelector('.viz-matrix');
  if (matrix) {
    const cols = Number(getComputedStyle(matrix).getPropertyValue('--cols')) || 26;
    const rows = cols > 20 ? 7 : 8;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cell = document.createElement('i');
        cell.style.setProperty('--t', (c / cols + Math.random() * 0.14).toFixed(3));
        cell.style.setProperty('--v', (0.16 + Math.random() * 0.62).toFixed(2));
        if (Math.random() < 0.09) cell.className = 'hot';
        matrix.append(cell);
      }
    }
  }

  document.querySelectorAll('.viz-nights span').forEach((bar, i) => bar.style.setProperty('--n', i));

  // Marquee: duplicate the items so the loop is seamless
  const track = document.querySelector('.marquee__track');
  if (track && !reduceMotion) {
    [...track.children].forEach((item) => {
      const copy = item.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      track.append(copy);
    });
  }

  // Scroll reveal, staggered within each batch that enters together
  const reveals = document.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    reveals.forEach((el) => el.classList.add('in'));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.filter((e) => e.isIntersecting).forEach((entry, i) => {
        entry.target.style.setProperty('--d', `${i * 0.08}s`);
        entry.target.classList.add('in');
        io.unobserve(entry.target);
        entry.target.querySelectorAll('[data-count]').forEach((el) => countUp(el, i * 80));
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
    reveals.forEach((el) => io.observe(el));
  }

  function countUp(el, delay) {
    const target = Number(el.dataset.count);
    const duration = 1500;
    el.textContent = '0';
    let start;
    const tick = (now) => {
      if (start === undefined) start = now + delay;
      const p = clamp((now - start) / duration, 0, 1);
      el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 4))));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // Statement: words brighten as the line scrolls through the viewport
  const statement = document.getElementById('statement');
  const words = [];
  if (statement && !reduceMotion) {
    const text = statement.textContent.trim();
    statement.setAttribute('aria-label', text);
    statement.textContent = '';
    text.split(/\s+/).forEach((word, i, all) => {
      const span = document.createElement('span');
      span.className = 'w';
      span.setAttribute('aria-hidden', 'true');
      span.textContent = word;
      statement.append(span, i < all.length - 1 ? ' ' : '');
      words.push(span);
    });
  }

  const nav = document.getElementById('nav');
  const navLinks = [...document.querySelectorAll('.nav__links a')];
  const navTargets = navLinks.map((a) => document.querySelector(a.getAttribute('href')));
  let ticking = false;
  const update = () => {
    ticking = false;
    const y = window.scrollY;
    const max = root.scrollHeight - window.innerHeight;
    nav.classList.toggle('is-scrolled', y > 8);
    nav.style.setProperty('--progress', max > 0 ? clamp(y / max, 0, 1).toFixed(4) : 0);

    // Mark the section currently being read
    let current = -1;
    navTargets.forEach((section, i) => {
      if (section && section.getBoundingClientRect().top <= window.innerHeight * 0.4) current = i;
    });
    if (max > 0 && y >= max - 2) current = navTargets.length - 1;
    navLinks.forEach((a, i) => {
      if (i === current) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });

    if (words.length) {
      const rect = statement.getBoundingClientRect();
      const vh = window.innerHeight;
      const progress = clamp((vh * 0.85 - rect.top) / (vh * 0.5), 0, 1);
      const lit = Math.round(progress * words.length);
      words.forEach((w, i) => w.classList.toggle('on', i < lit));
    }
  };
  const onScroll = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  update();

  // Tiles: soft highlight that follows the pointer
  document.querySelectorAll('.tile').forEach((tile) => {
    tile.addEventListener('pointermove', (e) => {
      const rect = tile.getBoundingClientRect();
      tile.style.setProperty('--mx', `${e.clientX - rect.left}px`);
      tile.style.setProperty('--my', `${e.clientY - rect.top}px`);
    });
  });

  // Dot field: ripples slowly, brightens near the pointer, pulses on click
  let dot = '255,255,255', glow = '127,178,255';
  const readColors = () => {
    const styles = getComputedStyle(root);
    dot = styles.getPropertyValue('--dot').trim() || dot;
    glow = styles.getPropertyValue('--glow').trim() || glow;
  };
  readColors();

  const GAP = 30;
  const RIPPLE_SPEED = 0.24;
  const RIPPLE_LIFE = 3400;

  function createField(host) {
    const canvas = host.querySelector('canvas');
    const ctx = canvas && canvas.getContext('2d');
    if (!ctx) return;

    let width = 0, height = 0, cols = 0, rows = 0, offsetX = 0, offsetY = 0;
    let running = false, frame = 0, lastAuto = 0;
    const pointer = { x: 0, y: 0, tx: 0, ty: 0, active: false };
    let ripples = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cols = Math.floor(width / GAP) + 1;
      rows = Math.floor(height / GAP) + 1;
      offsetX = (width - (cols - 1) * GAP) / 2;
      offsetY = (height - (rows - 1) * GAP) / 2;
    };

    const draw = (time) => {
      const t = time * 0.00032;
      pointer.x += (pointer.tx - pointer.x) * 0.12;
      pointer.y += (pointer.ty - pointer.y) * 0.12;
      ripples = ripples.filter((r) => time - r.start < RIPPLE_LIFE);
      ctx.clearRect(0, 0, width, height);

      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const px = offsetX + x * GAP;
          const py = offsetY + y * GAP;
          const wave = Math.sin(x * 0.31 + t * 2.1) * Math.cos(y * 0.27 - t * 1.7)
                     + Math.sin((x + y) * 0.13 + t * 1.2);
          const lift = Math.max(0, wave) / 2;

          let near = 0;
          if (pointer.active) {
            const dx = px - pointer.x;
            const dy = py - pointer.y;
            near = Math.exp(-(dx * dx + dy * dy) / 26000);
          }
          for (const r of ripples) {
            const age = time - r.start;
            const d = Math.hypot(px - r.x, py - r.y) - age * RIPPLE_SPEED;
            near += Math.exp(-(d * d) / 1400) * (1 - age / RIPPLE_LIFE) * r.strength;
          }
          near = Math.min(near, 1);

          const alpha = Math.min(1, 0.14 + lift * 0.42 + near * 0.75);
          const radius = 1 + lift * 0.5 + near * 1.3;
          ctx.fillStyle = near > 0.12 || lift > 0.72
            ? `rgba(${glow},${alpha})`
            : `rgba(${dot},${alpha})`;
          ctx.beginPath();
          ctx.arc(px, py, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    };

    const loop = (time) => {
      if (time - lastAuto > 5200) {
        lastAuto = time;
        ripples.push({ x: Math.random() * width, y: Math.random() * height, start: time, strength: 0.45 });
      }
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

    const locate = (e) => {
      const rect = canvas.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    host.addEventListener('pointermove', (e) => {
      const p = locate(e);
      pointer.tx = p.x;
      pointer.ty = p.y;
      if (!pointer.active) {
        pointer.x = p.x;
        pointer.y = p.y;
        pointer.active = true;
      }
    });
    host.addEventListener('pointerleave', () => { pointer.active = false; });
    host.addEventListener('pointerdown', (e) => {
      const p = locate(e);
      ripples.push({ x: p.x, y: p.y, start: performance.now(), strength: 0.9 });
    });

    let visible = false;
    window.addEventListener('resize', () => { resize(); if (!running) draw(0); });
    document.addEventListener('visibilitychange', () => (document.hidden || !visible ? stop() : start()));
    new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      visible ? start() : stop();
    }).observe(host);

    resize();
    draw(0);
    return () => { if (!running) draw(0); };
  }

  const redraws = [...document.querySelectorAll('[data-field]')].map(createField).filter(Boolean);
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    readColors();
    redraws.forEach((redraw) => redraw());
  });
})();
