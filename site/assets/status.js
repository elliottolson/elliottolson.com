// Status page: drawn from the record of the uptime checks, which build.py writes into the page.
// This runs before main.js, which then reveals and animates what has been drawn here.
(() => {
  const data = JSON.parse(document.getElementById('status-data').textContent);
  const root = document.documentElement;
  const $ = (id) => document.getElementById(id);
  const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const HOUR = 3600e3;
  const DAY = 24 * HOUR;
  const STALE_AFTER = 3 * HOUR;
  const dayFormat = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', timeZone: 'UTC' });
  const timeFormat = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  const ago = (time) => {
    const minutes = Math.round((Date.now() - time) / 60e3);
    if (minutes < 2) return 'just now';
    if (minutes < 60) return `${minutes} minutes ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 36) return hours === 1 ? 'an hour ago' : `${hours} hours ago`;
    return `${Math.round(hours / 24)} days ago`;
  };
  const lasted = (ms) => {
    const hours = Math.max(1, Math.round(ms / HOUR));
    if (hours < 48) return hours === 1 ? 'about an hour' : `about ${hours} hours`;
    return `about ${Math.round(hours / 24)} days`;
  };

  // What the latest check found
  const checked = data ? Date.parse(data.checked) : 0;
  const failing = data ? data.checks.filter((check) => !check.ok) : [];
  const state = !data ? 'none'
    : !data.sample && Date.now() - checked > STALE_AFTER ? 'stale'
    : !failing.length ? 'ok'
    : failing.some((check) => check.id === 'site') ? 'down' : 'warn';
  if (state === 'ok' || state === 'warn' || state === 'down') root.dataset.state = state;

  const headline = $('headline');
  const title = {
    ok: 'All systems operational.',
    warn: 'Something needs attention.',
    down: 'The site is down.',
    stale: 'No recent checks.',
    none: 'No checks yet.',
  }[state];
  headline.textContent = '';
  headline.setAttribute('aria-label', title);
  title.split(' ').forEach((word, i) => {
    const span = el('span', 'word', word);
    span.style.setProperty('--i', i + 1);
    span.setAttribute('aria-hidden', 'true');
    headline.append(span, ' ');
  });
  headline.classList.add('is-set');

  const describe = () => {
    $('summary').textContent = {
      ok: () => `Checked ${ago(checked)}. The checks run every hour.`,
      warn: () => `${failing[0].error}. Checked ${ago(checked)}.`,
      down: () => `${failing[0].error}. Checked ${ago(checked)}.`,
      stale: () => `The last check ran ${ago(checked)}, so this page may be out of date.`,
      none: () => 'The first check hasn’t run yet.',
    }[state]();
  };
  describe();

  if (!data) {
    document.querySelectorAll('main > section:not(.hero)').forEach((section) => { section.hidden = true; });
    return;
  }
  setInterval(describe, 30e3);

  if (data.sample) document.body.append(el('div', 'proto', 'Sample data · not real checks'));

  // The page looks back a fixed number of days, but the checks may not have been running that long
  const site = data.checks.find((check) => check.id === 'site') || data.checks[0];
  const shown = site.history.length;
  const since = Date.parse(data.since);
  const whole = Date.now() - since > (shown - 2) * DAY;
  const period = whole ? `the last ${shown} days` : `since ${dayFormat.format(since)}`;

  // Numbers count up when main.js reveals their tile
  const count = (node, value) => {
    if (value == null) return;
    node.textContent = String(value);
    node.dataset.count = String(value);
  };

  // Uptime
  $('uptime-label').textContent = `Uptime · ${period}`;
  count($('uptime'), site.uptime);
  $('uptime-total').textContent = site.total.toLocaleString('en');
  const ring = $('uptime-ring');
  ring.style.setProperty('--p', site.uptime || 0);
  if (site.uptime < 99) ring.classList.add(site.uptime < 95 ? 'is-down' : 'is-warn');

  // Response time, with a line through the most recent checks
  count($('response'), data.response.average);
  const times = data.response.recent;
  const points = times.map((ms, i) => [i, ms]).filter((point) => point[1] != null);
  if (points.length > 1) {
    const W = 300, H = 124, PAD = 12;
    const low = Math.min(...points.map((point) => point[1]));
    const high = Math.max(...points.map((point) => point[1]));
    const x = (i) => (i / (times.length - 1) * W).toFixed(1);
    const y = (ms) => (PAD + (1 - (ms - low) / (high - low || 1)) * (H - PAD * 2)).toFixed(1);
    const line = points.map(([i, ms], n) => `${n ? 'L' : 'M'}${x(i)} ${y(ms)}`).join(' ');
    const [endAt, endMs] = points[points.length - 1];
    $('spark').innerHTML = `<svg viewBox="0 0 ${W} ${H}">
      <defs><linearGradient id="spark-fade" x1="0" y1="0" x2="0" y2="1">
        <stop class="spark__stop" offset="0" stop-opacity="0.26"/><stop class="spark__stop" offset="1" stop-opacity="0"/>
      </linearGradient></defs>
      <path class="spark__area" fill="url(#spark-fade)" d="${line} L${x(endAt)} ${H} L${x(points[0][0])} ${H} Z"/>
      <path class="spark__line" pathLength="1" d="${line}"/>
      <circle class="spark__halo" cx="${x(endAt)}" cy="${y(endMs)}" r="4"/>
      <circle class="spark__dot" cx="${x(endAt)}" cy="${y(endMs)}" r="4"/>
    </svg>`;
  }

  // Certificate: how far through its life it is
  const { days, of } = data.certificate;
  count($('certificate'), days);
  if (days != null && of) {
    $('term').style.setProperty('--p', clamp((1 - days / of) * 100, 0, 100).toFixed(1));
    $('term-issued').textContent = `Issued ${dayFormat.format(checked - (of - days) * DAY)}`;
    $('term-expires').textContent = `Expires ${dayFormat.format(checked + days * DAY)}`;
  } else {
    $('term').hidden = true;
  }

  // Checks: one bar per day, coloured by how many of that day's checks failed
  const from = Date.parse(data.from);
  const tone = ([passed, total]) => (!total ? 'none' : passed === total ? 'ok' : (total - passed) / total < 0.25 ? 'warn' : 'down');
  const tip = $('tip');
  let lit = null;
  const hideTip = () => {
    if (lit) lit.classList.remove('on');
    lit = null;
    tip.classList.remove('on');
  };
  const showTip = (strip, check, event) => {
    // The bars have gaps between them, so the day is worked out from where the pointer is along the strip
    const all = [...strip.children];
    const bars = all.filter((bar) => bar.offsetWidth);
    const box = strip.getBoundingClientRect();
    const bar = bars[clamp(Math.floor((event.clientX - box.left) / box.width * bars.length), 0, bars.length - 1)];
    if (bar === lit) return;
    hideTip();
    lit = bar;
    bar.classList.add('on');
    const index = all.indexOf(bar);
    const [passed, total] = check.history[index];
    tip.firstElementChild.textContent = index === all.length - 1 ? 'Today' : dayFormat.format(from + index * DAY);
    tip.lastElementChild.textContent = total ? `${passed} of ${plural(total, 'check')} passed` : 'No checks recorded';
    tip.classList.add('on');
    const at = bar.getBoundingClientRect();
    const left = clamp(at.left + at.width / 2 - tip.offsetWidth / 2, 8, window.innerWidth - tip.offsetWidth - 8);
    tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(box.top - tip.offsetHeight - 14)}px)`;
  };

  data.checks.forEach((check) => {
    const item = el('article', 'check reveal');
    const head = el('header', 'check__head');
    head.append(
      el('h3', 'check__name', check.name),
      el('span', check.ok ? 'pill' : 'pill pill--down', check.ok ? 'Operational' : 'Failing'),
      el('span', 'check__uptime', check.uptime == null ? '–' : `${check.uptime}%`),
    );

    const strip = el('div', 'days');
    strip.setAttribute('role', 'img');
    strip.setAttribute('aria-label', check.uptime == null ? `${check.name}: no checks recorded`
      : `${check.name}: ${check.uptime}% of checks passed ${whole ? 'in ' : ''}${period}`);
    check.history.forEach((day, n) => {
      const bar = el('i', tone(day));
      bar.style.setProperty('--n', n);
      strip.append(bar);
    });
    strip.addEventListener('pointermove', (event) => showTip(strip, check, event));
    strip.addEventListener('pointerdown', (event) => showTip(strip, check, event));
    // A finger lifting shouldn't take the answer away with it
    strip.addEventListener('pointerleave', (event) => { if (event.pointerType !== 'touch') hideTip(); });

    const scale = el('div', 'days__scale');
    scale.append(
      el('span', 'wide', `${shown} days ago`),
      el('span', 'narrow', `${shown / 2} days ago`),
      el('span', '', 'Today'),
    );
    item.append(head, el('p', 'check__about', check.about), strip, scale);
    $('check-list').append(item);
  });
  window.addEventListener('scroll', hideTip, { passive: true });
  document.addEventListener('pointerdown', (event) => { if (!event.target.closest('.days')) hideTip(); });

  // History: every stretch of failing checks
  $('history-title').textContent = `Incidents ${whole ? 'in ' : ''}${period}.`;
  const list = $('incident-list');
  if (!data.incidents.length) {
    list.append(el('li', 'rows__empty reveal', `Nothing has gone wrong ${whole ? 'in ' : ''}${period}.`));
  }
  data.incidents.forEach((incident) => {
    const row = el('li', 'row reveal');
    const what = incident.checks.length === data.checks.length ? 'All checks' : incident.checks.join(', ');
    const where = el('span', 'row__where', `${what} · ${incident.end ? lasted(Date.parse(incident.end) - Date.parse(incident.start)) : 'ongoing'}`);
    if (!incident.end) where.classList.add('is-open');
    row.append(
      el('span', 'row__when', timeFormat.format(Date.parse(incident.start))),
      el('span', 'row__what', incident.error),
      where,
    );
    list.append(row);
  });
})();
